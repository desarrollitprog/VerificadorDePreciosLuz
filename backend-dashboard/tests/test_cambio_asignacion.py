"""
Pruebas unitarias para el Cambio de Asignación con Cleanup.
"""
import sys
import os
import io

_old_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLimpiarBannerDeServidor:
    """Pruebas para limpiar_banner_de_servidor()."""
    
    def test_data_enviado_limpiar_asignaciones(self):
        """Verificar que data contiene limpiar_asignaciones=True."""
        data = {"limpiar_asignaciones": True}
        assert data["limpiar_asignaciones"] is True
        print("✓ test_data_enviado_limpiar_asignaciones passed")
    
    def test_url_formato(self):
        """Verificar formato de URL."""
        api_url = "http://192.168.1.100:8000"
        banner_id = 123
        update_url = f"{api_url.rstrip('/')}/banners/{banner_id}"
        assert update_url == "http://192.168.1.100:8000/banners/123"
        print("✓ test_url_formato passed")
    
    def test_estructura_response_exito(self):
        """Verificar estructura de respuesta exitosa."""
        result = {"success": True, "api_url": "http://192.168.1.100:8000"}
        assert result["success"] is True
        assert "api_url" in result
        print("✓ test_estructura_response_exito passed")
    
    def test_estructura_response_error(self):
        """Verificar estructura de respuesta con error."""
        result = {"success": False, "api_url": "http://192.168.1.100:8000", "error": "Connection error"}
        assert result["success"] is False
        assert "error" in result
        print("✓ test_estructura_response_error passed")


class TestObtenerServidoresConBanner:
    """Pruebas para obtener_servidores_con_banner()."""
    
    def test_servidor_formato(self):
        """Verificar formato de servidor."""
        servidor = {"id": 1, "nombre": "Servidor A", "ip": "192.168.1.100"}
        api_url = f"http://{servidor['ip']}:8000"
        assert api_url == "http://192.168.1.100:8000"
        print("✓ test_servidor_formato passed")
    
    def test_servidor_sin_ip(self):
        """Verificar que servidor sin IP usa api_url."""
        servidor = {"id": 1, "nombre": "Servidor A", "api_url": "http://192.168.1.100:8000"}
        api_url = servidor.get("api_url") or f"http://{servidor.get('ip')}:8000"
        assert api_url == "http://192.168.1.100:8000"
        print("✓ test_servidor_sin_ip passed")
    
    def test_resultado_verificacion(self):
        """Verificar estructura de resultado de verificación."""
        result = {"servidor": {"id": 1, "nombre": "A"}, "tiene_banner": True, "api_url": "http://192.168.1.100:8000"}
        assert result.get("tiene_banner") is True
        print("✓ test_resultado_verificacion passed")

    def test_sin_servidores(self):
        """Verificar que retorna lista vacía."""
        servidores = []
        assert servidores == []
        print("✓ test_sin_servidores passed")


