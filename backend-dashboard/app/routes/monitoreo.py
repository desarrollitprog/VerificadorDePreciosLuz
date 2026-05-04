
"""
Rutas de monitoreo: heartbeat de servidores secundarios y estado.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios, AsyncSessionLocalUsuarios
from app.dependencies import get_current_cliente, validar_api_key, get_current_admin
from app.models.dispositivo import Dispositivo
from app.models.dispositivo_sesion import DispositivoSesion
from app.models.servidor_secundario import ServidorSecundario
from app.services.notificacion_service import registrar_accion
import asyncio
import uuid
import httpx
router = APIRouter(tags=["monitoreo"])
logger = logging.getLogger("uvicorn.error")


class HeartbeatBody(BaseModel):
    nombre_servidor: str
    ip: str
    almacenamiento_total: int
    almacenamiento_usado: int


class SyncSelectivoBody(BaseModel):
    servidor_ids: Optional[List[int]] = None
    dispositivo_ids: Optional[List[str]] = None



class DeviceRenameBody(BaseModel):
    nombre_amigable: str | None = None


class ServerRenameBody(BaseModel):
    nombre: str


def _utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


async def _obtener_dispositivos_de_servidor(ip: str) -> list[dict[str, Any]]:
    """
    Consulta al backend-api del servidor secundario:
    GET http://{ip}:8000/devices/status
    """
    url = f"http://{ip}:8000/devices/status"
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()

        if not isinstance(payload, dict):
            return []

        dispositivos: list[dict[str, Any]] = []
        for device_id, info in payload.items():
            if not isinstance(info, dict):
                continue
            dispositivos.append(
                {
                    "device_id": str(device_id),
                    "online": bool(info.get("online", False)),
                    "last_seen": info.get("last_seen"),
                    "server_id": info.get("server_id"),
                }
            )

        dispositivos.sort(key=lambda d: d["device_id"])
        logger.info("status-detalle: %s reportó %s dispositivos", ip, len(dispositivos))
        return dispositivos
    except Exception as e:
        logger.warning("status-detalle: fallo consultando %s: %s", url, e)
        return []


async def _obtener_conteo_videos_servidor(ip: str) -> int:
    url = f"http://{ip}:8000/banners"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()

        if isinstance(payload, list):
            return len(payload)
        return 0
    except Exception as e:
        logger.warning("videos-servidor: fallo consultando %s: %s", url, e)
        return 0


@router.post("/heartbeat")
async def heartbeat(
    body: HeartbeatBody,
    db: AsyncSession = Depends(get_db_usuarios),
    _: bool = Depends(validar_api_key),
):
    """
    Llamado por los servidores secundarios.
    Crea el servidor si no existe; si existe, actualiza IP, almacenamiento y ultimo_heartbeat.
    """
    now = _utcnow()
    nombre_servidor = (body.nombre_servidor or "").strip()
    ip_servidor = (body.ip or "").strip()

    # 1) Prioridad por IP (más estable que hostname en despliegues con contenedores)
    stmt_ip = select(ServidorSecundario).where(ServidorSecundario.ip == ip_servidor).order_by(ServidorSecundario.id.asc())
    result_ip = await db.execute(stmt_ip)
    servidor = result_ip.scalars().first()

    # 2) Fallback por nombre (compatibilidad hacia atrás)
    if servidor is None:
        stmt_nombre = select(ServidorSecundario).where(ServidorSecundario.nombre == nombre_servidor).order_by(ServidorSecundario.id.asc())
        result_nombre = await db.execute(stmt_nombre)
        servidor = result_nombre.scalars().first()

    if servidor:
        if not (servidor.nombre or "").strip():
            servidor.nombre = nombre_servidor
        servidor.ip = ip_servidor
        servidor.almacenamiento_total = body.almacenamiento_total
        servidor.almacenamiento_usado = body.almacenamiento_usado
        servidor.ultimo_heartbeat = now
    else:
        servidor = ServidorSecundario(
            nombre=nombre_servidor,
            ip=ip_servidor,
            almacenamiento_total=body.almacenamiento_total,
            almacenamiento_usado=body.almacenamiento_usado,
            ultimo_heartbeat=now,
        )
        db.add(servidor)

    await db.commit()
    await db.refresh(servidor)
    return {
        "success": True,
        "message": "Heartbeat registrado.",
        "servidor_id": servidor.id,
    }


# Umbral: sin heartbeat en los últimos 8 minutos = offline
HEARTBEAT_OFFLINE_MINUTES = 8
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
                        "status_code": None,
                        "backend_result": {},
                        "reason": str(e),
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
    """
    Obtiene los dispositivos filtrados por servidor y/o dispositivo.
    Retorna: {servidor_id: [codigo_kiosko, ...]}
    """
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
    """
    Ejecuta sincronización forzada: solo servidores y/o dispositivos específicos.
    """
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
            
            # Si se especifican dispositivo_ids pero no servidor_ids,
            # determinar automáticamente los servidores basados en los dispositivos
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
                        "status_code": None,
                        "backend_result": {},
                        "reason": str(e),
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


@router.get("/status")
async def status(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Devuelve la lista de todos los servidores.
    Marca como offline los que no han enviado heartbeat en los últimos 5 minutos.
    Requiere autenticación (Cliente o Admin).
    Además, registra en auditoría los cambios de estado y genera alertas automáticas.
    """
    now = _utcnow()
    umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

    stmt = select(ServidorSecundario).order_by(ServidorSecundario.nombre)
    result = await db.execute(stmt)
    servidores = result.scalars().all()

    lista = []
    usuario_id = current_user.get("user_id") if current_user else None
    espacio_critico_umbral = 0.95  # 95% de uso

    for s in servidores:
        online = s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral
        # Auditoría: registrar cambio de estado
        estado_actual = "ONLINE" if online else "OFFLINE"
        estado_prev = getattr(s, "_last_estado", None)
        if estado_prev is not None and estado_actual != estado_prev:
            await registrar_accion(
                db,
                usuario_id,
                tipo="CAMBIO_ESTADO_SERVIDOR",
                descripcion=f"Servidor '{s.nombre}' cambió a {estado_actual}"
            )
        s._last_estado = estado_actual

        # Alerta automática: espacio crítico
        espacio_usado = s.almacenamiento_usado / s.almacenamiento_total if s.almacenamiento_total else 0
        if online and espacio_usado >= espacio_critico_umbral:
            await registrar_accion(
                db,
                usuario_id,
                tipo="ALERTA_SERVIDOR",
                descripcion=f"Servidor '{s.nombre}' espacio crítico: {espacio_usado*100:.1f}%"
            )

        total = s.almacenamiento_total or 0
        usado = s.almacenamiento_usado or 0
        porcentaje_uso = (usado / total * 100) if total > 0 else 0.0

        lista.append({
            "id": s.id,
            "nombre": s.nombre,
            "ip": s.ip,
            "almacenamiento_total": s.almacenamiento_total,
            "almacenamiento_usado": s.almacenamiento_usado,
            "ultimo_heartbeat": s.ultimo_heartbeat.isoformat() if s.ultimo_heartbeat else None,
            "online": online,
            "porcentaje_uso": round(porcentaje_uso, 2),
        })

    return {"success": True, "servidores": lista}


