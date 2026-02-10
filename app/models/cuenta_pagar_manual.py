"""
Cuentas por pagar manuales (sin orden de compra).
Para facturas, renta, servicios, etc. que no pasan por OC.
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, String, Text, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from app.database import Base


class CuentaPagarManual(Base):
    __tablename__ = "cuentas_pagar_manual"

    id_cuenta = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_proveedor = Column(
        Integer,
        ForeignKey("proveedores.id_proveedor", ondelete="SET NULL"),
        nullable=True,
        comment="Proveedor si existe en catálogo; null para acreedores externos",
    )
    acreedor_nombre = Column(
        String(150),
        nullable=True,
        comment="Nombre del acreedor cuando no hay id_proveedor (ej. CFE, arrendador)",
    )
    referencia_factura = Column(String(80), nullable=True, comment="Nº factura o referencia contable")
    concepto = Column(String(200), nullable=False)
    monto_total = Column(Numeric(10, 2), nullable=False)
    fecha_registro = Column(Date, nullable=False, server_default=text("(CURDATE())"))
    fecha_vencimiento = Column(Date, nullable=True)
    observaciones = Column(Text, nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    cancelada = Column(Boolean, default=False, nullable=False)
    creado_en = Column(DateTime, server_default=func.now())

    proveedor = relationship("Proveedor")
    usuario = relationship("Usuario")
    pagos = relationship("PagoCuentaPagarManual", back_populates="cuenta", cascade="all, delete-orphan")


class PagoCuentaPagarManual(Base):
    __tablename__ = "pagos_cuenta_pagar_manual"

    id_pago = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_cuenta = Column(
        Integer,
        ForeignKey("cuentas_pagar_manual.id_cuenta", ondelete="CASCADE"),
        nullable=False,
    )
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_turno = Column(
        Integer,
        ForeignKey("caja_turnos.id_turno"),
        nullable=True,
        comment="Turno de caja cuando el pago es en efectivo",
    )
    fecha = Column(DateTime, nullable=False, default=func.now())
    monto = Column(Numeric(10, 2), nullable=False)
    metodo = Column(
        String(20),
        nullable=False,
        comment="EFECTIVO, TARJETA, TRANSFERENCIA, CHEQUE",
    )
    referencia = Column(String(100), nullable=True)
    observaciones = Column(String(255), nullable=True)

    cuenta = relationship("CuentaPagarManual", back_populates="pagos")
    usuario = relationship("Usuario")
