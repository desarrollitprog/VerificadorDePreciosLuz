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
    timeout: int = 30
) -> dict:
    """
    Envía un archivo y metadatos al endpoint de replicación del backend-api.
    Retorna la respuesta del API como dict.
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