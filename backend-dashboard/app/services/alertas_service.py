"""
Monitoreo proactivo de la flota de sedes.

Cada pocos minutos (ver scheduler.py) se verifica:
  1. Que cada sede haya enviado heartbeat recientemente.
  2. Que el backend-api de cada sede responda una consulta de precio real
     (smoke test contra el ERP).

Cuando algo falla se registra una notificación en la tabla `notificaciones`
(visible en el dashboard) y, opcionalmente, se envía un aviso a un webhook.

Variables de entorno (todas opcionales):
  ALERTS_ENABLED=1                  Activa/desactiva el monitoreo (0 lo apaga)
  ALERT_HEARTBEAT_MINUTES=10        Minutos sin heartbeat para considerar la sede caída
  ALERT_COOLDOWN_HOURS=6            Horas mínimas entre alertas iguales de la misma sede
  SMOKE_TEST_SKU=7591098800281      SKU usado para la consulta de prueba
  SMOKE_TEST_TIMEOUT=6              Timeout (segundos) del smoke test
  ALERTS_WEBHOOK_URL=               URL que recibe POST JSON {"text": "..."}
  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID   Alternativa para enviar por Telegram
"""
from __future__ import annotations

import asyncio
import os
from datetime import timedelta

import httpx
from sqlalchemy import select

from app.database import AsyncSessionLocalUsuarios
from app.models.notificacion import Notificacion
from app.models.servidor_secundario import ServidorSecundario
from app.services.server_service import _utcnow
from app.utils.logger import StructuredLogger

log = StructuredLogger("alertas")

TIPO_SIN_HEARTBEAT = "SEDE_SIN_CONEXION"
TIPO_ERP_CAIDO = "SEDE_ERP_CAIDO"
TIPO_RECUPERADA = "SEDE_RECUPERADA"

_TIPOS_FALLO = (TIPO_SIN_HEARTBEAT, TIPO_ERP_CAIDO)
_DESCRIPCION_MAX = 500


