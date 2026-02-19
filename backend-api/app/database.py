import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import asyncio
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


def _build_async_connection_string(
    server: str,
    database: str,
    user: str,
    password: str,
    port: str = "1433",
    driver: str = "ODBC Driver 18 for SQL Server"
) -> str:
    """
    Construye la cadena de conexión asíncrona para SQL Server usando aioodbc.
    """
    return (
        f"mssql+aioodbc://{user}:{password}@{server},{port}/{database}?"
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

async_engine = create_async_engine(
    _build_async_connection_string(
        server=DB_SERVER,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        driver=DB_DRIVER,
    ),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependencia para obtener la sesión async
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


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


# Crear engine async para BD ERP
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
engine_erp = create_async_engine(
    f"mssql+aioodbc://{DB_USER_ERP}:{DB_PASSWORD_ERP}@{DB_SERVER_ERP},{DB_PORT_ERP}/{DB_NAME_ERP}?driver={DB_DRIVER_ERP.replace(' ', '+')}&Encrypt=yes&TrustServerCertificate=yes",
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# Session maker async para BD ERP
AsyncSessionLocalERP = sessionmaker(
    bind=engine_erp,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base declarativa para BD ERP
BaseERP = declarative_base()

# Dependencia async para obtener la sesión ERP
async def get_db_erp():
    async with AsyncSessionLocalERP() as session:
        yield session

# ============================================================================
# CONEXIÓN 3: BASE DE DATOS PUBLICIDAD SECUNDARIA
# ============================================================================

# Variables de entorno para BD Publicidad Secundaria
DB_USER_PUBLICIDAD = _required("DB_USER_PUBLICIDAD")
DB_PASSWORD_PUBLICIDAD = _required("DB_PASSWORD_PUBLICIDAD")
DB_SERVER_PUBLICIDAD = _required("DB_SERVER_PUBLICIDAD")
DB_NAME_PUBLICIDAD = _required("DB_NAME_PUBLICIDAD")
DB_PORT_PUBLICIDAD = os.getenv("DB_PORT_PUBLICIDAD", "1433")
DB_DRIVER_PUBLICIDAD = os.getenv("DB_DRIVER_PUBLICIDAD", "ODBC Driver 18 for SQL Server")

async_engine_publicidad = create_async_engine(
    _build_async_connection_string(
        server=DB_SERVER_PUBLICIDAD,
        database=DB_NAME_PUBLICIDAD,
        user=DB_USER_PUBLICIDAD,
        password=DB_PASSWORD_PUBLICIDAD,
        port=DB_PORT_PUBLICIDAD,
        driver=DB_DRIVER_PUBLICIDAD,
    ),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
)
AsyncSessionLocalPublicidad = sessionmaker(
    bind=async_engine_publicidad,
    class_=AsyncSession,
    expire_on_commit=False
)

BasePublicidad = declarative_base()

# Dependencia para obtener la sesión async de publicidad secundaria
async def get_db_publicidad():
    async with AsyncSessionLocalPublicidad() as session:
        yield session


# ============================================================================
# VERIFICACIÓN DE CONEXIONES (Opcional - para debug)
# ============================================================================
async def test_connections_async():
    print("🔍 Verificando conexiones async a bases de datos...")
    # Test conexión Transaccional
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        print("✅ Conexión async a BD Transaccional: OK")
    except Exception as e:
        print(f"❌ Conexión async a BD Transaccional: FALLO")
        print(f"   Error: {e}")
    # Test conexión ERP
    try:
        async with AsyncSessionLocalERP() as db_erp:
            await db_erp.execute(text("SELECT 1"))
        print("✅ Conexión async a BD ERP_POS_CENTRAL: OK")
    except Exception as e:
        print(f"❌ Conexión async a BD ERP_POS_CENTRAL: FALLO")
        print(f"   Error: {e}")
    # Test conexión Publicidad Secundaria
    try:
        async with AsyncSessionLocalPublicidad() as db_publicidad:
            await db_publicidad.execute(text("SELECT 1"))
        print("✅ Conexión async a BD PUBLICIDAD SECUNDARIA: OK")
    except Exception as e:
        print(f"❌ Conexión async a BD PUBLICIDAD SECUNDARIA: FALLO")
        print(f"   Error: {e}")


# ============================================================================
# EJECUCIÓN DE PRUEBA (Descomentar para probar)
# ============================================================================

#if __name__ == "__main__":
  #  asyncio.run(test_connections_async())