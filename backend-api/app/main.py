from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
import asyncio
import logging
logging.basicConfig(level=logging.INFO, force=True)
import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect 
from fastapi.staticfiles import StaticFiles
import os
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv
from sqlalchemy import and_, or_, select, cast, Date, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Awaitable, Callable, List, Optional
import uuid
from pydantic import BaseModel
from redis.asyncio import Redis
from . import database, models, schemas
from .routes import consultas, publicidad
from .services import DeviceCommandBus, DeviceStateStore
from .services.scheduler_notifications import (
    save_pending_notification,
    get_pending_notification,
    remove_pending_notification,
)
from .database import get_db_publicidad
from .models.publicidad import Publicidad


def get_venezuela_now():
    return datetime.now(timezone(timedelta(hours=-4)))

# Cargar variables de entorno desde .env
load_dotenv()

app = FastAPI(title="Verificador de Precios Luz - Backend")
logger = logging.getLogger("uvicorn.error")


def normalizar_codigo_barras(codigo: str) -> list[str]:
    """
    Normaliza el código de barras/SKU para búsqueda.
    Agrega ceros al inicio hasta completar 13 dígitos.
    """
    codigo_limpio = codigo.strip()
    variantes = [codigo_limpio]
    
    if codigo_limpio.isdigit() and len(codigo_limpio) < 13:
        ceros_faltantes = '0' * (13 - len(codigo_limpio))
        variantes.append(ceros_faltantes + codigo_limpio)
    
    return variantes


# Comprimir respuestas grandes para reducir tiempo de descarga
app.add_middleware(GZipMiddleware, minimum_size=1024)


# Servir archivos estáticos (banners)
static_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")



device_state_store: DeviceStateStore | None = None
device_command_bus: DeviceCommandBus | None = None
device_bus_listener_task: asyncio.Task | None = None
reproducciones_local_task: asyncio.Task | None = None
reproducciones_sync_task: asyncio.Task | None = None
reproducciones_redis: redis.asyncio.Redis | None = None
command_acker: Any = None
pending_queue: Any = None
banner_batch_manager: Any = None

class PlaybackProgressRequest(BaseModel):
    reproduccion_id: str
    dispositivo_id: str
    banner_id: int
    titulo: str | None = None
    tipo_evento: str
    duracion_total_seg: float | None = None
    segundos_reproducidos: float | None = None
    porcentaje_completado: float | None = None
    cuartil_50: bool | None = None
    cuartil_75: bool | None = None
    cuartil_100: bool | None = None
    completo: bool | None = None
    motivo_fin: str | None = None


# Endpoint para consultar el estado de los dispositivos
@app.get("/devices/status")
async def get_devices_status():
    if device_state_store is None:
        raise HTTPException(status_code=503, detail="Estado de dispositivos no inicializado")
    status = await device_state_store.get_all_status()
    return status


@app.delete("/devices/{device_id}")
async def unregister_device_endpoint(device_id: str):
    """
    Desregistra un dispositivo del servidor secundario.
    El dashboard lo llama cuando se elimina un dispositivo de la BD.
    """
    from app.services.device_registry import unregister_device
    
    try:
        await unregister_device(device_id)
        if device_state_store is not None:
            await device_state_store.remove_device(device_id)
        logger.info(f"[UNREGISTER] Dispositivo {device_id} desvinculado del servidor")
        return {"success": True, "message": f"Dispositivo {device_id} desvinculado correctamente"}
    except Exception as e:
        logger.error(f"[UNREGISTER] Error desvinculando dispositivo {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ping")
async def ping(device_id: str | None = None):
    if device_id and device_state_store is not None:
        await device_state_store.upsert_heartbeat(device_id=device_id)
    return {"status": "Conexion Exitosa"}


# Endpoint de debug para recibir logs del BCV desde la app Android
@app.post("/api/debug-bcv")
async def debug_bcv(
    log_message: str = Query(...),
    device_id: str | None = Query(None),
    today: str | None = Query(None),
    cached_date: str | None = Query(None),
    cached_usd: str | None = Query(None),
    cached_eur: str | None = Query(None),
    api_usd: str | None = Query(None),
    api_eur: str | None = Query(None),
    cache_actualizado: str | None = Query(None)
):
    msg = f"[BCV-DEBUG] {log_message}"
    if device_id:
        msg = f"[BCV-DEBUG][{device_id}] {log_message}"
    
    if today:
        msg += f" | today={today}"
    if cached_date:
        msg += f" | cachedDate={cached_date}"
    if cached_usd:
        msg += f" | cachedUSD={cached_usd}"
    if cached_eur:
        msg += f" | cachedEUR={cached_eur}"
    if api_usd:
        msg += f" | apiUSD={api_usd}"
    if api_eur:
        msg += f" | apiEUR={api_eur}"
    if cache_actualizado:
        msg += f" | cacheActualizado={cache_actualizado}"
    
    logger.info(msg)
    return {"status": "logged"}


banner_check_task: asyncio.Task | None = None
banner_cleanup_task: asyncio.Task | None = None
notified_banners_start: set[int] = set()
notified_banners_end: set[int] = set()
scheduler_notifications: Any = None

BANNER_CHECK_INTERVAL = 20 * 60  # 20 minutos en segundos


async def _check_banners_starting():
    while True:
        try:
            # Verificar inmediatamente al iniciar y luego cada 20 minutos
            await _notify_banners_started()
            await _notify_banners_ended()
            await asyncio.sleep(BANNER_CHECK_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error en task de verificación de banners: %s", e)


async def _periodic_banner_cleanup():
    while True:
        try:
            from app.cleanup_service import cleanup_orphan_banners
            await cleanup_orphan_banners()
            await asyncio.sleep(86400)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error en limpieza de banners: {e}")
            await asyncio.sleep(86400)


async def _run_local_insert():
    """Wrapper que pasa las referencias al worker local."""
    from app.services.metricas_locales import insertar_reproducciones_locales
    global reproducciones_redis, device_state_store
    await insertar_reproducciones_locales(reproducciones_redis, device_state_store)


async def _notify_banners_started():
    try:
        async for db in get_db_publicidad():
            now = get_venezuela_now().replace(tzinfo=None)  # Usar naive para comparar con BD
            window_start = now - timedelta(minutes=20)
            window_end = now
            
            stmt = select(Publicidad).where(
                Publicidad.activo == True,
                Publicidad.fecha_inicio >= window_start,
                Publicidad.fecha_inicio <= window_end,
            )
            result = await db.execute(stmt)
            banners = result.scalars().all()
            
            for banner in banners:
                if banner.id in notified_banners_start:
                    continue
                
                notified_banners_start.add(banner.id)
                
                target_device_ids = None
                if banner.device_ids:
                    target_device_ids = [d.strip() for d in banner.device_ids.split(",") if d.strip()]
                
                await _send_banner_notification(banner, target_device_ids, "BANNER_INICIADO")
            break
    except Exception as e:
        logger.error("Error notificando banners iniciados: %s", e)


async def _notify_banners_ended():
    try:
        async for db in get_db_publicidad():
            now = get_venezuela_now().replace(tzinfo=None)  # Usar naive para comparar con BD
            window_start = now - timedelta(minutes=20)
            window_end = now
            
            stmt = select(Publicidad).where(
                Publicidad.activo == True,
                Publicidad.fecha_fin >= window_start,
                Publicidad.fecha_fin <= window_end,
            )
            result = await db.execute(stmt)
            banners = result.scalars().all()
            
            for banner in banners:
                if banner.id in notified_banners_end:
                    continue
                
                notified_banners_end.add(banner.id)
                
                target_device_ids = None
                if banner.device_ids:
                    target_device_ids = [d.strip() for d in banner.device_ids.split(",") if d.strip()]
                
                await _send_banner_notification(banner, target_device_ids, "BANNER_FINALIZADO")
            break
    except Exception as e:
        logger.error("Error notificando banners finalizados: %s", e)


async def _send_banner_notification(banner: Publicidad, target_device_ids: List[str] | None, command: str):
    banner_info = {
        "command": command,
        "banner_id": banner.id,
        "titulo": banner.titulo,
        "url": banner.url,
        "tipo": banner.tipo,
        "fecha_inicio": banner.fecha_inicio.isoformat() if banner.fecha_inicio else None,
        "fecha_fin": banner.fecha_fin.isoformat() if banner.fecha_fin else None,
    }
    
    if target_device_ids:
        for device_id in target_device_ids:
            await tablet_ws_manager.send_to_device(device_id, banner_info)
            logger.info(f"Enviado {command} a {device_id}: {banner.titulo}")
    else:
        connections_count = len(tablet_ws_manager.active_connections)
        logger.info(f"Broadcast {command}: {banner.titulo} - Conexiones activas: {connections_count}")
        await tablet_ws_manager.broadcast(banner_info)


async def _send_to_device_robust(device_id: str, banner_info: dict) -> bool:
    command = banner_info.get("command", "")

    # Si el dispositivo está conectado a este worker, enviar directo vía WS (evitar bus)
    ws = tablet_ws_manager.device_map.get(device_id)
    if ws:
        try:
            await ws.send_json(banner_info)
            logger.info(f"[BANNER_ROBUST] Enviado {command} via WS a {device_id}")
            return True
        except Exception as e:
            logger.warning(f"[BANNER_ROBUST] WS falló para {device_id}: {e}")

    # Dispositivo NO conectado aquí → publicar al bus para otros workers
    if device_command_bus is not None:
        try:
            await device_command_bus.publish_command(
                device_id=device_id,
                command=command,
                payload=banner_info,
            )
            logger.info(f"[BANNER_ROBUST] Enviado {command} via Redis a {device_id}")
            return True
        except Exception as e:
            logger.warning(f"[BANNER_ROBUST] Redis falló para {device_id}: {e}")

    # Fallback 1: key legacy pending:banner con TTL 24h
    try:
        key = f"device:pending:banner:{device_id}"
        import json
        await device_state_store.redis.set(key, json.dumps(banner_info), ex=86400)
        logger.info(f"[BANNER_ROBUST] Guardado en pending:banner para {device_id} (24h TTL)")
    except Exception as e:
        logger.warning(f"[BANNER_ROBUST] pending:banner falló para {device_id}: {e}")

    # Fallback 2: cola persistente Redis (se entrega en reconexión)
    if command in ("BANNER_INICIADO", "BANNER_FINALIZADO") and pending_queue is not None:
        try:
            await pending_queue.enqueue(device_id, banner_info)
            logger.info(f"[BANNER_ROBUST] Encolado en pending_queue para {device_id}")
        except Exception as e:
            logger.warning(f"[BANNER_ROBUST] pending_queue falló para {device_id}: {e}")

    return False


async def send_banner_notification_robust(banner: Publicidad, target_device_ids: List[str] | None, command: str):
    banner_info = {
        "command": command,
        "banner_id": banner.id,
        "titulo": banner.titulo,
        "url": banner.url,
        "tipo": banner.tipo,
        "fecha_inicio": banner.fecha_inicio.isoformat() if banner.fecha_inicio else None,
        "fecha_fin": banner.fecha_fin.isoformat() if banner.fecha_fin else None,
    }

    if target_device_ids:
        for device_id in target_device_ids:
            await _send_to_device_robust(device_id, banner_info)
    else:
        all_device_ids: set[str] = set()
        if device_state_store is not None:
            try:
                status_map = await device_state_store.get_all_status()
                all_device_ids = set(status_map.keys())
            except Exception as e:
                logger.warning(f"[BANNER_ROBUST] Error obteniendo estado de Redis: {e}")

        if not all_device_ids:
            all_device_ids = set(d for d, _ in tablet_ws_manager.get_connected_targets() if d)

        online_count = sum(1 for d in all_device_ids if d in tablet_ws_manager.device_map)
        logger.info(f"[BANNER_ROBUST] {command} para banner {banner.id}: {len(all_device_ids)} disp. ({online_count} online)")

        for device_id in all_device_ids:
            await _send_to_device_robust(device_id, banner_info)


async def _execute_banner_notification(banner, target_device_ids, command: str):
    """Entrega un banner usando batch (BANNER_INICIADO) o directo (BANNER_FINALIZADO).
    
    Mantiene la lógica de envío centralizada para que schedule_banner_notification
    y la recuperación post-reinicio compartan el mismo código.
    """
    if command == "BANNER_INICIADO" and banner_batch_manager is not None:
        try:
            banner_info = {
                "banner_id": banner.id,
                "titulo": banner.titulo,
                "url": banner.url,
                "tipo": banner.tipo,
                "device_ids": target_device_ids,
                "fecha_inicio": banner.fecha_inicio.isoformat() if banner.fecha_inicio else None,
                "fecha_fin": banner.fecha_fin.isoformat() if banner.fecha_fin else None,
            }
            is_coordinator = await banner_batch_manager.accumulate(banner_info)
            if is_coordinator:
                asyncio.create_task(_delayed_batch_flush())
            logger.info(f"Notificación de inicio acumulada para banner {banner.id}")
        except Exception as e:
            logger.error(f"Error acumulando banner {banner.id} en lote, enviando directo: {e}")
            await send_banner_notification_robust(banner, target_device_ids, command)
    else:
        await send_banner_notification_robust(banner, target_device_ids, command)


async def schedule_banner_notification(
    banner_id: int,
    device_ids: str | None,
    titulo: str | None,
    url: str,
    tipo: str,
    fecha_inicio: datetime,
    fecha_fin: datetime | None,
):
    """Programa notificaciones exactas para inicio y fin de banner."""
    now = get_venezuela_now()
    
    if fecha_inicio:
        if fecha_inicio.tzinfo is None:
            fecha_inicio_aware = fecha_inicio.replace(tzinfo=timezone(timedelta(hours=-4)))
        else:
            fecha_inicio_aware = fecha_inicio
        
        delay_inicio = (fecha_inicio_aware - now).total_seconds()
        if delay_inicio > 0:
            logger.info(f"Programando notificación de inicio para banner {banner_id} en {delay_inicio} segundos")
            
            await save_pending_notification(
                banner_id=banner_id,
                device_ids=device_ids,
                titulo=titulo,
                url=url,
                tipo=tipo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                command="BANNER_INICIADO",
                scheduled_at=fecha_inicio_aware,
            )
            
            await asyncio.sleep(delay_inicio)
            
            if banner_id in notified_banners_start:
                logger.info(f"Banner {banner_id} ya notificado de inicio, saltando")
                await remove_pending_notification(banner_id, "BANNER_INICIADO")
            else:
                pending = await get_pending_notification(banner_id, "BANNER_INICIADO")
                async for db in get_db_publicidad():
                    result = await db.execute(select(Publicidad).where(Publicidad.id == banner_id))
                    banner = result.scalars().first()
                    if banner and banner.activo:
                        target_device_ids = None
                        if banner.device_ids:
                            target_device_ids = [d.strip() for d in banner.device_ids.split(",") if d.strip()]
                        await _execute_banner_notification(banner, target_device_ids, "BANNER_INICIADO")
                        notified_banners_start.add(banner_id)
                    await remove_pending_notification(banner_id, "BANNER_INICIADO")
                    break
    
    if fecha_fin:
        if fecha_fin.tzinfo is None:
            fecha_fin_aware = fecha_fin.replace(tzinfo=timezone(timedelta(hours=-4)))
        else:
            fecha_fin_aware = fecha_fin
        
        delay_fin = (fecha_fin_aware - now).total_seconds()
        if delay_fin > 0:
            logger.info(f"Programando notificación de fin para banner {banner_id} en {delay_fin} segundos")
            
            await save_pending_notification(
                banner_id=banner_id,
                device_ids=device_ids,
                titulo=titulo,
                url=url,
                tipo=tipo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                command="BANNER_FINALIZADO",
                scheduled_at=fecha_fin_aware,
            )
            
            await asyncio.sleep(delay_fin)
            
            if banner_id in notified_banners_end:
                logger.info(f"Banner {banner_id} ya notificado de fin, saltando")
                await remove_pending_notification(banner_id, "BANNER_FINALIZADO")
            else:
                await get_pending_notification(banner_id, "BANNER_FINALIZADO")
                async for db in get_db_publicidad():
                    result = await db.execute(select(Publicidad).where(Publicidad.id == banner_id))
                    banner = result.scalars().first()
                    if banner:
                        target_device_ids = None
                        if banner.device_ids:
                            target_device_ids = [d.strip() for d in banner.device_ids.split(",") if d.strip()]
                        await _execute_banner_notification(banner, target_device_ids, "BANNER_FINALIZADO")
                        notified_banners_end.add(banner_id)
                        logger.info(f"Notificación de fin enviada para banner {banner_id}")
                    await remove_pending_notification(banner_id, "BANNER_FINALIZADO")
                    break


async def _delayed_batch_flush():
    """Espera la ventana de coalescencia y luego flushea el lote de banners."""
    global banner_batch_manager
    try:
        await asyncio.sleep(5)

        if banner_batch_manager is None:
            return

        async def _send(msg: dict):
            broadcast_id = str(uuid.uuid4())
            msg["_broadcast_id"] = broadcast_id
            await tablet_ws_manager.broadcast(msg)
            if device_command_bus is not None:
                try:
                    await device_command_bus.publish_command(
                        device_id="*",
                        command="BANNER_LIST",
                        payload=msg,
                    )
                except Exception as e:
                    logger.warning("[BANNER_BATCH] Redis bus falló: %s", e)

        banners = await banner_batch_manager.flush(_send)
        if not banners:
            return

        logger.info("[BANNER_BATCH] Lote enviado con %d banners", len(banners))

        # Encolar BANNER_LIST a dispositivos offline
        if pending_queue is not None and device_state_store is not None:
            try:
                status_map = await device_state_store.get_all_status()
                offline_ids = set(status_map.keys()) - set(tablet_ws_manager.device_map.keys())
                if not offline_ids:
                    return

                # Capa 3: Excluir dispositivos vivos en otro worker (el bus ya les entregó)
                from app.services import device_registry as dr
                if dr.device_registry is not None:
                    try:
                        for did in list(offline_ids):
                            if await dr.device_registry.is_device_registered(did):
                                offline_ids.discard(did)
                    except Exception as e:
                        logger.warning(f"[WS] Registry check falló: {e}")

                if not offline_ids:
                    return

                target: set[str] = set()
                is_broadcast = any(b.get("device_ids") is None for b in banners)
                if is_broadcast:
                    target = offline_ids
                else:
                    for b in banners:
                        dids = b.get("device_ids")
                        if dids:
                            target.update(d.strip() for d in dids if d.strip())
                    target &= offline_ids

                if not target:
                    return

                msg = {"command": "BANNER_LIST", "banners": banners}
                for device_id in target:
                    await pending_queue.enqueue(device_id, msg)
                logger.info("[BANNER_BATCH] BANNER_LIST encolado para %d disp. offline", len(target))

            except Exception as e:
                logger.error("[BANNER_BATCH] Error encolando para offline: %s", e)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("[BANNER_BATCH] Error en flush: %s", e)


async def _recover_pending_scheduler_notifications():
    """Re-programa notificaciones pendientes que no sobrevivieron al reinicio."""
    try:
        from app.services.scheduler_notifications import get_all_pending_notifications
        pending = await get_all_pending_notifications()
    except Exception as e:
        logger.error("[RECOVERY] Error obteniendo notificaciones: %s", e)
        return

    if not pending:
        logger.info("[RECOVERY] No hay notificaciones pendientes por recuperar")
        return

    now = get_venezuela_now()
    recovered = 0
    expired = 0

    for notif in pending:
        banner_id = notif["banner_id"]
        command = notif["command"]
        scheduled_at_str = notif.get("scheduled_at")
        if not scheduled_at_str:
            continue

        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone(timedelta(hours=-4)))
        except Exception:
            continue

        delay = (scheduled_at - now).total_seconds()

        if delay > 0:
            logger.info(f"[RECOVERY] Reprogramando {command} banner {banner_id} en {delay:.1f}s")
            asyncio.create_task(schedule_banner_notification(
                banner_id=banner_id,
                device_ids=notif.get("device_ids"),
                titulo=notif.get("titulo"),
                url=notif.get("url"),
                tipo=notif.get("tipo"),
                fecha_inicio=datetime.fromisoformat(notif["fecha_inicio"]) if notif.get("fecha_inicio") else None,
                fecha_fin=datetime.fromisoformat(notif["fecha_fin"]) if notif.get("fecha_fin") else None,
            ))
            recovered += 1

        elif delay > -300:
            logger.info(f"[RECOVERY] Ejecutando {command} banner {banner_id} inmediato (retraso {-delay:.1f}s)")
            async for db in get_db_publicidad():
                result = await db.execute(select(Publicidad).where(Publicidad.id == banner_id))
                banner = result.scalars().first()
                if banner and banner.activo:
                    target_device_ids = None
                    raw_ids = notif.get("device_ids")
                    if raw_ids:
                        target_device_ids = [d.strip() for d in raw_ids.split(",") if d.strip()]
                    await _execute_banner_notification(banner, target_device_ids, command)
                    if command == "BANNER_INICIADO":
                        notified_banners_start.add(banner_id)
                    elif command == "BANNER_FINALIZADO":
                        notified_banners_end.add(banner_id)
                await remove_pending_notification(banner_id, command)
                break
            recovered += 1

        else:
            logger.info(f"[RECOVERY] {command} banner {banner_id} vencido ({-delay:.1f}s), limpiando")
            await remove_pending_notification(banner_id, command)
            expired += 1

    logger.info(f"[RECOVERY] Recuperadas: {recovered}, expiradas: {expired}")


