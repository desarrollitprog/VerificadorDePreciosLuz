# AGENTS.md - VerificadorDePreciosLuz

## Project Structure

```
VerificadorDePreciosLuz/
├── dashboard/          # React frontend (Vite + TypeScript)
├── backend-dashboard/ # FastAPI - main admin dashboard (port 8001)
├── backend-api/      # FastAPI - runs on each secondary server (port 8000)
├── nginx/           # SSL proxy config
├── docker-compose.yml
└── updates/         # APK files for Android app
```

## Commands

### Frontend (dashboard)
```powershell
cd dashboard
npm install
npm run dev  # Port 3000, proxies to backend-dashboard
```

### Backend (backend-dashboard)
```powershell
cd backend-dashboard
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Backend (backend-api)
```powershell
cd backend-api
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Tests (backend-dashboard)
```powershell
cd backend-dashboard
pytest tests/ -v
```

### Docker
```powershell
docker-compose up -d --build  # All services
docker-compose logs -f       # View logs
```

## Environment Files

| File | Component |
|------|-----------|
| `.env.dashboard` | backend-dashboard |
| `.env` | backend-api |
| `.env.local` | dashboard frontend |

## Architecture Notes

- **Replication**: backend-dashboard replicates banners/videos to backend-api on secondary servers (kiosks) using `asyncio.gather()` for parallel execution
- **Heartbeat**: secondary servers (backend-api) send periodic health/status to dashboard
- **Two backends**: dashboard (admin UI) vs api (kiosko devices) - don't confuse them
- **Sessions**: APScheduler runs every 3.5 min to update device sessions
- **Storage**: banners stored in `static/banners/` - mounted volume

## Testing

Tests are in `backend-dashboard/tests/` - 127+ pytest tests covering:
- Rate limiting, sanitization, MIME validation
- Health checks, 2FA (Redis), pagination
- Parallel replication, code quality