import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


DB_USER = _required("DB_USER")
DB_PASSWORD = _required("DB_PASSWORD")
DB_SERVER = _required("DB_SERVER")
DB_NAME = _required("DB_NAME")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")


def _build_connection_string() -> str:
    # Driver 18 con cifrado y certificado confiable para entornos de prueba
    return (
        f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_SERVER},{DB_PORT}/{DB_NAME}?"
        f"driver={DB_DRIVER.replace(' ', '+')}&Encrypt=yes&TrustServerCertificate=yes"
    )


engine = create_engine(
    _build_connection_string(),
    pool_pre_ping=True,  # Verifica conexión antes de usar el pool
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

