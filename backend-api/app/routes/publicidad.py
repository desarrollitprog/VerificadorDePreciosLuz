from fastapi import UploadFile, File, Form, APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from ..database import get_db_publicidad
import shutil
from datetime import datetime
import os
from typing import List, Optional
from pydantic import BaseModel
from ..schemas import PublicidadResponse
from ..models.publicidad import Publicidad

router = APIRouter()


class EstadoRemotoBody(BaseModel):
    activo: bool


class BannerRemotoUpdateBody(BaseModel):
    activo: Optional[bool] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None


class PublicidadDispositivoBody(BaseModel):
    dispositivo_ids: List[str] = []


@router.get("/banners", response_model=List[PublicidadResponse])
async def listar_banners(
    device_ids: str = Query(None, description="Lista de device_ids separados por coma"),
    db: AsyncSession = Depends(get_db_publicidad)
):
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), datetime.min.time())
    
    query = select(Publicidad).where(
        Publicidad.activo == True,
        or_(Publicidad.fecha_inicio.is_(None), Publicidad.fecha_inicio <= now),
        or_(
            Publicidad.fecha_fin.is_(None),
            and_(
                func.date(Publicidad.fecha_fin) >= today_start,
                func.date(Publicidad.fecha_fin) >= now.date(),
            ),
        ),
    ).order_by(Publicidad.prioridad, Publicidad.id)
    
    result = await db.execute(query)
    banners = result.scalars().all()
    
    if device_ids:
        device_id_list = [d.strip() for d in device_ids.split(",") if d.strip()]
        filtered_banners = []
        for banner in banners:
            banner_device_ids = getattr(banner, 'device_ids', None)
            if banner_device_ids:
                banner_ids_set = set(banner_device_ids.split(","))
                if any(d in banner_ids_set for d in device_id_list):
                    filtered_banners.append(banner)
            else:
                filtered_banners.append(banner)
        banners = filtered_banners
    
    return [PublicidadResponse.model_validate(banner.__dict__) for banner in banners]

