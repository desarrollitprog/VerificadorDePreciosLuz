from sqlalchemy import Column, Integer, String, Numeric
from .database import Base


class Producto(Base):
    __tablename__ = "Productos"

    Id = Column(Integer, primary_key=True, index=True)
    CodigoBarras = Column(String(64), unique=True, index=True, nullable=False)
    Nombre = Column(String(200), nullable=False)
    Precio = Column(Numeric(10, 2), nullable=False)
    PrecioOferta = Column(Numeric(10, 2), nullable=True)