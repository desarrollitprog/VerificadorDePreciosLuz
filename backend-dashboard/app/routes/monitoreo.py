
"""
Rutas de monitoreo: heartbeat de servidores secundarios y estado.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import APIRouter, Depends,Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios, AsyncSessionLocalUsuarios
from app.dependencies import get_current_cliente, validar_api_key, get_current_admin
from app.models.servidor_secundario import ServidorSecundario
from app.services.notificacion_service import registrar_accion
import asyncio
import uuid
import httpx
router = APIRouter(tags=["monitoreo"])


class HeartbeatBody(BaseModel):
    nombre_servidor: str
    ip: str
    almacenamiento_total: int
    almacenamiento_usado: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
        return dispositivos
    except Exception:
        return []


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
    stmt = select(ServidorSecundario).where(ServidorSecundario.nombre == body.nombre_servidor)
    result = await db.execute(stmt)
    servidor = result.scalars().first()

    if servidor:
        servidor.ip = body.ip
        servidor.almacenamiento_total = body.almacenamiento_total
        servidor.almacenamiento_usado = body.almacenamiento_usado
        servidor.ultimo_heartbeat = now
    else:
        servidor = ServidorSecundario(
            nombre=body.nombre_servidor,
            ip=body.ip,
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

            async def send_force_sync(ip: str) -> dict[str, Any]:
                url = f"http://{ip}:8000/api/fuerza-sync"
                try:
                    async with httpx.AsyncClient(timeout=FORCE_SYNC_TIMEOUT_SECONDS) as client:
                        resp = await client.post(url)
                        payload = {}
                        try:
                            payload = resp.json()
                        except Exception:
                            payload = {}

                        ok = resp.status_code == 200 and bool(payload.get("success", True))
                        return {
                            "ok": ok,
                            "status_code": resp.status_code,
                            "backend_result": payload,
                            "reason": payload.get("message") if isinstance(payload, dict) else None,
                        }
                except Exception as e:
                    return {
                        "ok": False,
                        "status_code": None,
                        "backend_result": {},
                        "reason": str(e),
                    }

            results = []
            for server in online_servers:
                result_item = await send_force_sync(server.ip)
                results.append(result_item)

            success_count = sum(1 for r in results if r.get("ok") is True)
            failed_count = len(online_servers) - success_count

            details = []
            for i, server in enumerate(online_servers):
                result_item = results[i]
                backend_result = result_item.get("backend_result") or {}
                details.append(
                    {
                        "ip": server.ip,
                        "nombre": server.nombre,
                        "ok": result_item.get("ok") is True,
                        "status_code": result_item.get("status_code"),
                        "reason": result_item.get("reason"),
                        "sync_total": backend_result.get("total"),
                        "sync_sent": backend_result.get("sent"),
                        "sync_confirmed": backend_result.get("confirmed"),
                        "sync_failed": backend_result.get("failed"),
                        "sync_details": backend_result.get("details", []),
                    }
                )

            failed_servers = [d for d in details if not d["ok"]]
            resumen_fallos = ", ".join(
                f"{d['nombre']}({d['reason'] or 'sin motivo'})" for d in failed_servers[:5]
            )

            if user_id is not None:
                await registrar_accion(
                    db,
                    user_id,
                    "SINCRONIZACION_FORZADA",
                    (
                        f"Sincronización forzada ejecutada por usuario {username}. "
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

    lista = []
    for s in servidores:
        online = s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral
        total = s.almacenamiento_total or 0
        usado = s.almacenamiento_usado or 0
        porcentaje_uso = (usado / total * 100) if total > 0 else 0.0

        dispositivos = await _obtener_dispositivos_de_servidor(s.ip) if online else []
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

    return {"success": True, "servidores": lista}

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
    request: Request = None,
):
    """
    Inicia la sincronización forzada en background y retorna un job_id para polling.
    """
    job_id = str(uuid.uuid4())
    await _set_job_state(
        job_id,
        status="QUEUED",
        success=None,
        created_at=_utcnow().isoformat(),
        requested_by=current_user.get("nombre_usuario"),
    )

    asyncio.create_task(
        _execute_force_sync_job(
            job_id=job_id,
            user_id=current_user.get("user_id"),
            username=current_user.get("nombre_usuario"),
        )
    )

    return {
        "success": True,
        "message": "Sincronización en ejecución",
        "job_id": job_id,
        "status": "QUEUED",
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