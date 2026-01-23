Verificador Precios Luz — backend-api

Instrucciones rápidas (Windows)

Prerequisitos
- Python 3.10+ instalado
- Microsoft ODBC Driver 18 for SQL Server instalado
- SQL Server accesible y credenciales válidas

Pasos

1) Crear y activar entorno virtual (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate
```

2) Instalar dependencias

```powershell
pip install -r requirements.txt
```

3) Configurar variables de entorno
- Edita el archivo `.env` en la raíz de `backend-api` y completa `DB_SERVER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`. Opcional: `DB_DRIVER` (por defecto usa "ODBC Driver 18 for SQL Server").

4) Crear tablas en la base de datos (opcional)

```powershell
python -c "from app.models import Base; from app.database import engine; Base.metadata.create_all(bind=engine)"
```

5) Ejecutar servidor de desarrollo

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6) Opcional: Ejecutar en Docker
- Construir la imagen (no copies .env al build):
```bash
docker build -t verificador-backend .
```
- Correr el contenedor usando tu .env local y exponiendo 8000:
```bash
docker run --name verificador-backend -p 8000:8000 --env-file .env verificador-backend
```
- Si quieres persistir banners: añade `-v /ruta/host/banners:/code/static/banners`

Rutas útiles
- GET /consultas/productos  -> lista productos
- GET /publicidad/banners   -> lista banners desde `static/banners`

Notas
- No incluyas credenciales en commits; usa `.env` y guarda las credenciales localmente.
- Si tienes problemas con la conexión ODBC en Windows, verifica que el driver sea 18 y/o ajusta `DB_DRIVER` en `.env`.

Contacto
- Si quieres, puedo: crear el entorno virtual, instalar dependencias o arrancar la API ahora.
