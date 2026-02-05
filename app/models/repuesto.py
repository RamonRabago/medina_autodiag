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
    
    # Ubicación física - Jerarquía: Bodega → Estante → Nivel → Fila
    ubicacion = Column(String(50))  # Texto libre (legacy/notas)
    id_ubicacion = Column(Integer, ForeignKey("ubicaciones.id"), nullable=True, index=True)  # Legacy
    id_estante = Column(Integer, ForeignKey("estantes.id"), nullable=True, index=True)
    id_nivel = Column(Integer, ForeignKey("niveles.id"), nullable=True, index=True)
    id_fila = Column(Integer, ForeignKey("filas.id"), nullable=True, index=True)
    
    # Precios
    precio_compra = Column(DECIMAL(10, 2), nullable=False)
    precio_venta = Column(DECIMAL(10, 2), nullable=False)
    
    # Información adicional
    imagen_url = Column(String(500))  # URL de la foto del producto
    comprobante_url = Column(String(500))  # URL de factura/recibo/orden de compra (evidencia)
    marca = Column(String(100))
    modelo_compatible = Column(String(200))  # Ej: "Nissan Versa 2015-2020"
    unidad_medida = Column(String(20), default="PZA")  # PZA, LT, KG, etc.
    
    # Consumible: sugiere MERMA por defecto al cancelar ventas pagadas (aceite, filtros, fluidos)
    es_consumible = Column(Boolean, default=False, nullable=False)

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
    ubicacion_obj = relationship("Ubicacion", backref="repuestos")
    estante = relationship("Estante", foreign_keys=[id_estante], backref="repuestos")
    nivel = relationship("Nivel", foreign_keys=[id_nivel], backref="repuestos")
    fila = relationship("Fila", foreign_keys=[id_fila], backref="repuestos")
    movimientos = relationship("MovimientoInventario", back_populates="repuesto")
    
    detalles_orden = relationship("DetalleRepuestoOrden", back_populates="repuesto")

    @property
    def categoria_nombre(self):
        return self.categoria.nombre if self.categoria else ""

    @property
    def proveedor_nombre(self):
        return self.proveedor.nombre if self.proveedor else ""

    @property
    def bodega_nombre(self):
        if self.estante and self.estante.ubicacion and self.estante.ubicacion.bodega:
            return self.estante.ubicacion.bodega.nombre
        if self.ubicacion_obj and self.ubicacion_obj.bodega:
            return self.ubicacion_obj.bodega.nombre
        return ""

    @property
    def ubicacion_nombre(self):
        """Ubicación estructurada: Estante - Nivel - Fila, o legacy"""
        if self.estante:
            partes = [f"{self.estante.codigo} - {self.estante.nombre}"]
            if self.nivel:
                partes.append(f"Niv.{self.nivel.codigo}")
            if self.fila:
                partes.append(f"F{self.fila.codigo}")
            return " | ".join(partes)
        if self.ubicacion_obj:
            return f"{self.ubicacion_obj.codigo} - {self.ubicacion_obj.nombre}" if self.ubicacion_obj.nombre else self.ubicacion_obj.codigo
        return self.ubicacion or ""

    @property
    def estante_nombre(self):
        return f"{self.estante.codigo} - {self.estante.nombre}" if self.estante else ""

    @property
    def nivel_codigo(self):
        return self.nivel.codigo if self.nivel else ""

    @property
    def fila_codigo(self):
        return self.fila.codigo if self.fila else ""
