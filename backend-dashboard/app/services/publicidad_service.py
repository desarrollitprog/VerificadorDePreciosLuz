"""
Servicio de gestión de publicidad.
Ejecutado periódicamente para expirar banners vencidos.
"""
import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocalUsuarios
from app.models.publicidad import Publicidad
from app.models.servidor_secundario import ServidorSecundario
from app.utils.logger import StructuredLogger
from app.services.notificacion_service import crear_notificacion_sistema

log = StructuredLogger("publicidad_service")


def get_venezuela_now():
    tz = timezone(timedelta(hours=-4))
    return datetime.now(tz).replace(tzinfo=None)


# Margen solo para logs, no para expiración real (60s después de fecha_fin)
MARGEN_EXPIRACION_SEGUNDOS = 0


async def notificar_banner_expirado(banner_id: int, titulo: str) -> None:
    """
    Envía notificación WebSocket a todos los servidores sobre banner vencido.
    """
    mensaje = {
        "type": "BANNER_EXPIRED",
        "banner_id": banner_id,
        "titulo": titulo
    }
    
    try:
        # Obtener URLs de servidores desde BD
        async with AsyncSessionLocalUsuarios() as db:
            stmt = select(ServidorSecundario.Url).where(ServidorSecundario.Activo == True)
            result = await db.execute(stmt)
            servidores = result.scalars().all()
        
        for api_url in servidores:
            if not api_url:
                continue
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(f"{api_url}/ws/broadcast", json=mensaje)
                    log.info("notificacion_enviada", banner_id=banner_id, api_url=api_url)
            except Exception as e:
                log.warning("notificacion_fallo", api_url=api_url, error=str(e))
    except Exception as e:
        log.error("obtener_servidores_fallo", error=str(e))


async def expirar_banners_vencidos():
    """
    Expirar banners vencidos estableciendo activo=False.
    Se ejecuta cada 3.5 minutos por el scheduler.
    """
    log.info("expirar_banners_inicio")
    
    try:
        async with AsyncSessionLocalUsuarios() as db:
            now = get_venezuela_now()
            
            # Buscar banners activos cuya fecha_fin ya pasó
            stmt = (
                select(Publicidad)
                .where(Publicidad.Activo == True)
                .where(Publicidad.FechaFin.isnot(None))
            )
            result = await db.execute(stmt)
            banners = result.scalars().all()
            
            vencidos_banners = []
            for banner in banners:
                # Solo marcar vencido cuando YA PASÓ fecha_fin + margen
                fecha_vencimiento = banner.FechaFin + timedelta(seconds=MARGEN_EXPIRACION_SEGUNDOS) if banner.FechaFin else None
                if banner.FechaFin and fecha_vencimiento and fecha_vencimiento < now:
                    # Actualizar activo a False
                    banner.Activo = False
                    titulo = banner.Titulo or f"Banner #{banner.IdPublicidad}"
                    log.info(
                        "banner_expirado",
                        banner_id=banner.IdPublicidad,
                        titulo=titulo,
                        fecha_fin=banner.FechaFin.isoformat()
                    )
                    vencidos_banners.append({
                        "id": banner.IdPublicidad,
                        "titulo": titulo,
                        "fecha_fin": banner.FechaFin.strftime('%d/%m/%Y %H:%M')
                    })
                    
                    # Notificar a servidores secundarios
                    await notificar_banner_expirado(banner.IdPublicidad, titulo)
            
            if vencidos_banners:
                await db.commit()
                log.info("banners_expirados_ok", cantidad=len(vencidos_banners))
                
                # Crear notificaciones DESPUÉS del commit
                for banner_info in vencidos_banners:
                    try:
                        await crear_notificacion_sistema(
                            db,
                            tipo="PUBLICIDAD_VENCIDA",
                            descripcion=f"La publicidad '{banner_info['titulo']}' ha vencido y fue eliminada automáticamente. Fecha fin: {banner_info['fecha_fin']}",
                        )
                        log.info("notificacion_creada", banner_id=banner_info['id'])
                    except Exception as e:
                        log.error("error_notificacion", error=str(e))
            else:
                log.info("sin_banners_vencidos")
                
    except Exception as e:
        log.error("expirar_banners_error", error=str(e))