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

### 5.3 Docker Multi-stage Build ✅ COMPLETADO
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
| FASE 6 (Cambio Asignación) | 1/1 ✅ | 0/1 |
| FASE 7 (Fix Asignaciones + Vigencia) | 2/5 | 3/5 |
| FASE 8 (Background Monitoring Sesiones) | 4/4 ✅ | 0/4 |
| FASE 9 (Thumbnails Videos) | 6/6 ✅ | 0/6 |
| FASE 10 (Limpieza Columnas) | 5/5 ✅ | 0/5 |
| FASE 11 (Refactor Backend) | 3/3 ✅ | 0/3 |
| FASE 12 (Frontend Base) | 2/2 ✅ | 0/2 |
| FASE 13 (UX/UI) | 2/2 ✅ | 0/2 |
| FASE 14 (Pulido Visual) | 2/2 ✅ | 0/2 |
| FASE 15 (Blindaje WebSocket) | 17/17 ✅ | 0/17 |
| FASE 17 (Cola Dashboard) | 17/17 ✅ | 0/17 |
| FASE 18 (Bots Mantenimiento) | 5/5 ✅ | 0/5 |

**Total: 88/89 completados (99%) — solo falta FASE 5.1 (backups manuales en servidor)**

---

## FASE 6: Cambio de Asignación con Cleanup ✅ COMPLETADO

### Problema identificado
Cuando se edita una publicidad cambiando la asignación (ej: de "todos" a específico), el sistema no elimina el banner de los servidores que deben perderlo. Esto causa que el banner aparezca en dispositivos incorrectos.

### Descripción del problema (RESUELTO)
- **Caso B** ("todos" → específico): ✅ Ahora elimina de srv que deben perder
- **Caso D** (específico1 → específico2): ✅ Ahora elimina de srv removidos

### Casos de asignación

| Caso | Anterior | Nuevo | Estado |
|------|----------|-------|--------|
| A | "todos" → "todos" | ✅ Actualiza todos | ✅ Completado |
| B | "todos" → específico | ❌/✅ Ahora elimina de srv que deben perder | ✅ Completado |
| C | específico → "todos" | ✅ Agrega a srv que no lo tienen | ✅ Completado |
| D | específico1 → específico2 | ✅ Elimina de srv removidos + agrega a nuevos | ✅ Completado |

### Solución implementada

1. **Verificar asignación ANTERIOR** del banner antes de cambiar (`/banners/{id}/exists`)
2. **Consultar servidores** (paralelo) para ver quién tiene el banner actualmente
3. **Calcular diferencias** usando operaciones de conjuntos
4. **Ejecutar acciones**:
   - srv_AGREGAR → POST /replicar-archivo
   - srv_ELIMINAR → DELETE /banners/remoto/{id}
   - srv_ACTUALIZAR → PUT actualizar datos
   - **FALLBACK**: Si PUT retorna 404 → hacer POST automáticamente

### Bug crítico corregido
El endpoint `/exists` retornaba `true` pero PUT fallaba con 404. El fix:
- Cuando PUT falla (404), detectar `needs_replicate: true`
- Ejecutar POST `/replicar-archivo` automáticamente para crear el banner

### Especificaciones técnicas

| Parámetro | Valor |
|----------|------|
| Timeout consultas paralelo | 35 segundos |
| Manejo de errores | Detener proceso y notificar |
| Logging | Incluido para debugging |
| Escalabilidad | ✅ Soporta 10+ servidores (paralelo) |

### Funciones implementadas (PRIORIDAD 1)

| Función | Archivo | Estado |
|---------|--------|--------|
| `limpiar_banner_de_servidor()` | replicacion_service.py | ✅ Completado |
| `obtener_servidores_con_banner()` | replicacion_service.py | ✅ Completado |
| `procesar_cambio_asignacion()` | replicacion_service.py | ✅ Completado |
| Modificar endpoint publicidad.py | routes/publicidad.py | ✅ Completado |
| Fallback PUT→POST | replicacion_service.py | ✅ Completado |
| Debug logs | backend-api/routes/publicidad.py | ✅ Completado |

### Pruebas realizadas

| Test | Descripción | Resultado |
|------|-----------|-----------|
| Específico → Todos | PUT 404 → replicar automáticamente | ✅ PASS |
| Todos → Específico | DELETE del srv removido + PUT asignar | ✅ PASS |
| 2 servidores | Verificar comportamiento | ✅ PASS |

### Logs de ejemplo

```
fase6_caso_a_resultado: banner_id=3561, exito=true, agregar=1, eliminar=0, actualizar=2
fase6_resultado: banner_id=3561, exito=true, agregar=0, eliminar=2, actualizar=1
```

---

## FASE 7: Fix Asignaciones + Control de Vigencia (Banners fechaInicio/fechaFin)

### Problemas identificados

#### 7.1 Bug Caso D (específico → específico)
Cuando se cambia de un servidor específico a OTRO servidor específico:
- El banner se elimina de AMBOS servidores
- Queda marcado como "borrador" en el dashboard
- **Causa**: Si el frontend no envía `servidor_ids`, la lógica asume "sin asignaciones" y pasa `srv_nuevos_ids = {}` → elimina de todos

#### 7.2 Bug estado "borrador"
Cuando se cambia asignación específica:
- Si `asignacion_todos = false` + sin asignaciones → marca "borrador"
- La lógica NO verifica si la replicación fue exitosa
- **Causa**: Solo valida `len(asignaciones) == 0`, no valida el resultado de la replicación

#### 7.3 Falta de validación de vigencia en luzapp
- El sistema NO valida `fechaInicio/fechaFin` antes de reproducir un banner
- Si el dispositivo no sincroniza después de expirar, **sigue reproduciendo** el banner vencido desde cache local
- No hay validación "antes de reproducir" en la app

---

### Soluciones propuestas

#### 7.1 Fix Caso D (específico → específico)

| Problema | Solución |
|----------|----------|
| No detecta servidores nuevos | Incluir servidores anteriores como fallback si no vienen nuevos |
| Elimina de todos | Solo eliminar si hay nuevos servidores objetivo |
| Queda "borrador" | Validar que haya servidores antes de marcar `asignacion_todos=false` |

**Implementación sugerida**:
- En `publicidad.py:1142` - agregar fallback: si `target_dispositivo_ids` está vacío, mantener asignaciones anteriores
- Validar que `servidores_asignados_data` no esté vacío antes de ejecutar `procesar_cambio_asignacion`

#### 7.2 Fix estado "borrador"

| Problema | Solución |
|----------|----------|
| `asignacion_todos=false` + sin asignaciones → "borrador" | Mantener estado anterior si falla la replicación |
| No detecta errores de replicación | Verificar resultado de `procesar_cambio_asignacion` antes de confirmar cambio |

**Implementación sugerida**:
- En `publicidad.py:1037` - no marcar `asignacion_todos=false` si no hay servidores objetivo
- Verificar `update_result.get("exito")` antes de finalizar el cambio

#### 7.3 Control de Vigencia (3 capas de protección)

| # | Solución | Ubicación | Descripción |
|---|---------|-----------|------------|
| S1 | Pre-validation | luzapp | Validar `fechaFinMs` antes de reproducir (safety net) |
| S2 | Cache cleanup | luzapp | Eliminar banners vencidos al sincronizar |
| S3 | WebSocket push | backend-api | Invalidación inmediata cuando admin cambia |

**Flujo propuesto**:

