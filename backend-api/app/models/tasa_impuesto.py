from sqlalchemy import Column, Integer, Numeric
from ..database import BaseERP


class TasaImpuesto(BaseERP):
    """
    Modelo para la tabla ConfiguracionPOS.TasasImpuestos
    Contiene las tasas de IVA y otros impuestos.
    
    IMPORTANTE: Este modelo usa BaseERP porque está en otra base de datos.
    """
    __tablename__ = "TasasImpuestos"
    __table_args__ = {"schema": "ConfiguracionPOS"}
    
    # Campos reales
    IdTasaImpuesto = Column("IdTasaImpuesto", Integer, primary_key=True, index=True)
    Tasa = Column("Tasa", Numeric(5, 2), nullable=False)  # Ejemplo: 16.00 para 16%
    
    def __repr__(self):
        return f"<TasaImpuesto(IdTasaImpuesto={self.IdTasaImpuesto}, Tasa={self.Tasa}%)>"
