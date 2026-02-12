FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ unixodbc-dev

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


COPY ./app ./app
COPY ./static ./static
COPY .env.dashboard ./

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
