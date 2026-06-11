"""
Transiciones de estado de citas: matriz, ventana 24h, roles, historial y auditoría.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cita import Cita, EstadoCita
from app.models.cita_estado_historial import CitaEstadoHistorial
from app.services.auditoria_service import registrar as registrar_auditoria
from app.utils.fechas import ahora_local

MOTIVO_DETALLE_MIN_LEN = 10
VENTANA_CORRECCION_HORAS = 24

MOTIVOS_CODIGO = frozenset(
    {
        "ERROR_CAPTURA",
        "CLIENTE_TARDE",
        "CLIENTE_CONFIRMO_DESPUES",
        "ERROR_RECEPCION",
        "OTRO",
    }
)

ORIGEN_MANUAL = "MANUAL"
ORIGEN_CONVERTIR_OT = "CONVERTIR_OT"
ORIGEN_RECEPCION_RAPIDA = "RECEPCION_RAPIDA"
ORIGEN_CREACION = "CREACION"

ROLES_MARCACION_INICIAL = frozenset({"ADMIN", "CAJA", "EMPLEADO", "TECNICO"})
ROLES_CORRECCION_OPERATIVA = frozenset({"ADMIN", "CAJA", "EMPLEADO"})
ROLES_REACTIVAR_CANCELADA = frozenset({"ADMIN", "CAJA"})

TRANSICIONES_PERMITIDAS: dict[EstadoCita, frozenset[EstadoCita]] = {
    EstadoCita.CONFIRMADA: frozenset(
        {
            EstadoCita.SI_ASISTIO,
            EstadoCita.NO_ASISTIO,
            EstadoCita.CANCELADA,
        }
    ),
    EstadoCita.SI_ASISTIO: frozenset(
        {
            EstadoCita.CONFIRMADA,
            EstadoCita.NO_ASISTIO,
            EstadoCita.CANCELADA,
        }
    ),
    EstadoCita.NO_ASISTIO: frozenset(
        {
            EstadoCita.SI_ASISTIO,
            EstadoCita.CONFIRMADA,
            EstadoCita.CANCELADA,
        }
    ),
    EstadoCita.CANCELADA: frozenset({EstadoCita.CONFIRMADA}),
}


def _estado_valor(estado) -> str:
    return estado.value if hasattr(estado, "value") else str(estado)


def _parse_estado(valor: str) -> EstadoCita:
    v = (valor or "").upper().replace("REALIZADA", "SI_ASISTIO")
    try:
        return EstadoCita(v)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido: '{valor}'. Use: {', '.join(e.value for e in EstadoCita)}",
        ) from exc


def es_marcacion_inicial(estado_anterior: EstadoCita, estado_nuevo: EstadoCita) -> bool:
    return estado_anterior == EstadoCita.CONFIRMADA and estado_nuevo != EstadoCita.CONFIRMADA


def ventana_correccion_activa(cita: Cita) -> bool:
    """True si ahora está entre fecha_hora de la cita y +24 h."""
    if not cita.fecha_hora:
        return False
    ahora = ahora_local()
    fin = cita.fecha_hora + timedelta(hours=VENTANA_CORRECCION_HORAS)
    return cita.fecha_hora <= ahora <= fin


def _asignar_estado_origen_cierre(cita: Cita, estado_anterior: EstadoCita, estado_nuevo: EstadoCita) -> None:
    if cita.estado_origen_cierre is not None:
        return
    if estado_anterior == EstadoCita.CONFIRMADA and estado_nuevo != EstadoCita.CONFIRMADA:
        cita.estado_origen_cierre = estado_nuevo


def validar_motivo_correccion(motivo_codigo: Optional[str], motivo_detalle: Optional[str]) -> tuple[str, Optional[str]]:
    codigo = (motivo_codigo or "").strip().upper()
    if codigo not in MOTIVOS_CODIGO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"motivo_codigo inválido. Use: {', '.join(sorted(MOTIVOS_CODIGO))}",
        )
    detalle = (motivo_detalle or "").strip() or None
    if codigo == "OTRO":
        if not detalle or len(detalle) < MOTIVO_DETALLE_MIN_LEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Con motivo_codigo OTRO, motivo_detalle debe tener al menos {MOTIVO_DETALLE_MIN_LEN} caracteres.",
            )
    return codigo, detalle


def transicion_permitida_en_matriz(estado_anterior: EstadoCita, estado_nuevo: EstadoCita) -> bool:
    return estado_nuevo in TRANSICIONES_PERMITIDAS.get(estado_anterior, frozenset())


def puede_usuario_transicion(
    *,
    rol: str,
    estado_anterior: EstadoCita,
    estado_nuevo: EstadoCita,
    ventana_activa: bool,
    tiene_ot: bool,
) -> bool:
    if not transicion_permitida_en_matriz(estado_anterior, estado_nuevo):
        return False

    if es_marcacion_inicial(estado_anterior, estado_nuevo):
        return rol in ROLES_MARCACION_INICIAL

    if rol == "TECNICO":
        return False

    if tiene_ot:
        return rol == "ADMIN"

    if estado_anterior == EstadoCita.CANCELADA and estado_nuevo == EstadoCita.CONFIRMADA:
        return rol in ROLES_REACTIVAR_CANCELADA

    if rol == "ADMIN":
        return True

    if rol in ROLES_CORRECCION_OPERATIVA:
        return ventana_activa

    return False


def calcular_estado_meta(cita: Cita, rol: str) -> dict:
    estado_anterior = cita.estado
    ventana = ventana_correccion_activa(cita)
    tiene_ot = cita.id_orden is not None
    destinos = TRANSICIONES_PERMITIDAS.get(estado_anterior, frozenset())
    transiciones = [
        _estado_valor(d)
        for d in destinos
        if puede_usuario_transicion(
            rol=rol,
            estado_anterior=estado_anterior,
            estado_nuevo=d,
            ventana_activa=ventana,
            tiene_ot=tiene_ot,
        )
    ]

    def _destino_requiere_motivo_codigo(destino: EstadoCita) -> bool:
        if es_marcacion_inicial(estado_anterior, destino):
            return False
        return True

    requiere_motivo = any(_destino_requiere_motivo_codigo(EstadoCita(t)) for t in transiciones)

    return {
        "transiciones_permitidas": transiciones,
        "requiere_motivo": requiere_motivo,
        "estado_editable": len(transiciones) > 0,
        "ventana_activa": ventana,
        "tiene_ot": tiene_ot,
        "bloqueo_financiero": False,
    }


def flags_ligeros_estado(cita: Cita, rol: str) -> dict:
    meta = calcular_estado_meta(cita, rol)
    return {
        "estado_editable": meta["estado_editable"],
        "tiene_ot": meta["tiene_ot"],
        "bloqueo_financiero": meta["bloqueo_financiero"],
    }


def _serializar_evento(evento: CitaEstadoHistorial) -> dict:
    return {
        "id": evento.id,
        "id_cita": evento.id_cita,
        "estado_anterior": evento.estado_anterior,
        "estado_nuevo": evento.estado_nuevo,
        "motivo_codigo": evento.motivo_codigo,
        "motivo_detalle": evento.motivo_detalle,
        "id_usuario": evento.id_usuario,
        "id_orden": evento.id_orden,
        "origen": evento.origen,
        "creado_en": evento.creado_en.isoformat() if evento.creado_en else None,
    }


def registrar_evento_historial(
    db: Session,
    *,
    cita: Cita,
    estado_anterior: EstadoCita,
    estado_nuevo: EstadoCita,
    id_usuario: int,
    origen: str,
    motivo_codigo: Optional[str] = None,
    motivo_detalle: Optional[str] = None,
    id_orden: Optional[int] = None,
) -> CitaEstadoHistorial:
    evento = CitaEstadoHistorial(
        id_cita=cita.id_cita,
        estado_anterior=_estado_valor(estado_anterior) if estado_anterior else None,
        estado_nuevo=_estado_valor(estado_nuevo),
        motivo_codigo=motivo_codigo,
        motivo_detalle=motivo_detalle,
        id_usuario=id_usuario,
        id_orden=id_orden if id_orden is not None else cita.id_orden,
        origen=origen,
    )
    db.add(evento)
    db.flush()
    return evento


def registrar_auditoria_correccion(
    db: Session,
    *,
    id_usuario: int,
    cita: Cita,
    estado_anterior: EstadoCita,
    estado_nuevo: EstadoCita,
    motivo_codigo: Optional[str],
    motivo_detalle: Optional[str],
    correccion_con_ot: bool = False,
) -> None:
    payload = {
        "id_cita": cita.id_cita,
        "estado_anterior": _estado_valor(estado_anterior),
        "estado_nuevo": _estado_valor(estado_nuevo),
        "motivo_codigo": motivo_codigo,
        "motivo_detalle": motivo_detalle,
        "id_orden": cita.id_orden,
        "id_usuario": id_usuario,
    }
    if correccion_con_ot:
        payload["correccion_con_ot"] = True
    registrar_auditoria(
        db,
        id_usuario,
        "CITA_ESTADO_CORREGIDO",
        "CITA",
        cita.id_cita,
        payload,
    )


def aplicar_transicion_estado(
    db: Session,
    cita: Cita,
    *,
    estado_nuevo: str,
    id_usuario: int,
    rol: str,
    motivo_codigo: Optional[str] = None,
    motivo_detalle: Optional[str] = None,
    motivo_cancelacion: Optional[str] = None,
) -> tuple[Cita, CitaEstadoHistorial, bool]:
    destino = _parse_estado(estado_nuevo)
    origen_estado = cita.estado

    if destino == origen_estado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cita ya está en ese estado.",
        )

    if not transicion_permitida_en_matriz(origen_estado, destino):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transición no permitida: {_estado_valor(origen_estado)} → {_estado_valor(destino)}.",
        )

    ventana = ventana_correccion_activa(cita)
    tiene_ot = cita.id_orden is not None

    if not puede_usuario_transicion(
        rol=rol,
        estado_anterior=origen_estado,
        estado_nuevo=destino,
        ventana_activa=ventana,
        tiene_ot=tiene_ot,
    ):
        if rol == "TECNICO" and not es_marcacion_inicial(origen_estado, destino):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu rol no permite corregir estados cerrados de citas.",
            )
        if tiene_ot and rol != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo ADMIN puede corregir el estado de una cita con OT vinculada.",
            )
        if origen_estado == EstadoCita.CANCELADA and destino == EstadoCita.CONFIRMADA:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo ADMIN o CAJA pueden reactivar una cita cancelada.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para esta corrección (ventana de 24 h expirada o rol insuficiente).",
        )

    inicial = es_marcacion_inicial(origen_estado, destino)
    motivo_codigo_final: Optional[str] = None
    motivo_detalle_final: Optional[str] = None

    if destino == EstadoCita.CANCELADA:
        mc = (motivo_cancelacion or "").strip()
        if not mc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Al cancelar una cita debes indicar motivo_cancelacion.",
            )
        cita.motivo_cancelacion = mc
        if not inicial:
            motivo_codigo_final, motivo_detalle_final = validar_motivo_correccion(motivo_codigo, motivo_detalle)
    elif inicial:
        pass
    else:
        motivo_codigo_final, motivo_detalle_final = validar_motivo_correccion(motivo_codigo, motivo_detalle)

    _asignar_estado_origen_cierre(cita, origen_estado, destino)
    cita.estado = destino

    evento = registrar_evento_historial(
        db,
        cita=cita,
        estado_anterior=origen_estado,
        estado_nuevo=destino,
        id_usuario=id_usuario,
        origen=ORIGEN_MANUAL,
        motivo_codigo=motivo_codigo_final,
        motivo_detalle=motivo_detalle_final,
        id_orden=cita.id_orden,
    )

    if not inicial:
        pass  # auditoría se registra fuera de la transacción DB principal

    return cita, evento, not inicial


def registrar_evento_vinculo_ot(
    db: Session,
    cita: Cita,
    *,
    estado_anterior: EstadoCita,
    estado_nuevo: EstadoCita,
    id_usuario: int,
    id_orden: int,
    origen: str,
) -> None:
    if estado_anterior == estado_nuevo:
        return
    _asignar_estado_origen_cierre(cita, estado_anterior, estado_nuevo)
    registrar_evento_historial(
        db,
        cita=cita,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        id_usuario=id_usuario,
        origen=origen,
        id_orden=id_orden,
    )


def registrar_evento_creacion(
    db: Session,
    cita: Cita,
    id_usuario: int,
) -> CitaEstadoHistorial:
    evento = CitaEstadoHistorial(
        id_cita=cita.id_cita,
        estado_anterior=None,
        estado_nuevo=_estado_valor(EstadoCita.CONFIRMADA),
        id_usuario=id_usuario,
        id_orden=None,
        origen=ORIGEN_CREACION,
    )
    db.add(evento)
    db.flush()
    return evento
