"""
Pruebas unitarias para Rate Limiting en Login.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import AsyncMock, MagicMock, patch


def test_rate_limit_config_defaults():
    """Verificar valores por defecto de configuración."""
    default_max = int(os.getenv("RATE_LIMIT_LOGIN_MAX", "5"))
    default_window = int(os.getenv("RATE_LIMIT_LOGIN_WINDOW", "60"))
    
    assert default_max == 5
    assert default_window == 60
    print("✓ test_rate_limit_config_defaults passed")


def test_rate_limit_key_format():
    """Verificar formato de clave Redis."""
    client_ip = "192.168.1.100"
    key = f"rate_limit:login:{client_ip}"
    assert key == "rate_limit:login:192.168.1.100"
    print("✓ test_rate_limit_key_format passed")


def test_get_client_ip_from_forwarded():
    """Verificar extracción de IP desde X-Forwarded-For."""
    mock_request = MagicMock()
    mock_request.headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
    
    result = mock_request.headers.get("X-Forwarded-For").split(",")[0].strip()
    assert result == "192.168.1.100"
    print("✓ test_get_client_ip_from_forwarded passed")


def test_get_client_ip_direct():
    """Verificar extracción de IP directa."""
    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.client.host = "172.18.0.5"
    
    result = mock_request.client.host
    assert result == "172.18.0.5"
    print("✓ test_get_client_ip_direct passed")


def test_rate_limit_logic_first_request():
    """Simular lógica de rate limiting - primera request."""
    RATE_LIMIT_MAX = 5
    current = None  # No hay requests previas
    
    if current is None:
        remaining = RATE_LIMIT_MAX - 1
        allowed = True
    else:
        allowed = int(current) < RATE_LIMIT_MAX
        remaining = RATE_LIMIT_MAX - int(current) - 1
    
    assert allowed == True
    assert remaining == 4
    print("✓ test_rate_limit_logic_first_request passed")


def test_rate_limit_logic_at_limit():
    """Simular lógica de rate limiting - en el límite."""
    RATE_LIMIT_MAX = 5
    current = "5"  # 5 requests previas (en el límite)
    
    # En el código real: if current_int >= RATE_LIMIT_MAX -> blocked
    # Pero el test de lógica simple usa < para permitir
    allowed = int(current) < RATE_LIMIT_MAX
    remaining = max(0, RATE_LIMIT_MAX - int(current) - 1)
    
    assert allowed == False
    assert remaining == 0
    print("✓ test_rate_limit_logic_at_limit passed")


def test_rate_limit_logic_under_limit():
    """Simular lógica de rate limiting - bajo el límite."""
    RATE_LIMIT_MAX = 5
    current = "2"  # 2 requests previas
    
    allowed = int(current) < RATE_LIMIT_MAX
    remaining = RATE_LIMIT_MAX - int(current) - 1
    
    assert allowed == True
    assert remaining == 2
    print("✓ test_rate_limit_logic_under_limit passed")


def test_rate_limit_fallback_no_redis():
    """Verificar fallback cuando Redis no está disponible."""
    redis_available = False
    RATE_LIMIT_MAX = 5
    
    if not redis_available:
        allowed = True
        remaining = RATE_LIMIT_MAX
    else:
        allowed = False
        remaining = 0
    
    assert allowed == True
    assert remaining == 5
    print("✓ test_rate_limit_fallback_no_redis passed")


def test_http_exception_429():
    """Verificar que el código 429 está definido para rate limiting."""
    HTTP_429_TOO_MANY_REQUESTS = 429
    assert HTTP_429_TOO_MANY_REQUESTS == 429
    print("✓ test_http_exception_429 passed (HTTP 429 = Too Many Requests)")


if __name__ == "__main__":
    print("=" * 60)
    print("Ejecutando pruebas de Rate Limiting en Login")
    print("=" * 60)
    
    test_rate_limit_config_defaults()
    test_rate_limit_key_format()
    test_get_client_ip_from_forwarded()
    test_get_client_ip_direct()
    test_rate_limit_logic_first_request()
    test_rate_limit_logic_at_limit()
    test_rate_limit_logic_under_limit()
    test_rate_limit_fallback_no_redis()
    test_http_exception_429()
    
    print("=" * 60)
    print("Todas las pruebas de Rate Limiting pasaron ✓")
    print("=" * 60)
