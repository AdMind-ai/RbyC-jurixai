#!/bin/sh

set -e  

echo "💡 Aplicando migrações..."
python manage.py migrate --noinput

echo "💡 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "Criando superusuário..."
python manage.py shell << EOF
import os
from django.contrib.auth import get_user_model

User = get_user_model()
# Superuser
username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print("✅ Superuser created")

EOF

echo "🚀 Iniciando servidor Gunicorn..."
exec "$@"
# exec gunicorn backend.wsgi:application --bind 0.0.0.0:8000