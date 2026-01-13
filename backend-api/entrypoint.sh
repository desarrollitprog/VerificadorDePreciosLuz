#!/bin/sh
python app/create_tables_async.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
