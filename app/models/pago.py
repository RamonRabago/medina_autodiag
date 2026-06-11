from datetime import datetime

from sqlalchemy import DECIMAL, TIMESTAMP, Column, Enum, ForeignKey, Integer, String

from app.database import Base


class Pago(Base):
    __tablename__ = "pagos"

    id_pago = Column(Integer, primary_key=True, index=True)

    # 🔗 Relaciones
    id_venta = Column(Integer, ForeignKey("ventas.id_venta"), nullable=False)

    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)

    id_turno = Column(Integer, ForeignKey("caja_turnos.id_turno"), nullable=False)

    # 🕒 Fecha del pago (UTC, controlado por backend)
    fecha = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # 💳 Datos del pago
    metodo = Column(Enum("EFECTIVO", "TARJETA", "TRANSFERENCIA"), nullable=False)

    monto = Column(DECIMAL(10, 2), nullable=False)

    referencia = Column(String(100), nullable=True)
