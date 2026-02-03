-- Agregar columna motivo_cancelacion a ventas
-- Ejecutar: mysql -u root -p medina_autodiag < scripts/agregar_motivo_cancelacion.sql
ALTER TABLE ventas ADD COLUMN motivo_cancelacion TEXT NULL;
