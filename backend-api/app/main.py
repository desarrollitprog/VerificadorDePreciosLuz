
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from . import models, database, schemas
from .routes import consultas, publicidad

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Verificador de Precios Luz - Backend")

@app.get("/ping")
def ping():
    return {"status": "Conexion Exitosa"}

# Paso 1: Buscar producto y precio base
def buscar_producto_y_precio(db: Session, codigo_barras: str):
    """Busca el producto y su precio base por código de barras."""
    resultado = (
        db.query(models.Producto, models.ProductoPrecio)
        .join(models.ProductoPrecio, models.Producto.IdProducto == models.ProductoPrecio.IdProducto)
        .filter(models.Producto.SKU == codigo_barras, models.ProductoPrecio.CostoBase > 0)
        .first()
    )
    return resultado

# Paso 2: Buscar oferta asociada
def buscar_oferta(db: Session, id_producto: int):
    """Busca la oferta asociada al producto."""
    return db.query(models.ProductoOferta).filter(models.ProductoOferta.IdProducto == id_producto).first()

# Paso 3: Buscar detalle de oferta vigente
def buscar_detalle_oferta_vigente(db: Session, precio, now):
    """Busca si existe un detalle de oferta vigente para el empaque del producto."""
    sub_ofertas_vigentes = (
        db.query(models.OfertasxProductos.IdOfertaxProducto)
        .filter(
            models.OfertasxProductos.IndExpirado == 0,
            models.OfertasxProductos.FechaInicio <= now,
            or_(
                models.OfertasxProductos.FechaFin == None,
                models.OfertasxProductos.FechaFin >= now,
            ),
        )
        .subquery()
    )
    sub_ofertas_sucursal = (
        db.query(models.OfertasxProductosxSucursal.IdOfertaxProductoxSucursal)
        .filter(models.OfertasxProductosxSucursal.IdOfertaxProducto.in_(sub_ofertas_vigentes.select()))
        .subquery()
    )
    detalle = (
        db.query(models.OfertasxProductosxSucursalesDetalles)
        .filter(
            models.OfertasxProductosxSucursalesDetalles.IdEmpaque == precio.IdEmpaque,
            models.OfertasxProductosxSucursalesDetalles.IdOfertaxProductoxSucursal.in_(sub_ofertas_sucursal.select()),
        )
        .first()
    )
    return detalle

# Paso 4: Armar la respuesta final


# Paso 4: Armar la respuesta final (ahora incluye IVA)
def armar_respuesta(producto, precio, oferta, detalle, db, db_erp):
    """Arma el diccionario de respuesta según si hay oferta vigente o no, e incluye IVA solo en el monto base (Bs)."""
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

# Endpoint principal usando funciones auxiliares

@app.get("/consultar/{codigo_barras}", response_model=schemas.ProductoResponse)
def obtener_precio(codigo_barras: str, db: Session = Depends(database.get_db)):
    # 1. Buscar producto y precio base
    resultado = buscar_producto_y_precio(db, codigo_barras)
    if not resultado:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto, precio = resultado

    # 2. Buscar oferta asociada
    oferta = buscar_oferta(db, producto.IdProducto)

    # 3. Buscar detalle de oferta vigente
    now = datetime.now()
    detalle = buscar_detalle_oferta_vigente(db, precio, now)

    # 4. Crear sesión a la base ERP para consulta de tasas
    db_erp = next(database.get_db_erp())

    # 5. Armar respuesta final (incluye cálculo de IVA)
    return armar_respuesta(producto, precio, oferta, detalle, db, db_erp)

app.include_router(consultas)
app.include_router(publicidad)