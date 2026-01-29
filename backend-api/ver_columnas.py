"""
Script alternativo para ver columnas usando inspección directa de SQLAlchemy
"""

from app.database import engine, engine_erp
from sqlalchemy import inspect, MetaData, Table


def ver_tabla_completa(engine_obj, schema, tabla_nombre):
    """
    Inspecciona una tabla directamente usando SQLAlchemy
    """
    print(f"\n{'='*80}")
    print(f"Tabla: {schema}.{tabla_nombre}")
    print(f"{'='*80}")
    
    try:
        # Crear metadata y cargar la tabla
        metadata = MetaData()
        tabla = Table(tabla_nombre, metadata, autoload_with=engine_obj, schema=schema)
        
        print(f"{'Columna':<30} {'Tipo':<25} {'Nullable':<10} {'PK'}")
        print("-" * 80)
        
        for columna in tabla.columns:
            nombre = columna.name
            tipo = str(columna.type)
            nullable = "YES" if columna.nullable else "NO"
            es_pk = "YES" if columna.primary_key else "NO"
            
            print(f"{nombre:<30} {tipo:<25} {nullable:<10} {es_pk}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "="*80)
    print("INSPECCIONANDO TABLAS DE LA BASE DE DATOS")
    print("="*80)
    
    # Tabla 1: Productos
    ver_tabla_completa(engine, "Transaccional", "Productos")
    
    # Tabla 2: ProductosxEmpaquexSucursal
    ver_tabla_completa(engine, "Transaccional", "ProductosxEmpaquexSucursal")
    
    # Tabla 3: ProductosOfertasxSucursal
    ver_tabla_completa(engine, "Transaccional", "ProductosOfertasxSucursal")
    
    # Tabla 4: TasasImpuestos
    ver_tabla_completa(engine_erp, "ConfiguracionPOS", "TasasImpuestos")
    
    print("\n" + "="*80)
    print("✅ INSPECCIÓN COMPLETADA")
    print("="*80)


if __name__ == "__main__":
    main()