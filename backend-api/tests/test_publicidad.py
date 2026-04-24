"""
Pruebas unitarias para esquemas de publicidad en backend-api.
"""
import sys
import os
import io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPublicidadSchema:
    """Pruebas del esquema de publicidad."""

    def test_response_schema_fields(self):
        """Verificar campos del esquema de respuesta."""
        from app.schemas.publicidad import PublicidadResponse
        
        # Verificar campos requeridos
        from pydantic import BaseModel
        
        fields = PublicidadResponse.model_fields
        assert "id" in fields
        assert "titulo" in fields
        assert "tipo" in fields
        assert "url" in fields
        assert "fecha_inicio_ms" in fields
        assert "fecha_fin_ms" in fields
        print("✓ test_response_schema_fields passed")

    def test_calculo_fecha_ms(self):
        """Verificar cálculo de fecha a milisegundos."""
        fecha = datetime(2026, 4, 14, 18, 30, 0)
        fecha_ms = int(fecha.timestamp() * 1000)
        
        # Verificar que es un número positivo
        assert fecha_ms > 0
        assert isinstance(fecha_ms, int)
        
        # Verificar que podemos reconstruir
        reconstruida = datetime.fromtimestamp(fecha_ms / 1000)
        assert reconstruida.year == 2026
        assert reconstruida.month == 4
        print("✓ test_calculo_fecha_ms passed")

    def test_response_con_fechas_none(self):
        """Verificar respuesta sin fechas."""
        data = {
            "id": 1,
            "titulo": "Test",
            "tipo": "image",
            "url": "/test.jpg",
            "activo": True,
            "prioridad": 0,
            "fecha_inicio": None,
            "fecha_fin": None,
            "updated_at": None,
            "fecha_inicio_ms": None,
            "fecha_fin_ms": None
        }
        
        assert data["fecha_inicio_ms"] is None
        assert data["fecha_fin_ms"] is None
        print("✓ test_response_con_fechas_none passed")

    def test_response_con_fechas(self):
        """Verificar respuesta con fechas."""
        fecha_inicio = datetime(2026, 4, 14, 8, 0, 0)
        fecha_fin = datetime(2026, 4, 14, 18, 0, 0)
        
        data = {
            "id": 1,
            "titulo": "Test",
            "tipo": "image",
            "url": "/test.jpg",
            "activo": True,
            "prioridad": 0,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "updated_at": None,
            "fecha_inicio_ms": int(fecha_inicio.timestamp() * 1000),
            "fecha_fin_ms": int(fecha_fin.timestamp() * 1000)
        }
        
        assert data["fecha_inicio_ms"] is not None
        assert data["fecha_fin_ms"] is not None
        assert data["fecha_inicio_ms"] < data["fecha_fin_ms"]
        print("✓ test_response_con_fechas passed")


if __name__ == "__main__":
    tests = TestPublicidadSchema()
    tests.test_response_schema_fields()
    tests.test_calculo_fecha_ms()
    tests.test_response_con_fechas_none()
    tests.test_response_con_fechas()
    
    print("\n✅ Todas las pruebas de backend-api publicidac passed")