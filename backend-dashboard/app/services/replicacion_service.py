import requests
import os

def replicar_archivo_al_api(
    api_url: str,
    file_path: str,
    titulo: str = None,
    tipo: str = None,
    prioridad: int = 0,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    duracion_seg: int = None,
    timeout: int = 30
) -> dict:
    """
    Envía un archivo y metadatos al endpoint de replicación del backend-api.
    Retorna la respuesta del API como dict.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    files = {"file": open(file_path, "rb")}
    data = {
        "titulo": titulo,
        "tipo": tipo,
        "prioridad": prioridad,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "duracion_seg": duracion_seg
    }
    # Elimina campos None
    data = {k: v for k, v in data.items() if v is not None}

    # Concatenar endpoint de subida correcto
    upload_url = api_url.rstrip('/') + '/replicar-archivo' if not api_url.rstrip('/').endswith('/replicar-archivo') else api_url
    response = requests.post(
        upload_url,
        files=files,
        data=data,
        timeout=timeout
    )
    files["file"].close()
    response.raise_for_status()
    return response.json()

def Borrado_api(api_url: str, banner_id: int, timeout: int = 30) -> dict:
    """
    Envía una petición DELETE al backend-api para eliminar un banner remoto por ID.
    Retorna la respuesta del API como dict.
    """
    url = f"{api_url.rstrip('/')}/banners/{banner_id}"
    response = requests.delete(url, timeout=timeout)
    try:
        return response.json()
    except Exception:
        return {"success": False, "message": f"Respuesta inválida del API: {response.text}"}