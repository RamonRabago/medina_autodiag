# Tests MedinaAutoDiag API

## Ejecutar tests

```bash
# Con pytest (recomendado)
make test

# O directamente
python -m pytest tests/ -v

# Script legacy (pytest + scripts)
python scripts/ejecutar_todas_pruebas.py
```

## Estructura

- `conftest.py` - Fixtures (client TestClient)
- `test_api_*.py` - Tests de endpoints HTTP
- `test_modulos.py` - Verificación de imports y rutas
- `test_cuentas_por_pagar.py` - Módulo cuentas por pagar
- `test_reporte_utilidad.py` - Reporte de utilidad

## Dependencias

pytest, pytest-asyncio y httpx están en requirements.txt. Instalar con:

```bash
pip install -r requirements.txt
```
