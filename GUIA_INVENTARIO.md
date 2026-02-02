# 📦 Sistema de Inventario de Repuestos - Guía de Uso

## 🎯 Descripción General

El sistema de inventario permite gestionar el stock de repuestos del taller, incluyendo:
- Catálogo de repuestos con control de stock
- Movimientos de entrada/salida
- Alertas automáticas de stock bajo
- Reportes y estadísticas
- Gestión de proveedores y categorías

---

## 🚀 Instalación y Configuración

### 1. Aplicar Cambios a la Base de Datos

```bash
# Ejecutar el script SQL para crear las tablas
mysql -u root -p medinaautodiag < db_inventario.sql
```

### 2. Poblar con Datos de Ejemplo (Opcional)

```bash
# Ejecutar el script de población
python poblar_inventario.py
```

---

## 📚 Endpoints Disponibles

### 🏷️ Categorías de Repuestos

#### Crear Categoría
```http
POST /categorias-repuestos/
Authorization: Bearer {token}
Content-Type: application/json

{
  "nombre": "Motor",
  "descripcion": "Repuestos relacionados con el motor"
}
```

#### Listar Categorías
```http
GET /categorias-repuestos/
Authorization: Bearer {token}
```

#### Obtener Categoría
```http
GET /categorias-repuestos/{id_categoria}
Authorization: Bearer {token}
```

#### Actualizar Categoría
```http
PUT /categorias-repuestos/{id_categoria}
Authorization: Bearer {token}
Content-Type: application/json

{
  "nombre": "Motor y Transmisión",
  "descripcion": "Actualizado..."
}
```

#### Eliminar Categoría
```http
DELETE /categorias-repuestos/{id_categoria}
Authorization: Bearer {token}
```

---

### 🏢 Proveedores

#### Crear Proveedor
```http
POST /proveedores/
Authorization: Bearer {token}
Content-Type: application/json

{
  "nombre": "AutoPartes México SA",
  "contacto": "Juan Pérez",
  "telefono": "8181234567",
  "email": "ventas@autopartes.mx",
  "direccion": "Av. Reforma 123",
  "rfc": "APM970101ABC",
  "activo": true
}
```

#### Listar Proveedores
```http
GET /proveedores/?activo=true
Authorization: Bearer {token}
```

#### Actualizar Proveedor
```http
PUT /proveedores/{id_proveedor}
Authorization: Bearer {token}
Content-Type: application/json

{
  "telefono": "8181234999",
  "email": "nuevo@email.com"
}
```

#### Desactivar Proveedor
```http
DELETE /proveedores/{id_proveedor}
Authorization: Bearer {token}
```

#### Reactivar Proveedor
```http
POST /proveedores/{id_proveedor}/reactivar
Authorization: Bearer {token}
```

---

### 🔧 Repuestos

#### Crear Repuesto
```http
POST /repuestos/
Authorization: Bearer {token}
Content-Type: application/json

{
  "codigo": "MOT-001",
  "nombre": "Aceite Motor 10W-40",
  "descripcion": "Aceite sintético para motor",
  "id_categoria": 1,
  "id_proveedor": 1,
  "stock_actual": 20,
  "stock_minimo": 10,
  "stock_maximo": 50,
  "ubicacion": "Estante A-1",
  "precio_compra": 85.00,
  "precio_venta": 120.00,
  "marca": "Castrol",
  "modelo_compatible": "Universal",
  "unidad_medida": "LT"
}
```

#### Listar Repuestos con Filtros
```http
# Todos los repuestos activos
GET /repuestos/?activo=true

# Repuestos de una categoría
GET /repuestos/?id_categoria=1

# Repuestos con stock bajo
GET /repuestos/?stock_bajo=true

# Buscar por código, nombre o marca
GET /repuestos/?buscar=aceite
```

#### Buscar por Código Exacto
```http
GET /repuestos/buscar-codigo/MOT-001
Authorization: Bearer {token}
```

#### Obtener Repuesto
```http
GET /repuestos/{id_repuesto}
Authorization: Bearer {token}
```

#### Actualizar Repuesto
```http
PUT /repuestos/{id_repuesto}
Authorization: Bearer {token}
Content-Type: application/json

{
  "precio_compra": 90.00,
  "precio_venta": 130.00,
  "stock_minimo": 12
}
```

**NOTA:** El stock NO se modifica con este endpoint, usa los movimientos de inventario.

---

### 📊 Movimientos de Inventario

