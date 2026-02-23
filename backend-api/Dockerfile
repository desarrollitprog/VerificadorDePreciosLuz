
# Imagen base de Python
FROM python:3.11-slim

ENV ACCEPT_EULA=Y

# Instalar ODBC Driver 18 para SQL Server y dependencias para aioodbc
RUN apt-get update && apt-get install -y curl gnupg apt-transport-https unixodbc-dev gcc g++ \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /code

# Copiar requirements primero para aprovechar caché
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt


# Crear el directorio /app para logs y otros archivos
RUN mkdir -p /app

# Copiar el resto del código (no incluir .env en builds)
COPY . .

# Copiar entrypoint personalizado
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]