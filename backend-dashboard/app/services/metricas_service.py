import logging
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, cast, Date, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.reproduccion_metrica import ReproduccionMetrica
from app.models.dispositivo import Dispositivo

logger = logging.getLogger("uvicorn.error")


async def resumen_diario(db: AsyncSession, target_date: date) -> dict:
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())

    stmt_total = select(func.count(ReproduccionMetrica.id)).where(
        ReproduccionMetrica.fecha_creacion >= day_start,
        ReproduccionMetrica.fecha_creacion <= day_end,
    )
    total = (await db.execute(stmt_total)).scalar() or 0

    stmt_validas = select(func.count(ReproduccionMetrica.id)).where(
        ReproduccionMetrica.fecha_creacion >= day_start,
        ReproduccionMetrica.fecha_creacion <= day_end,
        (ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True),
    )
    validas = (await db.execute(stmt_validas)).scalar() or 0

    stmt_inicios = select(func.count(ReproduccionMetrica.id)).where(
        ReproduccionMetrica.fecha_creacion >= day_start,
        ReproduccionMetrica.fecha_creacion <= day_end,
        ReproduccionMetrica.motivo_fin == None,
        ReproduccionMetrica.completo == False,
        ReproduccionMetrica.fin_reproduccion == None,
    )
    inicios = (await db.execute(stmt_inicios)).scalar() or 0

    stmt_ver = select(func.count(ReproduccionMetrica.id)).where(
        ReproduccionMetrica.fecha_creacion >= day_start,
        ReproduccionMetrica.fecha_creacion <= day_end,
        ReproduccionMetrica.dispositivo_id.in_(
            select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "verificador")
        ),
    )
    ver_total = (await db.execute(stmt_ver)).scalar() or 0

    stmt_tv = select(func.count(ReproduccionMetrica.id)).where(
        ReproduccionMetrica.fecha_creacion >= day_start,
        ReproduccionMetrica.fecha_creacion <= day_end,
        ReproduccionMetrica.dispositivo_id.in_(
            select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "televisor")
        ),
    )
    tv_total = (await db.execute(stmt_tv)).scalar() or 0

    stmt_banners = select(
        ReproduccionMetrica.banner_id,
        ReproduccionMetrica.titulo,
        func.count(ReproduccionMetrica.id).label("inicios"),
        func.sum(
            func.cast(
                (ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True),
                Integer,
            )
        ).label("validas_50"),
        func.avg(ReproduccionMetrica.porcentaje_completado).label("vcr_promedio"),
    ).where(
        ReproduccionMetrica.fecha_creacion >= day_start,
        ReproduccionMetrica.fecha_creacion <= day_end,
    ).group_by(
        ReproduccionMetrica.banner_id,
        ReproduccionMetrica.titulo,
    )

    rows = (await db.execute(stmt_banners)).all()
    banners = []
    for row in rows:
        inicios_b = row.inicios or 0
        validas_b = row.validas_50 or 0
        vcr = round((validas_b / inicios_b * 100), 1) if inicios_b > 0 else 0.0
        banners.append({
            "banner_id": row.banner_id,
            "titulo": row.titulo,
            "inicios": inicios_b,
            "validas_50": validas_b,
            "vcr": vcr,
        })

    return {
        "total_eventos": total,
        "inicios": inicios,
        "validas_50": validas,
        "ver_total": ver_total,
        "tv_total": tv_total,
        "banners": banners,
    }


async def tendencia_14d(db: AsyncSession, hasta: date) -> list[dict]:
    desde = hasta - timedelta(days=13)
    results = []
    for i in range(14):
        dia = desde + timedelta(days=i)
        day_start = datetime.combine(dia, datetime.min.time())
        day_end = datetime.combine(dia, datetime.max.time())

        stmt_validas = select(func.count(ReproduccionMetrica.id)).where(
            ReproduccionMetrica.fecha_creacion >= day_start,
            ReproduccionMetrica.fecha_creacion <= day_end,
            (ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True),
            ReproduccionMetrica.dispositivo_id.in_(
                select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "verificador")
            ),
        )
        ver_validas = (await db.execute(stmt_validas)).scalar() or 0

        stmt_tv = select(func.count(ReproduccionMetrica.id)).where(
            ReproduccionMetrica.fecha_creacion >= day_start,
            ReproduccionMetrica.fecha_creacion <= day_end,
            ReproduccionMetrica.dispositivo_id.in_(
                select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "televisor")
            ),
        )
        tv_completadas = (await db.execute(stmt_tv)).scalar() or 0

        results.append({
            "fecha": dia.isoformat(),
            "tv_estimadas": tv_completadas,
            "ver_validas": ver_validas,
        })

    return results


async def consolidar_por_hora(db: AsyncSession) -> dict:
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    stmt = select(
        ReproduccionMetrica.banner_id,
        func.count(ReproduccionMetrica.id).label("eventos"),
        func.sum(
            func.cast(
                (ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True),
                Integer,
            )
        ).label("validas"),
    ).where(
        ReproduccionMetrica.fecha_creacion >= hour_ago,
    ).group_by(ReproduccionMetrica.banner_id)

    rows = (await db.execute(stmt)).all()
    consolidado = []
    for row in rows:
        consolidado.append({
            "banner_id": row.banner_id,
            "eventos": row.eventos or 0,
            "validas": row.validas or 0,
            "hora": hour_ago.strftime("%Y-%m-%d %H:00"),
        })
    return {"hora": hour_ago.strftime("%Y-%m-%d %H:00"), "banners": consolidado}


async def limpiar_metricas_antiguas(db: AsyncSession) -> int:
    corte = datetime.utcnow() - timedelta(days=90)
    stmt = select(func.count(ReproduccionMetrica.id)).where(
        ReproduccionMetrica.fecha_creacion < corte
    )
    total = (await db.execute(stmt)).scalar() or 0
    if total > 0:
        from sqlalchemy import delete
        d_stmt = delete(ReproduccionMetrica).where(
            ReproduccionMetrica.fecha_creacion < corte
        )
        await db.execute(d_stmt)
        await db.commit()
        logger.info(f"Limpieza de métricas: {total} registros eliminados (anteriores a {corte.date()})")
    return total