```
DASHBOARD                      BACKEND-API                   LUZAPP
──────────────────────────────────────────────────────────────────
1. Admin crea banner
   fecha_inicio: 14/04/2026 08:00
   fecha_fin:    14/04/2026 18:00
   ─────────────────────────────────────────────────────────────▶
2. POST /replicar-archivo
   Guarda en tabla publicidad
   (fecha_inicio, fecha_fin)
   ─────────────────────────────────────────────────────────────
3. GET /banners?device_id=xxx
   Backend filtra por fecha:
   WHERE fecha_fin >= ahora
   Retorna lista vigente
   ◀───────────────────────────────────────────────────────────
4. luzapp descarga + guarda en cache
   BannerCacheItem:
   - id, url, localPath
   - fechaFinMs: 1742055600000  ← NUEVO: guardar fechaFin
```

**Por qué NO implementar loop de report back**:
- Backend ya conoce `fecha_fin` de la base de datos
- Evita race conditions (admin cambia → dispositivo reporta inactivo → admin no puede reactivarlo)
- Las 3 soluciones son independientes y no requieren report back

---

### Tareas de FASE 7

| # | Tarea | Estado | Ubicación |
|---|-------|--------|-----------|
| 7.1 | Fix caso específico→específico | ✅ Completado | backend-dashboard/publicidad.py |
| 7.2 | Fix estado "borrador" | ✅ Completado | backend-dashboard/publicidad.py |
| 7.3 | Pre-validation (S1) - validar fechaFin antes de reproducir | ⏳ Pendiente | luzapp/ScanActivity.kt |
| 7.4 | Cache cleanup (S2) - eliminar banners vencidos | ✅ Completado | luzapp/BannerRepository.kt |
| 7.5 | WebSocket push (S3) - invalidación inmediata | ✅ Completado | backend-api + luzapp |

---

### Especificaciones técnicas para S1 (Pre-validation luzapp)

```kotlin
// En playStandbyItem() antes de reproducir:
if (item.fechaFinMs != null && now > item.fechaFinMs) {
    Log.w(TAG, "Banner vencido, skipping: ${item.id}")
    nextStandbyItem()  // Skip banner vencido
    return
}
```

### Especificaciones técnicas para S2 (Cache cleanup luzapp)

```kotlin
// En BannerRepository - al sincronizar:
fun cleanupExpiredBanners() {
    val now = System.currentTimeMillis()
    items.removeAll { 
        it.fechaFinMs != null && now > it.fechaFinMs 
    }
    saveMetadata()
}
```

### Especificaciones técnicas para S3 (WebSocket push)

```python
# backend-api - cuando admin cambia banner:
# Mensaje: { "type": "BANNER_EXPIRED", "banner_id": 123 }
# luzapp lo elimina del cache
```

---

**Total: 13/19 completados (68%)** - FASE 7 suma 5 tareas adicionales

---

## Orden de Implementación Sugerido

1. ~~✅ FASE 1 (Seguridad) - Completada~~
2. ~~✅ FASE 2 (Observabilidad) - Completada~~
3. ~~✅ FASE 3 (Performance) - Completada~~
4. ~~✅ FASE 4 (Code Quality) - Completada~~
5. ⏳ FASE 5 (Infra) - Backups y CI/CD

---

## FASE 8: Background Monitoring de Sesiones de Dispositivos

### Problema identificado

El monitoreo de sesiones de dispositivos **solo se ejecuta cuando alguien accede al dashboard**. Esto causa que:
- Si nadie entra al dashboard por un tiempo, los cronómetros de tiempo de actividad no se actualizan
- Los dispositivos pueden desconectarse y conectarse sin que el sistema lo detecte si no hay actividad en el dashboard

### Solución propuesta

Ejecutar el monitoreo de sesiones automáticamente en **background** cada **3 minutos 30 segundos** (3.5 minutos).

### Tareas de FASE 8

| # | Tarea | Estado | Ubicación |
|---|-------|--------|-----------|
| 8.1 | Agregar APScheduler a requirements.txt | ✅ Completado | requirements.txt |
| 8.2 | Extraer lógica de monitoreo | ✅ Completado | app/services/monitoreo_service.py |
| 8.3 | Crear módulo de scheduler | ✅ Completado | app/scheduler.py |
| 8.4 | Integrar scheduler en main.py | ✅ Completado | app/main.py |

### Especificaciones técnicas

**Nuevo servicio: app/services/monitoreo_service.py**

```python
async def actualizar_sesiones_dispositivos():
    """
    Función que se ejecuta cada 3.5 minutos.
    Consulta /devices/status de cada servidor secundario
    y actualiza sesiones en BD (DispositivoSesion).
    """
    # 1. Obtener todos los servidores secundarios online
    # 2. Para cada servidor: _obtener_dispositivos_de_servidor(ip)
    # 3. Actualizar DispositivoSesion (inicio/fin/duracion)
    # 4. Tolerancia a errores: si un servidor no responde, continuar
```

