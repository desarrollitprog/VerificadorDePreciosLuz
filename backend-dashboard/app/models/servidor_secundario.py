from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, BigInteger
from sqlalchemy.orm import relationship

from ..database import Base


class ServidorSecundario(Base):
    __tablename__ = "servidores_secundarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    ip = Column(String(45), nullable=False)
    almacenamiento_total = Column(BigInteger, nullable=False)
    almacenamiento_usado = Column(BigInteger, nullable=False, default=0)
    ultimo_heartbeat = Column(DateTime, nullable=True, default=None)
    dispositivos = relationship("Dispositivo", back_populates="servidor")

