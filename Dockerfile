# backend/Dockerfile
FROM python:3.12.6-slim-bullseye

# Establecer variables de entorno para una mejor ejecución de Python en Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema operativo
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencias para compilar paquetes (como psycopg2)
    build-essential \
    libpq-dev \
    # Dependencias para Pillow (manejo de imágenes)
    libjpeg-dev \
    zlib1g-dev \
    libwebp-dev \
    # --- DEPENDENCIAS PARA WEASYPRINT ---
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    # 'gobject' y sus dependencias son usualmente instaladas por las anteriores,
    # pero podemos ser explícitos si es necesario.
    # libgirepository1.0-dev
    # Herramienta útil para el script de entrypoint
    netcat-openbsd \
    # Limpiar el caché de apt para mantener la imagen pequeña
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos primero para aprovechar el caché de Docker
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el script de entrypoint y darle permisos de ejecución
COPY . .
RUN chmod +x entrypoint.sh

# Copiar el resto del código de la aplicación
# Exponer el puerto que Gunicorn usará
EXPOSE 8000

# El ENTRYPOINT ejecutará el script que espera a la BD y luego inicia Gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]