@app.on_event("startup")
async def start_device_monitor():
    global device_state_store, device_command_bus, device_bus_listener_task, banner_check_task, pending_queue, banner_batch_manager
    try:
        device_state_store = await DeviceStateStore.create()
        logger.info("DeviceStateStore inicializado con Redis")
    except Exception as e:
        logger.error("No se pudo inicializar DeviceStateStore: %s", e)

    # Inicializar DeviceRegistry (para compartir dispositivos entre workers)
    try:
        from app.services.device_registry import device_registry, DeviceRegistry
        global_device_registry = await DeviceRegistry.create(ttl_seconds=300)
        # Reemplazar el módulo global
        import app.services.device_registry
        app.services.device_registry.device_registry = global_device_registry
        logger.info("DeviceRegistry inicializado con Redis")
    except Exception as e:
        logger.error("No se pudo inicializar DeviceRegistry: %s", e)

    try:
        device_command_bus = await DeviceCommandBus.create()
        device_bus_listener_task = asyncio.create_task(_start_device_bus_listener_with_retry())
        logger.info("DeviceCommandBus inicializado con Redis pub/sub + auto-retry")
    except Exception as e:
        logger.error("No se pudo inicializar DeviceCommandBus: %s", e)

    # Inicializar CommandAcker (para confirmaciones de comandos via Redis)
    try:
        from app.services.command_acker import CommandAcker
        global command_acker
        command_acker = await CommandAcker.create(ttl=90)
        logger.info("CommandAcker inicializado con Redis (TTL=90s)")
    except Exception as e:
        logger.warning("CommandAcker no disponible: %s", e)

    banner_check_task = asyncio.create_task(_check_banners_starting())
    logger.info("Banner check task iniciada")

    banner_cleanup_task = asyncio.create_task(_periodic_banner_cleanup())
    logger.info("Banner cleanup task iniciada")

    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        global reproducciones_redis, reproducciones_local_task, reproducciones_sync_task
        reproducciones_redis = Redis.from_url(redis_url, decode_responses=True)
        await reproducciones_redis.ping()
        reproducciones_local_task = asyncio.create_task(_run_local_insert())
        logger.info("[Reproducciones] Worker local de metricas iniciado")

        from app.services.sync_metrics import sincronizar_metricas
        servidor_id_env = os.getenv("SERVIDOR_ID")
        if servidor_id_env:
            reproducciones_sync_task = asyncio.create_task(
                sincronizar_metricas(int(servidor_id_env))
            )
            logger.info(f"[Reproducciones] Worker sync cada 5h iniciado (servidor_id={servidor_id_env})")
        else:
            logger.warning("[Reproducciones] SERVIDOR_ID no configurado, sync deshabilitado")
    except Exception as e:
        logger.warning(f"[Reproducciones] No se pudo inicializar buffer Redis: {e}")

    try:
        from app.services.scheduler_notifications import SchedulerNotifications
        import app.services.scheduler_notifications as sn_mod
        global scheduler_notifications
        scheduler_notifications = await SchedulerNotifications.create(ttl_seconds=86400)
        sn_mod.scheduler_notifications = scheduler_notifications
        logger.info("SchedulerNotifications inicializado con Redis (TTL=24h)")
    except Exception as e:
        logger.warning(f"SchedulerNotifications no disponible: {e}")

    # Inicializar PendingCommandQueue (cola persistente en Redis)
    try:
        from app.services.pending_queue import PendingCommandQueue
        global pending_queue
        pending_queue = await PendingCommandQueue.create()
        logger.info("PendingCommandQueue inicializado con Redis")
    except Exception as e:
        logger.error("No se pudo inicializar PendingCommandQueue: %s", e)

    # Inicializar BannerBatchManager (coalescencia de BANNER_INICIADO)
    try:
        from app.services.banner_batch import BannerBatchManager
        global banner_batch_manager
        banner_batch_manager = await BannerBatchManager.create()
        logger.info("BannerBatchManager inicializado con Redis (batch_window=5s)")
    except Exception as e:
        logger.warning(f"BannerBatchManager no disponible: {e}")

    # Recuperar notificaciones programadas que no sobrevivieron al reinicio
    try:
        await _recover_pending_scheduler_notifications()
    except Exception as e:
        logger.error(f"[RECOVERY] Error en _recover_pending_scheduler_notifications: {e}")

    # Recuperar banners acumulados en batch cuyo coordinator murió
    if banner_batch_manager is not None:
        try:
            stale_banners = await banner_batch_manager.recover_pending_batch()
            if stale_banners:
                msg = {"command": "BANNER_LIST", "banners": stale_banners}
                await tablet_ws_manager.broadcast(msg)
                if device_command_bus is not None:
                    await device_command_bus.publish_command(
                        device_id="*",
                        command="BANNER_LIST",
                        payload=msg,
                    )

                # Encolar BANNER_LIST a dispositivos offline
                if pending_queue is not None and device_state_store is not None:
                    try:
                        status_map = await device_state_store.get_all_status()
                        offline_ids = set(status_map.keys()) - set(tablet_ws_manager.device_map.keys())
                        if offline_ids:
                            for device_id in offline_ids:
                                await pending_queue.enqueue(device_id, msg)
                            logger.info(f"[RECOVERY] BANNER_LIST encolado para {len(offline_ids)} disp. offline")
                    except Exception as e:
                        logger.error(f"[RECOVERY] Error encolando batch recuperado: {e}")

                logger.info(f"[RECOVERY] Batch pendiente recuperado: {len(stale_banners)} banners")
        except Exception as e:
            logger.error(f"[RECOVERY] Error recuperando batch pendiente: {e}")


