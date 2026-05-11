from datetime import datetime, timedelta
from typing import Any, List
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocalUsuarios
from app.models.dispositivo import Dispositivo
from app.models.servidor_secundario import ServidorSecundario
from app.services.server_service import HEARTBEAT_OFFLINE_MINUTES, _utcnow
from app.services.notificacion_service import registrar_accion
import asyncio
import httpx

logger = logging.getLogger("uvicorn.error")

FORCE_SYNC_TIMEOUT_SECONDS = 120
FORCE_SYNC_POLL_INTERVAL_SECONDS = 2

SYNC_JOBS: dict[str, dict[str, Any]] = {}
SYNC_JOBS_LOCK = asyncio.Lock()


async def _set_job_state(job_id: str, **fields: Any) -> None:
    async with SYNC_JOBS_LOCK:
        existing = SYNC_JOBS.get(job_id, {})
        existing.update(fields)
        existing["updated_at"] = _utcnow().isoformat()
        SYNC_JOBS[job_id] = existing


async def _get_job_state(job_id: str) -> dict[str, Any] | None:
    async with SYNC_JOBS_LOCK:
        job = SYNC_JOBS.get(job_id)
        return dict(job) if job else None


async def _execute_force_sync_job(job_id: str, user_id: int | None, username: str | None) -> None:
    await _set_job_state(job_id, status="RUNNING")
    try:
        async with AsyncSessionLocalUsuarios() as db:
            stmt = select(ServidorSecundario)
            result = await db.execute(stmt)
            servidores = result.scalars().all()

            now = _utcnow()
            umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)
            online_servers = [
                s for s in servidores
                if s.ultimo_heartbeat and s.ultimo_heartbeat >= umbral
            ]

            async def send_force_sync(ip: str, on_progress: Any = None) -> dict[str, Any]:
                url = f"http://{ip}:8000/api/fuerza-sync"
                try:
                    async with httpx.AsyncClient(timeout=FORCE_SYNC_TIMEOUT_SECONDS) as client:
                        resp = await client.post(url, params={"async_mode": "true"})
                        payload: dict[str, Any] = {}
                        try:
                            payload = resp.json()
                        except Exception:
                            logger.warning("json_parse_failed", extra={"url": str(resp.url)})
                            payload = {}

                        if resp.status_code != 200 or not bool(payload.get("success", True)):
                            return {
                                "ok": False,
                                "status_code": resp.status_code,
                                "backend_result": payload,
                                "reason": payload.get("message") if isinstance(payload, dict) else "Error iniciando sync",
                            }

                        remote_job_id = payload.get("job_id") if isinstance(payload, dict) else None
                        if not remote_job_id:
                            ok = resp.status_code == 200 and bool(payload.get("success", True))
                            return {
                                "ok": ok,
                                "status_code": resp.status_code,
                                "backend_result": payload,
                                "reason": payload.get("message") if isinstance(payload, dict) else None,
                            }

                        poll_url = f"http://{ip}:8000/api/fuerza-sync/{remote_job_id}"
                        deadline = asyncio.get_running_loop().time() + FORCE_SYNC_TIMEOUT_SECONDS

                        while True:
                            if asyncio.get_running_loop().time() > deadline:
                                return {
                                    "ok": False,
                                    "status_code": 504,
                                    "backend_result": {
                                        "total": 0,
                                        "sent": 0,
                                        "confirmed": 0,
                                        "failed": 0,
                                        "details": [],
                                    },
                                    "reason": "Timeout esperando progreso de sincronización",
                                }

                            poll_resp = await client.get(poll_url)
                            poll_payload: dict[str, Any] = {}
                            try:
                                poll_payload = poll_resp.json()
                            except Exception:
                                logger.warning("json_parse_failed", extra={"url": str(poll_resp.url)})
                                poll_payload = {}

                            if on_progress is not None and isinstance(poll_payload, dict):
                                await on_progress(poll_payload)

                            status = str(poll_payload.get("status", "")).upper()
                            if status in ("COMPLETED", "FAILED"):
                                ok = status == "COMPLETED" and bool(poll_payload.get("success", True))
                                return {
                                    "ok": ok,
                                    "status_code": poll_resp.status_code,
                                    "backend_result": poll_payload,
                                    "reason": poll_payload.get("error") or poll_payload.get("message"),
                                }

                            await asyncio.sleep(FORCE_SYNC_POLL_INTERVAL_SECONDS)
                except Exception as e:
                    return {
                        "ok": False,
                        "status_code": 500,
                        "error": str(e),
                    }

            servidores_ejecutados = await asyncio.gather(
                *[send_force_sync(s.ip) for s in online_servidores]
            )

            success_count = 0
            failed_count = 0
            details: list[dict[str, Any]] = []

            await _set_job_state(
                job_id,
                status="RUNNING",
                success=True,
                total_online=len(online_servers),
                success_count=success_count,
                failed_count=failed_count,
                details=details,
            )

            for server in online_servers:
                detail = {
                    "ip": server.ip,
                    "nombre": server.nombre,
                    "ok": False,
                    "status_code": None,
                    "reason": "Sincronizando...",
                    "sync_total": 0,
                    "sync_sent": 0,
                    "sync_confirmed": 0,
                    "sync_failed": 0,
                    "sync_details": [],
                }
                details.append(detail)

                await _set_job_state(
                    job_id,
                    status="RUNNING",
                    success=True,
                    total_online=len(online_servers),
                    success_count=success_count,
                    failed_count=failed_count,
                    details=details,
                )

                async def on_server_progress(progress_payload: dict[str, Any]) -> None:
                    detail["sync_total"] = progress_payload.get("total")
                    detail["sync_sent"] = progress_payload.get("sent")
                    detail["sync_confirmed"] = progress_payload.get("confirmed")
                    detail["sync_failed"] = progress_payload.get("failed")
                    detail["sync_queued"] = progress_payload.get("queued", 0)
                    detail["sync_details"] = progress_payload.get("details", [])
                    if str(progress_payload.get("status", "")).upper() == "RUNNING":
                        detail["reason"] = "Sincronizando..."

                    await _set_job_state(
                        job_id,
                        status="RUNNING",
                        success=True,
                        total_online=len(online_servers),
                        success_count=success_count,
                        failed_count=failed_count,
                        details=details,
                    )

                result_item = await send_force_sync(server.ip, on_progress=on_server_progress)
                backend_result = result_item.get("backend_result") or {}
                detail["ok"] = result_item.get("ok") is True
                detail["status_code"] = result_item.get("status_code")
                detail["reason"] = result_item.get("reason")
                detail["sync_total"] = backend_result.get("total")
                detail["sync_sent"] = backend_result.get("sent")
                detail["sync_confirmed"] = backend_result.get("confirmed")
                detail["sync_failed"] = backend_result.get("failed")
                detail["sync_queued"] = backend_result.get("queued", 0)
                detail["sync_details"] = backend_result.get("details", [])

                if detail["ok"]:
                    success_count += 1
                else:
                    failed_count += 1

                await _set_job_state(
                    job_id,
                    status="RUNNING",
                    success=True,
                    total_online=len(online_servers),
                    success_count=success_count,
                    failed_count=failed_count,
                    details=details,
                )

            failed_servers = [d for d in details if not d["ok"]]
            resumen_fallos = ", ".join(
                f"{d['nombre']}({d['reason'] or 'sin motivo'})" for d in failed_servers[:5]
            )

            if user_id is not None:
                actor_name = (username or "").strip() or "Sistema"
                await registrar_accion(
                    db,
                    user_id,
                    "SINCRONIZACION_FORZADA",
                    (
                        f"Sincronización forzada ejecutada por usuario {actor_name}. "
                        f"Servidores online: {len(online_servers)}, éxito: {success_count}, fallo: {failed_count}. "
                        f"Fallos: {resumen_fallos if resumen_fallos else 'ninguno'}"
                    ),
                    dispositivo_id=None,
                    servidor_id=None,
                )

            await _set_job_state(
                job_id,
                status="COMPLETED",
                success=True,
                total_online=len(online_servers),
                success_count=success_count,
                failed_count=failed_count,
                details=details,
            )
    except Exception as e:
        await _set_job_state(
            job_id,
            status="FAILED",
            success=False,
            error=str(e),
        )


