#!/bin/sh
# Railway: arranque rápido. Ejecuta migraciones UNA VEZ: railway run alembic upgrade head
# Crear estructura de uploads para volumen (/app/uploads) - repuestos y comprobantes
mkdir -p /app/uploads/repuestos /app/uploads/comprobantes
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
