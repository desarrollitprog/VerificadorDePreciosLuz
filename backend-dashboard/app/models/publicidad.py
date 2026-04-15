from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Publicidad(Base):
    """
    Modelo para publicidad (banners de imagen o video).
    Guarda metadata y vigencia, no el archivo en sí.
    """
    __tablename__ = "Publicidad"

    IdPublicidad = Column("IdPublicidad", Integer, primary_key=True, index=True)
    Titulo = Column("Titulo", String(200), nullable=True)
    Tipo = Column("Tipo", String(10), nullable=False, default="image")
    Url = Column("Url", String(500), nullable=False)
    Activo = Column("Activo", Boolean, nullable=False, default=True)
    Prioridad = Column("Prioridad", Integer, nullable=False, default=0)
    FechaInicio = Column("FechaInicio", DateTime, nullable=True)
    FechaFin = Column("FechaFin", DateTime, nullable=True)
    UpdatedAt = Column("UpdatedAt", DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    asignacion_todos = Column("asignacion_todos", Boolean, nullable=False, default=True)

    def __repr__(self):
        return (
            "<Publicidad(" 
            f"IdPublicidad={self.IdPublicidad}, Tipo={self.Tipo}, Url={self.Url}, Activo={self.Activo}, "
            f"Prioridad={self.Prioridad})>"
        )