@app.on_event("shutdown")
async def shutdown_device_state_store():
    global device_state_store, device_command_bus, device_bus_listener_task, banner_check_task
    logger.info("[Shutdown] Iniciando cierre graceful...")
    
    # 1. Notificar a todos los dispositivos (graceful shutdown)
    try:
        await tablet_ws_manager.broadcast({
            "type": "SERVER_SHUTDOWN",
            "message": "Server restarting"
        })
        logger.info("[Shutdown] Broadcast de cierre enviado a dispositivos")
        await asyncio.sleep(2)  # Dar tiempo a que se envíen los mensajes
    except Exception as e:
        logger.warning(f"[Shutdown] Error en broadcast: {e}")
    
    # 2. Cancelar tarea de cleanup periódico
    if tablet_ws_manager._cleanup_task is not None:
        tablet_ws_manager._cleanup_task.cancel()
        tablet_ws_manager._cleanup_task = None
        logger.info("[Shutdown] Tarea de cleanup cancelada")
    
    # 3. Cerrar todas las conexiones WebSocket
    for ws in tablet_ws_manager.active_connections.copy():
        try:
            await ws.close(code=1001, reason="Server shutdown")
        except Exception:
            pass
    
    # 4. Limpiar tareas de ping
    for ws_id, task in list(tablet_ws_manager.ping_tasks.items()):
        task.cancel()
    tablet_ws_manager.ping_tasks.clear()
    
    logger.info("[Shutdown] WebSockets cerrados")
    
    if banner_check_task is not None:
        banner_check_task.cancel()
        banner_check_task = None

    global banner_cleanup_task
    if banner_cleanup_task is not None:
        banner_cleanup_task.cancel()
        banner_cleanup_task = None

    if device_bus_listener_task is not None:
        device_bus_listener_task.cancel()
        device_bus_listener_task = None

    if device_command_bus is not None:
        await device_command_bus.close()
        device_command_bus = None

    global reproducciones_local_task, reproducciones_sync_task
    if reproducciones_local_task is not None:
        reproducciones_local_task.cancel()
        reproducciones_local_task = None

    if reproducciones_sync_task is not None:
        reproducciones_sync_task.cancel()
        reproducciones_sync_task = None

    global reproducciones_redis
    if reproducciones_redis is not None:
        await reproducciones_redis.close()
        reproducciones_redis = None

    if device_state_store is not None:
        await device_state_store.close()
        device_state_store = None

    global pending_queue
    if pending_queue is not None:
        await pending_queue.close()
        pending_queue = None
    
    logger.info("[Shutdown] Cierre completo")


# Paso 1: Buscar producto y precio base (async)
async def buscar_producto_y_precio(db: AsyncSession, codigo_barras: str):
    stmt = (
        select(models.Producto, models.ProductoPrecio)
        .join(
            models.ProductoPrecio,
            models.Producto.IdProducto == models.ProductoPrecio.IdProducto,
        )
        .where(
            models.Producto.SKU == codigo_barras,
            models.ProductoPrecio.CostoBase > 0,
        )
    )
    result = await db.execute(stmt)
    return result.first()


# Paso 1b: Buscar coincidencias cercanas (async)
async def buscar_coincidencias_cercanas(db: AsyncSession, codigo_barras: str, limite: int = 5):
    """
    Busca productos con SKU similar al código escaneado.
    Usa múltiples estrategias de búsqueda:
    1. LIKE% - SKU que empieza con el código
    2. %LIKE% - SKU que contiene el código en cualquier parte
    """
    codigo = codigo_barras.strip()
    
    if len(codigo) < 3:
        return []
    
    stmt = (
        select(models.Producto, models.ProductoPrecio)
        .join(
            models.ProductoPrecio,
            models.Producto.IdProducto == models.ProductoPrecio.IdProducto,
        )
        .where(
            models.ProductoPrecio.CostoBase > 0,
            or_(
                models.Producto.SKU.like(f"{codigo}%"),
                models.Producto.SKU.like(f"%{codigo}%"),
            )
        )
        .order_by(
            func.len(models.Producto.SKU),
            models.Producto.SKU
        )
        .limit(limite)
    )
    
    result = await db.execute(stmt)
    return result.all()


# Paso 1c: Buscar en BarrasAsociadas - Fallback cuando no se encuentra por SKU directo
async def buscar_en_barras_asociadas(db: AsyncSession, codigo_barras: str):
    """
    Busca el código de barras en la tabla Transaccional.BarrasAsociadas.
    Si lo encuentra, retorna el IdProducto asociado para buscar el producto completo.
    """
    stmt = select(models.BarrasAsociadas).where(
        models.BarrasAsociadas.Barra == codigo_barras,
        models.BarrasAsociadas.IndActivo == 1,
    )
    result = await db.execute(stmt)
    barra_asociada = result.scalars().first()
    
    if not barra_asociada:
        return None
    
    stmt_producto = (
        select(models.Producto, models.ProductoPrecio)
        .join(
            models.ProductoPrecio,
            models.Producto.IdProducto == models.ProductoPrecio.IdProducto,
        )
        .where(
            models.Producto.IdProducto == barra_asociada.IdProducto,
            models.ProductoPrecio.CostoBase > 0,
        )
    )
    result_producto = await db.execute(stmt_producto)
    return result_producto.first()


# Paso 2: Buscar oferta asociada (async)
async def buscar_oferta(db: AsyncSession, id_producto: int):
    stmt = select(models.ProductoOferta).where(
        models.ProductoOferta.IdProducto == id_producto,
        models.ProductoOferta.IndActivo == 1,
    )
    result = await db.execute(stmt)
    return result.scalars().first()


# Paso 3: Buscar detalle de oferta vigente por empaque (async)
async def buscar_detalle_oferta_vigente(
    db: AsyncSession,
    precio: models.ProductoPrecio | None,
    now: datetime,
):
    if not precio or precio.IdEmpaque is None:
        return None

    today_start = datetime.combine(now.date(), datetime.min.time())

    stmt = (
        select(models.OfertasxProductosxSucursalesDetalles)
        .join(
            models.OfertasxProductosxSucursal,
            models.OfertasxProductosxSucursal.IdOfertaxProductoxSucursal
            == models.OfertasxProductosxSucursalesDetalles.IdOfertaxProductoxSucursal,
        )
        .join(
            models.OfertasxProductos,
            models.OfertasxProductos.IdOfertaxProducto
            == models.OfertasxProductosxSucursal.IdOfertaxProducto,
        )
        .where(
            models.OfertasxProductosxSucursalesDetalles.IdEmpaque == precio.IdEmpaque,
            or_(
                models.OfertasxProductosxSucursalesDetalles.IndActivo == 1,
                models.OfertasxProductosxSucursalesDetalles.IndActivo.is_(None),
            ),
            or_(
                models.OfertasxProductos.IndExpirado != 1,
                models.OfertasxProductos.IndExpirado.is_(None),
            ),
            or_(
                models.OfertasxProductos.FechaInicio.is_(None),
                models.OfertasxProductos.FechaInicio <= now,
            ),
            or_(
                models.OfertasxProductos.FechaFin.is_(None),
                and_(
                    cast(models.OfertasxProductos.FechaFin, Date) >= today_start.date(),
                    cast(models.OfertasxProductos.FechaFin, Date) >= now.date(),
                ),
            ),
        )
        .limit(1)
    )

    result = await db.execute(stmt)
    return result.scalars().first()


# Paso 4: Buscar tasa de impuesto (ERP)
async def buscar_tasa_impuesto(
    db: AsyncSession,
    db_erp: AsyncSession,
    id_producto: int,
    precio: models.ProductoPrecio | None,
):
    if not precio or precio.IndIVA not in (1, True):
        return None

    impuesto_stmt = select(models.ProductosXImpuestos).where(
        models.ProductosXImpuestos.IdProducto == id_producto,
        models.ProductosXImpuestos.IndActivo == 1,
    )
    impuesto_result = await db.execute(impuesto_stmt)
    impuesto = impuesto_result.scalars().first()
    if not impuesto:
        return None

    tasa_stmt = select(models.TasaImpuesto).where(
        models.TasaImpuesto.IdTasaImpuesto == impuesto.IdTasaImpuesto
    )
    tasa_result = await db_erp.execute(tasa_stmt)
    tasa = tasa_result.scalars().first()
    return tasa.Tasa if tasa else None


def armar_respuesta(
    producto: models.Producto,
    precio: models.ProductoPrecio | None,
    oferta: models.ProductoOferta | None,
    detalle_oferta: models.OfertasxProductosxSucursalesDetalles | None,
    tasa_impuesto,
):
    pvp_base = float(precio.PVPBase) if precio and precio.PVPBase is not None else None
    pvp_conversion = (
        float(precio.PVPConversion)
        if precio and precio.PVPConversion is not None
        else pvp_base
    )
    pvp_oferta = float(oferta.PvpOferta) if oferta and oferta.PvpOferta is not None else None
    pvp_base_oferta = (
        float(oferta.PvpBaseOferta)
        if oferta and oferta.PvpBaseOferta is not None
        else None
    )

    factor = 1.0
    if tasa_impuesto is not None:
        factor += float(tasa_impuesto) / 100.0

    if pvp_base is not None:
        pvp_base *= factor
    if pvp_conversion is not None:
        pvp_conversion *= factor
    if pvp_oferta is not None:
        pvp_oferta *= factor
    if pvp_base_oferta is not None:
        pvp_base_oferta *= factor

    oferta_valida = (
        oferta is not None
        and (pvp_oferta or 0) > 0
        and (pvp_base_oferta or 0) > 0
    )
    oferta_vigente = oferta_valida and detalle_oferta is not None

    return {
        "id_producto": producto.IdProducto,
        "sku": producto.SKU,
        "nombre": producto.Nombre,
        "pvp_base": None if oferta_vigente else pvp_base,
        "pvp_conversion": None if oferta_vigente else pvp_conversion,
        "pvp_oferta": pvp_oferta if oferta_vigente else None,
        "pvp_base_oferta": pvp_base_oferta if oferta_vigente else None,
        "id_empaque": int(precio.IdEmpaque) if precio and precio.IdEmpaque is not None else None,
    }

