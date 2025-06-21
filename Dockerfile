
# Dockerfile (para el backend Django)
FROM python:3.12.6-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN groupadd -r django && useradd -r -g django django
# Instalar dependencias del sistema si son necesarias (ej. para Pillow, psycopg2)
# RUN apt-get update && apt-get install -y libpq-dev gcc python3-dev musl-dev jpeg-dev zlib1g-dev libwebp-dev libimagequant-dev

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libwebp-dev \
    # ... otras que puedas necesitar según los formatos de imagen ...
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Exponer el puerto que usará Gunicorn
EXPOSE 8000

COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Comando por defecto (se puede sobrescribir en docker-compose.yml)
# Esto asume que tienes un script entrypoint.sh o que gunicorn está en el PATH
# CMD ["gunicorn", "my_ecommerce.wsgi:application", "--bind", "0.0.0.0:8000"]

USER django

ENTRYPOINT ["/app/entrypoint.sh"]