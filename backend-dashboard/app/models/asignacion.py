from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class PublicidadAsignacion(Base):
    """
    Relación entre publicidad y dispositivos.
    """
    __tablename__ = "publicidad_asignacion"

    id = Column(Integer, primary_key=True, index=True)
    publicidad_id = Column(
        Integer,
        ForeignKey("Publicidad.IdPublicidad", ondelete="CASCADE"),
        nullable=False
    )
    servidor_id = Column(
        Integer,
        ForeignKey("servidores_secundarios.id", ondelete="CASCADE"),
        nullable=False
    )
    dispositivo_id = Column(
        Integer,
        ForeignKey("dispositivos.id", ondelete="CASCADE"),
        nullable=False
    )
    fecha_asignacion = Column(DateTime, nullable=False, server_default=func.now())

    publicidad = relationship(
        "Publicidad",
        backref="asignaciones",
        lazy="joined"
    )
    servidor = relationship(
        "ServidorSecundario",
        backref="asignaciones",
        lazy="joined"
    )
    dispositivo = relationship(
        "Dispositivo",
        backref="asignaciones",
        lazy="joined"
    )

    __table_args__ = (
        UniqueConstraint(
            "publicidad_id",
            "servidor_id",
            "dispositivo_id",
            name="uq_asignacion"
        ),
    )
