# Alertas de flota (heartbeat + smoke test de precios)

El `backend-dashboard` ejecuta cada **5 minutos** el job `alertas_flota`
(`app/services/alertas_service.py`). Verifica:

1. Que cada sede tenga `ultimo_heartbeat` reciente (por defecto < 10 min).
2. Que el `backend-api` de cada sede responda una consulta de precio real
   (`GET /consultar/{SMOKE_TEST_SKU}`) — detecta ERP caído o bloqueos de red.

Cuando algo falla crea una notificación en `notificaciones`
(tipo `SEDE_SIN_CONEXION` o `SEDE_ERP_CAIDO`), visible en el dashboard, y
cuando la sede vuelve crea `SEDE_RECUPERADA`. Hay *cooldown* para no repetir
la misma alerta (por defecto cada 6 h).

## Variables de entorno (opcionales, en `backend-dashboard/.env.dashboard`)

| Variable | Default | Descripción |
|---|---|---|
| `ALERTS_ENABLED` | `1` | `0` desactiva el monitoreo |
| `ALERT_HEARTBEAT_MINUTES` | `10` | Minutos sin heartbeat para alertar |
| `ALERT_COOLDOWN_HOURS` | `6` | Horas entre alertas iguales de la misma sede |
| `SMOKE_TEST_SKU` | `7591098800281` | SKU de prueba |
| `SMOKE_TEST_TIMEOUT` | `6` | Timeout del smoke test (s) |
| `ALERTS_WEBHOOK_URL` | — | Recibe `POST {"text": "..."}` (Slack/Discord/Google Chat) |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | — | Alternativa: aviso por Telegram |

## Prueba manual

```bash
# dentro del contenedor del dashboard
docker exec dashboard-backend python -c "import asyncio; from app.services.alertas_service import verificar_flota; asyncio.run(verificar_flota())"
# revisar las últimas notificaciones
docker exec dashboard-sqlserver /opt/mssql-tools/bin/sqlcmd -S 127.0.0.1 -U sa -P "$SA_PASSWORD" \
  -d "Dashboard Usuarios" -Q "SELECT TOP 10 fecha_creacion, tipo, descripcion FROM notificaciones ORDER BY fecha_creacion DESC"
```

## Qué NO cubre (pendiente)

- Alertas de antigüedad de backups (requiere montar `./backups` en el contenedor
  del dashboard o un endpoint en el host).
- Alertas de uso de disco en los kioscos.
- Métricas históricas (Prometheus/Grafana).
