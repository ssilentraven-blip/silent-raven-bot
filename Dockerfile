# Usa uma imagem oficial leve do Python
FROM python:3.10-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as bibliotecas necessárias (Flask, Gunicorn, CCXT, Pandas, Pandas-TA)
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o restante do código do projeto para dentro do container
COPY . .

# Expõe a porta padrão que o Render utiliza
EXPOSE 10000

# Comando para iniciar o servidor web usando o Gunicorn em produção
CMD gunicorn bot:app --bind 0.0.0.0:10000
