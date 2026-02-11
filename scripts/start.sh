#!/bin/sh
# Ejecuta migraciones antes de arrancar la app (Railway, etc.)
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
