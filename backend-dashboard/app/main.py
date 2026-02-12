# main.py para backend dashboard
from fastapi import FastAPI
from app.routes import publicidad, auth
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Dashboard Backend", version="1.0.0")

app.include_router(publicidad.router)
app.include_router(auth.router)
app.mount("/static", StaticFiles(directory="static"), name="static")
