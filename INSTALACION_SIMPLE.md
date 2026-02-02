# 🚀 INSTALACIÓN SIMPLE - MedinaAutoDiag API

## Pasos Rápidos

### 1️⃣ Configurar Base de Datos

Abre MySQL y ejecuta:

```sql
CREATE DATABASE medinaautodiag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2️⃣ Editar .env

Abre el archivo `.env` en la raíz del proyecto y verifica/edita:

```env
DB_USER=root
DB_PASSWORD=autodiag        ← Cambia si tu password es diferente
DB_HOST=localhost
DB_PORT=3306
DB_NAME=medinaautodiag

SECRET_KEY=...              ← Ver paso 2b (IMPORTANTE)
```

**2b. Generar SECRET_KEY:**

Ejecuta en terminal:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copia el resultado y pégalo en la línea `SECRET_KEY=` del archivo `.env`

### 3️⃣ Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4️⃣ Crear Usuario Admin (Opcional)

Si quieres crear/resetear el usuario admin:

```bash
python crear_usuario_admin.py
```

Esto creará:
- Email: `Admin@medinaautodiag.com`
- Password: `Admin1234`

### 5️⃣ Ejecutar la API

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### ✅ Verificar que Funciona

Abre tu navegador en: **http://127.0.0.1:8000/docs**

Deberías ver la documentación Swagger de la API.

---

## 🔍 Verificación Completa

Si ves esto en la consola, todo está bien:

```
============================================================
Iniciando MEDINAAUTODIAG API v1.0.0
============================================================
INFO: ✓ Tablas de base de datos creadas/verificadas
INFO: Uvicorn running on http://127.0.0.1:8000
```

---

## ⚠️ Problemas Comunes

### "Can't connect to MySQL"

**Solución:**
1. Verifica que MySQL esté corriendo
2. Revisa que el password en `.env` sea correcto (actualmente: `autodiag`)
3. Verifica que la base de datos `medinaautodiag` exista

### "No module named 'app.config'"

**Solución:**
```bash
pip install -r requirements.txt
```

### "SECRET_KEY not found"

**Solución:**
1. Asegúrate que el archivo `.env` existe
2. Verifica que tiene la línea `SECRET_KEY=...`
3. Genera una nueva ejecutando: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## 📝 Comandos para Copiar y Pegar

### Windows PowerShell:

```powershell
# Instalar dependencias
pip install -r requirements.txt

# Crear admin
python crear_usuario_admin.py

# Ejecutar API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Generar SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

### Linux/Mac Terminal:

```bash
# Instalar dependencias
pip install -r requirements.txt

# Crear admin
python crear_usuario_admin.py

# Ejecutar API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Generar SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🎯 Resumen Simplificado

1. Crear base de datos en MySQL
2. Editar `.env` (password + SECRET_KEY)
3. `pip install -r requirements.txt`
4. `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
5. Ir a http://127.0.0.1:8000/docs

**¡Listo!** 🎉
