# Procedimiento de Restore — DashboardUsuarios

## Prerrequisitos
- Acceso al servidor host (`srv-luzcadash-01`)
- Contenedor `dashboard-sqlserver` corriendo
- Archivo `.bak` disponible en `/backups/` (o ruta accesible)

## Pasos

### 1. Detener servicios que usan la BD
```bash
docker compose stop dashboard-backend dashboard-frontend
```

### 2. Restaurar la base de datos
```bash
# Listar backups disponibles
ls -la /backups/DashboardUsuarios_*.bak

# Elegir el archivo a restaurar (ejemplo)
BACKUP_FILE="/backups/DashboardUsuarios_20260926_020000.bak"

# Restaurar (sobrescribe la BD actual)
docker exec dashboard-sqlserver /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U sa -P "$SA_PASSWORD" -C \
    -Q "RESTORE DATABASE [DashboardUsuarios] FROM DISK = '$BACKUP_FILE' WITH REPLACE, RECOVERY"
```

### 3. Verificar la restauración
```bash
docker exec dashboard-sqlserver /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U sa -P "$SA_PASSWORD" -C \
    -d DashboardUsuarios -Q "SELECT COUNT(*) FROM dbo.Publicidad; SELECT COUNT(*) FROM dbo.dispositivos"
```

### 4. Reiniciar servicios
```bash
docker compose start dashboard-backend dashboard-frontend
```

### 5. Verificar salud
```bash
curl -sf http://localhost:8001/health
curl -sf http://localhost/
```

## Notas
- El modelo de recuperación es `SIMPLE` → no hay backups de log, solo full.
- Los backups se generan diariamente a las 02:30 (cron del host).
- Retención: 14 días (configurable en `scripts/backup_sqlserver.sh`).
- Verificar integridad: el script de backup ya ejecuta `RESTORE VERIFYONLY`.