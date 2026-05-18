from datetime import datetime
import logging
from typing import Any
from sqlalchemy import select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.dispositivo import Dispositivo
from app.models.dispositivo_sesion import DispositivoSesion
from app.models.servidor_secundario import ServidorSecundario
from app.services.notificacion_service import registrar_accion
import httpx

logger = logging.getLogger("uvicorn.error")

RESTART_TIMEOUT = 60


async def rename_device(
    db: AsyncSession,
    device_id: str,
    nuevo_nombre: str | None,
    user_id: int | None,
) -> dict[str, Any]:
    stmt = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result = await db.execute(stmt)
    dispositivo = result.scalars().first()
    result.close()

    if not dispositivo:
        return {"success": False, "status_code": 404, "detail": "Dispositivo no encontrado"}

    nombre_amigable = (nuevo_nombre or "").strip()
    dispositivo.nombre_amigable = nombre_amigable if nombre_amigable else None

    await db.commit()

    if user_id is not None:
        nombre_viejo = dispositivo.nombre_amigable or dispositivo.codigo_kiosko
        try:
            await registrar_accion(
                db,
                user_id,
                "RENOMBRAR_DISPOSITIVO",
                f"Dispositivo '{nombre_viejo}' ({dispositivo.codigo_kiosko}) renombrado a '{nuevo_nombre or ''}'",
                dispositivo_id=dispositivo.codigo_kiosko,
                servidor_id=dispositivo.servidor_id,
            )
        except Exception as e:
            logger.warning("No se pudo registrar auditoría de rename para %s: %s", dispositivo.codigo_kiosko, e)

    return {
        "success": True,
        "device_id": dispositivo.codigo_kiosko,
        "nombre_amigable": dispositivo.nombre_amigable,
    }


async def delete_device(
    db: AsyncSession,
    device_id: str,
    user_id: int | None,
) -> dict[str, Any]:
    stmt = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result = await db.execute(stmt)
    dispositivo = result.scalars().first()
    result.close()

    if not dispositivo:
        return {"success": False, "status_code": 404, "detail": "Dispositivo no encontrado"}

    from app.models.asignacion import PublicidadAsignacion

    stmt_asig = sql_delete(PublicidadAsignacion).where(
        PublicidadAsignacion.dispositivo_id == device_id
    )
    await db.execute(stmt_asig)

    stmt_ses = sql_delete(DispositivoSesion).where(
        DispositivoSesion.dispositivo_id == device_id
    )
    await db.execute(stmt_ses)

    servidor_id = dispositivo.servidor_id
    nombre_para_log = dispositivo.nombre_amigable or dispositivo.codigo_kiosko

    await db.delete(dispositivo)
    await db.commit()

    if servidor_id:
        stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == servidor_id)
        result_srv = await db.execute(stmt_srv)
        servidor = result_srv.scalars().first()

        if servidor:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.delete(f"http://{servidor.ip}:8000/devices/{device_id}")
                    if response.status_code == 200:
                        logger.info(f"Dispositivo {device_id} desvinculado del servidor {servidor.ip}: {response.status_code}")
                    else:
                        logger.warning(f"Dispositivo {device_id} no se pudo desvincular del servidor {servidor.ip}: {response.status_code}")
            except Exception as e:
                logger.warning(f"No se pudo desvincular {device_id} del servidor {servidor.ip}: {e}")

    if user_id is not None:
        try:
            await registrar_accion(
                db,
                user_id,
                "ELIMINAR_DISPOSITIVO",
                f"Dispositivo '{nombre_para_log}' ({device_id}) eliminado",
                dispositivo_id=device_id,
                servidor_id=servidor_id,
            )
        except Exception as e:
            logger.warning("No se pudo registrar auditoría de eliminación de dispositivo %s: %s", device_id, e)

    return {"success": True, "message": f"Dispositivo {device_id} eliminado correctamente"}


async def get_device_content(
    db: AsyncSession,
    device_id: str,
) -> dict[str, Any]:
    stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result_disp = await db.execute(stmt_disp)
    dispositivo = result_disp.scalars().first()

    if not dispositivo:
        return {"success": False, "status_code": 404, "detail": "Dispositivo no encontrado"}

    if not dispositivo.servidor_id:
        return {
            "device_id": device_id,
            "contenido": None,
            "message": "Dispositivo no asociado a servidor"
        }

    stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == dispositivo.servidor_id)
    result_srv = await db.execute(stmt_srv)
    servidor = result_srv.scalars().first()

    if not servidor:
        return {
            "device_id": device_id,
            "contenido": None,
            "message": "Servidor del dispositivo no encontrado"
        }

    servidor_ip = servidor.ip
    api_url = f"http://{servidor_ip}:8000/api/device-playing/{device_id}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(api_url)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "device_id": device_id,
                    "contenido": None,
                    "message": "Error al obtener contenido del servidor"
                }
    except Exception as e:
        logger.error(f"Error al obtener contenido del dispositivo {device_id}: %s", e)
        return {
            "device_id": device_id,
            "contenido": None,
            "message": f"Error de conexión: {str(e)}"
        }


