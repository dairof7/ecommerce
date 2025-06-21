#!/bin/sh
# backend/entrypoint.sh
set -e

echo "Esperando a PostgreSQL en db:5432..."
while ! nc -z db 5432; do
  echo "PostgreSQL no está listo todavía, esperando..."
  sleep 1
done
echo "PostgreSQL iniciado y listo."

echo "Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

echo "Iniciando Gunicorn en 0.0.0.0:8000..."
exec gunicorn my_ecommerce.wsgi:application --bind 0.0.0.0:8000 --workers 3 --log-level info --access-logfile - --error-logfile -