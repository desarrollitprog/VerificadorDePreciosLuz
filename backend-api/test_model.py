"""
Script de prueba para verificar que los modelos SQLAlchemy funcionan correctamente.
"""

from datetime import datetime
from sqlalchemy import and_, or_
from app.models import (
    Producto,
    ProductoPrecio,
    ProductoOferta,
    OfertasxProductosxSucursalesDetalles,
    OfertasxProductosxSucursal,
    OfertasxProductos,
    TasaImpuesto,
)
from app.database import SessionLocal, SessionLocalERP


def test_imports():
    """Prueba 1: Verificar que los modelos se importan correctamente"""
    print("=" * 60)
    print("PRUEBA 1: Importación de Modelos")
    print("=" * 60)
    
    modelos = [
        ("Producto", Producto),
        ("ProductoPrecio", ProductoPrecio),
        ("ProductoOferta", ProductoOferta),
        ("TasaImpuesto", TasaImpuesto)
    ]
    
    for nombre, modelo in modelos:
        try:
            print(f"✅ {nombre:20} → Tabla: {modelo.__tablename__:30} Schema: {modelo.__table_args__.get('schema', 'dbo')}")
        except Exception as e:
            print(f"❌ {nombre}: Error - {e}")
    
    print()


def test_query_producto(sku_prueba: str):
    """Prueba 2: Consultar un producto de la BD"""
    print("=" * 60)
    print("PRUEBA 2: Consultar Productos")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Contar productos
        count = db.query(Producto).count()
        print(f"📊 Total de productos en BD: {count}")

        producto = (
            db.query(Producto)
            .filter(Producto.SKU == sku_prueba)
            .first()
        )
        if producto:
            print(f"\n✅ Producto encontrado por SKU:")
            print(f"   IdProducto: {producto.IdProducto}")
            print(f"   SKU: {producto.SKU}")
            print(f"   Nombre: {producto.Nombre}")
        else:
            print("⚠️  Producto no encontrado con el SKU dado")
            
    except Exception as e:
        print(f"❌ Error al consultar productos: {e}")
    finally:
        db.close()
    
    print()


def test_query_precio(sku_prueba: str):
    """Prueba 3: Consultar precios"""
    print("=" * 60)
    print("PRUEBA 3: Consultar Precios")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Contar precios
        count = db.query(ProductoPrecio).count()
        print(f"📊 Total de precios en BD: {count}")

        precio = (
            db.query(ProductoPrecio)
            .join(Producto, Producto.IdProducto == ProductoPrecio.IdProducto)
            .filter(
                Producto.SKU == sku_prueba,
                ProductoPrecio.CostoBase > 0,
            )
            .first()
        )
        if precio:
            print(f"\n✅ Precio encontrado por SKU:")
            print(f"   IdProductosXEmpaqueXSucursal: {precio.IdProductosXEmpaqueXSucursal}")
            print(f"   IdProducto: {precio.IdProducto}")
            print(f"   IdEmpaque: {precio.IdEmpaque}")
            print(f"   CostoBase: {precio.CostoBase}")
            print(f"   PVPBase (Bs): {precio.PVPBase}")
            print(f"   PVPConversion ($): {precio.PVPConversion}")
            print(f"   IndIVA: {precio.IndIVA}")
        else:
            print("⚠️  No hay precios para el SKU dado")
            
    except Exception as e:
        print(f"❌ Error al consultar precios: {e}")
    finally:
        db.close()
    
    print()


