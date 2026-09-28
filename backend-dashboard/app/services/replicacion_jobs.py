import asyncio
import logging
import os
from typing import Any, Dict, Optional

from app.services.replicacion_service import replicar_archivo_a_todas_las_apis, replicar_archivos_batch_a_todas_las_apis
from ..utils import transcode_video, generar_thumbnail

logger = logging.getLogger("uvicorn.error")

REPLICATION_JOBS: Dict[str, Dict[str, Any]] = {}
REPLICATION_JOBS_LOCK = asyncio.Lock()


async def _set_job_state(job_id: str, **fields: Any) -> None:
    async with REPLICATION_JOBS_LOCK:
        existing = REPLICATION_JOBS.get(job_id, {})
        existing.update(fields)
        existing["updated_at"] = datetime.now().isoformat()
        REPLICATION_JOBS[job_id] = existing


async def _get_job_state(job_id: str) -> Optional[Dict[str, Any]]:
    async with REPLICATION_JOBS_LOCK:
        job = REPLICATION_JOBS.get(job_id)
        if job is None:
            return None
        return dict(job)


async def _execute_replication_job(
    job_id: str,
    file_path: str,
    titulo: str,
    tipo: str,
    IdPublicidadRemoto: int,
    activo: bool,
    prioridad: int,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    asignacion_todos: bool,
    dispositivo_ids: Optional[list],
    timeout: int = 300,
) -> None:
    """
    Background job: transcode (if video), then replicate to all servers.
    """
    await _set_job_state(job_id, status="TRANSCODING", progress=0)

    # Transcode if video and enabled
    if tipo == "video" and os.getenv("VIDEO_TRANSCODE_ENABLED", "1") != "0":
        try:
            # Only transcode if file is above threshold (optional)
            min_mb = int(os.getenv("VIDEO_TRANSCODE_MIN_MB", "0"))
            if min_mb > 0:
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if size_mb < min_mb:
                    logger.info(f"Video {file_path} is {size_mb:.1f} MB, below threshold {min_mb} MB, skipping transcode")
                else:
                    output_path = file_path + ".transcoded.mp4"
                    success, err = transcode_video(file_path, output_path, timeout=120)
                    if success:
                        # Replace original with transcoded
                        os.replace(output_path, file_path)
                        logger.info(f"Transcoded {file_path} successfully")
                    else:
                        logger.warning(f"Transcoding failed for {file_path}: {err}")
                        # Continue with original
        except Exception as e:
            logger.warning(f"Transcoding error: {e}")
            # Continue with original

    await _set_job_state(job_id, status="REPLICATING", progress=10)

    # Replicate to all servers
    try:
        results = await replicar_archivo_a_todas_las_apis(
            file_path=file_path,
            IdPublicidadRemoto=IdPublicidadRemoto,
            titulo=titulo,
            tipo=tipo,
            prioridad=prioridad,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activo=activo,
            dispositivo_ids=dispositivo_ids,
            timeout=timeout,
        )
        # Count successes
        successes = sum(1 for r in results if r.get("success"))
        total = len(results)
        await _set_job_state(
            job_id,
            status="COMPLETED",
            progress=100,
            success=successes == total,
            replicated_servers=successes,
            total_servers=total,
            details=results,
        )
    except Exception as e:
        logger.exception(f"Replication job {job_id} failed")
        await _set_job_state(job_id, status="FAILED", progress=0, error=str(e))