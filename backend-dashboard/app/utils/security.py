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
SECRET_KEY = os.getenv("SECRET_KEY", "Pit12345*")
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

def crear_token_jwt(data: dict, audience: str = "dashboard", subject: str = None):
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
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token_jwt(token: str, audience: str = "dashboard"):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=audience,  # Valida el claim 'aud'
            options={"require": ["exp", "nbf", "iat", "aud", "sub"]}  # Requiere estos claims
        )
        return payload
    except Exception as e:
        print(f"Token error: {e}")
        return None
