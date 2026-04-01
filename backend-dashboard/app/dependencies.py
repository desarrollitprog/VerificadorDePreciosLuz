"""
Dependencias de seguridad:
- RBAC basado en JWT (get_current_admin / get_current_cliente).
- Validación de API key para endpoints técnicos (ej. /heartbeat).
"""
import os

from fastapi import Depends, Header, HTTPException, status, WebSocket

from app.routes.auth import get_current_user, verificar_token_jwt


def get_current_admin(current_user: dict = Depends(get_current_user)):
    """Exige que el usuario autenticado tenga rol ADMIN."""
    if current_user.get("rol") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return current_user


def get_current_cliente(current_user: dict = Depends(get_current_user)):
    """Exige que el usuario autenticado tenga rol CLIENTE o ADMIN (acceso a recursos de cliente)."""
    rol = current_user.get("rol")
    if rol not in ("CLIENTE", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de cliente o administrador",
        )
    return current_user


async def get_user_from_token(token: str) -> dict:
    """
    Extrae información del usuario desde un token JWT.
    Uso: WebSocket authentication.
    """
    payload = verificar_token_jwt(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    user_id = payload.get("user_id")
    rol = payload.get("rol")
    if rol not in ("CLIENTE", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de cliente o administrador",
        )
    return {
        "user_id": int(user_id) if user_id is not None else None,
        "rol": rol,
    }


def validar_api_key(x_api_key: str = Header(..., alias="X-API-KEY")):
    """
    Valida la API key enviada por los servidores secundarios en el header X-API-KEY.
    Compara contra la variable de entorno HEARTBEAT_API_KEY.
    """
    api_key_esperada = os.getenv("HEARTBEAT_API_KEY")
    if not api_key_esperada:
        # Configuración incorrecta del servidor
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key de heartbeat no configurada en el servidor",
        )

    if x_api_key != api_key_esperada:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida para heartbeat",
        )

    # Si pasa la validación, no es necesario devolver nada concreto
    return True
