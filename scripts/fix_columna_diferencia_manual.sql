-- Ejecutar manualmente si la columna caja_turnos.diferencia no existe (error 1054 en Railway).
-- El usuario de la app puede no tener permiso ALTER en Aiven; usa el usuario admin.
--
-- Aiven Console: https://console.aiven.io
-- 1. Tu servicio MySQL → Overview
-- 2. Copia Host, Puerto, Usuario (avnadmin) y Contraseña
-- 3. Conecta con MySQL Workbench, DBeaver o: mysql -h HOST -P PUERTO -u avnadmin -p NOMBRE_BD
-- 4. Ejecuta:

ALTER TABLE caja_turnos ADD COLUMN diferencia NUMERIC(10, 2) NULL;

-- Si da error "Duplicate column", la columna ya existe y no hace falta hacer nada.
