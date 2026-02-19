# Railway Volumes: Fotos de inventario y comprobantes persistentes

Las fotos de repuestos (inventario) y los **comprobantes de órdenes de compra** (cotizaciones, facturas) se guardan en `uploads/`. Sin un volumen, Railway **borra esos archivos en cada deploy** y verás "Not found" al intentar abrirlos.

**Importante:** Tanto fotos de inventario como comprobantes de OC usan el **mismo volumen**. Montar `/app/uploads` persiste ambos.

---

## Ruta usada por la app

| Componente | Ruta absoluta (en container) |
|------------|------------------------------|
| Raíz uploads | `/app/uploads` |
| Fotos repuestos (inventario) | `/app/uploads/repuestos/` |
| Comprobantes (OC, cotizaciones, movimientos) | `/app/uploads/comprobantes/` |

La app escribe en `/app/uploads/...` y sirve archivos desde ahí vía la ruta `GET /uploads/{path}` en `main.py`.

---

## Pasos en Railway (plan Hobby $5)

1. **Railway** → tu proyecto → servicio **web**
2. **Variables** (o pestaña **Storage** si aparece)
3. **Volumes** → **Add Volume** (o **New Volume**)
4. **Mount Path**: `uploads` (Railway monta en la raíz del workdir) **o** usa la ruta absoluta que indique la UI
5. Guardar
6. **Redeploy** del servicio

### Ruta exacta de montaje

- En nuestro Dockerfile: `WORKDIR /app`
- La app escribe en `uploads/` (relativo a la raíz) → `/app/uploads`
- **Mount Path**: **`/app/uploads`** (ruta absoluta en el contenedor)

En Railway: al crear el volumen, en "Mount Path" escribe exactamente: `/app/uploads`

---

## Verificación

Tras el redeploy:

1. Crear o editar un repuesto y subir una foto
2. Comprobar que se muestra en el inventario
3. Hacer un **redeploy** o **Restart**
4. Verificar que la foto sigue visible

---

## Nota: Archivos subidos antes del volumen

Las fotos y comprobantes subidos **antes** de montar el volumen **no se recuperan**. Las URL siguen en la base de datos pero los archivos ya no existen. Tendrás que volver a subir desde:
- Inventario: formulario de cada repuesto
- Órdenes de compra: modal de detalle → "Adjuntar comprobante"

---

## Síntoma: "Not found" al ver comprobante o foto

Si al hacer clic en "Ver archivo (cotización/comprobante)" o en una foto de repuesto aparece `{"detail":"Not found"}`:

1. **Verifica** que el volumen existe en Railway (Storage → Volumes)
2. **Mount path** debe ser exactamente `/app/uploads`
3. **Redeploy** tras crear el volumen
4. Los archivos subidos **antes** del volumen se perdieron; vuelve a subirlos

---

## Auditoría: todos los módulos que suben fotos/documentos

| Módulo | Endpoint | Directorio | Campo en BD |
|--------|----------|------------|-------------|
| Inventario (foto repuesto) | `POST /repuestos/upload-imagen` | `uploads/repuestos/` | `repuestos.imagen_url` |
| Inventario (comprobante repuesto) | `POST /repuestos/upload-comprobante` | `uploads/comprobantes/` | `repuestos.comprobante_url` |
| Entrada inventario (comprobante) | `POST /inventario/movimientos/upload-comprobante` | `uploads/comprobantes/` | `movimientos_inventario.imagen_comprobante_url` |
| Órdenes de compra (cotización/comprobante) | `POST /inventario/movimientos/upload-comprobante` | `uploads/comprobantes/` | `ordenes_compra.comprobante_url` |
| Órdenes de compra (evidencia cancelación) | `POST /inventario/movimientos/upload-comprobante` | `uploads/comprobantes/` | `ordenes_compra.evidencia_cancelacion_url` |

**Entrada masiva** (Excel/CSV): No guarda archivos en disco; procesa en memoria. No requiere volumen.

**Nuevos módulos**: Para subir fotos o documentos, usar `uploads/repuestos/` (solo imágenes) o `uploads/comprobantes/` (imágenes y PDF). Luego agregar el subdir en `safe_uploads.ALLOWED_SUBDIRS` si se crea uno nuevo.

---

## Referencias

- [Railway Volumes](https://docs.railway.app/guides/volumes)
- `app/main.py` línea 217: `uploads_path = _project_root / "uploads"`
- `app/routers/repuestos.py` línea 48: `UPLOADS_DIR = .../uploads/repuestos`
