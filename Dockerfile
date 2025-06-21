# backend/Dockerfile
FROM python:3.12.6-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instalar dependencias del sistema (incluyendo netcat para el entrypoint)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libwebp-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt y entrypoint.sh primero
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY . .
RUN chmod +x entrypoint.sh

# Exponer el puerto que usará Gunicorn
EXPOSE 8000

# El ENTRYPOINT ejecutará el script que a su vez ejecutará Gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]