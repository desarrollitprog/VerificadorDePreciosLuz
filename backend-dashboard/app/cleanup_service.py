"""
Servicio de limpieza y mantenimiento de datos.
Bots 1-3: limpieza de sesiones antiguas, notificaciones viejas, y archivos huérfanos.
"""
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from app.database import AsyncSessionLocalUsuarios
from app.models.publicidad import Publicidad
from app.utils.logger import StructuredLogger
from sqlalchemy import select

log = StructuredLogger("cleanup_service")


async def cleanup_old_sessions() -> int:
    """
    Bot 1: Elimina sesiones de dispositivos con más de 90 días de antigüedad.
    Retorna cantidad de filas eliminadas.
    """
    try:
        async with AsyncSessionLocalUsuarios() as db:
            cutoff = datetime.now(timezone(timedelta(hours=-4))).replace(tzinfo=None) - timedelta(days=90)
            stmt = text("DELETE FROM dispositivo_sesiones WHERE fin < :cutoff")
            result = await db.execute(stmt, {"cutoff": cutoff})
            await db.commit()
            deleted = result.rowcount
            if deleted > 0:
                log.info("cleanup_old_sessions", deleted=deleted, cutoff=cutoff.isoformat())
            return deleted
    except Exception as e:
        log.error("cleanup_old_sessions_error", error=str(e))
        return 0


async def cleanup_old_notifications() -> int:
    """
    Bot 2: Elimina notificaciones con más de 15 días de antigüedad.
    NotificacionLeida se elimina en cascada por FK con ON DELETE CASCADE.
    Retorna cantidad de filas eliminadas.
    """
    try:
        async with AsyncSessionLocalUsuarios() as db:
            cutoff = datetime.now(timezone(timedelta(hours=-4))).replace(tzinfo=None) - timedelta(days=15)
            stmt = text("DELETE FROM notificaciones WHERE fecha_creacion < :cutoff")
            result = await db.execute(stmt, {"cutoff": cutoff})
            await db.commit()
            deleted = result.rowcount
            if deleted > 0:
                log.info("cleanup_old_notifications", deleted=deleted, cutoff=cutoff.isoformat())
            return deleted
    except Exception as e:
        log.error("cleanup_old_notifications_error", error=str(e))
        return 0


async def cleanup_orphan_files() -> int:
    """
    Bot 3: Elimina archivos huérfanos en static/banners/ que no están
    referenciados por ningún registro en Publicidad (Url o ThumbnailUrl).
    Retorna cantidad de archivos eliminados.
    """
    banners_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "static", "banners")
    )
    if not os.path.isdir(banners_dir):
        log.warning("cleanup_orphan_files_dir_not_found", path=banners_dir)
        return 0

    try:
        async with AsyncSessionLocalUsuarios() as db:
            stmt = select(Publicidad.Url, Publicidad.ThumbnailUrl)
            result = await db.execute(stmt)
            rows = result.all()

        referenced = set()
        for url, thumb_url in rows:
            if url:
                filename = url.replace("/static/banners/", "").strip("/")
                if filename:
                    referenced.add(filename)
            if thumb_url:
                thumb_filename = thumb_url.replace("/static/banners/", "").strip("/")
                if thumb_filename:
                    referenced.add(thumb_filename)

        removed = 0
        removed_size = 0
        for entry in os.listdir(banners_dir):
            full_path = os.path.join(banners_dir, entry)
            if not os.path.isfile(full_path):
                continue
            if entry not in referenced:
                try:
                    removed_size += os.path.getsize(full_path)
                    os.remove(full_path)
                    removed += 1
                except Exception as e:
                    log.warning("cleanup_orphan_files_remove_error", file=entry, error=str(e))

        if removed > 0:
            log.info(
                "cleanup_orphan_files",
                removed=removed,
                freed_mb=round(removed_size / (1024 * 1024), 2),
            )
        return removed
    except Exception as e:
        log.error("cleanup_orphan_files_error", error=str(e))
        return 0
