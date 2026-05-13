import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.dependencies import get_current_cliente
from app.services.server_service import _utcnow
from app.services.sync_service import _set_job_state, _get_job_state, _execute_selective_sync_job
import uuid
import httpx

router = APIRouter(tags=["monitoreo"])
logger = logging.getLogger("uvicorn.error")


class SyncSelectivoBody(BaseModel):
    servidor_ids: Optional[List[int]] = None
    dispositivo_ids: Optional[List[str]] = None


@router.post("/monitoreo/sincronizar-fuerza")
async def sincronizar_fuerza(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
    body: SyncSelectivoBody = None,
):
    actor_name = (current_user.get("nombre_usuario") or current_user.get("usuario") or "Sistema")
    job_id = str(uuid.uuid4())

    servidor_ids = body.servidor_ids if body else None
    dispositivo_ids = body.dispositivo_ids if body else None

    await _set_job_state(
        job_id,
        status="QUEUED",
        success=None,
        created_at=_utcnow().isoformat(),
        requested_by=actor_name,
        servidor_ids=servidor_ids,
        dispositivo_ids=dispositivo_ids,
    )

    asyncio.create_task(
        _execute_selective_sync_job(
            job_id=job_id,
            user_id=current_user.get("user_id"),
            username=actor_name,
            servidor_ids=servidor_ids,
            dispositivo_ids=dispositivo_ids,
        )
    )

    return {
        "success": True,
        "message": "Sincronización en ejecución",
        "job_id": job_id,
        "status": "QUEUED",
        "servidores_seleccionados": len(servidor_ids) if servidor_ids else "todos",
        "dispositivos_seleccionados": len(dispositivo_ids) if dispositivo_ids else "todos",
    }


@router.get("/monitoreo/sincronizar-fuerza/{job_id}")
async def obtener_estado_sincronizacion(
    job_id: str,
    current_user: dict = Depends(get_current_cliente),
):
    job = await _get_job_state(job_id)
    if not job:
        return {
            "success": False,
            "message": "Job no encontrado",
            "job_id": job_id,
        }

    return {
        "success": True,
        "job_id": job_id,
        **job,
    }


@router.get("/monitoreo/cola/{device_id}")
async def obtener_cola_dispositivo(
    device_id: str,
    current_user: dict = Depends(get_current_cliente),
):
    from app.services.replicacion_service import get_api_urls

    urls = get_api_urls()
    if not urls:
        raise HTTPException(status_code=502, detail="No hay URLs de backend-api configuradas")

    async def _query(base_url: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{base_url.rstrip('/')}/api/queue-status/{device_id}")
                if resp.status_code == 200:
                    return {"server": base_url, "status": resp.json()}
        except Exception:
            pass
        return None

    results = await asyncio.gather(*[_query(u) for u in urls], return_exceptions=True)
    return [r for r in results if isinstance(r, dict)]
