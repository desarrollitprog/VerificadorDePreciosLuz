import httpx
import os
import asyncio
from app.utils.logger import StructuredLogger, replicacion_logger

log = replicacion_logger

RETRY_MAX_ATTEMPTS = int(os.getenv("REPLICACION_RETRY_ATTEMPTS", "3"))
RETRY_MIN_WAIT = int(os.getenv("REPLICACION_RETRY_MIN_WAIT", "2"))
RETRY_MAX_WAIT = int(os.getenv("REPLICACION_RETRY_MAX_WAIT", "10"))

def is_retryable_error(exception):
    """Determina si un error es reintentable."""
    if isinstance(exception, httpx.TimeoutException):
        return True
    if isinstance(exception, httpx.ConnectError):
        return True
    if isinstance(exception, httpx.RemoteProtocolError):
        return True
    return False

async def retry_with_backoff(coro_func, *args, max_attempts=None, min_wait=None, max_wait=None, **kwargs):
    """
    Ejecuta una coroutine con retry y exponential backoff.
    
    Args:
        coro_func: Función async a ejecutar
        *args: Argumentos para la función
        max_attempts: Número máximo de intentos (default: RETRY_MAX_ATTEMPTS)
        min_wait: Espera mínima en segundos (default: RETRY_MIN_WAIT)
        max_wait: Espera máxima en segundos (default: RETRY_MAX_WAIT)
        **kwargs: Keyword arguments para la función
    """
    max_attempts = max_attempts or RETRY_MAX_ATTEMPTS
    min_wait = min_wait or RETRY_MIN_WAIT
    max_wait = max_wait or RETRY_MAX_WAIT
    
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if attempt == max_attempts:
                log.error("retry_exhausted", attempt=attempt, error=str(e))
                raise
            
            if not is_retryable_error(e):
                log.error("retry_non_retryable_error", attempt=attempt, error=str(e))
                raise
            
            wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
            log.debug("retry_attempt", attempt=attempt, wait_seconds=wait_time)
            
            await asyncio.sleep(wait_time)
    
    raise last_exception

async def replicar_archivo_al_api(
    api_url: str,
    file_path: str,
    IdPublicidadRemoto: int = None,
    titulo: str = None,
    tipo: str = None,
    prioridad: int = 0,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    activo: bool = True,
    timeout: int = 30,
    dispositivo_ids: list = None,
) -> dict:
    """
    Envía un archivo y metadatos al endpoint de replicación del backend-api.
    Retorna la respuesta del API como dict.
    Si dispositivo_ids está presente, solo replica a esos dispositivos.
    """
    if not os.path.isfile(file_path):
        log.error("file_not_found", file_path=file_path)
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    with open(file_path, "rb") as file_handle:
        data = {
            "IdPublicidadRemoto": IdPublicidadRemoto,
            "titulo": titulo,
            "tipo": tipo,
            "prioridad": prioridad,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "duracion_seg": duracion_seg,
            "activo": activo,
        }
        if dispositivo_ids:
            data["dispositivo_ids"] = ",".join(str(d) for d in dispositivo_ids)
        data = {k: v for k, v in data.items() if v is not None}

        upload_url = api_url.rstrip('/') + '/replicar-archivo' if not api_url.rstrip('/').endswith('/replicar-archivo') else api_url
        log.debug("replicating_file", api_url=api_url, banner_id=IdPublicidadRemoto)
        try:
            files = {
                "file": (os.path.basename(file_path), file_handle, "application/octet-stream")
            }
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(upload_url, files=files, data=data)
            log.debug("replication_response", api_url=api_url, status_code=response.status_code)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.error("replication_error", api_url=api_url, error=str(e))
            raise

async def replicar_archivos_batch_al_api(api_url: str, file_paths: list, banners: list, timeout: int = 30) -> list:
    """
    Replica múltiples archivos y metadatos al backend-api.
    Retorna una lista de resultados por archivo.
    """
    resultados = []
    for idx, file_path in enumerate(file_paths):
        banner = banners[idx]
        try:
            resp = await replicar_archivo_al_api(
                api_url=api_url,
                file_path=file_path,
                IdPublicidadRemoto=banner.IdPublicidad,
                titulo=banner.Titulo,
                tipo=banner.Tipo,
                prioridad=banner.Prioridad,
                fecha_inicio=banner.FechaInicio.isoformat() if banner.FechaInicio else None,
                fecha_fin=banner.FechaFin.isoformat() if banner.FechaFin else None,
                duracion_seg=banner.DuracionSeg,
                activo=banner.Activo,
                timeout=timeout
            )
            resultados.append({"filename": file_path, "success": True, "response": resp})
        except Exception as e:
            resultados.append({"filename": file_path, "success": False, "error": str(e)})
    return resultados

