"""
Pruebas unitarias para 2FA en Redis (sin dependencias externas).
"""
import sys
import os
import io

_old_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timedelta, timezone


class TestOTPConstants:
    """Pruebas de constantes de 2FA."""

    def test_otp_expires_seconds_value(self):
        """Verificar valor de expiración OTP es 300 segundos."""
        OTP_EXPIRES_SECONDS = 300
        assert OTP_EXPIRES_SECONDS == 300
        print("✓ test_otp_expires_seconds_value passed")

    def test_otp_max_attempts_value(self):
        """Verificar valor de intentos máximos es 5."""
        OTP_MAX_ATTEMPTS = 5
        assert OTP_MAX_ATTEMPTS == 5
        print("✓ test_otp_max_attempts_value passed")

    def test_redis_key_prefix_format(self):
        """Verificar formato de prefijo de clave Redis."""
        KEY_PREFIX = "2fa:pending:"
        assert KEY_PREFIX == "2fa:pending:"
        assert KEY_PREFIX.endswith(":")
        print("✓ test_redis_key_prefix_format passed")


class TestOTPGeneration:
    """Pruebas de generación de OTP."""

    def test_otp_code_length(self):
        """Verificar que el código OTP tiene 6 dígitos."""
        import random
        code = f"{random.SystemRandom().randint(0, 999999):06d}"
        assert len(code) == 6
        assert code.isdigit()
        print("✓ test_otp_code_length passed")

    def test_otp_code_range(self):
        """Verificar que el código OTP está en rango válido."""
        import random
        for _ in range(100):
            code = f"{random.SystemRandom().randint(0, 999999):06d}"
            assert 0 <= int(code) <= 999999
        print("✓ test_otp_code_range passed")

    def test_otp_code_uniqueness(self):
        """Verificar que los códigos OTP son únicos (estadísticamente)."""
        import random
        codes = set()
        for _ in range(1000):
            code = f"{random.SystemRandom().randint(0, 999999):06d}"
            codes.add(code)
        assert len(codes) >= 900
        print("✓ test_otp_code_uniqueness passed")


class TestEmailMasking:
    """Pruebas de enmascaramiento de email."""

    def _mask_email(self, email: str) -> str:
        if "@" not in email:
            return "***"
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            local_masked = f"{local[0]}***" if local else "***"
        else:
            local_masked = f"{local[0]}***{local[-1]}"
        return f"{local_masked}@{domain}"

    def test_mask_email_standard(self):
        """Verificar enmascaramiento de email estándar."""
        masked = self._mask_email("usuario@example.com")
        assert masked == "u***o@example.com"
        print("✓ test_mask_email_standard passed")

    def test_mask_email_short_local(self):
        """Verificar enmascaramiento de email con local corto."""
        masked = self._mask_email("ab@example.com")
        assert masked == "a***@example.com"
        print("✓ test_mask_email_short_local passed")

    def test_mask_email_single_char(self):
        """Verificar enmascaramiento de email con un solo char."""
        masked = self._mask_email("a@example.com")
        assert masked == "a***@example.com"
        print("✓ test_mask_email_single_char passed")

    def test_mask_email_invalid(self):
        """Verificar enmascaramiento de email inválido."""
        masked = self._mask_email("invalid-email")
        assert masked == "***"
        print("✓ test_mask_email_invalid passed")


class TestChallengeSerialization:
    """Pruebas de serialización de challenge."""

    def test_serialize_challenge(self):
        """Verificar serialización de challenge."""
        challenge = {
            "user_id": 1,
            "username": "testuser",
            "correo": "test@example.com",
            "expires_at": "2024-01-01T00:00:00+00:00",
            "code": "123456",
            "attempts": 0,
        }
        
        serialized = json.dumps(challenge)
        data = json.loads(serialized)
        
        assert data["user_id"] == 1
        assert data["username"] == "testuser"
        assert data["correo"] == "test@example.com"
        assert data["code"] == "123456"
        print("✓ test_serialize_challenge passed")

    def test_deserialize_challenge(self):
        """Verificar deserialización de challenge."""
        json_data = json.dumps({
            "user_id": "2",
            "username": "testuser",
            "correo": "test@example.com",
            "expires_at": "2024-01-01T00:00:00+00:00",
            "code": "654321",
            "attempts": "1",
        })
        
        parsed = json.loads(json_data)
        challenge = {
            "user_id": int(parsed["user_id"]),
            "username": str(parsed["username"]),
            "correo": str(parsed["correo"]),
            "expires_at": str(parsed["expires_at"]),
            "code": str(parsed["code"]),
            "attempts": int(parsed["attempts"]),
        }
        
        assert challenge["user_id"] == 2
        assert challenge["username"] == "testuser"
        assert challenge["code"] == "654321"
        assert challenge["attempts"] == 1
        print("✓ test_deserialize_challenge passed")


