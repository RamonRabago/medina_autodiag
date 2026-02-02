from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.schemas.venta import VentaCreate
from app.utils.roles import require_roles

router = APIRouter(
    prefix="/ventas",
    tags=["Ventas"]
)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED
)
def crear_venta(
    data: VentaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO"))
):
    # 1️⃣ Validación mínima
    if not data.detalles or len(data.detalles) == 0:
        raise HTTPException(
            status_code=400,
            detail="La venta debe tener al menos un detalle"
        )

    # 2️⃣ Crear venta (sin total todavía)
    venta = Venta(
        id_cliente=data.id_cliente,
        id_vehiculo=data.id_vehiculo,
        id_usuario=current_user.id_usuario,
        total=0
    )

    db.add(venta)
    db.commit()
    db.refresh(venta)

    # 3️⃣ Crear detalles y calcular total
    total_venta = 0

    for item in data.detalles:
        subtotal = item.cantidad * item.precio_unitario
        total_venta += subtotal

        detalle = DetalleVenta(
            id_venta=venta.id_venta,
            tipo=item.tipo,
            id_item=item.id_item,
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            subtotal=subtotal
        )

        db.add(detalle)

    # 4️⃣ Actualizar total de la venta
    venta.total = total_venta
    db.commit()

    return {
        "id_venta": venta.id_venta,
        "total": float(venta.total),
        "estado": venta.estado
    }
