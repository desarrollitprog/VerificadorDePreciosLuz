"""
Pruebas unitarias para el módulo de retry logic.
"""
import sys
import os
import io

_old_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
from app.utils.logger import setup_logging
from app.services.replicacion_service import (
    retry_with_backoff,
    is_retryable_error,
    RETRY_MAX_ATTEMPTS,
    RETRY_MIN_WAIT,
    RETRY_MAX_WAIT
)

setup_logging("DEBUG")

def test_is_retryable_error():
    """Verificar qué errores son reintentables."""
    assert is_retryable_error(httpx.TimeoutException("timeout")) == True
    assert is_retryable_error(httpx.ConnectError("connect error")) == True
    assert is_retryable_error(httpx.RemoteProtocolError("protocol error")) == True
    assert is_retryable_error(httpx.HTTPStatusError("status error", request=None, response=None)) == False
    assert is_retryable_error(ValueError("value error")) == False
    print("✓ test_is_retryable_error passed")

def test_retry_config():
    """Verificar configuración de retry."""
    assert RETRY_MAX_ATTEMPTS >= 1
    assert RETRY_MIN_WAIT >= 0
    assert RETRY_MAX_WAIT >= RETRY_MIN_WAIT
    print(f"✓ test_retry_config passed (attempts={RETRY_MAX_ATTEMPTS}, min_wait={RETRY_MIN_WAIT}, max_wait={RETRY_MAX_WAIT})")

async def test_successful_call():
    """Verificar que las llamadas exitosas no reintentan."""
    call_count = 0
    
    async def success_func():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await retry_with_backoff(success_func)
    assert result == "success"
    assert call_count == 1
    print("✓ test_successful_call passed")

async def test_retry_on_timeout():
    """Verificar retry en timeout."""
    call_count = 0
    
    async def timeout_then_success():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.TimeoutException("timeout")
        return "success"
    
    result = await retry_with_backoff(
        timeout_then_success,
        max_attempts=3,
        min_wait=0,  
        max_wait=0
    )
    assert result == "success"
    assert call_count == 3
    print("✓ test_retry_on_timeout passed")

async def test_max_retries_exceeded():
    """Verificar que se lanza excepción después de max retries."""
    call_count = 0
    
    async def always_fail():
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("always timeout")
    
    try:
        await retry_with_backoff(
            always_fail,
            max_attempts=3,
            min_wait=0,
            max_wait=0
        )
        assert False, "Should have raised exception"
    except httpx.TimeoutException:
        pass
    
    assert call_count == 3
    print("✓ test_max_retries_exceeded passed")

async def test_non_retryable_error():
    """Verificar que errores no reintentables fallan inmediatamente."""
    call_count = 0
    
    async def non_retryable():
        nonlocal call_count
        call_count += 1
        raise ValueError("not retryable")
    
    try:
        await retry_with_backoff(
            non_retryable,
            max_attempts=3,
            min_wait=0,
            max_wait=0
        )
        assert False, "Should have raised exception"
    except ValueError:
        pass
    
    assert call_count == 1
    print("✓ test_non_retryable_error passed")

async def test_http_status_error_not_retried():
    """Verificar que HTTPStatusError (como 500) no se reintenta."""
    call_count = 0
    
    async def http_error():
        nonlocal call_count
        call_count += 1
        raise httpx.HTTPStatusError(
            "500",
            request=None,
            response=httpx.Response(500)
        )
    
    try:
        await retry_with_backoff(
            http_error,
            max_attempts=3,
            min_wait=0,
            max_wait=0
        )
        assert False, "Should have raised exception"
    except httpx.HTTPStatusError:
        pass
    
    assert call_count == 1
    print("✓ test_http_status_error_not_retried passed")

if __name__ == "__main__":
    print("=" * 50)
    print("Ejecutando pruebas de retry logic")
    print("=" * 50)
    
    test_is_retryable_error()
    test_retry_config()
    
    asyncio.run(test_successful_call())
    asyncio.run(test_retry_on_timeout())
    asyncio.run(test_max_retries_exceeded())
    asyncio.run(test_non_retryable_error())
    asyncio.run(test_http_status_error_not_retried())
    
    print("=" * 50)
    print("Todas las pruebas de retry pasaron ✓")
    print("=" * 50)
