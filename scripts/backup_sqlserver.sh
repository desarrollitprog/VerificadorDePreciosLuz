#!/bin/bash
# Backup script para SQL Server - DashboardUsuarios
# Se ejecuta via cron en el host: 0 2 * * * /home/desarrolloit/VerificadorDePreciosLuz/scripts/backup_sqlserver.sh
# NOTA: SQL Server en Docker no puede escribir directamente a bind mounts.
# Workaround: backup a /tmp dentro del contenedor y copiar con docker cp.

set -euo pipefail

# Cargar variables de entorno
source /home/desarrolloit/VerificadorDePreciosLuz/.env

BACKUP_DIR="/home/desarrolloit/VerificadorDePreciosLuz/backups"
LOG_FILE="/tmp/backup_sqlserver.log"
RETENTION_DAYS=14
DB_NAME="DashboardUsuarios"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Iniciando backup de $DB_NAME ==="

# Verificar que el directorio existe en el host
mkdir -p "$BACKUP_DIR"

# Nombre del archivo con timestamp
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE_HOST="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.bak"
BACKUP_FILE_CONTAINER="/tmp/${DB_NAME}_${TIMESTAMP}.bak"

# Ejecutar backup dentro del contenedor a /tmp (funciona en Docker)
log "Ejecutando BACKUP DATABASE a /tmp..."
if docker exec -u 999 dashboard-sqlserver /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U sa -P "$SA_PASSWORD" -C \
    -Q "BACKUP DATABASE [$DB_NAME] TO DISK = '/tmp/${DB_NAME}_${TIMESTAMP}.bak' WITH INIT, COMPRESSION, CHECKSUM" 2>&1 | tee -a "$LOG_FILE"; then
    log "Backup completado en contenedor: /tmp/${DB_NAME}_${TIMESTAMP}.bak"
else
    log "ERROR: Fallo en BACKUP DATABASE"
    exit 1
fi

# Copiar el backup del contenedor al host
log "Copiando backup del contenedor al host..."
if docker cp "dashboard-sqlserver:/tmp/${DB_NAME}_${TIMESTAMP}.bak" "$BACKUP_FILE_HOST" 2>&1 | tee -a "$LOG_FILE"; then
    log "Backup copiado al host: $BACKUP_FILE_HOST"
else
    log "ERROR: Fallo al copiar backup del contenedor"
    exit 1
fi

# Verificar integridad del backup en el host
log "Verificando integridad con RESTORE VERIFYONLY..."
# Copiar de vuelta al contenedor para verificación
docker cp "$BACKUP_FILE_HOST" "dashboard-sqlserver:/tmp/${DB_NAME}_${TIMESTAMP}_verify.bak" 2>&1 | tee -a "$LOG_FILE"
if docker exec -u 999 dashboard-sqlserver /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U sa -P "$SA_PASSWORD" -C \
    -Q "RESTORE VERIFYONLY FROM DISK = '/tmp/${DB_NAME}_${TIMESTAMP}_verify.bak'" 2>&1 | tee -a "$LOG_FILE"; then
    log "Verificación OK"
    # Limpiar archivo temporal de verificación
    docker exec -u 999 dashboard-sqlserver rm -f "/tmp/${DB_NAME}_${TIMESTAMP}_verify.bak"
else
    log "ERROR: Verificación falló"
    exit 1
fi

# Limpiar archivo temporal en el contenedor
docker exec -u 999 dashboard-sqlserver rm -f "/tmp/${DB_NAME}_${TIMESTAMP}.bak"

# Poda de backups antiguos
log "Eliminando backups con más de $RETENTION_DAYS días..."
find "$BACKUP_DIR" -type f -name "${DB_NAME}_*.bak" -mtime +$RETENTION_DAYS -delete 2>&1 | tee -a "$LOG_FILE"

# Contar backups restantes
COUNT=$(find "$BACKUP_DIR" -type f -name "${DB_NAME}_*.bak" | wc -l)
log "Backups actuales en disco: $COUNT"
log "=== Backup finalizado ==="