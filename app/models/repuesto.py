from sqlalchemy import Column, Integer, String, Text, DECIMAL, TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

from sqlalchemy.orm import relationship

class Repuesto(Base):
    __tablename__ = "repuestos"

    id_repuesto = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    
    # Relaciones
    id_categoria = Column(Integer, ForeignKey("categorias_repuestos.id_categoria"))
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"))
    
    # Inventario
    stock_actual = Column(Integer, default=0, nullable=False)
    stock_minimo = Column(Integer, default=5, nullable=False)
    stock_maximo = Column(Integer, default=100, nullable=False)
    
    # Ubicación física
    ubicacion = Column(String(50))  # Ej: "Estante A-3", "Bodega 2"
    
    # Precios
    precio_compra = Column(DECIMAL(10, 2), nullable=False)
    precio_venta = Column(DECIMAL(10, 2), nullable=False)
    
    # Información adicional
    imagen_url = Column(String(500))  # URL de la foto del producto
    marca = Column(String(100))
    modelo_compatible = Column(String(200))  # Ej: "Nissan Versa 2015-2020"
    unidad_medida = Column(String(20), default="PZA")  # PZA, LT, KG, etc.
    
    # Estado
    activo = Column(Boolean, default=True)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    actualizado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Soft delete (oculto en listado y selección; historial en ventas/órdenes se mantiene)
    eliminado = Column(Boolean, default=False, nullable=False)
    fecha_eliminacion = Column(TIMESTAMP, nullable=True)
    motivo_eliminacion = Column(Text, nullable=True)
    id_usuario_eliminacion = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    
    # Relaciones
    categoria = relationship("CategoriaRepuesto", back_populates="repuestos")
    proveedor = relationship("Proveedor", back_populates="repuestos")
    movimientos = relationship("MovimientoInventario", back_populates="repuesto")
    
    detalles_orden = relationship("DetalleRepuestoOrden", back_populates="repuesto")

    @property
    def categoria_nombre(self):
        return self.categoria.nombre if self.categoria else ""

    @property
    def proveedor_nombre(self):
        return self.proveedor.nombre if self.proveedor else ""
