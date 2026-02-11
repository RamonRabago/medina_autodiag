#!/bin/sh
# Railway: arranque rápido. Ejecuta migraciones UNA VEZ: railway run alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
