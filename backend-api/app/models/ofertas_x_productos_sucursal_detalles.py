from sqlalchemy import Column, Integer
from ..database import Base


class OfertasxProductosxSucursalesDetalles(Base):
    """
    Modelo para la tabla Transaccional.OfertasxProductosxSucursalesDetalles
    Relaciona la oferta por sucursal con el empaque.
    """

    __tablename__ = "OfertasxProductosxSucursalesDetalles"
    __table_args__ = {"schema": "Transaccional"}

    IdOfertaxProductoxSucursalDetalle = Column(
        "IdOfertaxProductoxSucursalDetalle", Integer, primary_key=True, index=True
    )
    IdEmpaque = Column("IdEmpaque", Integer, nullable=False, index=True)
    IdOfertaxProductoxSucursal = Column(
        "IdOfertaxProductoxSucursal", Integer, nullable=False, index=True
    )
    IndActivo = Column("IndActivo", Integer, nullable=True, index=True)

    def __repr__(self):
        return (
            "<OfertasxProductosxSucursalesDetalles("
            f"IdOfertaxProductoxSucursalDetalle={self.IdOfertaxProductoxSucursalDetalle}, "
            f"IdEmpaque={self.IdEmpaque}, "
            f"IdOfertaxProductoxSucursal={self.IdOfertaxProductoxSucursal}"
            ")>"
        )
