import asyncio
import logging
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from app.models.usuario import Usuario
from app.utils.security import verificar_contrasena, crear_token_jwt, verificar_token_jwt
from app.database import get_db_usuarios
from app.utils.twofa_redis import (
    create_2fa_challenge,
    verify_2fa_code,
    update_2fa_code,
    delete_2fa_challenge,
    get_2fa_challenge,
    get_masked_email,
    get_otp_expires_seconds,
    _generate_otp_code,
)
import redis.asyncio as redis

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

RATE_LIMIT_LOGIN_MAX = int(os.getenv("RATE_LIMIT_LOGIN_MAX", "5"))
RATE_LIMIT_LOGIN_WINDOW = int(os.getenv("RATE_LIMIT_LOGIN_WINDOW", "60"))

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://dashboard-redis:6380")
        try:
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            await _redis_client.ping()
        except Exception:
            logger.warning("redis_connection_failed")
            _redis_client = None
    return _redis_client


async def check_rate_limit(client_ip: str) -> tuple[bool, int]:
    redis_client = await get_redis()
    if redis_client is None:
        return True, RATE_LIMIT_LOGIN_MAX

    key = f"rate_limit:login:{client_ip}"
    try:
        current = await redis_client.get(key)
        if current is None:
            await redis_client.setex(key, RATE_LIMIT_LOGIN_WINDOW, "1")
            return True, RATE_LIMIT_LOGIN_MAX - 1
        
        current_int = int(current)
        if current_int >= RATE_LIMIT_LOGIN_MAX:
            return False, 0
        
        await redis_client.incr(key)
        return True, RATE_LIMIT_LOGIN_MAX - current_int - 1
    except Exception:
        logger.warning("rate_limit_check_failed")
        return True, RATE_LIMIT_LOGIN_MAX


async def clear_rate_limit(client_ip: str):
    redis_client = await get_redis()
    if redis_client:
        try:
            key = f"rate_limit:login:{client_ip}"
            await redis_client.delete(key)
        except Exception:
            logger.warning("rate_limit_clear_failed")


async def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class LoginBody(BaseModel):
    username: str
    correo: str | None = None
    contrasena: str


class TwoFactorVerifyBody(BaseModel):
    temp_token: str
    code: str


class TwoFactorResendBody(BaseModel):
    temp_token: str


