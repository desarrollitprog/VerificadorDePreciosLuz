import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

def _required(name: str) -> str:
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
    return (
        f"mssql+aioodbc://{user}:{password}@{server},{port}/{database}?"
        f"driver={driver.replace(' ', '+')}&Encrypt=yes&TrustServerCertificate=yes&MARS_Connection=yes"
    )

# Conexión a la base de datos de usuarios_dashboard
DB_USER_USUARIOS = _required("DB_USER_USUARIOS")
DB_PASSWORD_USUARIOS = _required("DB_PASSWORD_USUARIOS")
DB_SERVER_USUARIOS = _required("DB_SERVER_USUARIOS")
DB_NAME_USUARIOS = _required("DB_NAME_USUARIOS")
DB_PORT_USUARIOS = os.getenv("DB_PORT_USUARIOS", "1433")
DB_DRIVER_USUARIOS = os.getenv("DB_DRIVER_USUARIOS", "ODBC Driver 18 for SQL Server")

engine_usuarios = create_async_engine(
    _build_async_connection_string(
        server=DB_SERVER_USUARIOS,
        database=DB_NAME_USUARIOS,
        user=DB_USER_USUARIOS,
        password=DB_PASSWORD_USUARIOS,
        port=DB_PORT_USUARIOS,
        driver=DB_DRIVER_USUARIOS,
    ),
    echo=False,
)

AsyncSessionLocalUsuarios = sessionmaker(
    bind=engine_usuarios,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db_usuarios():
    async with AsyncSessionLocalUsuarios() as session:
        yield session

Base = declarative_base()