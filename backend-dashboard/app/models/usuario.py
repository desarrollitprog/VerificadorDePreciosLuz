from sqlalchemy import Column, Integer, String, Boolean
from ..database import Base

class Usuario(Base):
    __tablename__ = "usuarios_dashboard"
    __table_args__ = {"schema": "dbo"}

    id = Column(Integer, primary_key=True, index=True)
    nombre_usuario = Column(String(50), unique=True, nullable=False, index=True)
    contrasena_hash = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True)
