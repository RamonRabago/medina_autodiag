# Guía: Implementar mensajes automáticos por WhatsApp

Objetivo: enviar WhatsApp automáticos al **crear una cita** (confirmación al cliente) y al **enviar orden de compra** al proveedor (notificación).

---

## Resumen de lo que tienes hoy

| Dato | Cliente | Proveedor |
|------|---------|-----------|
| Teléfono | ✅ `telefono` | ✅ `telefono` |
| Email | ✅ `email` | ✅ `email` |
| Uso actual | Cotizaciones, contacto | Envío de OC por email |

**Integración actual:** ya envías emails (SMTP / Microsoft Graph) a proveedores cuando se envía una orden de compra.

---

## Paso 0: Opciones para WhatsApp

### Opción A: Meta WhatsApp Cloud API (recomendada)

- API oficial de Meta, integración directa (sin intermediarios).
- Requiere: número de teléfono dedicado, cuenta Meta Business.
- Costo: se cobra por conversación/mensaje.
- Ventaja: estable, escalable, permite plantillas aprobadas.

**Guías:**
- [GUIA_WHATSAPP_META_CLOUD_API.md](./GUIA_WHATSAPP_META_CLOUD_API.md) — pasos generales
- [GUIA_NUMERO_VIRTUAL_TWILIO_META.md](./GUIA_NUMERO_VIRTUAL_TWILIO_META.md) — comprar número virtual en Twilio (México) y vincular a Meta

### Opción B: Servicios tipo “puente” (Twilio, 360dialog, etc.)

- Twilio: uso sencillo, documentación amplia.
- 360dialog: centrado en WhatsApp Business.
- Proceso similar: te registras, conectas tu número y usas la API.

### Opción C: Soluciones sin API

- Servicios que emulan WhatsApp Web (no oficiales, riesgo de bloqueo).
- No recomendado para producción.

**Para Medina Auto-Diag:** usar **Twilio** o **360dialog** es lo más práctico.

---

## Paso 1: Cuenta y configuración en Meta / proveedor

### 1.1 Meta Business Suite

