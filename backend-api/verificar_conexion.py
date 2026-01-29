"""
Verificar exactamente a qué base de datos estamos conectados
"""

from app.database import SessionLocal, SessionLocalERP
from sqlalchemy import text


def verificar_bd(db, nombre):
    """Muestra información de la conexión"""
    print(f"\n{'='*80}")
    print(f"VERIFICANDO: {nombre}")
    print(f"{'='*80}")
    
    try:
        # Ver nombre de la BD actual
        resultado = db.execute(text("SELECT DB_NAME() as base_datos_actual"))
        bd_actual = resultado.fetchone()[0]
        print(f"✅ Base de datos actual: {bd_actual}")
        
        # Ver usuario actual
        resultado = db.execute(text("SELECT SUSER_NAME() as usuario_actual"))
        usuario = resultado.fetchone()[0]
        print(f"✅ Usuario conectado: {usuario}")
        
        # Ver servidor
        resultado = db.execute(text("SELECT @@SERVERNAME as servidor"))
        servidor = resultado.fetchone()[0]
        print(f"✅ Servidor: {servidor}")
        
        # Intentar contar tablas de forma simple
        resultado = db.execute(text("SELECT COUNT(*) FROM sys.tables"))
        cantidad_tablas = resultado.fetchone()[0]
        print(f"✅ Cantidad de tablas en esta BD: {cantidad_tablas}")
        
        # Si hay tablas, listarlas
        if cantidad_tablas > 0:
            print(f"\n📋 Primeras 20 tablas:")
            resultado = db.execute(text("""
                SELECT TOP 20
                    SCHEMA_NAME(schema_id) as SchemaName,
                    name as TableName
                FROM sys.tables
                ORDER BY name
            """))
            tablas = resultado.fetchall()
            
            for schema, tabla in tablas:
                print(f"   - {schema}.{tabla}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("\n" + "🔍" * 40)
    print("VERIFICANDO CONEXIONES A BASES DE DATOS")
    print("🔍" * 40)
    
    db = SessionLocal()
    db_erp = SessionLocalERP()
    
    try:
        verificar_bd(db, "BD TRANSACCIONAL")
        verificar_bd(db_erp, "BD ERP_POS_CENTRAL")
        
    finally:
        db.close()
        db_erp.close()
    
    print("\n" + "="*80)
    print("✅ VERIFICACIÓN COMPLETADA")
    print("="*80)


if __name__ == "__main__":
    main()