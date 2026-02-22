from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, BigInteger

from ..database import Base


class ServidorSecundario(Base):
    __tablename__ = "servidores_secundarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    ip = Column(String(45), nullable=False)  # Soporta IPv4/IPv6
    almacenamiento_total = Column(BigInteger, nullable=False)  # bytes
    almacenamiento_usado = Column(BigInteger, nullable=False, default=0)  # bytes
    ultimo_heartbeat = Column(DateTime, nullable=True, default=None)

