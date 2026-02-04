-- Agregar columna imagen_url a repuestos
-- Ejecutar: mysql -u usuario -p base_datos < agregar_imagen_url_repuestos.sql
-- O copiar y ejecutar en tu cliente MySQL:

ALTER TABLE repuestos ADD COLUMN imagen_url VARCHAR(500) NULL;
