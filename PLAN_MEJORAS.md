# Plan de Mejoras - VerificadorDePreciosLuz

## Objetivo
Mejorar seguridad, performance, observabilidad y code quality del sistema de gestión de publicidad.

---

## FASE 1: Seguridad Crítica ✅ COMPLETADA

### 1.1 Rate Limiting en Login ✅ COMPLETADO
- ~~**Archivos**: `backend-dashboard/app/routes/auth.py`, `docker-compose.yml`~~
- ~~**Descripción**: Limitación de intentos de login (5 por minuto por IP) usando Redis~~
- ~~**Impacto**: Previene ataques de fuerza bruta~~
- ~~**Complejidad**: Baja~~
- ~~**Dependencias**: Redis (`dashboard-redis` agregado al docker-compose)~~
- ~~**Variables de entorno**: `RATE_LIMIT_LOGIN_MAX=5`, `RATE_LIMIT_LOGIN_WINDOW=60`~~

### 1.2 Sanitización de Inputs ✅ COMPLETADO
- ~~**Archivos**: `backend-dashboard/app/utils/__init__.py`, `backend-dashboard/app/routes/publicidad.py`~~
- ~~**Descripción**: Funciones de sanitización para HTML, filenames y queries~~
- ~~**Impacto**: Previene XSS en tablets y path traversal~~
- ~~**Complejidad**: Media~~
- ~~**Funciones implementadas**: `sanitize_html()`, `sanitize_filename()`, `sanitize_search_query()`~~

### 1.3 Validación MIME en Uploads ✅ COMPLETADO
- ~~**Archivos**: `backend-dashboard/app/utils/__init__.py`, `backend-dashboard/app/routes/publicidad.py`~~
- ~~**Descripción**: Verificación de magic bytes del archivo, no solo extensión~~
- ~~**Impacto**: Previene upload de archivos maliciosos renombrados~~
- ~~**Complejidad**: Media~~
- ~~**Tipos soportados**: JPEG, PNG, GIF, BMP, WebP, MP4, WebM, AVI~~

---

## FASE 2: Observabilidad Base

### 2.1 Health Check Endpoint ✅ COMPLETADO
- ~~**Archivos**: `backend-dashboard/app/main.py`, `backend-dashboard/app/utils/health.py`~~
- ~~**Descripción**: Crear endpoint `GET /health` que verifique DB y Redis~~
- ~~**Impacto**: Docker/K8s puede monitorear salud del servicio~~
- ~~**Complejidad**: Baja~~
- ~~**Dependencias**: Ninguna~~
- ~~**Tests**: 15 tests implementados en `tests/test_health_check.py`~~

### 2.2 Logging Estructurado ✅ COMPLETADO (Implementado previamente)
- ~~**Archivos**: `backend-dashboard/app/utils/logger.py`~~
- ~~**Descripción**: Logging JSON con trace_id, user_id, timestamps~~
- ~~**Impacto**: Logs centralizados y analizables~~

### 2.3 2FA en Redis ✅ COMPLETADO
- ~~**Archivos**: `backend-dashboard/app/utils/twofa_redis.py`, `backend-dashboard/app/routes/auth.py`~~
- ~~**Descripción**: Guardar códigos 2FA pendientes en Redis en vez de memoria~~
- ~~**Impacto**: Usuarios no pierden sesión si servidor reinicia~~
- ~~**Complejidad**: Media~~
- ~~**Dependencias**: Redis (ya disponible)~~
- ~~**Tests**: 23 tests implementados en `tests/test_2fa_redis.py`~~

---

## FASE 3: Performance

### 3.1 Paginación en /banners ✅ COMPLETADO
- ~~**Archivos**: `backend-dashboard/app/routes/publicidad.py`~~
- ~~**Descripción**: Agregar parámetros `limit` y `offset` al endpoint~~
- ~~**Impacto**: Respuestas más rápidas con muchos banners~~
- ~~**Complejidad**: Media~~
- ~~**Dependencias**: Frontend update~~
- ~~**Tests**: 14 tests en `tests/test_pagination.py`~~

### 3.2 Fix N+1 Queries ✅ COMPLETADO
- ~~**Archivo**: `backend-dashboard/app/routes/publicidad.py`~~
- ~~**Descripción**: Pre-cargar todos los dispositivos en una query antes del loop~~
- ~~**Impacto**: Elimina queries N+1, mejora rendimiento con muchos banners~~
- ~~**Complejidad**: Media~~
- ~~**Dependencias**: SQLAlchemy~~

### 3.3 Replicación Paralela ✅ COMPLETADO
- ~~**Archivo**: `backend-dashboard/app/services/replicacion_service.py`~~
- ~~**Descripción**: Usar `asyncio.gather()` para replicar a múltiples servidores en paralelo~~
- ~~**Impacto**: 10 servidores: 10s secuencial → 1s paralelo~~
- ~~**Complejidad**: Media~~
- ~~**Dependencias**: Ninguna~~
- ~~**Tests**: 14 tests en `tests/test_parallel_replication.py`~~

