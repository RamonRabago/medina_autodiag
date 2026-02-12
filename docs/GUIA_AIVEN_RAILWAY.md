# Guía: Aiven + Railway desde cero

Pasos para tener MedinaAutoDiag en producción con MySQL en Aiven y la app en Railway.

---

## Parte 1: Crear MySQL en Aiven

### 1.1 Cuenta y proyecto

1. Entra en **[aiven.io](https://aiven.io)** → **Get started for free**
2. Regístrate con **GitHub** o **Google** (sin tarjeta de crédito)
3. En la consola: **Create project** → nombre ej. `medina-autodiag`
4. Acepta el proyecto creado

### 1.2 Crear servicio MySQL

1. **Services** → **Create service**
2. Selecciona **MySQL** como tipo
3. Elige el plan **Free** (1 CPU, 1 GB RAM, 1 GB disco)
4. No eliges región en el plan gratuito
5. **Create service** y espera 2–3 minutos a que esté en estado **Running**

### 1.3 Obtener la URL de conexión

1. Entra en tu servicio MySQL
2. Abre la pestaña **Overview**
3. En **Connection information** → **Service URI**:
   - Haz clic en **Copy** para copiar la URI
   - Formato: `mysql://avnadmin:PASSWORD@HOST:PORT/defaultdb?ssl-mode=REQUIRED`
4. Si la URI no incluye `?ssl-mode=REQUIRED`, añádelo al final
5. Guárdala: la usarás como `DATABASE_URL` en Railway

### 1.4 Crear base de datos (opcional)

Aiven crea una base `defaultdb`. Puedes usarla o crear una nueva:

1. **Databases** → **Create database**
2. Nombre: `medina_autodiag` (o el que prefieras)
3. Si creas una nueva, cambia en la URI el último segmento:  
   `.../defaultdb?...` → `.../medina_autodiag?...`

---

## Parte 2: Desplegar en Railway

### 2.1 Crear proyecto en Railway

1. Entra en **[railway.app](https://railway.app)** → **Login with GitHub**
2. **New Project** → **Deploy from GitHub repo**
3. Conecta GitHub si falta y elige el repo `medina_autodiag` (o el tuyo)
4. Rama: `main`
5. Railway detecta el **Dockerfile** y hace el build automáticamente

### 2.2 Generar URL pública

1. En tu servicio → **Settings** → **Networking**
2. En **Public networking** → **Generate domain**
3. Aparecerá una URL como `https://medina-autodiag-production-xxxx.up.railway.app`
4. **Cópiala**: la necesitas para `ALLOWED_ORIGINS`

### 2.3 Configurar variables de entorno

1. Pestaña **Variables** del servicio
2. Añade (o modifica) estas variables:

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | La Service URI de Aiven (con `?ssl-mode=REQUIRED`) |
| `SECRET_KEY` | Ejecuta el comando de abajo → pega el resultado |
| `ALLOWED_ORIGINS` | `https://tu-url.up.railway.app` (la URL que generaste en 2.2) |
| `DEBUG_MODE` | `false` |

Para generar `SECRET_KEY` en tu PC:

```powershell
cd c:\medina_autodiag_api
.\venv\Scripts\Activate.ps1
python -c "import secrets; print(secrets.token_hex(32))"
```

Copia el texto que aparece y pégalo como valor de `SECRET_KEY`.

### 2.4 Redeploy

Tras guardar las variables, Railway hará un nuevo deploy solo. Si no:

- **Deployments** → menú (⋮) del último deploy → **Redeploy**

---

## Parte 3: Migraciones de base de datos

Cuando el deploy termine, crea las tablas en MySQL:

### Opción A: CLI de Railway

```powershell
npm install -g @railway/cli
railway login
railway link    # selecciona tu proyecto y servicio
railway run alembic upgrade head
```

### Opción B: Local con DATABASE_URL

```powershell
cd c:\medina_autodiag_api
.\venv\Scripts\Activate.ps1
$env:DATABASE_URL = "mysql://avnadmin:TU_PASSWORD@HOST:PORT/defaultdb?ssl-mode=REQUIRED"
alembic upgrade head
```

Usa la misma Service URI de Aiven que pusiste en Railway. La app la convierte a `mysql+pymysql://` automáticamente.

---

## Parte 4: Verificación

| URL | Debe mostrar |
|-----|--------------|
| `https://tu-url.railway.app/health` | `{"status":"ok","database":"connected",...}` |
| `https://tu-url.railway.app/` | Frontend de MedinaAutoDiag |
| `https://tu-url.railway.app/api/docs` | Documentación OpenAPI |

---

## Checklist rápido

- [ ] Aiven: servicio MySQL en estado **Running**
- [ ] Aiven: Service URI copiada (con `?ssl-mode=REQUIRED`)
- [ ] Railway: proyecto creado desde GitHub
- [ ] Railway: dominio público generado
- [ ] Railway: `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_ORIGINS`, `DEBUG_MODE=false`
- [ ] Migraciones: `alembic upgrade head` ejecutado
- [ ] `/health` responde OK

---

## Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| `DATABASE_URL no está definida` | Falta la variable | Añade `DATABASE_URL` en Variables |
| `SECRET_KEY no configurado` | Falta o es débil | Genera una con `secrets.token_hex(32)` |
| CORS bloqueando peticiones | `ALLOWED_ORIGINS` incorrecta | Usa la URL exacta de Railway (con `https://`) |
| No conecta a MySQL | SSL o URI incorrecta | Añade `?ssl-mode=REQUIRED` a la URI |
