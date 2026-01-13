import os
from typing import List
from fastapi import APIRouter
from ..schemas import PublicidadSchema

router = APIRouter()



@router.get("/banners", response_model=List[PublicidadSchema])
async def listar_banners():
    base = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "static", "banners")
    )
    banners = []
    if os.path.isdir(base):
        for fn in sorted(os.listdir(base)):
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                banners.append(
                    {
                        "id": len(banners) + 1,
                        "titulo": fn,
                        "imagen": f"/static/banners/{fn}",
                        "activo": True,
                    }
                )
    return banners
