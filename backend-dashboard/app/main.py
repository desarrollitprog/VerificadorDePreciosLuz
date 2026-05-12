from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.routes import publicidad, auth, monitoreo, usuarios, notificaciones, auditoria
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.utils.health import get_health_status
from app.scheduler import iniciar_scheduler, detener_scheduler
import logging
import time
import os
import uuid
from app.utils.logger import setup_logging, set_trace_id, set_user_id, StructuredLogger


@asynccontextmanager
async def lifespan(app: FastAPI):
    iniciar_scheduler()
    yield
    detener_scheduler()


os.makedirs("static/banners", exist_ok=True)

setup_logging(os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="Dashboard Backend", version="1.0.0", lifespan=lifespan)
logger = logging.getLogger("uvicorn.error")
request_logger = StructuredLogger("requests")

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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "Error interno del servidor"},
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
	trace_id = str(uuid.uuid4())
	set_trace_id(trace_id)
	
	auth_header = request.headers.get("Authorization", "")
	user_id = None
	if auth_header.startswith("Bearer "):
		try:
			from jose import jwt
			SECRET_KEY = os.getenv("SECRET_KEY", "secret")
			token = auth_header[7:]
			payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
			user_id = payload.get("user_id")
		except Exception:
			request_logger.warning("jwt_decode_failed")
	
	if user_id:
		set_user_id(user_id)
	
	start = time.perf_counter()
	response = await call_next(request)
	duration_ms = (time.perf_counter() - start) * 1000
	
	request_logger.info(
		"http_request",
		method=request.method,
		path=request.url.path,
		status_code=response.status_code,
		duration_ms=round(duration_ms, 2),
		trace_id=trace_id,
		user_id=user_id
	)
	return response

@app.get("/health")
async def health_check():
    health = await get_health_status()
    status_code = 200 if health["status"] == "healthy" else 503
    return health, status_code


app.include_router(publicidad.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(monitoreo.router, prefix="/api")
app.include_router(notificaciones.router, prefix="/api")
app.include_router(auditoria.router, prefix="/api")
app.mount("/static", StaticFiles(directory="static"), name="static")
