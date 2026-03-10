"""
Modelos SQLAlchemy para el backend del dashboard.
Importa todos los modelos aquí para facilitar su uso en otras partes de la aplicación.
"""

from sqlalchemy.orm import relationship
from .usuario import Usuario, RolUsuario
from .publicidad import Publicidad
from .servidor_secundario import ServidorSecundario
from .dispositivo import Dispositivo
from .notificacion import Notificacion
from .notificacion_leida import NotificacionLeida
from .publicidad_dispositivo import publicidad_dispositivo

# INYECCIÓN DE RELACIONES (Patching)
# Lo hacemos aquí para que Publicidad y Dispositivo ya estén cargados
Publicidad.dispositivos = relationship(
    "Dispositivo",
    secondary=publicidad_dispositivo,
    back_populates="publicidades",
    lazy="selectin"
)

Dispositivo.publicidades = relationship(
    "Publicidad",
    secondary=publicidad_dispositivo,
    back_populates="dispositivos",
    lazy="selectin"
)

__all__ = [
    "Usuario",
    "RolUsuario",
    "Publicidad",
    "ServidorSecundario",
    "Dispositivo",
    "Notificacion",
    "NotificacionLeida",
    "publicidad_dispositivo"
]