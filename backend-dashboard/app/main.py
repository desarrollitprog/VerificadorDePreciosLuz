# main.py para backend dashboard


from fastapi import FastAPI
from app.routes import publicidad, auth
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os


# Asegura que la carpeta static/banners existe
os.makedirs("static/banners", exist_ok=True)


app = FastAPI(title="Dashboard Backend", version="1.0.0")

# Middleware CORS para permitir peticiones del frontend
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # Cambia esto por el dominio de tu frontend en producción
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(publicidad.router)
app.include_router(auth.router)
app.mount("/static", StaticFiles(directory="static"), name="static")
