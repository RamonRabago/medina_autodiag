# Análisis: Deploy Railway y sync con GitHub

## 1. Commits relevantes (orden cronológico)

| Commit    | Descripción                          | ¿Incluye start.sh sin alembic? |
|-----------|--------------------------------------|--------------------------------|
| `a00ac12` | docs: guía Railway-GitHub            | Sí (hereda de edc1241)         |
| `edc1241` | fix: no ejecutar alembic al arrancar | Sí – quitó alembic del start   |
| `7626e13` | fix: ssl-mode en config.py           | Sí                             |

**Conclusión:** `a00ac12` es el último commit en `main` y usa un `start.sh` sin alembic.

---

## 2. Qué debería desplegar Railway

Con el repo y rama correctos, el deploy activo debería ser **`a00ac12`** o uno posterior.

---

## 3. Origen de los mensajes de Alembic

### 3.1 Dockerfile (usado por railway.toml)

- `railway.toml` → `builder = "DOCKERFILE"` → se usa solo el Dockerfile.
- Dockerfile → `CMD ["sh", "scripts/start.sh"]`.
- `scripts/start.sh` en el repo → **no ejecuta alembic**, solo uvicorn.

Si Railway usa Dockerfile, no debería aparecer alembic en los logs.

### 3.2 nixpacks.toml (fallback o detección automática)

```toml
[start]
cmd = "alembic upgrade head && uvicorn app.main:app ..."
```

Si Railway usara Nixpacks en vez del Dockerfile, sí ejecutaría alembic.

Posibles casos:

- La configuración de Railway apunta a Nixpacks en lugar de Dockerfile.
- Hay un fallback a Nixpacks si el build con Docker falla.
- El `railway.toml` no se lee o no se aplica correctamente.

---

## 4. El hash `c58cb1a0`

- `c58cb1a0` **no existe** en el historial de commits del repo actual.
- Es probable que sea un ID de Railway u otra referencia, no un commit de este repo.

---

## 5. Comprobaciones recomendadas

1. **Settings → Build**  
   - Confirmar que el builder es **Dockerfile** (y no Nixpacks/Railpack).
   - Revisar la ruta del Dockerfile (por defecto `./Dockerfile`).

2. **Actualizar `nixpacks.toml`**  
   - Quitar `alembic upgrade head` del comando de inicio para evitar que, si se usa Nixpacks, se ejecute alembic en el arranque.

3. **Sync con GitHub**  
   - Confirmar que el último deploy muestra un commit como `a00ac12` (o posterior).
   - Si sigue apareciendo otro hash o el mismo comportamiento, revisar:
     - Webhooks de GitHub.
     - Variable `NO_CACHE=1` y redeploy.

4. **Build Logs**  
   - En el build, comprobar si se indica explícitamente que usa Dockerfile o Nixpacks.
