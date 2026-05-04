"""Schemas Pydantic — cotizaciones refacción especial."""
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.cotizacion_refaccion_especial import EstadoCotizacionRefaccion


class CotizacionRefaccionCreate(BaseModel):
    id_cliente: int = Field(..., gt=0)
    id_vehiculo: Optional[int] = Field(None, gt=0)
    id_orden_trabajo: Optional[int] = Field(None, gt=0)
    notas_generales: Optional[str] = None
    tc_referencia_usd_mxn: Optional[Decimal] = None
    margen_objetivo_pct: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("500"))


class CotizacionRefaccionUpdate(BaseModel):
    id_vehiculo: Optional[int] = Field(None, gt=0)
    id_orden_trabajo: Optional[int] = Field(None, gt=0)
    notas_generales: Optional[str] = None
    tc_referencia_usd_mxn: Optional[Decimal] = None
    margen_objetivo_pct: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("500"))


class LineaCreate(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=2000)
    cantidad: Decimal = Field(default=Decimal("1"), gt=0)
    posicion_lado: Optional[str] = Field(None, max_length=80)
    observaciones: Optional[str] = None


class LineaUpdate(BaseModel):
    descripcion: Optional[str] = Field(None, min_length=1, max_length=2000)
    cantidad: Optional[Decimal] = Field(None, gt=0)
    posicion_lado: Optional[str] = Field(None, max_length=80)
    observaciones: Optional[str] = None


class OpcionCreate(BaseModel):
    origen_nombre: str = Field(..., min_length=1, max_length=160)
    url_compra: Optional[str] = Field(None, max_length=2048)
    moneda: str = Field(default="MXN", pattern="^(USD|MXN)$")
    monto_unitario: Decimal = Field(..., ge=Decimal("0"))
    tipo_cambio_a_mxn: Optional[Decimal] = None
    otros_costos_mxn: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    dias_estimados_entrega: Optional[int] = Field(None, ge=0)
    notas: Optional[str] = None
    es_preferida: bool = False


class OpcionUpdate(BaseModel):
    origen_nombre: Optional[str] = Field(None, min_length=1, max_length=160)
    url_compra: Optional[str] = Field(None, max_length=2048)
    moneda: Optional[str] = Field(None, pattern="^(USD|MXN)$")
    monto_unitario: Optional[Decimal] = Field(None, ge=Decimal("0"))
    tipo_cambio_a_mxn: Optional[Decimal] = None
    otros_costos_mxn: Optional[Decimal] = Field(None, ge=Decimal("0"))
    dias_estimados_entrega: Optional[int] = Field(None, ge=0)
    notas: Optional[str] = None
    es_preferida: Optional[bool] = None


class ComentarioCreate(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=8000)


class CompraRegistradaIn(BaseModel):
    id_linea: Optional[int] = None
    id_opcion: Optional[int] = None
    monto_pagado: Decimal = Field(..., gt=Decimal("0"))
    moneda: str = Field(default="MXN", pattern="^(USD|MXN)$")
    tipo_cambio_aplicado: Optional[Decimal] = None
    metodo: str = Field(default="OTRO", pattern="^(PAYPAL|TARJETA|TRANSFERENCIA|OTRO)$")
    comprobante_url: Optional[str] = Field(None, max_length=500)
    notas: Optional[str] = None

    @field_validator("tipo_cambio_aplicado", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        if v == "" or v is None:
            return None
        return v


class OpcionOut(BaseModel):
    id: int
    id_linea: int
    origen_nombre: str
    url_compra: Optional[str] = None
    moneda: str
    monto_unitario: Decimal
    tipo_cambio_a_mxn: Optional[Decimal] = None
    otros_costos_mxn: Decimal
    dias_estimados_entrega: Optional[int] = None
    notas: Optional[str] = None
    es_preferida: bool
    costo_unitario_mxn: Optional[Decimal] = None
    precio_sugerido_linea: Optional[Decimal] = None
    ganancia_estimada_linea: Optional[Decimal] = None
    costo_error: Optional[str] = None

    class Config:
        from_attributes = True


class LineaOut(BaseModel):
    id: int
    id_cotizacion: int
    n_linea: int
    descripcion: str
    cantidad: Decimal
    posicion_lado: Optional[str] = None
    observaciones: Optional[str] = None
    opciones: List[OpcionOut] = []


class ComentarioOut(BaseModel):
    id: int
    id_cotizacion: int
    id_usuario: int
    usuario_nombre: Optional[str] = None
    mensaje: str
    creado_en: datetime

    class Config:
        from_attributes = True


class CompraOut(BaseModel):
    id: int
    id_cotizacion: int
    id_linea: Optional[int] = None
    id_opcion: Optional[int] = None
    monto_pagado: Decimal
    moneda: str
    tipo_cambio_aplicado: Optional[Decimal] = None
    metodo: str
    comprobante_url: Optional[str] = None
    notas: Optional[str] = None
    fecha_pago: datetime
    id_usuario_registro: int

    class Config:
        from_attributes = True


class CotizacionRefaccionDetail(BaseModel):
    id: int
    numero: str
    id_cliente: int
    cliente_nombre: Optional[str] = None
    id_vehiculo: Optional[int] = None
    vehiculo_texto: Optional[str] = None
    id_orden_trabajo: Optional[int] = None
    id_usuario_creo: int
    creador_nombre: Optional[str] = None
    estado: str
    notas_generales: Optional[str] = None
    tc_referencia_usd_mxn: Optional[Decimal] = None
    margen_objetivo_pct: Optional[Decimal] = None
    congelada: bool
    id_usuario_aceptacion: Optional[int] = None
    fecha_aceptacion_cliente: Optional[datetime] = None
    creado_en: datetime
    actualizado_en: datetime
    lineas: List[LineaOut] = []
    comentarios: List[ComentarioOut] = []
    compras_ejecutadas: List[CompraOut] = []
    totales: Optional[dict] = None


class CotizacionListaItem(BaseModel):
    id: int
    numero: str
    id_cliente: int
    cliente_nombre: Optional[str] = None
    estado: str
    creado_en: datetime
    actualizado_en: datetime


class ListaResponse(BaseModel):
    items: List[CotizacionListaItem]
    total: int
    pagina: int
    total_paginas: int
