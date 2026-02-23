#!/bin/sh
python app/create_tables_async.py
# Eliminar carpeta si existe con el nombre del log y crear archivo vacío
if [ -d "/app/heartbeat_errors.log" ]; then
	rm -rf /app/heartbeat_errors.log
fi
touch /app/heartbeat_errors.log
# Ejecutar heartbeat_client.py en segundo plano
python heartbeat_client.py &
# Iniciar la API principal
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
