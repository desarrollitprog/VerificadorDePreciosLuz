"""
Modelos SQLAlchemy para el backend del dashboard.
Importa todos los modelos aquí para facilitar su uso en otras partes de la aplicación.
"""

from .usuario import Usuario, RolUsuario
from .publicidad import Publicidad
from .servidor_secundario import ServidorSecundario
from .dispositivo import Dispositivo
from .notificacion import Notificacion
from .notificacion_leida import NotificacionLeida
from .asignacion import PublicidadAsignacion

__all__ = [
    "Usuario",
    "RolUsuario",
    "Publicidad",
    "ServidorSecundario",
    "Dispositivo",
    "Notificacion",
    "NotificacionLeida",
    "PublicidadAsignacion",
]
