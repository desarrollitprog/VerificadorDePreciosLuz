import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, validator

ROL_LITERAL = Literal["ADMIN", "CLIENTE"]


def _validar_correo(value: str) -> str:
    correo = (value or "").strip().lower()
    patron = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(patron, correo):
        raise ValueError("El correo electrónico no tiene un formato válido")
    return correo


def _validar_contrasena_fuerte(value: str) -> str:
    if len(value) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if not re.search(r"[A-Z]", value):
        raise ValueError("La contraseña debe incluir al menos una letra mayúscula")
    if not re.search(r"[a-z]", value):
        raise ValueError("La contraseña debe incluir al menos una letra minúscula")
    if not re.search(r"\d", value):
        raise ValueError("La contraseña debe incluir al menos un número")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("La contraseña debe incluir al menos un carácter especial")
    return value


class UsuarioBase(BaseModel):
    nombre_usuario: str
    correo: str
    activo: Optional[bool] = True
    rol: ROL_LITERAL = "CLIENTE"

    @validator("nombre_usuario")
    def validar_nombre_usuario(cls, value: str):
        username = (value or "").strip()
        patron = r"^[A-Za-z0-9._-]{3,50}$"
        if not re.match(patron, username):
            raise ValueError("El nombre de usuario debe tener 3-50 caracteres y solo letras, números, punto, guion o guion bajo")
        return username

    @validator("correo")
    def validar_correo(cls, value: str):
        return _validar_correo(value)


class UsuarioCreate(UsuarioBase):
    contrasena: str
    rol: ROL_LITERAL = "CLIENTE"

    @validator("contrasena")
    def validar_contrasena_fuerte(cls, value: str):
        return _validar_contrasena_fuerte(value)


class UsuarioUpdate(BaseModel):
    nombre_usuario: Optional[str] = None
    correo: Optional[str] = None
    contrasena: Optional[str] = None
    activo: Optional[bool] = None
    rol: Optional[ROL_LITERAL] = None

    @validator("nombre_usuario")
    def validar_nombre_usuario_update(cls, value: Optional[str]):
        if value is None:
            return value
        username = value.strip()
        patron = r"^[A-Za-z0-9._-]{3,50}$"
        if not re.match(patron, username):
            raise ValueError("El nombre de usuario debe tener 3-50 caracteres y solo letras, números, punto, guion o guion bajo")
        return username

    @validator("correo")
    def validar_correo_update(cls, value: Optional[str]):
        if value is None:
            return value
        return _validar_correo(value)

    @validator("contrasena")
    def validar_contrasena_update(cls, value: Optional[str]):
        if value is None:
            return value
        return _validar_contrasena_fuerte(value)


class UsuarioResponse(UsuarioBase):
    id: int
    rol: str
    fecha_registro: datetime

    @validator("rol", pre=True)
    def rol_to_str(cls, v):
        if hasattr(v, "value"):
            return v.value
        return v if isinstance(v, str) else "CLIENTE"

    class Config:
        orm_mode = True


class UsuarioListResponse(BaseModel):
    success: bool
    items: list[UsuarioResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
