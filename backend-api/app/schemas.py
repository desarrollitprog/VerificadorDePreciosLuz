from typing import Optional
from pydantic import BaseModel


class ProductoSchema(BaseModel):
    id: int
    codigo_barras: str
    nombre: str
    precio: float
    precio_oferta: Optional[float] = None

    class Config:
        orm_mode = True


class PublicidadSchema(BaseModel):
    id: int
    titulo: Optional[str]
    imagen: Optional[str]
    activo: bool

    class Config:
        orm_mode = True
