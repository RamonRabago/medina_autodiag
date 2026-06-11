# Cotizaciones de refacciones no locales (importación / compra en línea)
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from app.database import Base


class EstadoCotizacionRefaccion(str, enum.Enum):
    BORRADOR = "BORRADOR"
    ENVIADA = "ENVIADA"
    ACEPTADA_CLIENTE = "ACEPTADA_CLIENTE"
    EN_COMPRA = "EN_COMPRA"
    RECIBIDA = "RECIBIDA"
    ENTREGADA = "ENTREGADA"
    CANCELADA = "CANCELADA"


class MonedaCotizacion(str, enum.Enum):
    USD = "USD"
    MXN = "MXN"


class MetodoPagoCompraRefaccion(str, enum.Enum):
    PAYPAL = "PAYPAL"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"
    OTRO = "OTRO"


class CotizacionRefaccionEspecial(Base):
    """
    Cabecera: cotización de refacciones fuera del stock local / importación.
    Opcionalmente vinculada a vehículo u orden de trabajo.
    """

    __tablename__ = "cotizaciones_refaccion_especial"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(50), unique=True, nullable=False, index=True)

    id_cliente = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False, index=True)
    id_vehiculo = Column(Integer, ForeignKey("vehiculos.id_vehiculo"), nullable=True, index=True)
    id_orden_trabajo = Column(Integer, ForeignKey("ordenes_trabajo.id", ondelete="SET NULL"), nullable=True, index=True)

    id_usuario_creo = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)

    estado = Column(
        SQLEnum(
            EstadoCotizacionRefaccion,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=EstadoCotizacionRefaccion.BORRADOR,
        index=True,
    )

    notas_generales = Column(Text, nullable=True)
    tc_referencia_usd_mxn = Column(Numeric(12, 4), nullable=True)
    margen_objetivo_pct = Column(Numeric(5, 2), nullable=True)

    congelada = Column(Boolean, nullable=False, default=False)

    id_usuario_aceptacion = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    fecha_aceptacion_cliente = Column(DateTime, nullable=True)

    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", foreign_keys=[id_cliente])
    vehiculo = relationship("Vehiculo", foreign_keys=[id_vehiculo])
    orden_trabajo = relationship("OrdenTrabajo", foreign_keys=[id_orden_trabajo])
    usuario_creo = relationship("Usuario", foreign_keys=[id_usuario_creo])
    usuario_aceptacion = relationship("Usuario", foreign_keys=[id_usuario_aceptacion])

    lineas = relationship(
        "LineaCotizacionRefaccion",
        back_populates="cotizacion",
        cascade="all, delete-orphan",
        order_by="LineaCotizacionRefaccion.n_linea",
    )
    comentarios = relationship(
        "ComentarioCotizacionRefaccion",
        back_populates="cotizacion",
        cascade="all, delete-orphan",
        order_by="ComentarioCotizacionRefaccion.creado_en",
    )
    compras_ejecutadas = relationship(
        "CompraEjecutadaCotizacionRefaccion",
        back_populates="cotizacion",
        cascade="all, delete-orphan",
    )


class LineaCotizacionRefaccion(Base):
    __tablename__ = "lineas_cotizacion_refaccion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cotizacion = Column(
        Integer,
        ForeignKey("cotizaciones_refaccion_especial.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    n_linea = Column(Integer, nullable=False, default=1)
    descripcion = Column(Text, nullable=False)
    cantidad = Column(Numeric(10, 3), nullable=False, default=Decimal("1"))
    posicion_lado = Column(String(80), nullable=True)
    observaciones = Column(Text, nullable=True)

    cotizacion = relationship("CotizacionRefaccionEspecial", back_populates="lineas")
    opciones = relationship(
        "OpcionCompraLineaCotizacion",
        back_populates="linea",
        cascade="all, delete-orphan",
        foreign_keys="OpcionCompraLineaCotizacion.id_linea",
    )


class OpcionCompraLineaCotizacion(Base):
    __tablename__ = "opciones_compra_linea_cotizacion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_linea = Column(
        Integer,
        ForeignKey("lineas_cotizacion_refaccion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    origen_nombre = Column(String(160), nullable=False)
    url_compra = Column(String(2048), nullable=True)
    moneda = Column(
        SQLEnum(
            MonedaCotizacion,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
            length=3,
        ),
        nullable=False,
        default=MonedaCotizacion.MXN,
    )
    monto_unitario = Column(Numeric(12, 2), nullable=False)
    tipo_cambio_a_mxn = Column(Numeric(12, 4), nullable=True)
    otros_costos_mxn = Column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    dias_estimados_entrega = Column(Integer, nullable=True)
    notas = Column(Text, nullable=True)
    es_preferida = Column(Boolean, nullable=False, default=False)

    linea = relationship(
        "LineaCotizacionRefaccion",
        back_populates="opciones",
        foreign_keys=[id_linea],
    )


class ComentarioCotizacionRefaccion(Base):
    __tablename__ = "comentarios_cotizacion_refaccion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cotizacion = Column(
        Integer,
        ForeignKey("cotizaciones_refaccion_especial.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    mensaje = Column(Text, nullable=False)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    cotizacion = relationship("CotizacionRefaccionEspecial", back_populates="comentarios")
    usuario = relationship("Usuario", foreign_keys=[id_usuario])


class CompraEjecutadaCotizacionRefaccion(Base):
    """Registro de compra real (PayPal, tarjeta, etc.), sin depender de orden de compra formal."""

    __tablename__ = "compras_ejecutadas_cotizacion_refaccion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cotizacion = Column(
        Integer,
        ForeignKey("cotizaciones_refaccion_especial.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_linea = Column(
        Integer,
        ForeignKey("lineas_cotizacion_refaccion.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    id_opcion = Column(
        Integer,
        ForeignKey("opciones_compra_linea_cotizacion.id", ondelete="SET NULL"),
        nullable=True,
    )

    monto_pagado = Column(Numeric(12, 2), nullable=False)
    moneda = Column(
        SQLEnum(
            MonedaCotizacion,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
            length=3,
        ),
        nullable=False,
        default=MonedaCotizacion.MXN,
    )
    tipo_cambio_aplicado = Column(Numeric(12, 4), nullable=True)
    metodo = Column(
        SQLEnum(
            MetodoPagoCompraRefaccion,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
            length=20,
        ),
        nullable=False,
        default=MetodoPagoCompraRefaccion.OTRO,
    )

    comprobante_url = Column(String(500), nullable=True)
    notas = Column(Text, nullable=True)
    fecha_pago = Column(DateTime, nullable=False, default=datetime.utcnow)
    id_usuario_registro = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)

    cotizacion = relationship("CotizacionRefaccionEspecial", back_populates="compras_ejecutadas")
    linea = relationship("LineaCotizacionRefaccion", foreign_keys=[id_linea])
    opcion = relationship("OpcionCompraLineaCotizacion", foreign_keys=[id_opcion])
    usuario_registro = relationship("Usuario", foreign_keys=[id_usuario_registro])
