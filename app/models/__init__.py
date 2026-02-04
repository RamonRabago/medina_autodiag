from .usuario import Usuario
from .cliente import Cliente
from .vehiculo import Vehiculo

from .venta import Venta
from .detalle_venta import DetalleVenta

# Modelos de Inventario
from .bodega import Bodega
from .categoria_repuesto import CategoriaRepuesto
from .proveedor import Proveedor
from .repuesto import Repuesto
from .movimiento_inventario import MovimientoInventario, TipoMovimiento
from .alerta_inventario import AlertaInventario, TipoAlertaInventario


from app.models.categoria_servicio import CategoriaServicio
from app.models.servicio import Servicio
from app.models.orden_trabajo import OrdenTrabajo
from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
from app.models.registro_eliminacion_vehiculo import RegistroEliminacionVehiculo
from app.models.registro_eliminacion_cliente import RegistroEliminacionCliente