#!/bin/sh

set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Applying migrations..."
  python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

if [ "${CREATE_SUPERUSER:-0}" = "1" ]; then
  echo "Ensuring superuser exists..."
  python manage.py shell << EOF
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

if username and email and password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print("Superuser created")
EOF
fi

echo "Starting process..."
exec "$@"
