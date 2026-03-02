import os
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

# Hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_contrasena(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hashear_contrasena(password):
    return pwd_context.hash(password)

# JWT
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Falta la variable de entorno SECRET_KEY")
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

def crear_token_jwt(
    data: dict,
    audience: str = "dashboard",
    subject: str | None = None,
    role: str | None = None,
    user_id: int | None = None,
):
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "nbf": now,
        "iat": now,
        "aud": audience,
    })
    if subject:
        to_encode["sub"] = subject
    if role is not None:
        to_encode["rol"] = role
    if user_id is not None:
        to_encode["user_id"] = int(user_id)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token_jwt(token: str, audience: str = "dashboard"):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=audience,  # Valida el claim 'aud'
            options={"require": ["exp", "nbf", "iat", "aud", "sub", "rol", "user_id"]}  # Requiere estos claims
        )
        return payload
    except Exception as e:
        print(f"Token error: {e}")
        return None
