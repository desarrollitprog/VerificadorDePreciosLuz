# Plan de Mejoras — Backend API / Consulta de Precios

> **Estado:** Pendiente por implementar  
> **Problema detectado:** Alto consumo de CPU en SQL Server de Mele durante consultas de precio desde Florida (3 verificadores)  
> **Causa raíz:** Queries no-sargable + múltiples round trips por request + pool de conexiones sin límite

---

## Resumen de Cambios

| # | Optimización | Archivos | Impacto | Esfuerzo | Prioridad |
|---|-------------|----------|---------|----------|-----------|
| 1 | Eliminar `CAST(FechaFin AS DATE)` (no-sargable) | `app/main.py` | 🔴 Alto | 🟢 Bajo | **1** |
| 2 | Unificar producto+precio+oferta+detalle en 1 query | `app/main.py` | 🔴 Alto | 🟡 Medio | **2** |
| 3 | Optimizar fallback BarrasAsociadas a 1 query | `app/main.py` | 🟡 Medio | 🟢 Bajo | **4** |
| 4 | Cachear tasas de impuesto en memoria (TTL 10min) | `app/main.py` | 🔴 Medio-Alto | 🟢 Bajo | **3** |
| 5 | Configurar pool_size y max_overflow en conexiones | `app/database.py` | 🟡 Medio | 🟢 Bajo | **5** |
| 6 | Fix N+1 en endpoint `/productos` | `app/routes/consultas.py` | 🟢 Bajo | 🟡 Medio | **6** |

---

## Punto 1: Eliminar CAST(FechaFin AS DATE)

### Problema

En `app/main.py:982-988` se aplica `CAST(FechaFin AS DATE)` que impide que SQL Server use el índice en la columna `FechaFin`, forzando un **Index Scan** completo en `OfertasxProductos` por cada consulta. Además hay una condición duplicada e idéntica en las líneas 985-986.

### Código actual

```python
or_(
    models.OfertasxProductos.FechaFin.is_(None),
    and_(
        cast(models.OfertasxProductos.FechaFin, Date) >= today_start.date(),
        cast(models.OfertasxProductos.FechaFin, Date) >= now.date(),
    ),
),
```

### Solución

Reemplazar con comparación directa contra `today_start` (datetime, ya definido en línea 954). SQL Server puede usar el índice en `FechaFin` al no haber función envolviendo la columna.

```python
or_(
    models.OfertasxProductos.FechaFin.is_(None),
    models.OfertasxProductos.FechaFin >= today_start,
),
```

### SQL generado (antes vs después)

```sql
-- Antes (no-sargable - Table Scan):
AND (O.FechaFin IS NULL OR (CAST(O.FechaFin AS DATE) >= '2024-01-15' AND CAST(O.FechaFin AS DATE) >= '2024-01-15'))

-- Después (sargable - Index Seek):
AND (O.FechaFin IS NULL OR O.FechaFin >= '2024-01-15 00:00:00')
```

---

## Punto 2: Unificar Consultas con OUTER JOIN + Subqueries

### Problema

Cada request ejecuta **3-4 queries secuenciales** a ERP_MPC:

1. `buscar_producto_y_precio()` — JOIN Producto + ProductoPrecio
2. `buscar_oferta()` — ProductosOfertasxSucursal
3. `buscar_detalle_oferta_vigente()` — 3 tablas JOIN con CAST
4. `buscar_tasa_impuesto()` — ProductosXImpuestos (parcial)

Cada una espera la respuesta de la anterior (round trip). Con latencia Florida → Mele (~50-100ms), 3-4 viajes = ~200-400ms solo en red.

### Solución propuesta

Unificar pasos 1-3 en **una sola query** con `OUTER JOIN` + subqueries (adaptando el enfoque existente en `test_model.py:237-279` a SQLAlchemy 2.0 async):

```python
async def buscar_producto_completo(
    db: AsyncSession, codigo_barras: str, now: datetime
) -> tuple | None:
    today_start = datetime.combine(now.date(), datetime.min.time())

    sub_ofertas_vigentes = (
        select(models.OfertasxProductos.IdOfertaxProducto)
        .where(
            models.OfertasxProductos.IndExpirado == 0,
            models.OfertasxProductos.FechaInicio <= now,
            or_(
                models.OfertasxProductos.FechaFin.is_(None),
                models.OfertasxProductos.FechaFin >= today_start,
            ),
        )
        .subquery()
    )

    sub_ofertas_sucursal = (
        select(models.OfertasxProductosxSucursal.IdOfertaxProductoxSucursal)
        .where(
            models.OfertasxProductosxSucursal.IdOfertaxProducto.in_(
                select(sub_ofertas_vigentes.c.IdOfertaxProducto)
            )
        )
        .subquery()
    )

    stmt = (
        select(
            models.Producto,
            models.ProductoPrecio,
            models.ProductoOferta,
            models.OfertasxProductosxSucursalesDetalles,
        )
        .join(
            models.ProductoPrecio,
            models.Producto.IdProducto == models.ProductoPrecio.IdProducto,
        )
        .outerjoin(
            models.ProductoOferta,
            models.Producto.IdProducto == models.ProductoOferta.IdProducto,
        )
        .outerjoin(
            models.OfertasxProductosxSucursalesDetalles,
            and_(
                models.ProductoPrecio.IdEmpaque
                == models.OfertasxProductosxSucursalesDetalles.IdEmpaque,
                models.OfertasxProductosxSucursalesDetalles.IdOfertaxProductoxSucursal.in_(
                    select(sub_ofertas_sucursal.c.IdOfertaxProductoxSucursal)
                ),
            ),
        )
        .where(
            models.Producto.SKU == codigo_barras,
            models.ProductoPrecio.CostoBase > 0,
        )
        .limit(1)
    )

    result = await db.execute(stmt)
    return result.first()
```

