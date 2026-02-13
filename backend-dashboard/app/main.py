# main.py para backend dashboard

from fastapi import FastAPI
from app.routes import publicidad, auth
from fastapi.staticfiles import StaticFiles
import os


# Asegura que la carpeta static/banners existe
os.makedirs("static/banners", exist_ok=True)

app = FastAPI(title="Dashboard Backend", version="1.0.0")

app.include_router(publicidad.router)
app.include_router(auth.router)
app.mount("/static", StaticFiles(directory="static"), name="static")
