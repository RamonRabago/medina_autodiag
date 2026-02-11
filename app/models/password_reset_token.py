"""Token de recuperación de contraseña (uso único, expira en 1 hora)."""
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
import datetime


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), nullable=False, index=True)
    token = Column(String(100), nullable=False, unique=True)
    expira_en = Column(DateTime, nullable=False)
    creado_en = Column(DateTime, default=datetime.datetime.utcnow)
