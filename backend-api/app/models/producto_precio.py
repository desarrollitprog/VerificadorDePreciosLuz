from sqlalchemy import Column, Integer, Numeric, BigInteger
from ..database import Base

class ProductoPrecio(Base):
    """
    Modelo para la tabla Transaccional.ProductosXEmpaqueXSucursal
    Contiene los precios de los productos.
    """
    __tablename__ = "ProductosXEmpaqueXSucursal"
    __table_args__ = {"schema": "Transaccional"}

    # Campos
    IdProductosXEmpaqueXSucursal = Column(
        "IdProductosXEmpaqueXSucursal", BigInteger, primary_key=True, index=True
    )
    IdProducto = Column("IdProducto", Integer, nullable=False, index=True)
    IdEmpaque = Column("IdEmpaque", Integer, nullable=False, index=True)

    # Costos
    CostoBase = Column("CostoBase", Numeric(18, 2), nullable=True)

    # Precios
    PVPBase = Column("PVPBase", Numeric(18, 2), nullable=False)
    PVPConversion = Column("PVPConversion", Numeric(18, 2), nullable=True)

    # Indicador IVA (0/1)
    IndIVA = Column("IndIVA", Integer, nullable=True)

    def __repr__(self):
        return (
            "<ProductoPrecio("
            f"IdProductosXEmpaqueXSucursal={self.IdProductosXEmpaqueXSucursal}, "
            f"IdProducto={self.IdProducto}, "
            f"IdEmpaque={self.IdEmpaque}, "
            f"CostoBase={self.CostoBase}, "
            f"PVPBase={self.PVPBase}, "
            f"PVPConversion={self.PVPConversion}, "
            f"IndIVA={self.IndIVA}"
            ")>"
        )