def test_query_oferta(sku_prueba: str):
    """Prueba 4: Consultar ofertas (tabla ProductosOfertasxSucursal)"""
    print("=" * 60)
    print("PRUEBA 4: Consultar Ofertas Activas")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Contar ofertas
        count = db.query(ProductoOferta).count()
        print(f"📊 Total de ofertas en BD: {count}")

        oferta = (
            db.query(ProductoOferta)
            .join(Producto, Producto.IdProducto == ProductoOferta.IdProducto)
            .filter(Producto.SKU == sku_prueba)
            .first()
        )

        if oferta:
            print(f"\n✅ Oferta encontrada por SKU:")
            print(f"   IdProductoOfertaxSucursal: {oferta.IdProductoOfertaxSucursal}")
            print(f"   IdProducto: {oferta.IdProducto}")
            print(f"   IdEmpaque: {oferta.IdEmpaque}")
            print(f"   PvpBaseOferta (Bs): {oferta.PvpBaseOferta}")
            print(f"   PvpOferta ($): {oferta.PvpOferta}")
            print(f"   IndActivo (IVA): {oferta.IndActivo}")
        else:
            print("⚠️  No hay ofertas para el SKU dado")
            
    except Exception as e:
        print(f"❌ Error al consultar ofertas: {e}")
    finally:
        db.close()
    
    print()


def test_query_tasa_iva():
    """Prueba 5: Consultar tasas de IVA en BD ERP"""
    print("=" * 60)
    print("PRUEBA 5: Consultar Tasas de IVA (BD ERP)")
    print("=" * 60)
    
    db_erp = SessionLocalERP()
    
    try:
        # Contar tasas de IVA
        count = db_erp.query(TasaImpuesto).count()
        print(f"📊 Total de tasas de IVA: {count}")
        
        if count > 0:
            # Obtener todas las tasas
            tasas = db_erp.query(TasaImpuesto).all()
            print(f"\n✅ Tasas de IVA:")
            for tasa in tasas:
                print(f"   ID: {tasa.IdTasaImpuesto} | Tasa: {tasa.Tasa}%")
        else:
            print("⚠️  No hay tasas de IVA en la base de datos")
            
    except Exception as e:
        print(f"❌ Error al consultar tasas de IVA: {e}")
    finally:
        db_erp.close()
    
    print()


def test_join_producto_precio(sku_prueba: str):
    """Prueba 6: JOIN entre Producto y Precio (simulando consulta real)"""
    print("=" * 60)
    print("PRUEBA 6: JOIN Producto + Precio")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Query con JOIN
        resultado = (
            db.query(Producto, ProductoPrecio)
            .join(ProductoPrecio, Producto.IdProducto == ProductoPrecio.IdProducto)
            .filter(Producto.SKU == sku_prueba)
            .first()
        )
        
        if resultado:
            producto, precio = resultado
            print(f"✅ JOIN exitoso por SKU:")
            print(f"\n   📦 Producto:")
            print(f"      SKU: {producto.SKU}")
            print(f"      Nombre: {producto.Nombre}")
            print(f"\n   💰 Precio:")
            print(f"      Bs: {precio.PVPBase}")
            print(f"      $: {precio.PVPConversion}")
            print(f"      IVA ID: {precio.IndIVA}")
        else:
            print("⚠️  No se encontraron resultados para el JOIN")
            
    except Exception as e:
        print(f"❌ Error en JOIN: {e}")
    finally:
        db.close()
    
    print()


