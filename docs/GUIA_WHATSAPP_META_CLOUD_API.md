# Guía paso a paso: Meta WhatsApp Cloud API

Integración directa con la API de WhatsApp de Meta (sin Twilio ni 360dialog).

---

## Requisitos previos

- [ ] Cuenta de **Facebook** o **Meta**
- [ ] Número de teléfono (para verificar la cuenta)
- [ ] Número de WhatsApp Business (puede ser el mismo del taller o uno dedicado)
- [ ] Dominio con HTTPS (para webhooks; en desarrollo puedes usar ngrok)

---

## Fase 1: Cuenta Meta Business y app

### Paso 1.1: Meta for Developers

1. Entra a **[developers.facebook.com](https://developers.facebook.com)**
2. Inicia sesión con tu cuenta de Facebook
3. Haz clic en **"My Apps"** (Mis aplicaciones)
4. Clic en **"Create App"** (Crear aplicación)
5. Elige **"Business"** y clic en **"Next"**
6. Completa:
   - **App name:** `Medina Auto-Diag` (o el nombre de tu taller)
   - **App contact email:** tu correo
   - **Business Account:** selecciona tu empresa o crea una nueva
7. Clic en **"Create App"**

### Paso 1.2: Agregar producto WhatsApp

1. En el panel de tu app, ve a **"Add Products"** (Agregar productos) o **"Set up"**
2. Busca **"WhatsApp"** y clic en **"Set up"**
3. Te redirigirá al **WhatsApp → API Setup**

---

## Fase 2: Número de teléfono y WhatsApp Business Account

### Paso 2.1: Crear o usar WhatsApp Business Account

1. En **WhatsApp → API Setup** verás tu **WhatsApp Business Account ID**
2. Si no tienes una, Meta la crea al agregar el producto
3. Anota el **WhatsApp Business Account ID** (lo usarás después)

### Paso 2.2: Agregar número de teléfono

¿Necesitas un número virtual? Ver **[GUIA_NUMERO_VIRTUAL_TWILIO_META.md](GUIA_NUMERO_VIRTUAL_TWILIO_META.md)** para comprarlo en Twilio (México) y vincularlo aquí.

1. En la misma pantalla, sección **"Phone numbers"**
2. Clic en **"Add phone number"** (Agregar número)
3. Completa:
   - **Business phone number:** número con el que enviarás mensajes (formato: 5215512345678)
   - **Display name:** nombre que verá el cliente (ej. `Medina Auto-Diag`)
   - **Timezone:** `America/Mexico_City`
   - **About:** breve descripción del negocio
   - **Category:** `Automotive` o `Other`
4. Verifica el número: elige **SMS** o **Voice call**, ingresa el código
5. Al terminar, verás:
   - **Phone Number ID** → anótalo
   - **WhatsApp ID** → formato `+5215512345678` (con código de país)

**Importante:** anota:
- `PHONE_NUMBER_ID`
- `WHATSAPP_ID` (ej. `+5215512345678`)

---

## Fase 3: Token de acceso (Access Token)

### Paso 3.1: Token temporal (solo desarrollo)

1. En **WhatsApp → API Setup**, sección **"Temporary access token"**
2. Clic en **"Generate"**
3. Copia el token (válido ~24 horas, sirve para pruebas)
4. Guárdalo como `WHATSAPP_ACCESS_TOKEN`

### Paso 3.2: Token permanente (producción)

1. Ve a **[business.facebook.com](https://business.facebook.com)**
2. **Configuración del negocio** (Business Settings) → **Cuentas** → **Usuarios del sistema** (System Users)
3. Clic en **"Agregar"** y crea un usuario de sistema (ej. `medina-whatsapp-bot`)
4. Asigna rol **Administrador**
5. Clic en **"Generar token"** para ese usuario
6. Selecciona tu **App** (Medina Auto-Diag)
7. Marca permisos: **`whatsapp_business_management`** y **`whatsapp_business_messaging`**
8. Genera y copia el token (válido 60 días por defecto; puedes extenderlo)
9. Guárdalo en un gestor de secretos (Railway Variables, .env, etc.)

**Variables que necesitarás:**
```env
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxx...
WHATSAPP_PHONE_NUMBER_ID=123456789012345
```

---

## Fase 4: Plantillas de mensajes

WhatsApp exige plantillas aprobadas para mensajes proactivos.

### Paso 4.1: Crear plantilla desde Meta Business Suite

1. Entra a **[business.facebook.com](https://business.facebook.com)**
2. **Todos los servicios** → **WhatsApp Manager**
3. Menú **"Plantillas de mensajes"** (Message Templates) → **"Crear plantilla"**
4. O desde **developers.facebook.com** → Tu app → **WhatsApp** → **Message templates**

### Paso 4.2: Plantilla "Confirmación de cita"

- **Nombre:** `confirmacion_cita` (solo minúsculas y guiones bajos)
- **Categoría:** Utility (Utilidad)
- **Idioma:** Spanish
- **Componentes:**

**Header** (opcional): tipo Texto
```
Medina Auto-Diag - Confirmación
```

**Body** (obligatorio):
```
Hola {{1}}, tu cita ha sido confirmada.

📅 Fecha: {{2}}
🕐 Hora: {{3}}
📋 Servicio: {{4}}

¿Tienes dudas? Responde a este mensaje.
```

**Variables:**
- {{1}} = Nombre del cliente
- {{2}} = Fecha (ej. 15/03/2025)
- {{3}} = Hora (ej. 10:00)
- {{4}} = Motivo o tipo de servicio

Clic en **"Enviar para aprobación"**. La revisión suele tardar de 15 minutos a 24 horas.

### Paso 4.3: Plantilla "Orden de compra al proveedor"

- **Nombre:** `orden_compra_proveedor`
- **Categoría:** Utility
- **Idioma:** Spanish

**Body:**
```
Hola {{1}}, te enviamos una nueva orden de compra.

📋 Número: {{2}}
💰 Total estimado: ${{3}}

Revisa tu correo electrónico para ver el detalle completo.
```

- {{1}} = Nombre del proveedor
- {{2}} = Número de orden (ej. OC-20250315-0001)
- {{3}} = Total

Envíala para aprobación igual que la anterior.

---

## Fase 5: Formato del número de destino

Los números deben estar en formato **E.164**:

- México: `+52` + 10 dígitos (celular: 10 dígitos que empiezan en 1)
- Ejemplo: `5512345678` → `+5215512345678`
- Ejemplo: `(55) 1234-5678` → `+5215512345678`

---

## Fase 6: Enviar mensaje por API

### Endpoint

```
POST https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages
```

### Headers

```
Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}
Content-Type: application/json
```

### Body (plantilla de texto)

```json
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "5215512345678",
  "type": "template",
  "template": {
    "name": "confirmacion_cita",
    "language": {
      "code": "es"
    },
    "components": [
      {
        "type": "body",
        "parameters": [
          {"type": "text", "text": "Juan Pérez"},
          {"type": "text", "text": "15/03/2025"},
          {"type": "text", "text": "10:00"},
          {"type": "text", "text": "Cambio de aceite"}
        ]
      }
    ]
  }
}
```

**Nota:** `to` va sin el `+`, solo dígitos (ej. `5215512345678`).

### Ejemplo con curl

```bash
curl -X POST "https://graph.facebook.com/v18.0/TU_PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "5215512345678",
    "type": "template",
    "template": {
      "name": "confirmacion_cita",
      "language": {"code": "es"},
      "components": [{
        "type": "body",
        "parameters": [
          {"type": "text", "text": "Juan Pérez"},
          {"type": "text", "text": "15/03/2025"},
          {"type": "text", "text": "10:00"},
          {"type": "text", "text": "Cambio de aceite"}
        ]
      }]
    }
  }'
```

---

## Fase 7: Webhooks (solo si quieres recibir respuestas)

Para leer mensajes entrantes (respuestas del cliente) necesitas un webhook:

1. En **developers.facebook.com** → Tu app → **WhatsApp** → **Configuration**
2. **Callback URL:** `https://tu-dominio.com/api/webhooks/whatsapp`
3. **Verify Token:** una cadena secreta que tú eliges (ej. `medina_verify_2025`)
4. WhatsApp hará un GET para verificar; tu endpoint debe devolver `hub.challenge`
5. Suscríbete a: **messages**, **message_template_status_update**

**En desarrollo:** usa [ngrok](https://ngrok.com) para exponer tu localhost.

---

## Checklist final antes de implementar código

- [ ] App creada en Meta for Developers
- [ ] Producto WhatsApp agregado
- [ ] Número de teléfono verificado (tienes Phone Number ID)
- [ ] Token de acceso (temporal o permanente) obtenido
- [ ] Plantilla `confirmacion_cita` creada y **aprobada**
- [ ] Plantilla `orden_compra_proveedor` creada y **aprobada**
- [ ] Variables en .env o Railway:
  - `WHATSAPP_ACCESS_TOKEN`
  - `WHATSAPP_PHONE_NUMBER_ID`

---

## Siguiente paso: implementación en el código

Cuando tengas lo anterior listo:

1. Crear `app/services/whatsapp_service.py`
2. Integrar en `crear_cita` (enviar plantilla de confirmación al cliente)
3. Integrar en `enviar_orden` (enviar plantilla de orden al proveedor)

Avísame cuando hayas completado las fases 1–4 y las plantillas estén aprobadas para continuar con el código.
