#!/bin/bash
# Backup script para SQL Server - DashboardUsuarios
# Se ejecuta via cron en el host: 0 2 * * * /home/desarrolloit/VerificadorDePreciosLuz/scripts/backup_sqlserver.sh

set -euo pipefail

# Cargar variables de entorno
source /home/desarrolloit/VerificadorDePreciosLuz/.env

BACKUP_DIR_HOST="/home/desarrolloit/VerificadorDePreciosLuz/backups"
BACKUP_DIR_CONTAINER="/backups"
LOG_FILE="/tmp/backup_sqlserver.log"
RETENTION_DAYS=14
DB_NAME="DashboardUsuarios"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Iniciando backup de $DB_NAME ==="

# Verificar que el directorio existe en el host
mkdir -p "$BACKUP_DIR_HOST"

# Nombre del archivo con timestamp
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE_HOST="$BACKUP_DIR_HOST/${DB_NAME}_${TIMESTAMP}.bak"
BACKUP_FILE_CONTAINER="$BACKUP_DIR_CONTAINER/${DB_NAME}_${TIMESTAMP}.bak"

# Ejecutar backup dentro del contenedor (usa ruta del contenedor)
log "Ejecutando BACKUP DATABASE..."
if docker exec dashboard-sqlserver /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U sa -P "$SA_PASSWORD" -C \
    -Q "BACKUP DATABASE [$DB_NAME] TO DISK = '$BACKUP_FILE_CONTAINER' WITH INIT, COMPRESSION, CHECKSUM" 2>&1 | tee -a "$LOG_FILE"; then
    log "Backup completado: $BACKUP_FILE_HOST"
else
    log "ERROR: Fallo en BACKUP DATABASE"
    exit 1
fi

# Verificar integridad del backup (usa ruta del contenedor)
log "Verificando integridad con RESTORE VERIFYONLY..."
if docker exec dashboard-sqlserver /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U sa -P "$SA_PASSWORD" -C \
    -Q "RESTORE VERIFYONLY FROM DISK = '$BACKUP_FILE_CONTAINER'" 2>&1 | tee -a "$LOG_FILE"; then
    log "Verificación OK"
else
    log "ERROR: Verificación falló"
    exit 1
fi

# Poda de backups antiguos (usa ruta del host)
log "Eliminando backups con más de $RETENTION_DAYS días..."
find "$BACKUP_DIR_HOST" -type f -name "${DB_NAME}_*.bak" -mtime +$RETENTION_DAYS -delete 2>&1 | tee -a "$LOG_FILE"

# Contar backups restantes
COUNT=$(find "$BACKUP_DIR_HOST" -type f -name "${DB_NAME}_*.bak" | wc -l)
log "Backups actuales en disco: $COUNT"
log "=== Backup finalizado ==="