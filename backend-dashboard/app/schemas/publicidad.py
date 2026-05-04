from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel


class PublicidadBase(BaseModel):
    Titulo: Optional[str] = None
    Tipo: Literal["image", "video"] = "image"
    Url: str
    ThumbnailUrl: Optional[str] = None
    Activo: bool = True
    Prioridad: int = 0
    FechaInicio: Optional[datetime] = None
    FechaFin: Optional[datetime] = None

class PublicidadCreate(PublicidadBase):
    pass

class PublicidadUpdate(BaseModel):
    titulo: Optional[str] = None
    tipo: Optional[Literal["image", "video"]] = None
    url: Optional[str] = None
    activo: Optional[bool] = None
    prioridad: Optional[int] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None


class PublicidadResponse(PublicidadBase):
    IdPublicidad: int
    UpdatedAt: Optional[datetime] = None
    class Config:
        from_attributes = True
