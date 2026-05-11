"""
Servicio de monitoreo de sesiones de dispositivos.
Ejecutado cada 3.5 minutos por el scheduler.
"""
from datetime import datetime, timedelta
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocalUsuarios
from app.models.dispositivo import Dispositivo
from app.models.dispositivo_sesion import DispositivoSesion
from app.models.servidor_secundario import ServidorSecundario
from app.services.server_service import HEARTBEAT_OFFLINE_MINUTES, _utcnow, _obtener_dispositivos_de_servidor
from app.utils.logger import StructuredLogger

log = StructuredLogger("monitoreo")


async def actualizar_sesiones_dispositivos() -> None:
    """
    Función que se ejecuta cada 3.5 minutos.
    Consulta /devices/status de cada servidor secundario
    y actualiza sesiones en BD (DispositivoSesion).
    """
    start_time = time.perf_counter()
    log.info("monitoreo_inicio")
    
    sesiones_creadas = 0
    sesiones_cerradas = 0
    dispositivos_actualizados = 0
    servidores_procesados = 0
    errores = 0
    
    try:
        async with AsyncSessionLocalUsuarios() as db:
            now = _utcnow()
            umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

            stmt = select(ServidorSecundario)
            result = await db.execute(stmt)
            servidores = result.scalars().all()

            dispositivos_result = await db.execute(select(Dispositivo))
            dispositivos_db = list(dispositivos_result.scalars().all())
            dispositivo_por_codigo: dict[str, Dispositivo] = {
                d.codigo_kiosko: d for d in dispositivos_db
            }

            for s in servidores:
                servidores_procesados += 1
                online = s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral

                if not online:
                    for dispositivo in dispositivo_por_codigo.values():
                        if dispositivo.servidor_id == s.id:
                            if dispositivo.online:
                                await _cerrar_sesion_activa(db, dispositivo.codigo_kiosko, now)
                                sesiones_cerradas += 1
                            dispositivo.online = False
                            dispositivos_actualizados += 1
                    continue

                dispositivos_runtime = await _obtener_dispositivos_de_servidor(s.ip)
                if not dispositivos_runtime:
                    errores += 1
                    
                runtime_por_codigo = {d["device_id"]: d for d in dispositivos_runtime}
                vistos = set(runtime_por_codigo.keys())

                for codigo, info in runtime_por_codigo.items():
                    dispositivo = dispositivo_por_codigo.get(codigo)
                    ahora_online = bool(info.get("online", False))

                    if dispositivo is None:
                        dispositivo = Dispositivo(
                            codigo_kiosko=codigo,
                            online=ahora_online,
                            servidor_id=s.id,
                        )
                        db.add(dispositivo)
                        dispositivo_por_codigo[codigo] = dispositivo
                        dispositivos_actualizados += 1

                        if ahora_online:
                            await _crear_nueva_sesion(db, codigo, now)
                            sesiones_creadas += 1
                    else:
                        estaba_online = dispositivo.online

                        if not estaba_online and ahora_online:
                            await _crear_nueva_sesion(db, codigo, now)
                            sesiones_creadas += 1
                        elif estaba_online and not ahora_online:
                            await _cerrar_sesion_activa(db, codigo, now)
                            sesiones_cerradas += 1

                        dispositivo.online = ahora_online
                        dispositivo.servidor_id = s.id
                        dispositivos_actualizados += 1

                for dispositivo in dispositivo_por_codigo.values():
                    if dispositivo.servidor_id == s.id and dispositivo.codigo_kiosko not in vistos:
                        if dispositivo.online:
                            await _cerrar_sesion_activa(db, dispositivo.codigo_kiosko, now)
                            sesiones_cerradas += 1
                        dispositivo.online = False
                        dispositivos_actualizados += 1

            await db.commit()

        duration = round(time.perf_counter() - start_time, 2)
        log.info(
            "monitoreo_completado",
            servidores=servidores_procesados,
            dispositivos_actualizados=dispositivos_actualizados,
            sesiones_creadas=sesiones_creadas,
            sesiones_cerradas=sesiones_cerradas,
            errores=errores,
            duracion_segundos=duration
        )
    except Exception as e:
        log.error("monitoreo_error", error=str(e))


async def _crear_nueva_sesion(db: AsyncSession, dispositivo_id: str, inicio: datetime) -> None:
    """Crea una nueva sesión para el dispositivo."""
    sesion = DispositivoSesion(
        dispositivo_id=dispositivo_id,
        inicio=inicio,
    )
    db.add(sesion)
    await db.flush()


async def _cerrar_sesion_activa(db: AsyncSession, dispositivo_id: str, fin: datetime) -> None:
    """Cierra la sesión activa del dispositivo."""
    stmt_sesion = select(DispositivoSesion).where(
        DispositivoSesion.dispositivo_id == dispositivo_id,
        DispositivoSesion.fin == None
    )
    result_sesion = await db.execute(stmt_sesion)
    sesion_activa = result_sesion.scalars().first()
    if sesion_activa:
        sesion_activa.fin = fin
        duracion = int((fin - sesion_activa.inicio).total_seconds())
        sesion_activa.duracion_segundos = duracion
        await db.flush()