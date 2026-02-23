#!/bin/sh
python app/create_tables_async.py
LOG_PATH="/app/heartbeat_errors.log"
# Si existe como carpeta, eliminarla
if [ -d "$LOG_PATH" ]; then
	rm -rf "$LOG_PATH"
fi
# Si existe como archivo, dejarlo; si no, crearlo vacío
if [ ! -f "$LOG_PATH" ]; then
	touch "$LOG_PATH"
fi
# Ejecutar heartbeat_client.py en segundo plano
python heartbeat_client.py &
# Iniciar la API principal
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
