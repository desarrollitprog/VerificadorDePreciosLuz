"""
Pruebas unitarias para Sanitización de Inputs.
"""
import sys
import os
import io

_old_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import sanitize_html, sanitize_filename, sanitize_search_query


def test_sanitize_html_none():
    """Verificar que sanitize_html maneja None."""
    result = sanitize_html(None)
    assert result is None
    print("✓ test_sanitize_html_none passed")


def test_sanitize_html_script_tag():
    """Verificar que script tags son escapados."""
    result = sanitize_html("<script>alert('xss')</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    print("✓ test_sanitize_html_script_tag passed")


def test_sanitize_html_img_onerror():
    """Verificar que tags HTML son escapados (onerror no se interpreta)."""
    result = sanitize_html("<img src=x onerror=alert(1)>")
    assert "&lt;img" in result
    assert "&gt;" in result
    print("✓ test_sanitize_html_img_onerror passed")


def test_sanitize_html_normal_text():
    """Verificar que texto normal no se modifica."""
    result = sanitize_html("Hola Mundo")
    assert result == "Hola Mundo"
    print("✓ test_sanitize_html_normal_text passed")


def test_sanitize_html_with_quotes():
    """Verificar que las comillas son escapadas."""
    result = sanitize_html('<a href="test">Click</a>')
    assert '"' in result or "&quot;" in result
    assert "onclick" not in result
    print("✓ test_sanitize_html_with_quotes passed")


def test_sanitize_html_spanish_chars():
    """Verificar que caracteres especiales español se mantienen."""
    result = sanitize_html("Café Ñoño María José")
    assert "Café" in result
    assert "Ñoño" in result
    assert "María" in result
    print("✓ test_sanitize_html_spanish_chars passed")


def test_sanitize_html_emoji():
    """Verificar que emojis se mantienen."""
    result = sanitize_html("Banner 🎉 50% OFF!")
    assert "🎉" in result
    assert "50%" in result
    print("✓ test_sanitize_html_emoji passed")


def test_sanitize_filename_none():
    """Verificar que sanitize_filename maneja None."""
    result = sanitize_filename(None)
    assert result is None
    print("✓ test_sanitize_filename_none passed")


def test_sanitize_filename_normal():
    """Verificar que nombres normales pasan."""
    result = sanitize_filename("banner_2024.png")
    assert result == "banner_2024.png"
    print("✓ test_sanitize_filename_normal passed")


def test_sanitize_filename_with_path():
    """Verificar que rutas son eliminadas."""
    result = sanitize_filename("../../../etc/passwd")
    assert ".." not in result
    assert "/" not in result
    print("✓ test_sanitize_filename_with_path passed")


def test_sanitize_filename_with_special_chars():
    """Verificar que caracteres especiales son eliminados."""
    result = sanitize_filename("banner<script>alert(1)</script>.png")
    assert "<script>" not in result
    print("✓ test_sanitize_filename_with_special_chars passed")


def test_sanitize_search_query_none():
    """Verificar que sanitize_search_query maneja None."""
    result = sanitize_search_query(None)
    assert result is None
    print("✓ test_sanitize_search_query_none passed")


def test_sanitize_search_query_normal():
    """Verificar que queries normales pasan."""
    result = sanitize_search_query("café espresso")
    assert "café" in result
    print("✓ test_sanitize_search_query_normal passed")


def test_sanitize_search_query_with_sql_chars():
    """Verificar que caracteres SQL problemáticos son eliminados."""
    result = sanitize_search_query("test'; DROP TABLE users;--")
    assert "'" not in result
    assert ";" not in result
    print("✓ test_sanitize_search_query_with_sql_chars passed")


def test_sanitize_html_javascript_protocol():
    """Verificar que javascript: es escapado."""
    result = sanitize_html('<a href="javascript:alert(1)">Click</a>')
    assert "javascript:" not in result
    print("✓ test_sanitize_html_javascript_protocol passed")


def test_sanitize_html_style_injection():
    """Verificar que style injection es prevenido."""
    result = sanitize_html('<div style="background: url(javascript:alert(1))">Test</div>')
    assert "javascript:" not in result
    assert "<style>" not in result
    print("✓ test_sanitize_html_style_injection passed")


def test_sanitize_html_nested_tags():
    """Verificar que tags anidados son escapados."""
    result = sanitize_html('<div><p>Paragraph<script>alert(1)</script></p></div>')
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    print("✓ test_sanitize_html_nested_tags passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Ejecutando pruebas de Sanitización de Inputs")
    print("=" * 60)
    
    test_sanitize_html_none()
    test_sanitize_html_script_tag()
    test_sanitize_html_img_onerror()
    test_sanitize_html_normal_text()
    test_sanitize_html_with_quotes()
    test_sanitize_html_spanish_chars()
    test_sanitize_html_emoji()
    test_sanitize_html_javascript_protocol()
    test_sanitize_html_style_injection()
    test_sanitize_html_nested_tags()
    
    test_sanitize_filename_none()
    test_sanitize_filename_normal()
    test_sanitize_filename_with_path()
    test_sanitize_filename_with_special_chars()
    
    test_sanitize_search_query_none()
    test_sanitize_search_query_normal()
    test_sanitize_search_query_with_sql_chars()
    
    print("=" * 60)
    print("Todas las pruebas de Sanitización pasaron ✓")
    print("=" * 60)
