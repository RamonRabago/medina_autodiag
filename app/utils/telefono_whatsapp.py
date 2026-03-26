"""Normalización de teléfonos para WhatsApp Cloud API (México por defecto)."""
import re


def normalizar_para_whatsapp(telefono: str | None, codigo_pais_default: str = "52") -> str | None:
    """
    Devuelve solo dígitos, sin +, listo para el campo `to` de Meta.
    México: 52 + 10 dígitos (celular suele empezar en 1).
    """
    if not telefono or not str(telefono).strip():
        return None
    raw = str(telefono).strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    # Ya incluye código de país (52 para MX)
    if len(digits) in (12, 13) and digits.startswith("52"):
        return digits
    if len(digits) == 11 and digits.startswith("521"):
        return digits
    # 10 dígitos: asumir México
    if len(digits) == 10:
        return f"{codigo_pais_default}{digits}"
    # +1 u otros: si tiene 10–15 dígitos y no es MX, devolver tal cual (sin +)
    if 10 <= len(digits) <= 15:
        return digits
    return None
