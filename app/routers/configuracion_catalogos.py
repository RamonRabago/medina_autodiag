"""
Router agregado para Configuración: un solo endpoint que devuelve todos los
catálogos que la página de Configuración necesita, reduciendo de 9 requests a 1.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.categoria_servicio import CategoriaServicio
from app.models.categoria_repuesto import CategoriaRepuesto
from app.models.bodega import Bodega
from app.models.ubicacion import Ubicacion
from app.models.estante import Estante
from app.models.nivel import Nivel
from app.models.fila import Fila
from app.models.usuario import Usuario
from app.models.festivo import Festivo
from app.models.usuario_bodega import UsuarioBodega
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles

router = APIRouter(prefix="/configuracion", tags=["Configuración"])


@router.get("/catalogos")
def get_catalogos_agregados(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA", "TECNICO", "EMPLEADO")),
):
    """
    Endpoint agregado de catálogos para la página Configuración.
    Devuelve en una sola respuesta: categorías servicios/repuestos, bodegas,
    ubicaciones, estantes, niveles, filas, usuarios (si ADMIN) y festivos.
    """
    rol = getattr(current_user.rol, "value", None) or str(getattr(current_user, "rol", ""))
    es_admin = rol == "ADMIN"

    # Bodegas: si no es ADMIN, filtrar por bodegas permitidas
    q_bodegas = db.query(Bodega).order_by(Bodega.nombre)
    if not es_admin:
        ids_bodega = [r[0] for r in db.query(UsuarioBodega.id_bodega).filter(
            UsuarioBodega.id_usuario == current_user.id_usuario
        ).all()]
        if ids_bodega:
            q_bodegas = q_bodegas.filter(Bodega.id.in_(ids_bodega))
    bodegas = [{"id": b.id, "nombre": b.nombre, "descripcion": b.descripcion, "activo": b.activo} for b in q_bodegas.limit(500).all()]

    categorias_servicios = [
        {"id": c.id, "nombre": c.nombre, "descripcion": c.descripcion, "activo": c.activo}
        for c in db.query(CategoriaServicio).order_by(CategoriaServicio.nombre).limit(500).all()
    ]
    # CategoriaRepuesto no tiene columna activo (solo nombre, descripcion)
    categorias_repuestos = [
        {"id_categoria": c.id_categoria, "nombre": c.nombre, "descripcion": c.descripcion}
        for c in db.query(CategoriaRepuesto).order_by(CategoriaRepuesto.nombre).limit(500).all()
    ]
    ubicaciones = [
        {"id": u.id, "codigo": u.codigo, "nombre": u.nombre, "id_bodega": u.id_bodega, "activo": u.activo}
        for u in db.query(Ubicacion).order_by(Ubicacion.codigo).limit(500).all()
    ]
    estantes = [
        {"id": e.id, "codigo": e.codigo, "nombre": e.nombre, "id_ubicacion": e.id_ubicacion, "activo": e.activo}
        for e in db.query(Estante).order_by(Estante.codigo).limit(500).all()
    ]
    niveles = [
        {"id": n.id, "codigo": n.codigo, "nombre": n.nombre, "activo": n.activo}
        for n in db.query(Nivel).order_by(Nivel.codigo).limit(100).all()
    ]
    filas = [
        {"id": f.id, "codigo": f.codigo, "nombre": f.nombre, "activo": f.activo}
        for f in db.query(Fila).order_by(Fila.codigo).limit(100).all()
    ]

    usuarios = []
    if es_admin:
        usuarios = [
            {
                "id_usuario": u.id_usuario,
                "nombre": u.nombre,
                "email": u.email,
                "rol": u.rol.value if hasattr(u.rol, "value") else str(u.rol),
                "activo": u.activo,
                "salario_base": float(u.salario_base) if u.salario_base is not None else None,
                "bono_puntualidad": float(u.bono_puntualidad) if u.bono_puntualidad is not None else None,
                "periodo_pago": (u.periodo_pago.value if hasattr(u.periodo_pago, "value") else str(u.periodo_pago)) if u.periodo_pago else None,
            }
            for u in db.query(Usuario).order_by(Usuario.nombre).all()
        ]

    festivos = [
        {"id": f.id, "fecha": f.fecha.isoformat() if f.fecha else None, "nombre": f.nombre, "anio": f.anio}
        for f in db.query(Festivo).order_by(Festivo.fecha).all()
    ]

    return {
        "categorias_servicios": categorias_servicios,
        "categorias_repuestos": categorias_repuestos,
        "bodegas": bodegas,
        "ubicaciones": ubicaciones,
        "estantes": estantes,
        "niveles": niveles,
        "filas": filas,
        "usuarios": usuarios,
        "festivos": festivos,
    }