### Reestructura del endpoint

El endpoint `obtener_precio` en `main.py:1313-1349` se simplifica a:

```
por cada variante de código:
    resultado = await buscar_producto_completo(db, codigo, now)
    si resultado:
        producto, precio, oferta, detalle = resultado
        tasa = await buscar_tasa_impuesto(...)  # se optimiza en Punto 4
        return armar_respuesta(...)
    
    resultado = await buscar_por_barras_asociadas(db, codigo, now)  # Punto 3
    si resultado: ... similar ...
```

### Advertencia de lógica

El código actual usa `IndExpirado != 1 OR IndExpirado IS NULL` (líneas 974-976), pero la subquery en `test_model.py` usa `IndExpirado == 0`. **No son equivalentes**: `!= 1` incluye valores `0` y `NULL`, mientras `== 0` solo incluye `0`. Revisar cuál es la semántica correcta antes de implementar.

---

## Punto 3: Optimizar Fallback BarrasAsociadas

### Problema

`buscar_en_barras_asociadas()` (`main.py:905-932`) ejecuta **2 queries secuenciales**:
1. Busca el código en `BarrasAsociadas`
2. Con el `IdProducto` obtenido, busca producto + precio

### Solución

Unificar en una sola query con JOIN directo desde `BarrasAsociadas` → `Productos` → `ProductosXEmpaqueXSucursal`, más los mismos OUTER JOIN de ofertas del Punto 2.

```python
async def buscar_por_barras_asociadas(
    db: AsyncSession, codigo_barras: str, now: datetime
) -> tuple | None:
    # misma subquery de ofertas vigentes que buscar_producto_completo
    ...

    stmt = (
        select(Producto, ProductoPrecio, ProductoOferta, OfertasxProductosxSucursalesDetalles)
        .join(BarrasAsociadas, BarrasAsociadas.IdProducto == Producto.IdProducto)
        .join(ProductoPrecio, Producto.IdProducto == ProductoPrecio.IdProducto)
        .outerjoin(ProductoOferta, ...)
        .outerjoin(OfertasxProductosxSucursalesDetalles, ...)
        .where(
            BarrasAsociadas.Barra == codigo_barras,
            BarrasAsociadas.IndActivo == 1,
            ProductoPrecio.CostoBase > 0,
        )
        .limit(1)
    )

    result = await db.execute(stmt)
    return result.first()
```

---

## Punto 4: Cachear Tasas de Impuesto en Memoria

### Problema

`buscar_tasa_impuesto()` (`main.py:998-1021`) ejecuta **2 queries secuenciales cross-DB**:
1. `ERP_MPC` → `ProductosXImpuestos WHERE IdProducto = ?`
2. `ERP_POS_CENTRAL` → `TasasImpuestos WHERE IdTasaImpuesto = ?`

Las tasas de IVA son pocas (3-5 registros: 8%, 16%, exento) y cambian muy rara vez.

### Solución

Caché en memoria con TTL de 10 minutos. La primera consulta carga todas las tasas desde `ERP_POS_CENTRAL` y las reusa desde RAM.

```python
from time import time

_tax_rate_cache: dict[int, float] = {}
_tax_cache_ts: float = 0
TAX_CACHE_TTL = 600  # 10 minutos

async def buscar_tasa_impuesto(
    db: AsyncSession,
    db_erp: AsyncSession,
    id_producto: int,
    precio: models.ProductoPrecio | None,
):
    if not precio or precio.IndIVA not in (1, True):
        return None

    impuesto_stmt = select(models.ProductosXImpuestos).where(
        models.ProductosXImpuestos.IdProducto == id_producto,
        models.ProductosXImpuestos.IndActivo == 1,
    )
    impuesto_result = await db.execute(impuesto_stmt)
    impuesto = impuesto_result.scalars().first()
    if not impuesto:
        return None

    global _tax_rate_cache, _tax_cache_ts
    now = time()
    if now - _tax_cache_ts > TAX_CACHE_TTL:
        tasa_stmt = select(models.TasaImpuesto)
        tasa_result = await db_erp.execute(tasa_stmt)
        _tax_rate_cache = {
            t.IdTasaImpuesto: float(t.Tasa)
            for t in tasa_result.scalars().all()
        }
        _tax_cache_ts = now

    return _tax_rate_cache.get(impuesto.IdTasaImpuesto)
```

### Nota sobre workers múltiples