**Scheduler en app/main.py:**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(
    actualizar_sesiones_dispositivos,
    'interval',
    minutes=3.5,  # 3 minutos 30 segundos
    id='monitoreo_sesiones'
)
scheduler.start()
```

### Consideraciones

| Aspecto | Detalle |
|---------|---------|
| **Frecuencia** | 3.5 minutos (evita choque con desconexión de 8 min para servidores y 3 min para dispositivos) |
| **Tolerancia a errores** | Si un servidor no responde, continuar con los demás |
| **Logging** | Registrar inicio y fin de cada ejecución |
| **Sesiones** | Se registrarán igual que ahora: inicio/fin/duración (sin notificaciones) |

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

## Archivos Modificados en FASE 1-8

| Archivo | Cambios |
|---------|---------|
| `docker-compose.yml` | ✅ Agregado `dashboard-redis` |
| `backend-dashboard/app/routes/auth.py` | ✅ Rate limiting y 2FA en Redis |
| `backend-dashboard/app/utils/__init__.py` | ✅ Sanitización y validación MIME |
| `backend-dashboard/app/routes/publicidad.py` | ✅ Sanitización, paginación, fix N+1, sin prints, FASE 6, FASE 7 (parser, validación), logs estructurados |
| `backend-dashboard/app/routes/monitoreo.py` | ✅ Logs estructurados (sin prints) |
| `backend-dashboard/app/main.py` | ✅ Endpoint `/health`, lifespan scheduler |
| `backend-dashboard/app/utils/health.py` | ✅ Funciones de health check |
| `backend-dashboard/app/utils/twofa_redis.py` | ✅ Gestión de 2FA en Redis |
| `backend-dashboard/app/utils/security.py` | ✅ Logging estructurado |
| `backend-dashboard/app/services/replicacion_service.py` | ✅ Replicación paralela, Cleanup FASE 6, fallback PUT→POST |
| `backend-dashboard/app/services/monitoreo_service.py` | ✅ Nuevo - lógica de monitoreo de sesiones |
| `backend-dashboard/app/scheduler.py` | ✅ Nuevo - scheduler APScheduler |
| `backend-dashboard/requirements.txt` | ✅ Agregado apscheduler |
| `backend-api/app/routes/publicidad.py` | ✅ Debug logs para /exists y PUT |
| `dashboard/services/videoService.ts` | ✅ Fix tipo dispositivoIds (string[]), mapeo thumbnail |
| `dashboard/components/ServerDeviceSelector.tsx` | ✅ Props actualizadas |
| `backend-dashboard/tests/test_rate_limiting.py` | ✅ 9 tests |
| `backend-dashboard/tests/test_sanitization.py` | ✅ 17 tests |
| `backend-dashboard/tests/test_mime_validation.py` | ✅ 6 tests |
| `backend-dashboard/tests/test_health_check.py` | ✅ 15 tests |
| `backend-dashboard/tests/test_2fa_redis.py` | ✅ 23 tests |
| `backend-dashboard/tests/test_pagination.py` | ✅ 14 tests |
| `backend-dashboard/tests/test_parallel_replication.py` | ✅ 14 tests |
| `backend-dashboard/tests/test_code_quality.py` | ✅ 14 tests |
| `PLAN_MEJORAS.md` | ✅ Documentación del plan |

**Total tests: 127 (+ FASE 6 manual test)**

## Tareas Pendientes (FASE 5)

| Tarea | Ubicación | Cómo |
|-------|-----------|------|
| Backups SQL Server | Servidor (manual) | Script + cron |
| Docker Multi-stage | `backend-dashboard/Dockerfile` | Implementar build分开 |

---

## FASE 9: Thumbnails de Videos ✅ COMPLETADA

### Problema identificado

Los videos en el dashboard no muestran miniatura (thumbnail) en el preview, lo cual dificulta identificar el contenido visualmente.

### Solución implementada

Generar thumbnails automáticamente al subir videos usando OpenCV, y mostrarlos en el atributo `poster` del elemento `<video>`.

### Tareas de FASE 9

| # | Tarea | Estado | Ubicación |
|---|-------|--------|-----------|
| 9.1 | Agregar campo ThumbnailUrl al modelo | ✅ Completado | app/models/publicidad.py |
| 9.2 | Agregar campo al schema response | ✅ Completado | app/schemas/publicidad.py |
| 9.3 | Agregar dependencia opencv | ✅ Completado | requirements.txt |
| 9.4 | Implementar generación de thumbnail | ✅ Completado | app/routes/publicidad.py |
| 9.5 | Mapear thumbnail en frontend | ✅ Completado | services/videoService.ts |
| 9.6 | Usar poster en video player | ✅ Completado | screens/DashboardScreen.tsx |

---

## FASE 10: Limpieza de Columnas No Utilizadas

### Problema identificado

Existen columnas legacy que ya no aportan valor funcional y generan complejidad de mantenimiento:
- `DuracionSeg` en `Publicidad` (dashboard + api)
- `api_url` en `servidores_secundarios` (dashboard)

### Solución propuesta

Eliminar el uso en código y luego eliminar físicamente las columnas en base de datos.

### Tareas de FASE 10

| # | Tarea | Estado | Ubicación |
|---|-------|--------|-----------|
| 10.1 | Eliminar `api_url` de modelo y uso en backend-dashboard | ✅ Completado | `backend-dashboard/app/models/servidor_secundario.py` + `backend-dashboard/app/routes/publicidad.py` |
| 10.2 | Eliminar `DuracionSeg` en backend-dashboard (modelo/schemas/rutas/servicios) | ✅ Completado | `backend-dashboard/app/**` |
| 10.3 | Eliminar `DuracionSeg` en backend-api (modelo/schemas/rutas) | ✅ Completado | `backend-api/app/**` |
| 10.4 | Ajustar frontend para no depender de `DuracionSeg` | ✅ Completado | `dashboard/services/videoService.ts` |
| 10.5 | Ejecutar migración SQL para dropear columnas en BD | ✅ Completado | SQL Server |

### Query de migración SQL (pendiente ejecutar)

```sql
ALTER TABLE Publicidad DROP COLUMN DuracionSeg;
ALTER TABLE servidores_secundarios DROP COLUMN api_url;
```

### Especificaciones técnicas

**Dependencia (requirements.txt):**
```
opencv-python-headless
```

**Modelo (app/models/publicidad.py):**
```python
ThumbnailUrl = Column("ThumbnailUrl", String(500), nullable=True)
```

**Generación de thumbnail (app/routes/publicidad.py):**
```python
if Tipo == "video":
    thumbnail_filename = generar_thumbnail(file_location, banners_dir)
    thumbnail_url = f"/static/banners/{thumbnail_filename}"
else:
    thumbnail_url = url  # Para imágenes, usar la misma URL

nuevo_banner = Publicidad(..., ThumbnailUrl=thumbnail_url)
```

**Frontend (DashboardScreen.tsx):**
```tsx
<video 
  poster={preview.thumbnail || preview.url}
  src={preview.url}
  controls
/>
```

---

## Estado Actual: Progreso Total (FASES ORIGINALES)

**Total: 37/40 completados (93%)**

- FASE 1-4: ✅ Completas
- FASE 5: ⏳ Pendiente (2 tareas manual en servidor)
- FASE 6: ✅ Completada
- FASE 7: 🔄 Parcial (2/5, tareas luzapp pendientes)
- FASE 8: ✅ Completada
- FASE 9: ✅ Completada
- FASE 10: ✅ Completada
- FASE 11: ✅ Completada
- FASE 12: ✅ Completada
- FASE 13: ✅ Completada
- FASE 14: ✅ Completada

---

## FASE 11: Refactorización y Estabilidad (Backend) ✅ COMPLETADA

*Prioridad: Crítica | Objetivo: Eliminar deuda técnica y mejorar mantenibilidad.*

### 11.1 Refactorización de `monitoreo.py` ✅ COMPLETADO
- ~~**Descripción**: Dividir `monitoreo.py` en módulos independientes:~~
  - ~~`servers.py` - Gestión de servidores secundarios~~
  - ~~`devices.py` - Gestión de dispositivos~~
  - ~~`sync.py` - Lógica de sincronización~~
- ~~**Impacto**: Estructura modular y mantenible~~
- ~~**Complejidad**: Media~~

### 11.2 Implementación de `sync_service.py` y servicios ✅ COMPLETADO
- ~~**Descripción**: Mover lógica de negocio de rutas a servicios~~
- ~~**Impacto**: Permite pruebas unitarias y desacopla la API~~
- ~~**Complejidad**: Media~~

### 11.3 Manejador Global de Excepciones ✅ COMPLETADO
- ~~**Descripción**: Reemplazar `try-except: pass` por respuestas estandarizadas y logging en 20 sitios silenciosos (9 archivos): `publicidad.py` (4x `ValueError: pass` + 4x bare `except`), `auth.py` (3 silent catches), `main.py` (1 `except: pass`), `sync_service.py` (4 silent fallbacks), `twofa_redis.py` (1), `health.py` (1), `utils/__init__.py` (1), `replicacion_service.py` (1), `notificaciones.py` (1)~~
- ~~**Impacto**: Frontend recibe errores claros + visibilidad en logs~~
- ~~**Complejidad**: Baja~~

---

## FASE 12: Infraestructura de Navegación y Estado (Frontend) ✅ COMPLETADA

*Prioridad: Alta | Objetivo: Crear una base sólida para la expansión de la UI.*

### 12.1 Integración de `react-router-dom` ✅ COMPLETADO
- ~~**Archivos**: `dashboard/App.tsx`, `dashboard/components/Sidebar.tsx`, `dashboard/components/DashboardHeader.tsx`, `dashboard/components/GeneralNotifications.tsx`, `dashboard/components/ProtectedLayout.tsx` (nuevo)~~
- ~~**Descripción**: Migrado switch de `currentScreen` a rutas reales con react-router-dom v6~~
- ~~**Rutas**: `/` (Mis Videos), `/servidores`, `/usuarios`, `/calendario`, `/auditoria`~~
- ~~**Layout protegido**: `ProtectedLayout` con verificación de sesión + token expiry watcher + `<Outlet>`~~

### 12.2 Implementación de `Zustand` ✅ COMPLETADO
- ~~**Archivos**: `dashboard/stores/sessionStore.ts` (nuevo)~~
- ~~**Descripción**: Store centralizada de sesión (`isAuthenticated`, `role`, `userName`, `login`, `logout`, `checkSession`)~~
- ~~**Impacto**: Elimina prop-drilling de sesión, estado accesible desde cualquier componente~~

---

## FASE 13: Experiencia de Usuario y Funcionalidades (UX/UI) ✅ COMPLETADA (parcial)

*Prioridad: Media | Objetivo: Profesionalizar la interacción con el usuario.*

### 13.1 Sistema de Feedback (Toasts y Modales) ✅ COMPLETADO
- ~~**Descripción**: Implementar avisos descriptivos y confirmaciones. Añadido: botón X por toast, barra progreso auto-dismiss, removeAll, límite 5, modo persistent, animación slide-fade-out. Backwards-compatible (no rompe consumidores existentes).~~
- ~~**Impacto**: Reduce errores accidentales del usuario~~
- ~~**Complejidad**: Baja~~

### 13.2 Vista de Auditoría Detallada + PDF ✅ COMPLETADO
- ~~**Descripción**: Crear pantalla de logs con filtros avanzados. Backend: `GET /auditoria/exportar` genera PDF landscape con fpdf2, tabla word-wrap, header repetido. Frontend: botón "Exportar PDF", filtro servidor `<select>`, `<TableSkeleton>`.~~
- ~~**Impacto**: Aprovecha robustez del backend (FASE 11)~~
- ~~**Complejidad**: Media~~

### 13.3 Visualización de Datos (`Recharts`) ❌ POSPUESTO
- **Descripción**: Implementar gráficas de almacenamiento y uptime
- **Impacto**: Transforma datos crudos en información visual
- **Complejidad**: Media
- **Dependencias**: recharts
- **Nota**: Pos puesto para un módulo Dashboard aparte

---

### Mejora Adicional: Nombres Amigables en Notificaciones ✅ COMPLETADO
- ~~**Descripción**: Las notificaciones ahora muestran `"NombreAmigable (device_id)"` en lugar de solo `device_id`. Aplicado en webhooks entrantes (`SYNC_FAILED`, `PLAYBACK_FAILED`, `BANNER_INICIADO/FINALIZADO`) y operaciones internas (`RENOMBRAR_DISPOSITIVO`, `REINICIAR_DISPOSITIVO`, `FALLO`).~~
- ~~**Archivos**: `backend-dashboard/app/routes/notificaciones.py`, `backend-dashboard/app/services/device_service.py`~~
- ~~**Helper**: `_get_device_name()` consulta `Dispositivo.nombre_amigable`~~
- ~~**Complejidad**: Baja~~

### Mejora Adicional: Nombres Amigables en Descripciones + Auditoría ✅ COMPLETADO
- ~~**Descripción**: Descripciones de notificaciones (`SINCRONIZACION_SELECTIVA`, `BORRADO_MULTIMEDIA`, `EDICION_VIGENCIA_MULTIMEDIA`) ahora muestran `"NombreAmigable (id_disp)"` y `"id_srv - NombreServidor"`. Auditoría resuelve nombres vía JOIN para notificaciones. Columna servidor en frontend muestra nombre + ID secundario.~~
- ~~**Archivos**: `backend-dashboard/app/services/sync_service.py`, `backend-dashboard/app/routes/publicidad.py`, `backend-dashboard/app/routes/auditoria.py`, `dashboard/screens/AuditoriaScreen.tsx`~~
- ~~**Helper**: `_resolve_device_names()` en `sync_service.py`~~

### Mejora Adicional: Cards Grid items-baseline ✅ COMPLETADO
- ~~**Descripción**: Grid de tarjetas de video y servidores usa `items-baseline` para evitar que al expandir una tarjeta, las vecinas se estiren.~~
- ~~**Archivos**: `dashboard/screens/DashboardScreen.tsx`, `dashboard/components/ServerDashboard.tsx`~~

---

## FASE 14: Pulido Visual y Estética (Polishing) ✅ COMPLETADA

*Prioridad: Baja | Objetivo: Lograr un acabado de producto final.*

### 14.1 Sistemas de Carga (Skeleton Screens) ✅ COMPLETADO
- ~~**Descripción**: Añadir estados de carga visuales. Creados: `Spinner.tsx`, `Skeleton.tsx`, `TableSkeleton.tsx`, `CardSkeleton.tsx`. Aplicados en `DashboardScreen.tsx`, `UsersScreen.tsx`, `AuditoriaScreen.tsx`, `CalendarScreen.tsx`.~~
- ~~**Impacto**: Mejora la percepción de velocidad~~
- ~~**Complejidad**: Baja~~

### 14.2 Selector de Tema (Dark/Light Mode) ✅ COMPLETADO
- ~~**Descripción**: Implementar persistencia con `localStorage`. Creado `stores/themeStore.ts` (Zustand), script anti-flash en `index.html`, quitado `class="dark"` hardcodeado, `DashboardHeader.tsx` migrado de `useState` a `useThemeStore`.~~
- ~~**Impacto**: Mejora el confort visual del operador (tema persiste entre recargas)~~
- ~~**Complejidad**: Baja~~

---

## FASE 15: Blindaje de Entrega de Comandos WebSocket (Cola Persistente)

*Prioridad: CRÍTICA | Objetivo: Garantizar que los comandos (WIPE_AND_RESYNC, REINICIAR, BANNER_INICIADO, BANNER_FINALIZADO) lleguen al dispositivo incluso en conexiones inestables.*

### Problema Raíz

Cuando un WebSocket se cae y reconecta múltiples veces al día, existen **7 puntos de fallo** identificados:

| # | Problema | Impacto |
|---|---------|---------|
| P1 | Bus listener muere silenciosamente si `send_to_device()` raisea | Todos los comandos vía Redis pub/sub se pierden hasta reiniciar |
| P2 | Socket zombie en `device_map` hasta 30s (pong timeout) | Comandos se envían al vacío sin encolar |
| P3 | Race condition en `flush_message_queue`: cola se popea antes de enviar | Si el WS cae durante el flush, mensajes perdidos sin rollback |
| P4 | `_message_queues` es `asyncio.Queue` en RAM | Se pierde al reiniciar servidor; límite 10 msg, TTL 5 min |
| P5 | `device:pending:banner:*` se escribe pero **nunca se consume** | Dead-end: datos que nadie lee |
| P6 | No hay `pending_sync` flag en Redis | No se puede detectar que un sync falta al reconectar |
| P7 | REINICIAR sin reintentos (solo timeout 60s) | Si no llega, se abandona para siempre |

---

### Fase 15.1 — Fix Críticos Inmediatos (backend-api)

| # | Tarea | Estado | Ubicación |
|---|-------|--------|-----------|
| 15.1.1 | Envolver `_on_bus_command` y `_on_bus_confirmation` en try/except para evitar muerte del bus listener | ✅ Completado | `backend-api/app/main.py:1923-1938` |
| 15.1.2 | Agregar reconexión automática del bus listener si muere (wrap con restart loop) | ✅ Completado | `backend-api/app/main.py:1997-2005` |
| 15.1.3 | En `send_to_device()`: si falla el envío por socket zombie, encolar mensaje **después** del disconnect | ✅ Completado | `backend-api/app/main.py:1640-1657` |
| 15.1.4 | En `flush_message_queue()`: no `pop()`ear la cola hasta confirmar envío. Si falla, re-encolar | ✅ Completado | `backend-api/app/main.py:1714-1754` |

**Detalle técnico 15.1.1 — Protección del bus listener:**

```python
async def _on_bus_command(device_id, command, payload):
    try:
        if command == "WIPE_AND_RESYNC":
            await tablet_ws_manager.send_to_device(device_id, {"command": "WIPE_AND_RESYNC"})
        elif command == "REINICIAR":
            message = {"command": "REINICIAR"}
            if payload:
                message.update(payload)
            await tablet_ws_manager.send_to_device(device_id, message)
        elif command in ("BANNER_INICIADO", "BANNER_FINALIZADO"):
            await tablet_ws_manager.send_to_device(device_id, payload)
    except Exception as e:
        logger.error(f"[BUS] Error procesando comando para {device_id}: {e}")
```

**Detalle técnico 15.1.2 — Auto-restart del listener:**

```python
async def _start_device_bus_listener_with_retry():
    while True:
        try:
            await _start_device_bus_listener()
        except Exception as e:
            logger.error(f"[BUS] Listener murió, reiniciando en 5s: {e}")
            await asyncio.sleep(5)
```

**Detalle técnico 15.1.3 — Encolar después de zombie:**

```python
async def send_to_device(self, device_id, message):
    ws = self.device_map.get(device_id)
    if ws:
        try:
            await ws.send_json(message)
            return True
        except Exception as e:
            await self.disconnect(ws)
            # NO raise — encolar después del disconnect
    # Encolar siempre si no hay socket vivo
    await self._enqueue_message(device_id, message)
    return False
```

**Detalle técnico 15.1.4 — Flush atómico:**

```python
async def flush_message_queue(self, device_id, websocket):
    if device_id not in self._message_queues:
        return 0
    queue = self._message_queues[device_id]
    delivered = 0
    failed_messages = []
    while not queue.empty():
        try:
            msg = queue.get_nowait()
            await websocket.send_json(msg)
            delivered += 1
        except Exception as e:
            failed_messages.append(msg)
            break
    # Re-encolar los que fallaron
    for msg in failed_messages:
        await queue.put(msg)
    if not queue.empty():
        self._message_queues[device_id] = queue
    else:
        self._message_queues.pop(device_id, None)
    return delivered
```

---

### Fase 15.2 — Cola Persistente en Redis (backend-api)

| # | Tarea | Estado | Ubicación |
|---|-------|--------|-----------|
| 15.2.1 | Crear `PendingCommandQueue` service con Redis LIST | ✅ Completado | `backend-api/app/services/pending_queue.py` |
| 15.2.2 | Reemplazar `_message_queues` (asyncio.Queue) por cola Redis | ✅ Completado | `backend-api/app/main.py` |
| 15.2.3 | Implementar patrón LMOVE (queue → inflight) con cleanup periódico | ✅ Completado | `backend-api/app/main.py` |
| 15.2.4 | Integrar cola Redis en `send_to_device()` y `connect()` | ✅ Completado | `backend-api/app/main.py` |
| 15.2.5 | Consumir `device:pending:banner:*` al reconectar (actual dead-end) | ✅ Completado | `backend-api/app/main.py` |

**Estructura en Redis:**

```
device:queue:{device_id}                   → LIST - comandos pendientes de enviar
device:queue:{device_id}:inflight          → LIST - enviados pero no confirmados
device:pending:sync:{device_id}            → STRING "true"/"false"
device:pending:reboot:{device_id}          → STRING - JSON último REINICIAR
```

**Diagrama de flujo:**

```
Comando llega
    │
    ▼
┌──────────────────────────────┐
│ 1. RPUSH device:queue:{id}   │ ◄── Redis (persistente, sobrevive crashes)
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 2. LPUSH → LMOVE a inflight         │ ◄── Transacción atómica
│    → send_json() vía WebSocket      │
└──────────────┬───────────────────────┘
               │
        ┌──────┴──────┐
        ▼              ▼
   ¿CONFIRMATION?   ¿Fallo/Timeout?
        │              │
        ▼              ▼
┌──────────────┐ ┌──────────────────────┐
│ LREM inflight│ │ LMOVE inflight→queue │ ◄── Rollback automático
│ ✓ Comando OK │ │ + cleanup periódico  │
└──────────────┘ └──────────────────────┘
```

**Detalle técnico 15.2.1 — PendingCommandQueue:**

```python
# backend-api/app/services/pending_queue.py
class PendingCommandQueue:
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def enqueue(self, device_id: str, message: dict) -> None:
        key = f"device:queue:{device_id}"
        await self.redis.rpush(key, json.dumps(message))
    
    async def dequeue(self, device_id: str) -> dict | None:
        key = f"device:queue:{device_id}"
        inflight_key = f"{key}:inflight"
        # LMOVE atómico: saca de queue y pasa a inflight
        data = await self.redis.lmove(key, inflight_key, "LEFT", "RIGHT")
        if data:
            return json.loads(data)
        return None
    
    async def confirm(self, device_id: str, message_id: str) -> None:
        # Eliminar de inflight (confirmado por el dispositivo)
        inflight_key = f"device:queue:{device_id}:inflight"
        await self.redis.lrem(inflight_key, 1, message_id)
    
    async def recover_inflight(self, device_id: str) -> int:
        """Mueve todos los inflight de vuelta a queue (en disconnect)."""
        key = f"device:queue:{device_id}"
        inflight_key = f"{key}:inflight"
        count = 0
        while await self.redis.llen(inflight_key) > 0:
            data = await self.redis.lmove(inflight_key, key, "LEFT", "RIGHT")
            if data:
                count += 1
        return count
    
    async def get_all_pending(self, device_id: str) -> list[dict]:
        key = f"device:queue:{device_id}"
        inflight_key = f"{key}:inflight"
        items = await self.redis.lrange(key, 0, -1)
        inflight = await self.redis.lrange(inflight_key, 0, -1)
        return [json.loads(i) for i in items] + [json.loads(i) for i in inflight]
```

**Detalle técnico 15.2.5 — Consumir pending banners al reconectar:**

```python
# En connect(), después del IDENTIFY exitoso:
# 1. Flush message_queues (actual)
# 2. NUEVO: procesar cola Redis
async def process_pending_queue(self, device_id, websocket):
    queue = PendingCommandQueue(redis)
    while True:
        msg = await queue.dequeue(device_id)
        if not msg:
            break
        try:
            await websocket.send_json(msg)
            await queue.confirm(device_id, json.dumps(msg))
        except Exception:
            # Re-encolar si falla
            await queue.enqueue(device_id, msg)
            break

# 3. NUEVO: consumir device:pending:banner:{device_id}
async def consume_pending_banners(self, device_id, websocket):
    key = f"device:pending:banner:{device_id}"
    data = await redis.get(key)
    if data:
        banner_info = json.loads(data)
        await websocket.send_json(banner_info)
        await redis.delete(key)

# 4. NUEVO: check pending_sync
async def check_pending_sync(self, device_id):
    key = f"device:pending:sync:{device_id}"
    pending = await redis.get(key)
    if pending == "true":
        await device_command_bus.publish_command(
            device_id=device_id,
            command="WIPE_AND_RESYNC",
            payload={}
        )
        await redis.delete(key)
```

---

### Fase 15.3 — Flag de Pendientes y Reinteligencia en IDENTIFY (backend-api)

| # | Tarea | Estado | Ubicación |
|---|-------|--------|-----------|
| 15.3.1 | Crear flag `device:pending:sync:{device_id}` en Redis al fallar envío de WIPE_AND_RESYNC | ⏳ Pendiente | `backend-api/app/main.py` |
| 15.3.2 | En `connect()`: al recibir IDENTIFY, verificar flags y disparar comandos pendientes | ⏳ Pendiente | `backend-api/app/main.py:1564-1566` |
| 15.3.3 | Setear flag `pending:reboot:{device_id}` al enviar REINICIAR sin confirmación | ⏳ Pendiente | `backend-api/app/main.py:1254-1316` |
| 15.3.4 | Cleanup periódico de flags huérfanos (más de 1 hora) | ⏳ Pendiente | `backend-api/app/main.py` |

**Flujo completo en IDENTIFY:**

```
luzapp conecta → envía IDENTIFY
                    │
                    ▼
          ┌─────────────────┐
          │ 1. Flush queue  │ ◄── message_queues (actual)
          └────────┬────────┘
                   ▼
          ┌──────────────────────┐
          │ 2. Consume pending   │ ◄── device:pending:banner:* (NUEVO)
          │    banners           │
          └────────┬────────────┘
                   ▼
          ┌──────────────────────┐
          │ 3. Check pending     │ ◄── device:pending:sync:{id} (NUEVO)
          │    sync flag         │ → Si true, auto-trigger WIPE_AND_RESYNC
          └────────┬────────────┘
                   ▼
          ┌──────────────────────┐
          │ 4. Check pending     │ ◄── device:pending:reboot:{id} (NUEVO)
          │    reboot flag       │ → Si existe, re-enviar REINICIAR
          └────────┬────────────┘
                   ▼
          ┌──────────────────────┐
          │ 5. Process Redis     │ ◄── device:queue:{id} (NUEVO)
          │    persistent queue  │ → Enviar todos los pendientes
          └──────────────────────┘
```

---

### Fase 15.4 — REINICIAR Robusto con Reintentos (backend-api)

| # | Tarea | Estado | Ubicación |
|---|-------|--------|-----------|
| 15.4.1 | Agregar reintentos automáticos para REINICIAR (máx 5, backoff 30s) | ⏳ Pendiente | `backend-api/app/main.py` |
| 15.4.2 | Guardar `device:pending:reboot:{device_id}` en Redis si falla el envío | ⏳ Pendiente | `backend-api/app/main.py:1254-1316` |
| 15.4.3 | Re-enviar REINICIAR automáticamente en IDENTIFY si flag existe | ⏳ Pendiente | `backend-api/app/main.py:connect()` |
| 15.4.4 | Limpiar flag cuando el dispositivo confirma COMPLETED | ⏳ Pendiente | `backend-api/app/main.py:process_sync_confirmation` |

**Detalle técnico 15.4.1 — Reintentos para REINICIAR:**

```python
REBOOT_RETRY_LIMIT = 5
REBOOT_RETRY_DELAY = 30  # segundos
reboot_retry_counters: dict[str, int] = {}

async def retry_reboot_with_device(device_id: str):
    count = reboot_retry_counters.get(device_id, 0)
    if count < REBOOT_RETRY_LIMIT:
        reboot_retry_counters[device_id] = count + 1
        await asyncio.sleep(REBOOT_RETRY_DELAY)
        # Re-enviar REINICIAR
        await device_command_bus.publish_command(
            device_id=device_id,
            command="REINICIAR",
            payload={}
        )
    else:
        reboot_retry_counters.pop(device_id, None)
        logger.error(f"Dispositivo {device_id} falló reinicio tras {REBOOT_RETRY_LIMIT} reintentos.")
```

---

### Fase 15.5 — Versión Objetivo (Estado vs Evento) — LARGO PLAZO

| # | Tarea | Estado | Ubicación |
|---|-------|--------|-----------|
| 15.5.1 | Guardar `device:target_version:{device_id}` en Redis con versión actual de banners | ⏳ Pendiente | `backend-api + backend-dashboard` |
| 15.5.2 | Enviar `target_version` en respuesta al IDENTIFY (IDENTIFY_ACK) | ⏳ Pendiente | `backend-api/app/main.py:connect()` |
| 15.5.3 | En luzapp: almacenar `local_version` y comparar contra `target_version` al reconectar | ⏳ Pendiente | `luzapp/ScanActivity.kt` |
| 15.5.4 | Si versiones difieren, luzapp solicita sync automáticamente | ⏳ Pendiente | `luzapp/ScanActivity.kt` |

**Concepto:**

```
En lugar de:  {"command": "WIPE_AND_RESYNC"}  ← evento
Usar:         {"target_version": 15}           ← estado

Flujo:
1. Servidor guarda: device:target_version:{id} = 15
2. IDENTIFY → servidor responde: {"type": "IDENTIFY_ACK", "target_version": 15}
3. luzapp compara: local_version(14) != target_version(15) → auto-sync
4. No importa si el comando se pierde — en la próxima reconexión se auto-corrige
```

---

**Nota sobre MQTT**: Se evaluó MQTT (Mosquitto) como alternativa y se descartó para esta fase por su complejidad operativa (nuevo broker, puertos, librería Android). Se reconsiderará en una actualización futura si la cola persistente Redis no es suficiente.

---

## Orden de Implementación (FASE 15)

La implementación se divide en **4 lotes** desplegables de forma independiente. Cada lote incluye pruebas unitarias + verificación manual antes de pasar al siguiente.

### Lote 1 — Fix Críticos + Salvaguardas inmediatas ✅ COMPLETADO

| # | Tarea | Archivo | Estado |
|---|-------|---------|:------:|
| L1.1 | Proteger bus listener: try/except en `_on_bus_command` + reconexión automática | `main.py:1923-1938, 1997-2005` | ✅ |
| L1.2 | Zombie socket → encola: quitar `raise`, always enqueue after disconnect | `main.py:1640-1657` | ✅ |
| L1.3 | Flush atómico: no popear hasta confirmar send, re-encolar si falla | `main.py:1714-1754` | ✅ |
| L1.4 | Command ID + dedup en luzapp: UUID por comando, HashSet últimos 20 IDs | `main.py:1642` + `ScanActivity.kt:767` | ✅ |
| L1.5 | Límite de cola: max 100 msg por dispositivo + TTL 24h por mensaje | `main.py:1668` + `pending_queue.py:30` | ✅ |
| L1.6 | Endpoint `GET /api/queue/health` para monitoreo en tiempo real | `main.py:~2360` | ✅ |

### Lote 2 — Cola Persistente en Redis ✅ COMPLETADO

| # | Tarea | Archivo | Estado |
|---|-------|---------|:------:|
| L2.1 | Crear `PendingCommandQueue` service con Redis LIST + LMOVE inflight | `services/pending_queue.py` | ✅ |
| L2.2 | Reemplazar `_message_queues` (asyncio.Queue) por cola Redis | `main.py` | ✅ |
| L2.3 | Integrar cola Redis en `send_to_device()` y `connect()` | `main.py` | ✅ |
| L2.4 | Consumir `device:pending:banner:*` al reconectar (actual dead-end) | `main.py` | ✅ |

### Lote 3 — Flags de Pendientes + Dead-Letter Queue ✅ COMPLETADO

| # | Tarea | Archivo | Estado |
|---|-------|---------|:------:|
| L3.1 | Flag `device:pending:sync:{id}` en Redis, setear al fallar WIPE_AND_RESYNC | `main.py:2195,2279,2313,2561` + `pending_queue.py:205` | ✅ |
| L3.2 | Flag `device:pending:reboot:{id}` para REINICIAR no confirmado | `main.py:1331,1347,2585` + `pending_queue.py:219` | ✅ |
| L3.3 | En `connect()`: verificar flags al recibir IDENTIFY y disparar comandos | `main.py:_flush_all_queues():1736-1759` | ✅ |
| L3.4 | Dead-letter queue: máximo 5 reintentos por mensaje, luego a DLQ | `pending_queue.py:262-324` (flush_all_to_device + _move_to_dlq) | ✅ |

### Lote 4 — REINICIAR Robusto + Reconciliación ✅ COMPLETADO

| # | Tarea | Archivo | Estado |
|---|-------|---------|:------:|
| L4.1 | Reintentos automáticos REINICIAR (máx 5, backoff 30s) | `main.py:2565-2586` (retry_reboot_with_device) | ✅ |
| L4.2 | Job de reconciliación periódico (30 min): verificar colas vs online, recuperar inflight, cleanup DLQ y flags | `main.py:1976-1985` (_reconciliation_loop cada 1800s) + `main.py:1940-1974` (_reconcile_all_queues) | ✅ |
| L4.3 | Cleanup de flags huérfanos y DLQ antigua (> 24h) | `pending_queue.py:343-397` (cleanup_old_dlq + cleanup_orphan_flags) | ✅ |

### Fase 15.5 — Versión Objetivo (PENDIENTE, no incluida en lotes actuales)

Se deja para después por requerir cambios en backend-dashboard + luzapp. No es crítica para la entrega de comandos.

---

## FASE 17: Cola de Comandos — Notificaciones y Visibilidad en Dashboard

*Prioridad: Alta | Objetivo: Dar visibilidad al dashboard del estado de la cola de comandos en Redis, diferenciando comandos encolados de fallos reales, y cerrando el ciclo de notificación cuando la cola entrega exitosamente.*

### Problema Raíz

El dashboard no tiene visibilidad de la cola Redis en backend-api:

- Cuando un sync falla por timeout, se reporta `FAILED` aunque el comando se haya encolado exitosamente
- El usuario reintenta sin saber que el comando ya está pendiente
- Cuando la cola eventualmente entrega el comando, el dashboard nunca se entera
- No hay forma de consultar cuántos comandos están encolados para un dispositivo

### Item 1: QUEUED vs FAILED — Diferenciar estado en respuesta de sync

**Descripción**: Cuando el dispositivo está offline pero el comando se encola exitosamente, reportar `"QUEUED"` en vez de `"TIMEOUT"/"SEND_FAILED"`. Crear notificación `COMANDO_ENCOLADO` en lugar de `SYNC_FAILED`.

| # | Archivo | Cambio | Esfuerzo |
|---|---------|--------|----------|
| 17.1.1 | `backend-api/app/main.py` `orchestrate_forced_sync_sequential` | Timeout/SEND_FAILED → `set_pending_sync()` exitoso → detail `status: "QUEUED"`, `queued: true`. Contador `queued` separado | ✅ |
| 17.1.2 | `backend-api/app/main.py` `_run_force_sync_job` | Forwardear `queued` del resultado al job state | ✅ |
| 17.1.3 | `backend-api/app/main.py` nueva función `notify_dashboard_sync_queued` | `POST /api/sync-queued` al dashboard | ✅ |
| 17.1.4 | `backend-dashboard/app/routes/notificaciones.py` | Nuevo `POST /api/sync-queued` → crea `COMANDO_ENCOLADO`, dedup 120s | ✅ |
| 17.1.5 | `backend-dashboard/app/services/sync_service.py` | Leer `queued` del backend-api, no contar como failed | ✅ |
| 17.1.6 | `backend-dashboard/app/services/sync_service.py` GET job | Incluir `queued` en response del job | ✅ |
| 17.1.7 | `dashboard/screens/DashboardScreen.tsx` | `SyncServerProgress` type + `queued`. Barra naranja, toast queued | ✅ |
| 17.1.8 | `dashboard/services/notificacionesPresentation.ts` | Case `COMANDO_ENCOLADO` → severity `info`, título "Comando encolado" | ✅ |

### Item 2: Endpoint de estado de cola (`/queue-status`)

**Descripción**: Permitir que el dashboard consulte el estado de la cola Redis de un dispositivo (pendientes, inflight, DLQ, flags).

| # | Archivo | Cambio | Estado |
|---|---------|--------|:------:|
| 17.2.1 | `backend-api/app/main.py` | Nuevo `GET /api/queue-status/{device_id}` → `{ device_id, pending, inflight, total, pending_sync, pending_reboot }`. Auth via API key | ✅ |
| 17.2.2 | `backend-dashboard/app/routes/monitoreo/sync.py` | Nuevo `GET /api/monitoreo/cola/{device_id}` → proxy a backend-api | ✅ |
| 17.2.3 | `dashboard/components/ServerDashboard.tsx` | En cada dispositivo, badge "N pendientes" con tooltip. Naranja si > 0, gris si vacío | ⏳ Pendiente |

### Item 3: Notificar entrega exitosa desde la cola

**Descripción**: Cuando la cola Redis entrega el comando al dispositivo y este confirma SUCCESS, notificar al dashboard para crear `SINCRONIZACION_COMPLETADA`.

| # | Archivo | Cambio | Estado |
|---|---------|--------|:------:|
| 17.3.1 | `backend-api/app/services/pending_queue.py` | Nuevos métodos: `set_delivery_pending(device_id)` + `check_delivery_pending(device_id)`. Redis key `device:delivery_pending:{id}`, TTL 300s | ✅ |
| 17.3.2 | `backend-api/app/main.py` `_flush_all_queues` | Después de `check_pending_sync() == True` → `set_delivery_pending()`. En `flush_all_to_device`, al dequeuear WIPE_AND_RESYNC → `set_delivery_pending()` | ✅ |
| 17.3.3 | `backend-api/app/main.py` `process_sync_confirmation` | Cuando WIPE_AND_RESYNC SUCCESS → `check_delivery_pending()` → si True → `notify_dashboard_sync_delivered()` | ✅ |
| 17.3.4 | `backend-api/app/main.py` nueva función `notify_dashboard_sync_delivered` | `POST /api/sync-delivered` al dashboard con `{ device_id, status: "SUCCESS" }` | ✅ |
| 17.3.5 | `backend-dashboard/app/routes/notificaciones.py` | Nuevo `POST /api/sync-delivered` → crea `SINCRONIZACION_COMPLETADA` | ✅ |
| 17.3.6 | `dashboard/services/notificacionesPresentation.ts` | Case `SINCRONIZACION_COMPLETADA` → severity `success`, título "Sincronización completada" | ✅ |

### Orden de implementación sugerido

```
Item 1 (QUEUED vs FAILED)   → desplegable independiente, bajo riesgo
Item 2 (queue-status)        → desplegable independiente, bajo riesgo
Item 3 (delivery notify)     → desplegable independiente, requiere Item 1
```

Cada item es desplegable por separado. Item 1 y 2 no tienen dependencias entre sí.

### Archivos a modificar (resumen)

| Archivo | Items | Cambios |
|---------|-------|---------|
| `backend-api/app/main.py` | 1, 2, 3 | 7 cambios (orchestrate, _run_job, notify_queued, queue-status endpoint, _flush_all_queues, process_sync_confirmation, notify_delivered) |
| `backend-api/app/services/pending_queue.py` | 3 | 1 cambio (delivery_pending methods) |
| `backend-dashboard/app/routes/notificaciones.py` | 1, 3 | 2 endpoints nuevos (sync-queued, sync-delivered) |
| `backend-dashboard/app/routes/monitoreo.py` | 1, 2 | 1 endpoint nuevo (cola-status), 2 cambios en sync job |
| `dashboard/screens/DashboardScreen.tsx` | 1 | SyncServerProgress type + UI rendering |
| `dashboard/components/ServerDashboard.tsx` | 2 | Badge de cola en dispositivo |
| `dashboard/services/notificacionesPresentation.ts` | 1, 3 | 2 nuevos cases |
| `PLAN_MEJORAS.md` | - | Documentación |

---

## FASE 18: Bots de Mantenimiento y Limpieza de Datos

*Prioridad: Media | Objetivo: Evitar crecimiento infinito de BD, disco y Redis.*

### Problema Raíz

El sistema no tiene **ningún** job de limpieza automática. Datos que crecen sin control:

| Dato | Crecimiento | Riesgo |
|------|-------------|--------|
| `DispositivoSesion` | ~8,000 filas/día (3M/año) | Queries lentas en auditoría |
| `Notificacion` + `NotificacionLeida` | ~100 filas/día | BD crece sin límite |
| `static/banners/` archivos huérfanos | Archivos de uploads fallidos, renombrados, banners eliminados | Disco lleno |
| `device:state:*` en Redis | Dispositivos dados de baja nunca se limpian | Redis retiene datos stale |
| Banners en servidores API (archivos huérfanos) | Archivos no referenciados en cada servidor | Disco lleno en servidores remotos |

---

### Bot 1: `limpiar_sesiones` ✅ COMPLETADO

| Propiedad | Valor |
|-----------|-------|
| **Tabla** | `DispositivoSesion` |
| **Acción** | `DELETE WHERE fecha_fin < DATEADD(DAY, -90, GETDATE())` |
| **Retención** | 90 días |
| **Frecuencia** | Cada 15 días |
| **Log** | `"cleanup_old_sessions: deleted 8421 rows"` |
| **Ubicación** | `backend-dashboard/app/cleanup_service.py` + `scheduler.py` |

### Bot 2: `limpiar_notificaciones` ✅ COMPLETADO

| Propiedad | Valor |
|-----------|-------|
| **Tablas** | `Notificacion` + `NotificacionLeida` (cascada) |
| **Acción** | `DELETE WHERE fecha_creacion < DATEADD(DAY, -15, GETDATE())` |
| **Retención** | 15 días |
| **Frecuencia** | Cada 15 días (mismo job que sesiones) |
| **Log** | `"cleanup_old_notifications: deleted 340 rows"` |
| **Ubicación** | `backend-dashboard/app/cleanup_service.py` + `scheduler.py` |

### Bot 3: `limpiar_archivos` (dashboard) ✅ COMPLETADO

| Propiedad | Valor |
|-----------|-------|
| **Directorio** | `backend-dashboard/static/banners/` |
| **Acción** | `os.listdir()` → cruzar contra `SELECT Url, ThumbnailUrl FROM Publicidad` → `os.remove()` no referenciados |
| **Frecuencia** | Cada 24h |
| **Log** | `"cleanup_orphan_files: removed 12 files (85.3 MB)"` |
| **Ubicación** | `backend-dashboard/app/cleanup_service.py` + `scheduler.py` |

### Bot 4: `limpiar_redis_stale` ✅ COMPLETADO

| Propiedad | Valor |
|-----------|-------|
| **Target** | `device:state:{device_id}`, `devices:all`, `device:pending:banner:{device_id}` |
| **Acción** | Agregar `EXPIRE key 172800` (48h TTL) al crear/actualizar `device:state:*`. Renovar en cada heartbeat. Agregar TTL a `device:pending:banner:*`. |
| **Frecuencia** | Auto-gestionado por TTL de Redis (sin scheduler) |
| **Log** | No aplica (automático) |
| **Ubicación** | `backend-api/app/main.py` (heartbeat/connect) + `backend-dashboard/app/services/device_service.py` |

### Bot 5: `limpiar_banners_api` (backend-api) ✅ COMPLETADO

| Propiedad | Valor |
|-----------|-------|
| **Directorio** | Carpeta local de banners en cada servidor backend-api |
| **Acción** | `os.listdir()` → cruzar contra `SELECT Url FROM Publicidad` → `os.remove()` no referenciados |
| **Frecuencia** | Cada 24h |
| **Ubicación** | `backend-api/app/cleanup_service.py` + scheduler en `main.py` |

---

## Prioridades de Implementación (Pendientes)

| Prioridad | Item | Fase | Dónde | Dependencias |
|-----------|------|------|-------|-------------|
| 🟢 **1** | Badge "N pendientes" en ServerDashboard | FASE 17.2.3 | dashboard/components/ServerDashboard.tsx | ✅ |
| 🟢 **2** | Bot `limpiar_sesiones` (90 días, c/15d) | FASE 18 | backend-dashboard | ✅ |
| 🟢 **3** | Bot `limpiar_notificaciones` (15 días, c/15d) | FASE 18 | backend-dashboard | ✅ |
| 🟢 **4** | Bot `limpiar_archivos` (c/24h) | FASE 18 | backend-dashboard | ✅ |
| 🟢 **5** | Bot `limpiar_redis_stale` (TTL 48h) | FASE 18 | backend-api + dashboard | ✅ |
| 🟢 **6** | Bot `limpiar_banners_api` (c/24h) | FASE 18 | backend-api | ✅ |
| 🟢 **7** | Control vigencia luzapp (S2, S3) | FASE 7.4-7.5 | luzapp + backend-api | ✅ |
| 🟢 **8** | Backups SQL Server (manual) | FASE 5.1 | servidor | — |
| 🟢 **9** | Docker multi-stage build | FASE 5.3 | Dockerfile | ✅ |
| ⚪ **10** | Versión Objetivo (FASE 15.5) | FASE 15 Lote 5 | backend-api + luzapp | largo plazo |

---

## Resumen de Progreso Total (Todas las Fases)

| Grupo | Fases | Completado | Pendiente |
|-------|-------|------------|-----------|
| Originales | 1-10 | 39/40 (98%) | 1/40 |
| Refactor Backend | 11 | 3/3 ✅ (100%) | 0/3 |
| Frontend Base | 12 | 2/2 ✅ (100%) | 0/2 |
| UX/UI | 13-14 | 5/5 ✅ (100%) | 0/5 |
| Blindaje WebSocket | 15 | 17/17 ✅ (100%) | 0/17 |
| Cola Dashboard | 17 | 17/17 ✅ (100%) | 0/17 |
| Bots Mantenimiento | 18 | 5/5 ✅ (100%) | 0/5 |
| **TOTAL** | **1-18** | **88/89 (99%)** | **1/89** |