ALLOW_LEGACY_LOGIN_WITHOUT_CORREO = True
OTP_EXPIRES_SECONDS = get_otp_expires_seconds()
OTP_MAX_ATTEMPTS = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _send_otp_email_sync(to_email: str, otp_code: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    if not smtp_host or not smtp_from:
        raise RuntimeError("SMTP no configurado. Define SMTP_HOST y SMTP_FROM")

    msg = EmailMessage()
    msg["Subject"] = "Código de verificación - Verificador de Precios Luz"
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg.set_content(
        (
            "Tu código de verificación es: "
            f"{otp_code}\n\n"
            f"Este código expira en {OTP_EXPIRES_SECONDS // 60} minutos."
        )
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        if smtp_use_tls:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)


async def _send_otp_email(to_email: str, otp_code: str) -> None:
    await asyncio.to_thread(_send_otp_email_sync, to_email, otp_code)


async def _create_2fa_challenge(usuario: Usuario) -> dict:
    correo_destino = (usuario.correo or "").strip().lower()
    if not correo_destino:
        raise HTTPException(status_code=422, detail="El usuario no tiene correo configurado para 2FA")

    result = await create_2fa_challenge(
        user_id=usuario.id,
        username=usuario.nombre_usuario,
        correo=correo_destino,
    )

    if result is None:
        raise HTTPException(status_code=503, detail="Servicio 2FA no disponible")

    challenge = await get_2fa_challenge(result["temp_token"])
    if challenge:
        await _send_otp_email(correo_destino, challenge["code"])

    return result


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verificar_token_jwt(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    usuario = payload.get("sub")
    user_id = payload.get("user_id")
    audiencia = payload.get("aud")
    emitido_en = payload.get("iat")
    not_before = payload.get("nbf")
    rol = payload.get("rol")
    return {
        "usuario": usuario,
        "user_id": int(user_id) if user_id is not None else None,
        "audiencia": audiencia,
        "emitido_en": emitido_en,
        "not_before": not_before,
        "rol": rol,
    }

@router.post("/auth/login")
async def login(request: Request, db: AsyncSession = Depends(get_db_usuarios)):
    client_ip = await get_client_ip(request)
    allowed, remaining = await check_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos de login. Espera un momento e intenta de nuevo."
        )

    username = ""
    correo = ""
    contrasena = ""

    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        username = str(payload.get("username") or "").strip()
        correo = str(payload.get("correo") or "").strip().lower()
        contrasena = str(payload.get("contrasena") or payload.get("password") or "")
    else:
        form = await request.form()
        username = str(form.get("username") or "").strip()
        correo = str(form.get("correo") or "").strip().lower()
        contrasena = str(form.get("contrasena") or form.get("password") or "")

    if not username or not contrasena:
        raise HTTPException(status_code=422, detail="username y contrasena son requeridos")

    username_norm = username.lower()

    if correo:
        stmt = select(Usuario).where(
            func.lower(Usuario.nombre_usuario) == username_norm,
            func.lower(Usuario.correo) == correo,
        )
    elif ALLOW_LEGACY_LOGIN_WITHOUT_CORREO:
        stmt = select(Usuario).where(func.lower(Usuario.nombre_usuario) == username_norm)
    else:
        raise HTTPException(status_code=422, detail="correo es requerido")

    result = await db.execute(stmt)
    usuario = result.scalars().first()
    if not usuario or not usuario.activo:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not verificar_contrasena(contrasena, usuario.contrasena_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    await clear_rate_limit(client_ip)
    return await _create_2fa_challenge(usuario)


@router.post("/auth/verify-2fa")
async def verify_2fa(body: TwoFactorVerifyBody, db: AsyncSession = Depends(get_db_usuarios)):
    temp_token = (body.temp_token or "").strip()
    code = (body.code or "").strip()
    if not temp_token or not code:
        raise HTTPException(status_code=422, detail="temp_token y code son requeridos")

    valid, error_msg = await verify_2fa_code(temp_token, code)
    if not valid:
        if "expir" in error_msg.lower() or "inválido" in error_msg.lower():
            raise HTTPException(status_code=401, detail=error_msg)
        if "intentos" in error_msg.lower():
            raise HTTPException(status_code=429, detail=error_msg)
        raise HTTPException(status_code=401, detail=error_msg)

    challenge = await get_2fa_challenge(temp_token)
    if not challenge:
        raise HTTPException(status_code=401, detail="Desafío 2FA inválido o expirado")

    user_id = challenge["user_id"]
    await delete_2fa_challenge(temp_token)

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    usuario = result.scalars().first()
    if not usuario or not usuario.activo:
        raise HTTPException(status_code=401, detail="Usuario inactivo o no encontrado")

    rol_valor = usuario.rol.value if hasattr(usuario.rol, "value") else str(usuario.rol)
    token = crear_token_jwt(
        {"sub": usuario.nombre_usuario},
        subject=usuario.nombre_usuario,
        role=rol_valor,
        user_id=usuario.id,
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/resend-2fa")
async def resend_2fa(body: TwoFactorResendBody):
    temp_token = (body.temp_token or "").strip()
    if not temp_token:
        raise HTTPException(status_code=422, detail="temp_token es requerido")

    challenge = await get_2fa_challenge(temp_token)
    if not challenge:
        raise HTTPException(status_code=401, detail="Desafío 2FA inválido o expirado")

    expires_at = datetime.fromisoformat(challenge["expires_at"])
    if _utcnow() > expires_at:
        await delete_2fa_challenge(temp_token)
        raise HTTPException(status_code=401, detail="El desafío 2FA expiró")

    correo_destino = challenge["correo"]

    otp_code = _generate_otp_code()
    new_expires_at = _utcnow() + timedelta(seconds=OTP_EXPIRES_SECONDS)
    await update_2fa_code(temp_token, otp_code, new_expires_at)
    await _send_otp_email(correo_destino, otp_code)

    return {
        "success": True,
        "message": "Código reenviado al correo registrado",
        "masked_email": get_masked_email(correo_destino),
        "expires_in": OTP_EXPIRES_SECONDS,
    }


@router.get("/auth/me")
async def me(info: dict = Depends(get_current_user)):
    return info
