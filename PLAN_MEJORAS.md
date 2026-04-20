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
| FASE 6 (Cambio Asignación) | 1/1 ✅ | 0/1 |
| FASE 7 (Fix Asignaciones + Vigencia) | 2/5 | 3/5 |
| FASE 8 (Background Monitoring Sesiones) | 4/4 ✅ | 0/4 |
| FASE 9 (Thumbnails Videos) | 6/6 ✅ | 0/6 |
| FASE 10 (Limpieza Columnas) | 5/5 ✅ | 0/5 |

**Total: 16/27 completados (59%)**

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
| 7.4 | Cache cleanup (S2) - eliminar banners vencidos | ⏳ Pendiente | luzapp/BannerRepository.kt |
| 7.5 | WebSocket push (S3) - invalidación inmediata | ⏳ Pendiente | backend-api + luzapp |

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

**Total: 25/28 completados (89%)**

- FASE 1-4: ✅ Completas
- FASE 5: ⏳ Pendiente (2 tareas manual en servidor)
- FASE 6: ✅ Completada
- FASE 7: 🔄 Parcial (40% - 2/5, tareas luzapp pendientes)
- FASE 8: ✅ Completada
- FASE 9: ✅ Completada
- FASE 10: ✅ Completada

---

## FASE 11: Refactorización y Estabilidad (Backend)

*Prioridad: Crítica | Objetivo: Eliminar deuda técnica y mejorar mantenibilidad.*

### 11.1 Refactorización de `monitoreo.py` ⏳ PENDIENTE
- **Descripción**: Dividir `monitoreo.py` en módulos independientes:
  - `servers.py` - Gestión de servidores secundarios
  - `devices.py` - Gestión de dispositivos
  - `sync.py` - Lógica de sincronización
- **Impacto**: Estructura modular y mantenible
- **Complejidad**: Media

### 11.2 Implementación de `sync_service.py` ⏳ PENDIENTE
- **Descripción**: Mover lógica de negocio de rutas a servicios
- **Impacto**: Permite pruebas unitarias y desacopla la API
- **Complejidad**: Media

### 11.3 Manejador Global de Excepciones ⏳ PENDIENTE
- **Descripción**: Reemplazar `try-except: pass` por respuestas estandarizadas
- **Impacto**: Frontend recibe errores claros
- **Complejidad**: Baja

---

## FASE 12: Infraestructura de Navegación y Estado (Frontend)

*Prioridad: Alta | Objetivo: Crear una base sólida para la expansión de la UI.*

### 12.1 Integración de `react-router-dom` ⏳ PENDIENTE
- **Descripción**: Migrar estado `currentScreen` a rutas reales
- **Impacto**: Navegación fluida y enlaces directos
- **Complejidad**: Media
- **Dependencias**: react-router-dom

### 12.2 Implementación de `Zustand` ⏳ PENDIENTE
- **Descripción**: Centralizar estado de sesión y configuraciones
- **Impacto**: Elimina prop-drilling y optimiza flujo de datos
- **Complejidad**: Media
- **Dependencias**: zustand

---

## FASE 13: Experiencia de Usuario y Funcionalidades (UX/UI)

*Prioridad: Media | Objetivo: Profesionalizar la interacción con el usuario.*

### 13.1 Sistema de Feedback (Toasts y Modales) ⏳ PENDIENTE
- **Descripción**: Implementar avisos descriptivos y confirmaciones
- **Impacto**: Reduce errores accidentales del usuario
- **Complejidad**: Baja

### 13.2 Vista de Auditoría Detallada ⏳ PENDIENTE
- **Descripción**: Crear pantalla de logs con filtros avanzados
- **Impacto**: Aprovecha robustez del backend (FASE 11)
- **Complejidad**: Media

### 13.3 Visualización de Datos (`Recharts`) ⏳ PENDIENTE
- **Descripción**: Implementar gráficas de almacenamiento y uptime
- **Impacto**: Transforma datos crudos en información visual
- **Complejidad**: Media
- **Dependencias**: recharts

---

## FASE 14: Pulido Visual y Estética (Polishing)

*Prioridad: Baja | Objetivo: Lograr un acabado de producto final.*

### 14.1 Sistemas de Carga (Skeleton Screens) ⏳ PENDIENTE
- **Descripción**: Añadir estados de carga visuales
- **Impacto**: Mejora la percepción de velocidad
- **Complejidad**: Baja

### 14.2 Selector de Tema (Dark/Light Mode) ⏳ PENDIENTE
- **Descripción**: Implementar persistencia con `localStorage`
- **Impacto**: Mejora el confort visual del operador
- **Complejidad**: Baja

---

## Resumen de Progreso Total (Todas las Fases)

| Grupo | Fases | Completado | Pendiente |
|-------|-------|------------|-----------|
| Originales | 1-10 | 25/28 (89%) | 5/28 |
| Nuevas | 11-14 | 0/11 (0%) | 11/11 |
| **TOTAL** | **1-14** | **25/39 (64%)** | **14/39**
