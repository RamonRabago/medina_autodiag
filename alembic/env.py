"""
Configuración del entorno de migraciones Alembic.
Usa app.config para la URL de la base de datos.
Importa todos los modelos para que autogenerate los detecte.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Cargar configuración de la aplicación
from app.config import settings
from app.database import Base

# Importar todos los modelos para que Base.metadata tenga las tablas
from app.models import (  # noqa: F401
    Usuario,
    UsuarioBodega,
    Cliente,
    Vehiculo,
    Venta,
    DetalleVenta,
    CancelacionProducto,
    Pago,
    CajaTurno,
    CajaAlerta,
    GastoOperativo,
    OrdenCompra,
    DetalleOrdenCompra,
    PagoOrdenCompra,
    Bodega,
    Ubicacion,
    Estante,
    Nivel,
    Fila,
    CategoriaRepuesto,
    Proveedor,
    Repuesto,
    MovimientoInventario,
    AlertaInventario,
    CategoriaServicio,
    Servicio,
    OrdenTrabajo,
    DetalleOrdenTrabajo,
    DetalleRepuestoOrden,
    RegistroEliminacionVehiculo,
    RegistroEliminacionCliente,
    RegistroEliminacionRepuesto,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadatos de los modelos para autogenerate
target_metadata = Base.metadata

# Sobrescribir sqlalchemy.url con la URL de app.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def include_object(object, name, type_, reflected, compare_to):
    """
    Evita que Alembic sugiera DROP de tablas que existen en la BD
    pero no tienen modelo (ej: detalles_devolucion, citas, auditoria).
    Solo comparamos tablas que tenemos en nuestros modelos.
    """
    if type_ == "table" and reflected:
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Genera el script SQL sin conectar a la base de datos.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Conecta a la base de datos y ejecuta las migraciones.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
