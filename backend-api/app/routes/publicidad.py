from fastapi import UploadFile, File, Form, APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db_publicidad
import shutil
from datetime import datetime
import os
from typing import List
from ..schemas import PublicidadResponse
from ..models.publicidad import Publicidad

router = APIRouter()

@router.get("/banners", response_model=List[PublicidadResponse])
async def listar_banners(db: AsyncSession = Depends(get_db_publicidad)):
    result = await db.execute(
        select(Publicidad).order_by(Publicidad.prioridad, Publicidad.id)
    )
    banners = result.scalars().all()
    return [PublicidadResponse.model_validate(banner.__dict__) for banner in banners]

@router.post("/replicar-archivo")
async def replicar_archivo(
    file: UploadFile = File(...),
    IdPublicidadRemoto: int = Form(None),
    titulo: str = Form(None),
    tipo: str = Form(None),
    prioridad: int = Form(0),
    fecha_inicio: str = Form(None),
    fecha_fin: str = Form(None),
    duracion_seg: int = Form(None),
    db: AsyncSession = Depends(get_db_publicidad)
):
    """
    Recibe un archivo (imagen/video) y metadatos para replicación desde el dashboard.
    Guarda el archivo en static/banners y registra en la base de datos.
    """
    banners_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners"))
    os.makedirs(banners_dir, exist_ok=True)
    ext = file.filename.lower().split('.')[-1]
    allowed_images = ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
    allowed_videos = ["mp4", "webm", "mkv", "avi", "mov"]
    if ext in allowed_images:
        tipo_archivo = "image"
    elif ext in allowed_videos:
        tipo_archivo = "video"
    else:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: .{ext}")

    filename = file.filename
    file_location = os.path.join(banners_dir, filename)
    if os.path.exists(file_location):
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        file_location = os.path.join(banners_dir, filename)
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

    url = f"/static/banners/{filename}"
    try:
        from ..models.publicidad import Publicidad
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio) if fecha_inicio else None
        fecha_fin_dt = datetime.fromisoformat(fecha_fin) if fecha_fin else None
        nuevo_banner = Publicidad(
            titulo=titulo,
            tipo=tipo or tipo_archivo,
            url=url,
            activo=True,
            prioridad=prioridad,
            fecha_inicio=fecha_inicio_dt,
            fecha_fin=fecha_fin_dt,
            duracion_seg=duracion_seg,
            IdPublicidadRemoto=IdPublicidadRemoto
        )
        db.add(nuevo_banner)
        await db.commit()
        await db.refresh(nuevo_banner)
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Error al guardar metadatos: {str(e)}")

    return {
        "success": True,
        "message": "Archivo replicado y registrado correctamente.",
        "url": url,
        "id": nuevo_banner.id
    }

@router.delete("/banners/{banner_id}")
async def eliminar_banner(banner_id: int, db: AsyncSession = Depends(get_db_publicidad)):
    from ..models.publicidad import Publicidad
    result = await db.execute(select(Publicidad).where(Publicidad.id == banner_id))
    banner = result.scalars().first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner no encontrado")
    # Eliminar archivo físico si existe
    if banner.url:
        # url es tipo /static/banners/filename.ext
        file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", banner.url.lstrip("/")))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    await db.delete(banner)
    await db.commit()
    return {"success": True, "message": "Banner eliminado correctamente."}