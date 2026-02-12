# Plan: Cuentas por pagar manuales

**Fecha:** 2025-01  
**Estado:** Implementado

## Objetivo

Permitir registrar facturas sin orden de compra (renta, servicios, luz, etc.) como cuentas por pagar, con seguimiento de saldo y pagos parciales, cumpliendo requisitos contables.

## Qué está implementado

### Backend
- **Modelos:** `CuentaPagarManual`, `PagoCuentaPagarManual`
- **API:** `GET/POST /cuentas-pagar-manuales`, `GET/PUT /cuentas-pagar-manuales/{id}`, `POST /cuentas-pagar-manuales/{id}/pagar`, `POST /cuentas-pagar-manuales/{id}/cancelar`
- **Integración Caja:** Los pagos en efectivo se vinculan al turno activo y afectan el cierre de caja
- **Aging:** Rangos 0-30, 31-60, 61+ días (por fecha vencimiento o registro)
- **Ordenamiento:** Por fecha, saldo, proveedor, antigüedad
- **Exportación:** `GET /exportaciones/cuentas-pagar-manuales`

### Frontend
- **Pestañas:** "Por órdenes de compra" y "Manuales" en `/cuentas-por-pagar`
- **Manuales:** Tabla con concepto, acreedor, ref. factura, total, pagado, saldo, vencimiento, antigüedad
- **Modales:** Nueva cuenta, Registrar pago, Historial de pagos
- **Filtros:** Proveedor, fechas, incluir saldadas
- **Ordenamiento:** Encabezados clicables

### Dashboard
- Total cuentas por pagar = OC + Manuales

## Si la sesión se cierra

1. El código está en el repo; nada se pierde.
2. Para retomar: `git status` para ver cambios pendientes.
3. Para probar: iniciar backend y frontend, ir a Cuentas por pagar → pestaña Manuales.

## Evitar cierres inesperados

- Dividir trabajo en tareas pequeñas y guardar con frecuencia.
- Usar `TODO` en el código para marcar pendientes.
- Mantener este documento actualizado al agregar funcionalidades.
