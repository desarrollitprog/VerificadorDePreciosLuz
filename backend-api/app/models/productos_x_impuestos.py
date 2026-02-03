from sqlalchemy import Column, Integer, BigInteger
from ..database import Base

class ProductosXImpuestos(Base):
    """
    Modelo para la tabla Transaccional.ProductosXImpuestos
    Relaciona productos con tasas de impuestos.
    """
    __tablename__ = "ProductosXImpuestos"
    __table_args__ = {"schema": "Transaccional"}

    IdProductoxImpuesto = Column("IdProductoxImpuesto", BigInteger, primary_key=True, index=True)
    IdProducto = Column("IdProducto", Integer, nullable=False, index=True)
    IdTasaImpuesto = Column("IdTasaImpuesto", Integer, nullable=False, index=True)
    IndActivo = Column("IndActivo", Integer, nullable=False, index=True)

    def __repr__(self):
        return (
            f"<ProductosXImpuestos(IdProductoxImpuesto={self.IdProductoxImpuesto}, "
            f"IdProducto={self.IdProducto}, IdTasaImpuesto={self.IdTasaImpuesto}, "
            f"IndActivo={self.IndActivo})>"
        )