---

## FASE 4: Code Quality

### 4.1 Eliminar Prints ✅ COMPLETADO
- ~~**Archivos**: `backend-dashboard/app/routes/publicidad.py`, `backend-dashboard/app/routes/monitoreo.py`, `backend-dashboard/app/utils/security.py`~~
- ~~**Descripción**: Reemplazar todos los `print()` por logging estructurado~~
- ~~**Impacto**: Logs van a sistema centralizado, no se pierden en Docker~~
- ~~**Complejidad**: Baja~~
- ~~**Dependencias**: Logging (ya implementado)~~

### 4.2 Type Hints ✅ COMPLETADO
- ~~**Archivos**: Varios~~
- ~~**Descripción**: Agregar type hints a funciones sin ellos~~
- ~~**Impacto**: Errores detectados en desarrollo, no producción~~
- ~~**Complejidad**: Baja~~
- ~~**Dependencias**: Ninguna~~

### 4.3 Tests Unitarios ✅ COMPLETADO
- ~~**Archivos**: `backend-dashboard/tests/`~~
- ~~**Tests implementados**: 113 tests en 9 archivos~~
- ~~**Tests nuevos en FASE 4**: 14 tests de Code Quality~~
- ~~**Complejidad**: Alta~~
- ~~**Dependencias**: pytest, pytest-asyncio~~

---

## FASE 5: Infraestructura

### 5.1 Backups Automatizados ⏳ PENDIENTE (Para implementar en servidor)
- **Archivos a crear manualmente en servidor**:
  - `scripts/backup_sqlserver.sh` - Script de backup
  - `backups/` - Carpeta para guardar backups
- **Descripción**: Script que ejecuta backup de SQL Server cada noche
- **Impacto**: Recuperación ante desastres
- **Complejidad**: Media
- **Cómo se configura**:
  ```
  1. Crear carpetas scripts/ y backups/
  2. Subir script backup_sqlserver.sh
  3. chmod +x scripts/backup_sqlserver.sh
  4. crontab -e → agregar: 0 3 * * * /ruta/scripts/backup_sqlserver.sh
  ```
- **NOTA**: Esta tarea se configura MANUALMENTE en el servidor, no en Git

### 5.2 CI/CD Pipeline ❌ NO APLICA
- **Razón**: Servidor propio con NOIP, no usa Vercel/Heroku
- **Alternativa**: Deploy manual con `docker-compose pull && docker-compose up -d`

### 5.3 Docker Multi-stage Build ⏳ PENDIENTE
- **Archivo**: `backend-dashboard/Dockerfile`
- **Descripción**: Usar multi-stage para reducir tamaño de imagen (~900MB → ~250MB)
- **Impacto**: Imágenes más pequeñas, builds más rápidos
- **Complejidad**: Media
- **Dependencias**: Ninguna
- **Cambio**:
  - Separar builder de runtime
  - Solo copiar lo necesario a imagen final

---

## Resumen de Progreso

| Fase | Completado | Pendiente |
|------|------------|-----------|
| FASE 1 (Seguridad) | 3/3 ✅ | 0/3 |
| FASE 2 (Observabilidad) | 3/3 ✅ | 0/3 |
| FASE 3 (Performance) | 3/3 ✅ | 0/3 |
| FASE 4 (Code Quality) | 3/3 ✅ | 0/3 |
| FASE 5 (Infraestructura) | 0/2 | 2/2 |

**Total: 12/14 completados (86%)**

---

## FASE 6: Cambio de Asignación con Cleanup ⏳ EN PROGRESO (Funciones listas)

### Problema identificado
Cuando se edita una publicidad cambiando la asignación (ej: de "todos" a específico), el sistema no elimina el banner de los servidores que deben perderlo. Esto causa que el banner aparezca en dispositivos incorrectos.

### Descripción del problema
- **Caso B** ("todos" → específico): Solo envía a nuevos srv, no elimina de antiguos
- **Caso D** (específico1 → específico2): Solo envía a nuevos srv, no elimina de los quitados

### Casos de asignación

| Caso | Anterior | Nuevo | Problema |
|------|----------|-------|---------|
| A | "todos" → "todos" | ✅ Actualiza todos (funciona) |
| B | "todos" → específico | ❌ No elimina de srv que deben perder |
| C | específico → "todos" | ⚠️ Funciona pero sin verificación |
| D | específico1 → específico2 | ❌ No elimina de srv removidos |

### Solución diseño

1. **Verificar asignación ANTERIOR** del banner antes de cambiar
2. **Consultar servidores** (paralelo) para ver quién tiene el banner actualmente
3. **Calcular diferencias** usando operaciones de conjuntos
4. **Ejecutar acciones**:
   - srv_AGREGAR → POST /replicar-archivo
   - srv_ELIMINAR → PUT con dispositivo_ids=""
   - srv_ACTUALIZAR → PUT actualizar datos

