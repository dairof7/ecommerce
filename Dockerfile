# Usar una imagen base de Python oficial
FROM python:3.12.6-slim-bullseye

# Establecer variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Crear y establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2 y otras
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    # Añade otras dependencias del sistema si son necesarias
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación al directorio de trabajo
COPY . .

# Exponer el puerto en el que Gunicorn se ejecutará dentro del contenedor
EXPOSE 8000

# Comando para ejecutar la aplicación (se puede sobrescribir en docker-compose)
# Este CMD es un fallback. El comando real lo pondremos en docker-compose.
ENTRYPOINT ["/app/entrypoint.sh"] # Ver Paso 5 (Opcional pero recomendado)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "gym_project.wsgi:application"]