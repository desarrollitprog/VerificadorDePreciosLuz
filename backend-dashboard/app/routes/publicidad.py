import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Path
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models import Publicidad
from ..schemas import PublicidadResponse, PublicidadCreate
from ..database import get_db_usuarios
from ..dependencies import get_current_cliente
from ..services.notificacion_service import registrar_accion
from ..services.replicacion_service import replicar_archivo_a_todas_las_apis, replicar_archivos_batch_a_todas_las_apis, Borrado_a_todas_las_apis, actualizar_estado_a_todas_las_apis, actualizar_metadata_a_todas_las_apis


router = APIRouter()


def _format_size_human(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    return f"{value:.1f} {units[unit_index]}"


def _resolve_banner_size(url: str | None) -> tuple[int, str]:
    if not url:
        return 0, "0 B"
    file_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", url.lstrip("/"))
    )
    if not os.path.isfile(file_path):
        return 0, "0 B"
    size_bytes = os.path.getsize(file_path)
    return size_bytes, _format_size_human(size_bytes)


class EstadoBannerBody(BaseModel):
    activo: bool


class BannerMetadataBody(BaseModel):
    activo: Optional[bool] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None


@router.get("/banners")
async def listar_banners(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    try:
        result = await db.execute(select(Publicidad).order_by(Publicidad.Prioridad, Publicidad.IdPublicidad))
        banners = result.scalars().all()
        banners_payload = []
        for banner in banners:
            size_bytes, size_human = _resolve_banner_size(banner.Url)
            banners_payload.append(
                {
                    "IdPublicidad": banner.IdPublicidad,
                    "Titulo": banner.Titulo,
                    "Tipo": banner.Tipo,
                    "Url": banner.Url,
                    "Activo": banner.Activo,
                    "Prioridad": banner.Prioridad,
                    "FechaInicio": banner.FechaInicio.isoformat() if banner.FechaInicio else None,
                    "FechaFin": banner.FechaFin.isoformat() if banner.FechaFin else None,
                    "DuracionSeg": banner.DuracionSeg,
                    "UpdatedAt": banner.UpdatedAt.isoformat() if banner.UpdatedAt else None,
                    "size_bytes": size_bytes,
                    "size_human": size_human,
                }
            )
        return {
            "success": True,
            "message": "Banners obtenidos correctamente.",
            "banners": banners_payload,
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
    Activo: bool = Form(True),
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
        max_size = 20 * 1024 * 1024  # 20 MB
    elif ext in allowed_videos:
        Tipo = "video"
        max_size = 20 * 1024 * 1024  # 20 MB
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
        if FechaInicio_dt and FechaFin_dt and FechaInicio_dt > FechaFin_dt:
            raise HTTPException(status_code=400, detail="Rango inválido: FechaInicio no puede ser mayor que FechaFin.")
        nuevo_banner = Publicidad(
            Titulo=Titulo,
            Tipo=Tipo,
            Url=url,
            Activo=Activo,
            Prioridad=Prioridad,
            FechaInicio=FechaInicio_dt,
            FechaFin=FechaFin_dt,
            DuracionSeg=DuracionSeg
        )
        db.add(nuevo_banner)
        await db.commit()
        await db.refresh(nuevo_banner)
        print(f"Se ha guardado correctamente en la base de datos: Id={nuevo_banner.IdPublicidad}, Titulo={nuevo_banner.Titulo}, Url={nuevo_banner.Url}")
    except HTTPException:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise
    except Exception as e:
        # Si falla la BD, elimina el archivo subido
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Error al guardar metadatos en la base de datos: {str(e)}")

    # Replicar archivo al backend-api y guardar el ID remoto
    id_remoto = None
    try:
        print(f"Replicando archivo al backend-api: {file_location}")
        replicacion_resultados = await replicar_archivo_a_todas_las_apis(
            file_path=file_location,
            IdPublicidadRemoto=nuevo_banner.IdPublicidad,
            titulo=Titulo,
            tipo=Tipo,
            prioridad=Prioridad,
            fecha_inicio=FechaInicio,
            fecha_fin=FechaFin,
            duracion_seg=DuracionSeg,
            activo=Activo,
        )
        print(f"Replicación al backend-api finalizada: {replicacion_resultados}")
        for res in replicacion_resultados:
            if res.get("success") and res.get("response", {}).get("id"):
                id_remoto = res["response"]["id"]
                break
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
            remote_id = banner.IdPublicidad
            replicacion_resultados = await Borrado_a_todas_las_apis(remote_id)
            for res in replicacion_resultados:
                if not res.get("success", False):
                    raise Exception(f"No se pudo borrar remotamente en {res['api_url']}: {res.get('error', 'Sin mensaje')}")
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

# Endpoint batch para subir múltiples archivos y metadatos
@router.post("/banners/upload-batch")
async def upload_banners_batch(
    files: List[UploadFile] = File(...),
    Titulos: List[str] = Form(...),
    Activos: List[bool] = Form(...),
    Prioridades: List[int] = Form(...),
    FechasInicio: List[str] = Form(...),
    FechasFin: List[str] = Form(...),
    DuracionesSeg: List[int] = Form(...),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    banners_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners"))
    os.makedirs(banners_dir, exist_ok=True)
    resultados = []
    archivos_guardados = []
    metadatos_guardados = []
    errores = []
    for idx, file in enumerate(files):
        ext = file.filename.lower().split('.')[-1]
        allowed_images = ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
        allowed_videos = ["mp4", "webm", "mkv", "avi", "mov"]
        if ext in allowed_images:
            Tipo = "image"
            max_size = 20 * 1024 * 1024
        elif ext in allowed_videos:
            Tipo = "video"
            max_size = 20 * 1024 * 1024
        else:
            errores.append({"filename": file.filename, "error": f"Tipo de archivo no permitido: .{ext}"})
            continue
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > max_size:
            errores.append({"filename": file.filename, "error": f"El archivo excede el tamaño máximo permitido ({max_size // (1024*1024)} MB)."})
            continue
        filename = file.filename
        file_location = os.path.join(banners_dir, filename)
        if os.path.exists(file_location):
            unique_suffix = uuid.uuid4().hex[:8]
            filename = f"{os.path.splitext(file.filename)[0]}_{unique_suffix}.{ext}"
            file_location = os.path.join(banners_dir, filename)
        try:
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            url = f"/static/banners/{filename}"
            FechaInicio_dt = datetime.fromisoformat(FechasInicio[idx]) if FechasInicio[idx] else None
            FechaFin_dt = datetime.fromisoformat(FechasFin[idx]) if FechasFin[idx] else None
            if FechaInicio_dt and FechaFin_dt and FechaInicio_dt > FechaFin_dt:
                raise Exception("Rango inválido: FechaInicio no puede ser mayor que FechaFin.")
            nuevo_banner = Publicidad(
                Titulo=Titulos[idx],
                Tipo=Tipo,
                Url=url,
                Activo=Activos[idx],
                Prioridad=Prioridades[idx],
                FechaInicio=FechaInicio_dt,
                FechaFin=FechaFin_dt,
                DuracionSeg=DuracionesSeg[idx]
            )
            db.add(nuevo_banner)
            await db.commit()
            await db.refresh(nuevo_banner)
            archivos_guardados.append(file_location)
            metadatos_guardados.append(nuevo_banner)
            resultados.append({
                "filename": filename,
                "success": True,
            })
        except Exception as e:
            errores.append({"filename": file.filename, "error": str(e)})
            continue
    # Replicación batch a todas las APIs
    replicacion_resultados = []
    try:
        if archivos_guardados:
            replicacion_resultados = await replicar_archivos_batch_a_todas_las_apis(
                file_paths=archivos_guardados,
                banners=metadatos_guardados
            )
    except Exception as e:
        errores.append({"error": f"Error en replicación batch: {str(e)}"})
    user_id = current_user.get("user_id")
    if user_id is not None:
        await registrar_accion(
            db,
            user_id,
            "SUBIDA_MULTIMEDIA_BATCH",
            f"Archivos subidos: {[r['filename'] for r in resultados]}"
        )
    return JSONResponse(content={
        "resultados": resultados,
        "errores": errores,
        "success": len(resultados) > 0,
        "message": f"Batch upload finalizado. {len(resultados)} archivos exitosos, {len(errores)} errores."
    })
  
@router.patch("/banners/{id}/estado")
async def cambiar_estado_banner(
    id: int = Path(..., description="ID del banner"),
    body: EstadoBannerBody = ...,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    banner = await db.get(Publicidad, id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner no encontrado.")

    estado_anterior = bool(banner.Activo)
    banner.Activo = body.activo
    await db.commit()
    await db.refresh(banner)

    # Replica estado al backend-api (si falla, revierte para evitar desalineación)
    try:
        replicacion_resultados = await actualizar_estado_a_todas_las_apis(
            id_remoto=banner.IdPublicidad,
            activo=body.activo,
        )
        for res in replicacion_resultados:
            if not res.get("success", False):
                raise Exception(f"Error en {res['api_url']}: {res.get('error', 'Sin detalle')}")
    except Exception as e:
        banner.Activo = estado_anterior
        await db.commit()
        raise HTTPException(status_code=502, detail=f"No se pudo actualizar estado remoto: {str(e)}")

    user_id = current_user.get("user_id") if current_user else None
    if user_id is not None:
        await registrar_accion(
            db,
            user_id,
            "CAMBIO_ESTADO_MULTIMEDIA",
            f"Banner IdPublicidad={banner.IdPublicidad} -> {'ACTIVO' if banner.Activo else 'INACTIVO'}",
        )

    return {
        "success": True,
        "message": "Estado actualizado correctamente.",
        "banner": {
            "IdPublicidad": banner.IdPublicidad,
            "Activo": banner.Activo,
        },
    }


@router.patch("/banners/{id}")
async def actualizar_banner_metadata(
    id: int = Path(..., description="ID del banner"),
    body: BannerMetadataBody = ...,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Actualiza Activo, FechaInicio y FechaFin.
    Validación: si ambas fechas existen, FechaInicio <= FechaFin.
    Replica al backend-api por IdPublicidadRemoto.
    """
    banner = await db.get(Publicidad, id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner no encontrado.")

    fecha_inicio = body.fecha_inicio
    fecha_fin = body.fecha_fin

    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="Rango inválido: FechaInicio no puede ser mayor que FechaFin.",
        )

    prev_activo = banner.Activo
    prev_inicio = banner.FechaInicio
    prev_fin = banner.FechaFin

    if body.activo is not None:
        banner.Activo = body.activo
    banner.FechaInicio = fecha_inicio
    banner.FechaFin = fecha_fin

    await db.commit()
    await db.refresh(banner)

    try:
        replicacion_resultados = await actualizar_metadata_a_todas_las_apis(
            id_remoto=banner.IdPublicidad,
            activo=banner.Activo,
            fecha_inicio=banner.FechaInicio.isoformat() if banner.FechaInicio else None,
            fecha_fin=banner.FechaFin.isoformat() if banner.FechaFin else None,
        )
        for res in replicacion_resultados:
            if not res.get("success", False):
                raise Exception(f"Error en {res['api_url']}: {res.get('error', 'Sin detalle')}")
    except Exception as e:
        banner.Activo = prev_activo
        banner.FechaInicio = prev_inicio
        banner.FechaFin = prev_fin
        await db.commit()
        raise HTTPException(status_code=502, detail=f"No se pudo actualizar remotamente: {str(e)}")

    user_id = current_user.get("user_id") if current_user else None
    if user_id is not None:
        await registrar_accion(
            db,
            user_id,
            "EDICION_VIGENCIA_MULTIMEDIA",
            f"Banner IdPublicidad={banner.IdPublicidad}, Activo={banner.Activo}, "
            f"FechaInicio={banner.FechaInicio}, FechaFin={banner.FechaFin}",
        )

    return {
        "success": True,
        "message": "Banner actualizado correctamente.",
        "banner": {
            "IdPublicidad": banner.IdPublicidad,
            "Activo": banner.Activo,
            "FechaInicio": banner.FechaInicio.isoformat() if banner.FechaInicio else None,
            "FechaFin": banner.FechaFin.isoformat() if banner.FechaFin else None,
        },
    }


