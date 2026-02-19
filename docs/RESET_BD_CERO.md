# Reset Base de Datos a Cero

Script para vaciar todas las tablas y dejar solo al administrador (Ramon).

## Uso

**PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
python scripts/reset_bd_cero.py
python scripts/reset_bd_cero.py --yes
```

**CMD:**
```cmd
venv\Scripts\activate.bat
python scripts/reset_bd_cero.py
python scripts/reset_bd_cero.py --yes
```

## Qué hace

1. **Borra** todas las tablas de la base de datos
2. **Recrea** el esquema desde los modelos actuales
3. **Marca** alembic en `head`
4. **Crea** el usuario Ramon como ADMIN

## Credenciales por defecto

| Campo      | Valor                       |
|-----------|-----------------------------|
| Nombre    | Ramon                       |
| Email     | rrabago@medinaautodiag.com  |
| Contraseña| Admin12345                  |

## Personalizar

Variables de entorno:

```env
RESET_ADMIN_NOMBRE=Ramon
RESET_ADMIN_EMAIL=rrabago@medinaautodiag.com
RESET_ADMIN_PASSWORD=Admin12345
```

## Ejecutar contra Aiven (desde tu PC)

### Paso 1: Obtener la Service URI de Aiven

1. Entra a [console.aiven.io](https://console.aiven.io)
2. Selecciona tu proyecto → tu servicio MySQL
3. En la pestaña **Overview**, busca **Connection information**
4. Copia la **Service URI** (formato: `mysql://usuario:contraseña@host:puerto/nombre_bd?ssl-mode=REQUIRED`)

### Paso 2: Configurar la conexión

**Opción A — Script helper (recomendado, no queda en disco):**

Ejecuta desde CMD:
```cmd
cd c:\medina_autodiag_api
scripts\reset_aiven.bat
```
El script te pedirá que pegues la Service URI; la usará en memoria y hará el reset.

**Opción A2 — Variable manual en CMD:**

Importante: debe incluir `DATABASE_URL=` antes del valor:
```cmd
set "DATABASE_URL=mysql://USUARIO:PASSWORD@HOST:PUERTO/NOMBRE_BD?ssl-mode=REQUIRED"
```
Si omites `DATABASE_URL=` el script conectará a localhost por defecto.

**Opción B — Archivo `.env`:**

Si prefieres usar `.env`, agrega la misma línea ahí. El script la leerá automáticamente.

### Paso 3: Ejecutar el reset

**CMD (ejemplo completo con variable en memoria):**
```cmd
cd c:\medina_autodiag_api
set "DATABASE_URL=mysql://USUARIO:PASSWORD@host.aivencloud.com:12345/defaultdb?ssl-mode=REQUIRED"
venv\Scripts\activate.bat
python scripts/reset_bd_cero.py --yes
```

**PowerShell (variable en memoria):**
```powershell
cd c:\medina_autodiag_api
$env:DATABASE_URL="mysql://USUARIO:PASSWORD@host.aivencloud.com:12345/defaultdb?ssl-mode=REQUIRED"
.\venv\Scripts\Activate.ps1
python scripts/reset_bd_cero.py --yes
```

Si todo va bien verás: `RESET COMPLETADO. Ya puedes iniciar sesión.`

### Paso 4: Verificar

Inicia sesión en tu app (frontend o Railway) con:
- **Email:** rrabago@medinaautodiag.com  
- **Contraseña:** Admin12345  

---

## Requisitos

- `DATABASE_URL` o `DB_*` configurados (mismo que la API)
- Conectar a la misma base que usas en desarrollo/producción

## Aviso

**Solo ejecutar cuando no hay datos importantes.** Borra TODO irreversiblemente.
