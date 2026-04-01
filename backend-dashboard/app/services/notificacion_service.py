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
    dispositivo_id: str = None,
    servidor_id: int = None,
) -> Notificacion:
    """
    Inserta un registro de auditoría en la tabla Notificacion.

    Args:
        db: Sesión asíncrona de base de datos.
        usuario_id: ID del usuario que realizó la acción.
        tipo: Tipo de acción (ej. SUBIDA_MULTIMEDIA, BORRADO, CREAR_USUARIO).
        descripcion: Detalle de la acción (puede ser cadena vacía).
        dispositivo_id: ID del dispositivo relacionado (opcional).
        servidor_id: ID del servidor relacionado (opcional).

    Returns:
        La instancia Notificacion creada (con id y fecha_creacion tras el commit).
    """
    notificacion = Notificacion(
        usuario_id=usuario_id,
        tipo=tipo,
        descripcion=descripcion,
        dispositivo_id=dispositivo_id,
        servidor_id=servidor_id,
    )
    db.add(notificacion)
    await db.commit()
    await db.refresh(notificacion)
    return notificacion
