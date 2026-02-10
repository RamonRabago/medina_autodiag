# Despliegue de MedinaAutoDiag en Railway

Guía paso a paso para publicar la API y el frontend en internet usando Railway.

---

## 1. Requisitos previos

- Cuenta en [Railway](https://railway.app) (registro con GitHub)
- Repositorio en **GitHub** con tu proyecto
- **MySQL externo** (Railway no ofrece MySQL nativo)
- Dominio propio (opcional; ej. Namecheap)

---

## 2. Base de datos MySQL externa

### Opción A: PlanetScale (recomendado)

1. Crea cuenta en [planetscale.com](https://planetscale.com)
2. Crea una base de datos
3. En **Connect** → **Connect with** copia la URL, por ejemplo:
   ```
   mysql://usuario:xxx@aws.connect.psdb.cloud/nombre_bd?sslaccept=strict
   ```
4. La app adapta automáticamente `mysql://` a `mysql+pymysql://` en `config.py`

### Opción B: Aiven (MySQL clásico)

1. Crea cuenta en [aiven.io](https://aiven.io)
2. Crea un servicio MySQL (plan gratuito disponible)
3. Copia la connection string

### Opción C: Otros

- [FreeSQLDatabase.com](https://freesqldatabase.com)
- MySQL en un VPS propio

---

## 3. Preparar y subir el proyecto

### 3.1 Archivos incluidos en el proyecto

El proyecto ya incluye:

- **`Dockerfile`**: build multi-etapa (Node para frontend + Python para API). Railway lo usa por defecto y evita el error "Error creating build plan with Railpack".
- **`Procfile`**: `web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` (por si se usa Nixpacks).
- **`nixpacks.toml`**: instala Python + Node, construye el frontend y arranca el backend (solo si no se usa Dockerfile).
- **`requirements.txt`**: dependencias Python

### 3.2 Construir frontend y servir desde FastAPI

El backend sirve el frontend compilado. En `app/main.py` existe la configuración para montar el SPA desde `frontend/dist`. Si ese directorio existe tras el build, se sirve automáticamente; si no existe, se muestra solo un warning.

### 3.3 Variable de API en el frontend

En `frontend/src/services/api.js` se usa:

```javascript
baseURL: import.meta.env.VITE_API_URL || '/api'
```

En producción (mismo dominio), el frontend se sirve desde el mismo origen que el API, así que `/api` funciona correctamente. Si el frontend está en otro dominio, configura `VITE_API_URL` al hacer el build.

### 3.4 Subir a GitHub

```bash
git add .
git commit -m "Preparar para Railway"
git push origin main
```

---

## 4. Crear proyecto en Railway

1. Entra en [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub repo**
3. Conecta GitHub y selecciona el repositorio
4. Elige la rama (ej. `main`)
5. Railway detectará el **Dockerfile** en la raíz y usará Docker para el build (recomendado). Si no hubiera Dockerfile, Railway usaría Railpack y podría fallar con "Error creating build plan with Railpack" en proyectos Python + Node.

### 4.1 Si el build falló antes con "Error creating build plan with Railpack"

- Los **nuevos servicios** en Railway usan **Railpack** por defecto; Nixpacks está deprecado. Railpack a veces no detecta bien proyectos con Python + Node (FastAPI + frontend React).
- **Solución:** El repositorio incluye un **`Dockerfile`** en la raíz. Si Railway ya creó el servicio con Railpack, haz un **nuevo deploy** tras subir el Dockerfile: Railway suele detectar el Dockerfile y usarlo automáticamente. Si no, en **Settings** → **Build** revisa que esté usando "Dockerfile" como método de build.

---

## 5. Variables de entorno

En Railway → tu servicio → **Variables** (o **Settings** → **Variables**):

| Variable | Valor | Requerido |
|----------|-------|-----------|
| `DATABASE_URL` | `mysql+pymysql://user:pass@host:3306/dbname` (o `mysql://...` para PlanetScale) | Sí |
| `SECRET_KEY` | Clave larga y aleatoria (mín. 32 caracteres). Ejemplo: `python -c "import secrets; print(secrets.token_hex(32))"` | Sí |
| `ALLOWED_ORIGINS` | URL de tu app. Ejemplo: `https://medinaautodiag-api-production.up.railway.app` (la que te asigne Railway) | Sí |
| `DEBUG_MODE` | `false` | Sí |

### Alternativa a DATABASE_URL

Si usas variables separadas:

- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`

### Opcionales

| Variable | Valor |
|----------|-------|
| `VITE_API_URL` | Solo si el frontend está en otro dominio. Si todo va junto, no la configures |
| `IVA_PORCENTAJE` | `8` o `16` según régimen fiscal (México) |
| `DOCS_ENABLED` | `true` para exponer `/docs` y `/redoc` |
| `DOCS_USER`, `DOCS_PASSWORD` | Si usas autenticación en la documentación |

---

## 6. Migraciones de base de datos

Después del primer deploy, ejecuta las migraciones:

### Opción 1: CLI de Railway

```bash
railway run alembic upgrade head
```

### Opción 2: Local apuntando a BD de producción

```bash
DATABASE_URL="mysql+pymysql://user:pass@host:3306/db" alembic upgrade head
```

---

## 7. Dominio personalizado y HTTPS

1. Railway genera una URL tipo `https://xxx.up.railway.app`
2. Para dominio propio (ej. `app.medinaautodiag.com`):
   - Railway → **Settings** → **Domains** → **Add custom domain**
   - En tu DNS (Namecheap, etc.):
     - **CNAME**: Host `app`, Value `tu-proyecto.up.railway.app`
     - O registro **A** según indique Railway
3. HTTPS se gestiona automáticamente en Railway

---

## 8. Verificación

| URL | Debe mostrar |
|-----|--------------|
| `https://tu-url.railway.app/health` | `{"status":"ok","database":"connected",...}` |
| `https://tu-url.railway.app/` | Frontend (SPA) de MedinaAutoDiag |
| `https://tu-url.railway.app/api/docs` | Documentación OpenAPI (si `DOCS_ENABLED=true`) |

---

## 9. Resumen rápido

1. Crear MySQL en PlanetScale (o similar)
2. Subir código a GitHub
3. Crear proyecto en Railway conectado al repo
4. Configurar variables: `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_ORIGINS`, `DEBUG_MODE=false`
5. Ejecutar migraciones: `railway run alembic upgrade head`
6. Abrir la URL generada por Railway y probar

---

## 10. Checklist final

- [ ] MySQL accesible desde internet (no solo localhost)
- [ ] Variables de entorno configuradas
- [ ] `SECRET_KEY` fuerte y único
- [ ] `ALLOWED_ORIGINS` con tu dominio real
- [ ] Migraciones ejecutadas
- [ ] Frontend construido por `nixpacks.toml` y servido por FastAPI
- [ ] HTTPS activo (Railway lo gestiona)

---

## 11. Problemas frecuentes

| Problema | Posible causa | Solución |
|----------|---------------|----------|
| 502 Bad Gateway | Backend no arranca o no escucha en `$PORT` | Verifica `Procfile` con `--port ${PORT:-8000}` y `--host 0.0.0.0` |
| CORS | Origen no permitido | Revisa `ALLOWED_ORIGINS` con la URL exacta del frontend |
| No conecta a MySQL | Firewall o URL incorrecta | Permite conexiones externas en el proveedor MySQL y revisa credenciales |
| 404 en rutas del frontend | SPA sin catch-all | El backend debe devolver `index.html` para rutas no-API |
| APIs no responden | Frontend en otro dominio sin `VITE_API_URL` | Configura `VITE_API_URL` al hacer el build del frontend |

---

## 12. Enlaces útiles

- [Railway Docs](https://docs.railway.app)
- [PlanetScale](https://planetscale.com)
- [Aiven MySQL](https://aiven.io/mysql)
