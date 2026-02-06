# Guía de migraciones con Alembic

Este proyecto usa **Alembic** para gestionar cambios de esquema de la base de datos de forma versionada y segura.

## Requisitos

- Python con `alembic` instalado (`pip install -r requirements.txt`)
- Variables de entorno configuradas (`.env`): `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`

## Comandos principales

| Comando | Descripción |
|---------|-------------|
| `python -m alembic current` | Ver la revisión actual de la BD |
| `python -m alembic history` | Ver historial de migraciones |
| `python -m alembic upgrade head` | Aplicar todas las migraciones pendientes |
| `python -m alembic downgrade -1` | Revertir la última migración |
| `python -m alembic stamp head` | Marcar la BD como "actualizada" sin ejecutar migraciones |
| `python -m alembic revision --autogenerate -m "descripcion"` | Generar migración automática desde los modelos |

## Primera vez: base de datos existente

Si ya tienes una base de datos funcionando con el esquema actual:

```bash
python -m alembic stamp head
```

Esto crea la tabla `alembic_version` y marca la revisión actual. **No modifica ninguna tabla existente.**

## Primera vez: base de datos nueva

1. Crear la base de datos en MySQL:
   ```sql
   CREATE DATABASE medina_autodiag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. Iniciar la aplicación una vez (crea las tablas vía `create_all`):
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

3. Marcar el esquema como baseline:
   ```bash
   python -m alembic stamp head
   ```

## Crear una nueva migración

Cuando modifiques modelos en `app/models/`:

1. Generar la migración:
   ```bash
   python -m alembic revision --autogenerate -m "agregar_campo_x_a_tabla_y"
   ```

2. Revisar el archivo generado en `alembic/versions/`. Verifica que:
   - Las operaciones `upgrade()` son correctas
   - Las operaciones `downgrade()` permiten revertir el cambio

3. Aplicar la migración:
   ```bash
   python -m alembic upgrade head
   ```

## Flujo recomendado en desarrollo

1. Modificar el modelo en `app/models/`
2. `python -m alembic revision --autogenerate -m "descripcion_cambio"`
3. Revisar y ajustar la migración si es necesario
4. `python -m alembic upgrade head`
5. Probar la aplicación

## Despliegue en producción

1. Hacer backup de la base de datos
2. Ejecutar migraciones antes de desplegar la nueva versión:
   ```bash
   python -m alembic upgrade head
   ```
3. Desplegar e iniciar la aplicación

## Tablas sin modelo

La BD puede tener tablas que no tienen modelo SQLAlchemy (ej: `detalles_devolucion`, `citas`, `auditoria`). Alembic está configurado para **no sugerir eliminarlas** al generar migraciones. Solo se comparan las tablas definidas en `app.models`.

## Estructura

```
alembic/
├── env.py              # Configuración: usa app.config, importa modelos
├── README
├── script.py.mako      # Plantilla para nuevas migraciones
└── versions/           # Archivos de migración
    └── 3d82bfb3252b_baseline_schema_existente.py
alembic.ini             # Configuración de Alembic
```

## Troubleshooting

**Error: "Can't locate revision identified by 'xxx'"**
- La tabla `alembic_version` tiene una revisión que no existe en `alembic/versions/`. Resuelve manualmente en la BD o restaura el archivo de migración.

**Error al conectar a la BD**
- Verifica que MySQL esté corriendo y que las variables de entorno estén correctas.

**Autogenerate sugiere cambios extraños**
- Revisa que los modelos coincidan con el esquema real. Puede haber diferencias de tipos (ENUM vs String) que requieren migraciones manuales.
