import os
import shutil
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Path, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
import cv2
from ..models import Publicidad, PublicidadAsignacion, ServidorSecundario, Dispositivo
from ..schemas import PublicidadResponse, PublicidadCreate
from ..database import get_db_usuarios
from ..dependencies import get_current_cliente
from ..services.notificacion_service import registrar_accion
from ..services.replicacion_service import (
    replicar_archivo_a_todas_las_apis,
    replicar_archivos_batch_a_todas_las_apis,
    replicar_a_servidores,
    Borrado_a_todas_las_apis,
    actualizar_estado_a_todas_las_apis,
    actualizar_metadata_a_todas_las_apis,
    sync_a_servidor,
    actualizar_banner_en_todas_las_apis,
    actualizar_banner_en_asignaciones,
    obtener_servidores_sin_banner,
    replicar_banner_completo_a_servidores,
    replicar_banner_completo_a_servidores_con_verificacion,
    verificar_banner_en_servidores,
    procesar_cambio_asignacion
)
from app.utils.logger import StructuredLogger
from app.utils import sanitize_html, FileTypeValidator

router = APIRouter()
log = StructuredLogger("publicidad")


def get_venezuela_now():
    return datetime.now(timezone(timedelta(hours=-4))).replace(tzinfo=None)


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


def generar_thumbnail(video_path: str, output_dir: str) -> Optional[str]:
    """
    Genera un thumbnail (frame inicial) de un video usando OpenCV.
    Retorna la URL relativa del thumbnail o None si falla.
    """
    try:
        video = cv2.VideoCapture(video_path)
        if not video.isOpened():
            log.warning("thumbnail_generation_failed", reason="cannot_open_video", path=video_path)
            return None
        
        success, frame = video.read()
        video.release()
        
        if not success:
            log.warning("thumbnail_generation_failed", reason="cannot_read_frame", path=video_path)
            return None
        
        thumbnail_filename = f"thumb_{uuid.uuid4().hex[:8]}.jpg"
        thumbnail_path = os.path.join(output_dir, thumbnail_filename)
        
        success = cv2.imwrite(thumbnail_path, frame)
        if not success:
            log.warning("thumbnail_generation_failed", reason="cannot_write_thumbnail", path=video_path)
            return None
        
        thumbnail_url = f"/static/banners/{thumbnail_filename}"
        log.info("thumbnail_generated", video_path=video_path, thumbnail=thumbnail_url)
        return thumbnail_url
    
    except Exception as e:
        log.warning("thumbnail_generation_error", error=str(e), path=video_path)
        return None


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
    titulo: Optional[str] = None


class AsignacionCreate(BaseModel):
    servidor_id: int
    dispositivo_id: int


class BannerUploadBody(BaseModel):
    Titulo: Optional[str] = None
    Activo: bool = True
    Prioridad: int = 0
    FechaInicio: Optional[str] = None
    FechaFin: Optional[str] = None
    AsignacionTodos: bool = True
    Asignaciones: Optional[List[AsignacionCreate]] = None