#### Registrar Entrada (Compra)
```http
POST /inventario/movimientos/
Authorization: Bearer {token}
Content-Type: application/json

{
  "id_repuesto": 1,
  "tipo_movimiento": "ENTRADA",
  "cantidad": 20,
  "precio_unitario": 85.00,
  "referencia": "FACT-12345",
  "motivo": "Compra de inventario"
}
```

#### Registrar Salida (Venta/Uso)
```http
POST /inventario/movimientos/
Authorization: Bearer {token}
Content-Type: application/json

{
  "id_repuesto": 1,
  "tipo_movimiento": "SALIDA",
  "cantidad": 5,
  "precio_unitario": 120.00,
  "referencia": "VTA-001",
  "motivo": "Venta al cliente",
  "id_venta": 123
}
```

#### Registrar Merma
```http
POST /inventario/movimientos/
Authorization: Bearer {token}
Content-Type: application/json

{
  "id_repuesto": 1,
  "tipo_movimiento": "MERMA",
  "cantidad": 2,
  "motivo": "Producto dañado en almacén"
}
```

#### Ajustar Inventario
```http
POST /inventario/movimientos/ajuste
Authorization: Bearer {token}
Content-Type: application/json

{
  "id_repuesto": 1,
  "stock_nuevo": 25,
  "motivo": "Ajuste por inventario físico - se encontraron 5 unidades adicionales",
  "referencia": "INV-2026-01"
}
```

#### Listar Movimientos con Filtros
```http
# Todos los movimientos
GET /inventario/movimientos/

# Movimientos de un repuesto específico
GET /inventario/movimientos/?id_repuesto=1

# Solo entradas
GET /inventario/movimientos/?tipo_movimiento=ENTRADA

# Por rango de fechas
GET /inventario/movimientos/?fecha_desde=2026-01-01&fecha_hasta=2026-01-31

# Por usuario
GET /inventario/movimientos/?id_usuario=1
```

#### Historial de un Repuesto
```http
GET /inventario/movimientos/repuesto/{id_repuesto}?limite=50
Authorization: Bearer {token}
```

#### Estadísticas de Movimientos
```http
GET /inventario/movimientos/estadisticas/resumen
Authorization: Bearer {token}
```

---

### 🚨 Alertas de Inventario

#### Listar Alertas Activas
```http
GET /inventario/alertas?activas_solo=true
Authorization: Bearer {token}
```

#### Filtrar por Tipo
```http
GET /inventario/alertas?tipo_alerta=STOCK_CRITICO
Authorization: Bearer {token}
```

Tipos de alerta:
- `STOCK_BAJO`: Stock cerca del mínimo
- `STOCK_CRITICO`: Stock por debajo del mínimo
- `SIN_STOCK`: Stock en cero
- `SIN_MOVIMIENTO`: Sin movimientos en X días
- `SOBRE_STOCK`: Stock superior al máximo

#### Resumen de Alertas
```http
GET /inventario/alertas/resumen
Authorization: Bearer {token}
```

Respuesta:
```json
{
  "total_alertas": 5,
  "alertas_criticas": 2,
  "alertas_stock_bajo": 2,
  "alertas_sin_stock": 1,
  "alertas_sin_movimiento": 0,
  "alertas_sobre_stock": 0
}
```

#### Resolver Alerta Manualmente
```http
POST /inventario/alertas/{id_alerta}/resolver
Authorization: Bearer {token}
```

#### Verificar Productos Sin Movimiento
```http
POST /inventario/alertas/verificar-sin-movimiento?dias=90
Authorization: Bearer {token}
```

---

### 📈 Reportes

#### Valor del Inventario
```http
GET /inventario/reportes/valor-inventario
Authorization: Bearer {token}
```

Respuesta:
```json
{
  "fecha_reporte": "2026-01-26T...",
  "valor_compra": 45500.00,
  "valor_venta": 65200.00,
  "utilidad_potencial": 19700.00,
  "total_productos": 50,
  "total_unidades": 350
}
```

#### Productos Más Vendidos
```http
GET /inventario/reportes/productos-mas-vendidos?limite=10
Authorization: Bearer {token}
```

#### Reporte de Stock Bajo
```http
GET /inventario/reportes/stock-bajo
Authorization: Bearer {token}
```

#### Rotación de Inventario
```http
GET /inventario/reportes/rotacion-inventario?dias=30
Authorization: Bearer {token}
```

#### Dashboard Completo
```http
GET /inventario/reportes/dashboard
Authorization: Bearer {token}
```

