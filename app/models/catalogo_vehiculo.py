"""
Catálogo de vehículos (independiente de clientes).
Para órdenes de compra y futura asociación con partes.
Año, Marca, Modelo, Versión, Motor — sin duplicados.
"""
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
from datetime import datetime


class CatalogoVehiculo(Base):
    __tablename__ = "catalogo_vehiculos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    anio = Column(Integer, nullable=False)
    marca = Column(String(80), nullable=False)
    modelo = Column(String(80), nullable=False)
    version_trim = Column(String(100), nullable=True)   # Versión / nivel de equipamiento
    motor = Column(String(80), nullable=True)
    vin = Column(String(50), nullable=True)             # Número de serie (opcional)

    creado_en = Column(DateTime, default=datetime.utcnow)
