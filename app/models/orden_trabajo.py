# app/models/orden_trabajo.py
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, date
import enum

class EstadoOrden(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    COTIZADA = "COTIZADA"
    EN_PROCESO = "EN_PROCESO"
    ESPERANDO_REPUESTOS = "ESPERANDO_REPUESTOS"
    ESPERANDO_AUTORIZACION = "ESPERANDO_AUTORIZACION"
    COMPLETADA = "COMPLETADA"
    ENTREGADA = "ENTREGADA"
    CANCELADA = "CANCELADA"

class PrioridadOrden(str, enum.Enum):
    BAJA = "BAJA"
    NORMAL = "NORMAL"
    ALTA = "ALTA"
    URGENTE = "URGENTE"

class OrdenTrabajo(Base):
    """
    Modelo para las órdenes de trabajo del taller
    Registra el trabajo a realizar en un vehículo
    """
    __tablename__ = "ordenes_trabajo"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    numero_orden = Column(String(50), unique=True, nullable=False, index=True)  # OT-YYYYMMDD-0001
    
    # Relaciones con otras tablas
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id_vehiculo"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False, index=True)
    tecnico_id = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True, index=True)  # Técnico asignado
    
    # Información de la orden
    fecha_ingreso = Column(DateTime, nullable=False, default=datetime.now)
    fecha_promesa = Column(DateTime, nullable=True)  # Fecha prometida de entrega
    fecha_inicio = Column(DateTime, nullable=True)  # Cuando se empieza a trabajar
    fecha_finalizacion = Column(DateTime, nullable=True)  # Cuando se termina el trabajo
    fecha_entrega = Column(DateTime, nullable=True)  # Cuando se entrega al cliente
    
    # Estado y prioridad
    estado = Column(SQLEnum(EstadoOrden), nullable=False, default=EstadoOrden.PENDIENTE, index=True)
    prioridad = Column(SQLEnum(PrioridadOrden), nullable=False, default=PrioridadOrden.NORMAL)
    
    # Kilometraje y diagnóstico
    kilometraje = Column(Integer, nullable=True)
    diagnostico_inicial = Column(Text, nullable=True)
    observaciones_cliente = Column(Text, nullable=True)  # Lo que reporta el cliente
    observaciones_tecnico = Column(Text, nullable=True)  # Notas del técnico
    observaciones_entrega = Column(Text, nullable=True)  # Notas al entregar
    
    # Cotización
    fecha_vigencia_cotizacion = Column(Date, nullable=True)  # Vigencia de la cotización

    # Costos
    subtotal_servicios = Column(Numeric(10, 2), nullable=False, default=0.00)
    subtotal_repuestos = Column(Numeric(10, 2), nullable=False, default=0.00)
    descuento = Column(Numeric(10, 2), nullable=False, default=0.00)
    total = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Control
    requiere_autorizacion = Column(Boolean, default=False, nullable=False)
    autorizado = Column(Boolean, default=False, nullable=False)
    fecha_autorizacion = Column(DateTime, nullable=True)
    id_usuario_autorizacion = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    id_usuario_inicio = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    id_usuario_finalizacion = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    id_usuario_entrega = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    cliente_proporciono_refacciones = Column(Boolean, default=False, nullable=False)  # True = no descontar stock al finalizar
    
    # Auditoría cancelación
    motivo_cancelacion = Column(Text, nullable=True)
    fecha_cancelacion = Column(DateTime, nullable=True)
    id_usuario_cancelacion = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    
    # Relaciones
    vehiculo = relationship("Vehiculo", back_populates="ordenes_trabajo")
    cliente = relationship("Cliente", back_populates="ordenes_trabajo")
    tecnico = relationship(
        "Usuario",
        back_populates="ordenes_asignadas",
        foreign_keys=[tecnico_id],
    )
    usuario_autorizacion = relationship("Usuario", foreign_keys=[id_usuario_autorizacion])
    usuario_inicio = relationship("Usuario", foreign_keys=[id_usuario_inicio])
    usuario_finalizacion = relationship("Usuario", foreign_keys=[id_usuario_finalizacion])
    usuario_entrega = relationship("Usuario", foreign_keys=[id_usuario_entrega])
    detalles_servicio = relationship("DetalleOrdenTrabajo", back_populates="orden", cascade="all, delete-orphan")
    detalles_repuesto = relationship("DetalleRepuestoOrden", back_populates="orden", cascade="all, delete-orphan")
    ordenes_compra = relationship("OrdenCompra", back_populates="orden_trabajo")
    
    def __repr__(self):
        return f"<OrdenTrabajo(numero='{self.numero_orden}', estado='{self.estado}', total={self.total})>"

    def calcular_total(self):
        """Calcula el total de la orden"""
        s = Decimal(str(self.subtotal_servicios or 0))
        r = Decimal(str(self.subtotal_repuestos or 0))
        d = Decimal(str(self.descuento or 0))
        self.total = (s + r) - d
        return self.total
