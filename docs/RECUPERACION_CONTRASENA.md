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

Los emails de recuperación se envían por el mismo sistema que las órdenes de compra a proveedores. No hay un correo "por defecto" incorporado: **debes configurar** una de estas dos opciones.

#### ¿Qué correo enviará (remitente)?

| Método | Variable que define el correo "De" | Ejemplo |
|--------|-----------------------------------|---------|
| **Microsoft Graph** | `AZURE_SEND_AS_EMAIL` | `rrabago@medinaautodiag.com` |
| **SMTP** | `SMTP_FROM_EMAIL` | `noreply@tudominio.com` o `taller@gmail.com` |

Prioridad: si ambas están configuradas, **Graph API se usa primero**; SMTP solo si Graph no está.

---

#### Opción A: Microsoft Graph API (si usas Microsoft 365)

Recomendado si tu negocio usa correo de Microsoft 365 (Outlook empresarial). Evita bloqueos por seguridad de Microsoft. Define `AZURE_SEND_AS_EMAIL` como tu correo de empresa; para Medina AutoDiag se usa `rrabago@medinaautodiag.com`.

| Variable | Descripción | Ejemplo |
|---------|-------------|---------|
| `AZURE_TENANT_ID` | ID del directorio de Azure AD | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_CLIENT_ID` | ID de la app en Azure | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_CLIENT_SECRET` | Secreto creado en Certificados y secretos | `abc123~xxxxx` |
| `AZURE_SEND_AS_EMAIL` | **Correo desde el que se envía** (debe existir en tu 365) | `rrabago@medinaautodiag.com` |

Pasos: [portal.azure.com](https://portal.azure.com) → Microsoft Entra ID → Registros de aplicaciones → Nueva app → Permiso **Mail.Send** → Consentimiento de admin.

Detalles completos: **`GUIA_GRAPH_API_EMAIL.md`** (raíz del proyecto).

---

#### Opción B: SMTP

Sirve con Gmail, Outlook.com, o servidores de correo propios. La variable **`SMTP_FROM_EMAIL`** es el remitente que verá el usuario.

| Variable | Obligatorio | Descripción |
|---------|-------------|-------------|
| `SMTP_HOST` | Sí | Servidor SMTP (ej. `smtp.gmail.com`, `smtp.office365.com`) |
| `SMTP_FROM_EMAIL` | Sí | **Correo "De"** que verá el destinatario |
| `SMTP_PORT` | No | Puerto (por defecto 587) |
| `SMTP_USER` | Según proveedor | Usuario SMTP (normalmente = email) |
| `SMTP_PASSWORD` | Según proveedor | Contraseña o "contraseña de aplicación" |
| `SMTP_USE_TLS` | No | `true` (por defecto) |

**Ejemplos rápidos:**

- **Gmail**: Necesitas una ["contraseña de aplicación"](https://myaccount.google.com/apppasswords) (no la contraseña normal).  
  ```
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=tuemail@gmail.com
  SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
  SMTP_FROM_EMAIL=tuemail@gmail.com
  ```

- **Outlook/Hotmail**: Similar; puede requerir contraseña de app.  
  ```
  SMTP_HOST=smtp.office365.com
  SMTP_PORT=587
  SMTP_USER=tuemail@outlook.com
  SMTP_PASSWORD=tu-contraseña
  SMTP_FROM_EMAIL=tuemail@outlook.com
  ```

- **Proveedor de hosting** (cPanel, etc.): Usa los datos de correo que te da el proveedor.

### 3. Sin correo configurado

Si no configuras correo, la solicitud de recuperación seguirá respondiendo correctamente (por seguridad no revela si el email existe), pero **no se enviará ningún email**. El usuario no recibirá el enlace. En ese caso, el administrador puede restablecer la contraseña desde **Configuración → Usuarios → Editar usuario** y establecer una nueva contraseña.

## Seguridad

- Los tokens expiran en 1 hora.
- Cada token es de un solo uso.
- No se revela si el email está registrado o no (siempre el mismo mensaje).
- Contraseña mínima: 4 caracteres (igual que el resto del sistema).
