"""
Pruebas unitarias para el módulo de logging estructurado.
"""
import sys
import os
import io

_old_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.logger import (
    StructuredLogger,
    setup_logging,
    set_trace_id,
    set_user_id,
    get_trace_id
)
import logging

def test_logger_creation():
    """Verificar que se puede crear un logger."""
    log = StructuredLogger("test")
    assert log.logger is not None
    print("✓ test_logger_creation passed")

def test_logging_levels():
    """Verificar que los niveles de logging funcionan."""
    setup_logging("DEBUG")
    log = StructuredLogger("test_levels")
    
    try:
        log.debug("debug_message", key="value")
        log.info("info_message", key="value")
        log.warning("warning_message", key="value")
        log.error("error_message", key="value")
        print("✓ test_logging_levels passed")
    except Exception as e:
        print(f"✗ test_logging_levels failed: {e}")
        raise

def test_trace_id_context():
    """Verificar que el trace_id se maneja correctamente."""
    set_trace_id("test-trace-123")
    assert get_trace_id() == "test-trace-123"
    
    set_trace_id("another-trace-456")
    assert get_trace_id() == "another-trace-456"
    print("✓ test_trace_id_context passed")

def test_user_id_context():
    """Verificar que el user_id se maneja correctamente."""
    set_user_id(123)
    log = StructuredLogger("test_user")
    log.info("message_with_user")
    print("✓ test_user_id_context passed")

def test_log_with_extra_data():
    """Verificar que se pueden agregar datos extra."""
    log = StructuredLogger("test_extra")
    log.info("event_name", 
             banner_id=5, 
             servidores=["srv1", "srv2"],
             success=True)
    print("✓ test_log_with_extra_data passed")

def test_log_with_exception():
    """Verificar que las excepciones se incluyen."""
    log = StructuredLogger("test_exception")
    try:
        raise ValueError("Test error")
    except Exception as e:
        log.error("exception_test", error=str(e))
    print("✓ test_log_with_exception passed")

if __name__ == "__main__":
    print("=" * 50)
    print("Ejecutando pruebas de logging estructurado")
    print("=" * 50)
    
    test_logger_creation()
    test_logging_levels()
    test_trace_id_context()
    test_user_id_context()
    test_log_with_extra_data()
    test_log_with_exception()
    
    print("=" * 50)
    print("Todas las pruebas de logging pasaron ✓")
    print("=" * 50)
