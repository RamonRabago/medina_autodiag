-- ========================================
-- SCRIPT DE CREACIÓN DE TABLAS DE INVENTARIO
-- MedinaAutoDiag - Sistema de Inventario de Repuestos
-- ========================================

-- Tabla: categorias_repuestos
CREATE TABLE IF NOT EXISTS categorias_repuestos (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla: proveedores
CREATE TABLE IF NOT EXISTS proveedores (
    id_proveedor INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    contacto VARCHAR(100),
    telefono VARCHAR(20),
    email VARCHAR(100),
    direccion TEXT,
    rfc VARCHAR(13),
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_nombre (nombre),
    INDEX idx_activo (activo),
    INDEX idx_rfc (rfc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla: repuestos
CREATE TABLE IF NOT EXISTS repuestos (
    id_repuesto INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    id_categoria INT,
    id_proveedor INT,
    stock_actual INT NOT NULL DEFAULT 0,
    stock_minimo INT NOT NULL DEFAULT 5,
    stock_maximo INT NOT NULL DEFAULT 100,
    ubicacion VARCHAR(50),
    precio_compra DECIMAL(10, 2) NOT NULL,
    precio_venta DECIMAL(10, 2) NOT NULL,
    marca VARCHAR(100),
    modelo_compatible VARCHAR(200),
    unidad_medida VARCHAR(20) DEFAULT 'PZA',
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (id_categoria) REFERENCES categorias_repuestos(id_categoria) ON DELETE SET NULL,
    FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor) ON DELETE SET NULL,
    
    INDEX idx_codigo (codigo),
    INDEX idx_nombre (nombre),
    INDEX idx_categoria (id_categoria),
    INDEX idx_proveedor (id_proveedor),
    INDEX idx_activo (activo),
    INDEX idx_stock (stock_actual)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla: movimientos_inventario
CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id_movimiento INT AUTO_INCREMENT PRIMARY KEY,
    id_repuesto INT NOT NULL,
    tipo_movimiento ENUM('ENTRADA', 'SALIDA', 'AJUSTE+', 'AJUSTE-', 'MERMA') NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10, 2),
    costo_total DECIMAL(10, 2),
    stock_anterior INT NOT NULL,
    stock_nuevo INT NOT NULL,
    referencia VARCHAR(100),
    motivo TEXT,
    id_venta INT,
    id_usuario INT,
    fecha_movimiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (id_repuesto) REFERENCES repuestos(id_repuesto) ON DELETE RESTRICT,
    FOREIGN KEY (id_venta) REFERENCES ventas(id_venta) ON DELETE SET NULL,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
    
    INDEX idx_repuesto (id_repuesto),
    INDEX idx_tipo (tipo_movimiento),
    INDEX idx_fecha (fecha_movimiento),
    INDEX idx_venta (id_venta),
    INDEX idx_usuario (id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla: alertas_inventario
CREATE TABLE IF NOT EXISTS alertas_inventario (
    id_alerta INT AUTO_INCREMENT PRIMARY KEY,
    id_repuesto INT NOT NULL,
    tipo_alerta ENUM('STOCK_BAJO', 'STOCK_CRITICO', 'SIN_STOCK', 'SIN_MOVIMIENTO', 'SOBRE_STOCK') NOT NULL,
    mensaje TEXT NOT NULL,
    stock_actual INT,
    stock_minimo INT,
    stock_maximo INT,
    activa BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion TIMESTAMP NULL,
    resuelto_por INT,
    
    FOREIGN KEY (id_repuesto) REFERENCES repuestos(id_repuesto) ON DELETE CASCADE,
    FOREIGN KEY (resuelto_por) REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
    
    INDEX idx_repuesto (id_repuesto),
    INDEX idx_tipo (tipo_alerta),
    INDEX idx_activa (activa),
    INDEX idx_fecha_creacion (fecha_creacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- DATOS INICIALES DE EJEMPLO
-- ========================================

-- Categorías de repuestos
INSERT INTO categorias_repuestos (nombre, descripcion) VALUES
('Motor', 'Repuestos relacionados con el motor'),
('Frenos', 'Sistema de frenos y componentes'),
('Suspensión', 'Amortiguadores, resortes y componentes de suspensión'),
('Eléctrico', 'Componentes eléctricos y electrónicos'),
('Filtros', 'Filtros de aceite, aire, combustible, etc.'),
('Transmisión', 'Componentes de transmisión y embrague'),
('Carrocería', 'Faros, espejos y componentes de carrocería'),
('Lubricantes', 'Aceites, grasas y lubricantes'),
('Llantas', 'Llantas y neumáticos'),
('Accesorios', 'Accesorios varios')
ON DUPLICATE KEY UPDATE nombre=nombre;

-- Proveedor de ejemplo
INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, rfc, activo) VALUES
('AutoPartes México SA', 'Juan Pérez', '8181234567', 'ventas@autopartes.mx', 'Av. Reforma 123, Monterrey, NL', 'APM970101ABC', TRUE),
('Distribuidora Nacional', 'María García', '5551234567', 'contacto@disnacional.com', 'Insurgentes 456, CDMX', 'DIN850215XYZ', TRUE)
ON DUPLICATE KEY UPDATE nombre=nombre;

-- ========================================
-- TRIGGERS ÚTILES
-- ========================================

-- Trigger para validar que el stock no sea negativo
DELIMITER //
CREATE TRIGGER before_repuesto_update
BEFORE UPDATE ON repuestos
FOR EACH ROW
BEGIN
    IF NEW.stock_actual < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'El stock no puede ser negativo';
    END IF;
END//
DELIMITER ;

-- ========================================
-- VISTAS ÚTILES
-- ========================================

-- Vista: Repuestos con stock bajo
CREATE OR REPLACE VIEW v_repuestos_stock_bajo AS
SELECT 
    r.id_repuesto,
    r.codigo,
    r.nombre,
    r.stock_actual,
    r.stock_minimo,
    r.stock_maximo,
    r.precio_compra,
    r.precio_venta,
    c.nombre AS categoria,
    p.nombre AS proveedor,
    (r.stock_minimo - r.stock_actual) AS unidades_faltantes,
    ((r.stock_minimo - r.stock_actual) * r.precio_compra) AS costo_reposicion
FROM repuestos r
LEFT JOIN categorias_repuestos c ON r.id_categoria = c.id_categoria
LEFT JOIN proveedores p ON r.id_proveedor = p.id_proveedor
WHERE r.activo = TRUE 
  AND r.stock_actual <= r.stock_minimo
ORDER BY r.stock_actual ASC;

-- Vista: Valor total del inventario
CREATE OR REPLACE VIEW v_valor_inventario AS
SELECT 
    COUNT(*) AS total_productos,
    SUM(stock_actual) AS total_unidades,
    SUM(stock_actual * precio_compra) AS valor_compra,
    SUM(stock_actual * precio_venta) AS valor_venta,
    SUM(stock_actual * precio_venta) - SUM(stock_actual * precio_compra) AS utilidad_potencial
FROM repuestos
WHERE activo = TRUE;

-- ========================================
-- CONSULTAS ÚTILES DOCUMENTADAS
-- ========================================

/*
-- Productos más vendidos (últimos 30 días)
SELECT 
    r.codigo,
    r.nombre,
    SUM(m.cantidad) AS total_vendido,
    SUM(m.costo_total) AS valor_total
FROM repuestos r
INNER JOIN movimientos_inventario m ON r.id_repuesto = m.id_repuesto
WHERE m.tipo_movimiento = 'SALIDA'
  AND m.fecha_movimiento >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY r.id_repuesto
ORDER BY total_vendido DESC
LIMIT 10;

-- Alertas activas por tipo
SELECT 
    tipo_alerta,
    COUNT(*) AS cantidad,
    GROUP_CONCAT(CONCAT(r.codigo, ' - ', r.nombre) SEPARATOR ', ') AS productos
FROM alertas_inventario a
INNER JOIN repuestos r ON a.id_repuesto = r.id_repuesto
WHERE a.activa = TRUE
GROUP BY tipo_alerta;

-- Movimientos del día
SELECT 
    m.tipo_movimiento,
    r.codigo,
    r.nombre,
    m.cantidad,
    m.stock_anterior,
    m.stock_nuevo,
    u.nombre AS usuario,
    m.fecha_movimiento
FROM movimientos_inventario m
INNER JOIN repuestos r ON m.id_repuesto = r.id_repuesto
LEFT JOIN usuarios u ON m.id_usuario = u.id_usuario
WHERE DATE(m.fecha_movimiento) = CURDATE()
ORDER BY m.fecha_movimiento DESC;
*/
