# MedinaAutoDiag API - Comandos de desarrollo

.PHONY: test install run

# Ejecutar tests
test:
	python -m pytest tests/ -v

# Instalar dependencias (incluye pytest, httpx)
install:
	pip install -r requirements.txt

# Ejecutar servidor (desarrollo)
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
