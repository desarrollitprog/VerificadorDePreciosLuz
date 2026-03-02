from enum import Enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum as SqlEnum, Integer, String
from ..database import Base


class RolUsuario(str, Enum):
    ADMIN = "ADMIN"
    CLIENTE = "CLIENTE"

class Usuario(Base):
    __tablename__ = "usuarios_dashboard"
    __table_args__ = {"schema": "dbo"}

    id = Column(Integer, primary_key=True, index=True)
    nombre_usuario = Column(String(50), unique=True, nullable=False, index=True)
    correo = Column(String(120), unique=True, nullable=False, index=True)
    contrasena_hash = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    rol = Column(
        SqlEnum(RolUsuario, name="rol_usuario"),
        nullable=False,
        default=RolUsuario.CLIENTE,
    )