async def reboot_device(
    db: AsyncSession,
    device_id: str,
    user_id: int | None,
    actor_name: str,
) -> dict[str, Any]:
    stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result_disp = await db.execute(stmt_disp)
    dispositivo = result_disp.scalars().first()

    if not dispositivo:
        return {"success": False, "status_code": 404, "detail": "Dispositivo no encontrado"}

    if not dispositivo.servidor_id:
        return {"success": False, "status_code": 400, "detail": "El dispositivo no está asociado a ningún servidor"}

    stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == dispositivo.servidor_id)
    result_srv = await db.execute(stmt_srv)
    servidor = result_srv.scalars().first()

    if not servidor:
        return {"success": False, "status_code": 404, "detail": "Servidor del dispositivo no encontrado"}

    servidor_ip = servidor.ip
    logger.info(f"[REINICIAR] Intentando reiniciar dispositivo {device_id} en servidor {servidor_ip}")

    api_url = f"http://{servidor_ip}:8000/api/comandos/{device_id}"
    logger.info(f"[REINICIAR] Llamando a: {api_url}")

    try:
        async with httpx.AsyncClient(timeout=RESTART_TIMEOUT) as client:
            logger.info(f"[REINICIAR] Enviando comando REINICIAR...")
            response = await client.post(
                api_url,
                json={"comando": "REINICIAR"},
            )
            logger.info(f"[REINICIAR] Respuesta recibida: status={response.status_code}")
            result = response.json()
            logger.info(f"[REINICIAR] Resultado: {result}")

            nombre_disp = dispositivo.nombre_amigable or device_id
            if result.get("success"):
                await registrar_accion(
                    db,
                    user_id,
                    "REINICIAR_DISPOSITIVO",
                    f"Dispositivo '{nombre_disp}' ({device_id}) reiniciado exitosamente por {actor_name}",
                    dispositivo_id=device_id,
                    servidor_id=servidor.id,
                )
            else:
                await registrar_accion(
                    db,
                    user_id,
                    "REINICIAR_DISPOSITIVO_FALLO",
                    f"Error al reiniciar '{nombre_disp}' ({device_id}): {result.get('message', 'Error desconocido')}",
                    dispositivo_id=device_id,
                    servidor_id=servidor.id,
                )

            return {"success": True, "result": result}

    except httpx.TimeoutException:
        return {"success": False, "status_code": 504, "detail": f"Timeout esperando confirmación del dispositivo ({RESTART_TIMEOUT}s)"}
    except Exception as e:
        logger.error(f"Error al reiniciar dispositivo {device_id}: %s", e)
        return {"success": False, "status_code": 500, "detail": f"Error al comunicarse con el servidor: {str(e)}"}


async def purge_device(
    db: AsyncSession,
    device_id: str,
    user_id: int | None,
    actor_name: str,
) -> dict[str, Any]:
    stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result_disp = await db.execute(stmt_disp)
    dispositivo = result_disp.scalars().first()

    if not dispositivo:
        return {"success": False, "status_code": 404, "detail": "Dispositivo no encontrado"}

    if not dispositivo.servidor_id:
        return {"success": False, "status_code": 400, "detail": "El dispositivo no está asociado a ningún servidor"}

    stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == dispositivo.servidor_id)
    result_srv = await db.execute(stmt_srv)
    servidor = result_srv.scalars().first()

    if not servidor:
        return {"success": False, "status_code": 404, "detail": "Servidor del dispositivo no encontrado"}

    servidor_ip = servidor.ip
    logger.info(f"[PURGE] Intentando limpiar cache de dispositivo {device_id} en servidor {servidor_ip}")

    api_url = f"http://{servidor_ip}:8000/api/comandos/{device_id}"
    logger.info(f"[PURGE] Llamando a: {api_url}")

    try:
        async with httpx.AsyncClient(timeout=RESTART_TIMEOUT) as client:
            logger.info(f"[PURGE] Enviando comando WIPE_AND_RESYNC...")
            response = await client.post(
                api_url,
                json={"comando": "WIPE_AND_RESYNC"},
            )
            logger.info(f"[PURGE] Respuesta recibida: status={response.status_code}")
            result = response.json()
            logger.info(f"[PURGE] Resultado: {result}")

            nombre_disp = dispositivo.nombre_amigable or device_id
            if result.get("success"):
                await registrar_accion(
                    db,
                    user_id,
                    "PURGA_DISPOSITIVO",
                    f"Cache de '{nombre_disp}' ({device_id}) limpiado y sincronizado exitosamente por {actor_name}",
                    dispositivo_id=device_id,
                    servidor_id=servidor.id,
                )
            else:
                await registrar_accion(
                    db,
                    user_id,
                    "PURGA_DISPOSITIVO_FALLO",
                    f"Error al limpiar cache de '{nombre_disp}' ({device_id}): {result.get('message', 'Error desconocido')}",
                    dispositivo_id=device_id,
                    servidor_id=servidor.id,
                )

            return {"success": True, "result": result}

    except httpx.TimeoutException:
        return {"success": False, "status_code": 504, "detail": f"Timeout esperando confirmación del dispositivo ({RESTART_TIMEOUT}s)"}
    except Exception as e:
        logger.error(f"Error al limpiar cache de dispositivo {device_id}: %s", e)
        return {"success": False, "status_code": 500, "detail": f"Error al comunicarse con el servidor: {str(e)}"}


