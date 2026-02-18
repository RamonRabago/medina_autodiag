"""
Configuración de comisiones por empleado y tipo de base.
Fase 0 comisiones: define qué % cobra cada empleado en cada base.
Al cambiar un %, se cierra la vigencia anterior y se crea nueva fila (histórico).
"""
from sqlalchemy import Column, Integer, Numeric, Date, Enum, ForeignKey, Boolean
from app.database import Base
from sqlalchemy.orm import relationship

TIPOS_BASE_COMISION = (
    "MANO_OBRA",       # Técnico: subtotal servicios OT
    "PARTES",           # Técnico: subtotal repuestos OT
    "SERVICIOS_VENTA",  # Vendedor: subtotal servicios en venta
    "PRODUCTOS_VENTA",  # Vendedor: subtotal productos en venta
)


class ConfiguracionComision(Base):
    __tablename__ = "configuracion_comision"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True)
    tipo_base = Column(Enum(*TIPOS_BASE_COMISION), nullable=False)
    porcentaje = Column(Numeric(5, 2), nullable=False)  # 0.00 - 100.00
    vigencia_desde = Column(Date, nullable=False)
    vigencia_hasta = Column(Date, nullable=True)  # NULL = vigente hasta hoy
    activo = Column(Boolean, default=True, nullable=False)

    usuario = relationship("Usuario", foreign_keys=[id_usuario])
