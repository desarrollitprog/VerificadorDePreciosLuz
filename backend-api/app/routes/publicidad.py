from fastapi import UploadFile, File, Form, APIRouter, HTTPException, status, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, cast, Date
from ..database import get_db_publicidad
import shutil
from datetime import datetime, timezone, timedelta
import os
from typing import List, Optional
from pydantic import BaseModel
from ..schemas import PublicidadResponse
from ..models.publicidad import Publicidad

router = APIRouter()


def get_venezuela_now():
    return datetime.now(timezone(timedelta(hours=-4)))


def get_venezuela_now_naive():
    return datetime.now(timezone(timedelta(hours=-4))).replace(tzinfo=None)


async def _notify_banner_iniciado_inmediato(banner: Publicidad, device_ids: str | None):
    """Notifica inmediatamente a los dispositivos cuando un banner ya debe iniciarse."""
    from ..main import tablet_ws_manager
    
    target_device_ids = None
    if device_ids:
        target_device_ids = [d.strip() for d in device_ids.split(",") if d.strip()]
    
    banner_info = {
        "command": "BANNER_INICIADO",
        "banner_id": banner.id,
        "titulo": banner.titulo,
        "url": banner.url,
        "tipo": banner.tipo,
        "fecha_inicio": banner.fecha_inicio.isoformat() if banner.fecha_inicio else None,
        "fecha_fin": banner.fecha_fin.isoformat() if banner.fecha_fin else None,
    }
    
    if target_device_ids:
        for device_id in target_device_ids:
            await tablet_ws_manager.send_to_device(device_id, banner_info)
    else:
        await tablet_ws_manager.broadcast(banner_info)


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
    device_id: str = Query(None, description="Un solo device_id del dispositivo"),
    device_ids: str = Query(None, description="Lista de device_ids separados por coma (deprecated, usar device_id)"),
    db: AsyncSession = Depends(get_db_publicidad)
):
    now = get_venezuela_now_naive()
    today_start = datetime.combine(now.date(), datetime.min.time())
    
    query = select(Publicidad).where(
        Publicidad.activo == True,
        or_(Publicidad.fecha_inicio.is_(None), Publicidad.fecha_inicio <= now),
        or_(
            Publicidad.fecha_fin.is_(None),
            and_(
                cast(Publicidad.fecha_fin, Date) >= today_start.date(),
                cast(Publicidad.fecha_fin, Date) >= now.date(),
            ),
        ),
    ).order_by(Publicidad.prioridad, Publicidad.id)
    
    result = await db.execute(query)
    banners = result.scalars().all()
    
    # Usar device_id si se proporciona, sino usar device_ids (para compatibilidad)
    target_device_ids = device_id if device_id else device_ids
    
    if target_device_ids:
        device_id_list = [d.strip() for d in target_device_ids.split(",") if d.strip()]
        filtered_banners = []
        for banner in banners:
            banner_device_ids = getattr(banner, 'device_ids', None)
            # Si el banner NO tiene device_ids asignados, es para TODOS los dispositivos
            if not banner_device_ids:
                filtered_banners.append(banner)
            else:
                # Si tiene device_ids, verificar si el dispositivo está en la lista
                banner_ids_set = set(banner_device_ids.split(","))
                if any(d in banner_ids_set for d in device_id_list):
                    filtered_banners.append(banner)
        banners = filtered_banners
    
    # Convertir banners a response incluyendo fecha_inicio_ms y fecha_fin_ms
    response_list = []
    for banner in banners:
        banner_dict = banner.__dict__.copy()
        # Calcular fecha_inicio_ms si existe fecha_inicio
        if banner.fecha_inicio:
            banner_dict['fecha_inicio_ms'] = int(banner.fecha_inicio.timestamp() * 1000)
        else:
            banner_dict['fecha_inicio_ms'] = None
        # Calcular fecha_fin_ms si existe fecha_fin
        if banner.fecha_fin:
            banner_dict['fecha_fin_ms'] = int(banner.fecha_fin.timestamp() * 1000)
        else:
            banner_dict['fecha_fin_ms'] = None
        response_list.append(PublicidadResponse.model_validate(banner_dict))
    return response_list


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

    max_size = 500 * 1024 * 1024  # 20 MB
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
        from sqlalchemy import select
        
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio) if fecha_inicio else None
        fecha_fin_dt = datetime.fromisoformat(fecha_fin) if fecha_fin else None
        tipo_final = tipo or tipo_archivo
        
        if IdPublicidadRemoto:
            check_stmt = select(Publicidad).where(Publicidad.IdPublicidadRemoto == IdPublicidadRemoto)
            check_result = await db.execute(check_stmt)
            existing_banner = check_result.scalars().first()
            if existing_banner:
                existing_banner.url = url
                existing_banner.titulo = titulo
                existing_banner.tipo = tipo_final
                existing_banner.activo = activo
                existing_banner.prioridad = prioridad
                existing_banner.fecha_inicio = fecha_inicio_dt
                existing_banner.fecha_fin = fecha_fin_dt
                existing_banner.device_ids = dispositivo_ids
                await db.commit()
                await db.refresh(existing_banner)
                return {
                    "success": True,
                    "message": "Banner actualizado correctamente",
                    "id": existing_banner.id,
                    "url": existing_banner.url
                }
        
        nuevo_banner = Publicidad(
            titulo=titulo,
            tipo=tipo_final,
            url=url,
            activo=activo,
            prioridad=prioridad,
            fecha_inicio=fecha_inicio_dt,
            fecha_fin=fecha_fin_dt,
            device_ids=dispositivo_ids,
            IdPublicidadRemoto=IdPublicidadRemoto
        )
        db.add(nuevo_banner)
        await db.commit()
        await db.refresh(nuevo_banner)
        
        # Notificar inmediatamente si fecha_inicio ya pasó o está muy cerca
        if fecha_inicio_dt and activo:
            now = get_venezuela_now_naive()
            # Notificar si fecha_inicio <= now (ya pasó)
            if fecha_inicio_dt <= now:
                await _notify_banner_iniciado_inmediato(nuevo_banner, dispositivo_ids)
                print(f"[DEBUG] Notificación inmediata enviada para banner ID={nuevo_banner.id}")
            else:
                # Programar notificación exacta para la hora de inicio
                import asyncio
                from ..main import schedule_banner_notification
                asyncio.create_task(
                    schedule_banner_notification(
                        banner_id=nuevo_banner.id,
                        device_ids=dispositivo_ids,
                        titulo=nuevo_banner.titulo,
                        url=nuevo_banner.url,
                        tipo=nuevo_banner.tipo,
                        fecha_inicio=fecha_inicio_dt,
                        fecha_fin=fecha_fin_dt,
                    )
                )
                print(f"[DEBUG] Tarea programada para banner ID={nuevo_banner.id} a las {fecha_inicio_dt}")
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


