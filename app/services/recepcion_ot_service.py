"""
Lógica compartida: OT mínima PENDIENTE (recepción rápida) y vínculo cita ↔ OT.
"""

from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cita import Cita, EstadoCita
from app.models.cliente import Cliente
from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.routers.ordenes_trabajo.helpers import generar_numero_orden
from app.utils.fechas import ahora_local_naive

MOTIVO_MIN_LEN = 10


def construir_motivo_desde_cita(cita: Cita) -> str:
    """Combina motivo, notas y tipo de cita en texto apto para OT (≥10 chars)."""
    partes = []
    if cita.motivo and str(cita.motivo).strip():
        partes.append(str(cita.motivo).strip())
    if cita.notas and str(cita.notas).strip():
        notas = str(cita.notas).strip()
        if notas not in partes:
            partes.append(notas)
    if not partes:
        tip = cita.tipo.value if hasattr(cita.tipo, "value") else str(cita.tipo or "OTRO")
        partes.append(f"Cita {tip.replace('_', ' ').title()}")
    texto = " — ".join(partes) if len(partes) > 1 else partes[0]
    if len(texto) < MOTIVO_MIN_LEN:
        texto = f"{texto} (cita #{cita.id_cita})"
    return texto[:2000]


def validar_motivo_texto(motivo: str) -> str:
    m = (motivo or "").strip()
    if len(m) < MOTIVO_MIN_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El motivo debe tener al menos {MOTIVO_MIN_LEN} caracteres.",
        )
    return m


def validar_cliente_y_vehiculo(db: Session, cliente_id: int, vehiculo_id: int) -> tuple[Cliente, Vehiculo]:
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehículo con ID {vehiculo_id} no encontrado",
        )
    cliente = db.query(Cliente).filter(Cliente.id_cliente == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente con ID {cliente_id} no encontrado",
        )
    if vehiculo.id_cliente != cliente_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El vehículo no pertenece al cliente seleccionado.",
        )
    return cliente, vehiculo


def validar_tecnico_opcional(db: Session, tecnico_id: Optional[int]) -> None:
    if not tecnico_id:
        return
    tecnico = (
        db.query(Usuario)
        .filter(
            Usuario.id_usuario == tecnico_id,
            Usuario.rol == "TECNICO",
        )
        .first()
    )
    if not tecnico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Técnico con ID {tecnico_id} no encontrado",
        )


