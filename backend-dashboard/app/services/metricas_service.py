import logging
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.metricas_por_sede import MetricasPorSede
from app.models.servidor_secundario import ServidorSecundario

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

    stmt_totals_tipo = select(
        MetricasPorSede.tipo_dispositivo,
        func.coalesce(func.sum(MetricasPorSede.validas_50), 0).label("validas"),
    ).where(
        MetricasPorSede.fecha == target_date
    ).group_by(
        MetricasPorSede.tipo_dispositivo,
    )
    rows_tipo = (await db.execute(stmt_totals_tipo)).all()

    ver_total = 0
    tv_total = 0
    for r in rows_tipo:
        if r.tipo_dispositivo == "televisor":
            tv_total = r.validas or 0
        else:
            ver_total = r.validas or 0

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
        "ver_total": ver_total,
        "tv_total": tv_total,
        "banners": banners,
    }


async def resumen_por_sede(db: AsyncSession, target_date: date) -> list[dict]:
    stmt = select(
        MetricasPorSede.servidor_id,
        ServidorSecundario.nombre,
        MetricasPorSede.banner_id,
        MetricasPorSede.titulo,
        MetricasPorSede.reproducciones,
        MetricasPorSede.validas_50,
        MetricasPorSede.segundos_totales,
    ).outerjoin(
        ServidorSecundario,
        MetricasPorSede.servidor_id == ServidorSecundario.id,
    ).where(
        MetricasPorSede.fecha == target_date
    ).order_by(
        MetricasPorSede.servidor_id,
        MetricasPorSede.reproducciones.desc(),
    )
    rows = (await db.execute(stmt)).all()

    sedes_map: dict[int, dict] = {}
    for row in rows:
        sid = row.servidor_id
        if sid not in sedes_map:
            sedes_map[sid] = {
                "servidor_id": sid,
                "nombre": row.nombre or f"Sede #{sid}",
                "total_reproducciones": 0,
                "total_validas_50": 0,
                "banners": [],
            }
        sedes_map[sid]["total_reproducciones"] += row.reproducciones or 0
        sedes_map[sid]["total_validas_50"] += row.validas_50 or 0
        vcr = round((row.validas_50 / row.reproducciones * 100), 1) if (row.reproducciones or 0) > 0 else 0.0
        sedes_map[sid]["banners"].append({
            "banner_id": row.banner_id,
            "titulo": row.titulo or "Sin título",
            "reproducciones": row.reproducciones or 0,
            "validas_50": row.validas_50 or 0,
            "vcr": vcr,
        })

    sedes = list(sedes_map.values())
    for s in sedes:
        total_r = s["total_reproducciones"]
        total_v = s["total_validas_50"]
        s["vcr_general"] = round((total_v / total_r * 100), 1) if total_r > 0 else 0.0
    return sedes


async def tendencia_14d(db: AsyncSession, hasta: date) -> list[dict]:
    desde = hasta - timedelta(days=13)
    results = []
    for i in range(14):
        dia = desde + timedelta(days=i)
        stmt = select(
            MetricasPorSede.tipo_dispositivo,
            func.coalesce(func.sum(MetricasPorSede.validas_50), 0).label("validas"),
        ).where(
            MetricasPorSede.fecha == dia
        ).group_by(
            MetricasPorSede.tipo_dispositivo,
        )
        rows = (await db.execute(stmt)).all()
        ver_validas = 0
        tv_estimadas = 0
        for r in rows:
            if r.tipo_dispositivo == "televisor":
                tv_estimadas = r.validas or 0
            else:
                ver_validas = r.validas or 0
        results.append({
            "fecha": dia.isoformat(),
            "tv_estimadas": tv_estimadas,
            "ver_validas": ver_validas,
        })
    return results
