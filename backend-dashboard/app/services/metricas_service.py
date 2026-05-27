import logging
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.metricas_por_sede import MetricasPorSede

logger = logging.getLogger("uvicorn.error")
TZ_VENEZUELA = timezone(timedelta(hours=-4))


def get_venezuela_now() -> datetime:
    return datetime.now(TZ_VENEZUELA).replace(tzinfo=None)


async def resumen_diario(db: AsyncSession, target_date: date) -> dict:
    stmt_totals = select(
        func.coalesce(func.sum(MetricasPorSede.reproducciones), 0).label("total_eventos"),
        func.coalesce(func.sum(MetricasPorSede.completados), 0).label("completados"),
        func.coalesce(func.sum(MetricasPorSede.validas_50), 0).label("validas_50"),
        func.coalesce(func.sum(MetricasPorSede.segundos_totales), 0).label("segundos_totales"),
    ).where(MetricasPorSede.fecha == target_date)
    totals = (await db.execute(stmt_totals)).one()

    stmt_banners = select(
        MetricasPorSede.titulo,
        func.coalesce(func.sum(MetricasPorSede.reproducciones), 0).label("inicios"),
        func.coalesce(func.sum(MetricasPorSede.validas_50), 0).label("validas_50"),
    ).where(
        MetricasPorSede.fecha == target_date
    ).group_by(
        MetricasPorSede.titulo,
    )
    rows = (await db.execute(stmt_banners)).all()

    total = totals.total_eventos or 0
    validas = totals.validas_50 or 0

    banners = []
    for row in rows:
        inicios_b = row.inicios or 0
        validas_b = row.validas_50 or 0
        vcr = round((validas_b / inicios_b * 100), 1) if inicios_b > 0 else 0.0
        banners.append({
            "titulo": row.titulo or "Sin título",
            "inicios": inicios_b,
            "validas_50": validas_b,
            "vcr": vcr,
        })

    return {
        "total_eventos": total,
        "inicios": total,
        "validas_50": validas,
        "ver_total": 0,
        "tv_total": 0,
        "banners": banners,
    }


async def tendencia_14d(db: AsyncSession, hasta: date) -> list[dict]:
    desde = hasta - timedelta(days=13)
    results = []
    for i in range(14):
        dia = desde + timedelta(days=i)
        stmt = select(
            func.coalesce(func.sum(MetricasPorSede.validas_50), 0).label("validas"),
        ).where(MetricasPorSede.fecha == dia)
        row = (await db.execute(stmt)).one()
        results.append({
            "fecha": dia.isoformat(),
            "tv_estimadas": 0,
            "ver_validas": row.validas or 0,
        })
    return results
