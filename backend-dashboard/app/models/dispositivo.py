from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class Dispositivo(Base):
    __tablename__ = "dispositivos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_kiosko = Column(String(100), unique=True, nullable=False, index=True)
    nombre_amigable = Column(String(120), nullable=True)
    online = Column(Boolean, default=False, nullable=False)
    hora_reinicio = Column(String(5), nullable=True)  # formato "06:35"
    reinicio_recurrente = Column(Boolean, default=False, nullable=False)
    tipo = Column(String(20), nullable=False, server_default="verificador")

    servidor_id = Column(
        Integer,
        ForeignKey("servidores_secundarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    servidor = relationship("ServidorSecundario", back_populates="dispositivos")

