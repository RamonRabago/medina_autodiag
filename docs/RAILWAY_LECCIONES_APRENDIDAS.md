# Lecciones aprendidas: Railway y cambios que no se reflejaban

**Fecha:** Febrero 2026  
**Estado final:** Deploy funcionando correctamente

---

## 1. ¿Qué pasaba?

Aunque se hacía `git commit` y `git push`, Railway parecía **no tomar los cambios**:

- Los logs seguían mostrando mensajes de **Alembic** al arrancar
- El arranque se quedaba bloqueado en `Context impl MySQLImpl`
- Cambios en `start.sh` (quitar alembic) no tenían efecto
- Probamos: NO_CACHE, redeploy, borrar y recrear el proyecto

**Síntoma:** "Los commits no se guardan" o "Railway no toma mis cambios".

---

## 2. Causa raíz (por qué no era un problema de sync)

Los commits **sí** se enviaban a GitHub. El build de Railway **sí** usaba código nuevo. El problema era otro:

**Railway tenía múltiples fuentes de configuración del comando de arranque.** Cuando varias definen el comando, alguna podía **anular** el CMD del Dockerfile:

| Prioridad | Fuente | Contenido problemático |
|-----------|--------|------------------------|
| 1 | **Start Command en Dashboard** | Si estaba configurado con `alembic upgrade head && uvicorn...` |
| 2 | **Procfile** | `web: alembic upgrade head && uvicorn...` |
| 3 | **Config en código (railway.toml)** | No había `startCommand` definido |
| 4 | **Dockerfile CMD** | `scripts/start.sh` (sin alembic) |

Si el Procfile o el Start Command del dashboard definían alembic, eso se usaba en lugar del CMD del Dockerfile.

---

## 3. Solución principal

**Definir el comando de arranque en `railway.toml`.** La configuración en código tiene prioridad sobre el dashboard y otras fuentes.

```toml
[deploy]
startCommand = '/bin/sh -c "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"'
```

Con esto, el arranque queda fijado en el repo y nadie puede cambiarlo por accidente.

---

## 4. Cambios que resolvieron todo

| Archivo | Cambio | Motivo |
|---------|--------|--------|
| **railway.toml** | Se añadió `[deploy] startCommand` explícito | Evitar que Procfile o dashboard definan el arranque con alembic |
| **Procfile** | Se quitó `alembic upgrade head &&` | Si algo usa Procfile, que no ejecute migraciones al arrancar |
| **nixpacks.toml** | Se quitó `alembic upgrade head` del `[start] cmd` | Evitar arranque con alembic si se usara Nixpacks |
| **scripts/start.sh** | Ya sin alembic (cambio anterior) | Sólo uvicorn |
| **app/config.py** | `DATABASE_URL` sin query params (`?ssl-mode=...`) | Evitar `TypeError: ssl-mode` en PyMySQL |
| **app/database.py** | SSL con `create_default_context()` y `check_hostname=False` | Conectar a Aiven sin errores de certificado |

---

## 5. Hash actual que debería verse en Railway

Si el deploy está actualizado, el hash debe ser **`9d9ed5a`** o posterior:

```
9d9ed5a fix: SSL check_hostname=False para Aiven (certificado autofirmado)
```

Comprobar en: **Railway → Deployments → deploy activo** (junto al nombre o en la cabecera).

---

## 6. Cómo evitar que vuelva a pasar

### Al conectar un proyecto nuevo en Railway

1. **railway.toml** en la raíz con al menos:
   ```toml
   [build]
   builder = "DOCKERFILE"
   
   [deploy]
   preDeployCommand = ["alembic", "upgrade", "head"]  # Migraciones ANTES de arrancar (fase separada)
   startCommand = '/bin/sh -c "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"'
   ```

2. **Procfile** (si existe): no incluir migraciones en el comando de arranque.

3. **nixpacks.toml** (si existe): no incluir `alembic` en el `[start] cmd`.

**Importante:** `preDeployCommand` corre en una fase separada (entre build y deploy). NO poner alembic en `startCommand`: bloqueaba el arranque. Ver sección 2 de este doc.

### Si los cambios no se reflejan

1. Railway → **Settings → Deploy** → revisar **Start Command** (borrarlo si está definido, para usar el de `railway.toml`).
2. Railway → **Settings → Build** → confirmar que **Builder = Dockerfile**.
3. Railway → **Deployments** → comprobar que el hash del deploy coincide con el último commit en GitHub.

---

## 7. Resumen ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| ¿Los commits no se guardaban? | No. Los commits sí se subían; el problema era un Start Command distinto al esperado. |
| ¿Qué lo solucionó? | Definir `startCommand` explícitamente en `railway.toml`. |
| ¿Qué hash ver ahora? | `9d9ed5a` o posterior. |
| ¿Cómo evitarlo? | Mantener `railway.toml` con `startCommand` explícito; no definir Start Command en el dashboard. |

---

## 8. Aclaración: ¿Los cambios de decimales afectaron el arranque?

**No.** Los cambios de stock decimales (stock inicial, etc. en inventario) **no tocaron** la lógica de arranque.

| Cambio | Archivos tocados | ¿Toca arranque? |
|--------|------------------|------------------|
| Stock decimales (37.6 L aceite) | `inventario_service.py`, `RepuestoForm.jsx`, migración `l2m3n4o5p6q7_stock_decimales.py`, modelos/schemas | **No** |
| Fix Decimal\*float en verificar_alertas_stock | `inventario_service.py`, `reporte rotacion` | **No** |
| Fix caja_turnos.diferencia (migraciones al iniciar) | **Procfile, nixpacks.toml, scripts/start.sh, Dockerfile** | **Sí** — aquí empezó el bloqueo |

**Timeline:**

1. **3f2e4ee** – feat: Stock decimales → no toca `railway.toml`, Procfile, `start.sh`, nixpacks.
2. **68d7f56, 817bd58, 582e40b** – fix Decimal\*float en inventario → tampoco tocan arranque.
3. **f500fd1, 0899d0b** – fix caja_turnos.diferencia: se añadió `alembic upgrade head` a **Procfile**, **nixpacks** y **start.sh** para ejecutar migraciones al iniciar.
4. Esa ejecución de alembic al arranque **bloqueaba** el deploy (queda en `Context impl MySQLImpl`).
5. **edc1241, 923aa62, a15f6e7** – se quitó alembic del arranque y se definió `startCommand` en `railway.toml`.

**Conclusión:** La sensación de que “después de los decimales no se aplicaban los cambios” coincidió en el tiempo con la incorporación de alembic al arranque para resolver `caja_turnos.diferencia`. Ese cambio en Procfile/start.sh causó el bloqueo. Los decimales no modifican `railway.toml`, Procfile ni el arranque.

---

## 9. Referencias

- [Railway Config as Code](https://docs.railway.app/config-as-code)
- [Railway Start Command](https://docs.railway.app/guides/start-command)
- `docs/DEPLOY_RAILWAY.md` — Guía de deploy
- `docs/GUIA_AIVEN_RAILWAY.md` — Guía Aiven + Railway
