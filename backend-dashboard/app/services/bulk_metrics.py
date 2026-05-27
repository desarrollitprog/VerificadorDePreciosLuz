import asyncio
import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from app.database import AsyncSessionLocalUsuarios
from app.models.reproduccion_metrica import ReproduccionMetrica
from app.services.metrics_redis import (
    get_metrics_redis, BULK_KEY, LOCK_KEY, LOCK_TTL,
    PAGE_SIZE, DEAD_LETTER_KEY, MAX_BULK_EVENTS,
)

logger = logging.getLogger("uvicorn.error")
_SUB_BATCH_SIZE = 25
PAGE_TIMEOUT = 120  # segundos máx por página antes de considerar SQL Server colgado

_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""


def _apply_evento(row: ReproduccionMetrica, ev: dict, now: datetime):
    tipo = ev.get("tipo_evento")
    if tipo == "START" and row.inicio_reproduccion is None:
        row.inicio_reproduccion = now
    titulo = ev.get("titulo")
    if titulo and not row.titulo:
        row.titulo = titulo
    duracion = ev.get("duracion_total_seg")
    if duracion is not None:
        row.duracion_total_seg = duracion
    sr = ev.get("segundos_reproducidos")
    if sr is not None and (row.segundos_reproducidos is None or sr > row.segundos_reproducidos):
        row.segundos_reproducidos = sr
    pc = ev.get("porcentaje_completado")
    if pc is not None and (row.porcentaje_completado is None or pc > row.porcentaje_completado):
        row.porcentaje_completado = pc
    if ev.get("cuartil_50"):
        row.cuartil_50 = True
    if ev.get("cuartil_75"):
        row.cuartil_75 = True
    if ev.get("cuartil_100"):
        row.cuartil_100 = True
    if ev.get("completo"):
        row.completo = True
    if ev.get("motivo_fin"):
        row.motivo_fin = ev["motivo_fin"]
    if tipo in ("COMPLETED", "INTERRUPTED"):
        row.fin_reproduccion = now


def _agrupar_por_reproduccion_id(eventos: list[dict]) -> dict[str, list[dict]]:
    """Agrupa eventos por reproduccion_id manteniendo el orden dentro de cada grupo."""
    grupos: dict[str, list[dict]] = {}
    for ev in eventos:
        rid = ev["reproduccion_id"]
        if rid not in grupos:
            grupos[rid] = []
        grupos[rid].append(ev)
    return grupos


async def _process_page(eventos: list[dict], raw_batch: list[str]) -> tuple[int, list[str]]:
    total_ok = 0
    failed_raw: list[str] = []

    async with AsyncSessionLocalUsuarios() as db:
        for i in range(0, len(eventos), _SUB_BATCH_SIZE):
            sub_ev = eventos[i:i + _SUB_BATCH_SIZE]
            sub_raw = raw_batch[i:i + _SUB_BATCH_SIZE]
            try:
                # 1. Agrupar eventos por reproduccion_id
                grupos = _agrupar_por_reproduccion_id(sub_ev)

                # 2. SELECT único con IN para todos los IDs del sub-batch
                stmt = select(ReproduccionMetrica).where(
                    ReproduccionMetrica.reproduccion_id.in_(list(grupos.keys()))
                )
                result = await db.execute(stmt)
                existing_rows = result.scalars().all()
                existing_map = {r.reproduccion_id: r for r in existing_rows}

                # 3. Procesar cada grupo con 1 sola operación DB
                now = datetime.utcnow()
                new_rows = []

                for rid, eventos_grupo in grupos.items():
                    existing = existing_map.get(rid)

                    if existing is None:
                        # Crear 1 objeto en memoria aplicando eventos en orden
                        row = None
                        for ev in eventos_grupo:
                            tipo = ev.get("tipo_evento")
                            if tipo not in ("START", "COMPLETED", "INTERRUPTED"):
                                continue
                            if row is None:
                                row = ReproduccionMetrica(
                                    reproduccion_id=rid,
                                    dispositivo_id=ev["dispositivo_id"],
                                    banner_id=ev["banner_id"],
                                    titulo=ev.get("titulo"),
                                    duracion_total_seg=ev.get("duracion_total_seg"),
                                    segundos_reproducidos=ev.get("segundos_reproducidos"),
                                    porcentaje_completado=ev.get("porcentaje_completado"),
                                    cuartil_50=ev.get("cuartil_50") or False,
                                    cuartil_75=ev.get("cuartil_75") or False,
                                    cuartil_100=ev.get("cuartil_100") or False,
                                    completo=ev.get("completo") or False,
                                    motivo_fin=ev.get("motivo_fin"),
                                    fecha_creacion=now,
                                )
                                if tipo == "START":
                                    row.inicio_reproduccion = now
                                if tipo in ("COMPLETED", "INTERRUPTED"):
                                    row.fin_reproduccion = now
                            else:
                                _apply_evento(row, ev, now)
                        if row is not None:
                            new_rows.append(row)
                    else:
                        for ev in eventos_grupo:
                            _apply_evento(existing, ev, now)

                    total_ok += 1

                if new_rows:
                    db.add_all(new_rows)
                await db.commit()
            except Exception as e:
                await db.rollback()
                failed_raw.extend(sub_raw)
                logger.warning(
                    f"Sub-batch {i}-{i+len(sub_ev)} falló: {e}, "
                    f"{len(sub_raw)} eventos movidos a dead-letter"
                )
                continue

    return total_ok, failed_raw


