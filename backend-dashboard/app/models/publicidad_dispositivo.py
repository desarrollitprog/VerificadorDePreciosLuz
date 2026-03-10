from sqlalchemy import Column, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship
from .publicidad import Publicidad
from .dispositivo import Dispositivo
from ..database import Base

# Tabla de relación muchos a muchos entre Publicidad y Dispositivo
publicidad_dispositivo = Table(
    "publicidad_dispositivo",
    Base.metadata,
    Column("publicidad_id", Integer, ForeignKey("Publicidad.IdPublicidad", ondelete="CASCADE"), primary_key=True),
    Column("dispositivo_id", Integer, ForeignKey("dispositivos.id", ondelete="CASCADE"), primary_key=True)
)
