# Guía para subir el proyecto a GitHub

## Paso 1: Instalar Git (si no lo tienes)

1. Descarga Git para Windows: https://git-scm.com/download/win
2. Instala con las opciones por defecto
3. Reinicia la terminal o Cursor para que reconozca el comando `git`

---

## Paso 2: Crear el repositorio en GitHub

1. Entra a https://github.com/new
2. **Repository name:** `medina-autodiag` (o el nombre que prefieras)
3. **Description:** Sistema de gestión para taller mecánico
4. Elige **Private** o **Public**
5. **NO** marques "Add a README file" (el proyecto ya tiene archivos)
6. Haz clic en **Create repository**

---

## Paso 3: Ejecutar estos comandos en la terminal

Abre una terminal en la carpeta del proyecto (`c:\medina_autodiag_api`) y ejecuta:

```powershell
# Ir a la carpeta del proyecto
cd c:\medina_autodiag_api

# Inicializar Git (si aún no está)
git init

# Ver archivos que se van a subir
git status

# Agregar todos los archivos
git add .

# Primer commit
git commit -m "Proyecto inicial - MedinaAutoDiag"

# Conectar con tu repositorio de GitHub (reemplaza con el nombre de tu repo si es diferente)
git remote add origin https://github.com/RamonRabago/medina-autodiag.git

# Subir a GitHub (rama main)
git branch -M main
git push -u origin main
```

---

## Paso 4: Autenticación

Al hacer `git push`, GitHub te pedirá autenticarte:

- **Usuario:** RamonRabago
- **Contraseña:** usa un **Personal Access Token** (no tu contraseña de GitHub)

### Crear un token:

1. GitHub → Configuración (tu foto) → **Settings**
2. **Developer settings** → **Personal access tokens** → **Tokens (classic)**
3. **Generate new token (classic)**
4. Ponle un nombre (ej: "MedinaAutoDiag")
5. Marca el permiso **repo**
6. Genera y copia el token (solo se muestra una vez)
7. Úsalo como "contraseña" cuando `git push` lo pida

---

## Resumen de comandos (después de tener Git)

```powershell
cd c:\medina_autodiag_api
git init
git add .
git commit -m "Proyecto inicial - MedinaAutoDiag"
git remote add origin https://github.com/RamonRabago/medina-autodiag.git
git branch -M main
git push -u origin main
```

---

## Para futuros cambios

```powershell
git add .
git commit -m "Descripción de lo que cambiaste"
git push
```
