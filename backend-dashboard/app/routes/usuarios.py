from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db_usuarios
from app.dependencies import get_current_admin
from app.models.usuario import RolUsuario, Usuario
from app.schemas import UsuarioResponse, UsuarioCreate, UsuarioUpdate
from app.services.notificacion_service import registrar_accion
from app.utils.security import hashear_contrasena

router = APIRouter()


def _rol_from_body(rol: str | None) -> RolUsuario:
    if not rol or rol not in ("ADMIN", "CLIENTE"):
        return RolUsuario.CLIENTE
    return RolUsuario.ADMIN if rol == "ADMIN" else RolUsuario.CLIENTE


@router.get("/usuarios", response_model=list[UsuarioResponse])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    result = await db.execute(select(Usuario))
    usuarios = result.scalars().all()
    return [UsuarioResponse.from_orm(u) for u in usuarios]


@router.post("/usuarios", response_model=UsuarioResponse)
async def crear_usuario(
    usuario: UsuarioCreate,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    nuevo_usuario = Usuario(
        nombre_usuario=usuario.nombre_usuario,
        contrasena_hash=hashear_contrasena(usuario.contrasena),
        activo=usuario.activo,
        rol=_rol_from_body(usuario.rol),
    )
    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)
    user_id = current_user.get("user_id")
    if user_id is not None:
        await registrar_accion(
            db,
            user_id,
            "CREAR_USUARIO",
            f"Usuario creado: {nuevo_usuario.nombre_usuario}",
        )
    return UsuarioResponse.from_orm(nuevo_usuario)


@router.put("/usuarios/{id}", response_model=UsuarioResponse)
async def actualizar_usuario(
    id: int,
    usuario: UsuarioUpdate,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    result = await db.execute(select(Usuario).where(Usuario.id == id))
    usuario_db = result.scalars().first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.nombre_usuario is not None:
        usuario_db.nombre_usuario = usuario.nombre_usuario
    if usuario.contrasena is not None:
        usuario_db.contrasena_hash = hashear_contrasena(usuario.contrasena)
    if usuario.activo is not None:
        usuario_db.activo = usuario.activo
    if usuario.rol is not None:
        usuario_db.rol = _rol_from_body(usuario.rol)
    await db.commit()
    await db.refresh(usuario_db)
    user_id = current_user.get("user_id")
    if user_id is not None:
        await registrar_accion(
            db,
            user_id,
            "ACTUALIZAR_USUARIO",
            f"Usuario actualizado: id={id}, nombre={usuario_db.nombre_usuario}",
        )
    return UsuarioResponse.from_orm(usuario_db)


@router.delete("/usuarios/{id}", status_code=204)
async def eliminar_usuario(
    id: int,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    result = await db.execute(select(Usuario).where(Usuario.id == id))
    usuario_db = result.scalars().first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    nombre_borrado = usuario_db.nombre_usuario
    await db.delete(usuario_db)
    await db.commit()
    user_id = current_user.get("user_id")
    if user_id is not None:
        await registrar_accion(
            db,
            user_id,
            "BORRAR_USUARIO",
            f"Usuario eliminado: {nombre_borrado}",
        )
    return None
