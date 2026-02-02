# 🔧 MÓDULO DE ÓRDENES DE TRABAJO - Instalación Rápida

## 📦 Contenido del Paquete

Este ZIP contiene todo lo necesario para agregar el módulo de Órdenes de Trabajo a tu sistema MedinaAutoDiag.

```
ordenes_trabajo_module/
├── 📄 README.md                               (Este archivo)
├── 📄 GUIA_ORDENES_TRABAJO.md                 (Documentación completa)
├── 📄 ACTUALIZACIONES_MODELOS_EXISTENTES.py   (Instrucciones de actualización)
│
├── 🗄️  db_ordenes_trabajo.sql                 (Script SQL - tablas y triggers)
├── 🐍 poblar_ordenes_trabajo.py               (Script de datos de ejemplo)
│
├── 📁 models/
│   ├── servicio.py                            → Copiar a app/models/
│   ├── orden_trabajo.py                       → Copiar a app/models/
│   └── detalle_orden.py                       → Copiar a app/models/
│
├── 📁 schemas/
│   ├── servicio_schema.py                     → Renombrar a servicio.py → app/schemas/
│   └── orden_trabajo_schema.py                → Renombrar a orden_trabajo.py → app/schemas/
│
└── 📁 routers/
    ├── servicios.py                           → Copiar a app/routers/
    ├── ordenes_trabajo_1.py                   ┐
    ├── ordenes_trabajo_2.py                   ├─→ Combinar en app/routers/ordenes_trabajo.py
    └── ordenes_trabajo_3.py                   ┘
```

---

## ⚡ Instalación en 7 Pasos

### ✅ **PASO 1: Copiar Modelos**

```bash
# Copiar los 3 archivos de modelos
cp models/servicio.py          TU_PROYECTO/app/models/
cp models/orden_trabajo.py     TU_PROYECTO/app/models/
cp models/detalle_orden.py     TU_PROYECTO/app/models/
```

### ✅ **PASO 2: Copiar Schemas**

```bash
# Renombrar y copiar schemas
cp schemas/servicio_schema.py         TU_PROYECTO/app/schemas/servicio.py
cp schemas/orden_trabajo_schema.py    TU_PROYECTO/app/schemas/orden_trabajo.py
```

### ✅ **PASO 3: Combinar y Copiar Router de Órdenes**

**Opción A - Manual:**
1. Crea un nuevo archivo: `TU_PROYECTO/app/routers/ordenes_trabajo.py`
2. Copia el contenido de `ordenes_trabajo_1.py`
3. Agrega el contenido de `ordenes_trabajo_2.py` (sin los imports duplicados)
4. Agrega el contenido de `ordenes_trabajo_3.py` (sin los imports duplicados)

**Opción B - Comando (Linux/Mac):**
```bash
cat routers/ordenes_trabajo_1.py routers/ordenes_trabajo_2.py routers/ordenes_trabajo_3.py > TU_PROYECTO/app/routers/ordenes_trabajo.py
```

### ✅ **PASO 4: Copiar Router de Servicios**

```bash
cp routers/servicios.py    TU_PROYECTO/app/routers/
```

### ✅ **PASO 5: Actualizar Modelos Existentes**

Abre `ACTUALIZACIONES_MODELOS_EXISTENTES.py` y sigue las instrucciones para actualizar:

- ✏️ `app/models/vehiculo.py` - Agregar relación con órdenes
- ✏️ `app/models/cliente.py` - Agregar relación con órdenes
- ✏️ `app/models/usuario.py` - Agregar relación con órdenes
- ✏️ `app/models/repuesto.py` - Agregar relación con detalles de orden
- ✏️ `app/models/__init__.py` - Agregar imports nuevos
- ✏️ `app/routers/main.py` (o `app/main.py`) - Incluir nuevos routers

### ✅ **PASO 6: Ejecutar Script SQL**

```bash
mysql -u root -p medinaautodiag < db_ordenes_trabajo.sql
```

O desde MySQL Workbench/PHPMyAdmin, ejecuta el contenido del archivo.

### ✅ **PASO 7: Poblar Datos de Ejemplo**

```bash
# Edita el archivo si necesitas cambiar credenciales de DB
python poblar_ordenes_trabajo.py
```

---

## 🎯 Verificación de Instalación

### 1. Reinicia la Aplicación

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Verifica en Swagger

Abre: http://127.0.0.1:8000/docs

Deberías ver estos nuevos grupos de endpoints:
- **Servicios** (7 endpoints)
- **Órdenes de Trabajo** (17 endpoints)

### 3. Prueba Rápida

```bash
# Listar servicios
curl http://127.0.0.1:8000/api/servicios/

# Listar órdenes
curl -H "Authorization: Bearer TU_TOKEN" http://127.0.0.1:8000/api/ordenes-trabajo/
```

---

## 📊 Datos Creados

Después de ejecutar `poblar_ordenes_trabajo.py`:

- ✅ **30 Servicios** en el catálogo (cambio de aceite, alineación, frenos, etc.)
- ✅ **10 Órdenes de Trabajo** de ejemplo con diferentes estados
- ✅ Relaciones con tus clientes, vehículos y técnicos existentes

