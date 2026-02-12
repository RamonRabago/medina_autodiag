# Guía de despliegue desde cero: Aiven + Railway (Medina AutoDiag)

Sigue estos pasos **en orden**. Si algo falla, revisa la sección de verificación y problemas al final.

---

## Parte 1: Base de datos en Aiven (MySQL)

### 1.1 Cuenta y proyecto

1. Entra en **[aiven.io](https://aiven.io)** e inicia sesión (o regístrate).
2. Si te pide "Create Apache Kafka®" o "Explore Aiven for streaming", elige **"Explore Aiven for streaming"**.
3. En el panel, haz clic en **"Create service"** (botón azul arriba a la derecha).
4. En el tipo de servicio elige **MySQL** (no Kafka).

### 1.2 Crear el servicio MySQL

1. **Service tier:** Elige **Developer** (~5 USD/mes tras prueba) o **Free** si solo quieres probar.
2. **Cloud:** North America (o la región que prefieras).
3. **Plan:** Developer-1 (1 CPU, 1 GB RAM, 8 GB).
4. **Name:** Pon por ejemplo `mysql-medina-autodiag` (no se puede cambiar después).
5. Clic en **"Create service and start trial"**.
6. Espera a que el estado pase de "Rebuilding" a **"Running"** (unos minutos).

### 1.3 Obtener la URL de conexión (Service URI)

1. En Aiven, entra al servicio MySQL que creaste.
2. Pestaña **Overview** → sección **"Connection information"**.
3. Busca **"Service URI"** (o "Connection string"). Cópiala completa. Se verá parecido a:
   ```text
   mysql://avnadmin:TU_PASSWORD@mysql-medina-autodiag-xxxx.aivencloud.com:12345/defaultdb?ssl-mode=REQUIRED
   ```
4. **Base de datos:**  
   - Si en "Database name" dice **defaultdb**, deja la URI tal cual.  
   - Si en el menú lateral creaste una base **medina_autodiag** (Databases → Create), en la URI cambia `defaultdb` por `medina_autodiag` en la parte final (antes de `?ssl-mode=...`).

**Importante:** No quites `?ssl-mode=REQUIRED` del final; Aiven lo exige. Guarda esta URI para el paso 2.

---

## Parte 2: Código en GitHub

### 2.1 Repositorio actualizado

1. El proyecto debe tener en la **raíz**: `Dockerfile`, `requirements.txt`, carpeta `app/`, `frontend/`, `alembic/`.
2. Sube los últimos cambios a tu rama `main`:
   ```bash
   cd c:\medina_autodiag_api
   git add .
   git status
   git commit -m "Preparar despliegue"
   git push origin main
   ```

---

## Parte 3: Proyecto en Railway

### 3.1 Crear proyecto desde GitHub

1. Entra en **[railway.app](https://railway.app)** e inicia sesión con GitHub.
2. **New Project** → **Deploy from GitHub repo**.
3. Conecta GitHub si te lo pide y selecciona el repositorio **medina_autodiag** (o el nombre que tenga).
4. Elige la rama **main**.
5. Railway creará un servicio y hará el primer build (usa el **Dockerfile** de la raíz). Espera a que el deploy termine (puede fallar la primera vez si faltan variables; lo arreglamos en 3.2).

### 3.2 Variables de entorno (obligatorias)

En Railway → tu servicio **medina_autodiag** → pestaña **Variables** (o **Settings** → **Variables**).

Añade o edita estas variables **una por una**:

| Variable        | Valor |
|-----------------|--------|
| `DATABASE_URL`  | La **Service URI** completa que copiaste de Aiven (con `?ssl-mode=REQUIRED` al final). Ejemplo: `mysql://avnadmin:xxx@mysql-xxx.aivencloud.com:12345/defaultdb?ssl-mode=REQUIRED` |
| `SECRET_KEY`    | Una clave aleatoria de al menos 32 caracteres. En tu PC: `python -c "import secrets; print(secrets.token_hex(32))"` y pega el resultado. |
| `DEBUG_MODE`    | `false` |
| `ALLOWED_ORIGINS` | Deja vacío por ahora; lo pondremos después de generar el dominio (paso 3.4). Si ya tienes la URL de Railway, ponla aquí (ej. `https://medina-autodiag-production-xxxx.up.railway.app`). |

**Sobre DATABASE_URL:**  
- La app convierte `mysql://` a `mysql+pymysql://` sola; no la cambies.  
- Si en Aiven creaste la base `medina_autodiag`, en la URI la parte de la base debe ser `/medina_autodiag?ssl-mode=REQUIRED`.  
- **Importante:** En Railway pon *solo* la URI de Aiven. No dejes variables `DB_HOST`, `DB_USER`, etc. con `localhost`; si existen, bórralas para que la app use solo `DATABASE_URL`.

**Opcional:** Si Railway detectó variables antiguas (`DB_HOST`, `DB_USER`, etc.) con valor `localhost`, **bórralas**; cuando `DATABASE_URL` está definida, la app solo usa esa. Si `DATABASE_URL` tiene localhost por error, la app en producción no arrancará (mensaje claro en logs).

### 3.3 Aplicar cambios y reiniciar

1. Guarda todas las variables (Railway suele guardar al salir del panel).
2. Si el servicio estaba caído o ya desplegado: en **Deployments** usa **Restart** en el último deploy para que arranque de nuevo con las variables actuales.

### 3.4 Generar dominio público (exponer el servicio)

1. En tu servicio, entra a **Settings** (o la pestaña donde esté **Networking** / **Public Networking**).
2. Busca **"Generate domain"**, **"Add domain"** o **"Public networking"**.
3. Genera el dominio. Te dará una URL como:  
   `https://medina-autodiag-production-xxxx.up.railway.app`
4. **Copia esa URL** y vuelve a **Variables**.
5. Edita `ALLOWED_ORIGINS` y pon **exactamente** esa URL (sin barra final). Ejemplo:  
   `https://medina-autodiag-production-xxxx.up.railway.app`
6. Guarda y **reinicia** el deploy otra vez (Restart) para que cargue el nuevo `ALLOWED_ORIGINS`.

---

## Parte 4: Migraciones (tablas en MySQL de Aiven)

Las tablas de la app se crean con Alembic. Hazlo **una vez** después de que el servicio esté en marcha y con `DATABASE_URL` correcta.

### Opción A: Con Railway CLI (recomendado)

1. Instala Railway CLI: [docs.railway.com/guides/cli](https://docs.railway.com/guides/cli).
2. En tu PC, en la carpeta del proyecto:
   ```bash
   cd c:\medina_autodiag_api
   railway login
   railway link
   ```
   (Elige el proyecto y el servicio medina_autodiag.)
3. Ejecuta migraciones (usa la `DATABASE_URL` del servicio en Railway):
   ```bash
   railway run alembic upgrade head
   ```
4. Debe salir algo como "Running alembic upgrade head" y terminar sin error.

### Opción B: Desde tu PC apuntando a Aiven

1. En tu PC, con la misma URI que tienes en Railway (copia la `DATABASE_URL` de Railway o reconstruye la URI de Aiven):
   ```bash
   cd c:\medina_autodiag_api
   set DATABASE_URL=mysql://avnadmin:TU_PASSWORD@mysql-xxx.aivencloud.com:12345/defaultdb?ssl-mode=REQUIRED
   railway run alembic upgrade head
   ```
   O en PowerShell:
   ```powershell
   $env:DATABASE_URL="mysql://avnadmin:TU_PASSWORD@mysql-xxx.aivencloud.com:12345/defaultdb?ssl-mode=REQUIRED"
   alembic upgrade head
   ```

---

## Parte 5: Verificación

1. **Health (API y base de datos)**  
   Abre en el navegador:  
   `https://TU-DOMINIO-RAILWAY.up.railway.app/health`  
   Debe devolver JSON con `"status":"ok"` y `"database":"connected"`.

2. **Frontend**  
   Abre:  
   `https://TU-DOMINIO-RAILWAY.up.railway.app/`  
   Debe cargar la app (login de Medina AutoDiag).

3. **Documentación API**  
   `https://TU-DOMINIO-RAILWAY.up.railway.app/api/docs`  
   (Si en variables tienes `DOCS_ENABLED=true`.)

4. **Login**  
   Crea un usuario inicial si la base estaba vacía (normalmente hay un endpoint de registro o lo haces desde la BD). Luego inicia sesión en la app.

---

## Resumen del orden

| Paso | Dónde   | Qué hacer |
|------|---------|-----------|
| 1    | Aiven   | Crear servicio MySQL, esperar "Running", copiar **Service URI** (con `?ssl-mode=REQUIRED`). |
| 2    | GitHub  | Código actualizado en `main` (con `Dockerfile` en la raíz). |
| 3    | Railway | Nuevo proyecto desde GitHub, rama `main`. |
| 4    | Railway | Variables: `DATABASE_URL` (URI de Aiven), `SECRET_KEY` (32+ caracteres), `DEBUG_MODE=false`. |
| 5    | Railway | Generar dominio → copiar URL → ponerla en `ALLOWED_ORIGINS` → Restart. |
| 6    | Railway / PC | Ejecutar `railway run alembic upgrade head` (o equivalente con `DATABASE_URL` local). |
| 7    | Navegador | Probar `/health`, luego la URL raíz y login. |

---

## Si algo falla

| Síntoma | Revisar |
|--------|--------|
| "SECRET_KEY no configurado o inseguro" | Variable `SECRET_KEY` en Railway con al menos 32 caracteres (generada con `secrets.token_hex(32)`). |
| "Can't connect to MySQL server on 'localhost'" | La app no está usando `DATABASE_URL`. En los logs debe aparecer **`[DB] DATABASE_URL is NOT set`** o **`[DB] DATABASE_URL is set. Connection target: ...`**. Si sale NOT set: en Railway entra al **servicio** que se despliega (el que tiene Deployments/Variables), pestaña **Variables**, y añade **`DATABASE_URL`** (nombre exacto) con la URI completa de Aiven. La variable debe estar en **ese servicio**, no solo en el proyecto. Guarda y haz **Restart** (o un nuevo deploy). |
| "Connection refused" o error SSL a la BD | Que la URI tenga `?ssl-mode=REQUIRED`; que el usuario/contraseña y host/puerto sean los de Aiven; que la base exista (defaultdb o medina_autodiag). |
| CORS o "blocked by CORS" | `ALLOWED_ORIGINS` debe ser exactamente la URL pública de Railway (sin `/` al final), y reiniciar después de cambiarla. |
| Build "Error creating build plan with Railpack" | Debe existir un **Dockerfile** en la raíz del repo; Railway lo usará en lugar de Railpack. Haz push del Dockerfile y redeploy. |
| Servicio "Unexposed" | En Settings del servicio, generar dominio (Generate domain / Public networking) para obtener URL pública. |

---

## Enlaces rápidos

- [Aiven Console](https://console.aiven.io/)
- [Railway Dashboard](https://railway.app/dashboard)
- [Railway CLI](https://docs.railway.com/guides/cli)
- Guía detallada en el mismo repo: `docs/DEPLOY_RAILWAY.md`
