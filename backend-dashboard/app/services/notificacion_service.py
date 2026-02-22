"""
Servicio de auditoría: registra acciones en la tabla Notificacion.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notificacion import Notificacion


async def registrar_accion(
    db: AsyncSession,
    usuario_id: int,
    tipo: str,
    descripcion: str,
) -> Notificacion:
    """
    Inserta un registro de auditoría en la tabla Notificacion.

    Args:
        db: Sesión asíncrona de base de datos.
        usuario_id: ID del usuario que realizó la acción.
        tipo: Tipo de acción (ej. SUBIDA_MULTIMEDIA, BORRADO, CREAR_USUARIO).
        descripcion: Detalle de la acción (puede ser cadena vacía).

    Returns:
        La instancia Notificacion creada (con id y fecha_creacion tras el commit).
    """
    notificacion = Notificacion(
        usuario_id=usuario_id,
        tipo=tipo,
        descripcion=descripcion,
    )
    db.add(notificacion)
    await db.commit()
    await db.refresh(notificacion)
    return notificacion
