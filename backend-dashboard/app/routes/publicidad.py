import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models import Publicidad
from ..schemas import PublicidadResponse, PublicidadCreate
from ..database import get_db_usuarios

router = APIRouter()

@router.get("/banners", response_model=List[PublicidadResponse])
async def listar_banners(db: AsyncSession = Depends(get_db_usuarios)):
    result = await db.execute(select(Publicidad).order_by(Publicidad.prioridad, Publicidad.id))
    banners = result.scalars().all()
    return banners

@router.post("/banners", response_model=PublicidadResponse)
async def crear_banner(banner: PublicidadCreate, db: AsyncSession = Depends(get_db_usuarios)):
    nuevo_banner = Publicidad(**banner.dict())
    db.add(nuevo_banner)
    await db.commit()
    await db.refresh(nuevo_banner)
    return nuevo_banner

@router.get("/banners/list")
def listar_archivos_banners():
    banners_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners")
    )
    archivos = []
    if os.path.exists(banners_dir):
        archivos = [f for f in os.listdir(banners_dir) if os.path.isfile(os.path.join(banners_dir, f))]
    return {"banners": archivos}

@router.post("/banners/upload")
async def upload_banner(file: UploadFile = File(...)):
    banners_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners")
    )
    os.makedirs(banners_dir, exist_ok=True)
    file_location = os.path.join(banners_dir, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Detecta tipo por extensión
    ext = file.filename.lower().split('.')[-1]
    tipo = "video" if ext in ["mp4", "webm", "mkv"] else "image"
    return {
        "filename": file.filename,
        "url": f"/static/banners/{file.filename}",
        "tipo": tipo
    }



