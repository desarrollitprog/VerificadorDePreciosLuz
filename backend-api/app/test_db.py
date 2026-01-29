# app/test_db.py
import sys
import os
from datetime import datetime

# Agregar la carpeta padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import test_connections, SessionLocal
from app import models


def probar_consulta(sku: str):
    db = SessionLocal()
    try:
        producto = (
            db.query(models.Producto)
            .filter(models.Producto.SKU == sku)
            .first()
        )

        if not producto:
            print("Producto no encontrado")
            return

        precio = (
            db.query(models.ProductoPrecio)
            .filter(models.ProductoPrecio.IdProducto == producto.IdProducto)
            .first()
        )

        oferta = (
            db.query(models.ProductoOferta)
            .filter(models.ProductoOferta.IdProducto == producto.IdProducto)
            .first()
        )

        oferta_vigente = False
        if oferta and oferta.IdEmpaque is not None:
            detalle = (
                db.query(models.OfertasxProductosxSucursalesDetalles)
                .filter(
                    models.OfertasxProductosxSucursalesDetalles.IdEmpaque
                    == oferta.IdEmpaque
                )
                .first()
            )
            if detalle:
                oferta_sucursal = (
                    db.query(models.OfertasxProductosxSucursal)
                    .filter(
                        models.OfertasxProductosxSucursal.IdOfertaxProductoxSucursal
                        == detalle.IdOfertaxProductoxSucursal
                    )
                    .first()
                )
                if oferta_sucursal:
                    oferta_estado = (
                        db.query(models.OfertasxProductos)
                        .filter(
                            models.OfertasxProductos.IdOfertaxProducto
                            == oferta_sucursal.IdOfertaxProducto
                        )
                        .first()
                    )
                    if oferta_estado:
                        now = datetime.now()
                        fecha_ok = True
                        if oferta_estado.FechaInicio and now < oferta_estado.FechaInicio:
                            fecha_ok = False
                        if oferta_estado.FechaFin and now > oferta_estado.FechaFin:
                            fecha_ok = False

                        estado_ok = (
                            oferta_estado.IndProcesado == 1
                            and oferta_estado.IndExpirado == 0
                        )

                        oferta_vigente = estado_ok and fecha_ok

        pvp_base = float(precio.PVPBase) if precio and precio.PVPBase is not None else None
        pvp_conversion = (
            float(precio.PVPConversion)
            if precio and precio.PVPConversion is not None
            else None
        )
        pvp_oferta = (
            float(oferta.PvpOferta) if oferta and oferta.PvpOferta is not None else None
        )
        pvp_base_oferta = (
            float(oferta.PvpBaseOferta)
            if oferta and oferta.PvpBaseOferta is not None
            else None
        )

        resultado = {
            "id_producto": producto.IdProducto,
            "sku": producto.SKU,
            "nombre": producto.Nombre,
            "pvp_base": None if oferta_vigente else pvp_base,
            "pvp_conversion": None if oferta_vigente else pvp_conversion,
            "ind_iva": int(precio.IndIVA) if precio and precio.IndIVA is not None else None,
            "pvp_oferta": pvp_oferta if oferta_vigente else None,
            "pvp_base_oferta": pvp_base_oferta if oferta_vigente else None,
            "id_empaque": int(oferta.IdEmpaque) if oferta and oferta.IdEmpaque is not None else None,
            "oferta_vigente": oferta_vigente,
        }

        print(resultado)
    finally:
        db.close()


if __name__ == "__main__":
    test_connections()
    sku = os.getenv("TEST_SKU")
    if not sku:
        print("Configura la variable de entorno TEST_SKU con un SKU válido para probar.")
    else:
        probar_consulta(sku)