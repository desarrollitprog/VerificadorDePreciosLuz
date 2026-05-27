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
    Agrega jobs de monitoreo cada 3.5 minutos.
    """
    global _scheduler
    if _scheduler is not None:
        log.info("scheduler_ya_iniciado")
        return _scheduler

    from app.services.monitoreo_service import actualizar_sesiones_dispositivos
    from app.services.publicidad_service import expirar_banners_vencidos
    from app.cleanup_service import cleanup_old_sessions, cleanup_old_notifications, cleanup_orphan_files
    from app.services.metricas_service import consolidar_por_hora, limpiar_metricas_antiguas, agregar_metricas_diarias

    _scheduler = AsyncIOScheduler()

    # Job 1: Monitoreo de sesiones de dispositivos
    _scheduler.add_job(
        actualizar_sesiones_dispositivos,
        'interval',
        minutes=3.5,
        id='monitoreo_sesiones',
        replace_existing=True
    )

    # Job 2: Expirar banners vencidos (cada 3.5 minutos)
    _scheduler.add_job(
        expirar_banners_vencidos,
        'interval',
        minutes=3.5,
        id='expirar_banners',
        replace_existing=True
    )

    # Job 3: Limpiar sesiones antiguas (>90 días) cada 15 días
    _scheduler.add_job(
        cleanup_old_sessions,
        'interval',
        days=15,
        id='limpiar_sesiones',
        replace_existing=True
    )

    # Job 4: Limpiar notificaciones viejas (>15 días) cada 15 días
    _scheduler.add_job(
        cleanup_old_notifications,
        'interval',
        days=15,
        id='limpiar_notificaciones',
        replace_existing=True
    )

    # Job 5: Limpiar archivos huérfanos cada 24 horas
    _scheduler.add_job(
        cleanup_orphan_files,
        'interval',
        hours=24,
        id='limpiar_archivos_huérfanos',
        replace_existing=True
    )

    # Job 6: Consolidar métricas de reproducción cada hora
    async def _consolidar_metricas():
        from app.database import AsyncSessionLocalUsuarios
        async with AsyncSessionLocalUsuarios() as db:
            await consolidar_por_hora(db)

    _scheduler.add_job(
        _consolidar_metricas,
        'cron',
        minute=5,
        id='consolidar_reproducciones',
        replace_existing=True
    )

    # Job 7: Limpiar métricas antiguas (12:05 AM Venezuela = 4:05 AM UTC)
    async def _limpiar_metricas():
        from app.database import AsyncSessionLocalUsuarios
        async with AsyncSessionLocalUsuarios() as db:
            await limpiar_metricas_antiguas(db)

    _scheduler.add_job(
        _limpiar_metricas,
        'cron',
        hour=4,
        minute=5,
        id='limpiar_metricas_antiguas',
        replace_existing=True
    )

    # Job 8: Agregar métricas diarias (12:00 AM Venezuela = 4:00 AM UTC)
    async def _agregar_metricas():
        from app.database import AsyncSessionLocalUsuarios
        async with AsyncSessionLocalUsuarios() as db:
            await agregar_metricas_diarias(db)

    _scheduler.add_job(
        _agregar_metricas,
        'cron',
        hour=4,
        minute=0,
        id='agregar_metricas_diarias',
        replace_existing=True
    )

    # Job 9: Bulk insert de reproducciones desde Redis cada 5 minutos
    from app.services.bulk_metrics import bulk_insert_reproducciones
    _scheduler.add_job(
        bulk_insert_reproducciones,
        'interval',
        minutes=5,
        id='bulk_insert_reproducciones',
        replace_existing=True,
        max_instances=1,
        coalesce=True
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