def test_buscar_por_codigo_barras(sku_prueba: str):
    """Prueba 7: Buscar producto por SKU (consulta real del endpoint)"""
    print("=" * 60)
    print("PRUEBA 7: Búsqueda por Código de Barras")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        print(f"🔍 Buscando producto con SKU: {sku_prueba}")
        
        # Buscar producto con precio (como lo hará el endpoint real)
        now = datetime.now()
        sub_ofertas_vigentes = (
            db.query(OfertasxProductos.IdOfertaxProducto)
            .filter(
                OfertasxProductos.IndExpirado == 0,
                OfertasxProductos.FechaInicio <= now,
                or_(
                    OfertasxProductos.FechaFin == None,
                    OfertasxProductos.FechaFin >= now,
                ),
            )
            .subquery()
        )

        sub_ofertas_sucursal = (
            db.query(OfertasxProductosxSucursal.IdOfertaxProductoxSucursal)
            .filter(
                OfertasxProductosxSucursal.IdOfertaxProducto.in_(
                    sub_ofertas_vigentes.select()
                )
            )
            .subquery()
        )

        resultado = (
            db.query(Producto, ProductoPrecio, ProductoOferta, OfertasxProductosxSucursalesDetalles)
            .join(ProductoPrecio, Producto.IdProducto == ProductoPrecio.IdProducto)
            .outerjoin(ProductoOferta, Producto.IdProducto == ProductoOferta.IdProducto)
            .outerjoin(
                OfertasxProductosxSucursalesDetalles,
                and_(
                    ProductoPrecio.IdEmpaque
                    == OfertasxProductosxSucursalesDetalles.IdEmpaque,
                    OfertasxProductosxSucursalesDetalles.IdOfertaxProductoxSucursal.in_(
                        sub_ofertas_sucursal.select()
                    ),
                ),
            )
            .filter(
                Producto.SKU == sku_prueba,
                ProductoPrecio.CostoBase > 0,
            )
            .first()
        )
        

        if resultado:
            producto, precio, oferta, detalle = resultado
            print(f"\n✅ Producto encontrado:")
            print(f"   SKU: {producto.SKU}")
            print(f"   Nombre: {producto.Nombre}")
            print(f"   Precio Bs: {precio.PVPBase}")
            print(f"   Precio $: {precio.PVPConversion}")

            print("\n🔎 Debug vigencia:")
            print(f"   IdEmpaque (Precio): {precio.IdEmpaque}")
            print(
                f"   IdOfertaxProductoxSucursal (Detalle): "
                f"{detalle.IdOfertaxProductoxSucursal if detalle else None}"
            )
            print(f"   Now: {now}")

            oferta_vigente = detalle is not None

            if oferta_vigente and oferta:
                print(f"\n   🏷️  Tiene oferta vigente:")
                print(f"      Precio Oferta Bs: {oferta.PvpBaseOferta}")
                print(f"      Precio Oferta $: {oferta.PvpOferta}")
            else:
                print(f"\n   ℹ️  No tiene oferta vigente")

            # Calcular e imprimir el IVA incluido en el precio base (Bs) siempre que exista relación activa
            from app.models import ProductosXImpuestos, TasaImpuesto
            from app.database import SessionLocalERP
            pvp_base = float(precio.PVPBase) if precio and precio.PVPBase is not None else None
            iva_incluido_bs = None
            id_tasa = None
            if pvp_base is not None:
                rel = db.query(ProductosXImpuestos).filter(
                    ProductosXImpuestos.IdProducto == producto.IdProducto,
                    ProductosXImpuestos.IndActivo == 1
                ).first()
                if rel:
                    id_tasa = rel.IdTasaImpuesto
                    db_erp = SessionLocalERP()
                    tasa_obj = db_erp.query(TasaImpuesto).filter(TasaImpuesto.IdTasaImpuesto == id_tasa).first()
                    if tasa_obj:
                        tasa = float(tasa_obj.Tasa)
                        iva_incluido_bs = round((pvp_base * tasa) / (100 + tasa), 2)
                    db_erp.close()
            print(f"\n🧮 IVA incluido en precio base (Bs): {iva_incluido_bs} (Tasa ID: {id_tasa})")
        else:
            print(f"❌ No se encontró el producto")
            
    except Exception as e:
        print(f"❌ Error en búsqueda: {e}")
    finally:
        db.close()
    
    print()


def main():
    """Ejecutar todas las pruebas"""
    print("\n")
    print("🧪" * 30)
    print(" PRUEBAS DE MODELOS SQLALCHEMY ".center(60, "="))
    print("🧪" * 30)
    print("\n")
    
    try:
        sku_prueba = input("Ingresa SKU para pruebas: ").strip()
        if not sku_prueba:
            print("⚠️  Debes ingresar un SKU para ejecutar las pruebas")
            return

        test_imports()
        test_query_producto(sku_prueba)
        test_query_precio(sku_prueba)
        test_query_oferta(sku_prueba)
        test_query_tasa_iva()
        test_join_producto_precio(sku_prueba)
        test_buscar_por_codigo_barras(sku_prueba)
        
        print("=" * 60)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()