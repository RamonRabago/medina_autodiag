from .usuario import Usuario
from .usuario_bodega import UsuarioBodega
from .cliente import Cliente
from .vehiculo import Vehiculo

from .venta import Venta
from .detalle_venta import DetalleVenta
from .cancelacion_producto import CancelacionProducto

# Modelos de Inventario
from .bodega import Bodega
from .ubicacion import Ubicacion
from .estante import Estante
from .nivel import Nivel
from .fila import Fila
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
from app.models.registro_eliminacion_repuesto import RegistroEliminacionRepuesto