### Especificaciones técnicas

| Parámetro | Valor |
|----------|------|
| Timeout consultas paralelo | 35 segundos |
| Manejo de errores | Detener proceso y notificar |
| Logging | Incluido para debugging |

### Funciones implementadas (PRIORIDAD 1)

| Función | Archivo | Estado |
|---------|--------|--------|
| `limpiar_banner_de_servidor()` | replicacion_service.py | ✅ Implementada |
| `obtener_servidores_con_banner()` | replicacion_service.py | ✅ Implementada |
| `procesar_cambio_asignacion()` | replicacion_service.py | ✅ Implementada |
| Modificar endpoint publicidad.py | routes | ⏳ Pendiente |
| Tests unitarios | tests/ | ⏳ Pendiente |

### Tests a implementar

| Test | Descripción |
|------|-----------|
| test_cambio_todos_a_especifico | Verifica agregar + eliminar |
| test_cambio_especifico_a_todos | Verifica agregar a todos |
| test_cambio_especifico_a_especifico | Verifica agregar + eliminar |
| test_error_en_servidor | Verifica que se detenga al fallar uno |
| test_timeout_paralelo | Verifica timeout de 35s |

### Implementación por prioridad

**_PRIORIDAD 1 (implementar ahora)**: Casos B y D (los más problemáticos)
** PRIORIDAD 2**: Casos A y C (mejoras adicionales)

---

**Total: 12/14 completados (86%)**

---

## Orden de Implementación Sugerido

1. ~~✅ FASE 1 (Seguridad) - Completada~~
2. ~~✅ FASE 2 (Observabilidad) - Completada~~
3. ~~✅ FASE 3 (Performance) - Completada~~
4. ~~✅ FASE 4 (Code Quality) - Completada~~
5. ⏳ FASE 5 (Infra) - Backups y CI/CD

---

## Notas
- Los datos sensibles (correo, claves) están cifrados o no son críticos
- Redis ya está disponible en el stack actual (`dashboard-redis`)
- Rate limiting persiste entre reinicios gracias a Redis

## Tareas Pendientes para FASE 5

### Backups Automatizados (Manual en servidor)
```bash
# En tu servidor, crear estructura:
mkdir -p scripts backups

# Script: scripts/backup_sqlserver.sh
# - Ejecuta backup SQL cada noche a las 3am
# - Guarda .bak en carpeta backups/
# - Mantiene últimos 7 días

# Configurar cron:
crontab -e
# Agregar: 0 3 * * * /home/user/scripts/backup_sqlserver.sh >> /var/log/backup.log 2>&1
```

### Docker Multi-stage Build (Pendiente implementar)
- Reducir tamaño de imagen de ~900MB a ~250MB
- Separar etapas de build y runtime

---

## Archivos Modificados en FASE 1, FASE 2, FASE 3 y FASE 4

| Archivo | Cambios |
|---------|---------|
| `docker-compose.yml` | ✅ Agregado `dashboard-redis` |
| `backend-dashboard/app/routes/auth.py` | ✅ Rate limiting y 2FA en Redis |
| `backend-dashboard/app/utils/__init__.py` | ✅ Sanitización y validación MIME |
| `backend-dashboard/app/routes/publicidad.py` | ✅ Sanitización, paginación, fix N+1, sin prints |
| `backend-dashboard/app/routes/monitoreo.py` | ✅ Logs estructurados (sin prints) |
| `backend-dashboard/app/main.py` | ✅ Endpoint `/health` |
| `backend-dashboard/app/utils/health.py` | ✅ Funciones de health check |
| `backend-dashboard/app/utils/twofa_redis.py` | ✅ Gestión de 2FA en Redis |
| `backend-dashboard/app/utils/security.py` | ✅ Logging estructurado |
| `backend-dashboard/app/services/replicacion_service.py` | ✅ Replicación paralela, logs optimizados |
| `backend-dashboard/tests/test_rate_limiting.py` | ✅ 9 tests |
| `backend-dashboard/tests/test_sanitization.py` | ✅ 17 tests |
| `backend-dashboard/tests/test_mime_validation.py` | ✅ 6 tests |
| `backend-dashboard/tests/test_health_check.py` | ✅ 15 tests |
| `backend-dashboard/tests/test_2fa_redis.py` | ✅ 23 tests |
| `backend-dashboard/tests/test_pagination.py` | ✅ 14 tests |
| `backend-dashboard/tests/test_parallel_replication.py` | ✅ 14 tests |
| `backend-dashboard/tests/test_code_quality.py` | ✅ 14 tests |
| `PLAN_MEJORAS.md` | ✅ Documentación del plan |

**Total tests: 127**

## Tareas Pendientes (FASE 5)

| Tarea | Ubicación | Cómo |
|-------|-----------|------|
| Backups SQL Server | Servidor (manual) | Script + cron |
| Docker Multi-stage | `backend-dashboard/Dockerfile` | Implementar build分开 |
