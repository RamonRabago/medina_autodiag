# Guía: Enviar correos con Microsoft Graph API (OAuth2)

Esta guía explica cómo configurar el envío de correos usando Microsoft Graph API en lugar de SMTP, para evitar bloqueos por políticas de seguridad de Microsoft 365.

---

## Requisitos

- Cuenta Microsoft 365 de la organización
- Acceso de **administrador** al portal de Azure/Microsoft 365
- La aplicación usará **Client Credentials** (app-only): no requiere que el usuario inicie sesión

---

## Paso 1: Registro de la aplicación en Azure AD

1. Ve a [portal.azure.com](https://portal.azure.com) e inicia sesión como administrador.
2. En el menú lateral, busca **Microsoft Entra ID** (antes Azure Active Directory).
3. Entra a **Registros de aplicaciones** → **Nuevo registro**.
4. Configura:
   - **Nombre**: `MedinaAutoDiag - Envío de correos`
   - **Tipo de cuenta**: "Cuentas solo de este directorio organizativo"
   - **URI de redirección**: deja vacío (no se usa para client credentials)
5. Haz clic en **Registrar**.

---

## Paso 2: Obtener credenciales

### Application (client) ID y Directory (tenant) ID

En la página de la aplicación, verás:
- **Application (client) ID** → será `AZURE_CLIENT_ID`
- **Directory (tenant) ID** → será `AZURE_TENANT_ID`

### Crear client secret

1. En el menú de la app, ve a **Certificados y secretos**.
2. Clic en **Nuevo secreto de cliente**.
3. Descripción: `Envío de correos MedinaAutoDiag`.
4. Expiración: 24 meses (o según tu política).
5. **Clic en Agregar** y **copia el valor** inmediatamente (no lo verás de nuevo) → será `AZURE_CLIENT_SECRET`.

---

## Paso 3: Permisos de la aplicación

1. Ve a **Permisos de API** → **Agregar un permiso**.
2. Elige **Microsoft Graph**.
3. Selecciona **Permisos de aplicación** (no delegados).
4. Busca y marca:
   - **Mail.Send**
5. Clic en **Agregar permisos**.
6. **Importante**: Clic en **Conceder consentimiento de administrador** para la organización.

---

## Paso 4: Asignar permiso a un buzón (opcional en algunos entornos)

Para que la app pueda enviar correo **en nombre de** un usuario (por ejemplo `rrabago@medinaautodiag.com`):

1. La app necesita permiso **Mail.Send** a nivel de aplicación (ya lo configuraste).
2. Con Mail.Send de aplicación, la app puede enviar correo como cualquier usuario del tenant, usando el endpoint:
   ```
   POST https://graph.microsoft.com/v1.0/users/{email}/sendMail
   ```
   Donde `{email}` es el UPN del buzón desde el que envías (ej: `rrabago@medinaautodiag.com`).

En algunos tenants no hace falta asignación adicional; en otros, el administrador puede tener que asignar la aplicación al buzón. Si obtienes errores de permisos, contacta al administrador.

---

## Paso 5: Variables de entorno

Agrega a tu archivo `.env`:

```env
# Microsoft Graph API (alternativa a SMTP)
AZURE_TENANT_ID=tu-tenant-id
AZURE_CLIENT_ID=tu-client-id
AZURE_CLIENT_SECRET=tu-client-secret
AZURE_SEND_AS_EMAIL=rrabago@medinaautodiag.com
```

La aplicación usará Graph API cuando estas variables estén configuradas. Si prefieres SMTP, deja vacías las de Azure y configura solo SMTP_*.

---

## Paso 6: Probar

```bash
# Instalar dependencia (si no está)
pip install msal

# Probar envío vía Graph API
python scripts/test_graph_email.py
python scripts/test_graph_email.py otro@email.com
```

Si el correo llega, la configuración es correcta. La app usará Graph API automáticamente al hacer "Enviar orden".

---

## Resumen de variables

| Variable | Descripción |
|----------|-------------|
| `AZURE_TENANT_ID` | ID del directorio (tenant) de Azure AD |
| `AZURE_CLIENT_ID` | ID de la aplicación registrada |
| `AZURE_CLIENT_SECRET` | Secreto de cliente creado en Certificados y secretos |
| `AZURE_SEND_AS_EMAIL` | Email desde el que se enviará (ej: rrabago@medinaautodiag.com) |

---

## Solución de problemas

- **401 Unauthorized**: Revisa tenant ID, client ID y client secret.
- **403 Forbidden**: Verifica que se concedió el consentimiento de administrador para Mail.Send.
- **User not found**: Comprueba que `AZURE_SEND_AS_EMAIL` sea un usuario válido del tenant.
