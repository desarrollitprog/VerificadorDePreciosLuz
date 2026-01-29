from typing import Optional
from pydantic import BaseModel


class ProductoResponse(BaseModel):
    id_producto: int
    sku: str
    nombre: str
    pvp_base: Optional[float] = None
    pvp_conversion: Optional[float] = None
    ind_iva: Optional[int] = None
    pvp_oferta: Optional[float] = None
    pvp_base_oferta: Optional[float] = None
    id_empaque: Optional[int] = None

    class Config:
        orm_mode = True
