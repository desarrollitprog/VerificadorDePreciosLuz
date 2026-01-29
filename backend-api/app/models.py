from sqlalchemy import Column, Integer, String
from .database import Base


class Producto(Base):
    __tablename__ = "Productos"

    IdProducto = Column("IdProducto", Integer, primary_key=True, index=True)
    SKU = Column("SKU", String(100), nullable=False, index=True)
    Nombre = Column("Nombre", String(200), nullable=False)