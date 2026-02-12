from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.usuario import Usuario
from app.schemas import UsuarioResponse

async def obtener_usuario_por_nombre(nombre_usuario: str, db: AsyncSession) -> Usuario | None:
    result = await db.execute(select(Usuario).where(Usuario.nombre_usuario == nombre_usuario))
    return result.scalars().first()

async def obtener_usuario_por_id(id: int, db: AsyncSession) -> Usuario | None:
    result = await db.execute(select(Usuario).where(Usuario.id == id))
    return result.scalars().first()

async def usuario_a_response(usuario: Usuario) -> UsuarioResponse:
    return UsuarioResponse.from_orm(usuario)
