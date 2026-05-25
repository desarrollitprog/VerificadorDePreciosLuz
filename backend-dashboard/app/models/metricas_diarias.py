from datetime import date
from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint
from ..database import Base


class MetricasDiarias(Base):
    __tablename__ = "metricas_diarias"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    banner_id = Column(Integer, nullable=False)
    titulo = Column(String(255), nullable=True)
    duracion_total_seg = Column(Float, nullable=True)
    inicios = Column(Integer, default=0)
    completados = Column(Integer, default=0)
    interrumpidos = Column(Integer, default=0)
    validas_50 = Column(Integer, default=0)
    segundos_totales = Column(Float, default=0)
    ver_validas = Column(Integer, default=0)
    tv_total = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("fecha", "banner_id", name="uq_metricas_diarias"),)
