#!/bin/sh
# backend/entrypoint.sh
set -e

echo "Esperando a PostgreSQL en $POSTGRES_HOST:$POSTGRES_PORT..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  echo "PostgreSQL no está listo todavía, esperando..."
  sleep 1
done
echo "PostgreSQL iniciado y listo."

# La variable 'SERVICE_TYPE' se definirá en docker-compose.yml
# para diferenciar qué tareas de inicialización ejecutar.
if [ "$SERVICE_TYPE" = "backend" ]; then
  echo "Running as BACKEND service. Applying migrations and collecting static files..."
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput --clear
elif [ "$SERVICE_TYPE" = "celery_beat" ]; then
  echo "Running as CELERY BEAT service. Skipping migrations and collectstatic."
  # Opcional: podrías querer limpiar PID files antiguos de Celery Beat
  rm -f /app/celerybeat.pid
else
  echo "Running as CELERY WORKER (or other) service. Skipping migrations and collectstatic."
fi

# El 'exec "$@"' es la parte CRUCIAL.
# Ejecuta el comando que se pasó al contenedor, reemplazando el proceso actual del script.
# Este comando vendrá de la sección 'command:' en tu docker-compose.yml.
echo "Iniciando el comando principal: $@"
exec "$@"