def crear_ot_minima_pendiente(
    db: Session,
    *,
    cliente_id: int,
    vehiculo_id: int,
    motivo: str,
    id_usuario_creo: int,
    prioridad: str = "NORMAL",
    tecnico_id: Optional[int] = None,
    kilometraje: Optional[int] = None,
    requiere_autorizacion: bool = False,
) -> OrdenTrabajo:
    """Crea OT mínima en PENDIENTE (sin commit; usar dentro de transaction)."""
    motivo_limpio = validar_motivo_texto(motivo)
    validar_cliente_y_vehiculo(db, cliente_id, vehiculo_id)
    validar_tecnico_opcional(db, tecnico_id)

    numero_orden = generar_numero_orden(db)
    nueva_orden = OrdenTrabajo(
        numero_orden=numero_orden,
        vehiculo_id=vehiculo_id,
        cliente_id=cliente_id,
        tecnico_id=tecnico_id,
        id_usuario_creo=id_usuario_creo,
        fecha_ingreso=ahora_local_naive(),
        prioridad=prioridad,
        kilometraje=kilometraje,
        diagnostico_inicial=motivo_limpio,
        observaciones_cliente=motivo_limpio,
        requiere_autorizacion=requiere_autorizacion,
        estado=EstadoOrden.PENDIENTE,
        subtotal_servicios=Decimal("0.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
        total=Decimal("0.00"),
    )
    db.add(nueva_orden)
    db.flush()
    return nueva_orden


ESTADOS_CITA_CONVERTIBLES = frozenset({EstadoCita.CONFIRMADA, EstadoCita.SI_ASISTIO})


def evaluar_cita_convertible(cita: Cita, *, requiere_vehiculo: bool = True) -> dict:
    """
    Evalúa si una cita puede convertirse a OT (solo lectura).
    Misma lógica que validar_cita_convertible sin HTTPException.

    requiere_vehiculo=True por defecto (Citas V2 y bandeja A0).
    requiere_vehiculo=False solo para casos excepcionales de lectura; no usar en convertir-orden.
    """
    est = cita.estado.value if hasattr(cita.estado, "value") else str(cita.estado)
    if est == EstadoCita.CANCELADA.value:
        return {
            "convertible": False,
            "motivo": "No se puede convertir una cita cancelada.",
            "codigo": "CITA_CANCELADA",
        }
    if est == EstadoCita.NO_ASISTIO.value:
        return {
            "convertible": False,
            "motivo": "No se puede convertir una cita marcada como no asistió. "
            "Cámbiala a «Sí asistió» o reactívala antes de crear la OT.",
            "codigo": "ESTADO_NO_CONVERTIBLE",
            "estado": est,
        }
    if cita.estado not in ESTADOS_CITA_CONVERTIBLES:
        return {
            "convertible": False,
            "motivo": f"Solo citas CONFIRMADA o SI_ASISTIO pueden convertirse a OT (estado actual: {est}).",
            "codigo": "ESTADO_NO_CONVERTIBLE",
            "estado": est,
        }
    if cita.id_orden is not None:
        return {
            "convertible": False,
            "motivo": "La cita ya tiene una orden de trabajo vinculada.",
            "codigo": "VER_ORDEN",
            "id_orden": cita.id_orden,
            "redirect": f"/ordenes-trabajo/{cita.id_orden}",
        }
    if not cita.id_cliente:
        return {
            "convertible": False,
            "motivo": "La cita no tiene cliente asignado.",
            "codigo": "SIN_CLIENTE",
        }
    if requiere_vehiculo and not cita.id_vehiculo:
        return {
            "convertible": False,
            "motivo": "La cita no tiene vehículo asignado. Completa el vehículo antes de convertir a OT.",
            "codigo": "COMPLETAR_RECEPCION",
            "redirect": f"/operaciones/recepcion?cita_id={cita.id_cita}",
        }
    return {"convertible": True, "motivo": None, "codigo": None}


def validar_cita_convertible(cita: Cita, id_cita: int) -> None:
    ev = evaluar_cita_convertible(cita, requiere_vehiculo=True)
    if ev.get("convertible"):
        return

    codigo = ev.get("codigo")
    motivo = ev.get("motivo") or "No se puede convertir la cita."

    if codigo == "CITA_CANCELADA" or codigo == "SIN_CLIENTE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=motivo,
        )
    if codigo == "ESTADO_NO_CONVERTIBLE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "mensaje": motivo,
                "accion": "ESTADO_NO_CONVERTIBLE",
                "estado": ev.get("estado"),
            },
        )
    if codigo == "VER_ORDEN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "mensaje": motivo,
                "accion": "VER_ORDEN",
                "id_orden": ev.get("id_orden"),
                "redirect": ev.get("redirect"),
            },
        )
    if codigo == "COMPLETAR_RECEPCION":
        raise error_cita_sin_vehiculo(id_cita)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=motivo,
    )


def error_cita_sin_vehiculo(id_cita: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "mensaje": "La cita no tiene vehículo asignado. Completa el vehículo antes de convertir a OT.",
            "accion": "COMPLETAR_RECEPCION",
            "redirect": f"/operaciones/recepcion?cita_id={id_cita}",
        },
    )


def vincular_cita_a_orden(
    db: Session,
    cita: Cita,
    orden_id: int,
    *,
    id_usuario: int | None = None,
    origen: str = "CONVERTIR_OT",
) -> None:
    """Asocia cita con OT. CONFIRMADA pasa a SI_ASISTIO; SI_ASISTIO se conserva."""
    from app.services.cita_estado_service import (
        ORIGEN_CONVERTIR_OT,
        ORIGEN_RECEPCION_RAPIDA,
        registrar_evento_vinculo_ot,
    )

    estado_anterior = cita.estado
    cita.id_orden = orden_id
    estado_nuevo = cita.estado
    if cita.estado != EstadoCita.SI_ASISTIO:
        cita.estado = EstadoCita.SI_ASISTIO
        estado_nuevo = EstadoCita.SI_ASISTIO

    if id_usuario is not None and estado_anterior != estado_nuevo:
        origen_evento = origen if origen in (ORIGEN_CONVERTIR_OT, ORIGEN_RECEPCION_RAPIDA) else ORIGEN_CONVERTIR_OT
        registrar_evento_vinculo_ot(
            db,
            cita,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            id_usuario=id_usuario,
            id_orden=orden_id,
            origen=origen_evento,
        )


def validar_cita_para_vinculo_recepcion(
    db: Session,
    cita_id: int,
    cliente_id: int,
    vehiculo_id: int,
) -> Cita:
    """Valida cita al completar recepción rápida con cita_id."""
    cita = db.query(Cita).filter(Cita.id_cita == cita_id).first()
    if not cita:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cita con ID {cita_id} no encontrada",
        )
    validar_cita_convertible(cita, cita_id)
    if cita.id_cliente != cliente_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente no coincide con la cita seleccionada.",
        )
    if cita.id_vehiculo and cita.id_vehiculo != vehiculo_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El vehículo no coincide con la cita seleccionada.",
        )
    return cita
