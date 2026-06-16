
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from .. import models, database
from ..schemas import ProductoResponse

router = APIRouter()


@router.get("/productos", response_model=list[ProductoResponse])
async def listar_productos(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(database.get_db),
    db_erp: AsyncSession = Depends(database.get_db_erp),
):
    limit = max(1, min(limit or 100, 500))

    stmt = select(models.Producto).order_by(models.Producto.IdProducto).offset(skip).limit(limit)
    result = await db.execute(stmt)
    productos = result.scalars().all()

    if not productos:
        return []

    ids = [p.IdProducto for p in productos]

    precio_stmt = select(models.ProductoPrecio).where(
        models.ProductoPrecio.IdProducto.in_(ids),
        models.ProductoPrecio.CostoBase > 0,
    )
    precio_result = await db.execute(precio_stmt)
    precios = precio_result.scalars().all()
    precio_map: dict[int, models.ProductoPrecio] = {p.IdProducto: p for p in precios}

    oferta_stmt = select(models.ProductoOferta).where(
        models.ProductoOferta.IdProducto.in_(ids),
        models.ProductoOferta.IndActivo == 1,
    )
    oferta_result = await db.execute(oferta_stmt)
    ofertas = oferta_result.scalars().all()
    oferta_map: dict[int, models.ProductoOferta] = {o.IdProducto: o for o in ofertas}

    responses = []
    for p in productos:
        precio = precio_map.get(p.IdProducto)
        oferta = oferta_map.get(p.IdProducto)

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

        responses.append(ProductoResponse(
            id_producto=p.IdProducto,
            sku=p.SKU,
            nombre=p.Nombre,
            pvp_base=pvp_base,
            pvp_conversion=pvp_conversion,
            pvp_oferta=pvp_oferta,
            pvp_base_oferta=pvp_base_oferta,
            id_empaque=int(precio.IdEmpaque) if precio and precio.IdEmpaque is not None else None,
        ))

    return responses
