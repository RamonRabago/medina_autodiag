# app/models/servicio.py
from sqlalchemy import Column, Integer, String, Numeric, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Servicio(Base):
    """
    Modelo para el catálogo de servicios del taller
    Ejemplo: Cambio de aceite, Alineación, Balanceo, etc.
    """
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)  # Ej: "SRV-001"
    nombre = Column(String(200), nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    id_categoria = Column(Integer, ForeignKey("categorias_servicios.id"), nullable=False, index=True)
    
    # Precios y tiempos estimados
    precio_base = Column(Numeric(10, 2), nullable=False, default=0.00)
    tiempo_estimado_minutos = Column(Integer, nullable=False, default=60)  # Tiempo estimado en minutos
    
    # Control
    activo = Column(Boolean, default=True, nullable=False)
    requiere_repuestos = Column(Boolean, default=False, nullable=False)  # Si típicamente usa repuestos
    
    # Relaciones
    categoria = relationship("CategoriaServicio", back_populates="servicios")
    detalles_orden = relationship("DetalleOrdenTrabajo", back_populates="servicio")

    @property
    def categoria_nombre(self):
        return self.categoria.nombre if self.categoria else ""

    def __repr__(self):
        return f"<Servicio(codigo='{self.codigo}', nombre='{self.nombre}', precio={self.precio_base})>"
