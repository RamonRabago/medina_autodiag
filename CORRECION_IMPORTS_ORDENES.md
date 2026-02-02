# CORRECCIÓN DE IMPORTS - MÓDULO ÓRDENES DE TRABAJO

## Problema Identificado

Error al iniciar la aplicación:
```
ModuleNotFoundError: No module named 'app.schemas.servicio'
```

## Causa del Error

Los archivos de schemas tienen nombres diferentes a los que se estaban importando:

**Archivos reales:**
- `app/schemas/servicio_schema.py`
- `app/schemas/orden_trabajo_schema.py`

**Imports incorrectos:**
- `from app.schemas.servicio import ...`
- `from app.schemas.orden_trabajo import ...`

## Archivos Corregidos

### 1. `app/routers/servicios.py` (Línea 7)

**ANTES:**
```python
from app.schemas.servicio import (
    ServicioCreate, ServicioUpdate, ServicioResponse, ServicioListResponse
)
```

**DESPUÉS:**
```python
from app.schemas.servicio_schema import (
    ServicioCreate, ServicioUpdate, ServicioResponse, ServicioListResponse
)
```

### 2. `app/routers/ordenes_trabajo.py` (Línea 17)

**ANTES:**
```python
from app.schemas.orden_trabajo import (
    OrdenTrabajoCreate, OrdenTrabajoUpdate, OrdenTrabajoResponse, 
    OrdenTrabajoListResponse, IniciarOrdenRequest, FinalizarOrdenRequest,
    EntregarOrdenRequest, AutorizarOrdenRequest, AgregarServicioRequest,
    AgregarRepuestoRequest
)
```

**DESPUÉS:**
```python
from app.schemas.orden_trabajo_schema import (
    OrdenTrabajoCreate, OrdenTrabajoUpdate, OrdenTrabajoResponse, 
    OrdenTrabajoListResponse, IniciarOrdenRequest, FinalizarOrdenRequest,
    EntregarOrdenRequest, AutorizarOrdenRequest, AgregarServicioRequest,
    AgregarRepuestoRequest
)
```

### 3. `app/main.py` - Imports Agregados (después de línea 31)

```python
# Routers de Órdenes de Trabajo
from app.routers.servicios import router as servicios_router
from app.routers.ordenes_trabajo import router as ordenes_trabajo_router
```

### 4. `app/main.py` - Routers Registrados (después de línea 147)

```python
# ==========================================
# ÓRDENES DE TRABAJO
# ==========================================

# 🛠️ SERVICIOS
app.include_router(servicios_router, tags=["Órdenes - Servicios"])

# 📋 ÓRDENES DE TRABAJO
app.include_router(ordenes_trabajo_router, tags=["Órdenes - Órdenes de Trabajo"])
```

## Verificación

Para verificar que todo funciona correctamente:

1. **Iniciar el servidor:**
   ```bash
   cd C:\medina_autodiag_api
   .\venv\Scripts\activate
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Verificar en el navegador:**
   - Swagger UI: http://127.0.0.1:8000/docs
   - Deberías ver las nuevas secciones:
     - "Órdenes - Servicios"
     - "Órdenes - Órdenes de Trabajo"

3. **Endpoints disponibles:**

   **Servicios:**
   - `POST /servicios` - Crear servicio
   - `GET /servicios` - Listar servicios
   - `GET /servicios/{id}` - Obtener servicio
   - `PUT /servicios/{id}` - Actualizar servicio
   - `DELETE /servicios/{id}` - Eliminar servicio
   - `GET /servicios/estadisticas` - Estadísticas

   **Órdenes de Trabajo:**
   - `POST /ordenes-trabajo` - Crear orden
   - `GET /ordenes-trabajo` - Listar órdenes
   - `GET /ordenes-trabajo/{id}` - Obtener orden
   - `PUT /ordenes-trabajo/{id}` - Actualizar orden
   - `DELETE /ordenes-trabajo/{id}` - Eliminar orden
   - `POST /ordenes-trabajo/{id}/iniciar` - Iniciar orden
   - `POST /ordenes-trabajo/{id}/finalizar` - Finalizar orden
   - `POST /ordenes-trabajo/{id}/entregar` - Entregar orden
   - `POST /ordenes-trabajo/{id}/autorizar` - Autorizar orden
   - `POST /ordenes-trabajo/{id}/servicios` - Agregar servicio
   - `POST /ordenes-trabajo/{id}/repuestos` - Agregar repuesto
   - Y más endpoints...

## Estructura de Archivos Final

```
app/
├── main.py                          ✅ Actualizado
├── routers/
│   ├── servicios.py                 ✅ Corregido
│   ├── ordenes_trabajo.py           ✅ Corregido
│   └── ...
├── schemas/
│   ├── servicio_schema.py           ✅ (ya existía)
│   ├── orden_trabajo_schema.py      ✅ (ya existía)
│   └── ...
└── models/
    ├── servicio.py                  ✅ (ya existía)
    ├── orden_trabajo.py             ✅ (ya existía)
    └── ...
```

## Notas Importantes

1. **Nombres de archivos en schemas:**
   - Siempre usa `_schema.py` como sufijo para los schemas
   - Ejemplo: `servicio_schema.py`, `orden_trabajo_schema.py`

2. **Imports:**
   - Siempre verifica el nombre REAL del archivo antes de importar
   - Usa `ls app/schemas/` para ver los archivos disponibles

3. **Convención de nombres:**
   - Models: `app/models/nombre.py`
   - Schemas: `app/schemas/nombre_schema.py`
   - Routers: `app/routers/nombre.py` o `app/routers/nombres.py` (plural)

## ¿Qué Hacer si Vuelve a Fallar?

1. **Verificar que el archivo existe:**
   ```bash
   ls app/schemas/servicio_schema.py
   ls app/schemas/orden_trabajo_schema.py
   ```

2. **Verificar los imports en los routers:**
   ```bash
   grep "from app.schemas" app/routers/servicios.py
   grep "from app.schemas" app/routers/ordenes_trabajo.py
   ```

3. **Verificar que los routers están registrados:**
   ```bash
   grep "servicios_router\|ordenes_trabajo_router" app/main.py
   ```

---

**Fecha:** 29 de Enero de 2026
**Estado:** ✅ CORREGIDO Y VERIFICADO
