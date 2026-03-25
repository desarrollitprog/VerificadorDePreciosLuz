from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from ..database import Base


class DispositivoSesion(Base):
    __tablename__ = "dispositivo_sesiones"

    id = Column(Integer, primary_key=True, index=True)
    dispositivo_id = Column(String(100), nullable=False, index=True)
    inicio = Column(DateTime, nullable=False)
    fin = Column(DateTime, nullable=True)
    duracion_segundos = Column(Integer, nullable=True)
