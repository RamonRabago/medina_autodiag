# Plan: Limpieza de scripts legacy (punto 16 auditoría)

## Estado: Completado

## Scripts eliminados (obsoletos)

Migraciones y creación de tablas ya cubiertas por Alembic o ejecutadas una sola vez:

| Script | Razón |
|--------|-------|
| `crear_tabla_*.py` | CREATE TABLE → Alembic maneja el esquema |
| `crear_tablas_orden_compra.py` | Igual |
| `crear_estantes_niveles_filas.py` | Igual |
| `agregar_*.py` | ALTER TABLE → migraciones Alembic |
| `agregar_*.sql` | SQL manual → Alembic |
| `fix_*.py`, `fix_*.sql` | Correcciones puntuales ya aplicadas |
| `migrar_*.py` | Migraciones de datos ya ejecutadas |
| `ejecutar_migracion_motivo.py` | Wrapper de migración obsoleto |
| `limpiar_ordenes_compra*.py` | Limpieza puntual |
| `sincronizar_ordenes_compra_schema.py` | Schema sync manual obsoleto |
| `verificar_tabla_pagos_orden_compra.py` | Verificación puntual |
| `agregar_descripcion_auditoria.py` | Columna en `j0k1l2m3n4o5_add_auditoria` |
| `test_bugs_criticos_*.py`, `test_cancelar_*.py`, `test_venta_manual_stock.py` | Tests puntuales ya cubiertos por pytest |
| `buscar_venta_con_repuestos.py` | Diagnóstico puntual |
| `limpiar_tablas.py` | Peligroso, no documentado como necesario |

## Scripts conservados

| Script | Uso |
|--------|-----|
| `auditar_dependencias.py` | Auditoría de seguridad (pip-audit, npm audit) |
| `ejecutar_todas_pruebas.py` | Ejecuta pytest + scripts de verificación |
| `start.sh` | Arranque en Dockerfile |
| `export_openapi.py` | Exporta schema OpenAPI (Makefile) |
| `test_graph_email.py` | Prueba Graph API (GUIA_GRAPH_API_EMAIL.md) |
| `test_smtp.py` | Prueba SMTP |
| `test_modulos_recientes.py` | Usado por ejecutar_todas_pruebas |
| `test_cuentas_por_pagar.py` | Usado por ejecutar_todas_pruebas |
| `test_reporte_utilidad.py` | Usado por ejecutar_todas_pruebas |
| `diagnostico_base_datos.py` | Diagnóstico de BD |
| `diagnostico_ordenes_compra.py` | Diagnóstico de órdenes compra |
| `corregir_usuario.py` | Recuperación de usuario admin |
| `liberar_codigos_repuestos_eliminados.py` | Admin: liberar códigos |
| `reactivar_repuestos_eliminados.py` | Admin: reactivar repuestos |
| `eliminar_repuestos_pdte_editar.py` | Admin: limpieza |

## Actualizaciones necesarias

- `diagnostico_ordenes_compra.py`: referenciaba `sincronizar_ordenes_compra_schema.py` (eliminado) → actualizar mensaje.
- `verificar_tabla_pagos_orden_compra.py`: eliminado; ya no referenciar desde otros scripts.
