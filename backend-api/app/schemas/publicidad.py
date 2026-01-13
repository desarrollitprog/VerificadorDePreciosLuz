from typing import Optional
from pydantic import BaseModel

class PublicidadSchema(BaseModel):
    id: int
    titulo: Optional[str]
    imagen: Optional[str]
    activo: bool

    class Config:
        from_attributes = True
