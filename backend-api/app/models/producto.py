from sqlalchemy import Column, Integer, String
from ..database import Base

class Producto(Base):
    """ 
    Modelo para la tabla Transaccional.Productos
    Contiene la información básica de los productos.
    """
    __tablename__ = "Productos"
    __table_args__ = {"schema": "Transaccional"}

    # Campos (solo los requeridos)
    IdProducto = Column("IdProducto", Integer, primary_key=True, index=True)
    SKU = Column("SKU", String(100), nullable=False, index=True)
    Nombre = Column("Nombre", String(200), nullable=False)

    def __repr__(self):
        return f"<Producto(IdProducto={self.IdProducto}, SKU='{self.SKU}', Nombre='{self.Nombre}')>"


    