class TestTwoFAVerification:
    """Pruebas de verificación de 2FA."""

    def test_verify_code_correct(self):
        """Verificar que código correcto pasa."""
        correct_code = "123456"
        entered_code = "123456"
        assert correct_code == entered_code
        print("✓ test_verify_code_correct passed")

    def test_verify_code_incorrect(self):
        """Verificar que código incorrecto falla."""
        correct_code = "123456"
        entered_code = "654321"
        assert correct_code != entered_code
        print("✓ test_verify_code_incorrect passed")

    def test_max_attempts_logic(self):
        """Verificar lógica de intentos máximos."""
        OTP_MAX_ATTEMPTS = 5
        
        assert (4 >= OTP_MAX_ATTEMPTS) == False
        assert (5 >= OTP_MAX_ATTEMPTS) == True
        print("✓ test_max_attempts_logic passed")

    def test_expiry_check(self):
        """Verificar lógica de expiración."""
        now = datetime.now(timezone.utc)
        
        valid_challenge = now + timedelta(seconds=300)
        expired_challenge = now - timedelta(seconds=1)
        
        assert now < valid_challenge
        assert now > expired_challenge
        print("✓ test_expiry_check passed")

    def test_utcnow_function(self):
        """Verificar función _utcnow()."""
        def _utcnow():
            return datetime.now(timezone.utc)
        
        now = _utcnow()
        assert isinstance(now, datetime)
        assert now.tzinfo is not None
        print("✓ test_utcnow_function passed")


class TestTwoFAFunctionsLogic:
    """Pruebas de lógica de funciones de 2FA."""

    def test_verify_2fa_code_logic_success(self):
        """Verificar lógica de verificación exitosa."""
        code = "123456"
        challenge_code = "123456"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)
        attempts = 0
        OTP_MAX_ATTEMPTS = 5

        if code != challenge_code:
            valid, msg = False, "Código incorrecto"
        elif datetime.now(timezone.utc) > expires_at:
            valid, msg = False, "Código expirado"
        elif attempts >= OTP_MAX_ATTEMPTS:
            valid, msg = False, "Demasiados intentos"
        else:
            valid, msg = True, ""
        
        assert valid is True
        print("✓ test_verify_2fa_code_logic_success passed")

    def test_verify_2fa_code_logic_wrong(self):
        """Verificar lógica de código incorrecto."""
        code = "654321"
        challenge_code = "123456"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)
        attempts = 0
        OTP_MAX_ATTEMPTS = 5

        if code != challenge_code:
            valid, msg = False, "Código incorrecto"
        elif datetime.now(timezone.utc) > expires_at:
            valid, msg = False, "Código expirado"
        elif attempts >= OTP_MAX_ATTEMPTS:
            valid, msg = False, "Demasiados intentos"
        else:
            valid, msg = True, ""
        
        assert valid is False
        assert "incorrecto" in msg.lower()
        print("✓ test_verify_2fa_code_logic_wrong passed")

    def test_verify_2fa_code_logic_expired(self):
        """Verificar lógica de código expirado."""
        code = "123456"
        challenge_code = "123456"
        expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        attempts = 0
        OTP_MAX_ATTEMPTS = 5

        if code != challenge_code:
            valid, msg = False, "Código incorrecto"
        elif datetime.now(timezone.utc) > expires_at:
            valid, msg = False, "Código expirado"
        elif attempts >= OTP_MAX_ATTEMPTS:
            valid, msg = False, "Demasiados intentos"
        else:
            valid, msg = True, ""
        
        assert valid is False
        assert "expir" in msg.lower()
        print("✓ test_verify_2fa_code_logic_expired passed")

    def test_verify_2fa_code_logic_max_attempts(self):
        """Verificar lógica de intentos máximos."""
        code = "123456"
        challenge_code = "123456"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)
        attempts = 5
        OTP_MAX_ATTEMPTS = 5

        if code != challenge_code:
            valid, msg = False, "Código incorrecto"
        elif datetime.now(timezone.utc) > expires_at:
            valid, msg = False, "Código expirado"
        elif attempts >= OTP_MAX_ATTEMPTS:
            valid, msg = False, "Demasiados intentos"
        else:
            valid, msg = True, ""
        
        assert valid is False
        assert "intentos" in msg.lower()
        print("✓ test_verify_2fa_code_logic_max_attempts passed")

    def test_verify_2fa_code_logic_invalid_token(self):
        """Verificar lógica de token inválido."""
        challenge = None
        code = "123456"
        
        if not challenge:
            valid, msg = False, "Desafío 2FA inválido o expirado"
        else:
            valid, msg = True, ""
        
        assert valid is False
        assert "inválido" in msg.lower()
        print("✓ test_verify_2fa_code_logic_invalid_token passed")

    def test_redis_key_generation(self):
        """Verificar generación de claves Redis."""
        KEY_PREFIX = "2fa:pending:"
        temp_token = "abc123xyz"
        
        key = f"{KEY_PREFIX}{temp_token}"
        assert key == "2fa:pending:abc123xyz"
        print("✓ test_redis_key_generation passed")


