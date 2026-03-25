from __future__ import annotations
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
import asyncio
import logging
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
from . import database, models, schemas
from .routes import consultas, publicidad
from .services import DeviceCommandBus, DeviceStateStore
from .database import get_db_publicidad
from .models.publicidad import Publicidad


def get_venezuela_now():
    return datetime.now(timezone(timedelta(hours=-4))).replace(tzinfo=None)

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

# Endpoint para consultar el estado de los dispositivos
@app.get("/devices/status")
async def get_devices_status():
    if device_state_store is None:
        raise HTTPException(status_code=503, detail="Estado de dispositivos no inicializado")
    status = await device_state_store.get_all_status()
    return status


@app.get("/ping")
async def ping(device_id: str | None = None):
    if device_id and device_state_store is not None:
        await device_state_store.upsert_heartbeat(device_id=device_id)
    return {"status": "Conexion Exitosa"}


banner_check_task: asyncio.Task | None = None
notified_banners_start: set[int] = set()
notified_banners_end: set[int] = set()

BANNER_CHECK_INTERVAL = 20 * 60  # 20 minutos en segundos


async def _check_banners_starting():
    while True:
        try:
            await asyncio.sleep(BANNER_CHECK_INTERVAL)
            await _notify_banners_started()
            await _notify_banners_ended()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error en task de verificación de banners: %s", e)


async def _notify_banners_started():
    try:
        async for db in get_db_publicidad():
            now = get_venezuela_now()
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
            now = get_venezuela_now()
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
        await tablet_ws_manager.broadcast(banner_info)
        logger.info(f"Broadcast {command}: {banner.titulo}")


@app.on_event("startup")
async def start_device_monitor():
    global device_state_store, device_command_bus, device_bus_listener_task, banner_check_task
    try:
        device_state_store = await DeviceStateStore.create()
        logger.info("DeviceStateStore inicializado con Redis")
    except Exception as e:
        logger.error("No se pudo inicializar DeviceStateStore: %s", e)

    try:
        device_command_bus = await DeviceCommandBus.create()
        device_bus_listener_task = asyncio.create_task(_start_device_bus_listener())
        logger.info("DeviceCommandBus inicializado con Redis pub/sub")
    except Exception as e:
        logger.error("No se pudo inicializar DeviceCommandBus: %s", e)

    banner_check_task = asyncio.create_task(_check_banners_starting())
    logger.info("Banner check task iniciada")


@app.on_event("shutdown")
async def shutdown_device_state_store():
    global device_state_store, device_command_bus, device_bus_listener_task, banner_check_task
    if banner_check_task is not None:
        banner_check_task.cancel()
        banner_check_task = None

    if device_bus_listener_task is not None:
        device_bus_listener_task.cancel()
        device_bus_listener_task = None

    if device_command_bus is not None:
        await device_command_bus.close()
        device_command_bus = None

    if device_state_store is not None:
        await device_state_store.close()
        device_state_store = None


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
# WebSocket manager para tabletas

# --- Reintentos automáticos y mapeo device_id <-> WebSocket ---
RETRY_LIMIT = 3
RETRY_DELAY = 30  # segundos
sync_retry_counters = {}  # device_id -> intentos
SYNC_ACK_TIMEOUT = 20  # segundos para esperar confirmación de recepción
SYNC_SEQUENCE_LOCK = asyncio.Lock()
sync_ack_waiters: dict[str, asyncio.Event] = {}
sync_ack_payloads: dict[str, dict] = {}

# --- Configuración de Ping WebSocket ---
WEBSOCKET_PING_INTERVAL = int(os.getenv("WEBSOCKET_PING_INTERVAL", "30"))
WEBSOCKET_PONG_TIMEOUT = int(os.getenv("WEBSOCKET_PONG_TIMEOUT", "10"))

class TabletWebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.device_map: dict[str, WebSocket] = {}  # device_id -> WebSocket
        self.ping_tasks: dict[int, asyncio.Task] = {}  # id(websocket) -> Task

    async def start_ping_loop(self, websocket: WebSocket):
        ws_id = id(websocket)
        
        async def ping_sender():
            while True:
                try:
                    await asyncio.sleep(WEBSOCKET_PING_INTERVAL)
                    
                    device_id = self.get_device_id(websocket)
                    if device_id and device_state_store is not None:
                        await device_state_store.upsert_heartbeat(device_id=device_id)
                    
                    try:
                        import time
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": int(time.time())
                        })
                        
                        try:
                            msg = await asyncio.wait_for(
                                websocket.receive_text(),
                                timeout=WEBSOCKET_PONG_TIMEOUT
                            )
                            import json
                            data = json.loads(msg)
                            if data.get("type") != "pong":
                                raise ValueError("No es un mensaje pong")
                        except asyncio.TimeoutError:
                            logger.warning(
                                f"[Ping] No se recibió pong del dispositivo {device_id or 'desconocido'} "
                                f"en {WEBSOCKET_PONG_TIMEOUT}s. Cerrando conexión."
                            )
                            try:
                                await websocket.close(code=1001, reason="Ping timeout")
                            except Exception:
                                pass
                            return
                        except (json.JSONDecodeError, ValueError, Exception) as e:
                            if "Ping timeout" not in str(e):
                                logger.warning(f"[Ping] Respuesta inválida: {e}")
                            raise
                    except Exception as e:
                        if "code=1001" in str(e) or "WebSocket is not connected" in str(e):
                            return
                        if "no Frame" in str(e) or "Connection closed" in str(e):
                            return
                        logger.error(f"[Ping] Error enviando ping: {e}")
                        return
                        
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
        await websocket.accept()
        ws_id = id(websocket)
        
        if ws_id in self.ping_tasks:
            self.ping_tasks[ws_id].cancel()
            del self.ping_tasks[ws_id]
        
        try:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=10)
            import json
            msg = json.loads(data)
            device_id = msg.get("device_id")
            if device_id:
                self.device_map[device_id] = websocket
                if device_state_store is not None:
                    await device_state_store.upsert_heartbeat(device_id=device_id)
        except Exception:
            pass
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.cancel_ping_task(websocket)
        
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for k, v in list(self.device_map.items()):
            if v == websocket:
                if device_state_store is not None:
                    asyncio.create_task(device_state_store.mark_offline(k))
                del self.device_map[k]

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

    async def send_to_device(self, device_id: str, message: dict):
        ws = self.device_map.get(device_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def send_to_websocket(self, websocket: WebSocket, message: dict) -> bool:
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            return False

    def get_device_id(self, websocket: WebSocket) -> str | None:
        for device_id, ws in self.device_map.items():
            if ws == websocket:
                return device_id
        return None

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
    if command == "WIPE_AND_RESYNC":
        await tablet_ws_manager.send_to_device(device_id, {"command": "WIPE_AND_RESYNC"})


async def _on_bus_confirmation(device_id: str, command: str, status: str, reason: str):
    if not device_id:
        return
    if command != "WIPE_AND_RESYNC":
        return
    await _apply_sync_confirmation(device_id=device_id, status=status, reason=reason)


async def _start_device_bus_listener():
    if device_command_bus is None:
        return
    try:
        await device_command_bus.subscribe_forever(
            on_command=_on_bus_command,
            on_confirmation=_on_bus_confirmation,
        )
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Error en listener de DeviceCommandBus: %s", e)


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
            "failed": 0,
            "details": [],
        }

    sent = 0
    confirmed = 0
    details = []

    if progress_hook:
        await progress_hook(
            {
                "total": len(target_device_ids),
                "sent": sent,
                "confirmed": confirmed,
                "failed": len(target_device_ids) - confirmed,
                "details": list(details),
            }
        )

    for device_id in target_device_ids:
        ack_key = f"device:{device_id}"
        waiter = asyncio.Event()
        sync_ack_waiters[ack_key] = waiter
        sync_ack_payloads.pop(ack_key, None)

        send_ok = False
        try:
            if device_command_bus is not None:
                await device_command_bus.publish_command(
                    device_id=device_id,
                    command="WIPE_AND_RESYNC",
                    payload={},
                )
                send_ok = True
            else:
                await tablet_ws_manager.send_to_device(device_id, {"command": "WIPE_AND_RESYNC"})
                send_ok = True
        except Exception:
            send_ok = False

        if not send_ok:
            reason = "No se pudo enviar comando por WebSocket"
            asyncio.create_task(notify_dashboard_sync_failure(device_id, reason))
            sync_ack_waiters.pop(ack_key, None)
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
                        "failed": len(target_device_ids) - confirmed,
                        "details": list(details),
                    }
                )
            continue

        sent += 1

        try:
            await asyncio.wait_for(waiter.wait(), timeout=SYNC_ACK_TIMEOUT)
            ack = sync_ack_payloads.pop(ack_key, {})
            status = str(ack.get("status", "")).upper()
            ok = status in ("RECEIVED", "SUCCESS", "DONE")
            if ok:
                confirmed += 1
            else:
                fail_reason = ack.get("reason", "") or f"Estado no exitoso: {status or 'UNKNOWN'}"
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
        except asyncio.TimeoutError:
            timeout_reason = f"Sin confirmación en {SYNC_ACK_TIMEOUT}s"
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
        finally:
            sync_ack_waiters.pop(ack_key, None)

        if progress_hook:
            await progress_hook(
                {
                    "total": len(target_device_ids),
                    "sent": sent,
                    "confirmed": confirmed,
                    "failed": len(target_device_ids) - confirmed,
                    "details": list(details),
                }
            )
        
        # Delay entre dispositivos para evitar colapsos (2 segundos)
        if len(target_device_ids) > 1:
            await asyncio.sleep(2)

    failed = len(target_device_ids) - confirmed
    return {
        "total": len(target_device_ids),
        "sent": sent,
        "confirmed": confirmed,
        "failed": failed,
        "details": details,
    }


