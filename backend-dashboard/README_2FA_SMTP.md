# Configuración SMTP y prueba rápida de OTP (2FA)

## 1) Configurar variables de entorno

Edita `backend-dashboard/.env.dashboard` y completa:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_USE_TLS`

Puedes usar `backend-dashboard/.env.dashboard.example` como plantilla base.

## 2) Reiniciar backend-dashboard

Desde la raíz del proyecto:

```powershell
docker compose up -d --build dashboard-backend
```

## 3) Probar inicio de login (genera y envía OTP)

```powershell
curl -Method POST "http://localhost:8001/auth/login" -ContentType "application/json" -Body '{"username":"TU_USUARIO","correo":"tu_correo@dominio.com","contrasena":"TuPassword123*"}'
```

Respuesta esperada (sin token aún):

- `requires_2fa: true`
- `temp_token`
- `masked_email`
- `expires_in`

## 4) Verificar OTP

Reemplaza `TEMP_TOKEN` y `CODIGO_6_DIGITOS`:

```powershell
curl -Method POST "http://localhost:8001/auth/verify-2fa" -ContentType "application/json" -Body '{"temp_token":"TEMP_TOKEN","code":"CODIGO_6_DIGITOS"}'
```

Respuesta esperada:

- `access_token`
- `token_type: bearer`

## 5) Reenviar OTP

```powershell
curl -Method POST "http://localhost:8001/auth/resend-2fa" -ContentType "application/json" -Body '{"temp_token":"TEMP_TOKEN"}'
```

Respuesta esperada:

- `success: true`
- `masked_email`
- `expires_in`

## Errores comunes

- `SMTP no configurado...`: faltan variables SMTP.
- `Credenciales incorrectas`: usuario/correo/contraseña no coinciden.
- `Código incorrecto` o `expiró`: solicitar nuevo código con `/auth/resend-2fa`.
