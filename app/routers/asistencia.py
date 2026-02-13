"""Router para Asistencia (Checador Fase 3). Registro día por día."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models.asistencia import Asistencia
from app.schemas.asistencia import AsistenciaCreate, AsistenciaUpdate, AsistenciaOut
from app.utils.roles import require_roles

router = APIRouter(prefix="/asistencia", tags=["Asistencia"])


def _inicio_semana(d: date) -> date:
    """Lunes de la semana (ISO: lunes=0)."""
    return d - timedelta(days=d.weekday())


@router.post("/", response_model=AsistenciaOut, status_code=201)
def crear_asistencia(
    data: AsistenciaCreate,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    existente = db.query(Asistencia).filter(
        Asistencia.id_usuario == data.id_usuario,
        Asistencia.fecha == data.fecha
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe registro para usuario {data.id_usuario} en fecha {data.fecha}"
        )
    a = Asistencia(
        id_usuario=data.id_usuario,
        fecha=data.fecha,
        tipo=data.tipo,
        horas_trabajadas=data.horas_trabajadas,
        turno_completo=data.turno_completo if data.turno_completo is not None else True,
        aplica_bono_puntualidad=data.aplica_bono_puntualidad if data.aplica_bono_puntualidad is not None else True,
        observaciones=data.observaciones,
        id_referencia=data.id_referencia,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.get("/", response_model=list[AsistenciaOut])
def listar_asistencia(
    id_usuario: int | None = Query(None, description="Filtrar por empleado"),
    fecha: date | None = Query(None, description="Fecha exacta"),
    fecha_inicio: date | None = Query(None, description="Inicio rango"),
    fecha_fin: date | None = Query(None, description="Fin rango"),
    semana_inicio: date | None = Query(None, description="Lunes de la semana (YYYY-MM-DD)"),
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA", "TECNICO", "EMPLEADO")),
):
    """
    Lista registros de asistencia.
    - id_usuario: filtrar por empleado
    - fecha: día exacto
    - fecha_inicio/fecha_fin: rango
    - semana_inicio: lunes de semana (calcula lunes-dom automáticamente)
    """
    q = db.query(Asistencia)
    if id_usuario is not None:
        q = q.filter(Asistencia.id_usuario == id_usuario)
    if fecha is not None:
        q = q.filter(Asistencia.fecha == fecha)
    if fecha_inicio is not None:
        q = q.filter(Asistencia.fecha >= fecha_inicio)
    if fecha_fin is not None:
        q = q.filter(Asistencia.fecha <= fecha_fin)
    if semana_inicio is not None:
        lun = _inicio_semana(semana_inicio)
        dom = lun + timedelta(days=6)
        q = q.filter(Asistencia.fecha >= lun, Asistencia.fecha <= dom)
    return q.order_by(Asistencia.fecha, Asistencia.id_usuario).all()


@router.get("/tipos", response_model=list[str])
def listar_tipos_asistencia(
    current_user=Depends(require_roles("ADMIN", "CAJA", "TECNICO", "EMPLEADO")),
):
    """Lista tipos de asistencia disponibles."""
    return [
        "TRABAJO", "FESTIVO", "VACACION",
        "PERMISO_CON_GOCE", "PERMISO_SIN_GOCE",
        "INCAPACIDAD", "FALTA"
    ]


@router.get("/{id_asistencia}", response_model=AsistenciaOut)
def obtener_asistencia(
    id_asistencia: int,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA", "TECNICO", "EMPLEADO")),
):
    a = db.query(Asistencia).filter(Asistencia.id == id_asistencia).first()
    if not a:
        raise HTTPException(status_code=404, detail="Registro de asistencia no encontrado")
    return a


@router.put("/{id_asistencia}", response_model=AsistenciaOut)
def actualizar_asistencia(
    id_asistencia: int,
    data: AsistenciaUpdate,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    a = db.query(Asistencia).filter(Asistencia.id == id_asistencia).first()
    if not a:
        raise HTTPException(status_code=404, detail="Registro de asistencia no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{id_asistencia}", status_code=204)
def eliminar_asistencia(
    id_asistencia: int,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    a = db.query(Asistencia).filter(Asistencia.id == id_asistencia).first()
    if not a:
        raise HTTPException(status_code=404, detail="Registro de asistencia no encontrado")
    db.delete(a)
    db.commit()