async def process_sync_confirmation(websocket: WebSocket, msg: dict):
    if msg.get("type") != "CONFIRMATION" or msg.get("command") != "WIPE_AND_RESYNC":
        return

    status = str(msg.get("status", "")).upper()
    reason = msg.get("reason", "")
    device_id = msg.get("device_id") or tablet_ws_manager.get_device_id(websocket)
    if not device_id:
        return

    if device_command_bus is not None:
        try:
            await device_command_bus.publish_confirmation(
                device_id=device_id,
                command="WIPE_AND_RESYNC",
                status=status,
                reason=reason,
            )
            return
        except Exception as e:
            logging.error("Error publicando confirmación en bus: %s", e)

    await _apply_sync_confirmation(device_id=device_id, status=status, reason=reason)

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
    # Lanzar reintentos automáticos en background
    asyncio.create_task(retry_sync_with_device(device_id))


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
        logging.error(f"Dispositivo {device_id} falló sincronización tras {RETRY_LIMIT} reintentos.")

@app.websocket("/ws/tablet")
async def websocket_tablet(websocket: WebSocket):
    await tablet_ws_manager.connect(websocket)
    asyncio.create_task(tablet_ws_manager.start_ping_loop(websocket))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                import json
                msg = json.loads(data)
                device_id = msg.get("device_id") or tablet_ws_manager.get_device_id(websocket)
                if device_id and device_state_store is not None:
                    await device_state_store.upsert_heartbeat(device_id=device_id)
                await process_sync_confirmation(websocket, msg)
            except Exception as e:
                logging.error(f"Error procesando mensaje de confirmación: {e}")
    except WebSocketDisconnect:
        tablet_ws_manager.disconnect(websocket)

app.include_router(consultas)
app.include_router(publicidad)