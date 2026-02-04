import os
from typing import List
from fastapi import APIRouter
from ..schemas import PublicidadResponse

router = APIRouter()



@router.get("/banners", response_model=List[PublicidadResponse])
async def listar_banners():
    base = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners")
    )
    banners = []
    if os.path.isdir(base):
        for fn in sorted(os.listdir(base)):
            lower = fn.lower()
            if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                tipo = "image"
            elif lower.endswith((".mp4", ".webm", ".mkv")):
                tipo = "video"
            else:
                continue

            banners.append(
                {
                    "id": len(banners) + 1,
                    "titulo": fn,
                    "tipo": tipo,
                    "url": f"/static/banners/{fn}",
                    "activo": True,
                    "prioridad": len(banners),
                    "fecha_inicio": None,
                    "fecha_fin": None,
                    "duracion_seg": None,
                    "updated_at": None,
                }
            )
    return banners
