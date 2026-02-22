import os
import shutil
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models import Publicidad
from ..schemas import PublicidadResponse, PublicidadCreate
from ..database import get_db_usuarios
from ..dependencies import get_current_cliente
from ..services.notificacion_service import registrar_accion
from ..services.replicacion_service import replicar_archivo_al_api, Borrado_api


router = APIRouter()


@router.get("/banners")
async def listar_banners(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    try:
        result = await db.execute(select(Publicidad).order_by(Publicidad.Prioridad, Publicidad.IdPublicidad))
        banners = result.scalars().all()
        return {
            "success": True,
            "message": "Banners obtenidos correctamente.",
            "banners": banners
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener banners: {str(e)}")

@router.post("/banners")
async def crear_banner(
    banner: PublicidadCreate,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    try:
        nuevo_banner = Publicidad(**banner.dict())
        db.add(nuevo_banner)
        await db.commit()
        await db.refresh(nuevo_banner)
        return {
            "success": True,
            "message": "Banner creado correctamente.",
            "banner": nuevo_banner
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear banner: {str(e)}")

@router.get("/banners/list")
def listar_archivos_banners(current_user: dict = Depends(get_current_cliente)):
    try:
        banners_dir = os.path.join("static", "banners")
        archivos = []
        if os.path.exists(banners_dir):
            archivos = [f for f in os.listdir(banners_dir) if os.path.isfile(os.path.join(banners_dir, f))]
        return {
            "success": True,
            "message": "Lista de archivos de banners obtenida correctamente.",
            "banners": archivos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar archivos: {str(e)}")

@router.post("/banners/upload")
async def upload_banner(
    file: UploadFile = File(...),
    Titulo: str = Form(None),
    Prioridad: int = Form(0),
    FechaInicio: str = Form(None),
    FechaFin: str = Form(None),
    DuracionSeg: int = Form(None),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
  
    # Calcula la ruta absoluta para static/banners, robusto ante cwd
    banners_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners"))
    os.makedirs(banners_dir, exist_ok=True)
    ext = file.filename.lower().split('.')[-1]
    allowed_images = ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
    allowed_videos = ["mp4", "webm", "mkv", "avi", "mov"]
    if ext in allowed_images:
        Tipo = "image"
        max_size = 10 * 1024 * 1024  # 10 MB
    elif ext in allowed_videos:
        Tipo = "video"
        max_size = 100 * 1024 * 1024  # 100 MB
    else:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: .{ext}")

    # Validar tamaño máximo
    file.file.seek(0, 2)  # Ir al final
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > max_size:
        raise HTTPException(status_code=400, detail=f"El archivo excede el tamaño máximo permitido ({max_size // (1024*1024)} MB).")

    # Evitar sobrescribir: renombrar si existe
    filename = file.filename
    file_location = os.path.join(banners_dir, filename)
    if os.path.exists(file_location):
        unique_suffix = uuid.uuid4().hex[:8]
        filename = f"{os.path.splitext(file.filename)[0]}_{unique_suffix}.{ext}"
        file_location = os.path.join(banners_dir, filename)

    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"Se ha guardado correctamente en la ruta: {file_location}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo: {str(e)}")

    # Guardar metadatos en la base de datos
    url = f"/static/banners/{filename}"
    try:
        FechaInicio_dt = datetime.fromisoformat(FechaInicio) if FechaInicio else None
        FechaFin_dt = datetime.fromisoformat(FechaFin) if FechaFin else None
        nuevo_banner = Publicidad(
            Titulo=Titulo,
            Tipo=Tipo,
            Url=url,
            Activo=True,
            Prioridad=Prioridad,
            FechaInicio=FechaInicio_dt,
            FechaFin=FechaFin_dt,
            DuracionSeg=DuracionSeg
        )
        db.add(nuevo_banner)
        await db.commit()
        await db.refresh(nuevo_banner)
        print(f"Se ha guardado correctamente en la base de datos: Id={nuevo_banner.IdPublicidad}, Titulo={nuevo_banner.Titulo}, Url={nuevo_banner.Url}")
    except Exception as e:
        # Si falla la BD, elimina el archivo subido
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Error al guardar metadatos en la base de datos: {str(e)}")

    # Replicar archivo al backend-api y guardar el ID remoto
    id_remoto = None
    try:
        api_url = os.getenv("BACKEND_API_URL", "http://192.168.1.109:8000/api")
        print(f"Replicando archivo al backend-api: {file_location} -> {api_url}")
        resp = replicar_archivo_al_api(
                api_url=api_url,
                file_path=file_location,
                IdPublicidadRemoto=nuevo_banner.IdPublicidad,
                titulo=Titulo,
                tipo=Tipo,
                prioridad=Prioridad,
                fecha_inicio=FechaInicio,
                fecha_fin=FechaFin,
                duracion_seg=DuracionSeg
            )
        print("Replicación al backend-api finalizada")
        id_remoto = resp.get("id") if resp else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al replicar archivo al backend-api: {str(e)}")

    user_id = current_user.get("user_id")
    if user_id is not None:
        await registrar_accion(
            db,
            user_id,
            "SUBIDA_MULTIMEDIA",
            f"Archivo subido: {filename}, IdPublicidad={nuevo_banner.IdPublicidad}",
        )

    return {
        "success": True,
        "message": "Archivo y metadatos guardados correctamente.",
        "filename": filename,
        "url": url,
        "tipo": Tipo,
        "banner": {
            "IdPublicidad": nuevo_banner.IdPublicidad,
            "Titulo": nuevo_banner.Titulo,
            "Prioridad": nuevo_banner.Prioridad,
            "FechaInicio": str(nuevo_banner.FechaInicio) if nuevo_banner.FechaInicio else None,
            "FechaFin": str(nuevo_banner.FechaFin) if nuevo_banner.FechaFin else None,
            "DuracionSeg": nuevo_banner.DuracionSeg
        }
    }
@router.delete("/banners/{id}")
async def eliminar_banner(
    id: int = Path(..., description="ID del banner a eliminar"),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    try:
        banner = await db.get(Publicidad, id)
        if not banner:
            raise HTTPException(status_code=404, detail="Banner no encontrado.")
        descripcion_audit = f"Banner eliminado: IdPublicidad={banner.IdPublicidad}, Titulo={banner.Titulo or ''}"
        # Eliminar archivo físico si existe
        if banner.Url:
            filename = os.path.basename(banner.Url)
            file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners", filename))
            if os.path.exists(file_path):
                os.remove(file_path)
        # Intentar borrar remotamente en backend-api usando el IdPublicidad como IdPublicidadRemoto
        try:
            api_url = os.getenv("BACKEND_API_URL", "http://192.168.1.109:8000/api")
            remote_id = banner.IdPublicidad
            remote_result = Borrado_api(api_url, remote_id)
            if not remote_result.get("success", False):
                raise Exception(f"No se pudo borrar remotamente: {remote_result.get('message', 'Sin mensaje')}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al borrar remotamente: {str(e)}")

        # Si el borrado remoto fue exitoso o no hay ID remoto, borrar localmente
        await db.delete(banner)
        await db.commit()
        user_id = current_user.get("user_id")
        if user_id is not None:
            await registrar_accion(db, user_id, "BORRADO_MULTIMEDIA", descripcion_audit)
        return {"success": True, "message": "Banner eliminado correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar banner: {str(e)}")


