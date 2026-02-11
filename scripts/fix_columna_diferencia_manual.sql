-- Ejecutar manualmente si la columna caja_turnos.diferencia no existe (error 1054 en Railway).
-- Conectar a la BD de producción y ejecutar:

ALTER TABLE caja_turnos ADD COLUMN diferencia NUMERIC(10, 2) NULL;

-- Si da error "Duplicate column", la columna ya existe y no hace falta hacer nada.
