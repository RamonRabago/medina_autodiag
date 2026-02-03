"""
Validadores personalizados para schemas Pydantic
"""
import re
from typing import Any


def validar_telefono_mexico(telefono: str) -> str:
    """
    Valida que el teléfono tenga formato mexicano
    
    Formatos aceptados:
    - 10 dígitos: 6441234567
    - Con lada: +526441234567
    - Con espacios: 644 123 4567
    - Con guiones: 644-123-4567
    - Acepta entre 7 y 15 dígitos
    
    Args:
        telefono: Número telefónico a validar
    
    Returns:
        Teléfono limpio (solo dígitos)
    
    Raises:
        ValueError: Si el formato es inválido
    """
    # Eliminar espacios, guiones y paréntesis
    telefono_limpio = re.sub(r'[\s\-\(\)]', '', telefono)
    
    # Eliminar código de país si existe (+52)
    if telefono_limpio.startswith('+52'):
        telefono_limpio = telefono_limpio[3:]
    elif telefono_limpio.startswith('52') and len(telefono_limpio) > 10:
        telefono_limpio = telefono_limpio[2:]
    
    # Validar que sean solo dígitos y longitud razonable (7-15 dígitos)
    if not re.match(r'^\d{7,15}$', telefono_limpio):
        raise ValueError(
            'El teléfono debe tener entre 7 y 15 dígitos'
        )
    
    return telefono_limpio


def validar_email_opcional(email: str | None) -> str | None:
    """
    Valida formato de email si se proporciona
    
    Args:
        email: Email a validar (puede ser None)
    
    Returns:
        Email normalizado (lowercase) o None
    
    Raises:
        ValueError: Si el formato es inválido
    """
    if not email:
        return None
    
    # Normalizar a minúsculas
    email = email.lower().strip()
    
    # Patrón básico de validación
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(patron, email):
        raise ValueError('Formato de email inválido')
    
    return email


def validar_placa_vehiculo(placa: str) -> str:
    """
    Valida formato de placa vehicular mexicana
    
    Formatos aceptados:
    - ABC-123-D (formato nuevo)
    - ABC-12-34 (formato antiguo)
    
    Args:
        placa: Placa a validar
    
    Returns:
        Placa en mayúsculas
    
    Raises:
        ValueError: Si el formato es inválido
    """
    placa = placa.upper().strip()
    
    # Formato nuevo: 3 letras - 3 números - 1 letra
    patron_nuevo = r'^[A-Z]{3}-\d{3}-[A-Z]$'
    
    # Formato antiguo: 3 letras - 2 números - 2 números
    patron_antiguo = r'^[A-Z]{3}-\d{2}-\d{2}$'
    
    if not (re.match(patron_nuevo, placa) or re.match(patron_antiguo, placa)):
        raise ValueError(
            'Formato de placa inválido. '
            'Use ABC-123-D o ABC-12-34'
        )
    
    return placa


def validar_rfc_mexicano(rfc: str) -> str:
    """
    Valida formato de RFC mexicano.

    Formatos aceptados:
    - Persona moral (12 chars): 3 letras + 6 dígitos (fecha) + 3 alfanum (homoclave)
    - Persona física (13 chars): 4 letras + 6 dígitos (fecha) + 3 alfanum (homoclave)

    Ejemplos: XAXX010101000, MABG850101ABC

    Args:
        rfc: RFC a validar

    Returns:
        RFC en mayúsculas

    Raises:
        ValueError: Si el formato es inválido
    """
    rfc = (rfc or "").strip()
    if not rfc:
        raise ValueError("RFC no puede estar vacío")
    rfc = rfc.upper()
    # Persona moral: 3 letras + 6 dígitos + 3 alfanum
    patron_pm = re.match(r"^[A-ZÑ&]{3}\d{6}[A-Z0-9]{3}$", rfc)
    # Persona física: 4 letras + 6 dígitos + 3 alfanum
    patron_pf = re.match(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$", rfc)
    if not (patron_pm or patron_pf):
        raise ValueError(
            "RFC inválido. Persona moral: 12 caracteres (AAA999999XXX). "
            "Persona física: 13 caracteres (AAAA999999XXX)."
        )
    return rfc


def validar_rfc_opcional(rfc: str | None) -> str | None:
    """
    Valida RFC mexicano si se proporciona. Retorna None para vacío/None.
    """
    if not rfc or not str(rfc).strip():
        return None
    return validar_rfc_mexicano(rfc)


def validar_monto_positivo(monto: float) -> float:
    """
    Valida que el monto sea positivo
    
    Args:
        monto: Cantidad a validar
    
    Returns:
        Monto validado
    
    Raises:
        ValueError: Si el monto es negativo o cero
    """
    if monto <= 0:
        raise ValueError('El monto debe ser mayor a cero')
    
    # Redondear a 2 decimales
    return round(monto, 2)
