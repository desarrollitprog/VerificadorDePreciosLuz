from typing import Literal, Optional

from pydantic import BaseModel, validator

ROL_LITERAL = Literal["ADMIN", "CLIENTE"]


class UsuarioBase(BaseModel):
    nombre_usuario: str
    activo: Optional[bool] = True
    rol: ROL_LITERAL = "CLIENTE"


class UsuarioCreate(UsuarioBase):
    contrasena: str
    rol: ROL_LITERAL = "CLIENTE"


class UsuarioUpdate(BaseModel):
    nombre_usuario: Optional[str] = None
    contrasena: Optional[str] = None
    activo: Optional[bool] = None
    rol: Optional[ROL_LITERAL] = None


class UsuarioResponse(UsuarioBase):
    id: int
    rol: str

    @validator("rol", pre=True)
    def rol_to_str(cls, v):
        if hasattr(v, "value"):
            return v.value
        return v if isinstance(v, str) else "CLIENTE"

    class Config:
        orm_mode = True
