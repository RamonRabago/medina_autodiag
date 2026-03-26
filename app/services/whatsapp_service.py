"""
Envío de mensajes vía Meta WhatsApp Cloud API.
Las plantillas deben existir y estar aprobadas en Meta (ver docs/GUIA_WHATSAPP_META_CLOUD_API.md).
"""
import logging
from typing import Any

import httpx

from app.config import settings
from app.utils.telefono_whatsapp import normalizar_para_whatsapp

logger = logging.getLogger(__name__)

GRAPH_MESSAGES = "https://graph.facebook.com/{version}/{phone_id}/messages"


def whatsapp_esta_configurado() -> bool:
    return bool(
        settings.WHATSAPP_ENABLED
        and settings.WHATSAPP_PHONE_NUMBER_ID
        and settings.WHATSAPP_ACCESS_TOKEN
    )


def _trunc(s: str, max_len: int = 900) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def enviar_plantilla(
    telefono_destino: str,
    nombre_plantilla: str,
    parametros_cuerpo: list[str],
    codigo_idioma: str | None = None,
    timeout_s: float = 30.0,
) -> tuple[bool, str | None]:
    """
    Envía un mensaje tipo template (variables en el body del template).
    telefono_destino: texto libre; se normaliza con normalizar_para_whatsapp.
    """
    if not whatsapp_esta_configurado():
        return False, "WhatsApp no está configurado (WHATSAPP_ENABLED y credenciales)"

    to_digits = normalizar_para_whatsapp(telefono_destino)
    if not to_digits:
        return False, "Teléfono inválido o vacío para WhatsApp"

    lang = (codigo_idioma or settings.WHATSAPP_TEMPLATE_LANGUAGE or "es").strip()
    phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
    token = settings.WHATSAPP_ACCESS_TOKEN
    ver = (settings.WHATSAPP_API_VERSION or "v21.0").strip()
    version = ver if ver.startswith("v") else f"v{ver}"

    url = GRAPH_MESSAGES.format(version=version, phone_id=phone_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    components: list[dict[str, Any]] = []
    if parametros_cuerpo:
        components.append(
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": _trunc(str(p))} for p in parametros_cuerpo
                ],
            }
        )
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_digits,
        "type": "template",
        "template": {
            "name": nombre_plantilla.strip(),
            "language": {"code": lang},
            "components": components,
        },
    }

    try:
        with httpx.Client(timeout=timeout_s) as client:
            r = client.post(url, headers=headers, json=payload)
        body_preview = (r.text or "")[:500]
        if r.status_code >= 400:
            err_msg = body_preview
            try:
                data = r.json()
                err = data.get("error") or {}
                if isinstance(err, dict) and err.get("message"):
                    err_msg = str(err.get("message"))
            except Exception:
                pass
            logger.warning("WhatsApp API error %s: %s", r.status_code, err_msg)
            return False, err_msg

        logger.info("WhatsApp plantilla '%s' enviada a ***%s", nombre_plantilla, to_digits[-4:])
        return True, None
    except httpx.RequestError as e:
        logger.exception("WhatsApp red: %s", e)
        return False, str(e)


def enviar_orden_compra_proveedor_whatsapp(
    telefono: str,
    nombre_proveedor: str,
    numero_orden: str,
    total_estimado_texto: str,
) -> tuple[bool, str | None]:
    """Plantilla por defecto: orden_compra_proveedor (3 variables body según guía)."""
    return enviar_plantilla(
        telefono,
        settings.WHATSAPP_TEMPLATE_ORDEN_COMPRA,
        [
            _trunc(nombre_proveedor or "proveedor", 120),
            _trunc(numero_orden or "", 80),
            _trunc(total_estimado_texto or "0", 40),
        ],
    )


def enviar_confirmacion_cita_whatsapp(
    telefono: str,
    nombre_cliente: str,
    fecha_txt: str,
    hora_txt: str,
    motivo_o_servicio: str,
) -> tuple[bool, str | None]:
    """Plantilla por defecto: confirmacion_cita (4 variables body según guía)."""
    return enviar_plantilla(
        telefono,
        settings.WHATSAPP_TEMPLATE_CONFIRMACION_CITA,
        [
            _trunc(nombre_cliente or "cliente", 120),
            _trunc(fecha_txt, 40),
            _trunc(hora_txt, 20),
            _trunc(motivo_o_servicio or "-", 200),
        ],
    )
