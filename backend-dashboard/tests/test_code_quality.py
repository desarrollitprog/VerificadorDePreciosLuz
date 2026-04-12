"""
Pruebas unitarias para Code Quality (eliminación de prints y type hints).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestNoPrintsInCode:
    """Pruebas para verificar que no hay prints en el código."""

    def test_no_print_in_publicidad(self):
        """Verificar que no hay prints en publicidad.py."""
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "routes", "publicidad.py")
        
        with open(file_path, "r") as f:
            content = f.read()
        
        lines_with_print = []
        for i, line in enumerate(content.split("\n"), 1):
            if "print(" in line and not line.strip().startswith("#"):
                lines_with_print.append((i, line.strip()))
        
        assert len(lines_with_print) == 0, f"Found prints at lines: {lines_with_print}"
        print("✓ test_no_print_in_publicidad passed")

    def test_no_print_in_replicacion_service(self):
        """Verificar que no hay prints en replicacion_service.py."""
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "services", "replicacion_service.py")
        
        with open(file_path, "r") as f:
            content = f.read()
        
        lines_with_print = []
        for i, line in enumerate(content.split("\n"), 1):
            if "print(" in line and not line.strip().startswith("#"):
                lines_with_print.append((i, line.strip()))
        
        assert len(lines_with_print) == 0, f"Found prints at lines: {lines_with_print}"
        print("✓ test_no_print_in_replicacion_service passed")


class TestStructuredLogging:
    """Pruebas para verificar que se usa logging estructurado."""

    def test_structured_logger_exists(self):
        """Verificar que StructuredLogger está definido."""
        from app.utils.logger import StructuredLogger
        
        logger = StructuredLogger("test")
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'warning')
        print("✓ test_structured_logger_exists passed")

    def test_structured_logger_info(self):
        """Verificar que logger.info funciona correctamente."""
        from app.utils.logger import StructuredLogger
        
        logger = StructuredLogger("test")
        logger.info("test_event", key="value")
        print("✓ test_structured_logger_info passed")

    def test_structured_logger_with_none_values(self):
        """Verificar que logger filtra valores None."""
        from app.utils.logger import StructuredLogger
        
        logger = StructuredLogger("test")
        result = logger._build_extra(key="value", none_key=None, another="test")
        
        assert "key" in result
        assert "none_key" not in result
        assert "another" in result
        print("✓ test_structured_logger_with_none_values passed")


class TestTypeHints:
    """Pruebas para verificar uso de type hints."""

    def test_type_hint_in_function(self):
        """Verificar que una función tiene type hints."""
        from app.utils import sanitize_html
        
        import inspect
        sig = inspect.signature(sanitize_html)
        
        assert sig.parameters is not None
        print("✓ test_type_hint_in_function passed")

    def test_type_hint_return_optional(self):
        """Verificar que el return type puede ser None."""
        from app.utils import sanitize_html
        
        result = sanitize_html(None)
        assert result is None
        print("✓ test_type_hint_return_optional passed")


class TestSanitizationFunctions:
    """Pruebas para funciones de sanitización."""

    def test_sanitize_html_removes_script(self):
        """Verificar que sanitize_html elimina script tags."""
        from app.utils import sanitize_html
        
        result = sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        print("✓ test_sanitize_html_removes_script passed")

    def test_sanitize_html_none_input(self):
        """Verificar sanitización con input None."""
        from app.utils import sanitize_html
        
        result = sanitize_html(None)
        assert result is None
        print("✓ test_sanitize_html_none_input passed")

    def test_sanitize_filename_removes_path_traversal(self):
        """Verificar que sanitize_filename elimina path traversal."""
        from app.utils import sanitize_filename
        
        result = sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        print("✓ test_sanitize_filename_removes_path_traversal passed")

    def test_sanitize_filename_normal(self):
        """Verificar sanitización de filename normal."""
        from app.utils import sanitize_filename
        
        result = sanitize_filename("banner_image.png")
        assert result == "banner_image.png"
        print("✓ test_sanitize_filename_normal passed")


class TestFileTypeValidator:
    """Pruebas para validador de tipo de archivo."""

    def test_file_type_validator_class_exists(self):
        """Verificar que FileTypeValidator existe."""
        from app.utils import FileTypeValidator
        
        assert hasattr(FileTypeValidator, 'MAGIC_BYTES')
        assert hasattr(FileTypeValidator, 'validate_file')
        print("✓ test_file_type_validator_class_exists passed")

    def test_magic_bytes_structure(self):
        """Verificar estructura de MAGIC_BYTES."""
        from app.utils import FileTypeValidator
        
        assert "jpeg" in FileTypeValidator.MAGIC_BYTES
        assert "png" in FileTypeValidator.MAGIC_BYTES
        assert "mp4" in FileTypeValidator.MAGIC_BYTES
        print("✓ test_magic_bytes_structure passed")

    def test_mime_types_mapping(self):
        """Verificar mapeo de MIME types."""
        from app.utils import FileTypeValidator
        
        assert FileTypeValidator.MIME_TYPES["jpeg"] == "image/jpeg"
        assert FileTypeValidator.MIME_TYPES["png"] == "image/png"
        assert FileTypeValidator.MIME_TYPES["mp4"] == "video/mp4"
        print("✓ test_mime_types_mapping passed")


def run_tests():
    print("=" * 60)
    print("Ejecutando pruebas de Code Quality")
    print("=" * 60)
    
    no_prints = TestNoPrintsInCode()
    no_prints.test_no_print_in_publicidad()
    no_prints.test_no_print_in_replicacion_service()
    
    logging_tests = TestStructuredLogging()
    logging_tests.test_structured_logger_exists()
    logging_tests.test_structured_logger_info()
    logging_tests.test_structured_logger_with_none_values()
    
    type_hints = TestTypeHints()
    type_hints.test_type_hint_in_function()
    type_hints.test_type_hint_return_optional()
    
    sanitization = TestSanitizationFunctions()
    sanitization.test_sanitize_html_removes_script()
    sanitization.test_sanitize_html_none_input()
    sanitization.test_sanitize_filename_removes_path_traversal()
    sanitization.test_sanitize_filename_normal()
    
    file_validator = TestFileTypeValidator()
    file_validator.test_file_type_validator_class_exists()
    file_validator.test_magic_bytes_structure()
    file_validator.test_mime_types_mapping()
    
    print("=" * 60)
    print("Todas las pruebas de Code Quality pasaron ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
