# AGENTS.md - VerificadorDePreciosLuz

Multiservice kiosk system: admin dashboard + secondary-server APIs + Android barcode scanner app. Manages banners/publicity, product price lookups, and device monitoring across ~10 servers / ~20 devices.

## Commands

### Frontend (dashboard)
```powershell
cd dashboard; npm install; npm run dev  # Port 3000, proxies /api+/static to backend-dashboard
```
### Backend (backend-dashboard)
```powershell
cd backend-dashboard; python -m venv venv; .\venv\Scripts\Activate; pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```
### Backend (backend-api) — runs on each kiosk server
```powershell
cd backend-api; python -m venv venv; .\venv\Scripts\Activate; pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
### Tests
```powershell
cd backend-dashboard; pytest tests/ -v
```
### Docker
```powershell
docker-compose up -d --build
```

## Architecture

### Two Backends — Different Roles
- **backend-dashboard** (port 8001 dev, port 8000 container → docker-compose maps 8001:8000): Admin UI backend. Routes mounted under `/api`: banners, heartbeat, monitoreo, auth, notificaciones, auditoria, resumen, reproducciones. Talks to `DashboardUsuarios` DB (SQL Server via aioodbc, ODBC Driver 18). Serves `/static` for banners/files.
- **backend-api** (port 8000): Runs on each kiosk server. Routes mounted **directly** (no prefix): `/consultar/{codigo}`, `/banners/remoto/{id}`, `/banners/{id}`, `/banners/{id}/exists`, `/replicar-archivo`, `/backup`, `/heartbeat`, `/api/comandos/{device_id}`, `/devices/status`, `/devices/{device_id}`, `/ping`. Talks to **3 databases**: (1) ERP_MPC (products/prices), (2) ERP_POS_CENTRAL (tax rates), (3) PublicidadSecundaria (banners). Exposes WebSocket (same port) for device commands.

### nginx (production)
- `nginx/nginx.conf`: Serves React SPA (`/usr/share/nginx/html`, SPA fallback), proxies `/api/` and `/static/` to backend container at `dashboard-backend:8000`. `client_max_body_size 100M` for banner uploads. Alternative SSL config at `nginx/nginx-ssl.conf`.

### Replication (banner sync)
- backend-dashboard **pushes** banners/videos to all backend-api servers via `asyncio.gather()` for parallel execution.
- `get_api_urls()` reads `BACKEND_API_URLS` env var (comma-separated). For `ServidorSecundario`-based targets, `api_url = f"http://{srv.ip}:8000"`.
- Endpoints hit on backend-api: `/replicar-archivo` (POST/PATCH), `/banners/remoto/{id_remoto}` (DELETE), `/banners/remoto/{id_remoto}/estado` (PATCH), `/banners/remoto/{id_remoto}` (PATCH metadata).
- **Deletion is idempotent**: `Borrado_api()` treats 200 and 404 as success (2026-05 fix). Server with no banner responds 404 = no-op.
- Some legacy functions (`Borrado_a_todas_las_apis`, `replicar_archivo_a_todas_las_apis`) iterate sequentially; newer ones use `asyncio.gather`.

### Heartbeat
- Each backend-api server sends periodic POST `/api/heartbeat` to dashboard with storage stats. Key-authenticated via `HEARTBEAT_API_KEY`.
- Devices send WebSocket heartbeats stored in Redis (`DeviceStateStore`).

### Scheduler (APScheduler) — `backend-dashboard/app/scheduler.py`
| Interval | Jobs |
|----------|------|
| Every 3.5 min | `actualizar_sesiones_dispositivos` (mark offline), `expirar_banners_vencidos` |
| Every 15 days | `cleanup_old_sessions` (>90 day sessions), `cleanup_old_notifications` (>15 day) |
| Every 24h | `cleanup_orphan_files` (stale banner files), `limpiar_metricas_antiguas` |
| Every hour | `consolidar_por_hora` (metric aggregation) |

### Databases
- **backend-dashboard**: `DashboardUsuarios` — users, banners, assignments, audit, devices, servers, notifications
- **backend-api**:
  - **ERP_MPC** (Transaccional) — products, prices, offers, barcodes, tax links
  - **ERP_POS_CENTRAL** — tax rates (`TasaImpuesto`)
  - **PublicidadSecundaria** — replicated banners (model `Publicidad` with `IdPublicidadRemoto` foreign key to dashboard's `IdPublicidad`)

### Redis
- Shared device state across backend-api instances (`DeviceStateStore`)
- Command bus (pub/sub) for device commands
- Command ack waiters (polling with timeout)
- 2FA rate limiting, pending notification storage, banner batch coalescence
- `dashboard-redis` container in docker-compose (port 6380, internal 6379)

### CORS
- `ALLOWED_ORIGINS` env var — comma-separated origins. `*` raises `RuntimeError` at startup (`main.py:36-37`).

## Frontend (dashboard/)

- React 18 + TypeScript + Vite 6 + Tailwind CSS
- Axios at `services/axiosInstance.ts`
- No lint/typecheck scripts in `package.json`
- Vite PWA plugin (Workbox for caching)
- `VITE_API_URL` in `.env.local` — Docker: `/api` (nginx proxy); local dev defaults to `http://192.168.0.104:8001` (`vite.config.ts:8`)

## Android App (luzapp/)

### Overview
- Kotlin, CameraX, ML Kit barcode scanning, Retrofit + OkHttp
- Price lookups via backend-api `/consultar/{codigo}`
- 3 notification channels: WS direct, Redis pub/sub, pending queue fallback
- Current: `versionCode = 17`, `versionName = "2.4.0"` (source of truth at `luzapp/app/build.gradle.kts:16-17`)
- Signing: **same release keystore for debug & release**. If a device has a locally-built debug APK, CI updates fail (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`). Reinstall from CI APK once.

### Updates
- **Not served by any backend**. Delivered via **GitHub Pages**: `https://tavorl25.github.io/VerificadorDePreciosLuz/version.json`
- CI builds `assembleRelease` daily at 9 AM UTC, signs via secrets, commits `luzapp.apk` + `version.json` to `main` with `--force` (build-apk.yml:67). Falls back to pull+rebase if force-push fails.
- 3 update modes: `DIALOG` (user confirms via FileProvider), `SILENT` (notification), `AUTO` (silent install via PackageInstaller + Device Owner)

## Gotchas

- **`dashboard/README.md`**: Ignore it — leftover AI Studio template. No `GEMINI_API_KEY` needed.
- **Env files**: `backend-dashboard/.env.dashboard`, `backend-api/.env`, `dashboard/.env.local` — all `.example` files in repo; real ones are gitignored.
- **Deletion**: Frontend re-fetches video list on any delete outcome via `getVideos()` in `finally` block of `handleDeleteConfirm`.
- **PWA caching**: Service worker may cache stale banner data during development. Hard refresh or disable cache in DevTools.
