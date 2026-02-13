"""
Servicio de cálculo de nómina - Etapa 4.
Integra asistencia, salario proporcional, bono puntualidad y descuentos por préstamos.
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.asistencia import Asistencia
from app.models.usuario import Usuario

# Tipos que cuentan como pagados (según plan)
TIPOS_PAGADOS = ("TRABAJO", "FESTIVO", "VACACION", "PERMISO_CON_GOCE", "INCAPACIDAD")


def _lunes_semana(d: date) -> date:
    """Retorna el lunes de la semana (ISO: lunes=0)."""
    return d - timedelta(days=d.weekday())


def _domingo_semana(d: date) -> date:
    """Retorna el domingo de la semana."""
    return _lunes_semana(d) + timedelta(days=6)


def calcular_nomina_semanal(
    db: Session,
    id_usuario: int,
    fecha_referencia: Optional[date] = None,
) -> dict:
    """
    Calcula la nómina semanal para un empleado.
    - fecha_referencia: si None, usa hoy para determinar la semana actual.
    Retorna: dias_pagados, dias_esperados, salario_proporcional, bono_puntualidad,
             detalle_asistencia, periodo_inicio, periodo_fin
    """
    if fecha_referencia is None:
        fecha_referencia = date.today()
    lun = _lunes_semana(fecha_referencia)
    dom = _domingo_semana(fecha_referencia)

    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        return {"error": "Usuario no encontrado"}

    salario_base = Decimal("0") if usuario.salario_base is None else Decimal(str(usuario.salario_base))
    bono_puntualidad_base = Decimal("0") if usuario.bono_puntualidad is None else Decimal(str(usuario.bono_puntualidad))
    dias_esperados = int(usuario.dias_por_semana or 5)
    horas_por_dia = float(usuario.horas_por_dia or 8)

    registros = (
        db.query(Asistencia)
        .filter(
            Asistencia.id_usuario == id_usuario,
            Asistencia.fecha >= lun,
            Asistencia.fecha <= dom,
        )
        .order_by(Asistencia.fecha)
        .all()
    )

    dias_pagados = Decimal("0")
    dias_con_bono = Decimal("0")
    detalle = []

    for r in registros:
        tipo_str = getattr(r.tipo, "value", None) or str(r.tipo)
        if tipo_str not in TIPOS_PAGADOS:
            continue

        # Días equivalentes para este registro
        if tipo_str == "TRABAJO":
            if r.turno_completo:
                eq_dias = Decimal("1")
            else:
                hrs = Decimal(str(r.horas_trabajadas or 0))
                eq_dias = (hrs / Decimal(str(horas_por_dia))) if horas_por_dia else Decimal("1")
        else:
            eq_dias = Decimal("1")

        dias_pagados += eq_dias
        if r.aplica_bono_puntualidad:
            dias_con_bono += eq_dias

        detalle.append({
            "fecha": str(r.fecha),
            "tipo": tipo_str,
            "dias_equiv": float(eq_dias),
            "aplica_bono": bool(r.aplica_bono_puntualidad),
        })

    # Salario proporcional
    if dias_esperados > 0:
        salario_proporcional = (dias_pagados / Decimal(dias_esperados)) * salario_base
    else:
        salario_proporcional = Decimal("0")

    # Bono puntualidad (proporcional a días con bono)
    if dias_esperados > 0 and bono_puntualidad_base > 0:
        bono_puntualidad = (dias_con_bono / Decimal(dias_esperados)) * bono_puntualidad_base
    else:
        bono_puntualidad = Decimal("0")

    return {
        "periodo_inicio": str(lun),
        "periodo_fin": str(dom),
        "dias_pagados": float(dias_pagados),
        "dias_esperados": dias_esperados,
        "salario_base": float(salario_base),
        "salario_proporcional": float(salario_proporcional),
        "bono_puntualidad_base": float(bono_puntualidad_base),
        "bono_puntualidad": float(bono_puntualidad),
        "detalle_asistencia": detalle,
    }