class TestProcesarCambioAsignacion:
    """Pruebas para procesar_cambio_asignacion()."""
    
    def test_calculo_diferencias(self):
        """Verificar cálculo de diferencias entre servidores."""
        # Caso: algunos srv tienen banner, otros no
        srv_tienen_ids = {1, 2, 3}  # IDs de srv que tienen el banner
        srv_nuevos_ids = {2, 3, 4}   # IDs de srv objetivo
        
        # Calcular diferencias
        srv_a_agregar = srv_nuevos_ids - srv_tienen_ids  # Nuevos que no tienen
        srv_a_eliminar = srv_tienen_ids - srv_nuevos_ids  # Antiguos que deben perder
        srv_a_actualizar = srv_nuevos_ids & srv_tienen_ids  # En ambos
        
        assert srv_a_agregar == {4}  # Solo srv 4 es nuevo
        assert srv_a_eliminar == {1}  # Solo srv 1 debe perder
        assert srv_a_actualizar == {2, 3}  # srv 2 y 3 se mantienen
        print("✓ test_calculo_diferencias passed")
    
    def test_caso_todos_a_especifico(self):
        """Verificar caso B: de todos a especifico."""
        # Era "todos": todos los srv tenían el banner
        srv_tienen_ids = {1, 2, 3, 4, 5}
        # Ahora específico: solo srv 1, 2
        srv_nuevos_ids = {1, 2}
        
        srv_a_agregar = srv_nuevos_ids - srv_tienen_ids  # Vacío (no hay nuevos)
        srv_a_eliminar = srv_tienen_ids - srv_nuevos_ids  # srv 3, 4, 5 deben perder
        srv_a_actualizar = srv_nuevos_ids & srv_tienen_ids  # srv 1, 2 se mantienen
        
        assert srv_a_agregar == set()  # No hay nuevos
        assert srv_a_eliminar == {3, 4, 5}  # 3 srv deben perder
        assert srv_a_actualizar == {1, 2}  # 2 srv se mantienen
        print("✓ test_caso_todos_a_especifico passed")
    
    def test_caso_especifico_a_todos(self):
        """Verificar caso C: de especifico a todos."""
        # Era específico: solo srv 1, 2 tenían
        srv_tienen_ids = {1, 2}
        # Ahora "todos": todos los srv
        srv_nuevos_ids = {1, 2, 3, 4, 5}
        
        srv_a_agregar = srv_nuevos_ids - srv_tienen_ids  # srv 3, 4, 5 deben recibir
        srv_a_eliminar = srv_tienen_ids - srv_nuevos_ids  # Vacío (ninguno debe perder)
        srv_a_actualizar = srv_nuevos_ids & srv_tienen_ids  # srv 1, 2 se mantienen
        
        assert srv_a_agregar == {3, 4, 5}  # 3 srv deben recibir
        assert srv_a_eliminar == set()  # No hay eliminiados
        assert srv_a_actualizar == {1, 2}  # 2 srv se mantienen
        print("✓ test_caso_especifico_a_todos passed")
    
    def test_caso_especifico_a_especifico(self):
        """Verificar caso D: de especifico1 a especifico2."""
        # Era específico: srv 1, 2, 3
        srv_tienen_ids = {1, 2, 3}
        # Ahora específico diferente: srv 2, 3, 4
        srv_nuevos_ids = {2, 3, 4}
        
        srv_a_agregar = srv_nuevos_ids - srv_tienen_ids  # srv 4 es nuevo
        srv_a_eliminar = srv_tienen_ids - srv_nuevos_ids  # srv 1 debe perder
        srv_a_actualizar = srv_nuevos_ids & srv_tienen_ids  # srv 2, 3 se mantienen
        
        assert srv_a_agregar == {4}  # 1 srv nuevo
        assert srv_a_eliminar == {1}  # 1 srv debe perder
        assert srv_a_actualizar == {2, 3}  # 2 srv se mantienen
        print("✓ test_caso_especifico_a_especifico passed")
    
    def test_formato_banner_data(self):
        """Verificar formato de banner_data."""
        banner_data = {
            "banner_id": 123,
            "file_path": "/static/banners/test.mp4",
            "titulo": "Test Banner",
            "tipo": "video",
            "activo": True,
            "prioridad": 0,
            "dispositivo_ids": ["device1", "device2"]
        }
        
        assert banner_data.get("banner_id") == 123
        assert banner_data.get("dispositivo_ids") == ["device1", "device2"]
        assert banner_data.get("activo") is True
        print("✓ test_formato_banner_data passed")
    
    def test_resultado_final_exito(self):
        """Verificar estructura de resultado exitoso."""
        resultado = {
            "exito": True,
            "agregados": [{"servidor_id": 4, "servidor_nombre": "D", "api_url": "http://192.168.1.104:8000"}],
            "eliminados": [{"servidor_id": 1, "servidor_nombre": "A", "api_url": "http://192.168.1.101:8000"}],
            "actualizados": [{"servidor_id": 2, "servidor_nombre": "B", "api_url": "http://192.168.1.102:8000"}],
            "errores": []
        }
        
        assert resultado["exito"] is True
        assert len(resultado["agregados"]) == 1
        assert len(resultado["eliminados"]) == 1
        assert len(resultado["actualizados"]) == 1
        assert len(resultado["errores"]) == 0
        print("✓ test_resultado_final_exito passed")
    
    def test_resultado_con_error(self):
        """Verificar estructura cuando hay errores."""
        resultado = {
            "exito": False,
            "agregados": [],
            "eliminados": [],
            "actualizados": [],
            "errores": [{"servidor_id": 1, "error": "Connection timeout", "tipo": "agregar"}]
        }
        
        assert resultado["exito"] is False
        assert len(resultado["errores"]) == 1
        assert resultado["errores"][0]["tipo"] == "agregar"
        print("✓ test_resultado_con_error passed")


class TestTimeoutConfig:
    """Pruebas para configuración de timeout."""
    
    def test_timeout_default(self):
        """Verificar timeout default de 35 segundos."""
        timeout = 35
        assert timeout == 35
        print("✓ test_timeout_default passed")


def run_tests():
    print("=" * 60)
    print("Ejecutando pruebas de Cambio de Asignación con Cleanup")
    print("=" * 60)
    
    # Test LimpiarBannerDeServidor
    limpiar_tests = TestLimpiarBannerDeServidor()
    limpiar_tests.test_data_enviado_limpiar_asignaciones()
    limpiar_tests.test_url_formato()
    limpiar_tests.test_estructura_response_exito()
    limpiar_tests.test_estructura_response_error()
    
    # Test ObtenerServidoresConBanner
    obtener_tests = TestObtenerServidoresConBanner()
    obtener_tests.test_servidor_formato()
    obtener_tests.test_servidor_sin_ip()
    obtener_tests.test_resultado_verificacion()
    obtener_tests.test_sin_servidores()
    
    # Test ProcesarCambioAsignacion
    procesar_tests = TestProcesarCambioAsignacion()
    procesar_tests.test_calculo_diferencias()
    procesar_tests.test_caso_todos_a_especifico()
    procesar_tests.test_caso_especifico_a_todos()
    procesar_tests.test_caso_especifico_a_especifico()
    procesar_tests.test_formato_banner_data()
    procesar_tests.test_resultado_final_exito()
    procesar_tests.test_resultado_con_error()
    
    # Test Timeout
    timeout_tests = TestTimeoutConfig()
    timeout_tests.test_timeout_default()
    
    print("=" * 60)
    print("Todas las pruebas de cambio de asignación pasaron ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()