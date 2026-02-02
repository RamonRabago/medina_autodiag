from .usuario import UsuarioCreate, UsuarioUpdate, UsuarioOut

# Schemas de Inventario
from .categoria_repuesto import (
    CategoriaRepuestoCreate,
    CategoriaRepuestoUpdate,
    CategoriaRepuestoOut
)
from .proveedor import (
    ProveedorCreate,
    ProveedorUpdate,
    ProveedorOut
)
from .repuesto import (
    RepuestoCreate,
    RepuestoUpdate,
    RepuestoOut,
    RepuestoConStock
)
from .movimiento_inventario import (
    MovimientoInventarioCreate,
    MovimientoInventarioOut,
    MovimientoInventarioFiltros,
    AjusteInventario
)
from .alerta_inventario import (
    AlertaInventarioCreate,
    AlertaInventarioOut,
    AlertaInventarioResolver,
    ResumenAlertas
)
