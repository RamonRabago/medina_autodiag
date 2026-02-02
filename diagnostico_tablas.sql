-- Script de Diagnóstico
-- Verificar estructura de tablas existentes

USE medina_autodiag;

-- Ver estructura de vehiculos
SHOW CREATE TABLE vehiculos;

-- Ver estructura de clientes  
SHOW CREATE TABLE clientes;

-- Ver estructura de usuarios
SHOW CREATE TABLE usuarios;

-- Ver estructura de repuestos
SHOW CREATE TABLE repuestos;

-- Ver las columnas de cada tabla
SELECT 'VEHICULOS:' as Tabla;
DESCRIBE vehiculos;

SELECT 'CLIENTES:' as Tabla;
DESCRIBE clientes;

SELECT 'USUARIOS:' as Tabla;
DESCRIBE usuarios;

SELECT 'REPUESTOS:' as Tabla;
DESCRIBE repuestos;
