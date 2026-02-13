"""Movimientos de vacaciones - Checador Fase 5."""
from sqlalchemy import Column, Integer, Date, Enum, Numeric, String
from app.database import Base


TIPOS_MOVIMIENTO_VACACIONES = ("TOMA", "ACREDITACION", "AJUSTE")


class MovimientoVacaciones(Base):
    """
    TOMA: empleado toma días -> reduce saldo
    ACREDITACION: acreditación anual -> aumenta saldo
    AJUSTE: corrección manual por admin
    """
    __tablename__ = "movimientos_vacaciones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    tipo = Column(Enum(*TIPOS_MOVIMIENTO_VACACIONES), nullable=False)
    dias = Column(Numeric(5, 2), nullable=False)  # Positivo: TOMA/ACREDITACION; AJUSTE puede ser ±
    periodo = Column(String(20), nullable=True)  # Ej: "2025" para acreditación anual
    observaciones = Column(String(500), nullable=True)
