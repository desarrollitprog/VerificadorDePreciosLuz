#!/bin/sh
python app/create_tables_async.py
# Ejecutar heartbeat_client.py en segundo plano
python heartbeat_client.py &
# Iniciar la API principal
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
