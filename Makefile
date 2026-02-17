# MedinaAutoDiag API - Comandos de desarrollo

.PHONY: test install run openapi audit

# Ejecutar tests
test:
	python -m pytest tests/ -v

# Instalar dependencias (incluye pytest, httpx)
install:
	pip install -r requirements.txt

# Ejecutar servidor (desarrollo)
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Exportar openapi.json estático a docs/
openapi:
	python scripts/export_openapi.py

# Auditoría de seguridad (pip-audit + npm audit) - ejecutar semanalmente
audit:
	python scripts/auditar_dependencias.py