Con `--workers 4`, cada proceso tiene su propia memoria y su propia caché. Habrá hasta 4 consultas a `ERP_POS_CENTRAL` cada 10 minutos (1 por worker). Sigue siendo **drásticamente mejor** que consultar en cada request (~180+ por hora actual → ~24 por hora con caché).

---

## Punto 5: Configurar Pool de Conexiones

### Problema

`database.py:56-68, 98-103` — Los 3 engines se crean sin `pool_size` ni `max_overflow`, usando defaults de SQLAlchemy (`pool_size=5, max_overflow=10`).

Con `--workers 4` (entrypoint.sh:15):
- ERP_MPC: 4 × 15 = **hasta 60 conexiones**
- ERP_POS_CENTRAL: 4 × 15 = **hasta 60 conexiones**

### Solución

```python
# ERP_MPC (database.py ~línea 65)
async_engine = create_async_engine(
    ...,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=3,
    max_overflow=2,
)

# ERP_POS_CENTRAL (database.py ~línea 101)
engine_erp = create_async_engine(
    ...,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=2,
    max_overflow=1,
)
```

### Conexiones resultantes

| Engine | pool_size | max_overflow | Máx por worker | Máx total (4 workers) |
|--------|-----------|-------------|----------------|----------------------|
| ERP_MPC | 3 | 2 | 5 | 20 |
| ERP_POS_CENTRAL | 2 | 1 | 3 | 12 |
| PublicidadSecundaria | 5 (default) | 10 (default) | 15 | 60 |

> **Nota:** `PublicidadSecundaria` no se toca porque no impacta al ERP de Mele.

---

## Punto 6: Fix N+1 en `/productos`

### Problema

`routes/consultas.py:24-36` — Por cada producto en la lista (hasta 500), ejecuta queries individuales para precio, oferta e impuesto. Total: hasta **2,000 queries** por request.

### Solución

Cargar precio y oferta con `selectinload` o una sola query con JOIN. Baja prioridad porque este endpoint es de uso interno/debug.

---

## Impacto Estimado

### Escenario actual (3 verificadores, Florida → Mele)

| Métrica | Valor |
|---------|-------|
| Queries/hora al ERP | ~180-300 |
| Tiempo por scan | ~500-1500ms |
| Conexiones máximas | ~60 |
| Causa de CPU alto | Full scans por CAST + múltiples round trips |

### Escenario optimizado

| Métrica | Valor |
|---------|-------|
| Queries/hora al ERP | ~6-10 |
| Tiempo por scan | ~50-200ms |
| Conexiones máximas | ~20 |
| Causa de CPU alto | Eliminada |

---

## Orden de Implementación Sugerido

1. **Punto 1** — Eliminar CAST (bajo esfuerzo, alto impacto inmediato)
2. **Punto 4** — Caché de tasas (bajo esfuerzo, elimina queries cross-DB)
3. **Punto 2** — Unificación de consultas (esfuerzo medio, mayor impacto)
4. **Punto 5** — Pool de conexiones (bajo esfuerzo, preventivo)
5. **Punto 3** — Optimizar BarrasAsociadas (bajo esfuerzo, mejora fallback)
6. **Punto 6** — Fix N+1 (baja prioridad)

---

## Archivos a Modificar

| Archivo | Cambios |
|---------|---------|
| `backend-api/app/main.py` | Puntos 1, 2, 3, 4 |
| `backend-api/app/database.py` | Punto 5 |
| `backend-api/app/routes/consultas.py` | Punto 6 |

---

> ✅ **Implementado el 2026-06-16.** Todos los puntos completados.

## Resumen de Cambios Realizados

| # | Cambio | Archivo |
|---|--------|---------|
| 1 | Reemplazado `CAST(FechaFin AS DATE)` por comparación directa `FechaFin >= today_start` | `app/main.py` |
| 2 | Creadas funciones `buscar_producto_completo` y `_build_query_completo` con OUTER JOINs + subqueries | `app/main.py` |
| 3 | Creada `buscar_por_barras_asociadas` con JOIN directo en 1 query | `app/main.py` |
| 4 | Agregada caché en memoria para tasas de impuesto con TTL 10min | `app/main.py` |
| 5 | Configurado `pool_size=3, max_overflow=2` para ERP_MPC y `pool_size=2, max_overflow=1` para ERP_POS_CENTRAL | `app/database.py` |
| 6 | Eliminado N+1 en `/productos` con carga bulk de precios/ofertas por `IdProducto IN (...)` | `app/routes/consultas.py` |

### Correcciones de Fidelidad (puntos 2-3)

Durante la revisión se identificaron y corrigieron dos filtros faltantes para mantener el comportamiento original:

| Filtro faltante | Dónde se agregó | Línea |
|----------------|----------------|-------|
| `ProductoOferta.IndActivo == 1` | OUTER JOIN en `_build_query_completo` y `buscar_por_barras_asociadas` | `main.py:913, 973` |
| `Detalles.IndActivo == 1 OR Detalles.IndActivo IS NULL` | OUTER JOIN en `_build_query_completo` y `buscar_por_barras_asociadas` | `main.py:924-927, 984-987` |
