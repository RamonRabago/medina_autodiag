# Plan: Integración WhatsApp con API Directa de Meta

**Medina AutoDiag** — Envío de mensajes a proveedores y clientes vía WhatsApp Business Cloud API.

**Fecha:** 2025-02-17  
**Enfoque:** API directa de Meta (sin BSP/intermediarios)

---

## Resumen ejecutivo

Integrar WhatsApp Business Cloud API para:
1. **Proveedores:** Enviar orden de compra por WhatsApp (además de email)
2. **Clientes:** Enviar cotización en PDF por WhatsApp
3. **Clientes:** Notificar cuando el vehículo está listo (estado COMPLETADA)

---

## Fase 0: Prerequisitos y preparación

### 0.1 Cuenta Meta Business
- [ ] Crear cuenta en [business.facebook.com](https://business.facebook.com)
- [ ] Crear **App de negocio** en [developers.facebook.com](https://developers.facebook.com)
- [ ] Tipo de app: "Negocio"

### 0.2 Producto WhatsApp
- [ ] En la app, agregar producto **WhatsApp** → **Empezar**
- [ ] Obtener **número de teléfono de prueba** (gratis, hasta 5 destinatarios) para desarrollo
- [ ] Cuando vayas a producción: verificar número propio (migrar o nuevo)

### 0.3 Credenciales
- [ ] **App ID** (Application ID)
- [ ] **App Secret** (en Configuración → Básica)
- [ ] **Token de acceso** temporal (WhatsApp → API Setup); para producción se usará token permanente
- [ ] **ID del número de teléfono** (Phone Number ID) y **ID de la cuenta Business** (WhatsApp Business Account ID)

### 0.4 Referencia
- Documentación: [developers.facebook.com/docs/whatsapp/cloud-api](https://developers.facebook.com/docs/whatsapp/cloud-api)
- Precios: [developers.facebook.com/docs/whatsapp/pricing](https://developers.facebook.com/docs/whatsapp/pricing)

---

## Fase 1: Preparación de plantillas (Templates)

### 1.1 Plantillas obligatorias (mensajes iniciados por negocio)

Los mensajes **outbound** (cuando tú inicias) requieren plantillas preaprobadas por Meta.

| Nombre interno | Uso | Variables | Ejemplo de texto |
|----------------|-----|-----------|-------------------|
| `orden_compra_proveedor` | Orden de compra al proveedor | {{1}} nombre, {{2}} número orden, {{3}} resumen | "Estimado {{1}}, su orden {{2}} está lista. Detalle: {{3}}" |
| `cotizacion_lista_cliente` | Cotización lista para cliente | {{1}} nombre, {{2}} vehiculo, {{3}} total | "Hola {{1}}, su cotización para {{2}} está lista. Total: ${{3}}. Puede recogerla en el taller." |
| `vehiculo_listo_cliente` | Vehículo terminado | {{1}} nombre, {{2}} vehiculo, {{3}} numero_orden | "Hola {{1}}, su vehículo {{2}} ya está listo. Orden {{3}}. Puede pasar a recogerlo." |

### 1.2 Crear plantillas en Meta
- [ ] WhatsApp Manager → Plantillas de mensaje → Crear plantilla
- [ ] Escribir texto en español, respetar límites de caracteres
- [ ] Enviar a revisión (Meta suele responder en 24–48 h)
- [ ] Guardar **nombre** de cada plantilla aprobada (ej. `orden_compra_proveedor`)

### 1.3 Nota sobre archivos (PDF)
- Para cotización con PDF: usar endpoint de **documentos**
- Plantilla puede incluir botón "Ver documento" o enviarse como mensaje de documento después
- Meta permite adjuntar hasta ~100 MB por mensaje

---

## Fase 2: Variables de entorno y configuración

### 2.1 Nuevas variables (.env)

```env
# WhatsApp Business Cloud API
WHATSAPP_ENABLED=false
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_API_VERSION=v21.0
```

### 2.2 En producción (token permanente)
- [ ] Generar token de sistema (System User) con permisos `whatsapp_business_management`, `whatsapp_business_messaging`
- [ ] O usar Webhook + renovación automática de token (más complejo)

### 2.3 Actualizar `app/config.py`
- [ ] Añadir atributos para WhatsApp
- [ ] Validar que `WHATSAPP_ENABLED` sea bool
- [ ] Si está deshabilitado, el sistema no intenta enviar (fallback silencioso o solo email)

---

## Fase 3: Servicio de WhatsApp (`whatsapp_service.py`)

### 3.1 Estructura del servicio

```
app/services/whatsapp_service.py
├── _esta_configurado() -> bool
├── _normalizar_telefono(telefono: str) -> str | None   # Formato 5215512345678
├── enviar_texto_template(nombre_template, numero_destino, variables) -> (ok, error)
├── enviar_documento(numero_destino, url_archivo_o_bytes, nombre_archivo, caption) -> (ok, error)
├── enviar_orden_compra_proveedor(proveedor, orden, lineas) -> (ok, error)
├── enviar_cotizacion_cliente(cliente, orden, pdf_bytes) -> (ok, error)
└── enviar_vehiculo_listo_cliente(cliente, orden, vehiculo) -> (ok, error)
```

### 3.2 Detalles técnicos
- [ ] Llamar a `https://graph.facebook.com/{api_version}/{phone_number_id}/messages`
- [ ] Método POST, header `Authorization: Bearer {token}`
- [ ] Body JSON según [Send Messages](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages)
- [ ] Para template: `type: "template"`, `template: { name, language, components }`
- [ ] Para documento: `type: "document"`, subir a URL pública o usar [Media Upload](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media) primero
- [ ] Manejo de errores: 4xx/5xx, rate limit; log + retornar mensaje legible

### 3.3 Dependencias
- [ ] `requests` o `httpx` (ya usas uno para HTTP); no hace falta SDK especial para Cloud API básica

---

## Fase 4: Validación y normalización de teléfonos

### 4.1 Formato exigido por WhatsApp
- Código país + número sin espacios ni guiones
- México: `52` + 10 dígitos (ej. `5215512345678`)
- Validar que Cliente y Proveedor tengan `telefono` en formato utilizable

### 4.2 Utilidad
- [ ] Crear `app/utils/telefono_whatsapp.py` o extender `validators.py`
- [ ] Función: `normalizar_para_whatsapp(telefono: str) -> str | None`
- [ ] Asumir México si el número tiene 10 dígitos; permitir override de código país
- [ ] Retornar `None` si no es válido

---

## Fase 5: Integración en órdenes de compra

### 5.1 Endpoint `POST /ordenes-compra/{id}/enviar`
- [ ] Mantener envío por email como está
- [ ] Si `WHATSAPP_ENABLED` y proveedor tiene teléfono válido:
  - [ ] Llamar a `enviar_orden_compra_proveedor()`
  - [ ] Incluir en respuesta: `whatsapp_enviado: bool`, `mensaje_whatsapp: str | None`
- [ ] Si no tiene teléfono o WhatsApp falla: no bloquear; el email sigue siendo el principal
- [ ] Log de auditoría opcional: "WhatsApp enviado a proveedor X"

### 5.2 Contenido del mensaje (plantilla)
- Variables: nombre del proveedor, número de orden, resumen de líneas (ej. "3 repuestos: pastillas, aceite, filtro")
- Mensaje breve; el detalle completo puede pedirse por email si hace falta

---

## Fase 6: Integración en cotizaciones (órdenes de trabajo)

### 6.1 Momento del disparo
- Al marcar "Cotización enviada" (`marcar_cotizacion_enviada`)
- O nuevo botón "Enviar cotización por WhatsApp" que haga ambas cosas

### 6.2 Flujo
- [ ] Verificar que cliente tenga teléfono
- [ ] Generar PDF de cotización (ya existe en `cotizacion.py`)
- [ ] Subir PDF a URL temporal o usar Media API de Meta
- [ ] Enviar plantilla `cotizacion_lista_cliente` + documento PDF
- [ ] Actualizar `fecha_cotizacion_enviada` (y usuario) como ya se hace
- [ ] Respuesta al frontend: `whatsapp_enviado: bool`

### 6.3 Alternativa sin PDF en el primer mensaje
- Solo texto con total y número de orden; el cliente puede pedir el PDF por otro medio
- Simplifica implementación; el PDF se podría enviar después si el cliente responde

---

## Fase 7: Integración al finalizar orden (vehículo listo)

### 7.1 Momento del disparo
- En `finalizar` de `ordenes_trabajo/acciones.py`, cuando `estado` pasa a `COMPLETADA`

### 7.2 Flujo
- [ ] Después de actualizar orden (estado, fecha_finalizacion, etc.)
- [ ] Obtener cliente y vehículo de la orden
- [ ] Si cliente tiene teléfono y `WHATSAPP_ENABLED`:
  - [ ] Llamar a `enviar_vehiculo_listo_cliente()`
  - [ ] Plantilla `vehiculo_listo_cliente` con nombre, vehículo, número de orden
- [ ] No bloquear el flujo de finalización si WhatsApp falla; solo log
- [ ] Opcional: campo `whatsapp_vehiculo_listo_enviado` en orden para no reenviar

### 7.3 Consideración
- Envío **asíncrono** recomendado (tarea en background) para no retardar la respuesta al técnico

---

## Fase 8: Cola de mensajes (opcional, recomendable)

### 8.1 Motivación
- Evitar bloquear la UI o el endpoint
- Reintentos automáticos si la API de Meta falla
- Mejor trazabilidad

### 8.2 Opciones
- **Opción A:** Tarea en thread/background con `threading` o `asyncio` (simple, sin dependencias extra)
- **Opción B:** Redis + RQ (Redis Queue) — requiere Redis
- **Opción C:** Celery — más completo, requiere broker (Redis/RabbitMQ)

### 8.3 Decisión
- Si volumen bajo (<100 mensajes/día): Opción A puede bastar
- Si se prevé crecimiento o varios tipos de notificaciones: Opción B o C

### 8.4 Implementación (si se usa cola)
- [ ] Definir tarea `enviar_whatsapp_orden_proveedor`, etc.
- [ ] Encolar desde el endpoint; worker procesa en segundo plano
- [ ] Reintentos (ej. 3 intentos con backoff)
- [ ] Tabla o log de intentos fallidos para revisión manual

---

## Fase 9: Cambios en frontend

### 9.1 Órdenes de compra
- [ ] En vista de detalle/enviar: mostrar si se envió por email y/o WhatsApp
- [ ] Si proveedor no tiene teléfono: mensaje informativo "Agregue teléfono para enviar por WhatsApp"
- [ ] No bloquear el envío si WhatsApp falla; el email es el canal principal

### 9.2 Cotizaciones (DetalleOrdenTrabajo)
- [ ] Botón "Enviar cotización por WhatsApp" junto a "Marcar enviada"
- [ ] Validar teléfono del cliente antes de habilitar
- [ ] Feedback: "Enviado" / "Error: ..."
- [ ] Opcional: checkbox "Enviar también por email" (si implementas envío de cotización por email)

### 9.3 Vehículo listo
- [ ] Al finalizar: mensaje "Se notificó al cliente por WhatsApp" o "No se pudo enviar WhatsApp"
- [ ] Opcional: botón "Reenviar notificación" en órdenes COMPLETADAS

---

## Fase 10: Base de datos (opcional)

### 10.1 Auditoría de envíos
- [ ] Tabla `whatsapp_envios` (opcional):
  - `id`, `tipo` (orden_proveedor, cotizacion, vehiculo_listo), `id_referencia`, `destinatario`, `telefono`, `estado` (enviado, fallido), `error`, `creado_en`

### 10.2 Consentimiento (si aplica)
- [ ] Campo `whatsapp_consent` en Cliente (y opcional en Proveedor)
- [ ] Checkbox al crear/editar: "Acepta recibir notificaciones por WhatsApp"
- [ ] No enviar si consent=false

---

## Fase 11: Pruebas

### 11.1 Entorno de prueba
- [ ] Usar número de prueba de Meta (hasta 5 números de destinatario)
- [ ] Agregar tu número personal y de prueba a la lista
- [ ] Probar los 3 flujos: orden a proveedor, cotización, vehículo listo

### 11.2 Casos a validar
- [ ] Teléfono válido → mensaje llega
- [ ] Teléfono inválido o vacío → no falla, sigue con email si aplica
- [ ] WhatsApp deshabilitado (`WHATSAPP_ENABLED=false`) → no intenta enviar
- [ ] Token expirado o inválido → error controlado, log claro
- [ ] Rate limit de Meta → manejo con reintento o mensaje al usuario

---

## Fase 12: Producción

### 12.1 Antes de lanzar
- [ ] Verificar número de WhatsApp Business (migración o nuevo)
- [ ] Obtener token permanente (System User)
- [ ] Plantillas aprobadas en producción
- [ ] Variables de entorno en Railway/hosting
- [ ] Probar con número real antes de dar acceso a usuarios

### 12.2 Monitoreo
- [ ] Logs de envíos (éxito/fallo)
- [ ] Métricas: mensajes/día por tipo (orden, cotización, vehiculo_listo)
- [ ] Alerta si tasa de fallo > X%

### 12.3 Costos
- [ ] Revisar [calculador de precios de Meta](https://developers.facebook.com/docs/whatsapp/pricing)
- [ ] Mensajes de Utilidad en México: tarifa actual
- [ ] Presupuesto mensual estimado según volumen

---

## Resumen de archivos a crear/modificar

| Archivo | Acción |
|---------|--------|
| `docs/PLAN_WHATSAPP_API_DIRECTA.md` | Este plan |
| `app/config.py` | Añadir vars WhatsApp |
| `app/services/whatsapp_service.py` | **Crear** — envío de mensajes |
| `app/utils/telefono_whatsapp.py` | **Crear** (o en validators) — normalizar teléfono |
| `app/routers/ordenes_compra.py` | Integrar en `enviar_orden` |
| `app/routers/ordenes_trabajo/acciones.py` | Integrar en `finalizar` y/o `marcar_cotizacion_enviada` |
| `app/routers/ordenes_trabajo/cotizacion.py` | Endpoint o lógica para enviar PDF por WhatsApp |
| `frontend/.../OrdenesCompra`, `DetalleOrdenTrabajo` | Botones y feedback de WhatsApp |
| `.env.example` | Documentar variables WhatsApp |

---

## Orden sugerido de implementación

1. **Fase 0** — Cuenta Meta, credenciales, número de prueba  
2. **Fase 1** — Crear y aprobar plantillas  
3. **Fase 2** — Variables de entorno y config  
4. **Fase 3** — Servicio `whatsapp_service.py` (enviar plantilla de texto)  
5. **Fase 4** — Normalización de teléfonos  
6. **Fase 5** — Orden a proveedor (primer flujo funcional)  
7. **Fase 7** — Vehículo listo (más simple que cotización)  
8. **Fase 6** — Cotización con PDF  
9. **Fase 9** — Ajustes en frontend  
10. **Fase 8** — Cola asíncrona (si hace falta)  
11. **Fase 11–12** — Pruebas y producción  

---

## Referencias

- [WhatsApp Cloud API — Get Started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
- [Send Messages](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages)
- [Message Templates](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-template-messages)
- [Media — Upload and send documents](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media)
- [Pricing](https://developers.facebook.com/docs/whatsapp/pricing)
