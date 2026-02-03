-- Agregar columna requiere_factura a ventas
-- Ejecutar una sola vez: mysql -u root -p medina_autodiag < scripts/agregar_requiere_factura.sql
ALTER TABLE ventas ADD COLUMN requiere_factura TINYINT(1) DEFAULT 0 NULL;
