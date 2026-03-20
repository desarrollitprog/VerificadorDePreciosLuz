import httpx
import os

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
        print(f"[DEBUG] Archivo no encontrado: {file_path}")
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
        print(f"[DEBUG] Replicando archivo al backend-api: {upload_url}")
        print(f"[DEBUG] Datos enviados: {data}")
        try:
            files = {
                "file": (os.path.basename(file_path), file_handle, "application/octet-stream")
            }
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(upload_url, files=files, data=data)
            print(f"[DEBUG] Código de respuesta: {response.status_code}")
            print(f"[DEBUG] Respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[ERROR] Error al replicar archivo: {str(e)}")
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
    timeout: int = 30
) -> list:
    """
    Replica un archivo a todas las APIs de replicación configuradas.
    Retorna una lista de resultados por cada API.
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
                timeout=timeout
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
    Replica un archivo a los servidores seleccionados.
    Cada servidor debe tener 'ip' o 'api_url'.
    Si dispositivo_ids está presente, filtra por esos dispositivos.
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
                "api_url": api_url,
                "success": False,
                "error": "No se encontró URL del backend-api"
            })
            continue
        
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
            resultados.append({
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": api_url,
                "success": True,
                "response": resp
            })
        except Exception as e:
            resultados.append({
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": api_url,
                "success": False,
                "error": str(e)
            })
    return resultados


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