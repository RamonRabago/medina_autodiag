from sqlalchemy import Column, Integer, DECIMAL, TIMESTAMP, Enum, ForeignKey
from app.database import Base
import datetime

class Venta(Base):
    __tablename__ = "ventas"

    id_venta = Column(Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=True)
    id_vehiculo = Column(Integer, ForeignKey("vehiculos.id_vehiculo"), nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    fecha = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    total = Column(DECIMAL(10,2), nullable=False)
    estado = Column(Enum("PAGADA","PENDIENTE","CANCELADA"), default="PENDIENTE")