async def bulk_insert_reproducciones():
    r = await get_metrics_redis()
    if r is None:
        logger.warning("Redis no disponible, saltando bulk insert")
        return

    lock_id = str(uuid.uuid4())
    acquired = await r.setnx(LOCK_KEY, lock_id)
    if not acquired:
        logger.info("Worker anterior aún en ejecución, saltando este ciclo")
        return
    await r.expire(LOCK_KEY, LOCK_TTL)

    total_global = 0
    pagina = 0
    errores = 0
    dead_letters = 0

    try:
        while True:
            raw = await r.lrange(BULK_KEY, 0, PAGE_SIZE - 1)
            if not raw:
                break

            eventos = []
            for item in raw:
                try:
                    eventos.append(json.loads(item))
                except json.JSONDecodeError:
                    logger.warning("Evento malformado en Redis, moviendo a dead-letter")
                    dead_letters += 1

            if not eventos:
                await r.ltrim(BULK_KEY, len(raw), -1)
                break

            pagina += 1
            try:
                ok, failed_raw = await asyncio.wait_for(
                    _process_page(eventos, raw),
                    timeout=PAGE_TIMEOUT,
                )
                total_global += ok

                if failed_raw:
                    dead_letters += len(failed_raw)
                    await r.lpush(DEAD_LETTER_KEY, *failed_raw)
                    await r.ltrim(DEAD_LETTER_KEY, 0, MAX_BULK_EVENTS - 1)

                await r.ltrim(BULK_KEY, len(raw), -1)

                if failed_raw:
                    logger.info(
                        f"Página {pagina}: {ok} reproducciones ok, {len(failed_raw)} a dead-letter"
                    )
                else:
                    logger.info(f"Página {pagina}: {ok} reproducciones procesadas")
            except asyncio.TimeoutError:
                errores += 1
                logger.warning(
                    f"Página {pagina}: timeout {PAGE_TIMEOUT}s en SQL Server, "
                    f"eventos retenidos en Redis para reintentar"
                )
                break
    finally:
        await r.eval(_RELEASE_LOCK_SCRIPT, 1, LOCK_KEY, lock_id)

    if errores == 0 and dead_letters == 0:
        logger.info(
            f"Bulk insert completado: {total_global} reproducciones en {pagina} página(s)"
        )
    elif errores == 0 and dead_letters > 0:
        logger.info(
            f"Bulk insert completado: {total_global} reproducciones, "
            f"{dead_letters} a dead-letter en {pagina} página(s)"
        )
    else:
        logger.warning(
            f"Bulk insert parcial: {total_global} reproducciones ok, "
            f"{dead_letters} dead-letter, {errores} página(s) con timeout"
        )
