from pydantic import BaseModel
from typing import Optional

class UsuarioBase(BaseModel):
    nombre_usuario: str
    activo: Optional[bool] = True

class UsuarioCreate(UsuarioBase):
    contrasena: str

class UsuarioUpdate(BaseModel):
    nombre_usuario: Optional[str] = None
    contrasena: Optional[str] = None
    activo: Optional[bool] = None

class UsuarioResponse(UsuarioBase):
    id: int
    class Config:
        orm_mode = True
