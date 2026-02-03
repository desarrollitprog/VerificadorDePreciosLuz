from sqlalchemy import Column, Integer, Numeric, BigInteger
from ..database import Base


class ProductoOferta(Base):
    """
    Modelo para la tabla Transaccional.ProductosOfertasxSucursal
    Contiene las ofertas activas de productos.
    """
    __tablename__ = "ProductosOfertasxSucursal"
    __table_args__ = {"schema": "Transaccional"}
    
    # Campos
    IdProductoOfertaxSucursal = Column(
        "IdProductoOfertaxSucursal", BigInteger, primary_key=True, index=True
    )
    IdProducto = Column("IdProducto", Integer, nullable=False, index=True)
    IdEmpaque = Column("IdEmpaque", Integer, nullable=False, index=True)

    # Indicador de IVA (0/1)
    IndActivo = Column("IndActivo", Integer, nullable=False, index=True)

    # Precios de oferta
    PvpOferta = Column("PvpOferta", Numeric(18, 2), nullable=True)        # Oferta en $ 
    PvpBaseOferta = Column("PvpBaseOferta", Numeric(18, 2), nullable=True) # Oferta en Bs
    
    # Relación (opcional)
    # producto = relationship("Producto", back_populates="ofertas")
    
    def __repr__(self):
        return (
            "<ProductoOferta("
            f"IdProductoOfertaxSucursal={self.IdProductoOfertaxSucursal}, "
            f"IdProducto={self.IdProducto}, "
            f"IdEmpaque={self.IdEmpaque}, "
            f"IndActivo={self.IndActivo}, "
            f"PvpOferta={self.PvpOferta}, "
            f"PvpBaseOferta={self.PvpBaseOferta}"
            ")>"
        )