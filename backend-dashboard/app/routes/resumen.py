from datetime import datetime, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, cast, Date
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.dependencies import get_current_cliente
from app.models.servidor_secundario import ServidorSecundario
from app.models.dispositivo import Dispositivo
from app.models.publicidad import Publicidad
from app.models.usuario import Usuario
from app.models.asignacion import PublicidadAsignacion
from app.services.server_service import HEARTBEAT_OFFLINE_MINUTES, _utcnow

router = APIRouter(tags=["resumen"])
logger = logging.getLogger("uvicorn.error")


@router.get("/resumen")
async def obtener_resumen(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    try:
        now = _utcnow()
        umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

        # Servidores
        stmt_serv = select(ServidorSecundario).options(selectinload(ServidorSecundario.dispositivos)).order_by(ServidorSecundario.nombre)
        result_serv = await db.execute(stmt_serv)
        servidores = result_serv.scalars().all()

        servidores_total = len(servidores)
        servidores_online = sum(1 for s in servidores if s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral)

        # Dispositivos
        stmt_disp_total = select(func.count(Dispositivo.id))
        stmt_disp_online = select(func.count(Dispositivo.id)).where(Dispositivo.online == True)
        dispositivos_total = (await db.execute(stmt_disp_total)).scalar() or 0
        dispositivos_online = (await db.execute(stmt_disp_online)).scalar() or 0

        # Banners
        stmt_banners_total = select(func.count(Publicidad.IdPublicidad))
        stmt_banners_activos = select(func.count(Publicidad.IdPublicidad)).where(
            Publicidad.Activo == True, Publicidad.FechaFin > now
        )
        stmt_banners_vencidos = select(func.count(Publicidad.IdPublicidad)).where(
            Publicidad.FechaFin < now
        )
        stmt_banners_reproduciendose = select(func.count(Publicidad.IdPublicidad)).where(
            Publicidad.Activo == True, Publicidad.FechaInicio <= now, Publicidad.FechaFin >= now
        )
        banners_total = (await db.execute(stmt_banners_total)).scalar() or 0
        banners_activos = (await db.execute(stmt_banners_activos)).scalar() or 0
        banners_vencidos = (await db.execute(stmt_banners_vencidos)).scalar() or 0
        banners_reproduciendose = (await db.execute(stmt_banners_reproduciendose)).scalar() or 0

        # Usuarios
        stmt_usu_total = select(func.count(Usuario.id))
        stmt_usu_activos = select(func.count(Usuario.id)).where(Usuario.activo == True)
        usuarios_total = (await db.execute(stmt_usu_total)).scalar() or 0
        usuarios_activos = (await db.execute(stmt_usu_activos)).scalar() or 0

        # Servidores detalle
        servidores_detalle = []
        for s in servidores:
            online = s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral
            disp_total = len(s.dispositivos) if s.dispositivos else 0
            disp_online = sum(1 for d in (s.dispositivos or []) if d.online)
            almacenamiento_total = s.almacenamiento_total or 0
            almacenamiento_usado = s.almacenamiento_usado or 0
            porcentaje_uso = round((almacenamiento_usado / almacenamiento_total * 100), 1) if almacenamiento_total > 0 else 0
            servidores_detalle.append({
                "id": s.id,
                "nombre": s.nombre,
                "ip": s.ip,
                "online": online,
                "porcentaje_uso": porcentaje_uso,
                "almacenamiento_total": almacenamiento_total,
                "almacenamiento_usado": almacenamiento_usado,
                "dispositivos_total": disp_total,
                "dispositivos_online": disp_online,
            })

        # Banners por servidor
        stmt_bps = select(
            PublicidadAsignacion.servidor_id,
            func.count(PublicidadAsignacion.id).label("cantidad"),
        ).group_by(PublicidadAsignacion.servidor_id)

        result_bps = await db.execute(stmt_bps)
        bps_rows = result_bps.all()

        serv_dict = {s.id: s.nombre for s in servidores}
        banners_por_servidor = [
            {
                "servidor_id": row.servidor_id,
                "nombre": serv_dict.get(row.servidor_id, f"ID {row.servidor_id}"),
                "cantidad": row.cantidad,
            }
            for row in bps_rows
        ]

        # Historial subidas (últimos 30 días)
        hace_30 = now - timedelta(days=30)
        stmt_hist = select(
            cast(Publicidad.UpdatedAt, Date).label("fecha"),
            func.count(Publicidad.IdPublicidad).label("cantidad"),
        ).where(Publicidad.UpdatedAt >= hace_30).group_by(
            cast(Publicidad.UpdatedAt, Date)
        ).order_by(cast(Publicidad.UpdatedAt, Date))

        result_hist = await db.execute(stmt_hist)
        historial_subidas = [
            {"fecha": str(row.fecha), "cantidad": row.cantidad}
            for row in result_hist.all()
        ]

        return {
            "success": True,
            "servidores": {
                "total": servidores_total,
                "online": servidores_online,
                "offline": servidores_total - servidores_online,
            },
            "dispositivos": {
                "total": dispositivos_total,
                "online": dispositivos_online,
                "offline": dispositivos_total - dispositivos_online,
            },
            "banners": {
                "total": banners_total,
                "programados": banners_activos,
                "inactivos": banners_total - banners_activos - banners_vencidos,
                "vencidos": banners_vencidos,
                "reproduciendose": banners_reproduciendose,
            },
            "usuarios": {
                "total": usuarios_total,
                "activos": usuarios_activos,
            },
            "servidores_detalle": servidores_detalle,
            "banners_por_servidor": banners_por_servidor,
            "historial_subidas": historial_subidas,
        }
    except Exception as e:
        logger.error("Error al obtener resumen: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")
