FROM python:3.9-slim

WORKDIR /app

# Instala dependências de sistema necessárias
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements primeiro para aproveitar cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto da aplicação
COPY . .

CMD ["python", "app.py"]
