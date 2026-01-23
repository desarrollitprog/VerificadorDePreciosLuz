from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas, database

router = APIRouter()


@router.get("/productos", response_model=List[schemas.ProductoSchema])
def listar_productos(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    # MSSQL requiere ORDER BY para FETCH/OFFSET; aseguramos límite seguro
    limit = max(1, min(limit or 100, 500))
    productos = (
        db.query(models.Producto)
        .order_by(models.Producto.Id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": p.Id,
            "codigo_barras": p.CodigoBarras,
            "nombre": p.Nombre,
            "precio": float(p.Precio),
            "precio_oferta": float(p.PrecioOferta) if p.PrecioOferta else None,
        }
        for p in productos
    ]
