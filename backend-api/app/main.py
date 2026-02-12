from __future__ import annotations

from datetime import datetime, timedelta
import asyncio
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import os
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import database, models, schemas
from .routes import consultas, publicidad

app = FastAPI(title="Verificador de Precios Luz - Backend")
logger = logging.getLogger("uvicorn.error")

# Comprimir respuestas grandes para reducir tiempo de descarga
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Servir archivos estáticos (banners)
static_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

DEVICE_LAST_SEEN: dict[str, dict[str, object]] = {}
DEVICE_LOCK = asyncio.Lock()
DISCONNECT_THRESHOLD = timedelta(seconds=360)
CHECK_INTERVAL_SECONDS = 10


@app.get("/ping")
async def ping(device_id: str | None = None):
    if device_id:
        async with DEVICE_LOCK:
            DEVICE_LAST_SEEN[device_id] = {
                "last_seen": datetime.now(),
                "online": True,
            }
    return {"status": "Conexion Exitosa"}


@app.on_event("startup")
async def start_device_monitor():
    asyncio.create_task(monitor_devices())


async def monitor_devices():
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        now = datetime.now()
        async with DEVICE_LOCK:
            for device_id, info in DEVICE_LAST_SEEN.items():
                last_seen = info.get("last_seen")
                online = info.get("online", True)
                if last_seen and online and (now - last_seen) > DISCONNECT_THRESHOLD:
                    info["online"] = False
                    logger.warning("Dispositivo desconectado device_id=%s", device_id)


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
            or_(models.OfertasxProductos.FechaInicio.is_(None), models.OfertasxProductos.FechaInicio <= now),
            or_(models.OfertasxProductos.FechaFin.is_(None), models.OfertasxProductos.FechaFin >= now),
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


from fastapi import Query
from typing import Optional
from dateutil.parser import isoparse

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
    has_more = count == limit
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
@app.get("/consultar/{codigo_barras}", response_model=schemas.ProductoResponse)
async def obtener_precio(
    codigo_barras: str,
    db: AsyncSession = Depends(database.get_db),
    db_erp: AsyncSession = Depends(database.get_db_erp),
):
    resultado = await buscar_producto_y_precio(db, codigo_barras)
    if not resultado:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto, precio = resultado

    oferta = await buscar_oferta(db, producto.IdProducto)
    now = datetime.now()
    detalle = await buscar_detalle_oferta_vigente(db, precio, now)


    tasa_impuesto = await buscar_tasa_impuesto(db, db_erp, producto.IdProducto, precio)

    return armar_respuesta(producto, precio, oferta, detalle, tasa_impuesto)

app.include_router(consultas)
app.include_router(publicidad)