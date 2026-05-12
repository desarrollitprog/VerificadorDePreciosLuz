# AGENTS.md - VerificadorDePreciosLuz

## Project Overview

Multiservice kiosk system: admin dashboard + secondary-server APIs + Android barcode scanner app. Manages banners/publicity, product price lookups, and device monitoring across ~10 servers / ~20 devices.

## Commands

### Frontend (dashboard)
```powershell
cd dashboard
npm install
npm run dev  # Port 3000, proxies /api + /static to backend-dashboard via vite.config.ts
```

### Backend (backend-dashboard)
```powershell
cd backend-dashboard
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Backend (backend-api) - runs on each secondary server
```powershell
cd backend-api
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Tests
```powershell
cd backend-dashboard
pytest tests/ -v
```

### Docker
```powershell
docker-compose up -d --build
docker-compose logs -f
```

## Key Architecture

### Two Backends — Different Roles
- **backend-dashboard** (port 8001): Admin UI backend. Routes: `/api/banners`, `/api/heartbeat`, `/api/monitoreo`, `/api/auth`, `/api/notificaciones`, `/api/auditoria`. Talks to `DashboardUsuarios` DB.
- **backend-api** (port 8000): Runs on each kiosk server. Routes: `/consultar/{codigo}`, `/banners/remoto/{id}`, `/backup`, `/heartbeat`, `/api/comandos/{device_id}`. Talks to `ERP_MPC` + `PublicidadSecundaria` DBs. Exposes WebSocket for device commands.

### Replication (banner sync)
- backend-dashboard **pushes** banners/videos to all backend-api servers
- Uses `asyncio.gather()` for parallel execution across servers
- `get_api_urls()` reads `BACKEND_API_URLS` env var (comma-separated list)
- Endpoints: `/banners/remoto/{id}` (POST/PATCH/DELETE) on backend-api
- **Deletion is idempotent**: `Borrado_api()` treats both 200 and 404 as success (2026-05 fix). Server without a banner responds 404 = no-op, not error.
- Some legacy replication functions iterate sequentially (`Borrado_a_todas_las_apis`, `replicar_archivo_a_todas_las_apis`); newer ones use `asyncio.gather` in parallel.

### Heartbeat
- Each backend-api server sends periodic POST `/api/heartbeat` to dashboard with storage stats
- Key-authenticated via `HEARTBEAT_API_KEY`
- Devices also send WebSocket heartbeats stored in Redis (`DeviceStateStore`)

### Banner Storage
- Files stored in `backend-dashboard/static/banners/` (mounted volume)
- Served via FastAPI `StaticFiles` mount at `/static`
- Video thumbnails generated via OpenCV on upload

### Scheduler (APScheduler)
- Runs every 3.5 min in backend-dashboard (`lifespan` hook in `main.py`):
  - `actualizar_sesiones_dispositivos()` — marks offline devices
  - `expirar_banners_vencidos()` — sets `Activo=False` on expired banners

### Database
- SQL Server via `aioodbc`, ODBC Driver 18
- backend-dashboard: `DashboardUsuarios` DB (users, banners, assignments, audit)
- backend-api: `ERP_MPC` (products/prices) + `PublicidadSecundaria` (banners)

### Redis
- Shared device state across backend-api instances (`DeviceStateStore`)
- Command bus (pub/sub): device commands via Redis channels
- Command ack waiters (polling with timeout)
- 2FA rate limiting
- `dashboard-redis` container inside docker-compose (port 6380)

### CORS
- `ALLOWED_ORIGINS` env var on backend-dashboard — comma-separated, no wildcards allowed in production

### 2FA
- Email-based OTP via SMTP (Gmail) on login
- Rate-limited in Redis

## Android App (luzapp/)

### Overview
- Kotlin, CameraX, ML Kit for barcode scanning
- Price lookups via backend-api `/consultar/{codigo}`
- 3 banner notification channels: WS (direct), Redis pub/sub, pending queue fallback

### Updates
- **Not served by any backend**. Goes through **GitHub Pages**: `https://tavorl25.github.io/VerificadorDePreciosLuz/version.json`
- CI builds `assembleRelease` APK daily at 9 AM UTC (GitHub Actions), signs with keystore from secrets, pushes `luzapp.apk` + `version.json` to `main` (GitHub Pages)
- App checks for updates on launch (`UpdateChecker`) and daily via WorkManager at 6 AM Caracas
- 3 update modes: `DIALOG` (user confirms via `FileProvider`), `SILENT` (notification), `AUTO` (silent install via `PackageInstaller` + Device Owner)
- Keystore defined in `app/build.gradle.kts` via env vars: `KEYSTORE_PATH`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD` — same for debug and release builds
- **Critical**: both `debug` and `release` build types use the same release signing config. If a device has a debug APK from local dev, automated updates will **fail** (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`). Desinstall and reinstall via CI-built APK once.
- `versionName` in `app/build.gradle.kts` is the source of truth for version comparison (supports both semver like "1.2.0" and date like "20260429")

## Frontend (dashboard/)

- React 18 + TypeScript + Vite 6 + Tailwind CSS
- Axios for API calls (axios instance at `services/axiosInstance.ts`)
- No lint/typecheck scripts configured in package.json

## Useful Gotchas

### Deletion errors (2026-05 fix context)
When deleting a banner assigned to multiple servers, `Borrado_api` now treats 404 as success. A server that never had the banner responds 404 (not an error). Before the fix, this caused a 500 response. The frontend re-fetches the video list on any delete outcome (success or error) via `getVideos()` in the `finally` block of `handleDeleteConfirm`.

### `.env` files
| File | Component |
|------|-----------|
| `backend-dashboard/.env.dashboard` | backend-dashboard |
| `backend-api/.env` | backend-api |
| `dashboard/.env.local` | Vite proxy target (`VITE_API_URL`) |
| No `.env.dashboard` or `.env.local` in repo — tracked files are examples only |
| All `.jks`/`.keystore` files are gitignored |

### Tests
- 15 test files in `backend-dashboard/tests/`, pytest
- Coverage: rate limiting, sanitization, MIME validation, health checks, 2FA (Redis), pagination, parallel replication, code quality, banner exists endpoint
- Run via `pytest tests/`