@router.get("/status-detalle")
async def status_detalle(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Devuelve servidores + dispositivos conectados (consultando /devices/status por IP).
    """
    now = _utcnow()
    umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

    stmt = select(ServidorSecundario).order_by(ServidorSecundario.nombre)
    result = await db.execute(stmt)
    servidores = result.scalars().all()

    dispositivos_result = await db.execute(select(Dispositivo))
    dispositivos_db = list(dispositivos_result.scalars().all())
    dispositivo_por_codigo: dict[str, Dispositivo] = {
        d.codigo_kiosko: d for d in dispositivos_db
    }

    lista = []
    for s in servidores:
        online = s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral
        total = s.almacenamiento_total or 0
        usado = s.almacenamiento_usado or 0
        porcentaje_uso = (usado / total * 100) if total > 0 else 0.0

        dispositivos_runtime = await _obtener_dispositivos_de_servidor(s.ip) if online else []
        runtime_por_codigo = {d["device_id"]: d for d in dispositivos_runtime}

        if online:
            vistos = set(runtime_por_codigo.keys())

            for codigo, info in runtime_por_codigo.items():
                dispositivo = dispositivo_por_codigo.get(codigo)
                if dispositivo is None:
                    dispositivo = Dispositivo(
                        codigo_kiosko=codigo,
                        online=bool(info.get("online", False)),
                        servidor_id=s.id,
                    )
                    db.add(dispositivo)
                    dispositivo_por_codigo[codigo] = dispositivo
                    
                    if bool(info.get("online", False)):
                        sesion = DispositivoSesion(
                            dispositivo_id=codigo,
                            inicio=now,
                        )
                        db.add(sesion)
                        await db.flush()
                else:
                    estaba_online = dispositivo.online
                    ahora_online = bool(info.get("online", False))
                    
                    if not estaba_online and ahora_online:
                        sesion = DispositivoSesion(
                            dispositivo_id=codigo,
                            inicio=now,
                        )
                        db.add(sesion)
                        await db.flush()
                    elif estaba_online and not ahora_online:
                        stmt_sesion = select(DispositivoSesion).where(
                            DispositivoSesion.dispositivo_id == codigo,
                            DispositivoSesion.fin == None
                        )
                        result_sesion = await db.execute(stmt_sesion)
                        sesion_activa = result_sesion.scalars().first()
                        if sesion_activa:
                            sesion_activa.fin = now
                            duracion = int((now - sesion_activa.inicio).total_seconds())
                            sesion_activa.duracion_segundos = duracion
                            await db.flush()
                    
                    dispositivo.online = ahora_online
                    dispositivo.servidor_id = s.id

            for dispositivo in dispositivo_por_codigo.values():
                if dispositivo.servidor_id == s.id and dispositivo.codigo_kiosko not in vistos:
                    if dispositivo.online:
                        stmt_sesion = select(DispositivoSesion).where(
                            DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                            DispositivoSesion.fin == None
                        )
                        result_sesion = await db.execute(stmt_sesion)
                        sesion_activa = result_sesion.scalars().first()
                        if sesion_activa:
                            sesion_activa.fin = now
                            duracion = int((now - sesion_activa.inicio).total_seconds())
                            sesion_activa.duracion_segundos = duracion
                            await db.flush()
                    dispositivo.online = False
        else:
            for dispositivo in dispositivo_por_codigo.values():
                if dispositivo.servidor_id == s.id:
                    if dispositivo.online:
                        stmt_sesion = select(DispositivoSesion).where(
                            DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                            DispositivoSesion.fin == None
                        )
                        result_sesion = await db.execute(stmt_sesion)
                        sesion_activa = result_sesion.scalars().first()
                        if sesion_activa:
                            sesion_activa.fin = now
                            duracion = int((now - sesion_activa.inicio).total_seconds())
                            sesion_activa.duracion_segundos = duracion
                            await db.flush()
                    dispositivo.online = False

        dispositivos: list[dict[str, Any]] = []
        for dispositivo in dispositivo_por_codigo.values():
            if dispositivo.servidor_id != s.id:
                continue

            runtime_info = runtime_por_codigo.get(dispositivo.codigo_kiosko, {})
            is_online = bool(dispositivo.online) and online
            nombre_amigable = dispositivo.nombre_amigable
            nombre_mostrado = nombre_amigable if nombre_amigable else dispositivo.codigo_kiosko

            stmt_sesion_activa = select(DispositivoSesion).where(
                DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                DispositivoSesion.fin == None
            )
            result_sesion_activa = await db.execute(stmt_sesion_activa)
            sesion_activa = result_sesion_activa.scalars().first()

            sesion_activa_bool = sesion_activa is not None
            
            tiempo_actual = None
            if sesion_activa:
                tiempo_actual = int((now - sesion_activa.inicio).total_seconds())

            stmt_ultima = select(DispositivoSesion).where(
                DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                DispositivoSesion.duracion_segundos != None
            ).order_by(DispositivoSesion.inicio.desc()).limit(1)
            result_ultima = await db.execute(stmt_ultima)
            ultima_sesion = result_ultima.scalars().first()
            ultima_duracion = ultima_sesion.duracion_segundos if ultima_sesion else None

            stmt_total = select(func.sum(DispositivoSesion.duracion_segundos)).where(
                DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                DispositivoSesion.duracion_segundos != None
            )
            result_total = await db.execute(stmt_total)
            tiempo_acumulado = result_total.scalar() or 0

            dispositivos.append(
                {
                    "device_id": dispositivo.codigo_kiosko,
                    "nombre_amigable": nombre_amigable,
                    "nombre_mostrado": nombre_mostrado,
                    "online": is_online,
                    "last_seen": runtime_info.get("last_seen"),
                    "sesion_activa": sesion_activa_bool,
                    "tiempo_actual": tiempo_actual,
                    "ultima_duracion": ultima_duracion,
                    "tiempo_acumulado": tiempo_acumulado,
                    "server_id": runtime_info.get("server_id"),
                    "hora_reinicio": getattr(dispositivo, 'hora_reinicio', None),
                    "reinicio_recurrente": getattr(dispositivo, 'reinicio_recurrente', False),
                }
            )

        dispositivos.sort(key=lambda d: (d["nombre_mostrado"] or "").lower())
        dispositivos_online = sum(1 for d in dispositivos if d.get("online"))

        lista.append(
            {
                "id": s.id,
                "nombre": s.nombre,
                "ip": s.ip,
                "almacenamiento_total": total,
                "almacenamiento_usado": usado,
                "ultimo_heartbeat": s.ultimo_heartbeat.isoformat() if s.ultimo_heartbeat else None,
                "online": online,
                "porcentaje_uso": round(porcentaje_uso, 2),
                "dispositivos_total": len(dispositivos),
                "dispositivos_online": dispositivos_online,
                "dispositivos": dispositivos,
            }
        )

    await db.commit()
    logger.info("status-detalle: respuesta generada para %s servidores", len(lista))

    return {"success": True, "servidores": lista}


@router.patch("/dispositivos/{device_id}/nombre")
async def renombrar_dispositivo(
    device_id: str,
    body: DeviceRenameBody,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    stmt = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result = await db.execute(stmt)
    dispositivo = result.scalars().first()
    result.close()

    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    nuevo_nombre = (body.nombre_amigable or "").strip()
    dispositivo.nombre_amigable = nuevo_nombre if nuevo_nombre else None

    await db.commit()

    user_id = current_user.get("user_id") if current_user else None
    if user_id is not None:
        nombre_para_log = dispositivo.nombre_amigable or dispositivo.codigo_kiosko
        try:
            await registrar_accion(
                db,
                user_id,
                "RENOMBRAR_DISPOSITIVO",
                f"Dispositivo {dispositivo.codigo_kiosko} renombrado a '{nombre_para_log}'",
                dispositivo_id=dispositivo.codigo_kiosko,
                servidor_id=dispositivo.servidor_id,
            )
        except Exception as e:
            logger.warning("No se pudo registrar auditoría de rename para %s: %s", dispositivo.codigo_kiosko, e)

    return {
        "success": True,
        "device_id": dispositivo.codigo_kiosko,
        "nombre_amigable": dispositivo.nombre_amigable,
    }


@router.patch("/servidores/{server_id}/nombre")
async def renombrar_servidor(
    server_id: int,
    body: ServerRenameBody,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    nuevo_nombre = (body.nombre or "").strip()
    if not nuevo_nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")

    stmt_exists = select(ServidorSecundario).where(
        func.lower(ServidorSecundario.nombre) == nuevo_nombre.lower(),
        ServidorSecundario.id != server_id,
    )
    result_exists = await db.execute(stmt_exists)
    existing = result_exists.scalars().first()
    result_exists.close()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un servidor con ese nombre")

    stmt = select(ServidorSecundario).where(ServidorSecundario.id == server_id)
    result = await db.execute(stmt)
    servidor = result.scalars().first()
    result.close()

    if not servidor:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    servidor.nombre = nuevo_nombre
    await db.commit()

    user_id = current_user.get("user_id") if current_user else None
    if user_id is not None:
        try:
            await registrar_accion(
                db,
                user_id,
                "RENOMBRAR_SERVIDOR",
                f"Servidor {servidor.ip} renombrado a '{servidor.nombre}'",
            )
        except Exception as e:
            logger.warning("No se pudo registrar auditoría de rename para servidor %s: %s", servidor.id, e)

    return {
        "success": True,
        "server_id": servidor.id,
        "nombre": servidor.nombre,
        "ip": servidor.ip,
    }


@router.get("/monitoreo/servidores/videos-actuales")
async def servidores_videos_actuales(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    now = _utcnow()
    umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

    stmt = select(ServidorSecundario).order_by(ServidorSecundario.nombre)
    result = await db.execute(stmt)
    servidores = result.scalars().all()

    online_servers = [
        s for s in servidores
        if s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral
    ]

    conteos = await asyncio.gather(*[_obtener_conteo_videos_servidor(s.ip) for s in online_servers])

    data = []
    for server, count in zip(online_servers, conteos):
        data.append(
            {
                "id": server.id,
                "nombre": server.nombre,
                "ip": server.ip,
                "videos_actuales": int(count),
            }
        )

    return {
        "success": True,
        "servidores": data,
    }

@router.get("/alertas")
async def obtener_alertas(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    stmt = select(ServidorSecundario)
    result = await db.execute(stmt)
    servidores = result.scalars().all()
    alertas = []
    for s in servidores:
        if s.almacenamiento_total and s.almacenamiento_usado:
            porcentaje = (s.almacenamiento_usado / s.almacenamiento_total) * 100
            if porcentaje > 90:
                alertas.append({
                    "nombre_servidor": s.nombre,
                    "mensaje": f"Advertencia: el servidor '{s.nombre}' está al {porcentaje:.1f}% de capacidad."
                })
    return alertas

#Sincronizacion manual de Banners
@router.post("/monitoreo/sincronizar-fuerza")
async def sincronizar_fuerza(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
    body: SyncSelectivoBody = None,
):
    """
    Inicia la sincronización forzada en background.
    Si no se especifican servidor_ids, sincroniza todos los servidores online.
    Si se especifican servidor_ids, solo sincroniza esos servidores.
    Si se especifican dispositivo_ids, solo sincroniza esos dispositivos.
    """
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


@router.delete("/dispositivos/{device_id}")
async def eliminar_dispositivo(
    device_id: str,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    stmt = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result = await db.execute(stmt)
    dispositivo = result.scalars().first()
    result.close()

    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Eliminar asignaciones de publicidad relacionadas
    from app.models.asignacion import PublicidadAsignacion
    from sqlalchemy import delete as sql_delete

    stmt_asig = sql_delete(PublicidadAsignacion).where(
        PublicidadAsignacion.dispositivo_id == device_id
    )
    await db.execute(stmt_asig)

    # Eliminar sesiones relacionadas
    stmt_ses = sql_delete(DispositivoSesion).where(
        DispositivoSesion.dispositivo_id == device_id
    )
    await db.execute(stmt_ses)

    servidor_id = dispositivo.servidor_id
    nombre_para_log = dispositivo.nombre_amigable or dispositivo.codigo_kiosko

    await db.delete(dispositivo)
    await db.commit()

    # Desvincular el dispositivo del servidor secundario
    if servidor_id:
        stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == servidor_id)
        result_srv = await db.execute(stmt_srv)
        servidor = result_srv.scalars().first()
        
        if servidor:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.delete(f"http://{servidor.ip}:8000/devices/{device_id}")
                    if response.status_code == 200:
                        logger.info(f"Dispositivo {device_id} desvinculado del servidor {servidor.ip}: {response.status_code}")
                    else:
                        logger.warning(f"Dispositivo {device_id} no se pudo desvincular del servidor {servidor.ip}: {response.status_code}")
            except Exception as e:
                logger.warning(f"No se pudo desvincular {device_id} del servidor {servidor.ip}: {e}")

    user_id = current_user.get("user_id") if current_user else None
    if user_id is not None:
        try:
            await registrar_accion(
                db,
                user_id,
                "ELIMINAR_DISPOSITIVO",
                f"Dispositivo '{nombre_para_log}' ({device_id}) eliminado",
                dispositivo_id=device_id,
                servidor_id=servidor_id,
            )
        except Exception as e:
            logger.warning("No se pudo registrar auditoría de eliminación de dispositivo %s: %s", device_id, e)

    return {"success": True, "message": f"Dispositivo {device_id} eliminado correctamente"}


@router.delete("/servidores/{server_id}")
async def eliminar_servidor(
    server_id: int,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    stmt = select(ServidorSecundario).where(ServidorSecundario.id == server_id)
    result = await db.execute(stmt)
    servidor = result.scalars().first()
    result.close()

    if not servidor:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    nombre_para_log = servidor.nombre
    ip_para_log = servidor.ip

    # Eliminar asignaciones de publicidad relacionadas (CASCADE ya lo hace, pero por seguridad)
    from app.models.asignacion import PublicidadAsignacion
    from sqlalchemy import delete as sql_delete

    stmt_asig = sql_delete(PublicidadAsignacion).where(
        PublicidadAsignacion.servidor_id == server_id
    )
    await db.execute(stmt_asig)

    # Desvincular dispositivos (SET NULL en servidor_id)
    stmt_disp = Dispositivo.__table__.update().where(
        Dispositivo.servidor_id == server_id
    ).values(servidor_id=None)
    await db.execute(stmt_disp)

    await db.delete(servidor)
    await db.commit()

    user_id = current_user.get("user_id") if current_user else None
    if user_id is not None:
        try:
            await registrar_accion(
                db,
                user_id,
                "ELIMINAR_SERVIDOR",
                f"Servidor '{nombre_para_log}' ({ip_para_log}) eliminado",
            )
        except Exception as e:
            logger.warning("No se pudo registrar auditoría de eliminación de servidor %s: %s", server_id, e)

    return {"success": True, "message": f"Servidor {server_id} eliminado correctamente"}


RESTART_TIMEOUT = 60  # segundos para esperar confirmación de reinicio


@router.get("/dispositivos/{device_id}/contenido")
async def get_device_content(
    device_id: str,
    db: AsyncSession = Depends(get_db_usuarios),
):
    """
    Obtiene el contenido que se está reproduciendo actualmente en el dispositivo.
    Consulta al backend-api del servidor donde está el dispositivo.
    """
    # 1. Buscar el dispositivo y su servidor
    stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result_disp = await db.execute(stmt_disp)
    dispositivo = result_disp.scalars().first()
    
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    if not dispositivo.servidor_id:
        return {
            "device_id": device_id,
            "contenido": None,
            "message": "Dispositivo no asociado a servidor"
        }
    
    # 2. Obtener la IP del servidor
    stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == dispositivo.servidor_id)
    result_srv = await db.execute(stmt_srv)
    servidor = result_srv.scalars().first()
    
    if not servidor:
        return {
            "device_id": device_id,
            "contenido": None,
            "message": "Servidor del dispositivo no encontrado"
        }
    
    servidor_ip = servidor.ip
    
    # 3. Llamar al backend-api para obtener el contenido
    api_url = f"http://{servidor_ip}:8000/api/device-playing/{device_id}"
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(api_url)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "device_id": device_id,
                    "contenido": None,
                    "message": "Error al obtener contenido del servidor"
                }
    except Exception as e:
        logger.error(f"Error al obtener contenido del dispositivo {device_id}: %s", e)
        return {
            "device_id": device_id,
            "contenido": None,
            "message": f"Error de conexión: {str(e)}"
        }


@router.post("/dispositivos/{device_id}/reiniciar")
async def reiniciar_dispositivo(
    device_id: str,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Reinicia un dispositivo específico.
    1. Busca el servidor donde está el dispositivo
    2. Llama al backend-api del servidor para enviar el comando
    3. Espera confirmación (timeout 60s)
    """
    # 1. Buscar el dispositivo y su servidor
    stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result_disp = await db.execute(stmt_disp)
    dispositivo = result_disp.scalars().first()
    
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    if not dispositivo.servidor_id:
        raise HTTPException(status_code=400, detail="El dispositivo no está asociado a ningún servidor")
    
    # 2. Obtener la IP del servidor
    stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == dispositivo.servidor_id)
    result_srv = await db.execute(stmt_srv)
    servidor = result_srv.scalars().first()
    
    if not servidor:
        raise HTTPException(status_code=404, detail="Servidor del dispositivo no encontrado")
    
    servidor_ip = servidor.ip
    
    logger.info(f"[REINICIAR] Intentando reiniciar dispositivo {device_id} en servidor {servidor_ip}")
    
    # 3. Llamar al backend-api del servidor
    api_url = f"http://{servidor_ip}:8000/api/comandos/{device_id}"
    logger.info(f"[REINICIAR] Llamando a: {api_url}")
    
    try:
        async with httpx.AsyncClient(timeout=RESTART_TIMEOUT) as client:
            logger.info(f"[REINICIAR] Enviando comando REINICIAR...")
            response = await client.post(
                api_url,
                json={"comando": "REINICIAR"},
            )
            logger.info(f"[REINICIAR] Respuesta recibida: status={response.status_code}")
            result = response.json()
            logger.info(f"[REINICIAR] Resultado: {result}")
            
            # 4. Registrar en auditoría
            user_id = current_user.get("user_id") if current_user else None
            actor_name = current_user.get("nombre_usuario") or current_user.get("usuario") or "Sistema"
            
            if result.get("success"):
                await registrar_accion(
                    db,
                    user_id,
                    "REINICIAR_DISPOSITIVO",
                    f"Dispositivo {device_id} reiniciado exitosamente por {actor_name}",
                    dispositivo_id=device_id,
                    servidor_id=servidor.id,
                )
            else:
                await registrar_accion(
                    db,
                    user_id,
                    "REINICIAR_DISPOSITIVO_FALLO",
                    f"Error al reiniciar {device_id}: {result.get('message', 'Error desconocido')}",
                    dispositivo_id=device_id,
                    servidor_id=servidor.id,
                )
            
            return result
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Timeout esperando confirmación del dispositivo ({RESTART_TIMEOUT}s)")
    except Exception as e:
        logger.error(f"Error al reiniciar dispositivo {device_id}: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al comunicarse con el servidor: {str(e)}")