@router.put("/banners/{banner_id}")
async def actualizar_banner(
    banner_id: int = Path(..., description="ID del banner a actualizar (puede ser ID local o IdPublicidadRemoto)"),
    titulo: str = Form(None),
    tipo: str = Form(None),
    activo: bool = Form(None),
    prioridad: int = Form(None),
    fecha_inicio: str = Form(None),
    fecha_fin: str = Form(None),
    dispositivo_ids: str = Form(None),
    db: AsyncSession = Depends(get_db_publicidad)
):
    """
    Actualiza un banner existente (metadatos y device_ids).
    Si no encuentra por ID directo, busca por IdPublicidadRemoto.
    """
    from ..models.publicidad import Publicidad
    import logging
    logger = logging.getLogger("publicidad")
    
    # Primero buscar por ID directo
    logger.info(f"[PUT banners] Buscando por ID directo: {banner_id}")
    banner = await db.get(Publicidad, banner_id)
    
    # Si no encuentra, buscar por IdPublicidadRemoto (ID del dashboard)
    if not banner:
        logger.info(f"[PUT banners] No encontrado por ID {banner_id}, buscando por IdPublicidadRemoto: {banner_id}")
        stmt = select(Publicidad).where(Publicidad.IdPublicidadRemoto == banner_id)
        result = await db.execute(stmt)
        banner = result.scalars().first()
    
    if not banner:
        logger.info(f"[PUT banners] Banner NO encontrado en DB, retornando 404")
        raise HTTPException(status_code=404, detail=f"Banner no encontrado (ID: {banner_id})")
    
    logger.info(f"[PUT banners] Banner encontrado, ID local: {banner.id}, IdRemoto: {banner.IdPublicidadRemoto}")
    
    try:
        # Actualizar campos si se proporcionan
        if titulo is not None:
            banner.titulo = titulo
        if tipo is not None:
            banner.tipo = tipo
        if activo is not None:
            banner.activo = activo
        if prioridad is not None:
            banner.prioridad = prioridad
        
        if fecha_inicio:
            banner.fecha_inicio = datetime.fromisoformat(fecha_inicio)
        if fecha_fin:
            banner.fecha_fin = datetime.fromisoformat(fecha_fin)
        
        # Manejar dispositivo_ids:
        # - Si dispositivo_ids tiene valor: asignar a esos dispositivos
        # - Si dispositivo_ids es None o "": asignar a todos
        if dispositivo_ids is not None and dispositivo_ids.strip() != "":
            banner.device_ids = dispositivo_ids.strip()
        else:
            banner.device_ids = None
        
        await db.commit()
        await db.refresh(banner)
        
        # Notificar a los dispositivos si el banner está activo y tiene fecha de inicio pasada
        if banner.activo and banner.fecha_inicio:
            now = get_venezuela_now_naive()
            if banner.fecha_inicio <= now:
                await _notify_banner_iniciado_inmediato(banner, banner.device_ids)
        
        return {
            "success": True,
            "message": "Banner actualizado correctamente",
            "banner": {
                "id": banner.id,
                "titulo": banner.titulo,
                "device_ids": banner.device_ids,
                "activo": banner.activo
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar banner: {str(e)}")


@router.get("/banners/{banner_id}/exists")
async def verificar_banner_existe(
    banner_id: int = Path(..., description="ID del banner a verificar (puede ser ID local o IdPublicidadRemoto)"),
    db: AsyncSession = Depends(get_db_publicidad)
):
    """
    Verifica si un banner existe en la base de datos.
    Retorna True si existe, False si no.
    Busca primero por ID directo, luego por IdPublicidadRemoto.
    """
    from ..models.publicidad import Publicidad
    import logging
    logger = logging.getLogger("publicidad")
    
    logger.info(f"[EXISTS] Buscando por ID directo: {banner_id}")
    banner = await db.get(Publicidad, banner_id)
    
    if not banner:
        logger.info(f"[EXISTS] No encontrado por ID {banner_id}, buscando por IdPublicidadRemoto: {banner_id}")
        stmt = select(Publicidad).where(Publicidad.IdPublicidadRemoto == banner_id)
        result = await db.execute(stmt)
        banner = result.scalars().first()
    
    if banner:
        logger.info(f"[EXISTS] Banner encontrado, ID local: {banner.id}, IdRemoto: {banner.IdPublicidadRemoto}")
    else:
        logger.info(f"[EXISTS] Banner NO encontrado")
    
    return {"exists": banner is not None, "banner_id": banner_id}


@router.post("/replicar-archivos")
async def replicar_archivos_batch(
    files: List[UploadFile] = File(...),
    Titulos: List[str] = Form(...),
    Activos: List[bool] = Form(...),
    Prioridades: List[int] = Form(...),
    FechasInicio: List[str] = Form(...),
    FechasFin: List[str] = Form(...),
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
    
    # Notificar inmediatamente si fecha_inicio ya pasó
    if body.fecha_inicio and banner.activo:
        now = get_venezuela_now_naive()
        if body.fecha_inicio <= now:
            await _notify_banner_iniciado_inmediato(banner, banner.device_ids)
            print(f"[DEBUG] Notificación inmediata enviada por actualización para banner ID={banner.id}")

    return {
        "success": True,
        "message": "Banner remoto actualizado.",
        "id": banner.id,
        "IdPublicidadRemoto": banner.IdPublicidadRemoto,
        "activo": banner.activo,
        "fecha_inicio": banner.fecha_inicio.isoformat() if banner.fecha_inicio else None,
        "fecha_fin": banner.fecha_fin.isoformat() if banner.fecha_fin else None,
    }
