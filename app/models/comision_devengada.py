"""
Comisión devengada por venta.
Fase 2: se registra al quedar la venta PAGADA.
"""
from sqlalchemy import Column, Integer, Numeric, Date, Enum, ForeignKey
from app.database import Base

TIPOS_BASE_CD = ("MANO_OBRA", "PARTES", "SERVICIOS_VENTA", "PRODUCTOS_VENTA")


class ComisionDevengada(Base):
    __tablename__ = "comisiones_devengadas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True)  # Quien cobra
    id_venta = Column(Integer, ForeignKey("ventas.id_venta", ondelete="CASCADE"), nullable=False, index=True)
    id_detalle = Column(Integer, nullable=True)  # Referencia opcional al detalle
    tipo_base = Column(Enum(*TIPOS_BASE_CD), nullable=False)
    base_monto = Column(Numeric(10, 2), nullable=False)  # Subtotal del detalle
    porcentaje = Column(Numeric(5, 2), nullable=False)
    monto_comision = Column(Numeric(10, 2), nullable=False)
    fecha_venta = Column(Date, nullable=False, index=True)  # Para reportes por período
