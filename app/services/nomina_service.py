"""
Servicio de cálculo de nómina - Etapa 4+.
Integra asistencia, salario proporcional, bono puntualidad y descuentos por préstamos.
Soporta periodo SEMANAL, QUINCENAL y MENSUAL según usuario.periodo_pago.
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
import calendar

from app.models.asistencia import Asistencia
from app.models.usuario import Usuario

# Tipos que cuentan como pagados (según plan)
TIPOS_PAGADOS = ("TRABAJO", "FESTIVO", "VACACION", "PERMISO_CON_GOCE", "INCAPACIDAD")

# Días por tipo de periodo (para prorateo de préstamos)
DIAS_PERIODO = {"SEMANAL": 7, "QUINCENAL": 15, "MENSUAL": 30}


def _lunes_semana(d: date) -> date:
    """Retorna el lunes de la semana (ISO: lunes=0)."""
    return d - timedelta(days=d.weekday())


def _domingo_semana(d: date) -> date:
    """Retorna el domingo de la semana."""
    return _lunes_semana(d) + timedelta(days=6)


def _inicio_quincena(d: date) -> date:
    """Retorna el primer día de la quincena (1 o 16)."""
    if d.day <= 15:
        return date(d.year, d.month, 1)
    return date(d.year, d.month, 16)


def _fin_quincena(d: date) -> date:
    """Retorna el último día de la quincena."""
    if d.day <= 15:
        return date(d.year, d.month, 15)
    ultimo = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, ultimo)


def _inicio_mes(d: date) -> date:
    """Retorna el día 1 del mes."""
    return date(d.year, d.month, 1)


def _fin_mes(d: date) -> date:
    """Retorna el último día del mes."""
    ultimo = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, ultimo)


def _periodo_anterior(inicio: date, fin: date, tipo: str) -> tuple[date, date]:
    """Retorna el periodo anterior al dado."""
    dias = (fin - inicio).days + 1
    return (inicio - timedelta(days=dias), fin - timedelta(days=dias))


def _dias_laborables_en_rango(inicio: date, fin: date, dias_semana_trabaja: Optional[str] = None) -> int:
    """Cuenta días laborables en el rango según dias_semana_trabaja (1=lun..7=dom)."""
    if dias_semana_trabaja and str(dias_semana_trabaja).strip():
        try:
            dias_ok = set(int(x.strip()) for x in str(dias_semana_trabaja).split(",") if x.strip())
        except (ValueError, TypeError):
            dias_ok = {1, 2, 3, 4, 5}
    else:
        dias_ok = {1, 2, 3, 4, 5}  # lun-vie por defecto
    count = 0
    d = inicio
    while d <= fin:
        wd = 7 if d.weekday() == 6 else d.weekday() + 1  # ISO: lun=1, dom=7
        if wd in dias_ok:
            count += 1
        d += timedelta(days=1)
    return max(1, count)


def calcular_nomina_semanal(
    db: Session,
    id_usuario: int,
    fecha_referencia: Optional[date] = None,
) -> dict:
    """
    Calcula la nómina semanal (compatibilidad). Use calcular_nomina para soporte completo.
    """
    return calcular_nomina(db, id_usuario, fecha_referencia, "SEMANAL", 0)


def calcular_nomina(
    db: Session,
    id_usuario: int,
    fecha_referencia: Optional[date] = None,
    periodo_pago: Optional[str] = None,
    offset_periodos: int = 0,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
) -> dict:
    """
    Calcula la nómina para un empleado.
    - Si fecha_inicio y fecha_fin están definidos: usa ese rango (ignora offset/tipo).
    - Si no: usa periodo_pago y offset_periodos desde fecha_referencia.
    """
    if fecha_referencia is None:
        fecha_referencia = date.today()

    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        return {"error": "Usuario no encontrado"}

    salario_base = Decimal("0") if usuario.salario_base is None else Decimal(str(usuario.salario_base))
    bono_puntualidad_base = Decimal("0") if usuario.bono_puntualidad is None else Decimal(str(usuario.bono_puntualidad))
    horas_por_dia = float(usuario.horas_por_dia or 8)

    if fecha_inicio is not None and fecha_fin is not None and fecha_inicio <= fecha_fin:
        lun = fecha_inicio
        dom = fecha_fin
        tipo = "PERSONALIZADO"
        dias_esperados = _dias_laborables_en_rango(lun, dom, usuario.dias_semana_trabaja)
    else:
        tipo = (periodo_pago or getattr(usuario.periodo_pago, "value", None) or str(usuario.periodo_pago) if usuario.periodo_pago else "SEMANAL")
        if tipo not in ("SEMANAL", "QUINCENAL", "MENSUAL"):
            tipo = "SEMANAL"
        if tipo == "SEMANAL":
            lun = _lunes_semana(fecha_referencia)
            dom = _domingo_semana(fecha_referencia)
        elif tipo == "QUINCENAL":
            lun = _inicio_quincena(fecha_referencia)
            dom = _fin_quincena(fecha_referencia)
        else:
            lun = _inicio_mes(fecha_referencia)
            dom = _fin_mes(fecha_referencia)
        for _ in range(abs(offset_periodos)):
            lun, dom = _periodo_anterior(lun, dom, tipo)
        if tipo == "SEMANAL":
            dias_esperados = int(usuario.dias_por_semana or 5)
        elif tipo == "QUINCENAL":
            dias_esperados = 10
        else:
            dias_esperados = 22

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

    if dias_esperados > 0:
        salario_proporcional = (dias_pagados / Decimal(dias_esperados)) * salario_base
        bono_puntualidad = (dias_con_bono / Decimal(dias_esperados)) * bono_puntualidad_base if bono_puntualidad_base > 0 else Decimal("0")
    else:
        salario_proporcional = Decimal("0")
        bono_puntualidad = Decimal("0")

    return {
        "periodo_inicio": str(lun),
        "periodo_fin": str(dom),
        "tipo_periodo": tipo,
        "dias_pagados": float(dias_pagados),
        "dias_esperados": dias_esperados,
        "salario_base": float(salario_base),
        "salario_proporcional": float(salario_proporcional),
        "bono_puntualidad_base": float(bono_puntualidad_base),
        "bono_puntualidad": float(bono_puntualidad),
        "detalle_asistencia": detalle,
    }
