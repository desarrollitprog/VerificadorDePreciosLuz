from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ..database import Base


class Publicidad(Base):
    """
    Modelo para publicidad (banners de imagen o video).
    Guarda metadata y vigencia, no el archivo en sí.
    """

    __tablename__ = "Publicidad"
    __table_args__ = {"schema": "ConfiguracionPOS"}

    id = Column("IdPublicidad", Integer, primary_key=True, index=True)
    titulo = Column("Titulo", String(200), nullable=True)
    tipo = Column("Tipo", String(10), nullable=False, default="image")
    url = Column("Url", String(500), nullable=False)
    activo = Column("Activo", Boolean, nullable=False, default=True)
    prioridad = Column("Prioridad", Integer, nullable=False, default=0)
    fecha_inicio = Column("FechaInicio", DateTime, nullable=True)
    fecha_fin = Column("FechaFin", DateTime, nullable=True)
    duracion_seg = Column("DuracionSeg", Integer, nullable=True)
    updated_at = Column("UpdatedAt", DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return (
            "<Publicidad(" 
            f"id={self.id}, tipo={self.tipo}, url={self.url}, activo={self.activo}, "
            f"prioridad={self.prioridad})>"
        )