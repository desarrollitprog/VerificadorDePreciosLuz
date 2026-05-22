"""
Pruebas unitarias para el parser de IDs (FASE 7 - Fix Caso D).
"""
import sys
import os
import json
import io

_old_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_ids(ids_str):
    """Parser robusto - acepta JSON array ["1","2"], string "1,2,3", o entero 1."""
    if not ids_str:
        return []
    ids_str = str(ids_str).strip()
    if not ids_str:
        return []
    try:
        parsed = json.loads(ids_str)
        # Si es un entero solo, envolver en array
        if isinstance(parsed, int):
            return [str(parsed)]
        # Si es un array, convertir todos a string
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        return []
    except (json.JSONDecodeError, TypeError):
        return [x.strip() for x in ids_str.split(",") if x.strip()]


class TestParserIds:
    """Pruebas para parse_ids()."""
    
    def test_json_array_string(self):
        """Verificar parsing de array JSON como string."""
        result = parse_ids('["1", "2", "3"]')
        assert result == ["1", "2", "3"], f"Expected ['1', '2', '3'], got {result}"
        print("✓ test_json_array_string passed")
    
    def test_json_array_int(self):
        """Verificar parsing de array JSON con enteros."""
        result = parse_ids('[1, 2, 3]')
        assert result == ["1", "2", "3"], f"Expected ['1', '2', '3'], got {result}"
        print("✓ test_json_array_int passed")
    
    def test_comma_separated(self):
        """Verificar parsing de string separado por comas."""
        result = parse_ids("1,2,3")
        assert result == ["1", "2", "3"], f"Expected ['1', '2', '3'], got {result}"
        print("✓ test_comma_separated passed")
    
    def test_comma_separated_with_spaces(self):
        """Verificar parsing con espacios."""
        result = parse_ids("1, 2, 3")
        assert result == ["1", "2", "3"], f"Expected ['1', '2', '3'], got {result}"
        print("✓ test_comma_separated_with_spaces passed")
    
    def test_empty_string(self):
        """Verificar parsing de string vacío."""
        result = parse_ids("")
        assert result == [], f"Expected [], got {result}"
        print("✓ test_empty_string passed")
    
    def test_none_value(self):
        """Verificar parsing de None."""
        result = parse_ids(None)
        assert result == [], f"Expected [], got {result}"
        print("✓ test_none_value passed")
    
    def test_single_id(self):
        """Verificar parsing de un solo ID."""
        result = parse_ids("1")
        assert result == ["1"], f"Expected ['1'], got {result}"
        print("✓ test_single_id passed")
    
    def test_mixed_format(self):
        """Verificar formato mixto (string con comas y espacios)."""
        result = parse_ids("1, 2, 3, 4")
        assert result == ["1", "2", "3", "4"], f"Expected ['1', '2', '3', '4'], got {result}"
        print("✓ test_mixed_format passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Ejecutando pruebas de parser de IDs (FASE 7)")
    print("=" * 60)
    
    test = TestParserIds()
    
    # Ejecutar todos los tests
    test.test_json_array_string()
    test.test_json_array_int()
    test.test_comma_separated()
    test.test_comma_separated_with_spaces()
    test.test_empty_string()
    test.test_none_value()
    test.test_single_id()
    test.test_mixed_format()
    
    print("=" * 60)
    print("¡Todas las pruebas pasaron!")
    print("=" * 60)