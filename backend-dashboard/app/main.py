# main.py para backend dashboard


from fastapi import FastAPI
from app.routes import publicidad, auth, monitoreo, usuarios, notificaciones
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os


# Asegura que la carpeta static/banners existe
os.makedirs("static/banners", exist_ok=True)


app = FastAPI(title="Dashboard Backend", version="1.0.0")

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
if not allowed_origins:
    raise RuntimeError("ALLOWED_ORIGINS debe tener al menos un origen válido")
if "*" in allowed_origins:
    raise RuntimeError("ALLOWED_ORIGINS no puede contener '*' en producción")

# Middleware CORS para permitir peticiones del frontend
app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
	allow_headers=["Authorization", "Content-Type", "X-API-KEY"],
)

app.include_router(publicidad.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(monitoreo.router, prefix="/api")
app.include_router(notificaciones.router, prefix="/api")
app.mount("/static", StaticFiles(directory="static"), name="static")
