
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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

    from app.services.precio_service import armar_respuesta, buscar_tasa_impuesto
    responses = []
    for p in productos:
        # Consultas asíncronas para precio y oferta
        precio_stmt = select(models.ProductoPrecio).where(models.ProductoPrecio.IdProducto == p.IdProducto)
        precio_result = await db.execute(precio_stmt)
        precio = precio_result.scalars().first()

        oferta_stmt = select(models.ProductoOferta).where(models.ProductoOferta.IdProducto == p.IdProducto)
        oferta_result = await db.execute(oferta_stmt)
        oferta = oferta_result.scalars().first()

        detalle = None  # Si tienes lógica de oferta vigente, puedes agregarla aquí
        tasa_impuesto = await buscar_tasa_impuesto(db, db_erp, p.IdProducto, precio)
        responses.append(armar_respuesta(p, precio, oferta, detalle, tasa_impuesto))
    return responses
