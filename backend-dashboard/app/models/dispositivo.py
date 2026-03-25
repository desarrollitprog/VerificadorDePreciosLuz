from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class Dispositivo(Base):
    __tablename__ = "dispositivos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_kiosko = Column(String(100), unique=True, nullable=False, index=True)
    nombre_amigable = Column(String(120), nullable=True)
    online = Column(Boolean, default=False, nullable=False)

    servidor_id = Column(
        Integer,
        ForeignKey("servidores_secundarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    primera_conexion = Column(DateTime, nullable=True, default=None)
    servidor = relationship("ServidorSecundario", backref="dispositivos")

