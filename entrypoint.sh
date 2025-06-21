#!/bin/sh
# entrypoint.sh (en la raíz de tu proyecto Django, junto al Dockerfile)

echo "Esperando a PostgreSQL..."
# nc (netcat) es una forma de verificar si el puerto está abierto.
# Puede que necesites instalar netcat en tu imagen Docker de Python: apt-get install -y netcat-openbsd o net-tools
# Alternativa más simple: un bucle con sleep, o usar dockerize -wait tcp://db:5432
while ! nc -z db 5432; do # 'db' es el nombre del servicio postgres en docker-compose
  sleep 0.1
done
echo "PostgreSQL iniciado"

echo "Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear 
# --clear es útil para eliminar archivos viejos antes de copiar los nuevos

# echo "Creando superusuario si no existe (esto es un ejemplo, maneja la creación de forma más robusta)..."
# python manage.py createsuperuser_if_none_exists --username=admin --email=admin@example.com --password=adminpass
# (createsuperuser_if_none_exists es un comando personalizado que tendrías que crear)

echo "Iniciando Gunicorn..."
exec gunicorn my_ecommerce.wsgi:application --bind 0.0.0.0:8000 --workers 3