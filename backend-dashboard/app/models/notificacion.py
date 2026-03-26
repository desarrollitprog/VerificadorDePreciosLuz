from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)

    tipo = Column(String(50), nullable=False)
    descripcion = Column(String(500), nullable=True)

    dispositivo_id = Column(String(100), nullable=True, index=True)
    servidor_id = Column(Integer, nullable=True, index=True)

    usuario_id = Column(
        Integer,
        ForeignKey("dbo.usuarios_dashboard.id", ondelete="SET NULL"),
        nullable=True,
    )
    usuario = relationship("Usuario", backref="notificaciones")

    fecha_creacion = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

