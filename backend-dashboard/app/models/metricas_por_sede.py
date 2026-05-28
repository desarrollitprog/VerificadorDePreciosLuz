from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint
from ..database import Base


class MetricasPorSede(Base):
    __tablename__ = "metricas_por_sede"

    id = Column(Integer, primary_key=True, index=True)
    servidor_id = Column(Integer, nullable=False)
    banner_id = Column(Integer, nullable=False)
    titulo = Column(String(255), nullable=True)
    fecha = Column(Date, nullable=False)
    tipo_dispositivo = Column(String(20), nullable=True)
    reproducciones = Column(Integer, default=0)
    completados = Column(Integer, default=0)
    validas_50 = Column(Integer, default=0)
    tipo_dispositivo = Column(String(20), nullable=False, default="verificador")
    segundos_totales = Column(Float, default=0)
    __table_args__ = (
        UniqueConstraint("servidor_id", "banner_id", "fecha", "tipo_dispositivo", name="uq_metricas_por_sede"),
    )