class ProgramarReinicioBody(BaseModel):
    device_ids: list[str] = []  # vacío = todos los dispositivos
    hour: str  # formato "06:35"
    recurring: bool = True


@router.post("/dispositivos/programar-reinicio")
async def programar_reinicio_masivo(
    body: ProgramarReinicioBody,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Programa reinicio masivo para uno o todos los dispositivos.
    
    Lógica:
    - Si device_ids vacío: obtener todos los dispositivos de BD
    - Calcular scheduled_at basado en hour + fecha actual/mañana
    - Si recurring=True: configurar para ejecutarse diariamente
    """
    from datetime import datetime, timedelta, timezone
    
    # 1. Obtener lista de dispositivos
    # Si device_ids tiene elementos específicos, usarlos; si está vacía, obtener todos de BD
    dispositivos_ids = body.device_ids if body.device_ids and len(body.device_ids) > 0 else []
    
    if not dispositivos_ids:
        # Obtener todos los dispositivos de la base de datos
        stmt = select(Dispositivo.codigo_kiosko)
        result = await db.execute(stmt)
        dispositivos_ids = [row[0] for row in result.fetchall()]
    
    if not dispositivos_ids:
        raise HTTPException(status_code=400, detail="No hay dispositivos disponibles")
    
    logger.info(f"[PROGRAMAR_REINICIO] Programando para {len(dispositivos_ids)} dispositivos, hour={body.hour}, recurring={body.recurring}")
    
    # Validar formato de hora
    hour_parts = body.hour.split(':')
    if len(hour_parts) != 2:
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Use HH:MM")
    
    # 3. Enviar comando a cada dispositivo (el dispositivo calcular la próxima occurrence)
    resultados = {
        "total": len(dispositivos_ids),
        "enviados": 0,
        "fallidos": 0,
        "details": []
    }
    
    for device_id in dispositivos_ids:
        try:
            # Buscar servidor del dispositivo
            stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
            result_disp = await db.execute(stmt_disp)
            dispositivo = result_disp.scalars().first()
            
            logger.info(f"[PROGRAMAR_REINICIO] Procesando {device_id}, hora_reinicio_actual={dispositivo.hora_reinicio if dispositivo else 'None'}")
            
            if not dispositivo or not dispositivo.servidor_id:
                resultados["fallidos"] += 1
                resultados["details"].append({"device_id": device_id, "status": "error", "message": "Dispositivo sin servidor"})
                continue
            
            stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == dispositivo.servidor_id)
            result_srv = await db.execute(stmt_srv)
            servidor = result_srv.scalars().first()
            
            if not servidor:
                resultados["fallidos"] += 1
                resultados["details"].append({"device_id": device_id, "status": "error", "message": "Servidor no encontrado"})
                continue
            
            servidor_ip = servidor.ip
            
            # Llamar al backend-api del servidor
            api_url = f"http://{servidor_ip}:8000/api/comandos/{device_id}"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    api_url,
                    json={
                        "comando": "REINICIAR",
                        "hour": body.hour,
                        "recurring": body.recurring
                    }
                )
                
                if response.status_code == 200:
                    resultados["enviados"] += 1
                    resultados["details"].append({"device_id": device_id, "status": "enviado", "hour": body.hour, "recurring": body.recurring})
                    
                    # Guardar hora de reinicio en la BD
                    dispositivo.hora_reinicio = body.hour
                    dispositivo.reinicio_recurrente = body.recurring
                    await db.flush()
                    await db.refresh(dispositivo)
                    await db.commit()
                    
                    logger.info(f"[PROGRAMAR_REINICIO] Guardado en BD: {device_id} hora={body.hour} recurrente={body.recurring}")
                else:
                    resultados["fallidos"] += 1
                    resultados["details"].append({"device_id": device_id, "status": "error", "message": f"HTTP {response.status_code}"})
                    
        except Exception as e:
            logger.error(f"[PROGRAMAR_REINICIO] Error con {device_id}: {e}")
            resultados["fallidos"] += 1
            resultados["details"].append({"device_id": device_id, "status": "error", "message": str(e)})
    
    # 4. Registrar en auditoría
    user_id = current_user.get("user_id") if current_user else None
    actor_name = current_user.get("nombre_usuario") or current_user.get("usuario") or "Sistema"
    
    await registrar_accion(
        db,
        user_id,
        "PROGRAMAR_REINICIO_MASIVO",
        f"Reinicio programado por {actor_name}: {len(dispositivos_ids)} dispositivos, hour={body.hour}, recurring={body.recurring}",
    )
    
    return resultados