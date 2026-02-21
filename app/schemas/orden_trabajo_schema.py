# app/schemas/orden_trabajo.py
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# ============= Schemas para Detalles de Servicios =============

class DetalleServicioBase(BaseModel):
    servicio_id: int = Field(..., gt=0, description="ID del servicio")
    cantidad: int = Field(default=1, ge=1, description="Cantidad de veces que se aplica el servicio")
    precio_unitario: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Precio unitario (si es diferente al catálogo)")
    descuento: Decimal = Field(default=0.00, ge=0, decimal_places=2, description="Descuento aplicado")
    descripcion: Optional[str] = Field(None, max_length=500, description="Descripción personalizada")
    observaciones: Optional[str] = None

class DetalleServicioCreate(DetalleServicioBase):
    pass

class DetalleServicioResponse(DetalleServicioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    orden_trabajo_id: int
    subtotal: Decimal
    tiempo_real_minutos: Optional[int]

# ============= Schemas para Detalles de Repuestos =============

class DetalleRepuestoBase(BaseModel):
    repuesto_id: Optional[int] = Field(None, gt=0, description="ID del repuesto (omitir si descripcion_libre)")
    descripcion_libre: Optional[str] = Field(None, max_length=300, description="Descripción cuando no existe en inventario")
    cantidad: Decimal = Field(..., ge=0.001, description="Cantidad (permite decimales: 2.5 L). Mínimo 0.001.")
    precio_unitario: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Precio unitario (si es diferente al catálogo)")
    precio_compra_estimado: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Precio compra estimado (para markup)")
    descuento: Decimal = Field(default=0.00, ge=0, decimal_places=2, description="Descuento aplicado")
    observaciones: Optional[str] = None

class DetalleRepuestoCreate(DetalleRepuestoBase):
    @model_validator(mode='after')
    def repuesto_o_descripcion(self):
        rep = self.repuesto_id
        desc = (self.descripcion_libre or '').strip()
        if (rep is None or rep <= 0) and not desc:
            raise ValueError("Debe indicar repuesto_id o descripcion_libre")
        return self

class DetalleRepuestoResponse(DetalleRepuestoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    orden_trabajo_id: int
    subtotal: Decimal

# ============= Schemas para Orden de Trabajo =============

class OrdenTrabajoBase(BaseModel):
    vehiculo_id: int = Field(..., gt=0, description="ID del vehículo")
    cliente_id: int = Field(..., gt=0, description="ID del cliente")
    tecnico_id: Optional[int] = Field(None, gt=0, description="ID del técnico asignado")
    id_vendedor: Optional[int] = Field(None, gt=0, description="Comisiones: quien hizo seguimiento y cobra al concretar")
    fecha_promesa: Optional[datetime] = Field(None, description="Fecha prometida de entrega")
    fecha_vigencia_cotizacion: Optional[datetime] = Field(None, description="Vigencia de la cotización (fecha)")
    prioridad: str = Field(default="NORMAL", description="Prioridad de la orden")
    kilometraje: Optional[int] = Field(None, ge=0, description="Kilometraje del vehículo")
    diagnostico_inicial: Optional[str] = None
    observaciones_cliente: Optional[str] = None
    observaciones_tecnico: Optional[str] = None
    requiere_autorizacion: bool = Field(default=False, description="Si requiere autorización del cliente")
    cliente_proporciono_refacciones: bool = Field(default=False, description="Si el cliente trajo refacciones (total o parcial); no se descuenta inventario al finalizar")

    @field_validator('prioridad')
    @classmethod
    def validar_prioridad(cls, v):
        if v is None:
            return v
        v_str = v.value if hasattr(v, "value") else str(v)
        prioridades_validas = ["BAJA", "NORMAL", "ALTA", "URGENTE"]
        if v_str not in prioridades_validas:
            raise ValueError(f"Prioridad debe ser una de: {', '.join(prioridades_validas)}")
        return v_str

class OrdenTrabajoCreate(OrdenTrabajoBase):
    """Schema para crear una orden de trabajo"""
    servicios: List[DetalleServicioCreate] = Field(default=[], description="Lista de servicios a realizar")
    repuestos: List[DetalleRepuestoCreate] = Field(default=[], description="Lista de repuestos a utilizar")
    descuento: Decimal = Field(default=0.00, ge=0, decimal_places=2, description="Descuento general en la orden")

class OrdenTrabajoUpdate(BaseModel):
    """Schema para actualizar una orden de trabajo"""
    tecnico_id: Optional[int] = Field(None, gt=0)
    id_vendedor: Optional[int] = Field(None, gt=0)
    fecha_promesa: Optional[datetime] = None
    fecha_vigencia_cotizacion: Optional[datetime] = None
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    kilometraje: Optional[int] = Field(None, ge=0)
    diagnostico_inicial: Optional[str] = None
    observaciones_cliente: Optional[str] = None
    observaciones_tecnico: Optional[str] = None
    observaciones_entrega: Optional[str] = None
    descuento: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    requiere_autorizacion: Optional[bool] = None
    autorizado: Optional[bool] = None
    cliente_proporciono_refacciones: Optional[bool] = None
    servicios: Optional[List[DetalleServicioCreate]] = None  # Solo aplica si orden está PENDIENTE
    repuestos: Optional[List[DetalleRepuestoCreate]] = None  # Solo aplica si orden está PENDIENTE

    @field_validator('estado')
    @classmethod
    def validar_estado(cls, v):
        if v is None:
            return v
        estados_validos = [
            "PENDIENTE", "COTIZADA", "EN_PROCESO", "ESPERANDO_REPUESTOS",
            "ESPERANDO_AUTORIZACION", "COMPLETADA", "ENTREGADA", "CANCELADA"
        ]
        if v not in estados_validos:
            raise ValueError(f"Estado debe ser uno de: {', '.join(estados_validos)}")
        return v

    @field_validator('prioridad')
    @classmethod
    def validar_prioridad(cls, v):
        if v is None:
            return v
        prioridades_validas = ["BAJA", "NORMAL", "ALTA", "URGENTE"]
        if v not in prioridades_validas:
            raise ValueError(f"Prioridad debe ser una de: {', '.join(prioridades_validas)}")
        return v

class OrdenTrabajoResponse(OrdenTrabajoBase):
    """Schema para respuesta con datos completos de la orden"""
    id: int
    numero_orden: str
    fecha_ingreso: datetime
    fecha_inicio: Optional[datetime]
    fecha_finalizacion: Optional[datetime]
    fecha_entrega: Optional[datetime]
    estado: str
    subtotal_servicios: Decimal
    subtotal_repuestos: Decimal
    descuento: Decimal
    total: Decimal
    autorizado: bool
    fecha_autorizacion: Optional[datetime]

    # Auditoría cancelación
    motivo_cancelacion: Optional[str] = None
    fecha_cancelacion: Optional[datetime] = None
    id_usuario_cancelacion: Optional[int] = None

    # Detalles
    detalles_servicio: List[DetalleServicioResponse] = []
    detalles_repuesto: List[DetalleRepuestoResponse] = []

    # Cancelar: cuando se crea venta con repuestos utilizados
    id_venta_nueva: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class OrdenTrabajoListResponse(BaseModel):
    """Schema para listado de órdenes"""
    model_config = ConfigDict(from_attributes=True)
    ordenes: list[OrdenTrabajoResponse]
    total: int
    pagina: int
    total_paginas: int

# ============= Schemas para Acciones Específicas =============

class IniciarOrdenRequest(BaseModel):
    """Request para iniciar una orden"""
    observaciones_inicio: Optional[str] = None

class FinalizarOrdenRequest(BaseModel):
    """Request para finalizar una orden"""
    observaciones_finalizacion: Optional[str] = None

class EntregarOrdenRequest(BaseModel):
    """Request para entregar una orden al cliente"""
    observaciones_entrega: Optional[str] = None

class AutorizarOrdenRequest(BaseModel):
    """Request para autorizar una orden"""
    autorizado: bool = Field(..., description="True para autorizar, False para rechazar")
    observaciones: Optional[str] = None

class AgregarServicioRequest(DetalleServicioCreate):
    """Request para agregar un servicio a una orden existente"""
    pass

class AgregarRepuestoRequest(DetalleRepuestoCreate):
    """Request para agregar un repuesto a una orden existente"""
    pass


class DevolucionRepuestoItem(BaseModel):
    """Indica si un repuesto se devuelve al inventario o se cobra (usado)"""
    id_detalle: int = Field(..., description="ID del detalle (DetalleRepuestoOrden)")
    devolver: bool = Field(..., description="True = devolver al inventario, False = usado (se cobrará)")
    cantidad_a_devolver: Optional[Decimal] = Field(
        None, ge=0,
        description="Cantidad a devolver (opcional). Si no se indica y devolver=True, se devuelve todo."
    )


class CancelarOrdenBody(BaseModel):
    """Body opcional para cancelar con selección por repuesto"""
    devolucion_repuestos: Optional[List[DevolucionRepuestoItem]] = Field(
        None,
        description="Por cada repuesto: devolver (sí/no) y opcionalmente cantidad. Si no se envía, se usa lógica legacy."
    )
