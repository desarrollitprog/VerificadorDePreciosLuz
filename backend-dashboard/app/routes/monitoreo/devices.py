import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.dependencies import get_current_cliente, get_current_admin
from app.models.dispositivo import Dispositivo
from app.services.device_service import rename_device, delete_device, get_device_content, reboot_device, purge_device, program_reboot

router = APIRouter(tags=["monitoreo"])
logger = logging.getLogger("uvicorn.error")


class DeviceRenameBody(BaseModel):
    nombre_amigable: str | None = None


class DeviceTipoBody(BaseModel):
    tipo: str


class ProgramarReinicioBody(BaseModel):
    device_ids: list[str] = []
    hour: str
    recurring: bool = True


@router.patch("/dispositivos/{device_id}/nombre")
async def renombrar_dispositivo(
    device_id: str,
    body: DeviceRenameBody,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    user_id = current_user.get("user_id") if current_user else None
    result = await rename_device(db, device_id, body.nombre_amigable, user_id)
    if not result.get("success"):
        raise HTTPException(status_code=result.get("status_code", 400), detail=result.get("detail"))
    return result


@router.patch("/dispositivos/{device_id}/tipo")
async def cambiar_tipo_dispositivo(
    device_id: str,
    body: DeviceTipoBody,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    if body.tipo not in ("verificador", "televisor"):
        raise HTTPException(status_code=400, detail="tipo debe ser 'verificador' o 'televisor'")
    from sqlalchemy import select, update
    stmt = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result = await db.execute(stmt)
    dispositivo = result.scalars().first()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    dispositivo.tipo = body.tipo
    await db.commit()
    user_id = current_user.get("user_id") if current_user else None
    from app.services.notificacion_service import registrar_accion
    await registrar_accion(
        db,
        usuario_id=user_id,
        tipo="auditoria",
        descripcion=f"Tipo de dispositivo {device_id} cambiado a {body.tipo}",
    )
    return {"success": True, "device_id": device_id, "tipo": body.tipo}


@router.delete("/dispositivos/{device_id}")
async def eliminar_dispositivo(
    device_id: str,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    user_id = current_user.get("user_id") if current_user else None
    result = await delete_device(db, device_id, user_id)
    if not result.get("success"):
        raise HTTPException(status_code=result.get("status_code", 400), detail=result.get("detail"))
    return result


@router.get("/dispositivos/{device_id}/contenido")
async def get_device_content_endpoint(
    device_id: str,
    db: AsyncSession = Depends(get_db_usuarios),
):
    result = await get_device_content(db, device_id)
    if not result.get("success", True) and result.get("status_code") == 404:
        raise HTTPException(status_code=404, detail=result.get("detail"))
    return result


@router.post("/dispositivos/{device_id}/reiniciar")
async def reiniciar_dispositivo(
    device_id: str,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    user_id = current_user.get("user_id") if current_user else None
    actor_name = current_user.get("nombre_usuario") or current_user.get("usuario") or "Sistema"
    result = await reboot_device(db, device_id, user_id, actor_name)
    if not result.get("success"):
        raise HTTPException(status_code=result.get("status_code", 500), detail=result.get("detail"))
    return result.get("result")


@router.post("/dispositivos/{device_id}/purge")
async def limpiar_cache_dispositivo(
    device_id: str,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    user_id = current_user.get("user_id") if current_user else None
    actor_name = current_user.get("nombre_usuario") or current_user.get("usuario") or "Sistema"
    result = await purge_device(db, device_id, user_id, actor_name)
    if not result.get("success"):
        raise HTTPException(status_code=result.get("status_code", 500), detail=result.get("detail"))
    return result.get("result")


@router.post("/dispositivos/programar-reinicio")
async def programar_reinicio_masivo(
    body: ProgramarReinicioBody,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    user_id = current_user.get("user_id") if current_user else None
    actor_name = current_user.get("nombre_usuario") or current_user.get("usuario") or "Sistema"
    result = await program_reboot(db, body.device_ids, body.hour, body.recurring, user_id, actor_name)
    if not result.get("success", True) and result.get("status_code"):
        raise HTTPException(status_code=result.get("status_code"), detail=result.get("detail"))
    return result
