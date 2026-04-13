import logging
import json
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)


def set_trace_id(trace_id: str) -> None:
    """Establece el trace_id para el contexto actual."""
    trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """Obtiene el trace_id del contexto actual."""
    return trace_id_var.get()


def set_user_id(user_id: int | None) -> None:
    """Establece el user_id para el contexto actual."""
    user_id_var.set(user_id)


def get_user_id() -> int | None:
    """Obtiene el user_id del contexto actual."""
    return user_id_var.get()


def setup_logging(level: str = "INFO") -> None:
    """
    Configura el logging global de la aplicación.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)


class StructuredLogger:
    """
    Logger estructurado que genera logs en formato JSON.
    Incluye trace_id, user_id y timestamp automáticamente.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
    
    def _build_extra(self, **kwargs: Any) -> dict[str, Any]:
        """Construye el diccionario extra, filtrando valores None."""
        extra = {}
        
        trace_id = get_trace_id()
        if trace_id:
            extra["trace_id"] = trace_id
        
        user_id = get_user_id()
        if user_id is not None:
            extra["user_id"] = user_id
        
        for key, value in kwargs.items():
            if value is not None:
                extra[key] = value
        
        return extra
    
    def _log(self, level: int, event: str, **kwargs: Any) -> None:
        """Genera un log estructurado en formato JSON."""
        extra = self._build_extra(**kwargs)
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "logger": self.name,
            "event": event,
            **extra
        }
        
        self.logger.log(level, json.dumps(log_data))
    
    def debug(self, event: str, **kwargs: Any) -> None:
        """Log de nivel DEBUG."""
        self._log(logging.DEBUG, event, **kwargs)
    
    def info(self, event: str, **kwargs: Any) -> None:
        """Log de nivel INFO."""
        self._log(logging.INFO, event, **kwargs)
    
    def warning(self, event: str, **kwargs: Any) -> None:
        """Log de nivel WARNING."""
        self._log(logging.WARNING, event, **kwargs)
    
    def error(self, event: str, **kwargs: Any) -> None:
        """Log de nivel ERROR."""
        self._log(logging.ERROR, event, **kwargs)
    
    def critical(self, event: str, **kwargs: Any) -> None:
        """Log de nivel CRITICAL."""
        self._log(logging.CRITICAL, event, **kwargs)


replicacion_logger = StructuredLogger("replicacion")