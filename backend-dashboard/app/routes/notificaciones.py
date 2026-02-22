from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Notificacion
from app.database import get_db_usuarios
from app.dependencies import get_current_admin

router = APIRouter()

@router.get("/notificaciones")
async def listar_notificaciones(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    stmt = (
        select(Notificacion)
        .order_by(Notificacion.fecha_creacion.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    notificaciones = result.scalars().all()
    return {
        "success": True,
        "notificaciones": [n.__dict__ for n in notificaciones],
        "limit": limit,
        "offset": offset,
        "count": len(notificaciones)
    }
