# Plan de Mejoras — Métricas por Sede

## Problema Original

Saturación del pool SQL en backend-dashboard causada por escrituras concurrentes del batch de reproducciones. Con ~10 servidores y ~20 dispositivos reportando cada 60s, SQL Server sufría lock contention, deadlocks y pool exhaustion (`QueuePool limit reached`).

## Solución Adoptada

Cada sede (backend-api) almacena localmente sus métricas con merge en memoria. El dashboard solo recibe datos agregados cada 5h. Sin merge SQL, sin deadlocks, sin pool saturation.

---

## Arquitectura Final

```
┌─────────────────────────────────────────────────────┐
│  SEDE (backend-api)                                  │
│                                                       │
│  Dispositivos → POST /api/reproducciones/progreso     │
│       → Redis "reproducciones:pending" (TTL 8h)       │
│                                                       │
│  Worker LOCAL cada 60s:                               │
│    LRANGE todos los eventos raw                       │
│    Merge en MEMORIA (agrupa por reproduccion_id,      │
│      aplica START→cuartil→COMPLETED en orden)         │
│    INSERT del estado final                            │
│    Si INTEGRITYERROR (duplicado, ~2%):               │
│      → UPDATE por reproduccion_id (PK exacta)        │
│    LTRIM                                              │
│                                                       │
│  Worker SYNC cada 5h (stagger aleatorio 0-300s):      │
│    SELECT banner_id, titulo,                          │
│      COUNT(*) as reproducciones,                      │
│      SUM(completo) as completados,                    │
│      SUM(cuartil_50) as validas_50,                   │
│      SUM(segundos_reproducidos) as segundos           │
│    FROM reproducciones_metricas_sede                  │
│    WHERE fecha_creacion >= inicio_de_hoy              │
│    GROUP BY banner_id, titulo                         │
│    → POST /api/reproducciones/sincronizar              │
│      Payload: {servidor_id, fecha, banners: [...]}    │
│                                                       │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP cada 5h (~50 requests/día)
                       ▼
┌─────────────────────────────────────────────────────┐
│  DASHBOARD (backend-dashboard)                       │
│                                                       │
│  POST /api/reproducciones/sincronizar                  │
│    DELETE FROM metricas_por_sede                      │
│      WHERE servidor_id=X AND fecha=hoy               │
│    INSERT INTO metricas_por_sede (bulk)               │
│    COMMIT (atómico)                                   │
│    → Response 200 OK                                  │
│                                                       │
│  GET /api/reproducciones/resumen-diario                │
│    SELECT SUM de metricas_por_sede WHERE fecha=X      │
│    (sin tocar reproducciones_metricas ni metricas_diarias)│
│                                                       │
└─────────────────────────────────────────────────────┘
```

---

## Archivos a Crear (5)

### 1. `backend-api/app/models/reproduccion_metrica.py`

Modelo `ReproduccionMetricaSede` en `BasePublicidad` (DB `PublicidadSecundaria`).

```python
class ReproduccionMetricaSede(Base):
    __tablename__ = "reproducciones_metricas_sede"
    id = Column(Integer, primary_key=True)
    reproduccion_id = Column(String(255), unique=True, nullable=False)
    dispositivo_id = Column(String(100), nullable=False)
    banner_id = Column(Integer, nullable=False)
    titulo = Column(String(255), nullable=True)
    completo = Column(Boolean, default=False)
    cuartil_50 = Column(Boolean, default=False)
    segundos_reproducidos = Column(Float, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
```

### 2. `backend-api/app/services/metricas_locales.py`

Worker #1 (cada 60s):
- `LRANGE reproducciones:pending 0 -1`
- Merge en memoria por `reproduccion_id`
- INSERT estado final por cada grupo
- Catch `IntegrityError` → UPDATE solo por PK exacta
- `LTRIM` luego de procesar

### 3. `backend-api/app/services/sync_metrics.py`

Worker #2 (cada 5h con stagger):
- SELECT agregado: `COUNT(*) as reproducciones, SUM(completo) as completados, SUM(cuartil_50) as validas_50, SUM(segundos_reproducidos) as segundos`
- GROUP BY `banner_id, titulo`
- WHERE `fecha_creacion >= inicio_de_hoy`
- POST HTTP a `DASHBOARD_URL/api/reproducciones/sincronizar`
- Reintenta en el próximo ciclo si el dashboard no responde

### 4. `backend-dashboard/app/models/metricas_por_sede.py`

```python
class MetricasPorSede(Base):
    __tablename__ = "metricas_por_sede"
    id = Column(Integer, primary_key=True)
    servidor_id = Column(Integer, nullable=False)
    banner_id = Column(Integer, nullable=False)
    titulo = Column(String(255), nullable=True)
    fecha = Column(Date, nullable=False)
    reproducciones = Column(Integer, default=0)
    completados = Column(Integer, default=0)
    validas_50 = Column(Integer, default=0)
    segundos_totales = Column(Float, default=0)
    __table_args__ = (
        UniqueConstraint("servidor_id", "banner_id", "fecha", name="uq_metricas_sede"),
    )
```

### 5. `backend-dashboard/app/routes/reproducciones_sync.py`

Endpoint `POST /api/reproducciones/sincronizar`:
- Recibe `{servidor_id, fecha, banners: [...]}`
- `DELETE FROM metricas_por_sede WHERE servidor_id=X AND fecha=Y`
- `INSERT INTO metricas_por_sede` (bulk insert)
- `COMMIT` — atómico, o todo o nada
- Response 200

---

## Archivos a Modificar (3)

### 1. `backend-api/app/main.py`

