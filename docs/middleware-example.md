# Ejemplo de cambio para conectar a base en middleware

## Caso 1: Middleware expone SQL (proxy)
Solo cambias el host/puerto a los del middleware:

**Antes (directo a SQL Server):**
```
DB_SERVER=192.168.1.50
DB_PORT=1433
DB_NAME=Transaccional
DB_USER=sa
DB_PASSWORD=******
```

**Después (vía middleware SQL proxy):**
```
DB_SERVER=10.10.0.15
DB_PORT=15433
DB_NAME=Transaccional
DB_USER=middleware_user
DB_PASSWORD=******
```

## Caso 2: Middleware expone API
En este caso el backend ya no se conecta directo a SQL.
En vez de SQLAlchemy, consume el API del middleware.

**Ejemplo de pseudo-cambio (solo referencia):**

```
# ANTES: SQLAlchemy
result = await db.execute(select(models.Producto).where(models.Producto.SKU == sku))

# DESPUÉS: HTTP al middleware
resp = await http_client.get(f"{MIDDLEWARE_URL}/productos", params={"sku": sku})
producto = resp.json()
```

## Variables ejemplo para API
```
MIDDLEWARE_URL=https://middleware.miempresa.local/api
MIDDLEWARE_TOKEN=xxxxx
```

---

Este archivo es solo de referencia y no modifica tu código actual.
