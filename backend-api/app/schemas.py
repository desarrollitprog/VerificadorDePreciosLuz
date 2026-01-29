from typing import Optional
from pydantic import BaseModel


class ProductoSchema(BaseModel):
    id_producto: int
    sku: str
    nombre: str

    class Config:
        orm_mode = True


class PublicidadSchema(BaseModel):
    id: int
    titulo: Optional[str]
    imagen: Optional[str]
    activo: bool

    class Config:
        orm_mode = True
