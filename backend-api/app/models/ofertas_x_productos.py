from sqlalchemy import Column, Integer, DateTime
from ..database import Base


class OfertasxProductos(Base):
    """
    Modelo para la tabla Transaccional.OfertasxProductos
    Define el estado de vigencia de la oferta por IdOfertaxProducto.
    """

    __tablename__ = "OfertasxProductos"
    __table_args__ = {"schema": "Transaccional"}

    IdOfertaxProducto = Column("IdOfertaxProducto", Integer, primary_key=True, index=True)
    IndExpirado = Column("IndExpirado", Integer, nullable=True, index=True)
    FechaInicio = Column("FechaInicio", DateTime, nullable=True, index=True)
    FechaFin = Column("FechaFin", DateTime, nullable=True, index=True)

    def __repr__(self):
        return (
            "<OfertasxProductos("
            f"IdOfertaxProducto={self.IdOfertaxProducto}, "
            f"IndExpirado={self.IndExpirado}, "
            f"FechaInicio={self.FechaInicio}, "
            f"FechaFin={self.FechaFin}"
            ")>"
        )
