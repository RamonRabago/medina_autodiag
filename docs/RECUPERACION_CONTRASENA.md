# Recuperación de contraseña

## Flujo

1. El usuario hace clic en "¿Olvidaste tu contraseña?" en la pantalla de login.
2. Ingresa su email y solicita el enlace.
3. Si el email está registrado y el correo está configurado, recibe un email con un enlace válido por 1 hora.
4. Al hacer clic, abre la página de restablecer contraseña.
5. Ingresa la nueva contraseña dos veces y confirma.
6. Puede iniciar sesión con la nueva contraseña.

## Configuración

### 1. URL pública de la aplicación

Los enlaces en el email deben apuntar a tu aplicación. Configura en `.env` o en Railway:

```env
APP_PUBLIC_URL=https://tu-app.up.railway.app
```

En desarrollo local con Vite:

```env
APP_PUBLIC_URL=http://localhost:5173
```

### 2. Servidor de correo

Para enviar los emails de recuperación, configura **Microsoft Graph API** o **SMTP** (igual que para órdenes de compra a proveedores):

**Microsoft Graph (recomendado si usas Microsoft 365):**
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_SEND_AS_EMAIL`

**SMTP (alternativa):**
- `SMTP_HOST`
- `SMTP_PORT` (por defecto 587)
- `SMTP_FROM_EMAIL`
- `SMTP_USER` y `SMTP_PASSWORD` (si el servidor requiere autenticación)
- `SMTP_USE_TLS=true`

Ver `GUIA_GRAPH_API_EMAIL.md` para detalles de Graph API.

### 3. Sin correo configurado

Si no configuras correo, la solicitud de recuperación seguirá respondiendo correctamente (por seguridad no revela si el email existe), pero **no se enviará ningún email**. El usuario no recibirá el enlace. En ese caso, el administrador puede restablecer la contraseña desde **Configuración → Usuarios → Editar usuario** y establecer una nueva contraseña.

## Seguridad

- Los tokens expiran en 1 hora.
- Cada token es de un solo uso.
- No se revela si el email está registrado o no (siempre el mismo mensaje).
- Contraseña mínima: 4 caracteres (igual que el resto del sistema).
