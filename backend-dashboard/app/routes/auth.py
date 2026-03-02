import asyncio
import os
import random
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from app.models.usuario import Usuario
from app.utils.security import verificar_contrasena, crear_token_jwt, verificar_token_jwt
from app.database import get_db_usuarios

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class LoginBody(BaseModel):
    username: str
    correo: str | None = None
    contrasena: str


class TwoFactorVerifyBody(BaseModel):
    temp_token: str
    code: str


class TwoFactorResendBody(BaseModel):
    temp_token: str


# TODO(MIGRACION_LOGIN_2026-03): eliminar compatibilidad legacy cuando todo cliente
# use login con JSON { username, correo, contrasena }.
ALLOW_LEGACY_LOGIN_WITHOUT_CORREO = True
OTP_EXPIRES_SECONDS = 300
OTP_MAX_ATTEMPTS = 5

PENDING_2FA: dict[str, dict[str, Any]] = {}
PENDING_2FA_LOCK = asyncio.Lock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        local_masked = f"{local[0]}***" if local else "***"
    else:
        local_masked = f"{local[0]}***{local[-1]}"
    return f"{local_masked}@{domain}"


def _generate_otp_code() -> str:
    return f"{random.SystemRandom().randint(0, 999999):06d}"


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


async def _cleanup_expired_2fa() -> None:
    now = _utcnow()
    async with PENDING_2FA_LOCK:
        expired_keys = [key for key, value in PENDING_2FA.items() if value["expires_at"] <= now]
        for key in expired_keys:
            PENDING_2FA.pop(key, None)


async def _create_2fa_challenge(usuario: Usuario) -> dict[str, Any]:
    correo_destino = (usuario.correo or "").strip().lower()
    if not correo_destino:
        raise HTTPException(status_code=422, detail="El usuario no tiene correo configurado para 2FA")

    otp_code = _generate_otp_code()
    await _send_otp_email(correo_destino, otp_code)

    temp_token = secrets.token_urlsafe(32)
    expires_at = _utcnow() + timedelta(seconds=OTP_EXPIRES_SECONDS)
    async with PENDING_2FA_LOCK:
        PENDING_2FA[temp_token] = {
            "user_id": usuario.id,
            "username": usuario.nombre_usuario,
            "correo": correo_destino,
            "expires_at": expires_at,
            "code": otp_code,
            "attempts": 0,
        }

    return {
        "requires_2fa": True,
        "message": "Código de verificación enviado al correo registrado",
        "temp_token": temp_token,
        "masked_email": _mask_email(correo_destino),
        "expires_in": OTP_EXPIRES_SECONDS,
    }

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verificar_token_jwt(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Consumir los claims relevantes
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
    await _cleanup_expired_2fa()

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

    # Flujo nuevo: exige correo
    if correo:
        stmt = select(Usuario).where(
            func.lower(Usuario.nombre_usuario) == username_norm,
            func.lower(Usuario.correo) == correo,
        )
    # Compatibilidad temporal de migración
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

    return await _create_2fa_challenge(usuario)


@router.post("/auth/verify-2fa")
async def verify_2fa(body: TwoFactorVerifyBody, db: AsyncSession = Depends(get_db_usuarios)):
    await _cleanup_expired_2fa()

    temp_token = (body.temp_token or "").strip()
    code = (body.code or "").strip()
    if not temp_token or not code:
        raise HTTPException(status_code=422, detail="temp_token y code son requeridos")

    async with PENDING_2FA_LOCK:
        challenge = PENDING_2FA.get(temp_token)
        if not challenge:
            raise HTTPException(status_code=401, detail="Desafío 2FA inválido o expirado")

        if challenge["expires_at"] <= _utcnow():
            PENDING_2FA.pop(temp_token, None)
            raise HTTPException(status_code=401, detail="El código expiró, solicita uno nuevo")

        if challenge["attempts"] >= OTP_MAX_ATTEMPTS:
            PENDING_2FA.pop(temp_token, None)
            raise HTTPException(status_code=429, detail="Demasiados intentos fallidos")

        if code != challenge["code"]:
            challenge["attempts"] += 1
            raise HTTPException(status_code=401, detail="Código incorrecto")

        user_id = int(challenge["user_id"])
        PENDING_2FA.pop(temp_token, None)

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
    await _cleanup_expired_2fa()

    temp_token = (body.temp_token or "").strip()
    if not temp_token:
        raise HTTPException(status_code=422, detail="temp_token es requerido")

    async with PENDING_2FA_LOCK:
        challenge = PENDING_2FA.get(temp_token)
        if not challenge:
            raise HTTPException(status_code=401, detail="Desafío 2FA inválido o expirado")

        if challenge["expires_at"] <= _utcnow():
            PENDING_2FA.pop(temp_token, None)
            raise HTTPException(status_code=401, detail="El desafío 2FA expiró")

        correo_destino = challenge["correo"]

    otp_code = _generate_otp_code()
    await _send_otp_email(correo_destino, otp_code)

    async with PENDING_2FA_LOCK:
        challenge = PENDING_2FA.get(temp_token)
        if challenge:
            challenge["code"] = otp_code
            challenge["attempts"] = 0
            challenge["expires_at"] = _utcnow() + timedelta(seconds=OTP_EXPIRES_SECONDS)

    return {
        "success": True,
        "message": "Código reenviado al correo registrado",
        "masked_email": _mask_email(correo_destino),
        "expires_in": OTP_EXPIRES_SECONDS,
    }

# Ejemplo de endpoint protegido
@router.get("/auth/me")
async def me(info: dict = Depends(get_current_user)):
    return info
