"""
Modelos SQLAlchemy para el backend del dashboard.
Importa todos los modelos aquí para facilitar su uso en otras partes de la aplicación.
"""

from .usuario import Usuario
from .publicidad import Publicidad

__all__ = [
    "Usuario",
    "Publicidad"
]
