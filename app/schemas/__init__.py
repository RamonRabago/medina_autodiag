from .alerta_inventario import AlertaInventarioCreate, AlertaInventarioOut, AlertaInventarioResolver, ResumenAlertas

# Schemas de Inventario
from .categoria_repuesto import CategoriaRepuestoCreate, CategoriaRepuestoOut, CategoriaRepuestoUpdate
from .movimiento_inventario import (
    AjusteInventario,
    MovimientoInventarioCreate,
    MovimientoInventarioFiltros,
    MovimientoInventarioOut,
)
from .proveedor import ProveedorCreate, ProveedorOut, ProveedorUpdate
from .repuesto import RepuestoConStock, RepuestoCreate, RepuestoOut, RepuestoUpdate
from .usuario import UsuarioCreate, UsuarioOut, UsuarioUpdate
