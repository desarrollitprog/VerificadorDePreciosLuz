from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.database import get_db_usuarios
from app.dependencies import get_current_admin
from app.models.usuario import RolUsuario, Usuario
from app.schemas import UsuarioResponse, UsuarioCreate, UsuarioUpdate, UsuarioListResponse
from app.services.notificacion_service import registrar_accion
from app.utils.security import hashear_contrasena

router = APIRouter()


def _rol_from_body(rol: str | None) -> RolUsuario:
    if not rol or rol not in ("ADMIN", "CLIENTE"):
        return RolUsuario.CLIENTE
    return RolUsuario.ADMIN if rol == "ADMIN" else RolUsuario.CLIENTE


@router.get("/usuarios", response_model=UsuarioListResponse)
async def listar_usuarios(
    search: str | None = Query(default=None, description="Búsqueda por correo o nombre de usuario"),
    rol: str | None = Query(default=None, description="ADMIN o CLIENTE"),
    activo: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    stmt = select(Usuario)
    count_stmt = select(func.count()).select_from(Usuario)

    if search:
        search_term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Usuario.nombre_usuario).like(search_term)
            | func.lower(Usuario.correo).like(search_term)
        )
        count_stmt = count_stmt.where(
            func.lower(Usuario.nombre_usuario).like(search_term)
            | func.lower(Usuario.correo).like(search_term)
        )

    if rol in ("ADMIN", "CLIENTE"):
        rol_enum = RolUsuario.ADMIN if rol == "ADMIN" else RolUsuario.CLIENTE
        stmt = stmt.where(Usuario.rol == rol_enum)
        count_stmt = count_stmt.where(Usuario.rol == rol_enum)

    if activo is not None:
        stmt = stmt.where(Usuario.activo == activo)
        count_stmt = count_stmt.where(Usuario.activo == activo)

    total_result = await db.execute(count_stmt)
    total = int(total_result.scalar() or 0)

    offset = (page - 1) * page_size
    stmt = stmt.order_by(Usuario.id.desc()).offset(offset).limit(page_size)

    result = await db.execute(stmt)
    usuarios = result.scalars().all()

    total_pages = ceil(total / page_size) if total > 0 else 1
    return {
        "success": True,
        "items": [UsuarioResponse.from_orm(u) for u in usuarios],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("/usuarios", response_model=UsuarioResponse)
async def crear_usuario(
    usuario: UsuarioCreate,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    normalized_username = usuario.nombre_usuario.strip()
    normalized_correo = usuario.correo.strip().lower()

    exists_user_result = await db.execute(select(Usuario).where(func.lower(Usuario.nombre_usuario) == normalized_username.lower()))
    existing_username = exists_user_result.scalars().first()
    if existing_username:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre de usuario")

    exists_email_result = await db.execute(select(Usuario).where(func.lower(Usuario.correo) == normalized_correo))
    existing_email = exists_email_result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")

    nuevo_usuario = Usuario(
        nombre_usuario=normalized_username,
        correo=normalized_correo,
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
        nuevo_username = usuario.nombre_usuario.strip()
        exists_result = await db.execute(
            select(Usuario).where(
                func.lower(Usuario.nombre_usuario) == nuevo_username.lower(),
                Usuario.id != id,
            )
        )
        usuario_existente = exists_result.scalars().first()
        if usuario_existente:
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre de usuario")
        usuario_db.nombre_usuario = nuevo_username

    if usuario.correo is not None:
        nuevo_correo = usuario.correo.strip().lower()
        exists_result = await db.execute(
            select(Usuario).where(
                func.lower(Usuario.correo) == nuevo_correo,
                Usuario.id != id,
            )
        )
        usuario_existente = exists_result.scalars().first()
        if usuario_existente:
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")
        usuario_db.correo = nuevo_correo
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