@router.get("/banners")
async def listar_banners(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    incluir_todos: bool = False,
    limit: int = Query(50, ge=1, le=200, description="Número máximo de banners a retornar"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
):
    try:
        total_dispositivos_result = await db.execute(select(func.count(Dispositivo.id)))
        total_dispositivos = total_dispositivos_result.scalar() or 0
        
        count_query = select(func.count(Publicidad.IdPublicidad))
        if fecha_desde:
            try:
                desde_date = datetime.fromisoformat(fecha_desde.replace('Z', '+00:00'))
                count_query = count_query.where(Publicidad.FechaInicio >= desde_date)
            except ValueError:
                pass
        if fecha_hasta:
            try:
                hasta_date = datetime.fromisoformat(fecha_hasta.replace('Z', '+00:00'))
                count_query = count_query.where(Publicidad.FechaInicio <= hasta_date)
            except ValueError:
                pass
        
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar() or 0
        
        query = select(Publicidad).options(
            selectinload(Publicidad.asignaciones).selectinload(PublicidadAsignacion.servidor)
        )
        
        if fecha_desde:
            try:
                desde_date = datetime.fromisoformat(fecha_desde.replace('Z', '+00:00'))
                query = query.where(Publicidad.FechaInicio >= desde_date)
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                hasta_date = datetime.fromisoformat(fecha_hasta.replace('Z', '+00:00'))
                query = query.where(Publicidad.FechaInicio <= hasta_date)
            except ValueError:
                pass
        
        # Por defecto mostrar todos los banners (sin filtro de fecha inicio)
        # if not incluir_todos:
        #     query = query.where(Publicidad.FechaInicio.isnot(None))
        
        query = query.order_by(Publicidad.IdPublicidad.desc())
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        banners = result.scalars().all()
        
        all_dispositivo_ids = set()
        for banner in banners:
            if not banner.asignacion_todos:
                for asig in banner.asignaciones:
                    if asig.dispositivo_id:
                        all_dispositivo_ids.add(asig.dispositivo_id)
        
        dispositivos_mapa = {}
        if all_dispositivo_ids:
            stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko.in_(list(all_dispositivo_ids)))
            result_disp = await db.execute(stmt_disp)
            for disp in result_disp.scalars().all():
                dispositivos_mapa[disp.codigo_kiosko] = disp.nombre_amigable
        
        banners_payload = []
        
        for banner in banners:
            size_bytes, size_human = _resolve_banner_size(banner.Url)
            
            asignaciones = []
            if banner.asignacion_todos:
                dispositivos_count = total_dispositivos
            else:
                for asig in banner.asignaciones:
                    asignaciones.append({
                        "servidor_id": asig.servidor_id,
                        "servidor_nombre": asig.servidor.nombre if asig.servidor else None,
                        "dispositivo_id": asig.dispositivo_id,
                        "dispositivo_nombre": dispositivos_mapa.get(asig.dispositivo_id),
                        "dispositivo_codigo": asig.dispositivo_id,
                    })
                dispositivos_count = len(asignaciones)
            
            estado = "activo"
            if not banner.Activo:
                estado = "inactivo"
            # ETAPA 3: Fix estado "borrador" - solo mostrar si está inactivo Y no tiene asignaciones específicas
            # No marcar automáticamente como "borrador" por falta de asignaciones (esto ocurre por error en el flujo)
            # elif not banner.asignacion_todos and len(asignaciones) == 0:
            #     estado = "borrador"
            elif banner.FechaFin:
                now = get_venezuela_now()
                if banner.FechaFin < now:
                    estado = "vencido"
            
            banners_payload.append(
                {
                    "IdPublicidad": banner.IdPublicidad,
                    "Titulo": banner.Titulo,
                    "Tipo": banner.Tipo,
                    "Url": banner.Url,
                    "ThumbnailUrl": banner.ThumbnailUrl,
                    "Activo": banner.Activo,
                    "FechaInicio": banner.FechaInicio.isoformat() if banner.FechaInicio else None,
                    "FechaFin": banner.FechaFin.isoformat() if banner.FechaFin else None,
                    "UpdatedAt": banner.UpdatedAt.isoformat() if banner.UpdatedAt else None,
                    "size_bytes": size_bytes,
                    "size_human": size_human,
                    "asignacion_todos": banner.asignacion_todos,
                    "asignaciones": asignaciones,
                    "dispositivos_count": dispositivos_count,
                    "estado": estado,
                }
            )
        return {
            "success": True,
            "message": "Banners obtenidos correctamente.",
            "banners": banners_payload,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(banners_payload) < total_count,
            }
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
    AsignacionTodos: bool = Form(True),
    ServidorIds: str = Form(None),
    DispositivoIds: str = Form(None),
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
        
        is_valid, mime_type = FileTypeValidator.validate_file(file_location, allowed_images + allowed_videos)
        if not is_valid:
            os.remove(file_location)
            detail = f"Archivo no es una imagen o video válido. Tipo detectado: {mime_type}" if mime_type else "Archivo no es una imagen o video válido."
            raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo: {str(e)}")

    # Guardar metadatos en la base de datos
    url = f"/static/banners/{filename}"
    thumbnail_url = None
    
    # Generar thumbnail si es video
    if Tipo == "video":
        thumbnail_url = generar_thumbnail(file_location, banners_dir)
    
    try:
        FechaInicio_dt = datetime.fromisoformat(FechaInicio) if FechaInicio else None
        FechaFin_dt = datetime.fromisoformat(FechaFin) if FechaFin else None
        if FechaInicio_dt and FechaFin_dt and FechaInicio_dt > FechaFin_dt:
            raise HTTPException(status_code=400, detail="Rango inválido: FechaInicio no puede ser mayor que FechaFin.")
        
        titulo_sanitized = sanitize_html(Titulo)
        nuevo_banner = Publicidad(
            Titulo=titulo_sanitized,
            Tipo=Tipo,
            Url=url,
            ThumbnailUrl=thumbnail_url,
            Activo=Activo,
            Prioridad=Prioridad,
            FechaInicio=FechaInicio_dt,
            FechaFin=FechaFin_dt,
            asignacion_todos=AsignacionTodos
        )
        db.add(nuevo_banner)
        await db.commit()
        await db.refresh(nuevo_banner)
        log.info("banner_created", banner_id=nuevo_banner.IdPublicidad, titulo=nuevo_banner.Titulo)

        # Procesar servidores y dispositivos seleccionados
        import json
        selected_servidor_ids = []
        selected_dispositivo_ids = []
        
        if ServidorIds:
            try:
                selected_servidor_ids = json.loads(ServidorIds)
            except:
                selected_servidor_ids = []
        
        if DispositivoIds:
            try:
                selected_dispositivo_ids = json.loads(DispositivoIds)
            except:
                selected_dispositivo_ids = []

        # Guardar asignaciones en la tabla publicidad_asignacion
        guardar_asignaciones = (not AsignacionTodos and (selected_servidor_ids or selected_dispositivo_ids)) or (AsignacionTodos and selected_dispositivo_ids)
        if guardar_asignaciones:
            try:
                dispositivos_query = select(Dispositivo)
                if selected_servidor_ids:
                    dispositivos_query = dispositivos_query.where(Dispositivo.servidor_id.in_(selected_servidor_ids))
                if selected_dispositivo_ids:
                    dispositivos_query = dispositivos_query.where(Dispositivo.codigo_kiosko.in_(selected_dispositivo_ids))
                
                dispositivos_result = await db.execute(dispositivos_query)
                dispositivos = dispositivos_result.scalars().all()
                
                for disp in dispositivos:
                    asignacion = PublicidadAsignacion(
                        publicidad_id=nuevo_banner.IdPublicidad,
                        servidor_id=disp.servidor_id,
                        dispositivo_id=disp.codigo_kiosko
                    )
                    db.add(asignacion)
                
                await db.commit()
                log.info("asignaciones_guardadas", banner_id=nuevo_banner.IdPublicidad, cantidad=len(dispositivos))
            except Exception as e:
                log.error("error_asignaciones", banner_id=nuevo_banner.IdPublicidad, error=str(e))
                await db.rollback()
                raise
    except HTTPException:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise
    except Exception as e:
        # Si falla la BD, elimina el archivo subido
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Error al guardar metadatos en la base de datos: {str(e)}")

    # Replicar archivo al backend-api según asignaciones
    replicacion_resultados = []
    try:
        import json
        selected_servidor_ids = []
        selected_dispositivo_ids = []
        
        if ServidorIds:
            try:
                selected_servidor_ids = json.loads(ServidorIds)
            except:
                selected_servidor_ids = []
        
        if DispositivoIds:
            try:
                selected_dispositivo_ids = json.loads(DispositivoIds)
            except:
                selected_dispositivo_ids = []
        
        if AsignacionTodos and not selected_dispositivo_ids:
            log.info("upload_replicate_all", banner_id=nuevo_banner.IdPublicidad)
            replicacion_resultados = await replicar_archivo_a_todas_las_apis(
                file_path=file_location,
                IdPublicidadRemoto=nuevo_banner.IdPublicidad,
                titulo=Titulo,
                tipo=Tipo,
                prioridad=Prioridad,
                fecha_inicio=FechaInicio,
                fecha_fin=FechaFin,
                activo=Activo,
                dispositivo_ids=None,
            )
        elif selected_dispositivo_ids:
            log.info("upload_replicate_specific_devices", banner_id=nuevo_banner.IdPublicidad, dispositivo_ids=selected_dispositivo_ids)
            
            # Obtener servidores únicos de los dispositivos seleccionados
            disp_query = select(Dispositivo).where(Dispositivo.codigo_kiosko.in_(selected_dispositivo_ids))
            disp_result = await db.execute(disp_query)
            dispositivos_encontrados = disp_result.scalars().all()
            
            servidor_ids_unicos = list(set([d.servidor_id for d in dispositivos_encontrados]))
            
            if servidor_ids_unicos:
                srv_query = select(ServidorSecundario).where(ServidorSecundario.id.in_(servidor_ids_unicos))
                srv_result = await db.execute(srv_query)
                servidores = srv_result.scalars().all()
                servidores_data = [
                    {
                        "id": s.id,
                        "nombre": s.nombre,
                        "ip": s.ip,
                        "api_url": f"http://{s.ip}:8000"
                    }
                    for s in servidores
                ]
                log.info("upload_replicate_to_servers", banner_id=nuevo_banner.IdPublicidad, servidores=[s['nombre'] for s in servidores_data])
                replicacion_resultados = await replicar_a_servidores(
                    file_path=file_location,
                    servidores=servidores_data,
                    IdPublicidadRemoto=nuevo_banner.IdPublicidad,
                    titulo=Titulo,
                    tipo=Tipo,
                    prioridad=Prioridad,
                    fecha_inicio=FechaInicio,
                    fecha_fin=FechaFin,
                    activo=Activo,
                    dispositivo_ids=selected_dispositivo_ids,
                )
            else:
                log.warning("upload_no_servers_found", banner_id=nuevo_banner.IdPublicidad)
        elif selected_servidor_ids:
            log.info("upload_replicate_specific_servers", banner_id=nuevo_banner.IdPublicidad, servidor_ids=selected_servidor_ids)
            srv_query = select(ServidorSecundario).where(ServidorSecundario.id.in_(selected_servidor_ids))
            srv_result = await db.execute(srv_query)
            servidores = srv_result.scalars().all()
            servidores_data = [
                {
                    "id": s.id,
                    "nombre": s.nombre,
                    "ip": s.ip,
                    "api_url": f"http://{s.ip}:8000"
                }
                for s in servidores
            ]
            replicacion_resultados = await replicar_a_servidores(
                file_path=file_location,
                servidores=servidores_data,
                IdPublicidadRemoto=nuevo_banner.IdPublicidad,
                titulo=Titulo,
                tipo=Tipo,
                prioridad=Prioridad,
                fecha_inicio=FechaInicio,
                fecha_fin=FechaFin,
                activo=Activo,
                dispositivo_ids=None,  # Sin filtro = todos los dispositivos de esos servidores
            )
        else:
            log.warning("upload_no_replication", banner_id=nuevo_banner.IdPublicidad)
        log.info("upload_replication_complete", banner_id=nuevo_banner.IdPublicidad, resultados=replicacion_resultados)
    except Exception as e:
        log.error("upload_replication_error", banner_id=nuevo_banner.IdPublicidad if 'nuevo_banner' in dir() else None, error=str(e))

    user_id = current_user.get("user_id")
    if user_id is not None:
        # Obtener nombres de dispositivos y servidores
        dispositivos_info = ""
        if selected_dispositivo_ids:
            stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko.in_(selected_dispositivo_ids))
            result_disp = await db.execute(stmt_disp)
            dispositivos = result_disp.scalars().all()
            if dispositivos:
                nombres_disp = [f"'{d.nombre_amigable or d.codigo_kiosko}' ({d.codigo_kiosko})" for d in dispositivos]
                dispositivos_info = f" - Dispositivos: {', '.join(nombres_disp)}"
        
        servidores_info = ""
        if selected_servidor_ids:
            stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id.in_(selected_servidor_ids))
            result_srv = await db.execute(stmt_srv)
            servidores = result_srv.scalars().all()
            if servidores:
                nombres_srv = [f"'{s.nombre}' ({s.ip})" for s in servidores]
                servidores_info = f" - Servidores: {', '.join(nombres_srv)}"
        
        descripcion = f"Archivo '{filename}' (Id: {nuevo_banner.IdPublicidad}){dispositivos_info}{servidores_info}"
        
        # Usar el primer dispositivo/servidor para los campos de auditoría
        disp_id = selected_dispositivo_ids[0] if selected_dispositivo_ids else None
        srv_id = selected_servidor_ids[0] if selected_servidor_ids else None
        
        await registrar_accion(
            db,
            user_id,
            "SUBIDA_MULTIMEDIA",
            descripcion,
            dispositivo_id=disp_id,
            servidor_id=srv_id,
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
        
        # Obtener asignaciones para auditoría
        asignaciones_stmt = select(PublicidadAsignacion).where(PublicidadAsignacion.publicidad_id == id)
        result_asig = await db.execute(asignaciones_stmt)
        asignaciones = result_asig.scalars().all()
        
        dispositivo_ids = [a.dispositivo_id for a in asignaciones if a.dispositivo_id]
        servidor_ids = list(set([a.servidor_id for a in asignaciones if a.servidor_id]))
        
        disp_info = f", Dispositivos: {dispositivo_ids}" if dispositivo_ids else ""
        srv_info = f", Servidores: {servidor_ids}" if servidor_ids else ", Asignado a: todos"
        
        descripcion_audit = f"Banner eliminado: IdPublicidad={banner.IdPublicidad}, Titulo={banner.Titulo or ''}{disp_info}{srv_info}"
        # Eliminar archivo físico si existe
        if banner.Url:
            filename = os.path.basename(banner.Url)
            file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners", filename))
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Eliminar asignaciones primero
        try:
            from sqlalchemy import delete
            await db.execute(delete(PublicidadAsignacion).where(PublicidadAsignacion.publicidad_id == id))
            await db.commit()
        except Exception as e:
            log.error("error_eliminar_asignaciones", banner_id=id, error=str(e))
            await db.rollback()
        
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
            disp_id = dispositivo_ids[0] if dispositivo_ids else None
            srv_id = servidor_ids[0] if servidor_ids else None
            await registrar_accion(db, user_id, "BORRADO_MULTIMEDIA", descripcion_audit, dispositivo_id=disp_id, servidor_id=srv_id)
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
            
            is_valid, mime_type = FileTypeValidator.validate_file(file_location, allowed_images + allowed_videos)
            if not is_valid:
                os.remove(file_location)
                errores.append({"filename": file.filename, "error": f"Archivo no es una imagen o video válido. Tipo detectado: {mime_type}"})
                continue
            
            url = f"/static/banners/{filename}"
            thumbnail_url = None
            
            if Tipo == "video":
                thumbnail_url = generar_thumbnail(file_location, banners_dir)
            
            FechaInicio_dt = datetime.fromisoformat(FechasInicio[idx]) if FechasInicio[idx] else None
            FechaFin_dt = datetime.fromisoformat(FechasFin[idx]) if FechasFin[idx] else None
            if FechaInicio_dt and FechaFin_dt and FechaInicio_dt > FechaFin_dt:
                raise Exception("Rango inválido: FechaInicio no puede ser mayor que FechaFin.")
            titulo_sanitized = sanitize_html(Titulos[idx])
            nuevo_banner = Publicidad(
                Titulo=titulo_sanitized,
                Tipo=Tipo,
                Url=url,
                ThumbnailUrl=thumbnail_url,
                Activo=Activos[idx],
                Prioridad=Prioridades[idx],
                FechaInicio=FechaInicio_dt,
                FechaFin=FechaFin_dt,
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
    prev_titulo = banner.Titulo

    if body.activo is not None:
        banner.Activo = body.activo
    banner.FechaInicio = fecha_inicio
    banner.FechaFin = fecha_fin
    if body.titulo is not None:
        banner.Titulo = sanitize_html(body.titulo)

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
        # Obtener asignaciones para auditoría
        asignaciones_stmt = select(PublicidadAsignacion).where(PublicidadAsignacion.publicidad_id == id)
        result_asig = await db.execute(asignaciones_stmt)
        asignaciones = result_asig.scalars().all()
        
        dispositivo_ids = [a.dispositivo_id for a in asignaciones if a.dispositivo_id]
        servidor_ids = list(set([a.servidor_id for a in asignaciones if a.servidor_id]))
        
        disp_info = f", Dispositivos: {dispositivo_ids}" if dispositivo_ids else ""
        srv_info = f", Servidores: {servidor_ids}" if servidor_ids else ", Asignado a: todos"
        
        await registrar_accion(
            db,
            user_id,
            "EDICION_VIGENCIA_MULTIMEDIA",
            f"Banner IdPublicidad={banner.IdPublicidad}, Titulo={banner.Titulo or ''}, "
            f"Activo={banner.Activo}, FechaInicio={banner.FechaInicio}, FechaFin={banner.FechaFin}"
            f"{disp_info}{srv_info}",
            dispositivo_id=dispositivo_ids[0] if dispositivo_ids else None,
            servidor_id=servidor_ids[0] if servidor_ids else None,
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


@router.get("/servidores")
async def obtener_servidores(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Obtiene lista de servidores con sus dispositivos.
    """
    try:
        servidores_result = await db.execute(
            select(ServidorSecundario)
            .options(selectinload(ServidorSecundario.dispositivos))
        )
        servidores = servidores_result.scalars().all()
        
        resultado = []
        for srv in servidores:
            dispositivos = [
                {
                    "id": d.id,
                    "codigo_kiosko": d.codigo_kiosko,
                    "nombre_amigable": d.nombre_amigable,
                    "online": d.online
                }
                for d in srv.dispositivos
            ]
            resultado.append({
                "id": srv.id,
                "nombre": srv.nombre,
                "ip": srv.ip,
                "api_url": f"http://{srv.ip}:8000",
                "online": srv.ultimo_heartbeat is not None,
                "dispositivos": dispositivos
            })
        
        return {"success": True, "servidores": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener servidores: {str(e)}")


@router.post("/banners/{id}/asignaciones")
async def asignar_banner_a_dispositivos(
    id: int = Path(..., description="ID del banner"),
    asignaciones: List[AsignacionCreate] = ...,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Asigna una publicidad a dispositivos específicos.
    """
    banner = await db.get(Publicidad, id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner no encontrado.")
    
    try:
        banner.asignacion_todos = False
        await db.commit()
        
        resultados = []
        for asig in asignaciones:
            existing = await db.execute(
                select(PublicidadAsignacion).where(
                    PublicidadAsignacion.publicidad_id == id,
                    PublicidadAsignacion.servidor_id == asig.servidor_id,
                    PublicidadAsignacion.dispositivo_id == asig.dispositivo_id
                )
            )
            existente = existing.scalars().first()
            
            if existente:
                resultados.append({"servidor_id": asig.servidor_id, "dispositivo_id": asig.dispositivo_id, "status": "ya_existe"})
                continue
            
            nueva_asignacion = PublicidadAsignacion(
                publicidad_id=id,
                servidor_id=asig.servidor_id,
                dispositivo_id=asig.dispositivo_id
            )
            db.add(nueva_asignacion)
            resultados.append({"servidor_id": asig.servidor_id, "dispositivo_id": asig.dispositivo_id, "status": "creado"})
        
        await db.commit()
        
        user_id = current_user.get("user_id")
        if user_id is not None:
            await registrar_accion(
                db, user_id, "ASIGNAR_PUBLICIDAD",
                f"Publicidades asignadas a dispositivos: IdBanner={id}"
            )
        
        return {"success": True, "resultados": resultados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al asignar: {str(e)}")


@router.delete("/banners/{id}/asignaciones")
async def eliminar_asignaciones_banner(
    id: int = Path(..., description="ID del banner"),
    servidor_id: int = Query(None),
    dispositivo_id: int = Query(None),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Elimina asignaciones de una publicidad.
    Si no se especifican filtros, elimina todas las asignaciones.
    """
    try:
        query = select(PublicidadAsignacion).where(PublicidadAsignacion.publicidad_id == id)
        
        if servidor_id is not None:
            query = query.where(PublicidadAsignacion.servidor_id == servidor_id)
        if dispositivo_id is not None:
            query = query.where(PublicidadAsignacion.dispositivo_id == dispositivo_id)
        
        result = await db.execute(query)
        asignaciones = result.scalars().all()
        
        if not asignaciones:
            raise HTTPException(status_code=404, detail="No se encontraron asignaciones.")
        
        count = 0
        for asig in asignaciones:
            await db.delete(asig)
            count += 1
        
        await db.commit()
        
        return {"success": True, "eliminadas": count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar asignaciones: {str(e)}")


@router.put("/banners/{id}/asignaciones")
async def reemplazar_asignaciones_banner(
    id: int = Path(..., description="ID del banner"),
    asignacion_todos: bool = Query(True, description="Si es true, se asigna a todos"),
    servidor_ids: str = Query(None, description="IDs de servidores separados por coma"),
    dispositivo_ids: str = Query(None, description="IDs de dispositivos separados por coma"),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Reemplaza todas las asignaciones de una publicidad.
    """
    import json
    
    banner = await db.get(Publicidad, id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner no encontrado.")
    
    # ETAPA 2: Guardar estado anterior para posible rollback
    asignacion_todos_anterior = banner.asignacion_todos
    
    try:
        # ETAPA 1: Validación de seguridad temprana - verificar que hay servidores/dispositivos válidos
        # si no es asignacion_todos
        if not asignacion_todos:
            def parse_ids(ids_str):
                """Parsea IDs desde string JSON array, string separado por comas, o entero."""
                if not ids_str:
                    return []
                ids_str = str(ids_str).strip()
                if not ids_str:
                    return []
                try:
                    parsed = json.loads(ids_str)
                    if isinstance(parsed, int):
                        return [str(parsed)]
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed]
                    return []
                except (json.JSONDecodeError, TypeError):
                    return [x.strip() for x in ids_str.split(",") if x.strip()]
            
            parsed_servidor_ids = parse_ids(servidor_ids)
            parsed_dispositivo_ids = parse_ids(dispositivo_ids)
            
# NUEVA REGLA: Para asignación específica (no todos), se REQUIERE seleccionar un servidor
            # Similar a cuando se sube un archivo - debe seleccionar una sede
            if not parsed_servidor_ids:
                log.warning("fase7_validacion_fallida", 
                           banner_id=id,
                           parsed_servidor_ids=parsed_servidor_ids,
                           parsed_dispositivo_ids=parsed_dispositivo_ids,
                           mensaje="Debe seleccionar al menos un servidor para asignación específica")
                raise HTTPException(
                    status_code=400, 
                    detail="Debe seleccionar un servidor para asignación específica. Use 'Todos' si desea asignar a todos los servidores."
                )
        
        # Eliminar todas las asignaciones existentes
        await db.execute(
            select(PublicidadAsignacion).where(PublicidadAsignacion.publicidad_id == id)
        )
        result = await db.execute(
            select(PublicidadAsignacion).where(PublicidadAsignacion.publicidad_id == id)
        )
        existentes = result.scalars().all()
        for asig in existentes:
            await db.delete(asig)
        
        # Actualizar el flag de asignacion_todos
        banner.asignacion_todos = asignacion_todos
        await db.commit()
        
        target_dispositivo_ids = None
        dispositivos = []  # Definir variable para uso posterior en replicación
        
        # Si no es asignacion_todos, crear nuevas asignaciones
        if not asignacion_todos:
            parsed_servidor_ids = []
            parsed_dispositivo_ids = []
            
            # ETAPA 1: Parser robusto - acepta JSON array ["1","2"] o string "1,2,3" o entero 1
            def parse_ids(ids_str):
                """Parsea IDs desde string JSON array, string separado por comas, o entero."""
                if not ids_str:
                    return []
                ids_str = str(ids_str).strip()
                if not ids_str:
                    return []
                try:
                    # Intentar como JSON
                    parsed = json.loads(ids_str)
                    # Si es un entero solo, envolver en array
                    if isinstance(parsed, int):
                        return [str(parsed)]
                    # Si es un array, convertir todos a string
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed]
                    return []
                except (json.JSONDecodeError, TypeError):
                    # Fallback: string separado por comas
                    return [x.strip() for x in ids_str.split(",") if x.strip()]
            
            parsed_servidor_ids = parse_ids(servidor_ids)
            parsed_dispositivo_ids = parse_ids(dispositivo_ids)
            
            # ETAPA 1: Validación de seguridad - si no hay servidores/dispositivos válidos
            # y no es asignacion_todos, mantener las asignaciones anteriores
            if not parsed_servidor_ids and not parsed_dispositivo_ids:
                log.warning("fase7_asignacion_vacia", 
                           banner_id=id,
                           mensaje="No se recibieron servidores/dispositivos válidos, manteniendo asignaciones anteriores")
                # Mantener las asignaciones actuales - NO proceder con cambio
                return {"success": True, "message": "Asignaciones anteriores mantenidas (no se especificaron servidores/dispositivos nuevos)."}
            
            # Obtener dispositivos de los servidores seleccionados
            if parsed_servidor_ids or parsed_dispositivo_ids:
                # Convertir IDs a enteros para la consulta
                try:
                    parsed_servidor_ids_int = [int(x) for x in parsed_servidor_ids]
                except (ValueError, TypeError):
                    parsed_servidor_ids_int = []
                
                query = select(Dispositivo)
                if parsed_servidor_ids_int:
                    query = query.where(Dispositivo.servidor_id.in_(parsed_servidor_ids_int))
                if parsed_dispositivo_ids:
                    query = query.where(Dispositivo.codigo_kiosko.in_(parsed_dispositivo_ids))
                
                result = await db.execute(query)
                dispositivos = list(result.scalars().all())
                
                log.info("fase7_debug_dispositivos", 
                        banner_id=id,
                        parsed_servidor_ids=parsed_servidor_ids,
                        parsed_servidor_ids_int=parsed_servidor_ids_int,
                        dispositivos_encontrados=len(dispositivos),
                        dispositivos_ids=[d.codigo_kiosko for d in dispositivos])
                
                for disp in dispositivos:
                    nueva_asignacion = PublicidadAsignacion(
                        publicidad_id=id,
                        servidor_id=disp.servidor_id,
                        dispositivo_id=disp.codigo_kiosko
                    )
                    db.add(nueva_asignacion)
                
                await db.commit()
                
                # Guardar dispositivo_ids para replicación
                target_dispositivo_ids = [d.codigo_kiosko for d in dispositivos]
        
        # FASE 6: Usar procesar_cambio_asignacion para cleanup
        update_result = None
        if banner.IdPublicidad:
            try:
                # LOG: Debug asignación
                log.info("fase6_debug_inicio", 
                       banner_id=banner.IdPublicidad,
                       asignacion_todos=asignacion_todos,
                       target_dispositivo_ids=target_dispositivo_ids,
                       dispositivos_count=len(dispositivos))
                
                # Obtener TODOS los servidores
                todos_servidores_result = await db.execute(select(ServidorSecundario))
                todos_servidores = todos_servidores_result.scalars().all()
                todos_servidores_data = [
                    {
                        "id": s.id,
                        "nombre": s.nombre,
                        "ip": s.ip,
                        "api_url": f"http://{s.ip}:8000"
                    }
                    for s in todos_servidores
                ]
                
                # Preparar banner_data para procesar_cambio_asignacion
                file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", banner.Url.lstrip("/")))
                banner_data = {
                    "banner_id": banner.IdPublicidad,
                    "file_path": file_path,
                    "titulo": banner.Titulo,
                    "tipo": banner.Tipo,
                    "activo": banner.Activo,
                    "prioridad": banner.Prioridad,
                    "fecha_inicio": banner.FechaInicio.isoformat() if banner.FechaInicio else None,
                    "fecha_fin": banner.FechaFin.isoformat() if banner.FechaFin else None,
                    "dispositivo_ids": target_dispositivo_ids
                }
                
                if asignacion_todos:
                    # CASO A: Asignar a TODOS - usar procesar_cambio_asignacion
                    log.info("fase6_caso_a_inicio", banner_id=banner.IdPublicidad, 
                           srv_total=len(todos_servidores_data))
                    
                    update_result = await procesar_cambio_asignacion(
                        banner_data=banner_data,
                        servidores_todos=todos_servidores_data,
                        servidores_asignados=todos_servidores_data,
                        timeout=35
                    )
                    
                    log.info("fase6_caso_a_resultado", banner_id=banner.IdPublicidad, 
                           exito=update_result.get("exito"),
                           agregar=len(update_result.get("agregar", [])),
                           eliminar=len(update_result.get("eliminar", [])),
                           actualizar=len(update_result.get("actualizar", [])))
                else:
                    # CASO B/D: Asignación específica - usar procesar_cambio_asignacion
                    if target_dispositivo_ids:
                        servidor_ids_asignados = list(set([d.servidor_id for d in dispositivos]))
                        servidores_asignados_result = await db.execute(
                            select(ServidorSecundario).where(ServidorSecundario.id.in_(servidor_ids_asignados))
                        )
                        servidores_asignados = servidores_asignados_result.scalars().all()
                        servidores_asignados_data = [
                            {
                                "id": s.id,
                                "nombre": s.nombre,
                                "ip": s.ip,
                                "api_url": f"http://{s.ip}:8000"
                            }
                            for s in servidores_asignados
                        ]
                    else:
                        servidores_asignados_data = []
                    
                    log.info("fase6_procesando_cambio", banner_id=banner.IdPublicidad, 
                           srv_objetivo=len(servidores_asignados_data),
                           srv_total=len(todos_servidores_data))
                    
                    # USAR LA NUEVA FUNCIÓN FASE 6 para cleanup
                    update_result = await procesar_cambio_asignacion(
                        banner_data=banner_data,
                        servidores_todos=todos_servidores_data,
                        servidores_asignados=servidores_asignados_data,
                        timeout=35
                    )
                    
                    log.info("fase6_resultado", banner_id=banner.IdPublicidad, exito=update_result.get("exito"),
                           agregar=len(update_result.get("agregar", [])),
                           eliminar=len(update_result.get("eliminar", [])),
                           actualizar=len(update_result.get("actualizar", [])))
                    
                    # ETAPA 4: Verificar resultado y notificar si hay fallos
                    if update_result and not update_result.get("exito"):
                        errores = []
                        # Revisar errores en agregar
                        for item in update_result.get("agregar", []):
                            if not item.get("success"):
                                errores.append(item)
                        # Revisar errores en eliminar
                        for item in update_result.get("eliminar", []):
                            if not item.get("success"):
                                errores.append(item)
                        # Revisar errores en actualizar
                        for item in update_result.get("actualizar", []):
                            if not item.get("success"):
                                errores.append(item)
                        
                        if errores:
                            for error in errores:
                                srv_nombre = error.get("servidor_nombre", "Desconocido")
                                srv_id = error.get("servidor_id")
                                error_msg = error.get("error", error.get("message", "Error desconocido"))
                                
                                # Registrar en logs
                                log.error("fase7_replicacion_fallida",
                                          banner_id=banner.IdPublicidad,
                                          banner_titulo=banner.Titulo,
                                          servidor_nombre=srv_nombre,
                                          error=error_msg)
                                
                                # Crear notificación al dashboard
                                from app.services.notificacion_service import registrar_accion
                                await registrar_accion(
                                    db=db,
                                    usuario_id=current_user.get("user_id") if current_user else None,
                                    tipo="ERROR_REPLICACION_ASIGNACION",
                                    descripcion=f"Error al replicar banner '{banner.Titulo}' en servidor '{srv_nombre}': {error_msg}",
                                    servidor_id=srv_id,
                                    dispositivo_id=None
                                )
                            await db.commit()
                            # Revertir el cambio de asignacion_todos si hay errores
                            banner.asignacion_todos = asignacion_todos_anterior
                            await db.commit()
                            return {"success": False, "message": f"Error en replicación. No se aplicaron los cambios. Errores: {len(errores)}"}
                
            except Exception as e:
                log.error("fase6_error", banner_id=banner.IdPublicidad, error=str(e))
        
        return {"success": True, "message": "Asignaciones actualizadas correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar asignaciones: {str(e)}")


@router.post("/banners/sincronizar")
async def sincronizar_banners(
    publicidad_ids: List[int] = ...,
    servidor_ids: List[int] = ...,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Sincroniza publicidades específicas a servidores específicos.
    """
    try:
        servidores_result = await db.execute(
            select(ServidorSecundario).where(ServidorSecundario.id.in_(servidor_ids))
        )
        servidores = servidores_result.scalars().all()
        
        if not servidores:
            raise HTTPException(status_code=404, detail="Servidores no encontrados.")
        
        resultados = []
        for srv in servidores:
            dispositivo_ids_result = await db.execute(
                select(Dispositivo.codigo_kiosko).where(Dispositivo.servidor_id == srv.id)
            )
            dispositivo_ids = [d[0] for d in dispositivo_ids_result.fetchall()]
            
            sync_result = await sync_a_servidor(
                servidor_ip=srv.ip,
                dispositivo_ids=dispositivo_ids,
                publicidad_ids=publicidad_ids
            )
            
            resultados.append({
                "servidor_id": srv.id,
                "servidor_nombre": srv.nombre,
                "ip": srv.ip,
                "dispositivos_count": len(dispositivo_ids),
                "sync_result": sync_result
            })
        
        user_id = current_user.get("user_id")
        if user_id is not None:
            await registrar_accion(
                db, user_id, "SINCRONIZAR_PUBLICIDADES",
                f"Sincronización: {len(publicidad_ids)} publicidades a {len(servidores)} servidores"
            )
        
        return {"success": True, "resultados": resultados}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al sincronizar: {str(e)}")