---

## 🔐 Permisos por Rol

| Acción | ADMIN | CAJA | TECNICO | EMPLEADO |
|--------|-------|------|---------|----------|
| Ver repuestos | ✅ | ✅ | ✅ | ✅ |
| Crear repuestos | ✅ | ✅ | ❌ | ❌ |
| Modificar repuestos | ✅ | ✅ | ❌ | ❌ |
| Eliminar repuestos | ✅ | ❌ | ❌ | ❌ |
| Registrar movimientos | ✅ | ✅ | ✅ | ❌ |
| Ajustar inventario | ✅ | ✅ | ❌ | ❌ |
| Ver reportes | ✅ | ✅ | ❌ | ❌ |
| Gestionar proveedores | ✅ | ✅ | ❌ | ❌ |
| Gestionar categorías | ✅ | ✅ | ❌ | ❌ |
| Resolver alertas | ✅ | ✅ | ❌ | ❌ |

---

## 💡 Casos de Uso Comunes

### Caso 1: Recibir Compra de Proveedor

1. Recibir mercancía del proveedor
2. Registrar entrada para cada producto:
```http
POST /inventario/movimientos/
{
  "id_repuesto": 5,
  "tipo_movimiento": "ENTRADA",
  "cantidad": 50,
  "precio_unitario": 45.00,
  "referencia": "FACT-PROV-123",
  "motivo": "Compra semanal proveedor AutoPartes"
}
```

### Caso 2: Venta de Repuesto

1. Cliente compra un producto
2. Registrar la venta en el sistema
3. El sistema automáticamente registra la salida del inventario
4. Si el stock queda bajo, se crea una alerta automática

### Caso 3: Inventario Físico

1. Contar físicamente el stock
2. Comparar con el sistema
3. Ajustar las diferencias:
```http
POST /inventario/movimientos/ajuste
{
  "id_repuesto": 3,
  "stock_nuevo": 12,
  "motivo": "Inventario físico mensual - se encontró diferencia de 2 unidades",
  "referencia": "INV-FISICO-2026-01"
}
```

### Caso 4: Producto Dañado

```http
POST /inventario/movimientos/
{
  "id_repuesto": 7,
  "tipo_movimiento": "MERMA",
  "cantidad": 1,
  "motivo": "Producto dañado durante almacenamiento - empaque roto"
}
```

---

## 🔔 Alertas Automáticas

El sistema genera alertas automáticamente en los siguientes casos:

1. **Stock Bajo**: Cuando el stock actual es ≤ stock_mínimo * 1.2
2. **Stock Crítico**: Cuando el stock actual < stock_mínimo
3. **Sin Stock**: Cuando el stock actual = 0
4. **Sobre-stock**: Cuando el stock actual > stock_máximo

Las alertas se crean/actualizan automáticamente al registrar movimientos.

---

## 📝 Notas Importantes

1. **Stock Negativo**: El sistema NO permite stock negativo. Si intentas una salida mayor al stock disponible, recibirás un error.

2. **Modificación de Stock**: El stock SOLO se modifica mediante movimientos de inventario, no directamente en el endpoint de actualización de repuestos.

3. **Códigos Únicos**: Cada repuesto debe tener un código único.

4. **Precio de Venta**: Debe ser mayor o igual al precio de compra.

5. **Historial**: Todos los movimientos quedan registrados permanentemente con fecha, usuario, stock anterior y nuevo.

6. **Proveedores y Categorías**: Se pueden desactivar pero no eliminar si tienen repuestos asociados.

---

## 🆘 Problemas Comunes

### Error: "Stock insuficiente"
- Verifica el stock actual del repuesto
- La cantidad solicitada es mayor al disponible
- Usa el endpoint de ajuste si necesitas corregir el stock

### Error: "Repuesto inactivo"
- El repuesto está marcado como inactivo
- Reactívalo o usa otro repuesto

### Error: "Código duplicado"
- Ya existe un repuesto con ese código
- Usa un código diferente

---

## 📊 Consultas SQL Útiles

```sql
-- Ver repuestos con stock bajo
SELECT * FROM v_repuestos_stock_bajo;

-- Ver valor total del inventario
SELECT * FROM v_valor_inventario;

-- Movimientos del día
SELECT * FROM movimientos_inventario 
WHERE DATE(fecha_movimiento) = CURDATE();
```

---

**¿Necesitas ayuda?** Consulta la documentación Swagger en http://localhost:8000/docs
