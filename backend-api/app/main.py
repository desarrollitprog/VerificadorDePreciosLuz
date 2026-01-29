
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from . import models, database, schemas
from .routes import consultas, publicidad

models.Base.metadata.create_all(bind=database.engine)

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

# Paso extra: Calcular el IVA si corresponde

# Solo calcular el IVA incluido en el precio base (Bs)
def calcular_iva_incluido_bs(db: Session, db_erp: Session, producto, detalle, pvp_base):
    """
    Busca la tasa de impuesto asociada y calcula el IVA incluido en el precio base (Bs),
    siempre que exista relación activa y precio base.
    """
    # Buscar relación activa en ProductosXImpuestos
    rel = db.query(models.ProductosXImpuestos).filter(
        models.ProductosXImpuestos.IdProducto == producto.IdProducto,
        models.ProductosXImpuestos.IndActivo == 1
    ).first()
    if not rel:
        return None, None
    id_tasa = rel.IdTasaImpuesto
    # Buscar la tasa en la base ERP
    from .models import TasaImpuesto
    tasa_obj = db_erp.query(TasaImpuesto).filter(TasaImpuesto.IdTasaImpuesto == id_tasa).first()
    if not tasa_obj or pvp_base is None:
        return id_tasa, None
    tasa = float(tasa_obj.Tasa)
    # IVA incluido en el precio base (Bs):
    iva_incluido = round((pvp_base * tasa) / (100 + tasa), 2)
    return id_tasa, iva_incluido

# Paso 4: Armar la respuesta final (ahora incluye IVA)
def armar_respuesta(producto, precio, oferta, detalle, db, db_erp):
    """Arma el diccionario de respuesta según si hay oferta vigente o no, e incluye IVA solo en el monto base (Bs)."""
    oferta_vigente = detalle is not None
    pvp_base = float(precio.PVPBase) if precio and precio.PVPBase is not None else None
    pvp_conversion = float(precio.PVPConversion) if precio and precio.PVPConversion is not None else None
    pvp_oferta = float(oferta.PvpOferta) if oferta and oferta.PvpOferta is not None else None
    pvp_base_oferta = float(oferta.PvpBaseOferta) if oferta and oferta.PvpBaseOferta is not None else None
    # Solo calcular IVA incluido en el precio base (Bs)
    id_tasa, iva_incluido_bs = calcular_iva_incluido_bs(db, db_erp, producto, detalle, pvp_base)
    return {
        "id_producto": producto.IdProducto,
        "sku": producto.SKU,
        "nombre": producto.Nombre,
        "pvp_base": None if oferta_vigente else pvp_base,
        "pvp_conversion": None if oferta_vigente else pvp_conversion,
        "ind_iva": int(precio.IndIVA) if precio and precio.IndIVA is not None else None,
        "pvp_oferta": pvp_oferta if oferta_vigente else None,
        "pvp_base_oferta": pvp_base_oferta if oferta_vigente else None,
        "id_empaque": int(precio.IdEmpaque) if precio and precio.IdEmpaque is not None else None,
        "id_tasa_impuesto": id_tasa,
        "iva_incluido_bs": iva_incluido_bs,
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