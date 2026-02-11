# ============================================================
# Medina AutoDiag - Deploy en Railway (evita error Railpack)
# Multi-etapa: construye frontend con Node, ejecuta API con Python
# ============================================================

# --- Etapa 1: construir el frontend (React/Vite) ---
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# --- Etapa 2: API FastAPI + servir frontend estático ---
FROM python:3.12-slim
WORKDIR /app

# Dependencias del sistema (por si algún paquete Python las necesita)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# CÓDIGO PRIMERO: evita que Docker cachee app/ con código viejo
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY scripts/ ./scripts/

# Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend compilado (desde etapa 1)
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Railway inyecta PORT; por defecto 8000
ENV PORT=8000
EXPOSE 8000

# Migraciones antes de arrancar
RUN chmod +x scripts/start.sh
CMD ["sh", "scripts/start.sh"]