- **Startup**: instanciar y registrar ambos workers como tareas asíncronas
- **Shutdown**: cancelar workers
- **Reemplazar** `_forward_reproducciones_batch()` (envío HTTP a dashboard) por `_insert_local_reproducciones()` (merge + INSERT local)
- Mantener `POST /api/reproducciones/progreso` sin cambios

### 2. `backend-dashboard/app/routes/reproducciones.py`

- **Importar** `MetricasPorSede` en vez de `ReproduccionMetrica`
- **Eliminar** `POST /batch` (ya no se usa)
- **GET /resumen-diario**: leer de `MetricasPorSede`
  - `SELECT servidor_id, SUM(reproducciones), SUM(completados), SUM(validas_50), SUM(segundos_totales) WHERE fecha=X GROUP BY servidor_id, banner_id, titulo`

### 3. `backend-dashboard/app/services/metricas_service.py`

- **Reescribir** `resumen_diario()` usando `MetricasPorSede`
- **Reescribir** `tendencia_14d()` usando `MetricasPorSede`
- **Eliminar** `consolidar_por_hora()`
- **Eliminar** `limpiar_metricas_antiguas()`
- **Eliminar** `agregar_metricas_diarias()`

---

## Archivos a Eliminar (5)

| Archivo | Razón |
|---------|--------|
| `backend-dashboard/app/models/reproduccion_metrica.py` | Tabla `reproducciones_metricas` con data falsa |
| `backend-dashboard/app/models/metricas_diarias.py` | Tabla `metricas_diarias` con data falsa |
| `backend-dashboard/app/services/bulk_metrics.py` | Ya no hay merge en dashboard |
| `backend-dashboard/app/services/metrics_redis.py` | Ya no hay Redis queue en dashboard para métricas |
| `backend-dashboard/app/scheduler.py` | Eliminar jobs 6, 7, 8, 9. Mantener solo jobs 1-5 |

### Jobs a mantener en scheduler.py

- Job 1: `monitoreo_sesiones` (cada 3.5 min)
- Job 2: `expirar_banners` (cada 3.5 min)
- Job 3: `limpiar_sesiones` (cada 15 días)
- Job 4: `limpiar_notificaciones` (cada 15 días)
- Job 5: `limpiar_archivos_huérfanos` (cada 24h)

Jobs a eliminar:
- ~~Job 6: `consolidar_por_hora`~~
- ~~Job 7: `limpiar_metricas_antiguas`~~
- ~~Job 8: `agregar_metricas_diarias`~~
- ~~Job 9: `bulk_insert_reproducciones`~~

---

## Pool SQL del Dashboard

Reducir en `app/database.py`:

```python
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_POOL_OVERFLOW = int(os.getenv("DB_POOL_OVERFLOW", "5"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "5"))
```

Total máximo: **10 conexiones** (sobra ampliamente para ~50 requests/día de sync + heartbeats + frontend cada 10 min).

---

## Frontend

**Sin cambios.** `ResumenScreen.tsx:43` ya tiene `setInterval(load, 600000)` (10 min). Las primeras horas del día mostrará 0 eventos hasta que llegue el primer sync de cada sede (staggered cada 5h). El usuario aceptó "no hay apuro" con datos en tiempo real.

---

## Migración en SQL Server

Ejecutar en el SQL Server del dashboard:

```sql
DROP TABLE reproducciones_metricas;
DROP TABLE metricas_diarias;
```

Los datos existentes son incorrectos (confirmado por el usuario) y no se migran.

---

## Análisis de Riesgos

| Riesgo | Mitigación | Status |
|--------|-----------|--------|
| UPDATE duplicado deadlockea | **Imposible**: 1 escritor, 1 UPDATE por PK exacta. No hay segundo proceso que forme ciclo | 🟢 |
| SQL Server sede caído | Redis buffer 8h. Worker reintenta cada 60s sin pérdida | 🟢 |
| Dashboard caído durante sync | Sede reintenta en próximo ciclo de 5h. Datos acumulados en SQL local | 🟢 |
| Sede crashea entre INSERT y LTRIM | Mismo `reproduccion_id` reintenta en 60s → IntegrityError → UPDATE (idempotente) | 🟢 |
| Pool SQL de dashboard saturado | Solo ~50 requests/día de sync + heartbeats + frontend. Pool 5/5/5 sobra | 🟢 |
| Deadlock por SELECT+UPDATE previo | **Eliminado**: no hay SELECT+UPDATE en dashboard ni sedes. INSERT + UPDATE por PK | 🟢 |
| Redis dashboard desbordado | **Eliminado**: no hay Redis queue en dashboard para métricas | 🟢 |

---

## Orden de Implementación

1. Crear `backend-api/app/models/reproduccion_metrica.py`
2. Crear `backend-api/app/services/metricas_locales.py`
3. Crear `backend-api/app/services/sync_metrics.py`
4. Modificar `backend-api/app/main.py` (registrar workers, eliminar forward batch)
5. Crear `backend-dashboard/app/models/metricas_por_sede.py`
6. Crear `backend-dashboard/app/routes/reproducciones_sync.py`
7. Modificar `backend-dashboard/app/services/metricas_service.py`
8. Modificar `backend-dashboard/app/routes/reproducciones.py`
9. Modificar `backend-dashboard/app/database.py` (pool 5/5/5)
10. Modificar `backend-dashboard/app/scheduler.py` (eliminar jobs 6-9)
11. Eliminar archivos huérfanos (bulk_metrics.py, metrics_redis.py, reproduccion_metrica.py, metricas_diarias.py)
12. Ejecutar DROP TABLE en SQL Server dashboard
13. Rebuildear docker-compose
