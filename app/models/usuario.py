from sqlalchemy import Column, Integer, String, Enum, Boolean, TIMESTAMP, Numeric
from app.database import Base
import datetime

from sqlalchemy.orm import relationship

# Periodo de pago para nómina (Etapa 1)
PERIODOS_PAGO = ("SEMANAL", "QUINCENAL", "MENSUAL")


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum("ADMIN", "EMPLEADO", "TECNICO","CAJA"), default="TECNICO")
    activo = Column(Boolean, default=True)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    # Nómina (Etapa 1): salario base, periodo de pago y bono por puntualidad
    salario_base = Column(Numeric(12, 2), nullable=True)
    periodo_pago = Column(Enum(*PERIODOS_PAGO), nullable=True)
    bono_puntualidad = Column(Numeric(10, 2), nullable=True)
    
    ordenes_asignadas = relationship(
        "OrdenTrabajo",
        back_populates="tecnico",
        foreign_keys="OrdenTrabajo.tecnico_id",
    )
