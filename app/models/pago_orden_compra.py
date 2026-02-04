"""
Pagos a proveedores por órdenes de compra.
Cuentas por pagar: registra los pagos realizados contra una orden de compra.
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class PagoOrdenCompra(Base):
    __tablename__ = "pagos_orden_compra"

    id_pago = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_orden_compra = Column(
        Integer,
        ForeignKey("ordenes_compra.id_orden_compra", ondelete="CASCADE"),
        nullable=False,
    )
    id_usuario = Column(
        Integer,
        ForeignKey("usuarios.id_usuario"),
        nullable=False,
    )
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    monto = Column(Numeric(10, 2), nullable=False)
    metodo = Column(
        Enum("EFECTIVO", "TARJETA", "TRANSFERENCIA", "CHEQUE", name="metodo_pago_proveedor"),
        nullable=False,
    )
    referencia = Column(String(100), nullable=True)
    observaciones = Column(String(255), nullable=True)

    orden_compra = relationship("OrdenCompra", backref="pagos")
    usuario = relationship("Usuario")
