from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from ..database import BasePublicidad


class ReproduccionMetricaSede(BasePublicidad):
    __tablename__ = "reproducciones_metricas_sede"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reproduccion_id = Column(String(255), unique=True, nullable=False)
    dispositivo_id = Column(String(100), nullable=False)
    banner_id = Column(Integer, nullable=False)
    titulo = Column(String(255), nullable=True)
    completo = Column(Boolean, default=False)
    cuartil_50 = Column(Boolean, default=False)
    segundos_reproducidos = Column(Float, nullable=True)
    tipo_dispositivo = Column(String(20), nullable=False, default="verificador")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