@app.get("/backup")
async def backup_data(
    section: str = "productos",
    offset: int = 0,
    limit: int = 2000,
    updated_since: Optional[str] = Query(None, description="ISO8601 timestamp para cambios incrementales"),
    db: AsyncSession = Depends(database.get_db),
    db_erp: AsyncSession = Depends(database.get_db_erp),
):
    updated_at = datetime.utcnow().isoformat() + "Z"

    limit = max(1, min(limit or 1000, 5000))
    offset = max(0, offset)

    allowed_sections = {
        "productos",
        "precios",
        "ofertas",
        "ofertas_vigencia",
        "ofertas_sucursal",
        "ofertas_detalles",
        "impuestos_producto",
        "tasas_impuesto",
        "barras_asociadas",
    }
    if section not in allowed_sections:
        raise HTTPException(status_code=400, detail="Sección de backup inválida")

    logger.info("/backup section=%s offset=%s limit=%s updated_since=%s", section, offset, limit, updated_since)

    productos: list[models.Producto] = []
    precios: list[models.ProductoPrecio] = []
    ofertas: list[models.ProductoOferta] = []
    ofertas_vigencia: list[models.OfertasxProductos] = []
    ofertas_sucursal: list[models.OfertasxProductosxSucursal] = []
    ofertas_detalles: list[models.OfertasxProductosxSucursalesDetalles] = []
    impuestos_producto: list[models.ProductosXImpuestos] = []
    tasas_impuesto: list[models.TasaImpuesto] = []
    barras_asociadas: list[models.BarrasAsociadas] = []

    # Soporte incremental solo para precios (ejemplo)
    if section == "productos":
        stmt = select(models.Producto).order_by(models.Producto.IdProducto)
        stmt = stmt.offset(offset).limit(limit)
        productos = (await db.execute(stmt)).scalars().all()
    elif section == "precios":
        stmt = select(models.ProductoPrecio).order_by(models.ProductoPrecio.IdProductosXEmpaqueXSucursal)
        if updated_since:
            try:
                dt = isoparse(updated_since)
                stmt = stmt.where(models.ProductoPrecio.FechaModifica > dt)
            except Exception:
                raise HTTPException(status_code=400, detail="updated_since inválido")
        stmt = stmt.offset(offset).limit(limit)
        precios = (await db.execute(stmt)).scalars().all()
    elif section == "ofertas":
        ofertas = (
            await db.execute(
                select(models.ProductoOferta)
                .order_by(models.ProductoOferta.IdProductoOfertaxSucursal)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
    elif section == "ofertas_vigencia":
        ofertas_vigencia = (
            await db.execute(
                select(models.OfertasxProductos)
                .order_by(models.OfertasxProductos.IdOfertaxProducto)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
    elif section == "ofertas_sucursal":
        ofertas_sucursal = (
            await db.execute(
                select(models.OfertasxProductosxSucursal)
                .order_by(models.OfertasxProductosxSucursal.IdOfertaxProductoxSucursal)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
    elif section == "ofertas_detalles":
        ofertas_detalles = (
            await db.execute(
                select(models.OfertasxProductosxSucursalesDetalles)
                .order_by(models.OfertasxProductosxSucursalesDetalles.IdOfertaxProductoxSucursalDetalle)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
    elif section == "impuestos_producto":
        impuestos_producto = (
            await db.execute(
                select(models.ProductosXImpuestos)
                .order_by(models.ProductosXImpuestos.IdProductoxImpuesto)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
    elif section == "tasas_impuesto":
        tasas_impuesto = (
            await db_erp.execute(
                select(models.TasaImpuesto)
                .order_by(models.TasaImpuesto.IdTasaImpuesto)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
    elif section == "barras_asociadas":
        barras_asociadas = (
            await db.execute(
                select(models.BarrasAsociadas)
                .order_by(models.BarrasAsociadas.IdBarraAsociada)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()

    def _count_for_section() -> int:
        if section == "productos":
            return len(productos)
        if section == "precios":
            return len(precios)
        if section == "ofertas":
            return len(ofertas)
        if section == "ofertas_vigencia":
            return len(ofertas_vigencia)
        if section == "ofertas_sucursal":
            return len(ofertas_sucursal)
        if section == "ofertas_detalles":
            return len(ofertas_detalles)
        if section == "impuestos_producto":
            return len(impuestos_producto)
        if section == "tasas_impuesto":
            return len(tasas_impuesto)
        if section == "barras_asociadas":
            return len(barras_asociadas)
        return 0

    count = _count_for_section()
    has_more = count >= limit  
    next_offset = offset + limit if has_more else None

    return {
        "updated_at": updated_at,
        "section": section,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "next_offset": next_offset,
        "productos": [
            {
                "IdProducto": p.IdProducto,
                "SKU": p.SKU,
                "Nombre": p.Nombre
            }
            for p in productos
        ],
        "precios": [
            {
                "IdProductosXEmpaqueXSucursal": pr.IdProductosXEmpaqueXSucursal,
                "IdProducto": pr.IdProducto,
                "IdEmpaque": pr.IdEmpaque,
                "CostoBase": float(pr.CostoBase) if pr.CostoBase is not None else None,
                "PVPBase": float(pr.PVPBase) if pr.PVPBase is not None else None,
                "PVPConversion": float(pr.PVPConversion) if pr.PVPConversion is not None else None,
                "IndIVA": pr.IndIVA,
                **({"FechaModifica": pr.FechaModifica.isoformat()} if hasattr(pr, "FechaModifica") and pr.FechaModifica else {})
            }
            for pr in precios
        ],
        "ofertas": [
            {
                "IdProductoOfertaxSucursal": o.IdProductoOfertaxSucursal,
                "IdProducto": o.IdProducto,
                "IdEmpaque": o.IdEmpaque,
                "IndActivo": o.IndActivo,
                "PvpOferta": float(o.PvpOferta) if o.PvpOferta is not None else None,
                "PvpBaseOferta": float(o.PvpBaseOferta) if o.PvpBaseOferta is not None else None,
            }
            for o in ofertas
        ],
        "ofertas_vigencia": [
            {
                "IdOfertaxProducto": ov.IdOfertaxProducto,
                "IndExpirado": ov.IndExpirado,
                "FechaInicio": ov.FechaInicio.isoformat() if ov.FechaInicio else None,
                "FechaFin": ov.FechaFin.isoformat() if ov.FechaFin else None,
            }
            for ov in ofertas_vigencia
        ],
        "ofertas_sucursal": [
            {
                "IdOfertaxProductoxSucursal": os.IdOfertaxProductoxSucursal,
                "IdOfertaxProducto": os.IdOfertaxProducto,
            }
            for os in ofertas_sucursal
        ],
        "ofertas_detalles": [
            {
                "IdOfertaxProductoxSucursalDetalle": od.IdOfertaxProductoxSucursalDetalle,
                "IdEmpaque": od.IdEmpaque,
                "IdOfertaxProductoxSucursal": od.IdOfertaxProductoxSucursal,
                "IndActivo": od.IndActivo,
            }
            for od in ofertas_detalles
        ],
        "impuestos_producto": [
            {
                "IdProductoxImpuesto": ip.IdProductoxImpuesto,
                "IdProducto": ip.IdProducto,
                "IdTasaImpuesto": ip.IdTasaImpuesto,
                "IndActivo": ip.IndActivo,
            }
            for ip in impuestos_producto
        ],
        "tasas_impuesto": [
            {
                "IdTasaImpuesto": t.IdTasaImpuesto,
                "Tasa": float(t.Tasa) if t.Tasa is not None else None,
            }
            for t in tasas_impuesto
        ],
        "barras_asociadas": [
            {
                "IdBarraAsociada": b.IdBarraAsociada,
                "IdProducto": b.IdProducto,
                "IdEmpaque": b.IdEmpaque,
                "Barra": b.Barra,
                "IndActivo": b.IndActivo,
                "IndVisible": b.IndVisible,
            }
            for b in barras_asociadas
        ],
    }

# Endpoint principal usando funciones auxiliares async
@app.get("/consultar/{codigo_barras}")
async def obtener_precio(
    codigo_barras: str,
    db: AsyncSession = Depends(database.get_db),
    db_erp: AsyncSession = Depends(database.get_db_erp),
):
    # Normalizar código de barras para búsqueda
    codigos_a_buscar = normalizar_codigo_barras(codigo_barras)
    
    # Intentar buscar con cada variante del código
    for codigo in codigos_a_buscar:
        resultado = await buscar_producto_y_precio(db, codigo)
        if resultado:
            producto, precio = resultado
            oferta = await buscar_oferta(db, producto.IdProducto)
            now = datetime.now()
            detalle = await buscar_detalle_oferta_vigente(db, precio, now)
            tasa_impuesto = await buscar_tasa_impuesto(db, db_erp, producto.IdProducto, precio)
            return armar_respuesta(producto, precio, oferta, detalle, tasa_impuesto)
        
        # Buscar en BarrasAsociadas si no se encuentra por SKU
        resultado_barras_asociadas = await buscar_en_barras_asociadas(db, codigo)
        if resultado_barras_asociadas:
            producto, precio = resultado_barras_asociadas
            oferta = await buscar_oferta(db, producto.IdProducto)
            now = datetime.now()
            detalle = await buscar_detalle_oferta_vigente(db, precio, now)
            tasa_impuesto = await buscar_tasa_impuesto(db, db_erp, producto.IdProducto, precio)
            return armar_respuesta(producto, precio, oferta, detalle, tasa_impuesto)
    
    raise HTTPException(
        status_code=404,
        detail={
            "mensaje": "Producto no encontrado",
            "codigo_buscado": codigo_barras,
        }
    )


#Sincronizacion forzada
# Estado global para sincronización forzada
SYNC_REQUIRED_NOW = False
FORCE_SYNC_JOBS: dict[str, dict[str, Any]] = {}
FORCE_SYNC_JOBS_LOCK = asyncio.Lock()
PLAYBACK_FORWARD_DEDUPE_SECONDS = 60
PLAYBACK_FORWARD_CACHE: dict[str, float] = {}
PLAYBACK_FORWARD_LOCK = asyncio.Lock()


class PlayingContent(BaseModel):
    titulo: str | None = None
    url: str
    tipo: str  # "video" o "image"
    duracion: int | None = None


class PlayingNowBody(BaseModel):
    device_id: str
    content: PlayingContent | None = None


class PlaybackStatusBody(BaseModel):
    device_id: str
    video_name: str
    reason: str = ""


def _playback_dedupe_key(device_id: str, video_name: str, reason: str) -> str:
    return f"{(device_id or '').strip()}|{(video_name or '').strip()}|{(reason or '').strip()}"


async def _should_forward_playback(device_id: str, video_name: str, reason: str) -> bool:
    now = asyncio.get_running_loop().time()
    key = _playback_dedupe_key(device_id, video_name, reason)

    async with PLAYBACK_FORWARD_LOCK:
        expired_keys = [
            cache_key
            for cache_key, ts in PLAYBACK_FORWARD_CACHE.items()
            if (now - ts) >= PLAYBACK_FORWARD_DEDUPE_SECONDS
        ]
        for cache_key in expired_keys:
            PLAYBACK_FORWARD_CACHE.pop(cache_key, None)

        last_seen = PLAYBACK_FORWARD_CACHE.get(key)
        if last_seen is not None and (now - last_seen) < PLAYBACK_FORWARD_DEDUPE_SECONDS:
            return False

        PLAYBACK_FORWARD_CACHE[key] = now
        return True


async def _set_force_sync_job_state(job_id: str, **fields: Any) -> None:
    async with FORCE_SYNC_JOBS_LOCK:
        job = FORCE_SYNC_JOBS.get(job_id, {})
        job.update(fields)
        job["updated_at"] = datetime.utcnow().isoformat() + "Z"
        FORCE_SYNC_JOBS[job_id] = job


async def _get_force_sync_job_state(job_id: str) -> dict[str, Any] | None:
    async with FORCE_SYNC_JOBS_LOCK:
        job = FORCE_SYNC_JOBS.get(job_id)
        return dict(job) if job else None


async def _run_force_sync_job(job_id: str, dispositivo_ids: List[str] = None) -> None:
    try:
        async with SYNC_SEQUENCE_LOCK:
            await _set_force_sync_job_state(job_id, status="RUNNING", success=True)

            async def _on_progress(progress: dict[str, Any]) -> None:
                await _set_force_sync_job_state(
                    job_id,
                    status="RUNNING",
                    success=True,
                    total=progress.get("total", 0),
                    sent=progress.get("sent", 0),
                    confirmed=progress.get("confirmed", 0),
                    failed=progress.get("failed", 0),
                    queued=progress.get("queued", 0),
                    details=progress.get("details", []),
                )

            result = await orchestrate_forced_sync_sequential(
                progress_hook=_on_progress,
                dispositivo_ids=dispositivo_ids
            )

        await _set_force_sync_job_state(
            job_id,
            status="COMPLETED",
            success=True,
            total=result.get("total", 0),
            sent=result.get("sent", 0),
            confirmed=result.get("confirmed", 0),
            failed=result.get("failed", 0),
            queued=result.get("queued", 0),
            details=result.get("details", []),
        )
    except Exception as e:
        await _set_force_sync_job_state(
            job_id,
            status="FAILED",
            success=False,
            error=str(e),
        )

# Endpoint para sincronización forzada
@app.post("/api/fuerza-sync")
async def fuerza_sync(
    async_mode: bool = Query(False),
    dispositivo_ids: str = Query(None, description="Device IDs separados por coma"),
):
    global SYNC_REQUIRED_NOW
    SYNC_REQUIRED_NOW = True

    # Convertir string separado por comas a lista
    dispositivo_ids_list = None
    if dispositivo_ids:
        dispositivo_ids_list = [d.strip() for d in dispositivo_ids.split(",") if d.strip()]
    
    if async_mode:
        job_id = uuid.uuid4().hex
        await _set_force_sync_job_state(
            job_id,
            status="QUEUED",
            success=True,
            total=0,
            sent=0,
            confirmed=0,
            failed=0,
            details=[],
            created_at=datetime.utcnow().isoformat() + "Z",
            dispositivo_ids=dispositivo_ids_list,
        )
        asyncio.create_task(_run_force_sync_job(job_id, dispositivo_ids_list))
        return {
            "success": True,
            "message": "Sincronización forzada en ejecución",
            "job_id": job_id,
            "status": "QUEUED",
            "dispositivo_ids": dispositivo_ids_list,
        }

    async with SYNC_SEQUENCE_LOCK:
        result = await orchestrate_forced_sync_sequential(dispositivo_ids=dispositivo_ids_list)
    return {
        "success": True,
        "message": "Sincronización forzada secuencial ejecutada",
        **result,
    }


class ComandoBody(BaseModel):
    comando: str
    hour: str | None = None  # formato "06:35" - el dispositivo calcula la próxima occurrence
    scheduled_at: str | None = None  # formato ISO 8601 (legacy, para backward compatibility)
    recurring: bool = False


COMMAND_TIMEOUT = 60  # segundos para esperar confirmación de reinicio


command_ack_waiters: dict[str, asyncio.Event] = {}
command_ack_payloads: dict[str, dict] = {}


@app.post("/api/comandos/{device_id}")
async def enviar_comando_a_dispositivo(
    device_id: str,
    body: ComandoBody,
):
    """
    Envía un comando a un dispositivo específico vía WebSocket.
    Soporta: REINICIAR, WIPE_AND_RESYNC
    Espera confirmación del dispositivo (timeout 60s).
    """
    comando = body.comando.upper()
    
    if comando not in ("REINICIAR", "WIPE_AND_RESYNC"):
        raise HTTPException(status_code=400, detail=f"Comando no soportado: {comando}")
    
    # Preparar payload para comandos programados
    # El dispositivo calcula la próxima occurrence en su timezone local
    is_recurring = body.recurring
    
    # Preparar payload para el dispositivo
    command_payload = {}
    if body.hour:
        # Nuevo formato: enviar solo hour y recurring
        command_payload["hour"] = body.hour
        command_payload["recurring"] = is_recurring
        logger.info(f"[COMMAND] Payload con hour: {body.hour}, recurring: {is_recurring}")
    elif body.scheduled_at:
        # Legacy: scheduled_at para backward compatibility
        command_payload["scheduled_at"] = body.scheduled_at
        command_payload["recurring"] = is_recurring
        logger.info(f"[COMMAND] Payload legacy con scheduled_at: {body.scheduled_at}")
    
    logger.info(f"[COMMAND] Payload del comando: {command_payload}")
    
    # Generar command_id único para este comando (para rastrear ack)
    command_id = str(uuid.uuid4())
    command_payload["command_id"] = command_id
    
    # Preparar waiters para confirmación
    ack_key = f"command:{device_id}:{comando}"
    
    # Validar que Redis esté disponible
    if device_command_bus is None:
        logger.error(f"[COMMAND] Redis no disponible para enviar comando a {device_id}")
        raise HTTPException(
            status_code=503, 
            detail="Sistema de comandos no disponible. Verifique que Redis esté activo."
        )
    
    # Validar que el dispositivo esté conectado
    # Primero verificar en memoria (device_map) - más confiable
    ws = tablet_ws_manager.device_map.get(device_id)
    if ws:
        logger.info(f"[COMMAND] Dispositivo {device_id} encontrado en memoria (este servidor)")
    else:
        # Fallback: verificar en Redis (device_state) - cubre caso de dispositivo en otro servidor
        logger.info(f"[COMMAND] Dispositivo {device_id} no encontrado en memoria, verificando Redis...")
        if device_state_store:
            all_status = await device_state_store.get_all_status()
            is_online = all_status.get(device_id, {}).get("online", False)
            if not is_online:
                logger.warning(f"[COMMAND] Dispositivo {device_id} no registrado o desconectado, publicando {comando}...")
                await device_command_bus.publish_command(
                    device_id=device_id,
                    command=comando,
                    payload=command_payload,
                )
                return {
                    "success": True,
                    "status": "QUEUED",
                    "message": f"Dispositivo {device_id} offline, comando {comando} publicado para cuando reconecte",
                }
            logger.info(f"[COMMAND] Dispositivo {device_id} encontrado en Redis (otro servidor)")
        else:
            # Si no hay device_state_store, permitir el intento (comando se perderá pero no se rechaza prematuramente)
            logger.warning(f"[COMMAND] device_state_store no disponible, intentando enviar comando...")
    
    try:
        # Limpiar ack de comando ANTERIOR para evitar que polling lo confunda con el actual
        if command_acker:
            await command_acker.delete_confirmation(device_id, comando)
        
        # Enviar comando vía Redis pub/sub
        logger.info(f"[COMMAND] Publicando comando '{comando}' via Redis bus...")
        await device_command_bus.publish_command(
            device_id=device_id,
            command=comando,
            payload=command_payload,
        )
        
        # Esperar confirmación via polling a Redis
        ack = {}
        logger.info(f"[COMMAND] Esperando confirmación para {device_id} via polling (timeout={COMMAND_TIMEOUT}s)")
        
        for _ in range(COMMAND_TIMEOUT):
            await asyncio.sleep(1)
            
            # 1. Intentar obtener ack de Redis (prioridad máxima — funciona para local y remoto)
            if command_acker:
                redis_ack = await command_acker.get_confirmation(device_id, comando)
                if redis_ack:
                    # Verificar que es el ack de ESTE comando, no uno viejo
                    ack_command_id = redis_ack.get("command_id")
                    if ack_command_id and ack_command_id != command_id:
                        logger.debug(f"[COMMAND] Ignorando ack de comando anterior para {device_id}")
                        await command_acker.delete_confirmation(device_id, comando)
                        continue
                    logger.info(f"[COMMAND] Confirmación recibida de Redis para {device_id}: {redis_ack.get('status')}")
                    ack = redis_ack
                    await command_acker.delete_confirmation(device_id, comando)
                    break
            
            # 2. Detectar solo dispositivos que estaban local y se desconectaron
            if ws is not None and tablet_ws_manager.device_map.get(device_id) is None:
                logger.warning(f"[COMMAND] WebSocket de {device_id} se desconectó durante la espera")
                return {
                    "success": True,
                    "status": "QUEUED",
                    "message": f"Dispositivo {device_id} se desconectó, comando {comando} será entregado cuando reconecte",
                }
            
            # 3. Verificar dict local (backward compatibility)
            local_ack = command_ack_payloads.get(ack_key)
            if local_ack:
                logger.info(f"[COMMAND] Confirmación recibida del dict local para {device_id}: {local_ack.get('status')}")
                ack = local_ack
                command_ack_payloads.pop(ack_key, None)
                break
                
            # 4. Verificar si hay waiter seteado (trabaja con el mecanismo original)
            if command_ack_waiters.get(ack_key) and command_ack_payloads.get(ack_key):
                ack = command_ack_payloads.pop(ack_key, {})
                logger.info(f"[COMMAND] Confirmación via waiter para {device_id}: {ack.get('status')}")
                break
        
        status = str(ack.get("status", "")).upper()
        
        if not status:
            logger.warning(f"[COMMAND] Timeout esperando confirmación para {device_id}")
            return {
                "success": True,
                "status": "QUEUED",
                "message": f"Dispositivo no confirmó el comando en {COMMAND_TIMEOUT}s, {comando} se entregará cuando reconecte",
            }
        
        if status in ("RECEIVED", "COMPLETED", "SUCCESS", "DONE"):
            return {
                "success": True,
                "status": status,
                "message": f"Comando {comando} ejecutado correctamente",
            }
        else:
            return {
                "success": False,
                "status": status,
                "message": ack.get("reason") or f"Comando falló con estado: {status}",
            }
    finally:
        command_ack_waiters.pop(ack_key, None)


@app.get("/api/fuerza-sync/{job_id}")
async def fuerza_sync_status(job_id: str):
    job = await _get_force_sync_job_state(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job de sincronización no encontrado")
    return {
        "success": bool(job.get("success", True)),
        "job_id": job_id,
        "status": job.get("status", "UNKNOWN"),
        "total": int(job.get("total", 0)),
        "sent": int(job.get("sent", 0)),
        "confirmed": int(job.get("confirmed", 0)),
        "queued": int(job.get("queued", 0)),
        "failed": int(job.get("failed", 0)),
        "details": job.get("details", []),
        "error": job.get("error"),
        "updated_at": job.get("updated_at"),
        "created_at": job.get("created_at"),
    }


@app.post("/api/playback-status")
async def playback_status(body: PlaybackStatusBody):
    should_forward = await _should_forward_playback(
        device_id=body.device_id,
        video_name=body.video_name,
        reason=body.reason,
    )
    if not should_forward:
        return {
            "success": True,
            "message": "Notificación de playback deduplicada en backend-api",
            "duplicated": True,
        }

    await notify_dashboard_playback_failure(
        device_id=body.device_id,
        video_name=body.video_name,
        reason=body.reason,
    )
    return {
        "success": True,
        "message": "Notificación de playback reenviada al dashboard",
        "duplicated": False,
    }


@app.post("/api/playing-now")
async def playing_now(body: PlayingNowBody):
    """
    Recibe notificación del kiosk sobre qué contenido se está reproduciendo.
    Guarda en Redis para que el dashboard pueda consultarlo.
    """
    if not body.device_id:
        raise HTTPException(status_code=400, detail="device_id requerido")
    
    logger.info(f"[PLAYING_NOW] Recibido de {body.device_id}: {body.content}")
    
    if device_state_store is not None:
        try:
            await device_state_store.update_playing_content(
                device_id=body.device_id,
                content=body.content,
            )
            return {"success": True, "message": "Contenido actualizado"}
        except Exception as e:
            logger.error(f"[PLAYING_NOW] Error guardando en Redis: {e}")
            raise HTTPException(status_code=500, detail=f"Error guardando contenido: {e}")
    else:
        logger.warning(f"[PLAYING_NOW] device_state_store no disponible")
        return {"success": False, "message": "Redis no disponible"}


@app.get("/api/device-playing/{device_id}")
async def get_device_playing(device_id: str):
    """
    Endpoint para que el dashboard consulte qué contenido se está reproduciendo.
    """
    if device_state_store is not None:
        try:
            content = await device_state_store.get_playing_content(device_id)
            return {
                "device_id": device_id,
                "contenido": content,
            }
        except Exception as e:
            logger.error(f"[DEVICE_PLAYING] Error obteniendo contenido: {e}")
            return {
                "device_id": device_id,
                "contenido": None,
                "message": f"Error: {str(e)}"
            }
    else:
        return {
            "device_id": device_id,
            "contenido": None,
            "message": "Redis no disponible"
        }


# WebSocket manager para tabletas

# --- Reintentos automáticos y mapeo device_id <-> WebSocket ---
RETRY_LIMIT = 3
RETRY_DELAY = 30  # segundos
sync_retry_counters = {}  # device_id -> intentos
REBOOT_RETRY_LIMIT = 5
REBOOT_RETRY_DELAY = 30  # segundos
reboot_retry_counters: dict[str, int] = {}  # device_id -> intentos
SYNC_ACK_TIMEOUT = 20  # segundos para esperar confirmación de recepción
SYNC_SEQUENCE_LOCK = asyncio.Lock()
sync_ack_waiters: dict[str, asyncio.Event] = {}
sync_ack_payloads: dict[str, dict] = {}

# --- Configuración de Ping WebSocket ---
WEBSOCKET_PING_INTERVAL = int(os.getenv("WEBSOCKET_PING_INTERVAL", "60"))  # 60s (antes 30s) - mejor para conexiones 12h+
WEBSOCKET_PONG_TIMEOUT = int(os.getenv("WEBSOCKET_PONG_TIMEOUT", "30"))    # 30s (antes 10s) - más tiempo para respuesta
MAX_WS_CONNECTIONS = int(os.getenv("MAX_WS_CONNECTIONS", "100"))

class TabletWebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.device_map: dict[str, WebSocket] = {}  # device_id -> WebSocket
        self.device_types: dict[str, str] = {}  # device_id -> device_type
        self.ping_tasks: dict[int, asyncio.Task] = {}  # id(websocket) -> Task
        self.pending_pong: dict[int, asyncio.Event] = {}  # id(websocket) -> Event (set by main loop when pong arrives)
        self._lock = asyncio.Lock()  # Protege acceso concurrente a estructuras compartidas
        # L2: Cola persistente en Redis (se usa global pending_queue)
        self._message_queues: dict[str, asyncio.Queue] = {}  # fallback local
        self._cleanup_task: asyncio.Task | None = None
        self._started = False

    async def start_ping_loop(self, websocket: WebSocket):
        ws_id = id(websocket)
        self.pending_pong[ws_id] = asyncio.Event()

        async def ping_sender():
            while True:
                try:
                    await asyncio.sleep(WEBSOCKET_PING_INTERVAL)

                    device_id = self.get_device_id(websocket)
                    if device_id and device_state_store is not None:
                        try:
                            await device_state_store.upsert_heartbeat(device_id=device_id)
                        except Exception as e:
                            logger.error(f"[Heartbeat] Redis error para {device_id}: {e}")

                    try:
                        import time
                        self.pending_pong[ws_id].clear()
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": int(time.time())
                        })
                        await asyncio.wait_for(
                            self.pending_pong[ws_id].wait(),
                            timeout=WEBSOCKET_PONG_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            f"[Ping] No se recibió pong del dispositivo {device_id or 'desconocido'} "
                            f"en {WEBSOCKET_PONG_TIMEOUT}s. Cerrando conexión."
                        )
                        try:
                            await websocket.close(code=1001, reason="Ping timeout")
                        except Exception:
                            pass
                        await self.disconnect(websocket)
                        return
                    except Exception as e:
                        if "not connected" in str(e).lower() or "closed" in str(e).lower():
                            await self.disconnect(websocket)
                            return
                        logger.error(f"[Ping] Error enviando ping: {e}")
                        return
                    
                    # Actualizar TTL en Redis cuando el dispositivo responde al ping
                    if device_id:
                        from app.services.device_registry import extend_device_ttl
                        asyncio.create_task(extend_device_ttl(device_id))

                except asyncio.CancelledError:
                    logger.info(f"[Ping] Tarea de ping cancelada para websocket {ws_id}")
                    break
                except Exception as e:
                    logger.error(f"[Ping] Error en loop de ping: {e}")
                    break

        task = asyncio.create_task(ping_sender())
        self.ping_tasks[ws_id] = task

    def cancel_ping_task(self, websocket: WebSocket):
        ws_id = id(websocket)
        if ws_id in self.ping_tasks:
            self.ping_tasks[ws_id].cancel()
            del self.ping_tasks[ws_id]
            logger.info(f"[Ping] Tarea de ping cancelada para websocket {ws_id}")

    async def connect(self, websocket: WebSocket):
        # Iniciar tarea de cleanup periódico si no está corriendo
        if not self._started:
            self.start_cleanup_task()
            self._started = True
        
        if len(self.active_connections) >= MAX_WS_CONNECTIONS:
            logger.warning("[WebSocket] Límite de conexiones alcanzado. Rechazando.")
            await websocket.close(code=1013, reason="Too many connections")
            return
        await websocket.accept()
        ws_id = id(websocket)
        logger.info(f"[WebSocket] Nueva conexión establecida. Total conexiones: {len(self.active_connections) + 1}")

        if ws_id in self.ping_tasks:
            self.ping_tasks[ws_id].cancel()
            del self.ping_tasks[ws_id]

        device_id = None
        try:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=10)
            import json
            msg = json.loads(data)
            logger.info(f"[WebSocket] Primer mensaje recibido: {msg}")
            device_id = msg.get("device_id")
            logger.info(f"[WebSocket] device_id del mensaje: {device_id}")
            device_type = msg.get("device_type", "verificador")
            logger.info(f"[WebSocket] device_type del mensaje: {device_type}")
            
            if not device_id:
                logger.warning("[WebSocket] device_id no proporcionado, cerrando conexión")
                await websocket.close(code=1008, reason="Missing device_id")
                return
                
            # Registrar en Redis (para que todos los workers vean el dispositivo)
            from app.services.device_registry import register_device
            await register_device(device_id)
            
            # Purga de conexión vieja
            old_ws = self.device_map.get(device_id)
            if old_ws and old_ws is not websocket:
                await self._safe_disconnect(old_ws)
                logger.info(f"[WebSocket] Conexión anterior de {device_id} cerrada por reconexión")
                # Re-registrar porque _safe_disconnect hace unregister_device,
                # borrando el key que register_device creó arriba (race en is_device_registered)
                from app.services.device_registry import register_device
                await register_device(device_id)
            
            self.device_map[device_id] = websocket
            self.device_types[device_id] = device_type
            logger.info(f"[WebSocket] device_map actualizado: {device_id} -> websocket (tipo={device_type})")
            
            # Actualizar heartbeat en Redis
            if device_state_store is not None:
                try:
                    await device_state_store.upsert_heartbeat(device_id=device_id, device_type=device_type)
                except Exception as e:
                    logger.error(f"[Heartbeat] Error actualizando estado para {device_id}: {e}")
            
            # Flush de cola de mensajes pendientes (L2: Redis + local)
            asyncio.create_task(self._flush_all_queues(device_id, websocket))
                
        except asyncio.TimeoutError:
            logger.warning("[WebSocket] Timeout esperando IDENTIFY (10s)")
            await websocket.close(code=1008, reason="Identification timeout")
            return
        except json.JSONDecodeError as e:
            logger.warning(f"[WebSocket] IDENTIFY no es JSON válido: {e}")
            await websocket.close(code=1008, reason="Invalid identification format")
            return
        except Exception as e:
            logger.error(f"[WebSocket] Error al procesar identificación: {e}")
            await websocket.close(code=1008, reason="Identification failed")
            return
        
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            ws_id = id(websocket)
            self.cancel_ping_task(websocket)
            self.pending_pong.pop(ws_id, None)
            
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info(f"[WebSocket] Conexión cerrada. Total conexiones restantes: {len(self.active_connections)}")

            # Eliminar cola de mensajes y recuperar inflight
            device_id = None
            for k, v in list(self.device_map.items()):
                if v is websocket:
                    device_id = k
                    del self.device_map[k]
                    self.device_types.pop(k, None)
                    self._message_queues.pop(k, None)
                    # L2: Recuperar mensajes inflight de Redis
                    if pending_queue is not None:
                        asyncio.create_task(pending_queue.recover_inflight(k))
                    break

            # Marcar offline en Redis
            if device_id:
                if device_state_store is not None:
                    asyncio.create_task(device_state_store.mark_offline(device_id))
                from app.services.device_registry import unregister_device
                asyncio.create_task(unregister_device(device_id))

    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"[WS] Error en broadcast: {e}")
                dead.append(connection)
        for ws in dead:
            await self.disconnect(ws)

    async def send_to_device(self, device_id: str, message: dict):
        # L1.4: Agregar command_id único para dedup en cliente
        if "command_id" not in message:
            message["command_id"] = str(uuid.uuid4())
        
        ws = self.device_map.get(device_id)
        if ws:
            # Verificar estado real del socket ANTES de enviar
            # Previene "entregas fantasma" cuando TCP murió pero device_map aún referencia el WS
            ws_state = getattr(ws, 'client_state', None)
            if ws_state is not None and ws_state.name != "CONNECTED":
                logger.warning(
                    f"[WS] Dispositivo {device_id} tiene conexión fantasma "
                    f"(estado={ws_state.name}), limpiando — NO se encola"
                )
                await self.disconnect(ws)
                return True
            else:
                try:
                    await ws.send_json(message)
                    return True
                except Exception as e:
                    logger.warning(f"[WS] Error enviando a {device_id}: {e}")
                    await asyncio.sleep(0.5)
                    try:
                        await ws.send_json(message)
                        return True
                    except Exception as e2:
                        logger.warning(f"[WS] Reintento falló para {device_id}: {e2}")
                        await self.disconnect(ws)
                        await self._enqueue_message(device_id, message)
                        return False
        
        # Dispositivo no está en este worker
        # Verificar si está vivo en otro worker (registry compartido)
        from app.services import device_registry as dr
        if dr.device_registry is not None:
            try:
                if await dr.device_registry.is_device_registered(device_id):
                    # Vivo en otro worker → no enqueueamos (no infla badge)
                    # Seteamos pending_sync 24h como respaldo
                    # Pero NO si este mensaje viene del re-publish en reconnect
                    # (evita loop: pending_sync → bus → send_to_device → pending_sync)
                    if not message.get("_from_reconnect") and pending_queue is not None:
                        await pending_queue.set_pending_sync(device_id)
                    return True
            except Exception:
                pass
        
        # Dispositivo offline real — encolar para cuando reconecte
        if not message.get("_from_reconnect"):
            await self._enqueue_message(device_id, message)
        return False

    async def _enqueue_message(self, device_id: str, message: dict, websocket: WebSocket | None = None):
        # L2: Priorizar cola persistente en Redis
        if pending_queue is not None:
            logger.info(f"[WS] Encolando en Redis para {device_id}: command={message.get('command')} command_id={message.get('command_id')}")
            await pending_queue.enqueue(device_id, message)
            # Si el dispositivo reconectó entre tanto, flush inmediato
            ws = websocket or self.device_map.get(device_id)
            if ws:
                asyncio.create_task(pending_queue.flush_all_to_device(
                    device_id,
                    lambda msg, _w=ws: _w.send_json(msg) or True
                ))
            return
        
        # Fallback: cola local en memoria
        import time
        MAX_QUEUE_PER_DEVICE = 100
        if device_id not in self._message_queues:
            self._message_queues[device_id] = asyncio.Queue()
        if self._message_queues[device_id].qsize() < MAX_QUEUE_PER_DEVICE:
            message_with_ts = {**message, "enqueued_at": time.time()}
            self._message_queues[device_id].put_nowait(message_with_ts)
            logger.info(f"[WS] Mensaje encolado para {device_id} (cola: {self._message_queues[device_id].qsize()})")
        else:
            logger.warning(f"[WS] Cola llena para {device_id} ({MAX_QUEUE_PER_DEVICE} msgs), descartando mensaje")

    async def _flush_all_queues(self, device_id: str, websocket: WebSocket):
        """L2: Flush de cola Redis + cola local + pending banners."""
        # 1. Cola persistente Redis
        if pending_queue is not None:
            async def _deliver(msg):
                await websocket.send_json(msg)
                return True
            await pending_queue.flush_all_to_device(device_id, _deliver)

        # 2. Cola local en memoria (fallback)
        if device_id in self._message_queues:
            await self.flush_message_queue(device_id, websocket)
        
        # 3. Consumir pending banners legacy
        if pending_queue is not None:
            try:
                banner = await pending_queue.consume_pending_banner(device_id)
                if banner:
                    await websocket.send_json(banner)
                    logger.info(f"[QUEUE] Banner pendiente entregado a {device_id}: {banner.get('command')}")
            except Exception as e:
                logger.error(f"[QUEUE] Error consumiendo pending banner para {device_id}: {e}")

        # L3.3: Verificar flags de pendientes al reconectar
        if pending_queue is not None:
            try:
                if await pending_queue.check_pending_sync(device_id):
                    logger.info(f"[QUEUE] Sync pendiente detectado para {device_id}, disparando WIPE_AND_RESYNC")
                    if device_command_bus is not None:
                        await device_command_bus.publish_command(
                            device_id=device_id,
                            command="WIPE_AND_RESYNC",
                            payload={"_from_reconnect": True},
                        )
                    else:
                        await self.send_to_device(device_id, {"command": "WIPE_AND_RESYNC"})
                    await pending_queue.set_delivery_pending(device_id)
            except Exception as e:
                logger.error(f"[QUEUE] Error verificando pending sync para {device_id}: {e}")

            try:
                reboot_payload = await pending_queue.check_pending_reboot(device_id)
                if reboot_payload:
                    logger.info(f"[QUEUE] REINICIAR pendiente detectado para {device_id}, re-enviando")
                    await self.send_to_device(device_id, reboot_payload)
            except Exception as e:
                logger.error(f"[QUEUE] Error verificando pending reboot para {device_id}: {e}")
    
    async def send_to_websocket(self, websocket: WebSocket, message: dict) -> bool:
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            return False

    def get_device_id(self, websocket: WebSocket) -> str | None:
        for device_id, ws in self.device_map.items():
            if ws is websocket:
                return device_id
        return None

    async def flush_message_queue(self, device_id: str, websocket: WebSocket) -> int:
        """Entrega mensajes pendientes al dispositivo. Retorna cantidad entregada.
        L2: Usa cola Redis si está disponible, fallback a cola local."""
        # Priorizar cola Redis
        if pending_queue is not None:
            async def _deliver(msg):
                await websocket.send_json(msg)
                return True
            delivered = await pending_queue.flush_all_to_device(device_id, _deliver)
            return delivered
        
        # Fallback: cola local en memoria
        if device_id not in self._message_queues:
            return 0
        
        queue = self._message_queues[device_id]
        delivered = 0
        failed_messages = []
        
        while not queue.empty():
            try:
                msg = queue.get_nowait()
                await websocket.send_json(msg)
                delivered += 1
            except Exception as e:
                logger.warning(f"[WS] Error entregando mensaje de cola a {device_id}: {e}")
                failed_messages.append(msg)
                break
        
        for msg in failed_messages:
            try:
                queue.put_nowait(msg)
            except asyncio.QueueFull:
                break
        
        if queue.empty():
            self._message_queues.pop(device_id, None)
        
        if delivered > 0:
            logger.info(f"[WS] {delivered} mensajes entregados de la cola a {device_id}")
        return delivered

    async def cleanup_dead_connections(self):
        """Limpia conexiones en estado inválido. Se llama periódicamente."""
        async with self._lock:
            dead = []
            for ws in self.active_connections:
                if ws.client_state.name != "CONNECTED":
                    dead.append(ws)
            
            for ws in dead:
                logger.info(f"[WS] Limpiando conexión muerta: {id(ws)}")
                await self._safe_disconnect(ws)
            
            if dead:
                logger.info(f"[WS] Cleanup: {len(dead)} conexiones muertas removidas")

    async def _safe_disconnect(self, websocket: WebSocket):
        """Desconecta sin lock (para uso interno desde cleanup)."""
        try:
            ws_id = id(websocket)
            self.cancel_ping_task(websocket)
            self.pending_pong.pop(ws_id, None)
            
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            
            device_id = None
            for k, v in list(self.device_map.items()):
                if v is websocket:
                    device_id = k
                    del self.device_map[k]
                    self._message_queues.pop(k, None)
                    if pending_queue is not None:
                        asyncio.create_task(pending_queue.recover_inflight(k))
                    break
            
            if device_id:
                if device_state_store is not None:
                    asyncio.create_task(device_state_store.mark_offline(device_id))
                from app.services.device_registry import unregister_device
                asyncio.create_task(unregister_device(device_id))
        except Exception as e:
            logger.error(f"[WS] Error en _safe_disconnect: {e}")

    def start_cleanup_task(self):
        """Inicia la tarea de cleanup periódico y reconciliación si no están corriendo."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            asyncio.create_task(self._reconciliation_loop())
            logger.info("[WS] Tareas de cleanup y reconciliación iniciadas")

    async def _periodic_cleanup(self):
        """Cleanup periódico cada 60 segundos.
        L4.2: cleanup_old_dlq() se movió a reconciliación (30 min)."""
        while True:
            try:
                await asyncio.sleep(60)
                await self.cleanup_dead_connections()
                await self._cleanup_old_queues()
                # L2: Cleanup de mensajes antiguos en Redis
                if pending_queue is not None:
                    asyncio.create_task(pending_queue.cleanup_old_messages())
                # Flush de cola Redis para dispositivos online
                asyncio.create_task(self._flush_online_queues())
            except asyncio.CancelledError:
                logger.info("[WS] Tarea de cleanup cancelada")
                break
            except Exception as e:
                logger.error(f"[WS] Error en cleanup periódico: {e}")

    async def _cleanup_old_queues(self):
        """Limpia colas de mensajes antiguos o de dispositivos desconectados.
        L1.5: MAX_MESSAGE_AGE = 86400s (24h), cutoff original 300s (5 min) para dispositivos desconectados."""
        cleaned = 0
        import time
        MAX_MESSAGE_AGE = 86400  # 24 horas
        cutoff_offline = time.time() - 300  # 5 min para desconectados
        cutoff_age = time.time() - MAX_MESSAGE_AGE  # 24h para cualquier mensaje
        
        async with self._lock:
            for device_id in list(self._message_queues.keys()):
                queue = self._message_queues[device_id]
                is_connected = device_id in self.device_map
                
                if not is_connected:
                    queue_size = queue.qsize()
                    if queue_size > 0:
                        while not queue.empty():
                            try:
                                msg = queue.get_nowait()
                                msg_time = msg.get("enqueued_at", 0)
                                if msg_time > 0 and msg_time < cutoff_offline:
                                    cleaned += 1
                                else:
                                    # Re-encolar si no ha expirado aún
                                    try:
                                        queue.put_nowait(msg)
                                    except asyncio.QueueFull:
                                        cleaned += 1
                            except asyncio.QueueEmpty:
                                break
                        logger.info(f"[WS] Cola limpiada para dispositivo desconectado {device_id}: {queue_size} mensajes revisados, {cleaned} removidos")
                    if queue.empty():
                        self._message_queues.pop(device_id, None)
                else:
                    temp_queue = asyncio.Queue()
                    while not queue.empty():
                        try:
                            msg = queue.get_nowait()
                            msg_time = msg.get("enqueued_at", 0)
                            if msg_time > 0 and msg_time < cutoff_age:
                                # Mensaje con más de 24h, descartar
                                cleaned += 1
                            else:
                                temp_queue.put_nowait(msg)
                        except asyncio.QueueEmpty:
                            break
                    
                    while not temp_queue.empty():
                        try:
                            queue.put_nowait(temp_queue.get_nowait())
                        except asyncio.QueueFull:
                            break
        
        if cleaned > 0:
            logger.info(f"[WS] Total de mensajes antiguos limpiados: {cleaned}")

    async def _flush_online_queues(self):
        """Flushea colas Redis de dispositivos online en este worker.
        Se ejecuta cada 60s desde _periodic_cleanup para entregar
        mensajes encolados a dispositivos que están conectados."""
        if pending_queue is None:
            return
        for device_id, ws in list(self.device_map.items()):
            try:
                await pending_queue.flush_all_to_device(
                    device_id,
                    lambda msg, _w=ws: _w.send_json(msg) or True
                )
            except Exception as e:
                logger.warning(f"[FLUSH] Error flusheando cola para {device_id}: {e}")

    async def _reconcile_all_queues(self):
        """L4.2: Reconciliación de colas Redis vs dispositivos online cada 30 min.
        Recupera inflight huérfanos, flushea a online, limpia DLQ y flags huérfanos."""
        if pending_queue is None:
            return
        try:
            stats = await pending_queue.get_all_stats()
            for device_id, qstats in stats.items():
                total = qstats.get("total", 0)
                if total == 0:
                    continue
                is_online = device_id in self.device_map
                ws = self.device_map.get(device_id)
                if is_online and ws:
                    await pending_queue.recover_inflight(device_id)
                    _ws = ws  # captura por valor para el closure
                    await pending_queue.flush_all_to_device(
                        device_id,
                        lambda msg, _w=_ws: _w.send_json(msg) or True
                    )
            # Cleanup DLQ vieja
            if pending_queue is not None:
                asyncio.create_task(pending_queue.cleanup_old_dlq())
            # Cleanup flags huérfanos
            active_ids = set(self.device_map.keys())
            if device_state_store:
                try:
                    all_status = await device_state_store.get_all_status()
                    active_ids.update(all_status.keys())
                except Exception:
                    pass
            if pending_queue is not None:
                asyncio.create_task(pending_queue.cleanup_orphan_flags(active_ids))
        except Exception as e:
            logger.error(f"[RECONCILE] Error en reconciliación: {e}")

    async def _reconciliation_loop(self):
        """L4.2: Ejecuta reconciliación cada 30 minutos."""
        while True:
            try:
                await asyncio.sleep(1800)
                await self._reconcile_all_queues()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[RECONCILE] Error en loop: {e}")

    def get_connected_targets(self) -> list[tuple[str | None, WebSocket]]:
        targets: list[tuple[str | None, WebSocket]] = []
        mapped_sockets = set(self.device_map.values())

        for device_id, ws in self.device_map.items():
            targets.append((device_id, ws))

        for ws in self.active_connections:
            if ws not in mapped_sockets:
                targets.append((None, ws))

        return targets

    def ack_key(self, websocket: WebSocket, device_id: str | None = None) -> str:
        resolved_device = device_id or self.get_device_id(websocket)
        if resolved_device:
            return f"device:{resolved_device}"
        return f"ws:{id(websocket)}"

tablet_ws_manager = TabletWebSocketManager()


async def _apply_sync_confirmation(device_id: str, status: str, reason: str = ""):
    ack_key = f"device:{device_id}"
    normalized_status = str(status or "").upper()
    
    logger.info(f"[ACKER] Confirmación WIPE_AND_RESYNC de {device_id}: status={normalized_status}")
    
    # NO guardamos en Redis aquí - ya se hizo en process_sync_confirmation
    # Solo actualizamos el dict local para backward compatibility

    sync_ack_payloads[ack_key] = {
        "device_id": device_id,
        "status": normalized_status,
        "reason": reason,
    }

    waiter = sync_ack_waiters.get(ack_key)
    if waiter:
        waiter.set()

    if normalized_status == "FAILED":
        asyncio.create_task(notify_dashboard_sync_failure(device_id or "unknown", reason))


async def _on_bus_command(device_id: str, command: str, payload: dict):
    if not device_id or not command:
        return
    logger.info(f"[BUS] Comando recibido: '{command}' para dispositivo {device_id}")
    try:
        if command == "WIPE_AND_RESYNC":
            message = {"command": "WIPE_AND_RESYNC"}
            if payload:
                message.update(payload)
            await tablet_ws_manager.send_to_device(device_id, message)
        elif command == "REINICIAR":
            message = {"command": "REINICIAR"}
            if payload:
                message.update(payload)
            await tablet_ws_manager.send_to_device(device_id, message)
        elif command in ("BANNER_INICIADO", "BANNER_FINALIZADO"):
            banner_id = payload.get("banner_id") if payload else None
            if banner_id is not None and banner_batch_manager is not None:
                dedup_key = f"bus:notif:{device_id}:{command}:{banner_id}"
                added = await banner_batch_manager.redis.set(dedup_key, "1", nx=True, ex=60)
                if not added:
                    logger.debug(f"[BUS] {command} banner {banner_id} para {device_id} ya procesado, saltando")
                    return
            await tablet_ws_manager.send_to_device(device_id, payload)
        elif command == "BANNER_LIST":
            await tablet_ws_manager.broadcast(payload)
    except Exception as e:
        logger.error(f"[BUS] Error procesando comando '{command}' para {device_id}: {e}")


async def _on_bus_confirmation(device_id: str, command: str, status: str, reason: str):
    if not device_id:
        return
    
    # Manejar confirmación de WIPE_AND_RESYNC
    if command == "WIPE_AND_RESYNC":
        await _apply_sync_confirmation(device_id=device_id, status=status, reason=reason)
        # Limpiar pending_sync por si este worker no coincide con el que recibió la confirmación directa
        if pending_queue is not None and status in ("SUCCESS", "RECEIVED", "DONE"):
            try:
                await pending_queue.clear_pending_sync(device_id)
            except Exception:
                pass
        return
    
    # Manejar confirmación de REINICIAR
    if command == "REINICIAR":
        logger.info(f"[ACKER] Confirmación REINICIAR via bus de {device_id}: status={status}")
        
        # GUARDAR EN REDIS para que cualquier worker pueda procesarla
        global command_acker
        if command_acker:
            try:
                await command_acker.save_confirmation(
                    device_id=device_id,
                    command=command,
                    status=status,
                    reason=reason,
                )
            except Exception as e:
                logger.error(f"[ACKER] Error guardando confirmación en Redis: {e}")
        
        # Mantener backward compatibility
        ack_key = f"command:{device_id}:{command}"
        command_ack_payloads[ack_key] = {
            "device_id": device_id,
            "command": command,
            "status": status,
            "reason": reason,
        }
        waiter = command_ack_waiters.get(ack_key)
        if waiter:
            waiter.set()
        return


async def _start_device_bus_listener():
    if device_command_bus is None:
        return
    try:
        await device_command_bus.subscribe_forever(
            on_command=_on_bus_command,
            on_confirmation=_on_bus_confirmation,
        )
    except asyncio.CancelledError:
        logger.info("[BUS] Listener cancelado")
        raise
    except Exception as e:
        logger.error("Error en listener de DeviceCommandBus: %s", e)
        raise


async def _start_device_bus_listener_with_retry():
    while True:
        try:
            await _start_device_bus_listener()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[BUS] Listener murió, reiniciando en 5s: {e}")
            await asyncio.sleep(5)


async def orchestrate_forced_sync_sequential(
    progress_hook: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    dispositivo_ids: List[str] = None,
) -> dict:
    target_device_ids: list[str] = []

    if dispositivo_ids:
        target_device_ids = list(dispositivo_ids)
    elif device_state_store is not None:
        try:
            status_map = await device_state_store.get_all_status()
            target_device_ids = sorted([device_id for device_id, info in status_map.items() if info.get("online")])
        except Exception as e:
            logger.error("Error leyendo estado compartido de dispositivos: %s", e)

    if not target_device_ids:
        target_device_ids = sorted([device_id for device_id, _ in tablet_ws_manager.get_connected_targets() if device_id])

    if not target_device_ids:
        return {
            "total": 0,
            "sent": 0,
            "confirmed": 0,
            "queued": 0,
            "failed": 0,
            "details": [],
        }

    sent = 0
    confirmed = 0
    queued = 0
    details = []

    if progress_hook:
        await progress_hook(
            {
                "total": len(target_device_ids),
                "sent": sent,
                "confirmed": confirmed,
                "queued": queued,
                "failed": len(target_device_ids) - confirmed - queued,
                "details": list(details),
            }
        )

    for device_id in target_device_ids:
        ack_key = f"device:{device_id}"
        waiter = asyncio.Event()
        sync_ack_waiters[ack_key] = waiter
        sync_ack_payloads.pop(ack_key, None)

        # Limpiar ack de sync ANTERIOR para evitar que polling lo atrape
        if command_acker:
            await command_acker.delete_confirmation(device_id, "WIPE_AND_RESYNC")

        send_ok = False
        try:
            sync_command_id = str(uuid.uuid4())
            if device_command_bus is not None:
                await device_command_bus.publish_command(
                    device_id=device_id,
                    command="WIPE_AND_RESYNC",
                    payload={"command_id": sync_command_id},
                )
                send_ok = True
            else:
                await tablet_ws_manager.send_to_device(device_id, {"command": "WIPE_AND_RESYNC", "command_id": sync_command_id})
                send_ok = True
        except Exception:
            send_ok = False

        if not send_ok:
            reason = "No se pudo enviar comando por WebSocket"
            was_queued = False
            if pending_queue is not None:
                await pending_queue.set_pending_sync(device_id)
                was_queued = True
            sync_ack_waiters.pop(ack_key, None)
            if was_queued:
                asyncio.create_task(notify_dashboard_sync_queued(device_id, reason))
                queued += 1
                details.append(
                    {
                        "device_id": device_id,
                        "ack_key": ack_key,
                        "ok": True,
                        "status": "QUEUED",
                        "reason": "Dispositivo offline. Se ejecutará al reconectar.",
                        "queued": True,
                    }
                )
            else:
                asyncio.create_task(notify_dashboard_sync_failure(device_id, reason))
                details.append(
                    {
                        "device_id": device_id,
                        "ack_key": ack_key,
                        "ok": False,
                        "status": "SEND_FAILED",
                        "reason": reason,
                    }
                )
            if progress_hook:
                await progress_hook(
                    {
                        "total": len(target_device_ids),
                        "sent": sent,
                        "confirmed": confirmed,
                        "queued": queued,
                        "failed": len(target_device_ids) - confirmed - queued,
                        "details": list(details),
                    }
                )
            continue

        sent += 1

        try:
            # Polling a Redis para confirmación
            ack = {}
            logger.info(f"[SYNC] Esperando confirmación para {device_id} via polling (timeout={SYNC_ACK_TIMEOUT}s)")
            
            for _ in range(SYNC_ACK_TIMEOUT):
                await asyncio.sleep(1)
                
                # 1. Intentar obtener de Redis
                if command_acker:
                    redis_ack = await command_acker.get_confirmation(device_id, "WIPE_AND_RESYNC")
                    if redis_ack:
                        # Verificar que es el ack de ESTE sync, no uno viejo
                        ack_cmd_id = redis_ack.get("command_id")
                        if ack_cmd_id and ack_cmd_id != sync_command_id:
                            logger.debug(f"[SYNC] Ignorando ack de sync anterior para {device_id}")
                            await command_acker.delete_confirmation(device_id, "WIPE_AND_RESYNC")
                            continue
                        logger.info(f"[SYNC] Confirmación recibida de Redis para {device_id}: {redis_ack.get('status')}")
                        ack = redis_ack
                        await command_acker.delete_confirmation(device_id, "WIPE_AND_RESYNC")
                        break
                
                # 2. Verificar dict local (backward compatibility)
                local_ack = sync_ack_payloads.get(ack_key)
                if local_ack:
                    logger.info(f"[SYNC] Confirmación recibida del dict local para {device_id}: {local_ack.get('status')}")
                    ack = local_ack
                    sync_ack_payloads.pop(ack_key, None)
                    break
                    
                # 3. Verificar si hay waiter seteado
                if sync_ack_waiters.get(ack_key) and sync_ack_payloads.get(ack_key):
                    ack = sync_ack_payloads.pop(ack_key, {})
                    logger.info(f"[SYNC] Confirmación via waiter para {device_id}: {ack.get('status')}")
                    break
            
            # No se recibió ack en el timeout → comando ya está en Redis queue (encolado por bus listener)
            if not ack:
                timeout_reason = f"Sin confirmación en {SYNC_ACK_TIMEOUT}s"
                was_queued = False
                if pending_queue is not None:
                    # El command ya fue encolado en Redis por send_to_device/bus listener
                    # set_pending_sync es redundante y causaría badge "En espera" duplicado
                    was_queued = True
                if was_queued:
                    asyncio.create_task(notify_dashboard_sync_queued(device_id, timeout_reason))
                    queued += 1
                    details.append(
                        {
                            "device_id": device_id,
                            "ack_key": ack_key,
                            "ok": True,
                            "status": "QUEUED",
                            "reason": f"Sin confirmación en {SYNC_ACK_TIMEOUT}s. Se ejecutará al reconectar.",
                            "queued": True,
                        }
                    )
                else:
                    asyncio.create_task(notify_dashboard_sync_failure(device_id, timeout_reason))
                    details.append(
                        {
                            "device_id": device_id,
                            "ack_key": ack_key,
                            "ok": False,
                            "status": "TIMEOUT",
                            "reason": timeout_reason,
                        }
                    )
            else:
                status = str(ack.get("status", "")).upper()
                ok = status in ("RECEIVED", "SUCCESS", "DONE")
                if ok:
                    confirmed += 1
                else:
                    fail_reason = ack.get("reason", "") or f"Estado no exitoso: {status or 'UNKNOWN'}"
                    if pending_queue is not None:
                        await pending_queue.set_pending_sync(device_id)
                    asyncio.create_task(notify_dashboard_sync_failure(device_id, fail_reason))
                details.append(
                    {
                        "device_id": ack.get("device_id") or device_id,
                        "ack_key": ack_key,
                        "ok": ok,
                        "status": status or "UNKNOWN",
                        "reason": ack.get("reason", ""),
                    }
                )
        finally:
            sync_ack_waiters.pop(ack_key, None)

        if progress_hook:
            await progress_hook(
                {
                    "total": len(target_device_ids),
                    "sent": sent,
                    "confirmed": confirmed,
                    "queued": queued,
                    "failed": len(target_device_ids) - confirmed - queued,
                    "details": list(details),
                }
            )
        
        # Delay entre dispositivos para evitar colapsos (2 segundos)
        if len(target_device_ids) > 1:
            await asyncio.sleep(2)

    failed = len(target_device_ids) - confirmed - queued
    return {
        "total": len(target_device_ids),
        "sent": sent,
        "confirmed": confirmed,
        "queued": queued,
        "failed": failed,
        "details": details,
    }


async def process_sync_confirmation(websocket: WebSocket, msg: dict):
    if msg.get("type") != "CONFIRMATION":
        return
    
    command = msg.get("command")
    status = str(msg.get("status", "")).upper()
    reason = msg.get("reason", "")
    device_id = msg.get("device_id") or tablet_ws_manager.get_device_id(websocket)
    if not device_id:
        return
    
    # Manejar confirmación de BANNER_INICIADO
    if command == "BANNER_INICIADO" and status == "SUCCESS":
        banner_id = msg.get("banner_id")
        if banner_id is not None:
            await notify_dashboard_banner_iniciado(device_id, banner_id)
        else:
            logger.info(f"[CONFIRM] BANNER_INICIADO sin banner_id de {device_id}, omitiendo dashboard")
        return
    
    # Manejar confirmación de BANNER_FINALIZADO
    if command == "BANNER_FINALIZADO" and status == "SUCCESS":
        banner_id = msg.get("banner_id")
        if banner_id is not None:
            await notify_dashboard_banner_finalizado(device_id, banner_id)
        else:
            logger.info(f"[CONFIRM] BANNER_FINALIZADO sin banner_id de {device_id}, omitiendo dashboard")
        return
    
    # Manejar confirmación de REINICIAR
    if command == "REINICIAR":
        logger.info(f"[ACKER] Confirmación REINICIAR recibida de {device_id}: status={status}")
        
        # GUARDAR EN REDIS para que cualquier worker pueda procesarla
        global command_acker
        if command_acker:
            try:
                await command_acker.save_confirmation(
                    device_id=device_id,
                    command=command,
                    status=status,
                    reason=reason,
                    command_id=msg.get("command_id"),
                )
            except Exception as e:
                logger.error(f"[ACKER] Error guardando confirmación REINICIAR en Redis: {e}")
        
        # Mantener backward compatibility con dict local
        ack_key = f"command:{device_id}:{command}"
        command_ack_payloads[ack_key] = {
            "device_id": device_id,
            "command": command,
            "status": status,
            "reason": reason,
        }
        waiter = command_ack_waiters.get(ack_key)
        if waiter:
            waiter.set()
        
        # Limpiar pending_reboot si el reinicio se confirmó exitosamente
        if status == "SUCCESS" and pending_queue is not None:
            try:
                await pending_queue.clear_pending_reboot(device_id)
            except Exception as e:
                logger.error(f"[REBOOT] Error limpiando pending_reboot: {e}")

        # NO publicamos al bus aquí - ya guardamos en Redis directamente
        # El bus es solo para el caso fallback (cuando no hay WebSocket directo)
        return
    
    # Manejar confirmación de WIPE_AND_RESYNC (original)
    if command != "WIPE_AND_RESYNC":
        return

    # Guardar en Redis directamente (NO publicar al bus para evitar duplicados)
    # Solo guardamos aquí - NO en _apply_sync_confirmation para evitar duplicados
    logger.info(f"[ACKER] Confirmación WIPE_AND_RESYNC de {device_id}: status={status}")
    if command_acker:
        try:
            await command_acker.save_confirmation(
                device_id=device_id,
                command="WIPE_AND_RESYNC",
                status=status,
                reason=reason,
                command_id=msg.get("command_id"),
            )
        except Exception as e:
            logger.error(f"[ACKER] Error guardando confirmación SYNC en Redis: {e}")

    # Actualizar dict local (para backward compatibility)
    await _apply_sync_confirmation(device_id=device_id, status=status, reason=reason)

    # Limpiar pending_sync cuando el sync se completa exitosamente
    if status in ("SUCCESS", "RECEIVED", "DONE"):
        if pending_queue is not None:
            try:
                await pending_queue.clear_pending_sync(device_id)
            except Exception as e:
                logger.error(f"[SYNC] Error limpiando pending_sync: {e}")

    # Notificar entrega exitosa al dashboard (FASE 17.3)
    if status in ("SUCCESS", "RECEIVED", "DONE"):
        if pending_queue is not None:
            try:
                if await pending_queue.check_delivery_pending(device_id):
                    asyncio.create_task(notify_dashboard_sync_delivered(device_id))
            except Exception as e:
                logger.error(f"[DELIVERY] Error en check_delivery_pending: {e}")

# Endpoint WebSocket para tabletas
async def notify_dashboard_sync_failure(device_id: str, reason: str = ""):
    dashboard_url = os.getenv("DASHBOARD_URL")
    if not dashboard_url:
        logging.error("DASHBOARD_URL no está definida en el entorno. Agrega esta variable en tu archivo .env.")
        return
    notify_endpoint = f"{dashboard_url.rstrip('/')}/api/sync-status"
    try:
        async with httpx.AsyncClient() as client:
            payload = {"device_id": device_id, "status": "FAILED", "reason": reason}
            await client.post(notify_endpoint, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Error notificando a backend-dashboard: {e}")


async def notify_dashboard_sync_queued(device_id: str, reason: str = ""):
    dashboard_url = os.getenv("DASHBOARD_URL")
    if not dashboard_url:
        return
    notify_endpoint = f"{dashboard_url.rstrip('/')}/api/sync-queued"
    try:
        async with httpx.AsyncClient() as client:
            payload = {"device_id": device_id, "status": "QUEUED", "reason": reason}
            await client.post(notify_endpoint, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Error notificando sync queued al dashboard: {e}")


async def notify_dashboard_sync_delivered(device_id: str):
    dashboard_url = os.getenv("DASHBOARD_URL")
    if not dashboard_url:
        return
    notify_endpoint = f"{dashboard_url.rstrip('/')}/api/sync-delivered"
    try:
        async with httpx.AsyncClient() as client:
            payload = {"device_id": device_id, "status": "SUCCESS"}
            await client.post(notify_endpoint, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Error notificando sync delivered al dashboard: {e}")


async def notify_dashboard_banner_iniciado(device_id: str, banner_id: int | None = None):
    """Notifica al dashboard cuando un banner inicia en un dispositivo."""
    dashboard_url = os.getenv("DASHBOARD_URL")
    if not dashboard_url:
        logging.error("DASHBOARD_URL no está definida en el entorno.")
        return
    notify_endpoint = f"{dashboard_url.rstrip('/')}/api/banner-status"
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "device_id": device_id,
                "banner_id": banner_id,
                "status": "INICIADO",
            }
            await client.post(notify_endpoint, json=payload, timeout=10)
            logger.info(f"Notificación enviada al dashboard: Banner {banner_id} iniciado en dispositivo {device_id}")
    except Exception as e:
        logging.error(f"Error notificando banner iniciado al dashboard: {e}")


async def notify_dashboard_banner_finalizado(device_id: str, banner_id: int | None = None):
    """Notifica al dashboard cuando un banner finaliza en un dispositivo."""
    dashboard_url = os.getenv("DASHBOARD_URL")
    if not dashboard_url:
        logging.error("DASHBOARD_URL no está definida en el entorno.")
        return
    notify_endpoint = f"{dashboard_url.rstrip('/')}/api/banner-status"
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "device_id": device_id,
                "banner_id": banner_id,
                "status": "FINALIZADO",
            }
            await client.post(notify_endpoint, json=payload, timeout=10)
            logger.info(f"Notificación enviada al dashboard: Banner {banner_id} finalizado en dispositivo {device_id}")
    except Exception as e:
        logging.error(f"Error notificando banner finalizado al dashboard: {e}")


async def notify_dashboard_playback_failure(device_id: str, video_name: str, reason: str = ""):
    dashboard_url = os.getenv("DASHBOARD_URL")
    if not dashboard_url:
        logging.error("DASHBOARD_URL no está definida en el entorno. Agrega esta variable en tu archivo .env.")
        return
    notify_endpoint = f"{dashboard_url.rstrip('/')}/api/playback-status"
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "device_id": device_id,
                "video_name": video_name,
                "reason": reason,
            }
            await client.post(notify_endpoint, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Error notificando playback al backend-dashboard: {e}")

# --- Reintentos automáticos de sincronización ---
async def retry_sync_with_device(device_id: str):
    count = sync_retry_counters.get(device_id, 0)
    if count < RETRY_LIMIT:
        sync_retry_counters[device_id] = count + 1
        await asyncio.sleep(RETRY_DELAY)
        # Reenviar comando de sincronización solo a ese dispositivo
        try:
            if device_command_bus is not None:
                await device_command_bus.publish_command(
                    device_id=device_id,
                    command="WIPE_AND_RESYNC",
                    payload={},
                )
            else:
                await tablet_ws_manager.send_to_device(device_id, {"command": "WIPE_AND_RESYNC"})
        except Exception as e:
            logging.error("Error reenviando sincronización a %s: %s", device_id, e)
    else:
        sync_retry_counters.pop(device_id, None)
        if pending_queue is not None:
            await pending_queue.set_pending_sync(device_id)
        logging.error(f"Dispositivo {device_id} falló sincronización tras {RETRY_LIMIT} reintentos.")

# --- Reintentos automáticos de REINICIAR ---
async def retry_reboot_with_device(device_id: str, payload: dict):
    """L4.1: Reintenta enviar REINICIAR hasta REBOOT_RETRY_LIMIT veces."""
    count = reboot_retry_counters.get(device_id, 0)
    if count < REBOOT_RETRY_LIMIT:
        reboot_retry_counters[device_id] = count + 1
        await asyncio.sleep(REBOOT_RETRY_DELAY)
        try:
            if device_command_bus is not None:
                await device_command_bus.publish_command(
                    device_id=device_id,
                    command="REINICIAR",
                    payload=payload,
                )
            else:
                await tablet_ws_manager.send_to_device(device_id, {"command": "REINICIAR", **payload})
        except Exception as e:
            logging.error("Error reenviando REINICIAR a %s: %s", device_id, e)
    else:
        reboot_retry_counters.pop(device_id, None)
        if pending_queue is not None:
            await pending_queue.set_pending_reboot(device_id, payload)
        logging.error(f"Dispositivo {device_id} falló REINICIAR tras {REBOOT_RETRY_LIMIT} reintentos.")

@app.get("/api/queue/health")
async def queue_health():
    """L1.6/L2: Endpoint de monitoreo de colas de mensajes."""
    stats = {
        "total_connections": len(tablet_ws_manager.active_connections),
        "total_local_queues": len(tablet_ws_manager._message_queues),
        "redis_available": tablet_ws_manager.pending_queue is not None,
        "queues": {},
    }
    # Intentar obtener stats de Redis
    if tablet_ws_manager.pending_queue is not None:
        try:
            redis_stats = await tablet_ws_manager.pending_queue.get_all_stats()
            for device_id, qstats in redis_stats.items():
                stats["queues"][device_id] = {
                    **qstats,
                    "online": device_id in tablet_ws_manager.device_map,
                }
        except Exception:
            pass
    # Fallback: stats de colas locales
    if not stats["queues"]:
        for device_id, queue in tablet_ws_manager._message_queues.items():
            stats["queues"][device_id] = {
                "pending": queue.qsize(),
                "online": device_id in tablet_ws_manager.device_map,
            }
    return stats


@app.websocket("/ws/tablet")
async def websocket_tablet(websocket: WebSocket):
    await tablet_ws_manager.connect(websocket)
    if websocket.client_state.name != "CONNECTED":
        return
    ws_id = id(websocket)
    asyncio.create_task(tablet_ws_manager.start_ping_loop(websocket))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                import json
                msg = json.loads(data)
            except Exception:
                continue

            if msg.get("type") == "pong":
                event = tablet_ws_manager.pending_pong.get(ws_id)
                if event:
                    event.set()
                continue
            
            # Manejar PLAYING_NOW - contenido que se está reproduciendo
            if msg.get("type") == "PLAYING_NOW":
                device_id = msg.get("device_id") or tablet_ws_manager.get_device_id(websocket)
                content = msg.get("content")
                logger.info(f"[PLAYING_NOW] Recibido de {device_id}: {content}")
                if device_id and device_state_store is not None and content:
                    try:
                        await device_state_store.update_playing_content(device_id, content)
                    except Exception as e:
                        logger.error(f"[PLAYING_NOW] Error guardando contenido: {e}")
                continue
            
            device_id = msg.get("device_id") or tablet_ws_manager.get_device_id(websocket)
            if device_id and device_state_store is not None:
                try:
                    dt = tablet_ws_manager.device_types.get(device_id)
                    await device_state_store.upsert_heartbeat(device_id=device_id, device_type=dt)
                except Exception:
                    pass
            try:
                await process_sync_confirmation(websocket, msg)
            except Exception as e:
                logging.error(f"Error procesando mensaje de confirmación: {e}")
    except WebSocketDisconnect:
        await tablet_ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[WebSocket] Error inesperado en endpoint: {e}")
        await tablet_ws_manager.disconnect(websocket)

@app.get("/api/queue-status/{device_id}")
async def queue_status(device_id: str):
    if pending_queue is None:
        raise HTTPException(status_code=503, detail="Redis queue not available")
    try:
        queue_stats = await pending_queue.get_queue_size(device_id)
        dlq_size = await pending_queue.get_dlq_size(device_id)
        pending_sync = await pending_queue.has_pending_sync(device_id)
        pending_reboot = await pending_queue.has_pending_reboot(device_id)
        return {
            "device_id": device_id,
            "pending": queue_stats["pending"],
            "inflight": queue_stats["inflight"],
            "total": queue_stats["total"],
            "dlq": dlq_size,
            "pending_sync": pending_sync,
            "pending_reboot": pending_reboot,
        }
    except Exception as e:
        logger.error(f"Error obteniendo queue status para {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {e}")

@app.post("/ws/broadcast")
async def ws_broadcast(message: dict):
    if tablet_ws_manager is None:
        raise HTTPException(status_code=503, detail="WebSocket manager not available")
    msg_type = message.get("type", "")
    if msg_type == "BANNER_EXPIRED":
        logger.info(f"[ws/broadcast] BANNER_EXPIRED: banner_id={message.get('banner_id')} titulo={message.get('titulo')}")
        await tablet_ws_manager.broadcast(message)
        return {"success": True, "forwarded": len(tablet_ws_manager.active_connections)}
    logger.warning(f"[ws/broadcast] Unknown message type: {msg_type}")
    raise HTTPException(status_code=400, detail=f"Unknown message type: {msg_type}")

@app.post("/api/reproducciones/progreso")
async def recibir_progreso_reproduccion(body: PlaybackProgressRequest):
    global reproducciones_redis
    try:
        if reproducciones_redis is not None:
            import json
            item = body.model_dump()
            item["_ts"] = datetime.now(timezone.utc).isoformat()
            if device_state_store is not None:
                tipo_disp = await device_state_store.get_device_type(body.dispositivo_id)
                item["tipo_dispositivo"] = tipo_disp or "verificador"
            else:
                item["tipo_dispositivo"] = "verificador"
            await reproducciones_redis.rpush("reproducciones:pending", json.dumps(item))
            await reproducciones_redis.expire("reproducciones:pending", 28800)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error guardando progreso reproducción: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/reproducciones/pendientes")
async def obtener_reproducciones_pendientes():
    global reproducciones_redis
    if reproducciones_redis is None:
        return {"eventos": []}
    try:
        import json
        items = await reproducciones_redis.lrange("reproducciones:pending", 0, -1)
        eventos = [json.loads(i) for i in items]
        return {"eventos": eventos}
    except Exception as e:
        logger.error(f"Error leyendo reproducciones pendientes: {e}")
        return {"eventos": []}


app.include_router(consultas)
app.include_router(publicidad)