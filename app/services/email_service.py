"""
Servicio de envío de emails.
Soporta Microsoft Graph API (OAuth2) y SMTP como fallback.
Usado para enviar órdenes de compra a proveedores.
"""
import smtplib
import logging
import urllib.request
import urllib.parse
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _graph_esta_configurado() -> bool:
    """Verifica si Microsoft Graph API está configurado."""
    return bool(
        getattr(settings, "AZURE_TENANT_ID", None)
        and getattr(settings, "AZURE_CLIENT_ID", None)
        and getattr(settings, "AZURE_CLIENT_SECRET", None)
        and getattr(settings, "AZURE_SEND_AS_EMAIL", None)
    )


def _smtp_esta_configurado() -> bool:
    """Verifica si el SMTP está configurado."""
    return bool(
        getattr(settings, "SMTP_HOST", None)
        and getattr(settings, "SMTP_FROM_EMAIL", None)
    )


def _obtener_token_graph() -> tuple[Optional[str], Optional[str]]:
    """
    Obtiene access token de Microsoft Graph usando client credentials.
    Returns: (access_token, error_message)
    """
    try:
        import msal
        app = msal.ConfidentialClientApplication(
            client_id=settings.AZURE_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
            client_credential=settings.AZURE_CLIENT_SECRET,
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

        if result.get("access_token"):
            return result["access_token"], None

        # MSAL no lanza excepción; devuelve dict con error
        err = result.get("error", "unknown")
        desc = result.get("error_description", result.get("error_codes", "sin detalle"))
        msg = f"{err}: {desc}"
        logger.error(f"Graph token falló: {msg}")
        return None, msg
    except Exception as e:
        logger.exception(f"Error obteniendo token Graph: {e}")
        return None, str(e)


def _enviar_via_graph(
    email_destino: str,
    subject: str,
    cuerpo: str,
) -> tuple[bool, Optional[str]]:
    """Envía email vía Microsoft Graph API."""
    token, err_token = _obtener_token_graph()
    if not token:
        return False, err_token or "No se pudo obtener el token de Microsoft Graph"

    send_as = settings.AZURE_SEND_AS_EMAIL
    user_id = urllib.parse.quote(send_as)

    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/sendMail"
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": cuerpo},
            "toRecipients": [{"emailAddress": {"address": email_destino.strip()}}],
        },
        "saveToSentItems": True,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status in (200, 202):
                return True, None
            return False, f"Graph API devolvió status {resp.status}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore") if e.fp else ""
        try:
            err_data = json.loads(body) if body else {}
            msg = err_data.get("error", {}).get("message", str(e))
        except json.JSONDecodeError:
            msg = body or str(e)
        logger.error(f"Error Graph API: {msg}")
        return False, msg
    except Exception as e:
        logger.exception(f"Error inesperado Graph: {e}")
        return False, str(e)


def _enviar_via_smtp(
    email_destino: str,
    subject: str,
    cuerpo: str,
) -> tuple[bool, Optional[str]]:
    """Envía email vía SMTP."""
    try:
        from_email = settings.SMTP_FROM_EMAIL
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = email_destino.strip()
        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

        host = settings.SMTP_HOST
        port = getattr(settings, "SMTP_PORT", 587)
        user = getattr(settings, "SMTP_USER", None)
        password = getattr(settings, "SMTP_PASSWORD", None)
        use_tls = getattr(settings, "SMTP_USE_TLS", True)

        with smtplib.SMTP(host, port, timeout=30) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_email, [email_destino.strip()], msg.as_string())
        return True, None
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Error SMTP autenticación: {e}")
        return False, "Error de autenticación del servidor de correo"
    except smtplib.SMTPException as e:
        logger.error(f"Error SMTP: {e}")
        return False, str(e)
    except Exception as e:
        logger.exception(f"Error inesperado SMTP: {e}")
        return False, str(e)


def enviar_orden_compra_a_proveedor(
    email_destino: str,
    nombre_proveedor: str,
    numero_orden: str,
    lineas: list[dict],
    observaciones: Optional[str] = None,
    vehiculo_info: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Envía un email al proveedor con el detalle de la orden de compra.
    Usa Microsoft Graph API si está configurado; si no, SMTP.
    Sin precios ni total estimado; incluye datos del vehículo si aplica.

    Returns:
        (éxito: bool, mensaje_error: str | None)
    """
    if not email_destino or not email_destino.strip():
        return False, "El proveedor no tiene email configurado"

    subject = f"Orden de compra {numero_orden} - Medina AutoDiag"

    lineas_texto = []
    for i, linea in enumerate(lineas, 1):
        nom = linea.get("nombre_repuesto") or linea.get("codigo_repuesto") or "Sin nombre"
        cant = linea.get("cantidad_solicitada", 0)
        lineas_texto.append(f"  {i}. {nom} - Cant: {cant}")

    cuerpo = f"""Estimado(a) {nombre_proveedor},

Les enviamos la siguiente orden de compra:

Número: {numero_orden}
"""
    if vehiculo_info and vehiculo_info.strip():
        cuerpo += f"\nPara vehículo: {vehiculo_info.strip()}\n"

    cuerpo += f"""
Detalle:
{chr(10).join(lineas_texto)}
"""
    if observaciones and observaciones.strip():
        cuerpo += f"\nObservaciones: {observaciones.strip()}\n"

    cuerpo += """
Por favor confirme la recepción y la disponibilidad de los productos.

Saludos cordiales,
Medina AutoDiag
"""

    # Prioridad: Graph API > SMTP
    if _graph_esta_configurado():
        logger.debug("Intentando envío vía Microsoft Graph API")
        ok, err = _enviar_via_graph(email_destino, subject, cuerpo)
        if ok:
            logger.info(f"Email enviado vía Graph a {email_destino} para orden {numero_orden}")
        return ok, err

    if _smtp_esta_configurado():
        ok, err = _enviar_via_smtp(email_destino, subject, cuerpo)
        if ok:
            logger.info(f"Email enviado vía SMTP a {email_destino} para orden {numero_orden}")
        return ok, err

    logger.warning("Ni Graph API ni SMTP configurados.")
    return False, "Servidor de correo no configurado. Configure Azure (Graph API) o SMTP en .env"


def enviar_email_simple(
    email_destino: str,
    subject: str,
    cuerpo: str,
) -> tuple[bool, Optional[str]]:
    """
    Envía un email genérico (subject + cuerpo plano).
    Usa Graph API si está configurado; si no, SMTP.
    Returns: (éxito, mensaje_error)
    """
    if not email_destino or not email_destino.strip():
        return False, "Destinatario vacío"

    if _graph_esta_configurado():
        ok, err = _enviar_via_graph(email_destino.strip(), subject, cuerpo)
        if ok:
            logger.info(f"Email enviado vía Graph a {email_destino}")
        return ok, err

    if _smtp_esta_configurado():
        ok, err = _enviar_via_smtp(email_destino.strip(), subject, cuerpo)
        if ok:
            logger.info(f"Email enviado vía SMTP a {email_destino}")
        return ok, err

    return False, "Servidor de correo no configurado"
