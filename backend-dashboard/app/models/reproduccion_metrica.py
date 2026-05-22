from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from ..database import Base


class ReproduccionMetrica(Base):
    __tablename__ = "reproducciones_metricas"

    id = Column(Integer, primary_key=True, index=True)
    reproduccion_id = Column(String(255), unique=True, nullable=False, index=True)
    dispositivo_id = Column(String(100), nullable=False, index=True)
    banner_id = Column(Integer, nullable=False, index=True)
    titulo = Column(String(255), nullable=True)
    duracion_total_seg = Column(Float, nullable=True)
    inicio_reproduccion = Column(DateTime, nullable=True)
    fin_reproduccion = Column(DateTime, nullable=True)
    segundos_reproducidos = Column(Float, nullable=True)
    porcentaje_completado = Column(Float, nullable=True)
    cuartil_50 = Column(Boolean, default=False)
    cuartil_75 = Column(Boolean, default=False)
    cuartil_100 = Column(Boolean, default=False)
    completo = Column(Boolean, default=False)
    motivo_fin = Column(String(20), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
