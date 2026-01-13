from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, database
from ..schemas import ProductoResponse

router = APIRouter()

@router.get("/productos", response_model=list[ProductoResponse])
def listar_productos(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    # MSSQL requiere ORDER BY para FETCH/OFFSET; aseguramos límite seguro
    limit = max(1, min(limit or 100, 500))
    productos = (
        db.query(models.Producto)
        .order_by(models.Producto.IdProducto)
        .offset(skip)
        .limit(limit)
        .all()
    )
    # Aquí deberías aplicar la misma lógica que en ProductoResponse para cada producto
    # (puedes importar y reutilizar la función armar_respuesta si es posible)
    from app.main import armar_respuesta, database as main_database
    db_erp = next(main_database.get_db_erp())
    result = []
    for p in productos:
        # Simula los datos mínimos para armar_respuesta (puedes adaptar según tu modelo)
        precio = db.query(models.ProductoPrecio).filter(models.ProductoPrecio.IdProducto == p.IdProducto).first()
        oferta = db.query(models.ProductoOferta).filter(models.ProductoOferta.IdProducto == p.IdProducto).first()
        detalle = None  # Si tienes lógica de oferta vigente, puedes agregarla aquí
        result.append(armar_respuesta(p, precio, oferta, detalle, db, db_erp))
    return result
