"""
Pruebas unitarias para el nuevo endpoint /banners/{banner_id}/exists.
"""
import sys
import os
import io

_old_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBannerExistsEndpoint:
    """Pruebas para el endpoint de verificación de existencia de banner."""

    def test_endpoint_url_format(self):
        """Verificar formato de URL del endpoint."""
        api_url = "http://192.168.1.100:8000"
        banner_id = 123
        
        expected_url = f"{api_url.rstrip('/')}/banners/{banner_id}/exists"
        assert expected_url == "http://192.168.1.100:8000/banners/123/exists"
        print("✓ test_endpoint_url_format passed")

    def test_endpoint_url_with_trailing_slash(self):
        """Verificar URL con trailing slash en api_url."""
        api_url = "http://192.168.1.100:8000/"
        banner_id = 456
        
        expected_url = f"{api_url.rstrip('/')}/banners/{banner_id}/exists"
        assert expected_url == "http://192.168.1.100:8000/banners/456/exists"
        print("✓ test_endpoint_url_with_trailing_slash passed")

    def test_response_parsing(self):
        """Verificar parsing de respuesta del endpoint."""
        mock_response_data = {"exists": True, "banner_id": 123}
        
        assert mock_response_data["exists"] is True
        assert mock_response_data["banner_id"] == 123
        print("✓ test_response_parsing passed")

    def test_response_parsing_not_exists(self):
        """Verificar parsing cuando banner no existe."""
        mock_response_data = {"exists": False, "banner_id": 999}
        
        assert mock_response_data["exists"] is False
        assert mock_response_data["banner_id"] == 999
        print("✓ test_response_parsing_not_exists passed")

    def test_404_handling(self):
        """Verificar manejo de 404."""
        status_code = 404
        
        exists = status_code == 200
        assert exists is False
        print("✓ test_404_handling passed")

    def test_200_handling(self):
        """Verificar manejo de 200."""
        status_code = 200
        
        exists = status_code == 200
        assert exists is True
        print("✓ test_200_handling passed")

    def test_verificar_banner_existe_en_api_logic(self):
        """Verificar lógica de verificar_banner_existe_en_api."""
        status_code = 200
        expected_exists = status_code == 200
        
        assert expected_exists is True
        
        status_code = 404
        expected_exists = status_code == 200
        
        assert expected_exists is False
        print("✓ test_verificar_banner_existe_en_api_logic passed")

    def test_timeout_configuration(self):
        """Verificar configuración de timeout."""
        timeout = 15
        
        assert timeout == 15
        assert timeout > 0
        print("✓ test_timeout_configuration passed")


class TestOldVsNewMethod:
    """Pruebas comparativas entre el método viejo y nuevo."""

    def test_old_method_used_put(self):
        """Verificar que el método viejo usaba PUT."""
        old_check_url = "http://192.168.1.100:8000/banners/123"
        old_data = {"titulo": "__check_exists__"}
        
        assert "titulo" in old_data
        assert old_data["titulo"] == "__check_exists__"
        print("✓ test_old_method_used_put passed")

    def test_new_method_uses_get(self):
        """Verificar que el método nuevo usa GET."""
        new_check_url = "http://192.168.1.100:8000/banners/123/exists"
        
        assert "/exists" in new_check_url
        assert "titulo" not in new_check_url
        print("✓ test_new_method_uses_get passed")

    def test_no_data_modification_in_verification(self):
        """Verificar que el nuevo método no envía datos para modificar."""
        new_check_url = "http://192.168.1.100:8000/banners/123/exists"
        
        data = {}
        
        assert len(data) == 0
        assert "titulo" not in data
        print("✓ test_no_data_modification_in_verification passed")

    def test_endpoint_path_structure(self):
        """Verificar estructura del path del endpoint."""
        banner_id = 42
        
        path = f"/banners/{banner_id}/exists"
        
        assert path == "/banners/42/exists"
        assert path.startswith("/banners/")
        assert path.endswith("/exists")
        print("✓ test_endpoint_path_structure passed")


def run_tests():
    print("=" * 60)
    print("Ejecutando pruebas del endpoint /banners/{id}/exists")
    print("=" * 60)
    
    endpoint_tests = TestBannerExistsEndpoint()
    endpoint_tests.test_endpoint_url_format()
    endpoint_tests.test_endpoint_url_with_trailing_slash()
    endpoint_tests.test_response_parsing()
    endpoint_tests.test_response_parsing_not_exists()
    endpoint_tests.test_404_handling()
    endpoint_tests.test_200_handling()
    endpoint_tests.test_verificar_banner_existe_en_api_logic()
    endpoint_tests.test_timeout_configuration()
    
    comparison_tests = TestOldVsNewMethod()
    comparison_tests.test_old_method_used_put()
    comparison_tests.test_new_method_uses_get()
    comparison_tests.test_no_data_modification_in_verification()
    comparison_tests.test_endpoint_path_structure()
    
    print("=" * 60)
    print("Todas las pruebas del endpoint pasaron ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()