1. Crear cuenta en [business.facebook.com](https://business.facebook.com).
2. Registrar aplicación en [developers.facebook.com](https://developers.facebook.com).
3. Añadir producto “WhatsApp” y usar “WhatsApp Cloud API”.
4. Obtener:
   - **Access Token** (permisos para enviar mensajes).
   - **Phone Number ID** (número de negocio).
   - **WhatsApp Business Account ID**.

### 1.2 Si usas Twilio

1. Cuenta en [twilio.com](https://www.twilio.com).
2. Producto “Messaging” → “Try WhatsApp”.
3. Conectar con tu Meta Business Account.
4. Obtener:
   - **Account SID**
   - **Auth Token**
   - **WhatsApp sender** (ej. `whatsapp:+5215512345678`).

### 1.3 Si usas 360dialog

1. Cuenta en [360dialog.com](https://www.360dialog.com).
2. Conectar número con Meta.
3. Obtener **API key**.

---

## Paso 2: Plantillas de mensajes (templates)

WhatsApp exige plantillas aprobadas para mensajes proactivos (no iniciados por el usuario).

### 2.1 Plantilla “Confirmación de cita”

- **Nombre:** `confirmacion_cita`
- **Idioma:** `es`
- **Componentes:**
  - Header: texto fijo.
  - Body: texto con variables.
  - (Opcional) Botones: enlace a calendario / web.

**Ejemplo de plantilla:**

```
Hola {{1}}, tu cita en Medina Auto-Diag ha sido confirmada.

📅 Fecha: {{2}}
🕐 Hora: {{3}}
📋 Motivo: {{4}}

¿Dudas? Responde este mensaje.
```

Variables: `{{1}}` nombre, `{{2}}` fecha, `{{3}}` hora, `{{4}}` motivo.

### 2.2 Plantilla “Orden de compra al proveedor”

- **Nombre:** `orden_compra_proveedor`
- **Idioma:** `es`

**Ejemplo:**

```
Hola {{1}}, te enviamos una orden de compra.

📋 Número: {{2}}
📦 Total estimado: {{3}}

Revisa tu correo o entra al sistema para ver el detalle.
```

Variables: `{{1}}` nombre, `{{2}}` número de orden, `{{3}}` total.

**Importante:** debes crear y enviar las plantillas en el panel de Meta/Twilio/360dialog para que Meta las apruebe. Solo después podrás usarlas desde la API.

---

## Paso 3: Variables de entorno

En `.env` o en Railway añadirías algo así:

```env
# WhatsApp (Twilio)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+5215512345678

# O si usas Meta directo / 360dialog:
WHATSAPP_ACCESS_TOKEN=xxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=xxxxxxxxxxxxx
```

---

## Paso 4: Estructura del código

### 4.1 Servicio de WhatsApp

```
app/services/whatsapp_service.py
```

- Función para enviar mensaje de plantilla.
- Normalizar teléfono a formato E.164 (`+521234567890`).

### 4.2 Integrar en creación de citas

En `app/routers/citas.py`, después de `db.commit()` en `crear_cita`:

1. Cargar cliente y vehículo.
2. Si cliente tiene `telefono`:
   - Llamar a `whatsapp_service.enviar_confirmacion_cita(...)`.
   - Ejecutar en segundo plano (`threading.Thread` o Celery) para no retrasar la respuesta.

### 4.3 Integrar en envío de orden de compra

En `app/routers/ordenes_compra.py`, en `enviar_orden`:

- Junto al envío de email al proveedor:
  - Si el proveedor tiene `telefono`:
    - Enviar WhatsApp con plantilla `orden_compra_proveedor`.

---

## Paso 5: Normalización de teléfono

Los números deben estar en formato internacional:

- México: `+52` + 10 dígitos (sin el 01).
- Ejemplo: `5512345678` → `+5215512345678`.

En tu código ya tienes validación en `validar_telefono_mexico`. Hay que asegurar que, al enviar por WhatsApp, siempre se mande `+52` + los 10 dígitos.

---

## Paso 6: Configuración (opcional) en la app

Para poder activar/desactivar WhatsApp por entorno:

- Variable de entorno `WHATSAPP_ENABLED=true/false`.
- Si `false`, no enviar WhatsApp; solo seguir con emails y lógica actual.

---

## Orden recomendado de implementación

| Fase | Tarea                                      | Tiempo estimado |
|------|--------------------------------------------|------------------|
| 1    | Crear cuenta Meta/Twilio/360dialog         | 1–2 horas       |
| 2    | Crear y aprobar plantillas                 | 1–2 días        |
| 3    | Obtener credenciales y configurar .env      | ~30 min          |
| 4    | Crear `whatsapp_service.py`                | 1–2 horas       |
| 5    | Integrar en creación de citas              | ~1 hora          |
| 6    | Integrar en envío de orden de compra       | ~1 hora          |
| 7    | Pruebas con números de prueba              | 1–2 horas       |

---

## Costos aproximados (referencia)

- Meta: cobro por conversación/mensaje (según país).
- Twilio: cobro por mensaje enviado (depende del país y proveedor).
- México: suele ser de alrededor de 0.05–0.10 USD por mensaje (sujeto a cambios).

---

## Próximo paso

1. **Define el proveedor:** Twilio, 360dialog u otro.
2. **Registra la cuenta y vincula el número de negocio.**
3. **Crea y envía las plantillas a aprobación.**
4. Cuando tengas las credenciales y las plantillas aprobadas, se puede continuar con la implementación del código.

Si me dices si vas a usar Twilio o 360dialog, puedo proponerte el esquema exacto de `whatsapp_service.py` y los cambios puntuales en `citas.py` y `ordenes_compra.py`.
