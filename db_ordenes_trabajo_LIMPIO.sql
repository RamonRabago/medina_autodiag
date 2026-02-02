-- Script SQL ULTRA-LIMPIO para Módulo de Órdenes de Trabajo
-- MedinaAutoDiag - Sistema de Gestión de Taller Mecánico
-- Base de datos: medina_autodiag
-- Versión: LIMPIA - Sin Foreign Keys en CREATE TABLE

USE medina_autodiag;

-- ============================================
-- PASO 1: Crear tabla servicios (sin dependencias)
-- ============================================
CREATE TABLE IF NOT EXISTS servicios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    categoria ENUM(
        'MANTENIMIENTO',
        'REPARACION',
        'DIAGNOSTICO',
        'ELECTRICIDAD',
        'SUSPENSION',
        'FRENOS',
        'MOTOR',
        'TRANSMISION',
        'AIRE_ACONDICIONADO',
        'CARROCERIA',
        'OTROS'
    ) NOT NULL DEFAULT 'OTROS',
    precio_base DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    tiempo_estimado_minutos INT NOT NULL DEFAULT 60,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    requiere_repuestos BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_codigo (codigo),
    INDEX idx_nombre (nombre),
    INDEX idx_categoria (categoria),
    INDEX idx_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- PASO 2: Crear tabla ordenes_trabajo (sin FK)
-- ============================================
CREATE TABLE IF NOT EXISTS ordenes_trabajo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero_orden VARCHAR(50) NOT NULL UNIQUE,
    
    -- Relaciones (sin FK por ahora)
    vehiculo_id INT NOT NULL,
    cliente_id INT NOT NULL,
    tecnico_id INT NULL,
    
    -- Fechas
    fecha_ingreso DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_promesa DATETIME NULL,
    fecha_inicio DATETIME NULL,
    fecha_finalizacion DATETIME NULL,
    fecha_entrega DATETIME NULL,
    
    -- Estado y prioridad
    estado ENUM(
        'PENDIENTE',
        'EN_PROCESO',
        'ESPERANDO_REPUESTOS',
        'ESPERANDO_AUTORIZACION',
        'COMPLETADA',
        'ENTREGADA',
        'CANCELADA'
    ) NOT NULL DEFAULT 'PENDIENTE',
    prioridad ENUM('BAJA', 'NORMAL', 'ALTA', 'URGENTE') NOT NULL DEFAULT 'NORMAL',
    
    -- Información del vehículo y diagnóstico
    kilometraje INT NULL,
    diagnostico_inicial TEXT NULL,
    observaciones_cliente TEXT NULL,
    observaciones_tecnico TEXT NULL,
    observaciones_entrega TEXT NULL,
    
    -- Costos
    subtotal_servicios DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    subtotal_repuestos DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    descuento DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Control de autorización
    requiere_autorizacion BOOLEAN NOT NULL DEFAULT FALSE,
    autorizado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_autorizacion DATETIME NULL,
    
    -- Índices
    INDEX idx_numero_orden (numero_orden),
    INDEX idx_vehiculo (vehiculo_id),
    INDEX idx_cliente (cliente_id),
    INDEX idx_tecnico (tecnico_id),
    INDEX idx_estado (estado),
    INDEX idx_prioridad (prioridad),
    INDEX idx_fecha_ingreso (fecha_ingreso),
    INDEX idx_fecha_promesa (fecha_promesa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- PASO 3: Crear tabla detalles_orden_trabajo (sin FK)
-- ============================================
CREATE TABLE IF NOT EXISTS detalles_orden_trabajo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    orden_trabajo_id INT NOT NULL,
    servicio_id INT NOT NULL,
    
    descripcion VARCHAR(500) NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    cantidad INT NOT NULL DEFAULT 1,
    descuento DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    
    tiempo_real_minutos INT NULL,
    observaciones TEXT NULL,
    
    INDEX idx_orden (orden_trabajo_id),
    INDEX idx_servicio (servicio_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- PASO 4: Crear tabla detalles_repuesto_orden (sin FK)
-- ============================================
CREATE TABLE IF NOT EXISTS detalles_repuesto_orden (
    id INT AUTO_INCREMENT PRIMARY KEY,
    orden_trabajo_id INT NOT NULL,
    repuesto_id INT NOT NULL,
    
    cantidad INT NOT NULL DEFAULT 1,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    descuento DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    
    observaciones TEXT NULL,
    
    INDEX idx_orden (orden_trabajo_id),
    INDEX idx_repuesto (repuesto_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- PASO 5: Agregar Foreign Keys DESPUÉS de crear tablas
-- ============================================

-- FK para ordenes_trabajo
ALTER TABLE ordenes_trabajo 
ADD CONSTRAINT fk_orden_vehiculo 
FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id) ON DELETE RESTRICT;

ALTER TABLE ordenes_trabajo 
ADD CONSTRAINT fk_orden_cliente 
FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT;

ALTER TABLE ordenes_trabajo 
ADD CONSTRAINT fk_orden_tecnico 
FOREIGN KEY (tecnico_id) REFERENCES usuarios(id) ON DELETE SET NULL;

-- FK para detalles_orden_trabajo
ALTER TABLE detalles_orden_trabajo 
ADD CONSTRAINT fk_detalle_servicio_orden 
FOREIGN KEY (orden_trabajo_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE;

ALTER TABLE detalles_orden_trabajo 
ADD CONSTRAINT fk_detalle_servicio_servicio 
FOREIGN KEY (servicio_id) REFERENCES servicios(id) ON DELETE RESTRICT;

-- FK para detalles_repuesto_orden
ALTER TABLE detalles_repuesto_orden 
ADD CONSTRAINT fk_detalle_repuesto_orden 
FOREIGN KEY (orden_trabajo_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE;

ALTER TABLE detalles_repuesto_orden 
ADD CONSTRAINT fk_detalle_repuesto_repuesto 
FOREIGN KEY (repuesto_id) REFERENCES repuestos(id) ON DELETE RESTRICT;

-- ============================================
-- VERIFICACIÓN
-- ============================================
SELECT '✅ Script ejecutado exitosamente!' as Status;
SELECT '' as '';
SELECT 'Tablas creadas:' as Resumen;
SELECT '  1. servicios' as '';
SELECT '  2. ordenes_trabajo' as '';
SELECT '  3. detalles_orden_trabajo' as '';
SELECT '  4. detalles_repuesto_orden' as '';
SELECT '' as '';
SELECT '  7 Foreign Keys agregadas' as '';
SELECT '' as '';
SELECT 'Siguiente paso:' as '';
SELECT '  python poblar_ordenes_trabajo.py' as '';
