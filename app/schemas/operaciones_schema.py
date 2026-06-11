"""Schemas — Capa Operativa Central A0."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AccionOperativaOut(BaseModel):
    accion: str
    permitida: bool
    motivo_bloqueo: Optional[str] = None
    codigo_bloqueo: Optional[str] = None
    alcance: Optional[str] = None
    contexto: Optional[dict[str, Any]] = None


class BloqueoFinancieroOut(BaseModel):
    bloqueo_financiero: bool = False
    motivo_bloqueo: Optional[str] = None


class CajaResumenOut(BaseModel):
    turno_abierto: bool = False
    id_turno: Optional[int] = None
    alerta_turno_largo: bool = False


class AlertaOperativaOut(BaseModel):
    codigo: str
    severidad: str
    mensaje: str
    cantidad: int = 0


class MetaResumenOut(BaseModel):
    limit_items: int
    incluir_items: bool
    version_contrato: str = "a0-v2"


class UsuarioResumenOut(BaseModel):
    id_usuario: int
    rol: str
    nombre: str


class BandejaOut(BaseModel):
    total: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)


class MetricasOperativasOut(BaseModel):
    citas_pendientes_asistencia: int = 0
    citas_convertibles: int = 0
    ot_pendientes: int = 0
    ot_en_proceso: int = 0
    ot_completadas: int = 0
    ot_pendientes_cobro: int = 0
    ot_listas_entrega: int = 0
    ventas_saldo_pendiente: int = 0
    refacciones_en_compra: int = 0
    refacciones_recibidas_pendiente_entrega: int = 0


class OperacionesResumenOut(BaseModel):
    generado_en: str
    usuario: UsuarioResumenOut
    bloqueo_financiero: BloqueoFinancieroOut
    acciones_globales: list[AccionOperativaOut]
    metricas: MetricasOperativasOut
    bandejas: dict[str, BandejaOut]
    alertas_operativas: list[AlertaOperativaOut]
    caja: CajaResumenOut
    meta: MetaResumenOut
