from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, database
from .routes import consultas, publicidad


models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Verificador de Precios Luz - Backend")


@app.get("/ping")
def ping():
    return {"status": "Conexion Exitosa"}


@app.get("/consultar/{codigo_barras}")
def obtener_precio(codigo_barras: str, db: Session = Depends(database.get_db)):
    producto = (
        db.query(models.Producto)
        .filter(models.Producto.CodigoBarras == codigo_barras)
        .first()
    )

    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return {
        "id": producto.Id,
        "codigo_barras": producto.CodigoBarras,
        "nombre": producto.Nombre,
        "precio": float(producto.Precio),
        "precio_oferta": float(producto.PrecioOferta) if producto.PrecioOferta else None,
    }


app.include_router(consultas)
app.include_router(publicidad)