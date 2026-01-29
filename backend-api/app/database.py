import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from sqlalchemy import text  

load_dotenv()


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _required(name: str) -> str:
    """
    Obtiene una variable de entorno requerida.
    Lanza error si no existe.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


def _build_connection_string(
    server: str,
    database: str,
    user: str,
    password: str,
    port: str = "1433",
    driver: str = "ODBC Driver 18 for SQL Server"
) -> str:
    """
    Construye la cadena de conexión para SQL Server.
    Usa cifrado y confía en el certificado del servidor.
    """
    return (
        f"mssql+pyodbc://{user}:{password}@{server},{port}/{database}?"
        f"driver={driver.replace(' ', '+')}&Encrypt=yes&TrustServerCertificate=yes"
    )


# ============================================================================
# CONEXIÓN 1: BASE DE DATOS TRANSACCIONAL (Actual)
# ============================================================================

# Variables de entorno para BD Transaccional
DB_USER = _required("DB_USER")
DB_PASSWORD = _required("DB_PASSWORD")
DB_SERVER = _required("DB_SERVER")
DB_NAME = _required("DB_NAME")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

# Crear engine para BD Transaccional
engine = create_engine(
    _build_connection_string(
        server=DB_SERVER,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        driver=DB_DRIVER
    ),
    pool_pre_ping=True,  # Verifica conexión antes de usar del pool
    pool_recycle=3600,   # Recicla conexiones cada hora
    echo=False           # Cambia a True para debug SQL
)

# Session maker para BD Transaccional
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa para BD Transaccional
Base = declarative_base()


def get_db():
    """
    Generador de sesiones de base de datos Transaccional.
    Uso: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# CONEXIÓN 2: BASE DE DATOS ERP_POS_CENTRAL (Nueva)
# ============================================================================

# Variables de entorno para BD ERP
DB_USER_ERP = _required("DB_USER_ERP")
DB_PASSWORD_ERP = _required("DB_PASSWORD_ERP")
DB_SERVER_ERP = _required("DB_SERVER_ERP")
DB_NAME_ERP = _required("DB_NAME_ERP")
DB_PORT_ERP = os.getenv("DB_PORT_ERP", "1433")
DB_DRIVER_ERP = os.getenv("DB_DRIVER_ERP", "ODBC Driver 18 for SQL Server")

# Crear engine para BD ERP
engine_erp = create_engine(
    _build_connection_string(
        server=DB_SERVER_ERP,
        database=DB_NAME_ERP,
        user=DB_USER_ERP,
        password=DB_PASSWORD_ERP,
        port=DB_PORT_ERP,
        driver=DB_DRIVER_ERP
    ),
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# Session maker para BD ERP
SessionLocalERP = sessionmaker(autocommit=False, autoflush=False, bind=engine_erp)

# Base declarativa para BD ERP
BaseERP = declarative_base()


def get_db_erp():
    """
    Generador de sesiones de base de datos ERP_POS_CENTRAL.
    Uso: db_erp: Session = Depends(get_db_erp)
    """
    db = SessionLocalERP()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# VERIFICACIÓN DE CONEXIONES (Opcional - para debug)
# ============================================================================

def test_connections():
    """
    Función de utilidad para probar ambas conexiones.
    NO se usa en producción, solo para verificar durante desarrollo.
    """
    print("🔍 Verificando conexiones a bases de datos...")
    
    # Test conexión Transaccional
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print("✅ Conexión a BD Transaccional: OK")
    except Exception as e:
        print(f"❌ Conexión a BD Transaccional: FALLO")
        print(f"   Error: {e}")
    
    # Test conexión ERP
    try:
        db_erp = SessionLocalERP()
        db_erp.execute(text("SELECT 1"))
        db_erp.close()
        print("✅ Conexión a BD ERP_POS_CENTRAL: OK")
    except Exception as e:
        print(f"❌ Conexión a BD ERP_POS_CENTRAL: FALLO")
        print(f"   Error: {e}")


# ============================================================================
# EJECUCIÓN DE PRUEBA (Descomentar para probar)
# ============================================================================

if __name__ == "__main__":
     test_connections()