async def _get_dispositivos_por_servidor(db: AsyncSession, servidor_ids: List[int] = None, dispositivo_ids: List[str] = None) -> dict:
    query = select(Dispositivo)
    if dispositivo_ids:
        query = query.where(Dispositivo.codigo_kiosko.in_(dispositivo_ids))
    result = await db.execute(query)
    dispositivos = result.scalars().all()

    mapa = {}
    for d in dispositivos:
        if servidor_ids and d.servidor_id not in servidor_ids:
            continue
        if d.servidor_id and d.servidor_id not in mapa:
            mapa[d.servidor_id] = []
        if d.servidor_id:
            mapa[d.servidor_id].append(d.codigo_kiosko)

    return mapa


async def _execute_selective_sync_job(
    job_id: str,
    user_id: int | None,
    username: str | None,
    servidor_ids: List[int] = None,
    dispositivo_ids: List[str] = None,
) -> None:
    await _set_job_state(job_id, status="RUNNING")
    try:
        async with AsyncSessionLocalUsuarios() as db:
            stmt = select(ServidorSecundario)
            result = await db.execute(stmt)
            servidores = result.scalars().all()

            now = _utcnow()
            umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

            online_servers = [
                s for s in servidores
                if s.ultimo_heartbeat and s.ultimo_heartbeat >= umbral
            ]

            servidor_ids_a_buscar = servidor_ids
            if dispositivo_ids and not servidor_ids:
                dispositivos_mapa = await _get_dispositivos_por_servidor(db, None, dispositivo_ids)
                servidor_ids_automatico = list(dispositivos_mapa.keys())
                logger.debug(f"Dispositivo_ids sin servidores. Servers automáticos: {servidor_ids_automatico}")
                online_servers = [s for s in online_servers if s.id in servidor_ids_automatico]
                servidor_ids_a_buscar = servidor_ids_automatico
            elif servidor_ids:
                online_servers = [s for s in online_servers if s.id in servidor_ids]
                servidor_ids_a_buscar = servidor_ids

            dispositivos_por_servidor = await _get_dispositivos_por_servidor(
                db, servidor_ids_a_buscar, dispositivo_ids
            )
            logger.debug(f"Sync selectivo: servers={servidor_ids_a_buscar}, dispositivos={len(dispositivo_ids) if dispositivo_ids else 0}")

            async def send_selective_sync(ip: str, dispositivo_ids_list: List[str] = None, on_progress: Any = None) -> dict[str, Any]:
                url = f"http://{ip}:8000/api/fuerza-sync"
                try:
                    params = {"async_mode": "true"}
                    if dispositivo_ids_list:
                        logger.debug(f"Enviando sync a servidor {ip}: {len(dispositivo_ids_list)} dispositivos")
                        params["dispositivo_ids"] = ",".join(dispositivo_ids_list)

                    async with httpx.AsyncClient(timeout=FORCE_SYNC_TIMEOUT_SECONDS) as client:
                        resp = await client.post(url, params=params)
                        payload_response: dict[str, Any] = {}
                        try:
                            payload_response = resp.json()
                        except Exception:
                            payload_response = {}

                        if resp.status_code != 200 or not bool(payload_response.get("success", True)):
                            return {
                                "ok": False,
                                "status_code": resp.status_code,
                                "backend_result": payload_response,
                                "reason": payload_response.get("message") if isinstance(payload_response, dict) else "Error iniciando sync",
                            }

                        remote_job_id = payload_response.get("job_id") if isinstance(payload_response, dict) else None
                        if not remote_job_id:
                            ok = resp.status_code == 200 and bool(payload_response.get("success", True))
                            return {
                                "ok": ok,
                                "status_code": resp.status_code,
                                "backend_result": payload_response,
                                "reason": payload_response.get("message") if isinstance(payload_response, dict) else None,
                            }

                        poll_url = f"http://{ip}:8000/api/fuerza-sync/{remote_job_id}"
                        deadline = asyncio.get_running_loop().time() + FORCE_SYNC_TIMEOUT_SECONDS

                        while True:
                            if asyncio.get_running_loop().time() > deadline:
                                return {
                                    "ok": False,
                                    "status_code": 504,
                                    "backend_result": {"total": 0, "sent": 0, "confirmed": 0, "failed": 0, "details": []},
                                    "reason": "Timeout esperando progreso de sincronización",
                                }

                            poll_resp = await client.get(poll_url)
                            poll_payload: dict[str, Any] = {}
                            try:
                                poll_payload = poll_resp.json()
                            except Exception:
                                logger.warning("json_parse_failed", extra={"url": str(poll_resp.url)})
                                poll_payload = {}

                            if on_progress is not None and isinstance(poll_payload, dict):
                                await on_progress(poll_payload)

                            status = str(poll_payload.get("status", "")).upper()
                            if status in ("COMPLETED", "FAILED"):
                                ok = status == "COMPLETED" and bool(poll_payload.get("success", True))
                                return {
                                    "ok": ok,
                                    "status_code": poll_resp.status_code,
                                    "backend_result": poll_payload,
                                    "reason": poll_payload.get("error") or poll_payload.get("message"),
                                }

                            await asyncio.sleep(FORCE_SYNC_POLL_INTERVAL_SECONDS)
                except Exception as e:
                    return {
                        "ok": False,
                        "status_code": 500,
                        "error": str(e),
                    }

            success_count = 0
            failed_count = 0
            details: list[dict[str, Any]] = []

            await _set_job_state(
                job_id,
                status="RUNNING",
                success=True,
                total_online=len(online_servers),
                success_count=success_count,
                failed_count=failed_count,
                details=details,
            )

            for server in online_servers:
                disp_ids = dispositivos_por_servidor.get(server.id, None)

                detail = {
                    "ip": server.ip,
                    "nombre": server.nombre,
                    "ok": False,
                    "status_code": None,
                    "reason": "Sincronizando...",
                    "dispositivos_seleccionados": len(disp_ids) if disp_ids else "todos",
                    "sync_total": 0,
                    "sync_sent": 0,
                    "sync_confirmed": 0,
                    "sync_failed": 0,
                    "sync_details": [],
                }
                details.append(detail)

                await _set_job_state(
                    job_id,
                    status="RUNNING",
                    success=True,
                    total_online=len(online_servers),
                    success_count=success_count,
                    failed_count=failed_count,
                    details=details,
                )

                async def on_server_progress(progress_payload: dict[str, Any]) -> None:
                    detail["sync_total"] = progress_payload.get("total")
                    detail["sync_sent"] = progress_payload.get("sent")
                    detail["sync_confirmed"] = progress_payload.get("confirmed")
                    detail["sync_failed"] = progress_payload.get("failed")
                    detail["sync_queued"] = progress_payload.get("queued", 0)
                    detail["sync_details"] = progress_payload.get("details", [])
                    if str(progress_payload.get("status", "")).upper() == "RUNNING":
                        detail["reason"] = "Sincronizando..."
                    await _set_job_state(
                        job_id,
                        status="RUNNING",
                        success=True,
                        total_online=len(online_servers),
                        success_count=success_count,
                        failed_count=failed_count,
                        details=details,
                    )

                result_item = await send_selective_sync(server.ip, disp_ids, on_progress=on_server_progress)
                backend_result = result_item.get("backend_result") or {}
                detail["ok"] = result_item.get("ok") is True
                detail["status_code"] = result_item.get("status_code")
                detail["reason"] = result_item.get("reason")
                detail["sync_total"] = backend_result.get("total")
                detail["sync_sent"] = backend_result.get("sent")
                detail["sync_confirmed"] = backend_result.get("confirmed")
                detail["sync_failed"] = backend_result.get("failed")
                detail["sync_queued"] = backend_result.get("queued", 0)
                detail["sync_details"] = backend_result.get("details", [])

                if detail["ok"]:
                    success_count += 1
                else:
                    failed_count += 1

                await _set_job_state(
                    job_id,
                    status="RUNNING",
                    success=True,
                    total_online=len(online_servers),
                    success_count=success_count,
                    failed_count=failed_count,
                    details=details,
                )

            failed_servers = [d for d in details if not d["ok"]]
            resumen_fallos = ", ".join(
                f"{d['nombre']}({d['reason'] or 'sin motivo'})" for d in failed_servers[:5]
            )

            if user_id is not None:
                actor_name = (username or "").strip() or "Sistema"

                disp_id = dispositivo_ids[0] if dispositivo_ids else None
                srv_id = servidor_ids_a_buscar[0] if servidor_ids_a_buscar else None

                disp_info = f", Dispositivos: {dispositivo_ids}" if dispositivo_ids else ", Dispositivos: todos"
                srv_info = f", Servidores: {servidor_ids_a_buscar}" if servidor_ids_a_buscar else ""

                await registrar_accion(
                    db,
                    user_id,
                    "SINCRONIZACION_SELECTIVA",
                    (
                        f"Sincronización selectiva ejecutada por usuario {actor_name}. "
                        f"Servidores online: {len(online_servers)}, éxito: {success_count}, fallo: {failed_count}"
                        f"{disp_info}{srv_info}"
                    ),
                    dispositivo_id=disp_id,
                    servidor_id=srv_id,
                )

            await _set_job_state(
                job_id,
                status="COMPLETED",
                success=True,
                total_online=len(online_servers),
                success_count=success_count,
                failed_count=failed_count,
                details=details,
            )
    except Exception as e:
        await _set_job_state(
            job_id,
            status="FAILED",
            success=False,
            error=str(e),
        )