def _enabled() -> bool:
    return os.getenv("ALERTS_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


async def _ultima_alerta(db, tipo: str, servidor_id: int) -> Notificacion | None:
    stmt = (
        select(Notificacion)
        .where(Notificacion.tipo == tipo, Notificacion.servidor_id == servidor_id)
        .order_by(Notificacion.fecha_creacion.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    return res.scalars().first()


async def _puede_alertar(db, tipo: str, servidor_id: int) -> bool:
    """True si no hay alerta previa del mismo tipo dentro del cooldown."""
    ultima = await _ultima_alerta(db, tipo, servidor_id)
    if ultima is None or ultima.fecha_creacion is None:
        return True
    return ultima.fecha_creacion <= _utcnow() - timedelta(hours=_int_env("ALERT_COOLDOWN_HOURS", 6))


async def _debe_avisar_recuperacion(db, servidor_id: int) -> bool:
    """True si la última alerta de fallo es más reciente que la última de recuperación."""
    ultimo_fallo = None
    for tipo in _TIPOS_FALLO:
        alerta = await _ultima_alerta(db, tipo, servidor_id)
        if alerta and (ultimo_fallo is None or alerta.fecha_creacion > ultimo_fallo):
            ultimo_fallo = alerta.fecha_creacion
    if ultimo_fallo is None:
        return False
    ultima_recuperacion = await _ultima_alerta(db, TIPO_RECUPERADA, servidor_id)
    if ultima_recuperacion is None:
        return True
    return ultima_recuperacion.fecha_creacion < ultimo_fallo


async def _enviar_webhook(texto: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    url = os.getenv("ALERTS_WEBHOOK_URL", "").strip()
    if not url and not (token and chat):
        return
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            if token and chat:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat, "text": texto},
                )
            if url:
                await client.post(url, json={"text": texto})
    except Exception as e:  # noqa: BLE001 - nunca debe romper el job
        log.warning("alerta_webhook_fallo", error=str(e))


async def _crear_alerta(db, tipo: str, servidor: ServidorSecundario, mensaje: str) -> None:
    descripcion = mensaje[:_DESCRIPCION_MAX]
    db.add(
        Notificacion(
            tipo=tipo,
            descripcion=descripcion,
            servidor_id=servidor.id,
            fecha_creacion=_utcnow(),
        )
    )
    await db.commit()
    log.info("alerta_generada", tipo=tipo, servidor=servidor.nombre, detalle=descripcion)
    await _enviar_webhook(f"[{tipo}] {descripcion}")


async def _smoke_test_precio(ip: str, sku: str, timeout: float) -> tuple[bool, str]:
    url = f"http://{ip}:8000/consultar/{sku}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        data = resp.json()
        if not data.get("sku"):
            return False, "respuesta inválida"
        if data.get("pvp_base") is None and data.get("pvp_oferta") is None:
            return False, "sin precio en la respuesta"
        return True, "ok"
    except Exception as e:  # noqa: BLE001 - se reporta como detalle de la alerta
        detalle = str(e).strip() or type(e).__name__
        return False, detalle[:200]


async def verificar_flota() -> None:
    """
    Verifica heartbeat + consulta de precio de todas las sedes.
    Genera notificaciones de fallo y de recuperación (con cooldown).
    """
    if not _enabled():
        return

    sku = os.getenv("SMOKE_TEST_SKU", "7591098800281").strip()
    timeout = _float_env("SMOKE_TEST_TIMEOUT", 6.0)
    heartbeat_limit = _int_env("ALERT_HEARTBEAT_MINUTES", 10)

    try:
        async with AsyncSessionLocalUsuarios() as db:
            result = await db.execute(select(ServidorSecundario))
            servidores = list(result.scalars().all())
            if not servidores:
                return

            now = _utcnow()
            umbral = now - timedelta(minutes=heartbeat_limit)

            # 1) Smoke tests en paralelo (sin tocar la sesión de BD)
            sem = asyncio.Semaphore(8)

            async def _check(servidor: ServidorSecundario, online: bool):
                if not online:
                    return servidor, False, "sin heartbeat"
                async with sem:
                    ok, detalle = await _smoke_test_precio(servidor.ip, sku, timeout)
                return servidor, ok, detalle

            tareas = [
                _check(s, s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral)
                for s in servidores
            ]
            resultados = await asyncio.gather(*tareas)

            # 2) Registrar alertas de forma secuencial (una sola sesión de BD)
            for servidor, ok, detalle in resultados:
                online = servidor.ultimo_heartbeat is not None and servidor.ultimo_heartbeat >= umbral

                if not online:
                    if await _puede_alertar(db, TIPO_SIN_HEARTBEAT, servidor.id):
                        minutos = (
                            int((now - servidor.ultimo_heartbeat).total_seconds() // 60)
                            if servidor.ultimo_heartbeat
                            else None
                        )
                        detalle_edad = f"hace {minutos} min" if minutos is not None else "nunca registrado"
                        await _crear_alerta(
                            db,
                            TIPO_SIN_HEARTBEAT,
                            servidor,
                            f"Sede '{servidor.nombre}' ({servidor.ip}) sin heartbeat {detalle_edad}.",
                        )
                    continue

                if not ok:
                    if await _puede_alertar(db, TIPO_ERP_CAIDO, servidor.id):
                        await _crear_alerta(
                            db,
                            TIPO_ERP_CAIDO,
                            servidor,
                            f"Sede '{servidor.nombre}' ({servidor.ip}) no responde la consulta de precio "
                            f"(SKU {sku}): {detalle}.",
                        )
                    continue

                if await _debe_avisar_recuperacion(db, servidor.id):
                    await _crear_alerta(
                        db,
                        TIPO_RECUPERADA,
                        servidor,
                        f"Sede '{servidor.nombre}' ({servidor.ip}) volvió a responder correctamente.",
                    )

            log.info("alertas_verificacion_ok", sedes=len(servidores))
    except Exception as e:  # noqa: BLE001 - el scheduler no debe caerse
        log.error("alertas_verificacion_error", error=str(e))
