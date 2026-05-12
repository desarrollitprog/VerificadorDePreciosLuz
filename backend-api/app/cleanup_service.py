"""
Servicio de limpieza de archivos huérfanos en backend-api.
Bot 5: Elimina archivos de banners no referenciados en la base de datos.
"""
import os
import logging
from sqlalchemy import select
from .database import get_db_publicidad
from .models.publicidad import Publicidad

logger = logging.getLogger("cleanup_service")


async def cleanup_orphan_banners() -> int:
    """
    Elimina archivos en static/banners/ que no están referenciados
    por ningún registro en la tabla Publicidad (columna Url).
    Retorna cantidad de archivos eliminados.
    """
    banners_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "static", "banners")
    )
    if not os.path.isdir(banners_dir):
        logger.warning(f"cleanup_orphan_banners: directorio no encontrado: {banners_dir}")
        return 0

    try:
        referenced = set()
        async for db in get_db_publicidad():
            result = await db.execute(select(Publicidad.url))
            for (url,) in result.all():
                if url:
                    filename = url.replace("/static/banners/", "").strip("/")
                    if filename:
                        referenced.add(filename)
            break

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
                    logger.warning(f"Error eliminando {entry}: {e}")

        if removed > 0:
            logger.info(
                f"cleanup_orphan_banners: eliminados {removed} archivos "
                f"({round(removed_size / (1024 * 1024), 2)} MB)"
            )
        return removed
    except Exception as e:
        logger.error(f"cleanup_orphan_banners error: {e}")
        return 0