async def Borrado_api(api_url: str, id_remoto: int, timeout: int = 30) -> dict:
    """
    Envía una petición DELETE al backend-api para eliminar un banner remoto por IdPublicidadRemoto.
    Retorna la respuesta del API como dict.
    """
    url = f"{api_url.rstrip('/')}/banners/remoto/{id_remoto}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.delete(url)
    try:
        return response.json()
    except Exception:
        return {"success": False, "message": f"Respuesta inválida del API: {response.text}"}


async def actualizar_estado_api(api_url: str, id_remoto: int, activo: bool, timeout: int = 15) -> dict:
    """
    Actualiza Activo/Inactivo en backend-api usando IdPublicidadRemoto.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.patch(
                f"{api_url}/banners/remoto/{id_remoto}/estado",
                json={"activo": activo},
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


async def actualizar_metadata_api(
    api_url: str,
    id_remoto: int,
    activo: bool | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    timeout: int = 15,
) -> dict:
    """
    Actualiza metadatos (activo/fecha_inicio/fecha_fin) en backend-api por IdPublicidadRemoto.
    """
    payload: dict = {}
    if activo is not None:
        payload["activo"] = activo
    payload["fecha_inicio"] = fecha_inicio
    payload["fecha_fin"] = fecha_fin

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.patch(
                f"{api_url.rstrip('/')}/banners/remoto/{id_remoto}",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_api_urls() -> list:
    """
    Obtiene la lista de URLs de APIs de replicación desde variables de entorno.
    Soporta BACKEND_API_URLS (comma-separated) o BACKEND_API_URL (single, backwards compatible).
    """
    urls_env = os.getenv("BACKEND_API_URLS", "")
    if urls_env:
        return [u.strip() for u in urls_env.split(",") if u.strip()]
    
    legacy_url = os.getenv("BACKEND_API_URL", "")
    if legacy_url:
        return [legacy_url.strip()]
    
    return []


async def replicar_archivo_a_todas_las_apis(
    file_path: str,
    IdPublicidadRemoto: int = None,
    titulo: str = None,
    tipo: str = None,
    prioridad: int = 0,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    activo: bool = True,
    timeout: int = 30,
    dispositivo_ids: list = None
) -> list:
    """
    Replica un archivo a todas las APIs de replicación configuradas.
    Retorna una lista de resultados por cada API.
    Si dispositivo_ids está presente (no None), lo envía al backend-api.
    """
    api_urls = get_api_urls()
    resultados = []
    for api_url in api_urls:
        try:
            resp = await replicar_archivo_al_api(
                api_url=api_url,
                file_path=file_path,
                IdPublicidadRemoto=IdPublicidadRemoto,
                titulo=titulo,
                tipo=tipo,
                prioridad=prioridad,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                duracion_seg=duracion_seg,
                activo=activo,
                timeout=timeout,
                dispositivo_ids=dispositivo_ids
            )
            resultados.append({"api_url": api_url, "success": True, "response": resp})
        except Exception as e:
            resultados.append({"api_url": api_url, "success": False, "error": str(e)})
    return resultados


async def replicar_archivos_batch_a_todas_las_apis(file_paths: list, banners: list, timeout: int = 30) -> list:
    """
    Replica múltiples archivos a todas las APIs de replicación configuradas.
    Retorna una lista de resultados por cada archivo y cada API.
    """
    api_urls = get_api_urls()
    resultados = []
    for api_url in api_urls:
        try:
            batch_results = await replicar_archivos_batch_al_api(
                api_url=api_url,
                file_paths=file_paths,
                banners=banners,
                timeout=timeout
            )
            resultados.append({"api_url": api_url, "success": True, "results": batch_results})
        except Exception as e:
            resultados.append({"api_url": api_url, "success": False, "error": str(e)})
    return resultados


async def Borrado_a_todas_las_apis(id_remoto: int, timeout: int = 30) -> list:
    """
    Envía petición de borrado a todas las APIs de replicación configuradas.
    """
    api_urls = get_api_urls()
    resultados = []
    for api_url in api_urls:
        try:
            resp = await Borrado_api(api_url, id_remoto, timeout)
            resultados.append({"api_url": api_url, "success": True, "response": resp})
        except Exception as e:
            resultados.append({"api_url": api_url, "success": False, "error": str(e)})
    return resultados


async def actualizar_estado_a_todas_las_apis(id_remoto: int, activo: bool, timeout: int = 15) -> list:
    """
    Actualiza el estado activo/inactivo en todas las APIs de replicación.
    """
    api_urls = get_api_urls()
    resultados = []
    for api_url in api_urls:
        try:
            resp = await actualizar_estado_api(api_url, id_remoto, activo, timeout)
            resultados.append({"api_url": api_url, "success": True, "response": resp})
        except Exception as e:
            resultados.append({"api_url": api_url, "success": False, "error": str(e)})
    return resultados


async def actualizar_metadata_a_todas_las_apis(
    id_remoto: int,
    activo: bool | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    timeout: int = 15,
) -> list:
    """
    Actualiza metadatos en todas las APIs de replicación configuradas.
    """
    api_urls = get_api_urls()
    resultados = []
    for api_url in api_urls:
        try:
            resp = await actualizar_metadata_api(
                api_url, id_remoto, activo, fecha_inicio, fecha_fin, timeout
            )
            resultados.append({"api_url": api_url, "success": True, "response": resp})
        except Exception as e:
            resultados.append({"api_url": api_url, "success": False, "error": str(e)})
    return resultados


async def replicar_archivo_a_api_especifica(
    api_url: str,
    file_path: str,
    IdPublicidadRemoto: int = None,
    titulo: str = None,
    tipo: str = None,
    prioridad: int = 0,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    activo: bool = True,
    timeout: int = 30
) -> dict:
    """
    Replica un archivo a una API específica.
    Retorna la respuesta del API como dict.
    """
    return await replicar_archivo_al_api(
        api_url=api_url,
        file_path=file_path,
        IdPublicidadRemoto=IdPublicidadRemoto,
        titulo=titulo,
        tipo=tipo,
        prioridad=prioridad,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        duracion_seg=duracion_seg,
        activo=activo,
        timeout=timeout
    )


async def actualizar_banner_en_api(
    api_url: str,
    banner_id: int,
    titulo: str = None,
    tipo: str = None,
    activo: bool = None,
    prioridad: int = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    dispositivo_ids: list = None,
    timeout: int = 30
) -> dict:
    """
    Actualiza un banner existente en una API específica.
    """
    data = {}
    if titulo is not None:
        data["titulo"] = titulo
    if tipo is not None:
        data["tipo"] = tipo
    if activo is not None:
        data["activo"] = activo
    if prioridad is not None:
        data["prioridad"] = prioridad
    if fecha_inicio is not None:
        data["fecha_inicio"] = fecha_inicio
    if fecha_fin is not None:
        data["fecha_fin"] = fecha_fin
    if duracion_seg is not None:
        data["duracion_seg"] = duracion_seg
    # Siempre enviar dispositivo_ids (None o [] se convierte a "" para limpiar en backend-api)
    # Si es None o vacío, enviar "" para que el backend-api limpie el campo
    if dispositivo_ids is not None:
        data["dispositivo_ids"] = ",".join(str(d) for d in dispositivo_ids) if dispositivo_ids else ""
    else:
        data["dispositivo_ids"] = ""
    
    if not data:
        return {"success": True, "message": "No hay datos para actualizar"}
    
    update_url = api_url.rstrip('/') + f'/banners/{banner_id}'
    log.debug("updating_banner", banner_id=banner_id, api_url=api_url)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.put(update_url, data=data)
            log.debug("update_response", banner_id=banner_id, status_code=response.status_code)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        log.error("update_error", banner_id=banner_id, error=str(e))
        raise


async def actualizar_banner_en_todas_las_apis(
    banner_id: int,
    titulo: str = None,
    tipo: str = None,
    activo: bool = None,
    prioridad: int = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    dispositivo_ids: list = None,
    timeout: int = 30
) -> list:
    """
    Actualiza un banner existente en todas las APIs de replicación.
    """
    api_urls = get_api_urls()
    resultados = []
    for api_url in api_urls:
        try:
            resp = await actualizar_banner_en_api(
                api_url=api_url,
                banner_id=banner_id,
                titulo=titulo,
                tipo=tipo,
                activo=activo,
                prioridad=prioridad,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                duracion_seg=duracion_seg,
                dispositivo_ids=dispositivo_ids,
                timeout=timeout
            )
            resultados.append({"api_url": api_url, "success": True, "response": resp})
        except Exception as e:
            resultados.append({"api_url": api_url, "success": False, "error": str(e)})
    return resultados


async def replicar_a_servidores(
    file_path: str,
    servidores: list,
    IdPublicidadRemoto: int = None,
    titulo: str = None,
    tipo: str = None,
    prioridad: int = 0,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    activo: bool = True,
    timeout: int = 30,
    dispositivo_ids: list = None,
) -> list:
    """
    Replica un archivo a los servidores seleccionados (PARALELO).
    Cada servidor debe tener 'ip' o 'api_url'.
    Si dispositivo_ids está presente, filtra por esos dispositivos.
    """
    async def _replicar_a_un_servidor(servidor: dict) -> dict:
        api_url = servidor.get("api_url")
        if not api_url:
            ip = servidor.get("ip")
            if ip:
                api_url = f"http://{ip}:8000"
        
        if not api_url:
            return {
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": None,
                "success": False,
                "error": "No se encontró URL del backend-api"
            }
        
        try:
            resp = await replicar_archivo_al_api(
                api_url=api_url,
                file_path=file_path,
                IdPublicidadRemoto=IdPublicidadRemoto,
                titulo=titulo,
                tipo=tipo,
                prioridad=prioridad,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                duracion_seg=duracion_seg,
                activo=activo,
                timeout=timeout,
                dispositivo_ids=dispositivo_ids,
            )
            return {
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": api_url,
                "success": True,
                "response": resp
            }
        except Exception as e:
            return {
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": api_url,
                "success": False,
                "error": str(e)
            }
    
    if not servidores:
        return []
    
    results = await asyncio.gather(
        *[_replicar_a_un_servidor(srv) for srv in servidores],
        return_exceptions=False
    )
    
    return list(results)


async def sync_a_servidor(
    servidor_ip: str,
    dispositivo_ids: list = None,
    publicidad_ids: list = None,
    timeout: int = 120
) -> dict:
    """
    Envía comando de sincronización a un servidor específico.
    """
    api_url = f"http://{servidor_ip}:8000/api/fuerza-sync"
    payload = {}
    if dispositivo_ids:
        payload["dispositivo_ids"] = dispositivo_ids
    if publicidad_ids:
        payload["publicidad_ids"] = publicidad_ids
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(api_url, json=payload)
            response.raise_for_status()
            return {"success": True, "response": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def actualizar_banner_en_asignaciones(
    banner_id: int,
    servidores: list,
    titulo: str = None,
    tipo: str = None,
    activo: bool = None,
    prioridad: int = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    dispositivo_ids: list = None,
    timeout: int = 30
) -> list:
    """
    Actualiza un banner existente SOLO en los servidores que tienen asignaciones.
    
    Args:
        banner_id: ID del banner a actualizar
        servidores: Lista de dicts con 'id', 'nombre', 'api_url' o 'ip' de servidores objetivo
        dispositivo_ids: Lista de dispositivo_ids a asignar (None = todos, [] = ninguno)
        (otros parámetros son metadatos del banner)
    
    Returns:
        Lista de resultados por servidor
    """
    resultados = []
    
    for servidor in servidores:
        api_url = servidor.get("api_url")
        if not api_url:
            ip = servidor.get("ip")
            if ip:
                api_url = f"http://{ip}:8000"
        
        if not api_url:
            resultados.append({
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": None,
                "success": False,
                "error": "No se encontró URL del backend-api"
            })
            continue
        
        data = {}
        if titulo is not None:
            data["titulo"] = titulo
        if tipo is not None:
            data["tipo"] = tipo
        if activo is not None:
            data["activo"] = activo
        if prioridad is not None:
            data["prioridad"] = prioridad
        if fecha_inicio is not None:
            data["fecha_inicio"] = fecha_inicio
        if fecha_fin is not None:
            data["fecha_fin"] = fecha_fin
        if duracion_seg is not None:
            data["duracion_seg"] = duracion_seg
        
        # Enviar dispositivo_ids:
        # - Si es None: asignar a todos (limpiar filtro)
        # - Si es lista con elementos: asignar a esos dispositivos
        # - Si es lista vacía: limpiar asignaciones (ningún dispositivo)
        if dispositivo_ids is not None:
            data["dispositivo_ids"] = ",".join(str(d) for d in dispositivo_ids) if dispositivo_ids else ""
        else:
            data["dispositivo_ids"] = ""
        
        if not data:
            resultados.append({
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": api_url,
                "success": True,
                "message": "No hay datos para actualizar"
            })
            continue
        
        update_url = api_url.rstrip('/') + f'/banners/{banner_id}'
        log.info("updating_banner_assignment", banner_id=banner_id, api_url=api_url, servidor_nombre=servidor.get("nombre"), data=data)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.put(update_url, data=data)
                log.info("update_assignment_response", banner_id=banner_id, api_url=api_url, servidor_nombre=servidor.get("nombre"), status_code=response.status_code)
                response.raise_for_status()
                resultados.append({
                    "servidor_id": servidor.get("id"),
                    "servidor_nombre": servidor.get("nombre"),
                    "api_url": api_url,
                    "success": True,
                    "response": response.json()
                })
        except Exception as e:
            log.error("update_assignment_error", banner_id=banner_id, api_url=api_url, servidor_nombre=servidor.get("nombre"), error=str(e))
            resultados.append({
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": api_url,
                "success": False,
                "error": str(e)
            })
    
    return resultados


async def verificar_banner_existe_en_api(api_url: str, banner_id: int, timeout: int = 15) -> dict:
    """
    Verifica si un banner existe en un backend-api específico.
    Usa PUT porque es idempotente y retorna 404 si no existe.
    Returns: {"exists": True/False, "status_code": int}
    """
    check_url = f"{api_url.rstrip('/')}/banners/{banner_id}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.put(check_url, data={"titulo": "__check_exists__"})
            return {"exists": response.status_code == 200, "status_code": response.status_code}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"exists": False, "status_code": 404}
        return {"exists": False, "status_code": e.response.status_code, "error": str(e)}
    except Exception as e:
        return {"exists": False, "status_code": 0, "error": str(e)}


async def verificar_banner_en_servidores(
    banner_id: int,
    servidores: list,
    timeout: int = 15
) -> dict:
    """
    Verifica si un banner existe en todos los servidores objetivo (PARALELO).
    Retorna un reporte completo con:
    - servidores_con_banner: lista de servidores que tienen el banner
    - servidores_sin_banner: lista de servidores que NO tienen el banner
    - total: total de servidores verificados
    - exito: True si todos tienen el banner
    """
    log.debug("verification_start", banner_id=banner_id, total_servidores=len(servidores))
    
    async def _verificar_un_servidor(servidor: dict) -> dict:
        api_url = servidor.get("api_url")
        if not api_url:
            ip = servidor.get("ip")
            if ip:
                api_url = f"http://{ip}:8000"
        
        if not api_url:
            return {
                "servidor": servidor,
                "exists": False,
                "error": "No se encontró URL del backend-api"
            }
        
        try:
            result = await verificar_banner_existe_en_api(api_url, banner_id, timeout)
            return {
                "servidor": servidor,
                "exists": result.get("exists", False),
                "status_code": result.get("status_code"),
                "api_url": api_url
            }
        except Exception as e:
            return {
                "servidor": servidor,
                "exists": False,
                "error": str(e),
                "api_url": api_url
            }
    
    if not servidores:
        return {
            "banner_id": banner_id,
            "servidores_con_banner": [],
            "servidores_sin_banner": [],
            "errores": [],
            "total": 0,
            "total_con_banner": 0,
            "total_sin_banner": 0,
            "total_errores": 0,
            "exito": True
        }
    
    results = await asyncio.gather(
        *[_verificar_un_servidor(srv) for srv in servidores],
        return_exceptions=False
    )
    
    servidores_con_banner = []
    servidores_sin_banner = []
    errores = []
    
    for result in results:
        servidor = result.get("servidor")
        servidor_info = {
            "servidor_id": servidor.get("id"),
            "servidor_nombre": servidor.get("nombre"),
            "api_url": result.get("api_url"),
            "status_code": result.get("status_code")
        }
        
        if "error" in result:
            errores.append({
                "servidor": servidor,
                "error": result["error"]
            })
            log.warning("verification_server_error",
                      banner_id=banner_id,
                      servidor=servidor.get("nombre"))
        elif result.get("exists"):
            servidores_con_banner.append(servidor_info)
            log.debug("verification_server_has_banner", banner_id=banner_id, servidor=servidor.get("nombre"))
        else:
            servidores_sin_banner.append(servidor_info)
            log.warning("verification_server_missing_banner", banner_id=banner_id, servidor=servidor.get("nombre"))
    
    resultado = {
        "banner_id": banner_id,
        "servidores_con_banner": servidores_con_banner,
        "servidores_sin_banner": servidores_sin_banner,
        "errores": errores,
        "total": len(servidores),
        "total_con_banner": len(servidores_con_banner),
        "total_sin_banner": len(servidores_sin_banner),
        "total_errores": len(errores),
        "exito": len(servidores_sin_banner) == 0 and len(errores) == 0
    }
    
    log.info("verification_complete", banner_id=banner_id, exito=resultado["exito"], 
             total=resultado["total"], sin_banner=resultado["total_sin_banner"])
    
    return resultado


async def obtener_servidores_sin_banner(
    banner_id: int,
    servidores: list,
    timeout: int = 15
) -> list:
    """
    Obtiene la lista de servidores que NO tienen un banner específico (PARALELO).
    Returns: Lista de servidores que necesitan replicación.
    """
    async def _verificar_un_servidor(servidor: dict) -> dict:
        api_url = servidor.get("api_url")
        if not api_url:
            ip = servidor.get("ip")
            if ip:
                api_url = f"http://{ip}:8000"
        
        if not api_url:
            return {"servidor": servidor, "exists": None}
        
        result = await verificar_banner_existe_en_api(api_url, banner_id, timeout)
        return {"servidor": servidor, "exists": result.get("exists", False), "api_url": api_url}
    
    if not servidores:
        return []
    
    results = await asyncio.gather(
        *[_verificar_un_servidor(srv) for srv in servidores],
        return_exceptions=False
    )
    
    servidores_sin_banner = []
    for result in results:
        if result.get("exists") is None:
            continue
        if not result.get("exists"):
            log.debug("banner_not_found", banner_id=banner_id, servidor=result.get("servidor", {}).get("nombre"))
            servidores_sin_banner.append(result["servidor"])
        else:
            log.debug("banner_exists", banner_id=banner_id, servidor=result.get("servidor", {}).get("nombre"))
    
    return servidores_sin_banner


async def replicar_banner_completo_a_servidores(
    banner_data: dict,
    servidores: list,
    timeout: int = 30
) -> list:
    """
    Replica un banner existente (archivo + metadatos) a servidores específicos (PARALELO).
    Útil para replicar a servidores que no tienen el banner.
    
    Args:
        banner_data: Dict con 'banner_id', 'file_path', 'titulo', 'tipo', 'activo', 
                     'prioridad', 'fecha_inicio', 'fecha_fin', 'duracion_seg', 'dispositivo_ids'
        servidores: Lista de servidores objetivo
    """
    async def _replicar_a_un_servidor(servidor: dict) -> dict:
        api_url = servidor.get("api_url")
        if not api_url:
            ip = servidor.get("ip")
            if ip:
                api_url = f"http://{ip}:8000"
        
        if not api_url:
            return {
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": None,
                "success": False,
                "error": "No se encontró URL del backend-api"
            }
        
        file_path = banner_data.get("file_path")
        if not file_path or not os.path.isfile(file_path):
            return {
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": api_url,
                "success": False,
                "error": f"Archivo no encontrado: {file_path}"
            }
        
        try:
            with open(file_path, "rb") as file_handle:
                data = {
                    "IdPublicidadRemoto": banner_data.get("banner_id"),
                    "titulo": banner_data.get("titulo"),
                    "tipo": banner_data.get("tipo"),
                    "prioridad": banner_data.get("prioridad", 0),
                    "activo": banner_data.get("activo", True),
                    "fecha_inicio": banner_data.get("fecha_inicio"),
                    "fecha_fin": banner_data.get("fecha_fin"),
                    "duracion_seg": banner_data.get("duracion_seg"),
                }
                disp_ids = banner_data.get("dispositivo_ids")
                if disp_ids is not None:
                    data["dispositivo_ids"] = ",".join(str(d) for d in disp_ids) if disp_ids else ""
                
                files = {
                    "file": (os.path.basename(file_path), file_handle, "application/octet-stream")
                }
                
                log.debug("replicating_full_banner", banner_id=banner_data.get('banner_id'), servidor=servidor.get("nombre"))
                
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{api_url.rstrip('/')}/replicar-archivo",
                        files=files,
                        data=data
                    )
                    log.debug("replication_full_response", banner_id=banner_data.get('banner_id'), status_code=response.status_code)
                    response.raise_for_status()
                    
                    return {
                        "servidor_id": servidor.get("id"),
                        "servidor_nombre": servidor.get("nombre"),
                        "api_url": api_url,
                        "success": True,
                        "response": response.json()
                    }
        except Exception as e:
            log.error("replication_full_error", banner_id=banner_data.get('banner_id'), servidor=servidor.get("nombre"), error=str(e))
            return {
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": api_url,
                "success": False,
                "error": str(e)
            }
    
    if not servidores:
        return []
    
    results = await asyncio.gather(
        *[_replicar_a_un_servidor(srv) for srv in servidores],
        return_exceptions=False
    )
    
    return list(results)


async def replicar_banner_completo_a_servidores_con_verificacion(
    banner_data: dict,
    servidores: list,
    timeout: int = 30,
    verificar: bool = True
) -> dict:
    """
    Replica un banner existente (archivo + metadatos) a servidores específicos CON verificación post-replicación.
    
    Args:
        banner_data: Dict con 'banner_id', 'file_path', 'titulo', 'tipo', 'activo', 
                     'prioridad', 'fecha_inicio', 'fecha_fin', 'duracion_seg', 'dispositivo_ids'
        servidores: Lista de servidores objetivo
        verificar: Si True, realiza verificación post-replicación (default: True)
    
    Returns:
        Dict con:
        - replicacion_resultados: resultados de la replicación
        - verificacion_resultado: resultado de la verificación (si verificar=True)
        - exito: True si la replicación fue exitosa Y la verificación confirmó
    """
    banner_id = banner_data.get("banner_id")
    log.debug("replication_with_verification_start", banner_id=banner_id, servidores=len(servidores))
    
    replicacion_resultados = await replicar_banner_completo_a_servidores(
        banner_data=banner_data,
        servidores=servidores,
        timeout=timeout
    )
    
    resultado = {
        "banner_id": banner_id,
        "replicacion_resultados": replicacion_resultados,
        "verificacion_resultado": None,
        "exito": False
    }
    
    exitosos = [r for r in replicacion_resultados if r.get("success")]
    fallidos = [r for r in replicacion_resultados if not r.get("success")]
    
    log.info("replication_complete", banner_id=banner_id, exitosos=len(exitosos), fallidos=len(fallidos))
    
    if verificar and exitosos:
        servidores_exitosos = [s for s in servidores if any(
            r.get("servidor_id") == s.get("id") and r.get("success") 
            for r in exitosos
        )]
        
        verificacion = await verificar_banner_en_servidores(
            banner_id=banner_id,
            servidores=servidores_exitosos,
            timeout=timeout
        )
        
        resultado["verificacion_resultado"] = verificacion
        
        resultado["exito"] = (
            len(fallidos) == 0 and
            verificacion.get("exito", False)
        )
    else:
        resultado["exito"] = len(fallidos) == 0
    
    return resultado


async def _http_post_internal(url: str, files: dict = None, data: dict = None, timeout: int = 30) -> httpx.Response:
    """Helper interno para POST HTTP sin retry."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        if files:
            return await client.post(url, files=files, data=data)
        return await client.post(url, json=data)


