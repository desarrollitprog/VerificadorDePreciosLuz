from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.usuario import Usuario
from app.schemas import UsuarioResponse, UsuarioCreate, UsuarioUpdate
from app.database import get_db_usuarios
from app.utils.security import hashear_contrasena

router = APIRouter()

@router.get("/usuarios", response_model=list[UsuarioResponse])
async def listar_usuarios(db: AsyncSession = Depends(get_db_usuarios)):
    result = await db.execute(select(Usuario))
    usuarios = result.scalars().all()
    return [UsuarioResponse.from_orm(u) for u in usuarios]

@router.post("/usuarios", response_model=UsuarioResponse)
async def crear_usuario(usuario: UsuarioCreate, db: AsyncSession = Depends(get_db_usuarios)):
    nuevo_usuario = Usuario(
        nombre_usuario=usuario.nombre_usuario,
        contrasena_hash=hashear_contrasena(usuario.contrasena),
        activo=usuario.activo
    )
    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)
    return UsuarioResponse.from_orm(nuevo_usuario)

@router.put("/usuarios/{id}", response_model=UsuarioResponse)
async def actualizar_usuario(id: int, usuario: UsuarioUpdate, db: AsyncSession = Depends(get_db_usuarios)):
    result = await db.execute(select(Usuario).where(Usuario.id == id))
    usuario_db = result.scalars().first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.nombre_usuario:
        usuario_db.nombre_usuario = usuario.nombre_usuario
    if usuario.contrasena:
        usuario_db.contrasena_hash = hashear_contrasena(usuario.contrasena)
    if usuario.activo is not None:
        usuario_db.activo = usuario.activo
    await db.commit()
    await db.refresh(usuario_db)
    return UsuarioResponse.from_orm(usuario_db)

@router.delete("/usuarios/{id}", status_code=204)
async def eliminar_usuario(id: int, db: AsyncSession = Depends(get_db_usuarios)):
    result = await db.execute(select(Usuario).where(Usuario.id == id))
    usuario_db = result.scalars().first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await db.delete(usuario_db)
    await db.commit()
    return None
