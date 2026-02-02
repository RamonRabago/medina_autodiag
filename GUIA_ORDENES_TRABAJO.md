# 🔧 GUÍA COMPLETA - MÓDULO DE ÓRDENES DE TRABAJO

## 📋 Índice
1. [Introducción](#introducción)
2. [Instalación](#instalación)
3. [Características](#características)
4. [Estructura de Datos](#estructura-de-datos)
5. [Endpoints API](#endpoints-api)
6. [Flujo de Trabajo](#flujo-de-trabajo)
7. [Ejemplos de Uso](#ejemplos-de-uso)

---

## 🎯 Introducción

El módulo de **Órdenes de Trabajo** es el corazón del sistema MedinaAutoDiag. Integra todos los módulos existentes (clientes, vehículos, inventario, usuarios) para gestionar de manera completa el ciclo de vida de los trabajos realizados en el taller.

### ¿Qué incluye este módulo?

✅ **Catálogo de Servicios** - Base de datos de todos los servicios que ofrece el taller  
✅ **Órdenes de Trabajo** - Gestión completa del trabajo a realizar en cada vehículo  
✅ **Asignación de Técnicos** - Control de quién trabaja en cada orden  
✅ **Control de Estados** - Seguimiento del progreso de cada orden  
✅ **Integración con Inventario** - Uso automático de repuestos  
✅ **Costos y Facturación** - Cálculo automático de totales  
✅ **Sistema de Autorización** - Aprobación de trabajos por el cliente  

---

## 🚀 Instalación

### Paso 1: Copiar Archivos del Módulo

Copia los siguientes archivos a tu proyecto:

```
TU_PROYECTO/
├── app/
│   ├── models/
│   │   ├── servicio.py                    [NUEVO]
│   │   ├── orden_trabajo.py               [NUEVO]
│   │   └── detalle_orden.py               [NUEVO]
│   │
│   ├── schemas/
│   │   ├── servicio.py                    [NUEVO]
│   │   └── orden_trabajo.py               [NUEVO]
│   │
│   └── routers/
│       ├── servicios.py                   [NUEVO]
│       └── ordenes_trabajo.py             [NUEVO - combinar las 3 partes]
│
├── db_ordenes_trabajo.sql                 [NUEVO]
├── poblar_ordenes_trabajo.py              [NUEVO]
└── GUIA_ORDENES_TRABAJO.md               [NUEVO - este archivo]
```

### Paso 2: Combinar el Router de Órdenes

El router de órdenes de trabajo está dividido en 3 partes. Debes combinarlas en un solo archivo:

1. Abre `ordenes_trabajo_1.py`, `ordenes_trabajo_2.py` y `ordenes_trabajo_3.py`
2. Copia todo el contenido en orden en un solo archivo `app/routers/ordenes_trabajo.py`
3. Elimina las líneas de comentarios que dicen "PARTE 1", "PARTE 2", "PARTE 3"

### Paso 3: Actualizar Modelos Existentes

Abre el archivo `ACTUALIZACIONES_MODELOS_EXISTENTES.py` y sigue las instrucciones para agregar las relaciones necesarias en tus modelos de:
- `vehiculo.py`
- `cliente.py`
- `usuario.py`
- `repuesto.py`

### Paso 4: Ejecutar Script SQL

Ejecuta el script SQL en tu base de datos:

```bash
mysql -u root -p medinaautodiag < db_ordenes_trabajo.sql
```

O desde MySQL Workbench/PHPMyAdmin, ejecuta el contenido del archivo.

### Paso 5: Poblar Datos de Ejemplo

Ejecuta el script de Python para crear servicios y órdenes de ejemplo:

```bash
python poblar_ordenes_trabajo.py
```

### Paso 6: Actualizar main.py

Agrega los nuevos routers en tu `app/routers/main.py` o `app/main.py`:

```python
from app.routers import servicios, ordenes_trabajo

# Incluir routers
app.include_router(servicios.router, prefix="/api")
app.include_router(ordenes_trabajo.router, prefix="/api")
```

### Paso 7: Reiniciar la Aplicación

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## ✨ Características

### 1. Catálogo de Servicios

Gestiona todos los servicios que ofrece tu taller:

- **Categorías**: MANTENIMIENTO, REPARACION, DIAGNOSTICO, ELECTRICIDAD, SUSPENSION, FRENOS, MOTOR, TRANSMISION, AIRE_ACONDICIONADO, CARROCERIA, OTROS
- **Información**: Código, nombre, descripción, precio base, tiempo estimado
- **Control**: Activar/desactivar servicios
- **Flexibilidad**: Indica si requiere repuestos típicamente

### 2. Órdenes de Trabajo Completas

Cada orden incluye:

- **Número único**: Formato OT-YYYYMMDD-NNNN (ej: OT-20260128-0001)
- **Información del vehículo**: Cliente, vehículo, kilometraje
- **Asignación**: Técnico responsable
- **Fechas**: Ingreso, promesa de entrega, inicio, finalización, entrega
- **Estados**: PENDIENTE → EN_PROCESO → COMPLETADA → ENTREGADA
- **Prioridades**: BAJA, NORMAL, ALTA, URGENTE
- **Diagnóstico**: Inicial, observaciones del cliente y técnico
- **Detalles**: Servicios y repuestos utilizados
- **Costos**: Subtotales, descuentos, total automático

### 3. Control de Estados

El sistema gestiona automáticamente el ciclo de vida:

```
PENDIENTE
   ↓ (Iniciar trabajo)
EN_PROCESO
   ↓ (Finalizar trabajo + descontar inventario)
COMPLETADA
   ↓ (Entregar al cliente)
ENTREGADA
```

Estados adicionales:
- **ESPERANDO_REPUESTOS**: Cuando falta material
- **ESPERANDO_AUTORIZACION**: Cuando requiere OK del cliente
- **CANCELADA**: Orden cancelada por admin

### 4. Sistema de Autorización

Para trabajos que requieren aprobación del cliente:

1. Se marca la orden como `requiere_autorizacion = true`
2. El estado cambia a `ESPERANDO_AUTORIZACION`
3. Admin/Caja autoriza o rechaza
4. Si se autoriza, se puede iniciar el trabajo

### 5. Integración con Inventario

Al finalizar una orden:
- Se descuenta automáticamente del inventario los repuestos usados
- Se crea un movimiento de inventario de tipo SALIDA
- Se registra la referencia a la orden de trabajo
- Se verifica stock disponible antes de finalizar

---

## 📊 Estructura de Datos

### Tabla: servicios

```sql
id                          INT (PK)
codigo                      VARCHAR(50) UNIQUE
nombre                      VARCHAR(200)
descripcion                 TEXT
categoria                   ENUM
precio_base                 DECIMAL(10,2)
tiempo_estimado_minutos     INT
activo                      BOOLEAN
requiere_repuestos          BOOLEAN
```

### Tabla: ordenes_trabajo

```sql
id                      INT (PK)
numero_orden            VARCHAR(50) UNIQUE
vehiculo_id             INT (FK)
cliente_id              INT (FK)
tecnico_id              INT (FK) NULL
fecha_ingreso           DATETIME
fecha_promesa           DATETIME
fecha_inicio            DATETIME
fecha_finalizacion      DATETIME
fecha_entrega           DATETIME
estado                  ENUM
prioridad               ENUM
kilometraje             INT
diagnostico_inicial     TEXT
observaciones_cliente   TEXT
observaciones_tecnico   TEXT
observaciones_entrega   TEXT
subtotal_servicios      DECIMAL(10,2)
subtotal_repuestos      DECIMAL(10,2)
descuento               DECIMAL(10,2)
total                   DECIMAL(10,2)
requiere_autorizacion   BOOLEAN
autorizado              BOOLEAN
fecha_autorizacion      DATETIME
```

### Tabla: detalles_orden_trabajo

```sql
id                      INT (PK)
orden_trabajo_id        INT (FK)
servicio_id             INT (FK)
descripcion             VARCHAR(500)
precio_unitario         DECIMAL(10,2)
cantidad                INT
descuento               DECIMAL(10,2)
subtotal                DECIMAL(10,2)
tiempo_real_minutos     INT
observaciones           TEXT
```

### Tabla: detalles_repuesto_orden

```sql
id                  INT (PK)
orden_trabajo_id    INT (FK)
repuesto_id         INT (FK)
cantidad            INT
precio_unitario     DECIMAL(10,2)
descuento           DECIMAL(10,2)
subtotal            DECIMAL(10,2)
observaciones       TEXT
```

---

## 🔌 Endpoints API

### Servicios

| Método | Endpoint | Descripción | Roles |
|--------|----------|-------------|-------|
| POST | `/api/servicios/` | Crear servicio | ADMIN |
| GET | `/api/servicios/` | Listar servicios | Todos |
| GET | `/api/servicios/{id}` | Obtener servicio | Todos |
| PUT | `/api/servicios/{id}` | Actualizar servicio | ADMIN |
| DELETE | `/api/servicios/{id}` | Desactivar servicio | ADMIN |
| POST | `/api/servicios/{id}/activar` | Reactivar servicio | ADMIN |
| GET | `/api/servicios/categorias/listar` | Listar categorías | Todos |

### Órdenes de Trabajo

| Método | Endpoint | Descripción | Roles |
|--------|----------|-------------|-------|
| POST | `/api/ordenes-trabajo/` | Crear orden | ADMIN, CAJA, TECNICO |
| GET | `/api/ordenes-trabajo/` | Listar órdenes | Todos |
| GET | `/api/ordenes-trabajo/{id}` | Obtener orden | Todos |
| PUT | `/api/ordenes-trabajo/{id}` | Actualizar orden | ADMIN, CAJA, TECNICO |
| POST | `/api/ordenes-trabajo/{id}/iniciar` | Iniciar trabajo | ADMIN, TECNICO |
| POST | `/api/ordenes-trabajo/{id}/finalizar` | Finalizar trabajo | ADMIN, TECNICO |
| POST | `/api/ordenes-trabajo/{id}/entregar` | Entregar al cliente | ADMIN, CAJA |
| POST | `/api/ordenes-trabajo/{id}/cancelar` | Cancelar orden | ADMIN |
| POST | `/api/ordenes-trabajo/{id}/autorizar` | Autorizar orden | ADMIN, CAJA |
| POST | `/api/ordenes-trabajo/{id}/servicios` | Agregar servicio | ADMIN, TECNICO |
| DELETE | `/api/ordenes-trabajo/{id}/servicios/{detalle_id}` | Eliminar servicio | ADMIN, TECNICO |
| POST | `/api/ordenes-trabajo/{id}/repuestos` | Agregar repuesto | ADMIN, TECNICO |
| DELETE | `/api/ordenes-trabajo/{id}/repuestos/{detalle_id}` | Eliminar repuesto | ADMIN, TECNICO |
| GET | `/api/ordenes-trabajo/estados/listar` | Listar estados | Todos |
| GET | `/api/ordenes-trabajo/prioridades/listar` | Listar prioridades | Todos |
| GET | `/api/ordenes-trabajo/estadisticas/dashboard` | Dashboard | ADMIN, CAJA |

---

## 🔄 Flujo de Trabajo

### Flujo Normal de una Orden

```
1. CREACIÓN (ADMIN/CAJA/TECNICO)
   - Cliente llega con vehículo
   - Se crea orden con estado PENDIENTE
   - Se registra el diagnóstico inicial
   - Se agregan servicios y repuestos estimados
   ↓

2. ASIGNACIÓN (ADMIN)
   - Se asigna técnico
   - Se establece prioridad
   - Se define fecha promesa de entrega
   ↓

3. INICIO (TECNICO)
   - Técnico inicia el trabajo
   - Estado cambia a EN_PROCESO
   - Se registra fecha de inicio
   ↓

4. TRABAJO EN PROGRESO (TECNICO)
   - Se pueden agregar/quitar servicios
   - Se pueden agregar/quitar repuestos
   - Se registran observaciones
   ↓

5. FINALIZACIÓN (TECNICO)
   - Técnico finaliza el trabajo
   - Se descuenta inventario de repuestos
   - Estado cambia a COMPLETADA
   - Se registra fecha de finalización
   ↓

6. ENTREGA (ADMIN/CAJA)
   - Cliente recoge el vehículo
   - Se realizan cobros
   - Estado cambia a ENTREGADA
   - Se registra fecha de entrega
```

### Flujo con Autorización

```
1. CREACIÓN con requiere_autorizacion=true
   ↓
2. Estado: ESPERANDO_AUTORIZACION
   ↓
3. Cliente autoriza (ADMIN/CAJA)
   ↓
4. Estado: PENDIENTE
   ↓
5. Continúa flujo normal...
```

---

## 💡 Ejemplos de Uso

### Ejemplo 1: Crear una Orden Simple

```python
# POST /api/ordenes-trabajo/

{
  "vehiculo_id": 1,
  "cliente_id": 1,
  "tecnico_id": 2,
  "prioridad": "NORMAL",
  "kilometraje": 45000,
  "diagnostico_inicial": "Cliente reporta ruido en frenos",
  "observaciones_cliente": "Escucho rechinido al frenar",
  "servicios": [
    {
      "servicio_id": 8,  # Cambio de pastillas delanteras
      "cantidad": 1
    }
  ],
  "repuestos": [
    {
      "repuesto_id": 5,  # Pastillas de freno
      "cantidad": 1
    }
  ]
}
```

### Ejemplo 2: Iniciar Trabajo en una Orden

```python
# POST /api/ordenes-trabajo/1/iniciar

{
  "observaciones_inicio": "Iniciando revisión del sistema de frenos"
}
```

### Ejemplo 3: Agregar un Servicio Adicional

```python
# POST /api/ordenes-trabajo/1/servicios

{
  "servicio_id": 11,  # Purga de frenos
  "cantidad": 1,
  "observaciones": "Se detectó líquido de frenos viejo"
}
```

### Ejemplo 4: Finalizar Orden

```python
# POST /api/ordenes-trabajo/1/finalizar

{
  "observaciones_finalizacion": "Trabajo completado. Frenos funcionando correctamente."
}
```

### Ejemplo 5: Listar Órdenes con Filtros

```python
# GET /api/ordenes-trabajo/?estado=EN_PROCESO&prioridad=URGENTE&tecnico_id=2

# Respuesta: Lista de órdenes urgentes en proceso del técnico 2
```

---

## 🎨 Dashboard de Órdenes

El endpoint de estadísticas proporciona métricas en tiempo real:

```python
# GET /api/ordenes-trabajo/estadisticas/dashboard

{
  "ordenes_por_estado": [
    {"estado": "PENDIENTE", "total": 5},
    {"estado": "EN_PROCESO", "total": 8},
    {"estado": "COMPLETADA", "total": 3},
    {"estado": "ENTREGADA", "total": 12}
  ],
  "ordenes_hoy": 4,
  "total_facturado": 45600.00,
  "ordenes_urgentes": 2
}
```

---

## 🔒 Permisos por Rol

| Acción | ADMIN | CAJA | TECNICO | EMPLEADO |
|--------|-------|------|---------|----------|
| Crear orden | ✅ | ✅ | ✅ | ❌ |
| Ver órdenes | ✅ | ✅ | ✅ (propias) | ✅ |
| Actualizar orden | ✅ | ✅ | ✅ (propias) | ❌ |
| Iniciar orden | ✅ | ❌ | ✅ (propias) | ❌ |
| Finalizar orden | ✅ | ❌ | ✅ (propias) | ❌ |
| Entregar orden | ✅ | ✅ | ❌ | ❌ |
| Cancelar orden | ✅ | ❌ | ❌ | ❌ |
| Autorizar orden | ✅ | ✅ | ❌ | ❌ |
| Gestionar servicios | ✅ | ❌ | ❌ | ❌ |

---

## ⚠️ Consideraciones Importantes

### Inventario
- Los repuestos NO se descuentan al crear la orden
- El descuento ocurre al FINALIZAR la orden
- Verifica siempre el stock antes de finalizar
- Si falta stock, la orden no se puede finalizar

### Estados
- Solo se pueden cancelar órdenes no entregadas
- Las órdenes entregadas son inmutables
- Las órdenes pendientes pueden editarse libremente

### Autorización
- Si requiere_autorizacion=true, no se puede iniciar sin autorización
- La autorización la da ADMIN o CAJA
- Se registra fecha y hora de autorización

---

## 🚀 Próximas Mejoras

- [ ] Notificaciones por email/SMS al cliente
- [ ] Impresión de órdenes
- [ ] Firma digital del cliente
- [ ] Fotos del vehículo (antes/después)
- [ ] Historial de mantenimiento del vehículo
- [ ] Garantías de trabajos realizados
- [ ] Cotizaciones previas a órdenes
- [ ] Reportes avanzados de productividad

---

## 📞 Soporte

Para dudas o problemas con este módulo, contacta al desarrollador.

**Versión:** 1.0.0  
**Fecha:** Enero 2026  
**Estado:** ✅ Producción Ready
