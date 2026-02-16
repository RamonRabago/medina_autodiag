# Flujo: Cotización → Aprobación → Compra

## Resumen

Flujo formal para órdenes de trabajo que requieren cotización al cliente y compra de repuestos antes de iniciar.

## Pasos del flujo

### 1. Crear orden de trabajo
- Se registra cliente, vehículo, diagnóstico
- Se agregan servicios y repuestos necesarios
- Si requiere aprobación del cliente: `requiere_autorizacion = true`

### 2. Documento formal de cotización
- **Cotización PDF**: Botón "Cotización PDF" genera el documento formal para enviar al cliente
- El PDF incluye: logo, cliente, vehículo, servicios, refacciones, totales, vigencia
- Ubicación: DetalleOrdenTrabajo → "Cotización PDF"

### 3. Enviar cotización al cliente
- Descargar el PDF y enviarlo al cliente (WhatsApp, email, etc.)
- **Marcar cotización enviada**: Botón "Marcar cotización enviada" →
  - Si `requiere_autorizacion`: estado pasa a `ESPERANDO_AUTORIZACION`
  - Si no: estado pasa a `COTIZADA`

### 4. Aprobación del cliente
- Si `requiere_autorizacion`: el cliente autoriza → botón "Autorizar"
- Estado puede pasar de `ESPERANDO_AUTORIZACION` a `PENDIENTE`
- Si no requiere autorización: "Marcar cotización enviada" es suficiente para considerar lista

### 5. Generar orden de compra (OC)
- **Generar OC desde esta orden**: Botón que crea una OC con los repuestos de la OT
- Solo repuestos que el taller debe comprar (excluye `cliente_provee`)
- Modal: seleccionar proveedor → se crea OC prellenada
- Endpoint: `POST /api/ordenes-compra/desde-orden-trabajo/{orden_id}`
- La OC se crea en estado BORRADOR; luego autorizar y enviar al proveedor

### 6. Recibir mercancía y continuar
- En Ordenes de compra: recibir mercancía, registrar entrada a inventario
- En la OT: Iniciar trabajo cuando haya stock suficiente

## Estados relevantes

| Estado OT | Significado |
|-----------|-------------|
| PENDIENTE | Creada, pendiente de cotizar/enviar |
| COTIZADA | Cotización enviada al cliente |
| ESPERANDO_AUTORIZACION | Requiere OK del cliente |
| EN_PROCESO | Trabajo iniciado |
| ESPERANDO_REPUESTOS | Falta material (OC enviada, pendiente recibir) |

## Implementado

- [x] PDF cotización formal (logo, diseño naranja)
- [x] Botón "Marcar cotización enviada" → ESPERANDO_AUTORIZACION si requiere_autorizacion, si no COTIZADA
- [x] Botón "Autorizar" (requiere_autorizacion)
- [x] Botón "Generar OC desde esta orden" con modal de proveedor (solo visible si autorizado o no requiere autorización)
- [x] Endpoint `POST /ordenes-compra/desde-orden-trabajo/{orden_id}`
- [x] Vínculo OT ↔ OC: columna `id_orden_trabajo` en ordenes_compra, lista de OCs en DetalleOrdenTrabajo
