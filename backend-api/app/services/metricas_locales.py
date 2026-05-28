import asyncio
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ..database import AsyncSessionLocalPublicidad
from ..models.reproduccion_metrica import ReproduccionMetricaSede

logger = logging.getLogger("uvicorn.error")
REDIS_KEY = "reproducciones:pending"
INTERVALO_SEGUNDOS = 60
SUB_BATCH_SIZE = 25


def _merge_eventos(eventos: list[dict]) -> dict | None:
    """Agrupa eventos por reproduccion_id y aplica en orden para obtener estado final."""
    grupos: dict[str, list[dict]] = {}
    for ev in eventos:
        rid = ev.get("reproduccion_id")
        if not rid:
            continue
        grupos.setdefault(rid, []).append(ev)

    resultados = []
    for rid, evs in grupos.items():
        evs.sort(key=lambda x: x.get("_ts", ""))
        row = None
        for ev in evs:
            tipo = ev.get("tipo_evento", "")
            if row is None:
                if tipo not in ("START", "COMPLETED", "INTERRUPTED"):
                    continue
                row = {
                    "reproduccion_id": rid,
                    "dispositivo_id": ev.get("dispositivo_id", ""),
                    "banner_id": ev.get("banner_id", 0),
                    "titulo": ev.get("titulo"),
                    "completo": ev.get("completo") or tipo == "COMPLETED",
                    "cuartil_50": ev.get("cuartil_50") or False,
                    "segundos_reproducidos": ev.get("segundos_reproducidos"),
                    "tipo_dispositivo": ev.get("tipo_dispositivo", "verificador"),
                    "fecha_creacion": datetime.utcnow(),
                }
            else:
                if ev.get("completo") or tipo == "COMPLETED":
                    row["completo"] = True
                if ev.get("cuartil_50"):
                    row["cuartil_50"] = True
                sr = ev.get("segundos_reproducidos")
                if sr is not None and (
                    row["segundos_reproducidos"] is None or sr > row["segundos_reproducidos"]
                ):
                    row["segundos_reproducidos"] = sr
                if ev.get("titulo") and not row["titulo"]:
                    row["titulo"] = ev["titulo"]
        if row is not None:
            resultados.append(row)
    return resultados


DIAS_CLEANUP = 15


async def limpiar_metricas_viejas():
    """Elimina registros de reproducciones_metricas_sede con más de 15 días."""
    try:
        cutoff = datetime.utcnow() - timedelta(days=DIAS_CLEANUP)
        async with AsyncSessionLocalPublicidad() as db:
            stmt = ReproduccionMetricaSede.__table__.delete().where(
                ReproduccionMetricaSede.fecha_creacion < cutoff
            )
            result = await db.execute(stmt)
            await db.commit()
            if result.rowcount > 0:
                logger.info(f"[Cleanup] Eliminadas {result.rowcount} métricas viejas (> {DIAS_CLEANUP} días)")
    except Exception as e:
        logger.error(f"[Cleanup] Error limpiando métricas viejas: {e}")


async def _enriquecer_con_tipo_dispositivo(rows: list[dict], device_state_store) -> None:
    """Obtiene el tipo de dispositivo desde Redis y lo asigna a cada fila."""
    dispositivos_vistos: set[str] = set()
    for r in rows:
        did = r.get("dispositivo_id", "")
        if did and did not in dispositivos_vistos:
            dispositivos_vistos.add(did)

    tipo_cache: dict[str, str] = {}
    for did in dispositivos_vistos:
        tipo_cache[did] = await device_state_store.get_device_type(did)

    for r in rows:
        did = r.get("dispositivo_id", "")
        r["tipo_dispositivo"] = tipo_cache.get(did, "verificador")


async def insertar_reproducciones_locales(reproducciones_redis, device_state_store=None):
    """Worker que cada 60s lee Redis, mergea en memoria e INSERTA localmente."""
    await limpiar_metricas_viejas()
    while True:
        try:
            await asyncio.sleep(INTERVALO_SEGUNDOS)

            if reproducciones_redis is None:
                continue

            items = await reproducciones_redis.lrange(REDIS_KEY, 0, -1)
            if not items:
                continue

            eventos_raw = []
            for item in items:
                try:
                    eventos_raw.append(json.loads(item))
                except json.JSONDecodeError:
                    logger.warning("Evento malformado en Redis, saltando")

            if not eventos_raw:
                await reproducciones_redis.ltrim(REDIS_KEY, len(items), -1)
                continue

            rows = _merge_eventos(eventos_raw)
            if not rows:
                await reproducciones_redis.ltrim(REDIS_KEY, len(items), -1)
                continue

            if device_state_store is not None:
                await _enriquecer_con_tipo_dispositivo(rows, device_state_store)

            ok = 0
            failed = 0
            async with AsyncSessionLocalPublicidad() as db:
                for i in range(0, len(rows), SUB_BATCH_SIZE):
                    sub = rows[i:i + SUB_BATCH_SIZE]
                    for row in sub:
                        try:
                            db.add(ReproduccionMetricaSede(**row))
                            await db.flush()
                            ok += 1
                        except IntegrityError:
                            await db.rollback()
                            try:
                                stmt = (
                                    update(ReproduccionMetricaSede)
                                    .where(
                                        ReproduccionMetricaSede.reproduccion_id
                                        == row["reproduccion_id"]
                                    )
                                    .values(
                                        completo=row["completo"],
                                        cuartil_50=row["cuartil_50"],
                                        segundos_reproducidos=row[
                                            "segundos_reproducidos"
                                        ],
                                    )
                                )
                                await db.execute(stmt)
                                await db.flush()
                                ok += 1
                            except Exception:
                                await db.rollback()
                                failed += 1
                await db.commit()

            await reproducciones_redis.ltrim(REDIS_KEY, len(items), -1)
            if failed:
                logger.info(
                    f"[MetricasLocales] {ok} insertadas, {failed} fallaron"
                )
            else:
                logger.info(
                    f"[MetricasLocales] {ok} reproducciones insertadas"
                )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[MetricasLocales] Error en ciclo: {e}")
