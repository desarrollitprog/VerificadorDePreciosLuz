import logging
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, cast, case, Date, Integer, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.reproduccion_metrica import ReproduccionMetrica
from app.models.metricas_diarias import MetricasDiarias
from app.models.dispositivo import Dispositivo

logger = logging.getLogger("uvicorn.error")

TABLA_LIVE_DAYS = 1


def _tabla(target_date: date, today: date | None = None):
    if today is None:
        today = date.today()
    if target_date >= today - timedelta(days=TABLA_LIVE_DAYS):
        return ReproduccionMetrica
    return MetricasDiarias


async def resumen_diario(db: AsyncSession, target_date: date) -> dict:
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())
    tabla = _tabla(target_date)

    if tabla is ReproduccionMetrica:
        total = (await db.execute(
            select(func.count(ReproduccionMetrica.id)).where(
                ReproduccionMetrica.fecha_creacion >= day_start,
                ReproduccionMetrica.fecha_creacion <= day_end,
            )
        )).scalar() or 0

        validas = (await db.execute(
            select(func.count(ReproduccionMetrica.id)).where(
                ReproduccionMetrica.fecha_creacion >= day_start,
                ReproduccionMetrica.fecha_creacion <= day_end,
                (ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True),
            )
        )).scalar() or 0

        inicios = (await db.execute(
            select(func.count(ReproduccionMetrica.id)).where(
                ReproduccionMetrica.fecha_creacion >= day_start,
                ReproduccionMetrica.fecha_creacion <= day_end,
                ReproduccionMetrica.motivo_fin == None,
                ReproduccionMetrica.completo == False,
                ReproduccionMetrica.fin_reproduccion == None,
            )
        )).scalar() or 0

        ver_ids = select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "verificador")
        tv_ids = select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "televisor")

        ver_total = (await db.execute(
            select(func.count(ReproduccionMetrica.id)).where(
                ReproduccionMetrica.fecha_creacion >= day_start,
                ReproduccionMetrica.fecha_creacion <= day_end,
                ReproduccionMetrica.dispositivo_id.in_(ver_ids),
            )
        )).scalar() or 0

        tv_total = (await db.execute(
            select(func.count(ReproduccionMetrica.id)).where(
                ReproduccionMetrica.fecha_creacion >= day_start,
                ReproduccionMetrica.fecha_creacion <= day_end,
                ReproduccionMetrica.dispositivo_id.in_(tv_ids),
            )
        )).scalar() or 0

        rows = (await db.execute(
            select(
                ReproduccionMetrica.banner_id,
                ReproduccionMetrica.titulo,
                func.count(ReproduccionMetrica.id).label("inicios"),
                func.sum(
                    case(
                        ((ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True), 1),
                        else_=0
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
        )).all()
    else:
        rows = (await db.execute(
            select(
                MetricasDiarias.banner_id,
                MetricasDiarias.titulo,
                MetricasDiarias.inicios,
                MetricasDiarias.validas_50,
                case(
                    (MetricasDiarias.inicios > 0, func.round(MetricasDiarias.validas_50 * 100.0 / MetricasDiarias.inicios, 1)),
                    else_=0.0
                ).label("vcr_promedio"),
            ).where(
                MetricasDiarias.fecha == target_date,
            ).order_by(MetricasDiarias.banner_id)
        )).all()

        totals = (await db.execute(
            select(
                func.coalesce(func.sum(MetricasDiarias.inicios), 0).label("inicios"),
                func.coalesce(func.sum(MetricasDiarias.completados), 0).label("completados"),
                func.coalesce(func.sum(MetricasDiarias.interrumpidos), 0).label("interrumpidos"),
                func.coalesce(func.sum(MetricasDiarias.validas_50), 0).label("validas_50"),
                func.coalesce(func.sum(MetricasDiarias.segundos_totales), 0).label("segundos_totales"),
            ).where(MetricasDiarias.fecha == target_date)
        )).one()

        total = totals.inicios + totals.completados + totals.interrumpidos
        inicios = totals.inicios
        validas = totals.validas_50
        ver_total = 0
        tv_total = 0

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
        tabla = _tabla(dia)

        if tabla is ReproduccionMetrica:
            day_start = datetime.combine(dia, datetime.min.time())
            day_end = datetime.combine(dia, datetime.max.time())

            ver_ids = select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "verificador")

            ver_validas = (await db.execute(
                select(func.count(ReproduccionMetrica.id)).where(
                    ReproduccionMetrica.fecha_creacion >= day_start,
                    ReproduccionMetrica.fecha_creacion <= day_end,
                    (ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True),
                    ReproduccionMetrica.dispositivo_id.in_(ver_ids),
                )
            )).scalar() or 0

            tv_ids = select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "televisor")

            tv_estimadas = (await db.execute(
                select(func.count(ReproduccionMetrica.id)).where(
                    ReproduccionMetrica.fecha_creacion >= day_start,
                    ReproduccionMetrica.fecha_creacion <= day_end,
                    ReproduccionMetrica.dispositivo_id.in_(tv_ids),
                )
            )).scalar() or 0
        else:
            totals = (await db.execute(
                select(
                    func.coalesce(func.sum(MetricasDiarias.ver_validas), 0).label("ver_validas"),
                    func.coalesce(func.sum(MetricasDiarias.tv_total), 0).label("tv"),
                ).where(MetricasDiarias.fecha == dia)
            )).one()
            ver_validas = totals.ver_validas
            tv_estimadas = totals.tv

        results.append({
            "fecha": dia.isoformat(),
            "tv_estimadas": tv_estimadas,
            "ver_validas": ver_validas,
        })

    return results


async def agregar_metricas_diarias(db: AsyncSession, target_date: date | None = None):
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())

    ver_ids = select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "verificador")
    tv_ids = select(Dispositivo.codigo_kiosko).where(Dispositivo.tipo == "televisor")

    rows = (await db.execute(
        select(
            ReproduccionMetrica.banner_id,
            ReproduccionMetrica.titulo,
            ReproduccionMetrica.duracion_total_seg,
            func.count(ReproduccionMetrica.id).label("total"),
            func.sum(case((ReproduccionMetrica.completo == True, 1), else_=0)).label("completados"),
            func.sum(case((ReproduccionMetrica.motivo_fin == "interruption", 1), else_=0)).label("interrumpidos"),
            func.sum(case(
                ((ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True), 1),
                else_=0
            )).label("validas_50"),
            func.sum(case(
                (and_(
                    ReproduccionMetrica.motivo_fin == None,
                    ReproduccionMetrica.completo == False,
                    ReproduccionMetrica.fin_reproduccion == None,
                ), 1),
                else_=0
            )).label("inicios"),
            func.coalesce(func.sum(ReproduccionMetrica.segundos_reproducidos), 0).label("segundos_totales"),
            func.sum(case(
                (and_(
                    ReproduccionMetrica.dispositivo_id.in_(ver_ids),
                    (ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True),
                ), 1),
                else_=0
            )).label("ver_validas"),
            func.sum(case(
                (ReproduccionMetrica.dispositivo_id.in_(tv_ids), 1),
                else_=0
            )).label("tv_total"),
        ).where(
            ReproduccionMetrica.fecha_creacion >= day_start,
            ReproduccionMetrica.fecha_creacion <= day_end,
        ).group_by(
            ReproduccionMetrica.banner_id,
            ReproduccionMetrica.titulo,
            ReproduccionMetrica.duracion_total_seg,
        )
    )).all()

    count = 0
    for row in rows:
        existing = (await db.execute(
            select(MetricasDiarias).where(
                MetricasDiarias.fecha == target_date,
                MetricasDiarias.banner_id == row.banner_id,
            )
        )).scalars().first()

        if existing:
            existing.inicios = row.inicios
            existing.completados = row.completados
            existing.interrumpidos = row.interrumpidos
            existing.validas_50 = row.validas_50
            existing.segundos_totales = row.segundos_totales
            existing.ver_validas = row.ver_validas
            existing.tv_total = row.tv_total
        else:
            db.add(MetricasDiarias(
                fecha=target_date,
                banner_id=row.banner_id,
                titulo=row.titulo,
                duracion_total_seg=row.duracion_total_seg,
                inicios=row.inicios,
                completados=row.completados,
                interrumpidos=row.interrumpidos,
                validas_50=row.validas_50,
                segundos_totales=row.segundos_totales,
                ver_validas=row.ver_validas,
                tv_total=row.tv_total,
            ))
        count += 1

    await db.commit()
    logger.info(f"Metricas diarias agregadas para {target_date}: {count} banners")
    return count


async def consolidar_por_hora(db: AsyncSession) -> dict:
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    stmt = select(
        ReproduccionMetrica.banner_id,
        func.count(ReproduccionMetrica.id).label("eventos"),
        func.sum(
            case(
                ((ReproduccionMetrica.completo == True) | (ReproduccionMetrica.cuartil_50 == True), 1),
                else_=0
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
    corte = date.today() - timedelta(days=TABLA_LIVE_DAYS)
    corte_dt = datetime.combine(corte, datetime.min.time())
    stmt = select(func.count(ReproduccionMetrica.id)).where(
        ReproduccionMetrica.fecha_creacion < corte_dt
    )
    total = (await db.execute(stmt)).scalar() or 0
    if total > 0:
        from sqlalchemy import delete
        d_stmt = delete(ReproduccionMetrica).where(
            ReproduccionMetrica.fecha_creacion < corte_dt
        )
        await db.execute(d_stmt)
        await db.commit()
        logger.info(f"Limpieza de métricas: {total} registros eliminados (anteriores a {corte})")
    return total
