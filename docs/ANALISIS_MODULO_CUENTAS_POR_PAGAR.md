# Análisis del Módulo Cuentas por Pagar – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** OC (ordenes_compra), cuentas manuales (cuentas_pagar_manuales), exportaciones, frontend CuentasPorPagar.jsx, integración Dashboard.

---

## 1. Resumen ejecutivo

El módulo de Cuentas por Pagar combina:
- **Órdenes de compra (OC):** Saldo pendiente de OC recibidas, registro de pagos, aging por antigüedad
- **Cuentas manuales:** Facturas, renta, servicios sin OC; crear cuenta, registrar pagos, cancelar
- **Dashboard:** Total saldo OC + manuales
- **Exportaciones:** Excel para ambos tipos

---

## 2. Errores detectados

### E1. Filtro redundante en listar_cuentas_por_pagar

**Archivo:** `app/routers/ordenes_compra.py` — `listar_cuentas_por_pagar`, líneas 356-361

```python
query = db.query(OrdenCompra).filter(
    OrdenCompra.estado.in_([RECIBIDA, RECIBIDA_PARCIAL]),
    OrdenCompra.estado != EstadoOrdenCompra.CANCELADA,  # Redundante
)
```

**Impacto:** Si el estado está en `[RECIBIDA, RECIBIDA_PARCIAL]`, nunca puede ser `CANCELADA`.

**Recomendación:** Eliminar la condición `!= CANCELADA`.

---

### E2. Frontend: cargar sin useCallback

**Archivo:** `frontend/src/pages/CuentasPorPagar.jsx`

**Situación:** `cargar` es una función async definida en el componente. El `useEffect` depende de filtros pero no incluye `cargar` en las dependencias (para evitar loops). Patrón inconsistente con Caja, Asistencia, Vacaciones, etc.

**Recomendación:** Usar `useCallback` para `cargar` con las dependencias correctas.

---

### E3. Ref. en historial manual: typo "Ref: $"

**Archivo:** `frontend/src/pages/CuentasPorPagar.jsx`, línea 413

```jsx
Ref: ${historialCuenta.referencia_factura}
```

**Situación:** Muestra literal "Ref: $" + valor. El `$` antes de la interpolación sugiere monto en vez de referencia. Debería ser "Ref: " + valor (sin $ extra).

**Recomendación:** Cambiar a `Ref: ${historialCuenta.referencia_factura}` (ya está así) — el $ interior es parte de template literal. Revisar: ¿es "Ref: $ABC123" o "Ref: ABC123"? Si referencia_factura es "FAC-001", se mostraría "Ref: $FAC-001" porque el $ está fuera de las llaves. Verificar: `Ref: ${historialCuenta.referencia_factura}` → "Ref: FAC-001". El $ está DENTRO del string como carácter literal antes de {}. No, en `Ref: ${historialCuenta.referencia_factura}` el $ es el inicio del template placeholder. So "Ref: " + contenido. Si referencia es "FAC-001", output is "Ref: FAC-001". Good. So actually there's no bug - the $ in ${} is template syntax. Let me look again...

"Ref: ${historialCuenta.referencia_factura}" - the $ is template literal syntax for ${}, so we get "Ref: " + historialCuenta.referencia_factura. If referencia_factura is "FAC-001", we get "Ref: FAC-001". The $ is not displayed. So no bug. I'll remove E3.

Actually wait - "Ref: $ABC" - could the user have meant that we're showing "Ref: $" + ref? In template literals ${var} substitutes the variable. So "Ref: ${historialCuenta.referencia_factura}" = "Ref: " + value. Good. Skip E3 or verify - maybe the issue is something else. I'll skip E3.

---

## 3. Mejoras propuestas (no aplicadas en este ciclo)

### M1. Paginación en listar_cuentas_por_pagar

**Situación:** Carga todas las OC con saldo y filtra/ordena en memoria. Con muchos registros puede afectar rendimiento.

**Propuesta:** Límite configurable o paginación.

---

### M2. joinedload en cuentas_pagar_manuales

**Archivo:** `app/routers/cuentas_pagar_manuales.py` — `listar_cuentas`

**Situación:** Se accede a `c.pagos` y `c.proveedor` (vía `_nombre_acreedor`) por cada cuenta, causando N+1 queries.

**Propuesta:** `options(joinedload(CuentaPagarManual.pagos), joinedload(CuentaPagarManual.proveedor))`.

---

### M3. Rol seguro en endpoints

**Situación:** Los routers usan `require_roles("ADMIN", "CAJA")`; no hay comparación directa de rol. No aplica E1 de Caja.

---

## 4. Resumen de correcciones a aplicar

| ID | Tipo | Descripción |
|----|------|-------------|
| E1 | Error | Eliminar filtro redundante `!= CANCELADA` en listar_cuentas_por_pagar |
| E2 | Mejora | useCallback para cargar en CuentasPorPagar.jsx |
