from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from ..database import Base


class SubidaLog(Base):
    """
    Registro inmutable de subidas de banners.
    Cada vez que se crea un banner se inserta una fila aquí.
    Nunca se modifica ni elimina — preserva el histórico de subidas.
    """
    __tablename__ = "subida_log"

    id = Column(Integer, primary_key=True, index=True)
    publicidad_id = Column(Integer, nullable=False)
    titulo = Column(String(200), nullable=True)
    fecha_subida = Column(DateTime, nullable=False, default=datetime.utcnow)
