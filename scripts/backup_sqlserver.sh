#!/bin/bash
# Backup script para SQL Server - DashboardUsuarios
# Se ejecuta via cron en el host: 0 2 * * * /home/desarrolloit/VerificadorDePreciosLuz/scripts/backup_sqlserver.sh

set -euo pipefail

BACKUP_DIR="/home/desarrolloit/VerificadorDePreciosLuz/backups"
LOG_FILE="/tmp/backup_sqlserver.log"
RETENTION_DAYS=14
DB_NAME="DashboardUsuarios"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Iniciando backup de $DB_NAME ==="

# Verificar que el directorio existe
mkdir -p "$BACKUP_DIR"

# Nombre del archivo con timestamp
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.bak"

# Ejecutar backup dentro del contenedor
log "Ejecutando BACKUP DATABASE..."
if docker exec dashboard-sqlserver /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U sa -P "$SA_PASSWORD" -C \
    -Q "BACKUP DATABASE [$DB_NAME] TO DISK = '$BACKUP_FILE' WITH INIT, COMPRESSION, CHECKSUM" 2>&1 | tee -a "$LOG_FILE"; then
    log "Backup completado: $BACKUP_FILE"
else
    log "ERROR: Fallo en BACKUP DATABASE"
    exit 1
fi

# Verificar integridad del backup
log "Verificando integridad con RESTORE VERIFYONLY..."
if docker exec dashboard-sqlserver /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U sa -P "$SA_PASSWORD" -C \
    -Q "RESTORE VERIFYONLY FROM DISK = '$BACKUP_FILE'" 2>&1 | tee -a "$LOG_FILE"; then
    log "Verificación OK"
else
    log "ERROR: Verificación falló"
    exit 1
fi

# Poda de backups antiguos
log "Eliminando backups con más de $RETENTION_DAYS días..."
find "$BACKUP_DIR" -type f -name "${DB_NAME}_*.bak" -mtime +$RETENTION_DAYS -delete 2>&1 | tee -a "$LOG_FILE"

# Contar backups restantes
COUNT=$(find "$BACKUP_DIR" -type f -name "${DB_NAME}_*.bak" | wc -l)
log "Backups actuales en disco: $COUNT"
log "=== Backup finalizado ==="