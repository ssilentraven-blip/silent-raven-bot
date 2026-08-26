FROM python:3.10-slim

WORKDIR /app

# Instala o git para permitir baixar dependências direto do github
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
