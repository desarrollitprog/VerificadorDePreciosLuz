

from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, database, schemas
from .routes import consultas, publicidad

app = FastAPI(title="Verificador de Precios Luz - Backend")

@app.get("/ping")
async def ping():
    return {"status": "Conexion Exitosa"}

# Paso 1: Buscar producto y precio base (async)
async def buscar_producto_y_precio(db: AsyncSession, codigo_barras: str):
    stmt = select(models.Producto, models.ProductoPrecio).join(
        models.ProductoPrecio, models.Producto.IdProducto == models.ProductoPrecio.IdProducto
    ).where(
        models.Producto.SKU == codigo_barras,
        models.ProductoPrecio.CostoBase > 0
    )
    result = await db.execute(stmt)
    return result.first()

# Paso 2: Buscar oferta asociada (async)
async def buscar_oferta(db: AsyncSession, id_producto: int):
    stmt = select(models.ProductoOferta).where(models.ProductoOferta.IdProducto == id_producto)
    result = await db.execute(stmt)
    return result.scalars().first()

# Paso 3: Buscar detalle de oferta vigente (async)
async def buscar_detalle_oferta_vigente(db: AsyncSession, precio, now):
    sub_ofertas_vigentes = select(models.OfertasxProductos.IdOfertaxProducto).where(
        models.OfertasxProductos.IndExpirado == 0,
        models.OfertasxProductos.FechaInicio <= now,
        or_(
            models.OfertasxProductos.FechaFin == None,
            models.OfertasxProductos.FechaFin >= now,
        ),
    )
    result_vigentes = await db.execute(sub_ofertas_vigentes)
    ids_vigentes = [row[0] for row in result_vigentes.fetchall()]

    sub_ofertas_sucursal = select(models.OfertasxProductosxSucursal.IdOfertaxProductoxSucursal).where(
        models.OfertasxProductosxSucursal.IdOfertaxProducto.in_(ids_vigentes)
    )
    result_sucursal = await db.execute(sub_ofertas_sucursal)
    ids_sucursal = [row[0] for row in result_sucursal.fetchall()]

    stmt_detalle = select(models.OfertasxProductosxSucursalesDetalles).where(
        models.OfertasxProductosxSucursalesDetalles.IdEmpaque == precio.IdEmpaque,
        models.OfertasxProductosxSucursalesDetalles.IdOfertaxProductoxSucursal.in_(ids_sucursal)
    )
    result_detalle = await db.execute(stmt_detalle)
    return result_detalle.scalars().first()

# Paso 4: Armar la respuesta final (igual que antes)
def armar_respuesta(producto, precio, oferta, detalle):
    oferta_vigente = detalle is not None
    pvp_base = float(precio.PVPBase) if precio and precio.PVPBase is not None else None
    pvp_conversion = float(precio.PVPConversion) if precio and precio.PVPConversion is not None else None
    pvp_oferta = float(oferta.PvpOferta) if oferta and oferta.PvpOferta is not None else None
    pvp_base_oferta = float(oferta.PvpBaseOferta) if oferta and oferta.PvpBaseOferta is not None else None
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

# Endpoint principal usando funciones auxiliares async
@app.get("/consultar/{codigo_barras}", response_model=schemas.ProductoResponse)
async def obtener_precio(codigo_barras: str, db: AsyncSession = Depends(database.get_db)):
    resultado = await buscar_producto_y_precio(db, codigo_barras)
    if not resultado:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto, precio = resultado

    oferta = await buscar_oferta(db, producto.IdProducto)
    now = datetime.now()
    detalle = await buscar_detalle_oferta_vigente(db, precio, now)

    # Si tienes una base ERP asíncrona, deberías adaptar también esa conexión
    # db_erp = await get_db_erp() (adaptar si aplica)

    return armar_respuesta(producto, precio, oferta, detalle)

app.include_router(consultas)
app.include_router(publicidad)