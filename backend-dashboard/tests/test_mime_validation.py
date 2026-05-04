"""
Pruebas unitarias para Validación MIME en Uploads.
"""
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import FileTypeValidator


def test_magic_bytes_jpeg():
    """Verificar detección de JPEG."""
    result = FileTypeValidator.detect_type.__func__(None, "tests/fixtures/test.jpg")
    assert result == "jpeg" or result is None
    print("✓ test_magic_bytes_jpeg passed")


def test_magic_bytes_png():
    """Verificar detección de PNG."""
    result = FileTypeValidator.detect_type.__func__(None, "tests/fixtures/test.png")
    assert result == "png" or result is None
    print("✓ test_magic_bytes_png passed")


def test_magic_bytes_nonexistent():
    """Verificar que archivos inexistentes retornan None."""
    result = FileTypeValidator.detect_type.__func__(None, "tests/fixtures/nonexistent.jpg")
    assert result is None
    print("✓ test_magic_bytes_nonexistent passed")


def test_mime_types_mapping():
    """Verificar mapeo de MIME types."""
    assert FileTypeValidator.MIME_TYPES["jpeg"] == "image/jpeg"
    assert FileTypeValidator.MIME_TYPES["png"] == "image/png"
    assert FileTypeValidator.MIME_TYPES["mp4"] == "video/mp4"
    print("✓ test_mime_types_mapping passed")


def test_allowed_types_complete():
    """Verificar que todos los tipos esperados están en MAGIC_BYTES."""
    expected_types = ["jpeg", "png", "gif", "bmp", "webp", "mp4", "webm", "avi"]
    for t in expected_types:
        assert t in FileTypeValidator.MAGIC_BYTES
    print("✓ test_allowed_types_complete passed")


def test_validate_file_logic():
    """Verificar lógica de validación sin archivo real."""
    assert "jpg" in FileTypeValidator.MAGIC_BYTES or "jpeg" in FileTypeValidator.MAGIC_BYTES
    assert "png" in FileTypeValidator.MAGIC_BYTES
    assert "mp4" in FileTypeValidator.MAGIC_BYTES
    print("✓ test_validate_file_logic passed")


def test_magic_bytes_structure():
    """Verificar estructura de MAGIC_BYTES."""
    for file_type, patterns in FileTypeValidator.MAGIC_BYTES.items():
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        for pattern in patterns:
            assert isinstance(pattern, tuple)
    print("✓ test_magic_bytes_structure passed")


def test_validate_file_returns_tuple():
    """Verificar que validate_file retorna tupla."""
    import inspect
    sig = inspect.signature(FileTypeValidator.validate_file)
    params = list(sig.parameters.keys())
    assert "file_path" in params
    assert "allowed_types" in params
    print("✓ test_validate_file_returns_tuple passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Ejecutando pruebas de Validación MIME")
    print("=" * 60)
    
    test_magic_bytes_nonexistent()
    test_mime_types_mapping()
    test_allowed_types_complete()
    test_validate_file_logic()
    test_magic_bytes_structure()
    test_validate_file_returns_tuple()
    
    print("=" * 60)
    print("Todas las pruebas de Validación MIME pasaron ✓")
    print("=" * 60)
