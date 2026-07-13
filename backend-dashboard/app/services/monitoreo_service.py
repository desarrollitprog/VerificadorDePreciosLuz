"""
Servicio de monitoreo de sesiones de dispositivos.
Ejecutado cada 3.5 minutos por el scheduler.
"""
from datetime import datetime, timedelta
import time
import asyncio
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
    Las llamadas HTTP a servidores online se hacen EN PARALELO.
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

            # Paso 1: Separar servidores online/offline
            servidores_online = []
            servidores_offline = []
            for s in servidores:
                if s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral:
                    servidores_online.append(s)
                else:
                    servidores_offline.append(s)

            # Paso 2: Procesar servidores offline (sin HTTP)
            for s in servidores_offline:
                servidores_procesados += 1
                for dispositivo in dispositivo_por_codigo.values():
                    if dispositivo.servidor_id == s.id:
                        if dispositivo.online:
                            await _cerrar_sesion_activa(db, dispositivo.codigo_kiosko, now)
                            sesiones_cerradas += 1
                        dispositivo.online = False
                        dispositivos_actualizados += 1

            # Paso 3: Llamar a todos los servidores online EN PARALELO
            resultados = await asyncio.gather(
                *[_obtener_dispositivos_de_servidor(s.ip) for s in servidores_online],
                return_exceptions=True
            )

            # Paso 4: Procesar cada servidor online con su resultado pre-fetch
            for s, dispositivos_runtime in zip(servidores_online, resultados):
                servidores_procesados += 1

                if isinstance(dispositivos_runtime, Exception) or not dispositivos_runtime:
                    errores += 1
                    # Si falló la consulta, tratar todos sus dispositivos como offline
                    for dispositivo in dispositivo_por_codigo.values():
                        if dispositivo.servidor_id == s.id:
                            if dispositivo.online:
                                await _cerrar_sesion_activa(db, dispositivo.codigo_kiosko, now)
                                sesiones_cerradas += 1
                            dispositivo.online = False
                            dispositivos_actualizados += 1
                    continue

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
                            tipo=info.get("device_type", "verificador"),
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
    """Cierra sesiones huérfanas y crea una nueva sesión para el dispositivo."""
    await _cerrar_sesion_activa(db, dispositivo_id, inicio)
    sesion = DispositivoSesion(
        dispositivo_id=dispositivo_id,
        inicio=inicio,
    )
    db.add(sesion)
    await db.flush()


async def _cerrar_sesion_activa(db: AsyncSession, dispositivo_id: str, fin: datetime) -> None:
    """Cierra todas las sesiones activas del dispositivo."""
    stmt_sesion = select(DispositivoSesion).where(
        DispositivoSesion.dispositivo_id == dispositivo_id,
        DispositivoSesion.fin == None
    )
    result_sesion = await db.execute(stmt_sesion)
    sesiones_activas = result_sesion.scalars().all()
    for sesion in sesiones_activas:
        sesion.fin = fin
        sesion.duracion_segundos = int((fin - sesion.inicio).total_seconds())
    if sesiones_activas:
        await db.flush()