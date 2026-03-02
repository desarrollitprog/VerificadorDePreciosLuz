from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class NotificacionLeida(Base):
    __tablename__ = "notificaciones_leidas"
    __table_args__ = (
        UniqueConstraint("usuario_id", "notificacion_id", name="uq_notificaciones_leidas_usuario_notificacion"),
        {"schema": "dbo"},
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(
        Integer,
        ForeignKey("dbo.usuarios_dashboard.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notificacion_id = Column(
        Integer,
        ForeignKey("notificaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha_lectura = Column(DateTime, nullable=False, default=datetime.utcnow)

    usuario = relationship("Usuario", backref="notificaciones_leidas")
    notificacion = relationship("Notificacion", backref="lecturas")