---

## 🔍 Estructura de Tablas Creadas

El script SQL crea:

1. **`servicios`** - Catálogo de servicios del taller
2. **`ordenes_trabajo`** - Órdenes de trabajo principales
3. **`detalles_orden_trabajo`** - Servicios aplicados en cada orden
4. **`detalles_repuesto_orden`** - Repuestos usados en cada orden

Más **8 triggers** para cálculo automático de totales.

---

## 🎨 Características Principales

### ✨ Gestión de Servicios
- Catálogo completo de servicios del taller
- 11 categorías predefinidas
- Precios y tiempos estimados
- Control de activación/desactivación

### ✨ Órdenes de Trabajo Completas
- Número único auto-generado (OT-YYYYMMDD-NNNN)
- 7 estados posibles: PENDIENTE → EN_PROCESO → COMPLETADA → ENTREGADA
- 4 niveles de prioridad
- Asignación de técnicos
- Sistema de autorización para trabajos especiales

### ✨ Integración Total
- Vinculación con clientes y vehículos
- Descuento automático de inventario al finalizar
- Registro de movimientos de repuestos
- Cálculo automático de totales

### ✨ Dashboard y Estadísticas
- Órdenes por estado
- Órdenes del día
- Total facturado
- Órdenes urgentes pendientes

---

## 🔐 Permisos por Rol

| Acción | ADMIN | CAJA | TECNICO | EMPLEADO |
|--------|:-----:|:----:|:-------:|:--------:|
| Crear orden | ✅ | ✅ | ✅ | ❌ |
| Ver todas las órdenes | ✅ | ✅ | ❌ | ✅ |
| Ver órdenes propias | ✅ | ✅ | ✅ | ✅ |
| Iniciar/Finalizar | ✅ | ❌ | ✅ | ❌ |
| Entregar al cliente | ✅ | ✅ | ❌ | ❌ |
| Cancelar | ✅ | ❌ | ❌ | ❌ |
| Gestionar servicios | ✅ | ❌ | ❌ | ❌ |

---

## 📚 Documentación Completa

Para información detallada sobre uso, endpoints, ejemplos y flujos de trabajo, consulta:

📖 **GUIA_ORDENES_TRABAJO.md**

---

## ⚠️ Consideraciones Importantes

### Inventario
- Los repuestos se descuentan al **FINALIZAR** la orden, no al crearla
- Verifica stock disponible antes de finalizar
- Los movimientos de inventario se registran automáticamente

### Estados de Orden
- Las órdenes ENTREGADAS son inmutables
- Solo ADMIN puede cancelar órdenes
- Las órdenes con autorización requerida deben ser aprobadas antes de iniciar

### Integración
- Requiere módulos de: clientes, vehículos, usuarios, inventario (repuestos)
- Los técnicos deben tener rol "TECNICO" en la tabla usuarios

---

## 🐛 Solución de Problemas

### Error: "Servicio no encontrado"
- Verifica que ejecutaste `poblar_ordenes_trabajo.py`
- Revisa que la tabla `servicios` tenga datos

### Error: "Stock insuficiente"
- Asegúrate de tener repuestos con stock > 0
- Ejecuta el script `poblar_inventario.py` si no tienes repuestos

### Error: "Técnico no encontrado"
- Crea al menos un usuario con rol "TECNICO"
- Verifica el ID del técnico en la tabla usuarios

### Error al importar modelos
- Verifica que actualizaste `app/models/__init__.py`
- Reinicia la aplicación FastAPI

---

## 🚀 Próximos Pasos

Una vez instalado, puedes:

1. **Crear servicios personalizados** para tu taller
2. **Generar órdenes reales** con tus clientes y vehículos
3. **Asignar técnicos** a las órdenes
4. **Monitorear el progreso** en tiempo real
5. **Integrar con tu sistema de pagos** (módulo de ventas existente)

---

## 📞 Soporte

Si tienes problemas con la instalación:
1. Revisa que todos los archivos estén en su lugar
2. Verifica los logs de la aplicación
3. Consulta la guía completa en `GUIA_ORDENES_TRABAJO.md`

---

## ✅ Checklist de Instalación

- [ ] Archivos de models copiados (3 archivos)
- [ ] Archivos de schemas copiados y renombrados (2 archivos)
- [ ] Router de servicios copiado
- [ ] Router de órdenes combinado y copiado
- [ ] Modelos existentes actualizados (vehiculo, cliente, usuario, repuesto)
- [ ] `__init__.py` actualizado con imports
- [ ] `main.py` actualizado con include_router
- [ ] Script SQL ejecutado en MySQL
- [ ] Script de población ejecutado
- [ ] Aplicación reiniciada
- [ ] Endpoints verificados en Swagger
- [ ] Prueba de creación de orden exitosa

---

**¡Listo para usar! 🎉**

Tu sistema ahora cuenta con un módulo profesional de gestión de órdenes de trabajo que integra todos los componentes del taller.

**Versión:** 1.0.0  
**Fecha:** Enero 2026  
**Compatibilidad:** MedinaAutoDiag v1.0.0+