async def _http_put_internal(url: str, data: dict = None, timeout: int = 30) -> httpx.Response:
    """Helper interno para PUT HTTP sin retry."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.put(url, data=data)


async def _http_post_with_retry(url: str, files: dict = None, data: dict = None, timeout: int = 30) -> httpx.Response:
    """
    Realiza un POST HTTP con retry automático.
    """
    return await retry_with_backoff(
        _http_post_internal,
        url, files, data, timeout
    )


async def _http_put_with_retry(url: str, data: dict = None, timeout: int = 30) -> httpx.Response:
    """
    Realiza un PUT HTTP con retry automático.
    """
    return await retry_with_backoff(
        _http_put_internal,
        url, data, timeout
    )


async def replicar_archivo_al_api_con_retry(
    api_url: str,
    file_path: str,
    IdPublicidadRemoto: int = None,
    titulo: str = None,
    tipo: str = None,
    prioridad: int = 0,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    activo: bool = True,
    timeout: int = 30,
    dispositivo_ids: list = None,
) -> dict:
    """
    Envía un archivo y metadatos al endpoint de replicación del backend-api CON RETRY.
    Retorna la respuesta del API como dict.
    """
    if not os.path.isfile(file_path):
        log.error("file_not_found", file_path=file_path)
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    with open(file_path, "rb") as file_handle:
        data = {
            "IdPublicidadRemoto": IdPublicidadRemoto,
            "titulo": titulo,
            "tipo": tipo,
            "prioridad": prioridad,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "duracion_seg": duracion_seg,
            "activo": activo,
        }
        if dispositivo_ids:
            data["dispositivo_ids"] = ",".join(str(d) for d in dispositivo_ids)
        data = {k: v for k, v in data.items() if v is not None}

        upload_url = api_url.rstrip('/') + '/replicar-archivo' if not api_url.rstrip('/').endswith('/replicar-archivo') else api_url
        log.info("replicating_file_with_retry", api_url=api_url, banner_id=IdPublicidadRemoto)
        
        try:
            files = {
                "file": (os.path.basename(file_path), file_handle, "application/octet-stream")
            }
            response = await _http_post_with_retry(upload_url, files=files, data=data, timeout=timeout)
            log.info("replication_response", api_url=api_url, status_code=response.status_code)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.error("replication_error", api_url=api_url, error=str(e))
            raise


async def actualizar_banner_en_api_con_retry(
    api_url: str,
    banner_id: int,
    titulo: str = None,
    tipo: str = None,
    activo: bool = None,
    prioridad: int = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    dispositivo_ids: list = None,
    timeout: int = 30
) -> dict:
    """
    Actualiza un banner existente en una API específica CON RETRY.
    """
    data = {}
    if titulo is not None:
        data["titulo"] = titulo
    if tipo is not None:
        data["tipo"] = tipo
    if activo is not None:
        data["activo"] = activo
    if prioridad is not None:
        data["prioridad"] = prioridad
    if fecha_inicio is not None:
        data["fecha_inicio"] = fecha_inicio
    if fecha_fin is not None:
        data["fecha_fin"] = fecha_fin
    if duracion_seg is not None:
        data["duracion_seg"] = duracion_seg
    if dispositivo_ids is not None:
        data["dispositivo_ids"] = ",".join(str(d) for d in dispositivo_ids) if dispositivo_ids else ""
    else:
        data["dispositivo_ids"] = ""
    
    if not data:
        return {"success": True, "message": "No hay datos para actualizar"}
    
    update_url = api_url.rstrip('/') + f'/banners/{banner_id}'
    log.info("updating_banner_with_retry", banner_id=banner_id, api_url=api_url)
    
    try:
        response = await _http_put_with_retry(update_url, data=data, timeout=timeout)
        log.info("update_response", banner_id=banner_id, api_url=api_url, status_code=response.status_code)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.error("update_error", banner_id=banner_id, api_url=api_url, error=str(e))
        raise


async def _verificar_banner_check_internal(api_url: str, banner_id: int, timeout: int) -> httpx.Response:
    """Helper interno para verificación de banner sin retry."""
    check_url = f"{api_url.rstrip('/')}/banners/{banner_id}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.put(check_url, data={"titulo": "__check_exists__"})


async def verificar_banner_existe_en_api_con_retry(api_url: str, banner_id: int, timeout: int = 15) -> dict:
    """
    Verifica si un banner existe en un backend-api específico CON RETRY.
    """
    try:
        response = await retry_with_backoff(
            _verificar_banner_check_internal,
            api_url, banner_id, timeout
        )
        return {"exists": response.status_code == 200, "status_code": response.status_code}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"exists": False, "status_code": 404}
        return {"exists": False, "status_code": e.response.status_code, "error": str(e)}
    except Exception as e:
        return {"exists": False, "status_code": 0, "error": str(e)}