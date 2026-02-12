"""
Préstamos a empleados - Nómina Etapa 1+
Permite varios préstamos por empleado. Descuento fijo por periodo.
Si falta, se descuenta igual (regla de negocio).
"""
from sqlalchemy import Column, Integer, Numeric, Date, Enum, ForeignKey, TIMESTAMP, Text
from app.database import Base
import datetime

from sqlalchemy.orm import relationship

ESTADOS_PRESTAMO = ("ACTIVO", "LIQUIDADO", "CANCELADO")
PERIODOS_DESCUENTO = ("SEMANAL", "QUINCENAL", "MENSUAL")


class PrestamoEmpleado(Base):
    __tablename__ = "prestamos_empleados"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True)
    monto_total = Column(Numeric(12, 2), nullable=False)
    descuento_por_periodo = Column(Numeric(10, 2), nullable=False)
    periodo_descuento = Column(Enum(*PERIODOS_DESCUENTO), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    estado = Column(Enum(*ESTADOS_PRESTAMO), default="ACTIVO", nullable=False)
    observaciones = Column(Text, nullable=True)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    creado_por = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)

    empleado = relationship("Usuario", foreign_keys=[id_usuario])
    descuentos = relationship("DescuentoPrestamo", back_populates="prestamo", order_by="DescuentoPrestamo.fecha_periodo")


class DescuentoPrestamo(Base):
    """
    Registro de cada descuento aplicado a un préstamo.
    Se usa para calcular saldo pendiente y evitar doble deducción.
    """
    __tablename__ = "descuentos_prestamos"

    id = Column(Integer, primary_key=True, index=True)
    id_prestamo = Column(Integer, ForeignKey("prestamos_empleados.id"), nullable=False, index=True)
    monto_descontado = Column(Numeric(10, 2), nullable=False)
    fecha_periodo = Column(Date, nullable=False)  # primer día del periodo (ej. lunes para semanal)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    prestamo = relationship("PrestamoEmpleado", back_populates="descuentos")
