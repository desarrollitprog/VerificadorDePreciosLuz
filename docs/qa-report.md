# Informe de QA Senior – Verificador de Precios Luz

**Fecha:** 2026-04-11  
**Revisor:** QA Senior (Automated Audit)  
**Repositorio:** `Tavorl25/VerificadorDePreciosLuz`  
**Alcance:** backend-api, backend-dashboard, dashboard (frontend React/TypeScript), luzapp (Android), docker-compose

---

## Resumen Ejecutivo

El sistema está compuesto por cuatro capas: una API REST + WebSocket principal (`backend-api`), un backend de administración (`backend-dashboard`), un frontend web (`dashboard`) y una app Android (`luzapp`). El análisis revela **errores críticos de seguridad, deficiencias de arquitectura, problemas de lógica de negocio y ausencia total de pruebas automatizadas**, que en conjunto representan un riesgo alto para la estabilidad y confidencialidad del sistema en producción.

---

## Tabla de Contenidos

1. [Seguridad](#1-seguridad)
2. [Arquitectura](#2-arquitectura)
3. [Lógica de Negocio](#3-lógica-de-negocio)
4. [Diseño y Calidad de Código](#4-diseño-y-calidad-de-código)
5. [Base de Datos y Persistencia](#5-base-de-datos-y-persistencia)
6. [Gestión de Configuración y Secretos](#6-gestión-de-configuración-y-secretos)
7. [Pruebas y Observabilidad](#7-pruebas-y-observabilidad)
8. [Resumen de Hallazgos por Severidad](#8-resumen-de-hallazgos-por-severidad)

---

## 1. Seguridad

### 🔴 CRÍTICO — Endpoint `/backup` sin autenticación

**Archivo:** `backend-api/app/main.py`, línea 611  
**Descripción:** El endpoint `GET /backup` expone la totalidad de los datos de productos, precios, ofertas, impuestos, códigos de barras asociados y tasas de IVA sin ningún mecanismo de autenticación ni autorización. Cualquier usuario o bot en la red puede obtener un volcado completo de la base de datos transaccional.

```python
@app.get("/backup")
async def backup_data(
    section: str = "productos",
    offset: int = 0,
    limit: int = 2000,
    ...
```

**Impacto:** Exfiltración masiva de datos de negocio (precios, estructura de impuestos, inventario completo).  
**Recomendación:** Proteger el endpoint con al menos un API key en el header (`X-API-KEY`) o, preferiblemente, con JWT de la misma forma que el backend-dashboard protege sus rutas internas.

---

### 🔴 CRÍTICO — Endpoints de control de dispositivos sin autenticación

**Archivo:** `backend-api/app/main.py`  
**Afectados:**
- `POST /api/fuerza-sync` (línea 996)
- `GET /api/fuerza-sync/{job_id}` (línea 1187)
- `POST /api/comandos/{device_id}` (línea 1055)
- `POST /api/playback-status` (línea 1207)
- `POST /api/playing-now` (línea 1233)
- `GET /api/device-playing/{device_id}` (línea 1259)
- `POST /api/debug-bcv` (línea 82)

**Descripción:** Cualquier atacante puede forzar sincronizaciones en todos los dispositivos, reiniciarlos de forma remota, inyectar eventos de "reproducción" falsos y consultar qué contenido reproduce cada dispositivo sin ninguna credencial.  
**Recomendación:** Proteger todos estos endpoints con el mismo esquema de autenticación que usa `backend-dashboard` (JWT o API key). En el caso de `debug-bcv`, considerar eliminarlo en producción o filtrar por IP de origen.

---

### 🔴 CRÍTICO — Contraseña por defecto de SQL Server en docker-compose

**Archivo:** `docker-compose.yml`, líneas 8-9  

```yaml
- MSSQL_SA_PASSWORD=${SA_PASSWORD:-Dit12345*}
```

El valor por defecto `Dit12345*` quedará activo en cualquier entorno donde la variable `SA_PASSWORD` no esté definida explícitamente (CI, staging, despliegue rápido). Esto expone la instancia SQL Server con credenciales conocidas públicamente desde el repositorio.  
**Recomendación:** Eliminar el valor por defecto (`${SA_PASSWORD}` sin el fallback) y asegurarse de que el `.env` contenga contraseñas generadas aleatoriamente. Agregar al `.gitignore` cualquier archivo `.env.*`.

---

### 🔴 CRÍTICO — APK binaria comprometida en el repositorio

**Archivo:** `luzapp.apk` (raíz del repositorio)  
**Descripción:** Un binario compilado no debe estar en el repositorio de fuentes. Quien tenga acceso al repositorio puede ingeniería inversa la APK para extraer URLs de API, lógica de negocio, o credenciales hardcodeadas. Además, el binario puede estar desactualizado respecto al código fuente, generando confusión.  
**Recomendación:** Eliminar `luzapp.apk` del repositorio, agregarlo a `.gitignore` y distribuir únicamente a través del pipeline de CI/CD o una plataforma MDM.

---

### 🟠 ALTO — Almacenamiento de desafíos 2FA en memoria del proceso

**Archivo:** `backend-dashboard/app/routes/auth.py`, línea 46  

```python
PENDING_2FA: dict[str, dict[str, Any]] = {}
```

**Descripción:** Los tokens temporales 2FA se almacenan en el diccionario en memoria del proceso. Si el servidor se reinicia (lo cual ocurre en cada despliegue) todos los códigos OTP activos quedan invalidados, dejando al usuario sin la posibilidad de completar su login. En un entorno multi-worker (Gunicorn + varios workers) distintos workers no comparten el mismo diccionario, haciendo que la verificación falle aleatoriamente.  
**Recomendación:** Almacenar los desafíos 2FA en Redis con TTL, igual que se hace con el `CommandAcker`.

---

### 🟠 ALTO — Sin rate limiting en el endpoint de login

**Archivo:** `backend-dashboard/app/routes/auth.py`, línea 164  
**Descripción:** El endpoint `POST /auth/login` no tiene ningún mecanismo de rate limiting. Un atacante puede realizar ataques de fuerza bruta o credential stuffing sin ninguna fricción. El límite de 5 intentos para 2FA (`OTP_MAX_ATTEMPTS`) sólo aplica después de haber superado la primera fase de autenticación.  
**Recomendación:** Añadir rate limiting por IP usando un middleware (`slowapi`, `fastapi-limiter`) con Redis como backend para consistencia entre workers.

---

### 🟠 ALTO — `SECRET_KEY` del JWT sin valor por defecto pero vulnerable a rotación

**Archivo:** `backend-dashboard/app/utils/security.py`, línea 16  
**Descripción:** El `SECRET_KEY` se carga correctamente del entorno, pero no existe ningún mecanismo de rotación de claves ni revocación de tokens individuales. Un token robado es válido durante `ACCESS_TOKEN_EXPIRE_MINUTES` (60 min por defecto) sin posibilidad de invalidarlo.  
**Recomendación:** Implementar una lista negra de JTI (JWT ID) en Redis, o usar tokens de corta duración con refresh tokens que puedan ser revocados.

---

### 🟠 ALTO — Comunicación inter-servicio en HTTP plano

**Archivo:** `backend-dashboard/app/routes/monitoreo.py`, línea 55  
**Archivo:** `backend-api/app/main.py`, línea 2031  

```python
url = f"http://{ip}:8000/devices/status"
notify_endpoint = f"{dashboard_url.rstrip('/')}/api/sync-status"
```

Las llamadas entre `backend-api` y `backend-dashboard` se realizan en HTTP sin cifrado, exponiendo los datos en redes internas y siendo susceptibles a ataques man-in-the-middle.  
**Recomendación:** Usar HTTPS entre servicios, o al menos comunicación dentro de la red Docker con el proxy nginx como punto de terminación TLS.

---

### 🟡 MEDIO — `print()` expone detalles de tokens en logs de producción

**Archivo:** `backend-dashboard/app/utils/security.py`, línea 58  

```python
print(f"Token error: {e}")
```

Los errores de validación de JWT se imprimen en stdout (no en el logger configurado). En algunas plataformas esto puede exponer información de tokens inválidos en logs accesibles.  
**Recomendación:** Reemplazar `print` por `logger.warning` con el logger de uvicorn.

---

## 2. Arquitectura

### 🔴 CRÍTICO — `consultas.py` llama funciones no importadas de `main.py`

**Archivo:** `backend-api/app/routes/consultas.py`, líneas 35-36  

```python
tasa_impuesto = await buscar_tasa_impuesto(db, db_erp, p.IdProducto, precio)
responses.append(armar_respuesta(p, precio, oferta, detalle, tasa_impuesto))
```

Las funciones `buscar_tasa_impuesto` y `armar_respuesta` están definidas en `main.py` pero **no son importadas** en `consultas.py`. Esto produce un `NameError` en tiempo de ejecución cada vez que se invoca el endpoint `GET /productos`. El código es funcionalmente roto.  
**Recomendación:** Mover `buscar_tasa_impuesto` y `armar_respuesta` a un módulo de servicio compartido (`app/services/precio_service.py`) e importarlo tanto en `main.py` como en `consultas.py`.

---

### 🟠 ALTO — `main.py` de backend-api tiene 2173 líneas (violación de SRP)

**Archivo:** `backend-api/app/main.py`  
**Descripción:** Un único archivo contiene: configuración de la app, definición de la clase `TabletWebSocketManager`, lógica de websocket, lógica de banners, lógica de sincronización forzada, lógica de comandos a dispositivos, funciones de consulta a BD, funciones de serialización de respuestas, funciones de notificación al dashboard, y orquestación de reintentos. Esto viola el principio de responsabilidad única y hace el código extremadamente difícil de mantener, probar y depurar.  
**Recomendación:** Separar en módulos: `services/ws_manager.py`, `services/banner_service.py`, `services/sync_service.py`, `services/command_service.py`, `routes/productos.py`, etc.

---

### 🟠 ALTO — Conexiones a BD se crean en tiempo de importación del módulo

**Archivo:** `backend-api/app/database.py`, líneas 49-68, 88-110, 125-143  
**Descripción:** Las tres engines de SQLAlchemy se instancian en el cuerpo del módulo (fuera de cualquier función), y las variables de entorno se leen con `_required()` durante la importación. Esto significa que:
1. Si alguna variable de entorno está ausente, la aplicación falla con un `RuntimeError` al importar el módulo, sin un mensaje de error claro.
2. Los tests unitarios son imposibles sin mockear variables de entorno globales.
3. El módulo `database.py` reimporta `create_async_engine` y `AsyncSession` en la línea 97, que ya fueron importados en la línea 2.

**Recomendación:** Usar el patrón de *lazy initialization* o el `lifespan` de FastAPI para crear las engines solo en el momento de iniciar la aplicación.

---

### 🟠 ALTO — `@app.on_event("startup")` y `@app.on_event("shutdown")` deprecados

**Archivo:** `backend-api/app/main.py`, líneas 291, 331  
**Descripción:** FastAPI marcó `@app.on_event` como deprecado en favor del patrón `lifespan` con `asynccontextmanager`. El código actual usa eventos deprecados que serán removidos en futuras versiones de FastAPI.  
**Recomendación:** Migrar a:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown

app = FastAPI(lifespan=lifespan)
```

---

### 🟡 MEDIO — Estado global mutable en variables de módulo

**Archivo:** `backend-api/app/main.py`, líneas 61-63, 890-895, 1051-1052, 1294-1295  

```python
device_state_store: DeviceStateStore | None = None
FORCE_SYNC_JOBS: dict[str, dict[str, Any]] = {}
command_ack_waiters: dict[str, asyncio.Event] = {}
sync_ack_waiters: dict[str, asyncio.Event] = {}
```

El uso extensivo de `global` para actualizar estado del proceso es frágil en entornos multi-worker. Si se escala horizontalmente con Gunicorn + múltiples workers (sin sticky sessions), los dictionaries locales se des-sincronizan: un worker que envía un comando puede no ser el mismo que recibe la confirmación.  
**Recomendación:** Ya existe el `CommandAcker` con Redis para las confirmaciones. Migrar completamente los dictionaries locales (`command_ack_waiters`, `sync_ack_waiters`, `FORCE_SYNC_JOBS`) a Redis.

---

### 🟡 MEDIO — `schedule_banner_notification` bloquea la coroutine por horas

**Archivo:** `backend-api/app/main.py`, línea 243  

```python
await asyncio.sleep(delay_inicio)  # puede ser horas o días
```

La función `schedule_banner_notification` hace `await asyncio.sleep(delay_inicio)` donde `delay_inicio` puede ser de horas o días. Aunque no bloquea el event loop (es `asyncio.sleep`), la tarea persiste en memoria hasta el próximo reinicio. Si el servidor se reinicia, la notificación programada se pierde. Además, no existe ninguna forma de cancelar individualmente una notificación programada.  
**Recomendación:** Usar un scheduler externo (ej. `APScheduler` con backend Redis, o Celery Beat) en lugar de `asyncio.sleep` de larga duración.

---

### 🟡 MEDIO — `_safe_disconnect` y `disconnect` duplican lógica

**Archivo:** `backend-api/app/main.py`, líneas 1451 y 1559  
**Descripción:** Ambos métodos realizan las mismas operaciones (cancelar ping, limpiar `device_map`, marcar offline en Redis, cancelar cola). La duplicación puede llevar a que futuras correcciones se apliquen sólo en una rama.  
**Recomendación:** Extraer la lógica común a un método privado e invocarla desde ambos puntos de entrada.

---

### 🟡 MEDIO — `_cleanup_old_queues` usa variable `cleaned` incorrectamente

**Archivo:** `backend-api/app/main.py`, línea 1653  
**Descripción:** La variable `cleaned` se inicializa fuera del bucle `for device_id`, pero se usa tanto para contar mensajes de dispositivos desconectados como de dispositivos conectados. Cuando el log imprime `f"[WS] {cleaned} mensajes antiguos limpiados de cola {device_id}"` (línea 1654), el valor de `cleaned` puede incluir conteos de iteraciones anteriores del bucle, dando un número incorrecto.

---

## 3. Lógica de Negocio

### 🟠 ALTO — `has_more` en `/backup` da falso positivo

**Archivo:** `backend-api/app/main.py`, línea 752  

```python
has_more = count >= limit
```

Si la base de datos contiene exactamente `limit` registros, la respuesta indicará `has_more=True` y el cliente enviará otra petición que devolverá una página vacía. Si `limit` se fija en 5000 y la BD tiene exactamente 5000 productos, se genera una petición extra innecesaria. En sistemas con paginación crítica (sincronización de la app Android) esto puede generar bucles o estados inconsistentes.  
**Recomendación:** Hacer una consulta con `limit + 1` y evaluar si el resultado supera `limit`:

```python
rows = (await db.execute(stmt.limit(limit + 1))).scalars().all()
has_more = len(rows) > limit
rows = rows[:limit]
```

---

### 🟠 ALTO — `notify_dashboard_banner_finalizado` dispara un `retry_sync_with_device` incorrectamente

**Archivo:** `backend-api/app/main.py`, línea 2079  

```python
async def notify_dashboard_banner_finalizado(device_id: str, banner_id: int | None = None):
    ...
    asyncio.create_task(retry_sync_with_device(device_id))
```

Cuando un banner **finaliza** se lanza automáticamente un `WIPE_AND_RESYNC` al dispositivo. Esto fuerza una sincronización completa (borrar y recargar datos) por el simple hecho de que un banner terminó su periodo de exhibición. Esta operación es costosa e innecesaria, y puede interrumpir la operación normal del kiosk.  
**Recomendación:** Eliminar la llamada a `retry_sync_with_device` dentro de `notify_dashboard_banner_finalizado`.

---

### 🟠 ALTO — Zona horaria inconsistente en consultas de ofertas vigentes

**Archivo:** `backend-api/app/main.py`, líneas 864 y 875  

```python
now = datetime.now()  # hora LOCAL del servidor sin zona horaria
detalle = await buscar_detalle_oferta_vigente(db, precio, now)
```

La función `get_venezuela_now()` (línea 26) devuelve la hora de Venezuela (UTC-4) con información de zona horaria. Sin embargo, en el endpoint `GET /consultar/{codigo_barras}`, se usa `datetime.now()` (hora local del servidor, sin zona horaria). Si el servidor está en una zona diferente (ej. UTC), las ofertas con fechas de vigencia ajustadas a Venezuela aparecerán activas o inactivas incorrectamente.  
**Recomendación:** Reemplazar `datetime.now()` por `get_venezuela_now().replace(tzinfo=None)` o unificar toda la lógica de fechas con UTC.

---

### 🟡 MEDIO — Loop de `schedule_banner_notification` no maneja el caso `delay_inicio <= 0`

**Archivo:** `backend-api/app/main.py`, línea 241  

```python
if delay_inicio > 0:
    await asyncio.sleep(delay_inicio)
    ...
```

Si `delay_inicio <= 0` (banner ya comenzó), no se envía ninguna notificación de inicio. Sin embargo, el banner puede estar activo en ese momento y los dispositivos no recibirán la señal de inicio si la reconexión ocurre después del momento de inicio.  
**Recomendación:** Si `delay_inicio <= 0`, enviar la notificación inmediatamente.

---

### 🟡 MEDIO — `notified_banners_start` y `notified_banners_end` nunca se limpian

**Archivo:** `backend-api/app/main.py`, líneas 118-119  

```python
notified_banners_start: set[int] = set()
notified_banners_end: set[int] = set()
```

Estos conjuntos crecen indefinidamente durante la vida del proceso. En un servidor de larga duración con muchos banners rotativos, esto representa un memory leak menor pero constante.  
**Recomendación:** Usar un `TTLCache` o limpiar periódicamente los IDs de banners expirados.

---

### 🟡 MEDIO — `FORCE_SYNC_JOBS` nunca se limpia

**Archivo:** `backend-api/app/main.py`, línea 891  

```python
FORCE_SYNC_JOBS: dict[str, dict[str, Any]] = {}
```

Cada ejecución de `POST /api/fuerza-sync?async_mode=true` agrega una entrada al diccionario que nunca se elimina. En un servidor de producción con sincronizaciones frecuentes, el diccionario crecerá indefinidamente.  
**Recomendación:** Implementar limpieza periódica de jobs completados/fallidos con más de X horas de antigüedad.

---

### 🟡 MEDIO — `updated_at` en `/backup` usa `datetime.utcnow()` sin timezone

**Archivo:** `backend-api/app/main.py`, línea 620  

```python
updated_at = datetime.utcnow().isoformat() + "Z"
```

`datetime.utcnow()` está deprecado desde Python 3.12. La app Android puede tener problemas interpretando el timestamp si la serialización es inconsistente con el resto de los campos.  
**Recomendación:** Usar `datetime.now(timezone.utc).isoformat()`.

---

### 🟡 MEDIO — Variable `os` shadowed en list comprehension

**Archivo:** `backend-api/app/main.py`, líneas 803-809  

```python
"ofertas_sucursal": [
    {
        "IdOfertaxProductoxSucursal": os.IdOfertaxProductoxSucursal,
        ...
    }
    for os in ofertas_sucursal  # 'os' sobrescribe el módulo os importado
],
```

La variable de iteración `os` sombrea el módulo estándar `os` dentro de la comprensión. Aunque Python resuelve correctamente el scope en este caso particular, es una trampa para futuros desarrolladores y puede causar bugs si se accede a `os.path` dentro del mismo bloque.  
**Recomendación:** Renombrar la variable a `oferta_suc` o similar.

---

### 🟡 MEDIO — `_utcnow()` definida dos veces con implementaciones diferentes

**Archivo:** `backend-dashboard/app/routes/auth.py`, línea 50 y `backend-dashboard/app/routes/monitoreo.py`, línea 47  

```python
# auth.py
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

# monitoreo.py
def _utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)
```

Una versión devuelve datetime timezone-aware (correcto), la otra devuelve naive con `utcnow()` deprecado. Esto puede causar comparaciones `TypeError` si los datetimes se mezclan.  
**Recomendación:** Crear una función utilitaria centralizada en `app/utils/time.py` y usarla en todos los módulos.

---

## 4. Diseño y Calidad de Código

### 🟡 MEDIO — Re-importación redundante en `database.py`

**Archivo:** `backend-api/app/database.py`, línea 97  

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession  # Ya importado en línea 2
```

Esta importación duplicada no causa un error pero genera confusión sobre cuántos engines se definen y con qué configuración.

---

### 🟡 MEDIO — `import json` y `import time` dentro de métodos

**Archivo:** `backend-api/app/main.py`, líneas 1401, 1500, 1607  

```python
import json  # dentro de connect()
import time  # dentro de send_to_device() y _cleanup_old_queues()
```

Las importaciones deben estar al inicio del módulo. Hacerlas dentro de métodos aumenta la complejidad de lectura y puede confundir linters/IDEs.

---

### 🟡 MEDIO — `TabletWebSocketManager.connect()` no agrega el websocket a `active_connections` antes de manejar timeouts

**Archivo:** `backend-api/app/main.py`, líneas 1380-1449  
**Descripción:** Si ocurre un `TimeoutError` o `json.JSONDecodeError` durante la identificación inicial, el websocket ya fue aceptado (`await websocket.accept()`) pero nunca fue agregado a `active_connections`. Sin embargo, se intenta cerrar el websocket con `await websocket.close(...)`. Si el websocket ya fue cerrado por el cliente, esto genera una excepción silenciosa.  
**Recomendación:** Manejar explícitamente los errores de `websocket.close()` con `try/except` en estos paths de fallo.

---

### 🟡 MEDIO — Comentario ruso en producción

**Archivo:** `backend-dashboard/app/routes/notificaciones.py`, línea 181  

```python
return {"success": True, "message": "Notificación ya была marcada como leída"}
```

La cadena contiene texto en ruso ("была" = "fue" en ruso). Parece ser un error de autocorrección o copiar/pegar. Esto puede confundir a usuarios y a sistemas de monitoreo.  
**Recomendación:** Corregir a `"Notificación ya fue marcada como leída"`.

---

### 🟡 MEDIO — Endpoint `GET /productos` en `consultas.py` ejecuta N+1 queries

**Archivo:** `backend-api/app/routes/consultas.py`, líneas 24-36  
**Descripción:** Por cada producto obtenido en la primera consulta, se ejecutan dos queries adicionales (precio y oferta). Para una página de 100 productos, esto genera 201 queries a la base de datos.  
**Recomendación:** Usar `joinedload` o `selectinload` de SQLAlchemy para cargar precios y ofertas en una sola consulta con JOIN.

---

### 🟡 MEDIO — `backend-dashboard/app/database.py` no tiene `pool_pre_ping` ni `pool_recycle`

**Archivo:** `backend-dashboard/app/database.py`, línea 36  
**Descripción:** El engine del dashboard se crea sin `pool_pre_ping=True` ni `pool_recycle`. Bajo carga alta, las conexiones pueden cerrarse por el servidor SQL y el pool las reutiliza sin verificar su estado, generando errores esporádicos.

---

### 🟡 MEDIO — `verificar_token_jwt` usa `options={"require": [...]}` pero no valida el claim `rol`

**Archivo:** `backend-dashboard/app/utils/security.py`, línea 54  
**Descripción:** Se especifica `"rol"` en la lista `require`, pero los tokens generados para administradores y clientes lo incluyen como `str`. No se valida que el valor de `rol` sea uno de los permitidos dentro de `verificar_token_jwt`; esa validación ocurre más tarde en `get_current_admin` / `get_current_cliente`, lo que está bien, pero la función de verificación debería al menos documentar qué valores espera.

---

## 5. Base de Datos y Persistencia

### 🟡 MEDIO — Sin migraciones automáticas (Alembic)

**Descripción:** No existe directorio `alembic/` ni `migrations/` en ninguno de los dos backends. Los modelos SQLAlchemy (`Base.metadata.create_all`) se usan para crear tablas, pero sin un sistema de migraciones no hay historial de cambios al esquema. Cualquier ALTER TABLE en producción debe hacerse manualmente.  
**Recomendación:** Integrar Alembic para gestionar el ciclo de vida del esquema.

---

### 🟡 MEDIO — `create_tables_async.py` no se llama automáticamente

**Archivo:** `backend-api/app/create_tables_async.py`  
**Descripción:** El script existe como utilidad pero no se invoca en el entrypoint ni en el evento de startup. Si se despliega en un entorno nuevo, las tablas no se crean automáticamente.

---

### 🟡 MEDIO — Sin índices en campos de búsqueda frecuente (campo `Barra` en `BarrasAsociadas`)

**Archivo:** `backend-api/app/models/barras_asociadas.py`  
**Descripción:** La búsqueda en `/consultar/{codigo_barras}` filtra por `BarrasAsociadas.Barra` (línea 447 de `main.py`), pero el modelo no declara un índice en ese campo. En tablas grandes, esto resultará en full-table scans.

---

## 6. Gestión de Configuración y Secretos

### 🔴 CRÍTICO — `.env` files potencialmente no en `.gitignore`

**Descripción:** El repositorio tiene múltiples archivos `.env.*` referenciados en `docker-compose.yml` (`./backend-dashboard/.env.dashboard`). Si no están correctamente ignorados, pueden ser comprometidos inadvertidamente. Verificar que `.gitignore` excluya `*.env`, `.env.*` y `**/.env`.

---

### 🟠 ALTO — `DASHBOARD_URL` no tiene valor por defecto claro

**Archivo:** `backend-api/app/main.py`, línea 2027  

```python
dashboard_url = os.getenv("DASHBOARD_URL")
if not dashboard_url:
    logging.error("DASHBOARD_URL no está definida en el entorno.")
    return
```

Si `DASHBOARD_URL` no está definida, las notificaciones al dashboard fallan silenciosamente con un log de error. No hay alerta activa ni circuit breaker. Los administradores pueden no enterarse hasta que revisiten los logs.  
**Recomendación:** Validar esta variable al inicio de la aplicación (en el evento `startup`) y no silenciar el fallo.

---

### 🟡 MEDIO — Variables `REDIS_URL` sin validación en múltiples servicios

**Archivos:** `device_state.py`, `device_bus.py`, `command_acker.py`  
**Descripción:** `REDIS_URL` tiene el valor por defecto `redis://localhost:6379/0`. En un despliegue Docker este localhost no apunta al contenedor Redis sino al propio contenedor del backend-api, causando una falla silenciosa. El sistema debe verificar la conectividad Redis al iniciar y fallar explícitamente si no está disponible.

---

## 7. Pruebas y Observabilidad

### 🔴 CRÍTICO — Ausencia total de pruebas automatizadas

**Descripción:** Ni `backend-api` ni `backend-dashboard` tienen ningún test unitario, de integración ni end-to-end. El archivo `backend-api/test_model.py` existe pero está vacío o es un placeholder. La ausencia de pruebas hace imposible garantizar la correctitud del código en ningún refactor.  
**Recomendación:** Implementar como mínimo:
- Tests unitarios de `armar_respuesta`, `normalizar_codigo_barras`, `buscar_tasa_impuesto`
- Tests de integración para `GET /consultar/{codigo_barras}` con una BD en memoria (SQLite async)
- Tests de autenticación para los endpoints protegidos

---

### 🟠 ALTO — Sin métricas de aplicación (Prometheus/OpenTelemetry)

**Descripción:** No existe ningún endpoint `/metrics` ni integración con herramientas de observabilidad. En producción, no hay forma de monitorear tasa de errores, latencia por endpoint, número de conexiones WebSocket activas, tamaño de las colas de mensajes, etc.  
**Recomendación:** Integrar `prometheus-fastapi-instrumentator` o `opentelemetry-sdk`.

---

### 🟡 MEDIO — `verificar_conexion.py` y `heartbeat_client.py` sin documentación de uso

**Archivos:** `backend-api/verificar_conexion.py`, `backend-api/heartbeat_client.py`  
**Descripción:** Estos scripts parecen ser herramientas de debugging pero no tienen docstrings ni README asociado. No está claro si son parte del sistema productivo o artefactos de desarrollo.

---

### 🟡 MEDIO — Logging inconsistente (`logging.error` vs `logger.error`)

**Archivo:** `backend-api/app/main.py`, múltiples líneas  
**Descripción:** En algunos lugares se usa el logger instanciado (`logger = logging.getLogger("uvicorn.error")`) y en otros se usa el módulo directamente (`logging.error(...)`). El módulo logging sin instancia puede usar el root logger, que puede tener una configuración diferente.

---

## 8. Resumen de Hallazgos por Severidad

| Severidad | Cantidad | Descripción |
|-----------|----------|-------------|
| 🔴 Crítico | 5 | Endpoints sin auth, contraseña hardcodeada, APK en repo, ausencia de tests, .env en repo |
| 🟠 Alto | 8 | Endpoints de control sin auth, 2FA en memoria, sin rate limiting, HTTP entre servicios, DASHBOARD_URL silenciosa, métricas ausentes, consultas.py roto, state global en multi-worker |
| 🟡 Medio | 18 | Zona horaria inconsistente, variables shadowed, N+1 queries, `has_more` falso positivo, funciones duplicadas, re-imports, cleanup incompleto, sin Alembic, logging inconsistente, etc. |
| **Total** | **31** | |

---

## Recomendaciones Prioritarias

1. **Inmediato:** Proteger `/backup` y todos los endpoints de control con autenticación.
2. **Inmediato:** Eliminar la contraseña por defecto en `docker-compose.yml` y el APK del repositorio.
3. **Corto plazo:** Corregir `consultas.py` (importar las funciones que usa o moverlas a un servicio).
4. **Corto plazo:** Migrar el estado 2FA a Redis para compatibilidad multi-worker.
5. **Mediano plazo:** Fragmentar `main.py` en módulos coherentes.
6. **Mediano plazo:** Implementar suite de tests básica (pytest + httpx).
7. **Mediano plazo:** Integrar Alembic para gestión de migraciones.
8. **Largo plazo:** Añadir métricas de observabilidad y un scheduler externo para banners.

---

*Informe generado automáticamente a partir del análisis estático del código fuente del repositorio.*
