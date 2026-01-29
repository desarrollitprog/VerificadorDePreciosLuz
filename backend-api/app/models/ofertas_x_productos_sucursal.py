from sqlalchemy import Column, Integer
from ..database import Base


class OfertasxProductosxSucursal(Base):
    """
    Modelo para la tabla Transaccional.OfertasxProductosxSucursal
    Contiene el identificador de la oferta por producto en sucursal.
    """

    __tablename__ = "OfertasxProductosxSucursal"
    __table_args__ = {"schema": "Transaccional"}

    IdOfertaxProductoxSucursal = Column(
        "IdOfertaxProductoxSucursal", Integer, primary_key=True, index=True
    )
    IdOfertaxProducto = Column("IdOfertaxProducto", Integer, nullable=False, index=True)

    def __repr__(self):
        return (
            "<OfertasxProductosxSucursal("
            f"IdOfertaxProductoxSucursal={self.IdOfertaxProductoxSucursal}, "
            f"IdOfertaxProducto={self.IdOfertaxProducto}"
            ")>"
        )
