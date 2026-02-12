from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.usuario import Usuario
from app.utils.security import verificar_contrasena, crear_token_jwt, verificar_token_jwt
from app.database import get_db_usuarios

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verificar_token_jwt(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload["sub"]

@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db_usuarios)):
    stmt = select(Usuario).where(Usuario.nombre_usuario == form_data.username)
    result = await db.execute(stmt)
    usuario = result.scalars().first()
    if not usuario or not usuario.activo:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if not verificar_contrasena(form_data.password, usuario.contrasena_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    # Generar JWT real
    token = crear_token_jwt({"sub": usuario.nombre_usuario})
    return {"access_token": token, "token_type": "bearer"}

# Ejemplo de endpoint protegido
@router.get("/auth/me")
async def me(usuario: str = Depends(get_current_user)):
    return {"usuario": usuario}
