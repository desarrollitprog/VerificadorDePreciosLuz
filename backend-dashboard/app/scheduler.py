"""
Módulo de scheduler para tareas periódicas.
Utiliza APScheduler con AsyncIOScheduler para tareas asíncronas.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from app.utils.logger import StructuredLogger

log = StructuredLogger("scheduler")

_scheduler: AsyncIOScheduler | None = None


def iniciar_scheduler() -> AsyncIOScheduler:
    """
    Inicializa y devuelve el scheduler.
    Agrega el job de monitoreo de sesiones cada 3.5 minutos.
    """
    global _scheduler
    if _scheduler is not None:
        log.info("scheduler_ya_iniciado")
        return _scheduler

    from app.services.monitoreo_service import actualizar_sesiones_dispositivos

    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        actualizar_sesiones_dispositivos,
        'interval',
        minutes=3.5,
        id='monitoreo_sesiones',
        replace_existing=True
    )

    def job_executed_listener(event):
        if event.exception:
            log.error("job_fallo", job_id=event.job_id, error=str(event.exception))
        else:
            log.info("job_ok", job_id=event.job_id)

    _scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    _scheduler.start()
    log.info("scheduler_iniciado", intervalo_minutos=3.5, job_id="monitoreo_sesiones")
    return _scheduler


def obtener_scheduler() -> AsyncIOScheduler | None:
    """Retorna el scheduler actual, o None si no está inicializado."""
    return _scheduler


def detener_scheduler() -> None:
    """Detiene el scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=True)
        _scheduler = None
        log.info("scheduler_detenido")