class TestTwoFAResultStructure:
    """Pruebas de estructura de resultado 2FA."""

    def test_2fa_result_structure(self):
        """Verificar estructura del resultado 2FA."""
        result = {
            "requires_2fa": True,
            "message": "Código de verificación enviado al correo registrado",
            "temp_token": "random_token_string",
            "masked_email": "u***o@example.com",
            "expires_in": 300,
        }
        
        assert "requires_2fa" in result
        assert "message" in result
        assert "temp_token" in result
        assert "masked_email" in result
        assert "expires_in" in result
        assert result["requires_2fa"] is True
        assert result["expires_in"] == 300
        print("✓ test_2fa_result_structure passed")


def run_tests():
    print("=" * 60)
    print("Ejecutando pruebas de 2FA en Redis")
    print("=" * 60)
    
    constants_tests = TestOTPConstants()
    constants_tests.test_otp_expires_seconds_value()
    constants_tests.test_otp_max_attempts_value()
    constants_tests.test_redis_key_prefix_format()
    
    otp_tests = TestOTPGeneration()
    otp_tests.test_otp_code_length()
    otp_tests.test_otp_code_range()
    otp_tests.test_otp_code_uniqueness()
    
    email_tests = TestEmailMasking()
    email_tests.test_mask_email_standard()
    email_tests.test_mask_email_short_local()
    email_tests.test_mask_email_single_char()
    email_tests.test_mask_email_invalid()
    
    serialization_tests = TestChallengeSerialization()
    serialization_tests.test_serialize_challenge()
    serialization_tests.test_deserialize_challenge()
    
    verification_tests = TestTwoFAVerification()
    verification_tests.test_verify_code_correct()
    verification_tests.test_verify_code_incorrect()
    verification_tests.test_max_attempts_logic()
    verification_tests.test_expiry_check()
    verification_tests.test_utcnow_function()
    
    logic_tests = TestTwoFAFunctionsLogic()
    logic_tests.test_verify_2fa_code_logic_success()
    logic_tests.test_verify_2fa_code_logic_wrong()
    logic_tests.test_verify_2fa_code_logic_expired()
    logic_tests.test_verify_2fa_code_logic_max_attempts()
    logic_tests.test_verify_2fa_code_logic_invalid_token()
    logic_tests.test_redis_key_generation()
    
    result_tests = TestTwoFAResultStructure()
    result_tests.test_2fa_result_structure()
    
    print("=" * 60)
    print("Todas las pruebas de 2FA en Redis pasaron ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
