from sqlalchemy import Column, Integer, String, Boolean, DateTime
from ..database import Base


class BarrasAsociadas(Base):
    __tablename__ = "BarrasAsociadas"
    __table_args__ = {"schema": "Transaccional"}
    
    IdBarraAsociada = Column("IdBarraAsociada", Integer, primary_key=True, index=True)
    IdProducto = Column("IdProducto", Integer, nullable=False, index=True)
    IdEmpaque = Column("IdEmpaque", Integer, nullable=True)
    IdTipoEmpaque = Column("IdTipoEmpaque", Integer, nullable=True)
    IdAgrupacionGeneracionBarra = Column("IdAgrupacionGeneracionBarra", Integer, nullable=True)
    IdTipoGeneracionBarra = Column("IdTipoGeneracionBarra", Integer, nullable=True)
    IdTipoGtin = Column("IdTipoGtin", Integer, nullable=True)
    IdUsuarioCrea = Column("IdUsuarioCrea", Integer, nullable=True)
    IdUsuarioModifica = Column("IdUsuarioModifica", Integer, nullable=True)
    Barra = Column("Barra", String(100), nullable=False, index=True)
    IndActivo = Column("IndActivo", Boolean, nullable=True)
    IndVisible = Column("IndVisible", Boolean, nullable=True)
    FechaCrea = Column("FechaCrea", DateTime, nullable=True)
    FechaModifica = Column("FechaModifica", DateTime, nullable=True)
