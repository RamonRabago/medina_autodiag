-- Ejecutar en Aiven si el stock se redondea a enteros (ej: 37.6 → 38).
-- La migración l2m3n4o5p6q7 puede no haberse aplicado si el usuario no tiene permiso ALTER.
-- Usa el usuario admin (avnadmin) en MySQL Workbench / Aiven Console.
--
-- 1. Conecta a defaultdb (o tu base de datos)
-- 2. Ejecuta:

USE defaultdb;

-- Repuestos: permitir decimales (ej: 37.6 L de aceite)
ALTER TABLE repuestos MODIFY COLUMN stock_actual DECIMAL(10,3) NOT NULL DEFAULT 0;
ALTER TABLE repuestos MODIFY COLUMN stock_minimo DECIMAL(10,3) NOT NULL DEFAULT 5;
ALTER TABLE repuestos MODIFY COLUMN stock_maximo DECIMAL(10,3) NOT NULL DEFAULT 100;
