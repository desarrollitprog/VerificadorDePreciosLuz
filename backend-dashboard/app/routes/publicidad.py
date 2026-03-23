import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Path, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
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
    sync_a_servidor
)


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


class AsignacionCreate(BaseModel):
    servidor_id: int
    dispositivo_id: int


class BannerUploadBody(BaseModel):
    Titulo: Optional[str] = None
    Activo: bool = True
    Prioridad: int = 0
    FechaInicio: Optional[str] = None
    FechaFin: Optional[str] = None
    DuracionSeg: Optional[int] = None
    AsignacionTodos: bool = True
    Asignaciones: Optional[List[AsignacionCreate]] = None


@router.get("/banners")
async def listar_banners(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    try:
        total_dispositivos_result = await db.execute(select(func.count(Dispositivo.id)))
        total_dispositivos = total_dispositivos_result.scalar() or 0
        
        result = await db.execute(
            select(Publicidad)
            .options(selectinload(Publicidad.asignaciones).selectinload(PublicidadAsignacion.servidor))
            .options(selectinload(Publicidad.asignaciones).selectinload(PublicidadAsignacion.dispositivo))
            .order_by(Publicidad.IdPublicidad.desc())
        )
        banners = result.scalars().all()
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
                        "dispositivo_nombre": asig.dispositivo.nombre_amigable if asig.dispositivo else None,
                        "dispositivo_codigo": asig.dispositivo.codigo_kiosko if asig.dispositivo else None,
                    })
                dispositivos_count = len(asignaciones)
            
            estado = "activo"
            if not banner.Activo:
                estado = "inactivo"
            elif not banner.asignacion_todos and len(asignaciones) == 0:
                estado = "borrador"
            elif banner.FechaFin and banner.FechaFin < datetime.utcnow():
                estado = "vencido"
            
            banners_payload.append(
                {
                    "IdPublicidad": banner.IdPublicidad,
                    "Titulo": banner.Titulo,
                    "Tipo": banner.Tipo,
                    "Url": banner.Url,
                    "Activo": banner.Activo,
                    "FechaInicio": banner.FechaInicio.isoformat() if banner.FechaInicio else None,
                    "FechaFin": banner.FechaFin.isoformat() if banner.FechaFin else None,
                    "DuracionSeg": banner.DuracionSeg,
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
            DuracionSeg=DuracionSeg,
            asignacion_todos=AsignacionTodos
        )
        db.add(nuevo_banner)
        await db.commit()
        await db.refresh(nuevo_banner)
        print(f"Se ha guardado correctamente en la base de datos: Id={nuevo_banner.IdPublicidad}, Titulo={nuevo_banner.Titulo}, Url={nuevo_banner.Url}")

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
        # Guardar cuando: (NO es "todos" Y hay servidores/dispositivos) O (es "todos" pero hay dispositivos específicos seleccionados)
        print(f"[DEBUG] AsignacionTodos={AsignacionTodos}, selected_servidor_ids={selected_servidor_ids}, selected_dispositivo_ids={selected_dispositivo_ids}")
        guardar_asignaciones = (not AsignacionTodos and (selected_servidor_ids or selected_dispositivo_ids)) or (AsignacionTodos and selected_dispositivo_ids)
        if guardar_asignaciones:
            print(f"Guardando asignaciones para publicidad {nuevo_banner.IdPublicidad}: servidores={selected_servidor_ids}, dispositivos={selected_dispositivo_ids}")
            
            # Obtener dispositivos de los servidores seleccionados (usando codigo_kiosko para strings)
            dispositivos_query = select(Dispositivo)
            if selected_servidor_ids:
                dispositivos_query = dispositivos_query.where(Dispositivo.servidor_id.in_(selected_servidor_ids))
            if selected_dispositivo_ids:
                # Los selected_dispositivo_ids son strings (codigo_kiosko), no ids enteros
                dispositivos_query = dispositivos_query.where(Dispositivo.codigo_kiosko.in_(selected_dispositivo_ids))
            
            dispositivos_result = await db.execute(dispositivos_query)
            dispositivos = dispositivos_result.scalars().all()
            print(f"[DEBUG] Dispositivos encontrados: {len(dispositivos)}")
            
            # Crear registros de asignación - guardar codigo_kiosko como dispositivo_id (string)
            for disp in dispositivos:
                asignacion = PublicidadAsignacion(
                    publicidad_id=nuevo_banner.IdPublicidad,
                    servidor_id=disp.servidor_id,
                    dispositivo_id=disp.codigo_kiosko
                )
                db.add(asignacion)
            
            await db.commit()
            print(f"Asignaciones guardadas: {len(dispositivos)} registros")
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
            print(f"Replicando archivo a TODAS las APIs: {file_location}")
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
                dispositivo_ids=None,
            )
        elif selected_dispositivo_ids:
            print(f"Replicando archivo a dispositivos específicos: {selected_dispositivo_ids}")
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
                dispositivo_ids=selected_dispositivo_ids,
            )
        elif selected_servidor_ids or selected_dispositivo_ids:
            print(f"Replicando archivo a servidores seleccionados: {selected_servidor_ids}")
            query = select(ServidorSecundario)
            if selected_servidor_ids:
                query = query.where(ServidorSecundario.id.in_(selected_servidor_ids))
            servidores_result = await db.execute(query)
            servidores = servidores_result.scalars().all()
            servidores_data = [
                {
                    "id": s.id,
                    "nombre": s.nombre,
                    "ip": s.ip,
                    "api_url": s.api_url or f"http://{s.ip}:8000"
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
                duracion_seg=DuracionSeg,
                activo=Activo,
                dispositivo_ids=selected_dispositivo_ids,
            )
        else:
            print("No se replicó a ningún servidor (asignación específica sin servidores seleccionados)")
        print(f"Replicación finalizada: {replicacion_resultados}")
    except Exception as e:
        print(f"Error en replicación: {str(e)}")

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
                "api_url": srv.api_url or f"http://{srv.ip}:8000",
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

