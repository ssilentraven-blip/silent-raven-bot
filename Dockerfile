FROM python:3.10-slim

WORKDIR /app

# Instala o git para permitir dependências via repositório
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD gunicorn bot:app --bind 0.0.0.0:10000