@router.post("/replicar-archivo")
async def replicar_archivo(
    file: UploadFile = File(...),
    IdPublicidadRemoto: int = Form(None),
    titulo: str = Form(None),
    tipo: str = Form(None),
    activo: bool = Form(True),
    prioridad: int = Form(0),
    fecha_inicio: str = Form(None),
    fecha_fin: str = Form(None),
    duracion_seg: int = Form(None),
    dispositivo_ids: str = Form(None),
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

    max_size = 20 * 1024 * 1024  # 20 MB
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > max_size:
        raise HTTPException(status_code=400, detail="El archivo excede el tamaño máximo permitido (20 MB).")

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
            activo=activo,
            prioridad=prioridad,
            fecha_inicio=fecha_inicio_dt,
            fecha_fin=fecha_fin_dt,
            duracion_seg=duracion_seg,
            device_ids=dispositivo_ids,
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

@router.post("/replicar-archivos")
async def replicar_archivos_batch(
    files: List[UploadFile] = File(...),
    Titulos: List[str] = Form(...),
    Activos: List[bool] = Form(...),
    Prioridades: List[int] = Form(...),
    FechasInicio: List[str] = Form(...),
    FechasFin: List[str] = Form(...),
    DuracionesSeg: List[int] = Form(...),
    IdsPublicidadRemoto: List[int] = Form(...),
    db: AsyncSession = Depends(get_db_publicidad)
):
    banners_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners"))
    os.makedirs(banners_dir, exist_ok=True)
    resultados = []
    for idx, file in enumerate(files):
        ext = file.filename.lower().split('.')[-1]
        allowed_images = ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
        allowed_videos = ["mp4", "webm", "mkv", "avi", "mov"]
        if ext in allowed_images:
            tipo_archivo = "image"
        elif ext in allowed_videos:
            tipo_archivo = "video"
        else:
            resultados.append({"filename": file.filename, "success": False, "error": f"Tipo de archivo no permitido: .{ext}"})
            continue
        max_size = 20 * 1024 * 1024
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > max_size:
            resultados.append({"filename": file.filename, "success": False, "error": "El archivo excede el tamaño máximo permitido (20 MB)."})
            continue
        filename = file.filename
        file_location = os.path.join(banners_dir, filename)
        if os.path.exists(file_location):
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_location = os.path.join(banners_dir, filename)
        try:
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            resultados.append({"filename": file.filename, "success": False, "error": f"Error al guardar archivo: {str(e)}"})
            continue
        url = f"/static/banners/{filename}"
        try:
            fecha_inicio_dt = datetime.fromisoformat(FechasInicio[idx]) if FechasInicio[idx] else None
            fecha_fin_dt = datetime.fromisoformat(FechasFin[idx]) if FechasFin[idx] else None
            nuevo_banner = Publicidad(
                titulo=Titulos[idx],
                tipo=tipo_archivo,
                url=url,
                activo=Activos[idx],
                prioridad=Prioridades[idx],
                fecha_inicio=fecha_inicio_dt,
                fecha_fin=fecha_fin_dt,
                duracion_seg=DuracionesSeg[idx],
                IdPublicidadRemoto=IdsPublicidadRemoto[idx]
            )
            db.add(nuevo_banner)
            await db.commit()
            await db.refresh(nuevo_banner)
            resultados.append({
                "filename": filename,
                "success": True,
                "url": url,
                "id": nuevo_banner.id,
                "IdPublicidadRemoto": nuevo_banner.IdPublicidadRemoto
            })
        except Exception as e:
            if os.path.exists(file_location):
                os.remove(file_location)
            resultados.append({"filename": file.filename, "success": False, "error": f"Error al guardar metadatos: {str(e)}"})
            continue
    return {
        "resultados": resultados,
        "success": any(r["success"] for r in resultados),
        "message": f"Batch replicación finalizada. {sum(1 for r in resultados if r['success'])} archivos exitosos, {sum(1 for r in resultados if not r['success'])} errores."
    }

@router.delete("/banners/remoto/{id_remoto}")
async def eliminar_banner_remoto(id_remoto: int, db: AsyncSession = Depends(get_db_publicidad)):
    from ..models.publicidad import Publicidad
    result = await db.execute(select(Publicidad).where(Publicidad.IdPublicidadRemoto == id_remoto))
    banner = result.scalars().first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner no encontrado por IdPublicidadRemoto")
    # Eliminar archivo físico si existe
    if banner.url:
        file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", banner.url.lstrip("/")))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    await db.delete(banner)
    await db.commit()
    return {"success": True, "message": "Banner eliminado correctamente por IdPublicidadRemoto."}


@router.patch("/banners/remoto/{id_remoto}/estado")
async def actualizar_estado_remoto(
    id_remoto: int,
    body: EstadoRemotoBody,
    db: AsyncSession = Depends(get_db_publicidad),
):
    result = await db.execute(
        select(Publicidad).where(Publicidad.IdPublicidadRemoto == id_remoto)
    )
    banner = result.scalars().first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner no encontrado por IdPublicidadRemoto")

    banner.activo = body.activo
    await db.commit()
    await db.refresh(banner)

    return {
        "success": True,
        "message": "Estado remoto actualizado.",
        "id": banner.id,
        "IdPublicidadRemoto": banner.IdPublicidadRemoto,
        "activo": banner.activo,
    }


@router.patch("/banners/remoto/{id_remoto}")
async def actualizar_banner_remoto(
    id_remoto: int,
    body: BannerRemotoUpdateBody,
    db: AsyncSession = Depends(get_db_publicidad),
):
    result = await db.execute(
        select(Publicidad).where(Publicidad.IdPublicidadRemoto == id_remoto)
    )
    banner = result.scalars().first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner no encontrado por IdPublicidadRemoto")

    if body.fecha_inicio and body.fecha_fin and body.fecha_inicio > body.fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="Rango inválido: fecha_inicio no puede ser mayor que fecha_fin.",
        )

    if body.activo is not None:
        banner.activo = body.activo
    banner.fecha_inicio = body.fecha_inicio
    banner.fecha_fin = body.fecha_fin

    await db.commit()
    await db.refresh(banner)

    return {
        "success": True,
        "message": "Banner remoto actualizado.",
        "id": banner.id,
        "IdPublicidadRemoto": banner.IdPublicidadRemoto,
        "activo": banner.activo,
        "fecha_inicio": banner.fecha_inicio.isoformat() if banner.fecha_inicio else None,
        "fecha_fin": banner.fecha_fin.isoformat() if banner.fecha_fin else None,
    }