import json
import os
import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://dashboard-redis:6380")
OTP_EXPIRES_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
KEY_PREFIX = "2fa:pending:"

_redis_client: redis.Redis | None = None


class TwoFAChallenge(TypedDict):
    user_id: int
    username: str
    correo: str
    expires_at: str
    code: str
    attempts: int


class TwoFAResult(TypedDict):
    requires_2fa: bool
    message: str
    temp_token: str
    masked_email: str
    expires_in: int


async def get_redis_client() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            await _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


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


def _serialize_challenge(challenge: TwoFAChallenge) -> str:
    return json.dumps(challenge)


def _deserialize_challenge(data: str) -> TwoFAChallenge:
    parsed = json.loads(data)
    return TwoFAChallenge(
        user_id=int(parsed["user_id"]),
        username=str(parsed["username"]),
        correo=str(parsed["correo"]),
        expires_at=str(parsed["expires_at"]),
        code=str(parsed["code"]),
        attempts=int(parsed["attempts"]),
    )


async def create_2fa_challenge(
    user_id: int,
    username: str,
    correo: str,
) -> TwoFAResult | None:
    redis_client = await get_redis_client()
    if redis_client is None:
        return None

    temp_token = secrets.token_urlsafe(32)
    otp_code = _generate_otp_code()
    expires_at = _utcnow() + timedelta(seconds=OTP_EXPIRES_SECONDS)
    expires_at_str = expires_at.isoformat()

    challenge = TwoFAChallenge(
        user_id=user_id,
        username=username,
        correo=correo,
        expires_at=expires_at_str,
        code=otp_code,
        attempts=0,
    )

    key = f"{KEY_PREFIX}{temp_token}"
    await redis_client.setex(key, OTP_EXPIRES_SECONDS, _serialize_challenge(challenge))

    return TwoFAResult(
        requires_2fa=True,
        message="Código de verificación enviado al correo registrado",
        temp_token=temp_token,
        masked_email=_mask_email(correo),
        expires_in=OTP_EXPIRES_SECONDS,
    )


async def get_2fa_challenge(temp_token: str) -> TwoFAChallenge | None:
    redis_client = await get_redis_client()
    if redis_client is None:
        return None

    key = f"{KEY_PREFIX}{temp_token}"
    data = await redis_client.get(key)
    if not data:
        return None

    return _deserialize_challenge(data)


async def update_2fa_attempts(temp_token: str, attempts: int) -> None:
    redis_client = await get_redis_client()
    if redis_client is None:
        return

    key = f"{KEY_PREFIX}{temp_token}"
    data = await redis_client.get(key)
    if not data:
        return

    challenge = _deserialize_challenge(data)
    challenge["attempts"] = attempts
    ttl = await redis_client.ttl(key)
    if ttl > 0:
        await redis_client.setex(key, ttl, _serialize_challenge(challenge))


async def update_2fa_code(
    temp_token: str,
    code: str,
    expires_at: datetime,
) -> None:
    redis_client = await get_redis_client()
    if redis_client is None:
        return

    key = f"{KEY_PREFIX}{temp_token}"
    data = await redis_client.get(key)
    if not data:
        return

    challenge = _deserialize_challenge(data)
    challenge["code"] = code
    challenge["attempts"] = 0
    challenge["expires_at"] = expires_at.isoformat()

    ttl = int((expires_at - _utcnow()).total_seconds())
    if ttl > 0:
        await redis_client.setex(key, ttl, _serialize_challenge(challenge))


async def delete_2fa_challenge(temp_token: str) -> None:
    redis_client = await get_redis_client()
    if redis_client is None:
        return

    key = f"{KEY_PREFIX}{temp_token}"
    await redis_client.delete(key)


async def verify_2fa_code(
    temp_token: str,
    code: str,
) -> tuple[bool, str]:
    challenge = await get_2fa_challenge(temp_token)
    if not challenge:
        return False, "Desafío 2FA inválido o expirado"

    expires_at = datetime.fromisoformat(challenge["expires_at"])
    if _utcnow() > expires_at:
        await delete_2fa_challenge(temp_token)
        return False, "El código expiró, solicita uno nuevo"

    if challenge["attempts"] >= OTP_MAX_ATTEMPTS:
        await delete_2fa_challenge(temp_token)
        return False, "Demasiados intentos fallidos"

    if code != challenge["code"]:
        await update_2fa_attempts(temp_token, challenge["attempts"] + 1)
        return False, "Código incorrecto"

    return True, ""


def get_otp_code_from_email_template() -> str:
    return _generate_otp_code()


def get_masked_email(correo: str) -> str:
    return _mask_email(correo)


def get_otp_expires_seconds() -> int:
    return OTP_EXPIRES_SECONDS
