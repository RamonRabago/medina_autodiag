from app.models.asistencia import TIPOS_ASISTENCIA, Asistencia, TipoAsistencia
from app.models.auditoria import Auditoria
from app.models.categoria_servicio import CategoriaServicio
from app.models.comision_devengada import ComisionDevengada
from app.models.configuracion_comision import ConfiguracionComision
from app.models.cotizacion_refaccion_especial import (
    ComentarioCotizacionRefaccion,
    CompraEjecutadaCotizacionRefaccion,
    CotizacionRefaccionEspecial,
    EstadoCotizacionRefaccion,
    LineaCotizacionRefaccion,
    MetodoPagoCompraRefaccion,
    MonedaCotizacion,
    OpcionCompraLineaCotizacion,
)
from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
from app.models.festivo import Festivo
from app.models.movimiento_vacaciones import MovimientoVacaciones
from app.models.orden_trabajo import OrdenTrabajo
from app.models.prestamo_empleado import DescuentoPrestamo, PrestamoEmpleado
from app.models.registro_eliminacion_cliente import RegistroEliminacionCliente
from app.models.registro_eliminacion_repuesto import RegistroEliminacionRepuesto
from app.models.registro_eliminacion_vehiculo import RegistroEliminacionVehiculo
from app.models.servicio import Servicio

from .alerta_inventario import AlertaInventario, TipoAlertaInventario

# Modelos de Inventario
from .bodega import Bodega
from .caja_alerta import CajaAlerta

# Caja y gastos
from .caja_turno import CajaTurno
from .cancelacion_producto import CancelacionProducto

# Órdenes de compra
from .catalogo_vehiculo import CatalogoVehiculo
from .categoria_repuesto import CategoriaRepuesto
from .cita import Cita, EstadoCita, TipoCita
from .cita_estado_historial import CitaEstadoHistorial
from .cliente import Cliente
from .cuenta_pagar_manual import CuentaPagarManual, PagoCuentaPagarManual
from .detalle_venta import DetalleVenta
from .estante import Estante
from .fila import Fila
from .gasto_operativo import GastoOperativo
from .movimiento_inventario import MovimientoInventario, TipoMovimiento
from .nivel import Nivel
from .orden_compra import DetalleOrdenCompra, OrdenCompra
from .pago import Pago
from .pago_orden_compra import PagoOrdenCompra
from .password_reset_token import PasswordResetToken
from .proveedor import Proveedor
from .repuesto import Repuesto
from .repuesto_compatibilidad import RepuestoCompatibilidad
from .ubicacion import Ubicacion
from .usuario import Usuario
from .usuario_bodega import UsuarioBodega
from .vehiculo import Vehiculo
from .venta import Venta
