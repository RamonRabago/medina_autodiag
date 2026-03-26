# Guía: Comprar número virtual en Twilio (México) y vincularlo a Meta WhatsApp API

Esta guía te permite obtener un número virtual para usar con la Meta WhatsApp Cloud API, manteniendo tu número personal en WhatsApp intacto.

---

## Resumen de pasos

1. Crear cuenta Twilio y verificar pago
2. Comprar número de México
3. Configurar recepción de SMS (para el código de verificación de Meta)
4. Añadir el número en Meta for Developers
5. Verificar con el código recibido
6. Anotar credenciales para Autodiag

**Tiempo aproximado:** 20–30 minutos  
**Costo aproximado:** ~USD 1–2/mes (número) + consumo de Meta por conversación

---

## Fase 1: Cuenta Twilio

### Paso 1.1: Registro

1. Entra a **[twilio.com/try-twilio](https://www.twilio.com/try-twilio)**
2. Completa: correo, contraseña, nombre
3. Verifica tu correo si te lo piden
4. Verifica tu **teléfono personal** (Twilio envía un código)

### Paso 1.2: Cuenta de pago (obligatorio para comprar números)

Las cuentas de prueba (trial) tienen limitaciones. Para comprar un número de México necesitas **añadir método de pago**:

1. En la consola: **[console.twilio.com](https://console.twilio.com)**
2. Menú lateral → **Billing** (Facturación) → **Upgrade** (Actualizar)
3. Añade tarjeta de crédito o débito
4. Twilio suele dar crédito de bienvenida (ej. USD 15) al verificar

---

## Fase 2: Comprar número de México

### Paso 2.1: Ir a la búsqueda de números

1. Consola Twilio → menú lateral
2. **Phone Numbers** → **Manage** → **Buy a number**
3. O directo: **[console.twilio.com/us1/develop/phone-numbers/manage/search](https://console.twilio.com/us1/develop/phone-numbers/manage/search)**

### Paso 2.2: Filtrar por México

1. **Country:** selecciona **Mexico (MX)**
2. **Capabilities:** marca al menos **SMS** (para recibir el código de Meta)
3. Si quieres verificación por llamada: marca también **Voice**
4. **Number:** opcional, busca por ciudad (ej. 55 CDMX, 33 Guadalajara, 81 Monterrey)
5. Clic en **Search** (Buscar)

### Paso 2.3: Comprar

1. Elige un número de la lista (los de 10 dígitos con código de área son locales)
2. Clic en **Buy** (Comprar)
3. Confirma el precio (aprox. USD 1–2/mes)
4. El número queda en **Phone Numbers → Manage → Active numbers**

### Paso 2.4: Anotar el número

- Formato para Meta: `5215512345678` (52 = México, 10 dígitos)
- Ejemplo si compraste `55 1234 5678`: `5215512345678`

---

## Fase 3: Configurar recepción de SMS (para el código de Meta)

Meta enviará un SMS con el código de verificación. Twilio debe poder mostrártelo. La forma más simple es usar **webhook.site**:

### Paso 3.1: Obtener URL temporal

1. Abre **[webhook.site](https://webhook.site)** en otra pestaña
2. Te asignan una URL única, ej. `https://webhook.site/abc123-xyz`
3. **Copia esa URL** (la necesitas en el siguiente paso)
4. Mantén la pestaña abierta para ver los mensajes entrantes

### Paso 3.2: Configurar webhook en Twilio

1. En Twilio: **Phone Numbers** → **Manage** → **Active numbers**
2. Clic en el número que compraste
3. Baja a **Messaging configuration**
4. En **"A MESSAGE COMES IN"** (Cuando llega un mensaje):
   - Elige **Webhook**
   - Pega la URL de webhook.site (ej. `https://webhook.site/abc123-xyz`)
   - Método: **HTTP POST**
5. **Save** (Guardar)

Cuando Meta envíe el SMS, verás el contenido en webhook.site (incluido el código).

> **Alternativa con llamada de voz:** Si prefieres verificación por llamada en lugar de SMS, Meta dicta el código por teléfono. En Twilio, en **Voice configuration**, configura un webhook o usa un servicio que grabe/transcriba. Para la mayoría, SMS es más sencillo.

---

## Fase 4: Añadir el número en Meta

### Paso 4.1: Ir a WhatsApp API Setup

1. Entra a **[developers.facebook.com](https://developers.facebook.com)**
2. Abre tu app (ej. Medina Auto-Diag o conector_w)
3. Menú lateral → **WhatsApp** → **API Setup**

### Paso 4.2: Agregar número

1. En **Phone numbers**, clic en **Add phone number**
2. Completa:
   - **Business phone number:** en formato E.164 sin `+`  
     Ejemplo: `5215512345678`
   - **Display name:** `Medina Auto-Diag` (o nombre del negocio)
   - **Timezone:** `America/Matamoros` o `America/Mexico_City`
   - **About:** Breve descripción (ej. "Taller de diagnóstico automotriz")
   - **Category:** `Automotive` o `Other`
3. **Next** (Siguiente)

### Paso 4.3: Verificación

1. Meta pregunta cómo verificar: **SMS** o **Voice call**
2. Elige **SMS**
3. Meta envía el código al número de Twilio
4. Twilio recibe el SMS y lo reenvía a webhook.site
5. En webhook.site, busca el POST más reciente y revisa el **body**; ahí estará el código (suele ser un número de 6 dígitos)
6. Ingresa el código en Meta y confirma
7. Si todo va bien, Meta mostrará **Phone Number ID** y **WhatsApp ID**

### Paso 4.4: Si el código no llega

- Revisa que el webhook en Twilio esté en **HTTP POST** y la URL sea correcta
- Prueba **Voice call** si SMS falla
- Comprueba que el número de Twilio tenga capacidad **SMS** activa
- Espera 1–2 minutos; a veces hay retraso

---

## Fase 5: Anotar credenciales para Autodiag

Cuando el número esté vinculado a Meta, en **API Setup** verás:

| Variable | Dónde obtenerla |
|----------|------------------|
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp → API Setup → Phone numbers → tu número → Phone Number ID |
| `WHATSAPP_ACCESS_TOKEN` | API Setup → Temporary access token (pruebas) o System User token (producción) |

Añádelas a tu `.env`:

```env
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxx...
WHATSAPP_PHONE_NUMBER_ID=123456789012345
```

---

## Desactivar webhook temporal (opcional)

Tras verificar en Meta, puedes quitar el webhook de webhook.site:

1. Twilio → tu número → **Messaging configuration**
2. En **"A MESSAGE COMES IN"** → cambia a **"Do not configure"** o deja vacío si solo usas Meta para enviar mensajes
3. O configura tu propio webhook de Autodiag cuando implementes recepción de mensajes

---

## Checklist final

- [ ] Cuenta Twilio creada y con método de pago
- [ ] Número de México comprado (SMS habilitado)
- [ ] Webhook temporal en webhook.site configurado en Twilio
- [ ] Número añadido en Meta for Developers
- [ ] Verificación completada (código recibido e ingresado)
- [ ] `PHONE_NUMBER_ID` y `ACCESS_TOKEN` anotados en .env
- [ ] Webhook temporal eliminado o reemplazado (cuando corresponda)

---

## Próximos pasos

1. Crear y aprobar plantillas de mensaje en Meta (`confirmacion_cita`, `orden_compra_proveedor`)
2. Implementar `whatsapp_service.py` en Autodiag
3. Integrar en flujo de citas y envío de órdenes de compra

Consulta `GUIA_WHATSAPP_META_CLOUD_API.md` para detalles de plantillas, tokens permanentes y envío de mensajes.
