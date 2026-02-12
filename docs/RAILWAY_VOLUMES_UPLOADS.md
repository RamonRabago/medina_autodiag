# Railway Volumes: Fotos de inventario persistentes

Las fotos de repuestos y comprobantes se guardan en `uploads/`. Sin un volumen, Railway borra esos archivos en cada deploy. Con un volumen montado, **persisten**.

---

## Ruta usada por la app

| Componente | Ruta absoluta (en container) |
|------------|------------------------------|
| Raíz uploads | `/app/uploads` |
| Fotos repuestos | `/app/uploads/repuestos/` |
| Comprobantes | `/app/uploads/comprobantes/` |

La app escribe en `/app/uploads/...` y sirve archivos desde ahí vía `app.mount("/uploads", ...)` en `main.py`.

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

## Nota: Fotos antiguas

Las fotos subidas antes de montar el volumen **no se recuperan**. Las URL siguen en la base de datos pero los archivos ya no existen. Tendrás que volver a subir esas fotos desde el formulario de cada repuesto.

---

## Referencias

- [Railway Volumes](https://docs.railway.app/guides/volumes)
- `app/main.py` línea 217: `uploads_path = _project_root / "uploads"`
- `app/routers/repuestos.py` línea 48: `UPLOADS_DIR = .../uploads/repuestos`
