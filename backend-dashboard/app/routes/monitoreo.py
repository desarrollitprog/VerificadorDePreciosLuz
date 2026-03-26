
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
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


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
                    )
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
                print(f"[DEBUG] Dispositivo_ids especificados sin servidores. Servers automáticos: {servidor_ids_automatico}")
                online_servers = [s for s in online_servers if s.id in servidor_ids_automatico]
                servidor_ids_a_buscar = servidor_ids_automatico
            elif servidor_ids:
                online_servers = [s for s in online_servers if s.id in servidor_ids]
                servidor_ids_a_buscar = servidor_ids

            dispositivos_por_servidor = await _get_dispositivos_por_servidor(
                db, servidor_ids_a_buscar, dispositivo_ids
            )
            print(f"[DEBUG] servidores_ids: {servidor_ids}, dispositivo_ids: {dispositivo_ids}, online_servers: {[s.id for s in online_servers]}, disp_por_srv: {dispositivos_por_servidor}")

            async def send_selective_sync(ip: str, dispositivo_ids_list: List[str] = None, on_progress: Any = None) -> dict[str, Any]:
                url = f"http://{ip}:8000/api/fuerza-sync"
                try:
                    params = {"async_mode": "true"}
                    if dispositivo_ids_list:
                        print(f"[DEBUG] Enviando dispositivo_ids al servidor {ip}: {dispositivo_ids_list}")
                        # Enviar como string separado por comas
                        # IMPORTANTE: El backend-api espera "dispositivo_ids", no "device_ids"
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
                await registrar_accion(
                    db,
                    user_id,
                    "SINCRONIZACION_SELECTIVA",
                    (
                        f"Sincronización selectiva ejecutada por usuario {actor_name}. "
                        f"Servidores: {len(online_servers)}, éxito: {success_count}, fallo: {failed_count}. "
                        f"Dispositivos: {len(dispositivo_ids) if dispositivo_ids else 'todos'}"
                    )
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
    logger.info("status-detalle: solicitud recibida")
    now = _utcnow()
    umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

    stmt = select(ServidorSecundario).order_by(ServidorSecundario.nombre)
    result = await db.execute(stmt)
    servidores = result.scalars().all()

    dispositivos_result = await db.execute(select(Dispositivo))
    dispositivos_db = dispositivos_result.scalars().all()
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
                        await registrar_accion(
                            db,
                            None,
                            "CONEXION_DISPOSITIVO",
                            f"Dispositivo '{dispositivo.nombre_amigable or codigo}' ({codigo}) conectado al servidor '{s.nombre}' ({s.ip})"
                        )
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
                        await registrar_accion(
                            db,
                            None,
                            "CONEXION_DISPOSITIVO",
                            f"Dispositivo '{dispositivo.nombre_amigable or codigo}' ({codigo}) conectado al servidor '{s.nombre}' ({s.ip})"
                        )
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
                            await registrar_accion(
                                db,
                                None,
                                "DESCONEXION_DISPOSITIVO",
                                f"Dispositivo '{dispositivo.nombre_amigable or codigo}' ({codigo}) desconectado del servidor '{s.nombre}' ({s.ip}). Duración: {duracion} segundos"
                            )
                    
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
                            await registrar_accion(
                                db,
                                None,
                                "DESCONEXION_DISPOSITIVO",
                                f"Dispositivo '{dispositivo.nombre_amigable or dispositivo.codigo_kiosko}' ({dispositivo.codigo_kiosko}) desconectado del servidor '{s.nombre}' ({s.ip}). Duración: {duracion} segundos"
                            )
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
                            await registrar_accion(
                                db,
                                None,
                                "DESCONEXION_DISPOSITIVO",
                                f"Dispositivo '{dispositivo.nombre_amigable or dispositivo.codigo_kiosko}' ({dispositivo.codigo_kiosko}) desconectado del servidor '{s.nombre}' ({s.ip}). Duración: {duracion} segundos"
                            )
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