async def program_reboot(
    db: AsyncSession,
    device_ids: list[str],
    hour: str,
    recurring: bool,
    user_id: int | None,
    actor_name: str,
) -> dict[str, Any]:
    dispositivos_ids = device_ids if device_ids else []

    if not dispositivos_ids:
        stmt = select(Dispositivo.codigo_kiosko)
        result = await db.execute(stmt)
        dispositivos_ids = [row[0] for row in result.fetchall()]

    if not dispositivos_ids:
        return {"success": False, "status_code": 400, "detail": "No hay dispositivos disponibles"}

    logger.info(f"[PROGRAMAR_REINICIO] Programando para {len(dispositivos_ids)} dispositivos, hour={hour}, recurring={recurring}")

    hour_parts = hour.split(':')
    if len(hour_parts) != 2:
        return {"success": False, "status_code": 400, "detail": "Formato de hora inválido. Use HH:MM"}

    resultados: dict[str, Any] = {
        "total": len(dispositivos_ids),
        "enviados": 0,
        "fallidos": 0,
        "details": []
    }

    for device_id in dispositivos_ids:
        try:
            stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
            result_disp = await db.execute(stmt_disp)
            dispositivo = result_disp.scalars().first()

            logger.info(f"[PROGRAMAR_REINICIO] Procesando {device_id}, hora_reinicio_actual={dispositivo.hora_reinicio if dispositivo else 'None'}")

            if not dispositivo or not dispositivo.servidor_id:
                resultados["fallidos"] += 1
                resultados["details"].append({"device_id": device_id, "status": "error", "message": "Dispositivo sin servidor"})
                continue

            stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == dispositivo.servidor_id)
            result_srv = await db.execute(stmt_srv)
            servidor = result_srv.scalars().first()

            if not servidor:
                resultados["fallidos"] += 1
                resultados["details"].append({"device_id": device_id, "status": "error", "message": "Servidor no encontrado"})
                continue

            servidor_ip = servidor.ip
            api_url = f"http://{servidor_ip}:8000/api/comandos/{device_id}"

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    api_url,
                    json={
                        "comando": "REINICIAR",
                        "hour": hour,
                        "recurring": recurring
                    }
                )

                if response.status_code == 200:
                    resultados["enviados"] += 1
                    resultados["details"].append({"device_id": device_id, "status": "enviado", "hour": hour, "recurring": recurring})

                    dispositivo.hora_reinicio = hour
                    dispositivo.reinicio_recurrente = recurring
                    await db.flush()
                    await db.refresh(dispositivo)
                    await db.commit()

                    logger.info(f"[PROGRAMAR_REINICIO] Guardado en BD: {device_id} hour={hour} recurrente={recurring}")
                else:
                    resultados["fallidos"] += 1
                    resultados["details"].append({"device_id": device_id, "status": "error", "message": f"HTTP {response.status_code}"})

        except Exception as e:
            logger.error(f"[PROGRAMAR_REINICIO] Error con {device_id}: {e}")
            resultados["fallidos"] += 1
            resultados["details"].append({"device_id": device_id, "status": "error", "message": str(e)})

    await registrar_accion(
        db,
        user_id,
        "PROGRAMAR_REINICIO_MASIVO",
        f"Reinicio programado por {actor_name}: {len(dispositivos_ids)} dispositivos, hour={hour}, recurring={recurring}",
    )

    return resultados
