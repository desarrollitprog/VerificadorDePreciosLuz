# main.py para backend dashboard
from fastapi import FastAPI
from app.routes import consultas, publicidad
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Dashboard Backend", version="1.0.0")

app.include_router(consultas.router)
app.include_router(publicidad.router)
app.mount("/static", StaticFiles(directory="static"), name="static")
