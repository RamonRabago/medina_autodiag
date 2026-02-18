"""
Router para configuración de comisiones por empleado.
Solo ADMIN. Define % por tipo de base (MANO_OBRA, PARTES, SERVICIOS_VENTA, PRODUCTOS_VENTA).
Al cambiar un %, se cierra vigencia anterior y se crea nueva fila (histórico preservado).
"""
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.auditoria import Auditoria
from app.models.configuracion_comision import ConfiguracionComision, TIPOS_BASE_COMISION
from app.models.usuario import Usuario
from app.schemas.configuracion_comision import ConfiguracionComisionCreate, ConfiguracionComisionUpdatePorcentaje
from app.utils.roles import require_roles
from app.services.auditoria_service import registrar as registrar_auditoria

router = APIRouter(prefix="/configuracion/comisiones", tags=["Configuración comisiones"])


def _to_out(c: ConfiguracionComision, db: Session) -> dict:
    emp = db.query(Usuario).filter(Usuario.id_usuario == c.id_usuario).first()
    return {
        "id": c.id,
        "id_usuario": c.id_usuario,
        "tipo_base": c.tipo_base.value if hasattr(c.tipo_base, "value") else str(c.tipo_base),
        "porcentaje": float(c.porcentaje),
        "vigencia_desde": c.vigencia_desde.isoformat() if c.vigencia_desde else None,
        "vigencia_hasta": c.vigencia_hasta.isoformat() if c.vigencia_hasta else None,
        "activo": c.activo,
        "empleado_nombre": emp.nombre if emp else None,
    }


@router.get("/", response_model=List[dict])
def listar_configuraciones(
    id_usuario: Optional[int] = Query(None, description="Filtrar por empleado"),
    tipo_base: Optional[str] = Query(None, description="MANO_OBRA, PARTES, SERVICIOS_VENTA, PRODUCTOS_VENTA"),
    solo_vigentes: bool = Query(True, description="Solo configuraciones vigentes (vigencia_hasta IS NULL)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    """Lista configuraciones de comisión con filtros."""
    q = db.query(ConfiguracionComision).order_by(
        ConfiguracionComision.id_usuario,
        ConfiguracionComision.tipo_base,
        ConfiguracionComision.vigencia_desde.desc(),
    )
    if id_usuario:
        q = q.filter(ConfiguracionComision.id_usuario == id_usuario)
    if tipo_base:
        q = q.filter(ConfiguracionComision.tipo_base == tipo_base)
    if solo_vigentes:
        q = q.filter(ConfiguracionComision.vigencia_hasta.is_(None))
    items = q.limit(500).all()
    if not items:
        return []
    ids = [c.id for c in items]
    audits = (
        db.query(Auditoria)
        .filter(Auditoria.modulo == "CONFIGURACION_COMISION", Auditoria.id_referencia.in_(ids))
        .options(joinedload(Auditoria.usuario))
        .all()
    )
    creado_por_map = {}
    for a in audits:
        if a.id_referencia is not None and a.id_referencia not in creado_por_map:
            creado_por_map[a.id_referencia] = a.usuario.nombre if a.usuario else f"Usuario #{a.id_usuario}"
    result = []
    for c in items:
        d = _to_out(c, db)
        d["creado_por"] = creado_por_map.get(c.id)
        result.append(d)
    return result


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_configuracion(
    data: ConfiguracionComisionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    """
    Crea una nueva configuración de comisión.
    Si ya existe una vigente (vigencia_hasta=NULL) para ese usuario y tipo_base,
    se cierra primero (vigencia_hasta = vigencia_desde - 1 día).
    """
    emp = db.query(Usuario).filter(Usuario.id_usuario == data.id_usuario).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    tipo_str = data.tipo_base
    vigencia_desde = data.vigencia_desde

    # Cerrar configuraciones vigentes para mismo usuario y tipo_base
    vigentes = (
        db.query(ConfiguracionComision)
        .filter(
            ConfiguracionComision.id_usuario == data.id_usuario,
            ConfiguracionComision.tipo_base == tipo_str,
            ConfiguracionComision.vigencia_hasta.is_(None),
        )
        .all()
    )
    for v in vigentes:
        v.vigencia_hasta = vigencia_desde
        v.activo = False

    conf = ConfiguracionComision(
        id_usuario=data.id_usuario,
        tipo_base=tipo_str,
        porcentaje=data.porcentaje,
        vigencia_desde=vigencia_desde,
        vigencia_hasta=None,
        activo=True,
    )
    db.add(conf)
    db.commit()
    db.refresh(conf)
    registrar_auditoria(
        db,
        current_user.id_usuario,
        "CREAR",
        "CONFIGURACION_COMISION",
        conf.id,
        {"empleado": emp.nombre, "tipo_base": tipo_str, "porcentaje": float(data.porcentaje)},
    )
    return _to_out(conf, db)


@router.put("/{id_config}")
def actualizar_porcentaje(
    id_config: int,
    data: ConfiguracionComisionUpdatePorcentaje,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    """
    Actualiza el porcentaje de una configuración.
    Si la config está vigente (vigencia_hasta=NULL), se cierra y se crea una nueva
    con vigencia_desde = hoy, preservando el histórico.
    """
    porcentaje = float(data.porcentaje)

    conf = db.query(ConfiguracionComision).filter(ConfiguracionComision.id == id_config).first()
    if not conf:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    emp = db.query(Usuario).filter(Usuario.id_usuario == conf.id_usuario).first()
    emp_nombre = emp.nombre if emp else f"Usuario #{conf.id_usuario}"

    hoy = date.today()

    if conf.vigencia_hasta is None:
        # Está vigente: cerrar y crear nueva
        conf.vigencia_hasta = hoy
        conf.activo = False
        nueva = ConfiguracionComision(
            id_usuario=conf.id_usuario,
            tipo_base=conf.tipo_base,
            porcentaje=porcentaje,
            vigencia_desde=hoy,
            vigencia_hasta=None,
            activo=True,
        )
        db.add(nueva)
        db.commit()
        db.refresh(nueva)
        registrar_auditoria(
            db,
            current_user.id_usuario,
            "ACTUALIZAR",
            "CONFIGURACION_COMISION",
            nueva.id,
            {"empleado": emp_nombre, "tipo_base": str(conf.tipo_base), "porcentaje_anterior": float(conf.porcentaje), "porcentaje_nuevo": porcentaje},
        )
        return _to_out(nueva, db)
    else:
        # Histórica: no modificar. El usuario debe crear una nueva.
        raise HTTPException(
            status_code=400,
            detail="No se puede modificar una configuración histórica. Crea una nueva con vigencia_desde desde hoy.",
        )
