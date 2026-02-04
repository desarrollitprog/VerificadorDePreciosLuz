from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class PublicidadBase(BaseModel):
    titulo: Optional[str] = None
    tipo: Literal["image", "video"] = "image"
    url: str
    activo: bool = True
    prioridad: int = 0
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    duracion_seg: Optional[int] = Field(default=None, ge=1)


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
    duracion_seg: Optional[int] = Field(default=None, ge=1)


class PublicidadResponse(PublicidadBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
