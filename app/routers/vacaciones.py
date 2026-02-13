"""Router para Movimientos de Vacaciones (Checador Fase 5)."""
from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models.movimiento_vacaciones import MovimientoVacaciones
from app.models.usuario import Usuario
from app.models.asistencia import Asistencia
from app.schemas.movimiento_vacaciones import MovimientoVacacionesCreate, MovimientoVacacionesOut, TomarAgendadoCreate
from app.utils.roles import require_roles

router = APIRouter(prefix="/vacaciones", tags=["Vacaciones"])


def _saldo_usuario(db, id_usuario) -> Decimal:
    u = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not u:
        return None
    s = u.dias_vacaciones_saldo
    return Decimal("0") if s is None else s


@router.post("/movimientos", response_model=MovimientoVacacionesOut, status_code=201)
def crear_movimiento(
    data: MovimientoVacacionesCreate,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Registra un movimiento y actualiza el saldo del usuario."""
    usuario = db.query(Usuario).filter(Usuario.id_usuario == data.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    saldo = _saldo_usuario(db, data.id_usuario)
    dias = Decimal(str(data.dias))

    if data.tipo == "TOMA":
        if dias <= 0:
            raise HTTPException(status_code=400, detail="Días debe ser mayor a 0 en TOMA")
        if saldo < dias:
            raise HTTPException(
                status_code=400,
                detail=f"Saldo insuficiente: tiene {saldo}, solicita {dias}",
            )
        nuevo_saldo = saldo - dias
    elif data.tipo == "ACREDITACION":
        if dias <= 0:
            raise HTTPException(status_code=400, detail="Días debe ser mayor a 0 en ACREDITACION")
        nuevo_saldo = saldo + dias
    elif data.tipo == "AJUSTE":
        nuevo_saldo = saldo + dias
        if nuevo_saldo < 0:
            raise HTTPException(status_code=400, detail="El ajuste dejaría saldo negativo")
    else:
        raise HTTPException(status_code=400, detail="Tipo de movimiento no válido")

    m = MovimientoVacaciones(
        id_usuario=data.id_usuario,
        fecha=data.fecha,
        tipo=data.tipo,
        dias=float(dias),
        periodo=data.periodo,
        observaciones=data.observaciones,
    )
    db.add(m)
    usuario.dias_vacaciones_saldo = nuevo_saldo
    db.commit()
    db.refresh(m)
    return m


@router.post("/tomar-agendado", response_model=MovimientoVacacionesOut, status_code=201)
def tomar_vacaciones_agendado(
    data: TomarAgendadoCreate,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """
    Toma de vacaciones con fechas específicas.
    Crea registros en Asistencia (tipo=VACACION) para cada fecha y reduce el saldo.
    """
    usuario = db.query(Usuario).filter(Usuario.id_usuario == data.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    fechas_unicas = sorted(set(data.fechas))
    dias = Decimal(len(fechas_unicas))
    saldo = _saldo_usuario(db, data.id_usuario)

    if saldo < dias:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo insuficiente: tiene {saldo}, solicita {dias} días",
        )

    for f in fechas_unicas:
        existente = (
            db.query(Asistencia)
            .filter(Asistencia.id_usuario == data.id_usuario, Asistencia.fecha == f)
            .first()
        )
        if existente:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe registro para {f}. Edita en Asistencia o elige otras fechas.",
            )

    fecha_mov = fechas_unicas[0] if fechas_unicas else date.today()
    for f in fechas_unicas:
        a = Asistencia(
            id_usuario=data.id_usuario,
            fecha=f,
            tipo="VACACION",
            turno_completo=True,
            aplica_bono_puntualidad=True,
            observaciones=data.observaciones,
        )
        db.add(a)

    obs_mov = data.observaciones
    if not obs_mov and len(fechas_unicas) > 1:
        obs_mov = f"Agendado: {fechas_unicas[0]} a {fechas_unicas[-1]}"
    m = MovimientoVacaciones(
        id_usuario=data.id_usuario,
        fecha=fecha_mov,
        tipo="TOMA",
        dias=float(dias),
        periodo=None,
        observaciones=obs_mov,
    )
    db.add(m)
    usuario.dias_vacaciones_saldo = saldo - dias
    db.commit()
    db.refresh(m)
    return m


@router.get("/movimientos", response_model=list[MovimientoVacacionesOut])
def listar_movimientos(
    id_usuario: int | None = Query(None, description="Filtrar por empleado"),
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA", "TECNICO", "EMPLEADO")),
):
    """TECNICO/EMPLEADO solo ven sus propios movimientos."""
    q = db.query(MovimientoVacaciones)
    if current_user.rol in ("TECNICO", "EMPLEADO"):
        q = q.filter(MovimientoVacaciones.id_usuario == current_user.id_usuario)
    elif id_usuario is not None:
        q = q.filter(MovimientoVacaciones.id_usuario == id_usuario)
    return q.order_by(MovimientoVacaciones.fecha.desc(), MovimientoVacaciones.id.desc()).all()
