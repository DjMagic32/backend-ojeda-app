#!/usr/bin/env bash
set -e  # si algo falla, la imagen no arranca

echo "⏳ Generando migraciones necesarias…"
python manage.py makemigrations usuarios  # tu app de usuario
python manage.py makemigrations           # el resto
python manage.py migrate --noinput

echo "⏳ Creando super-usuario (si no existe)…"
python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
import os, sys

User = get_user_model()
email     = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
username  = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
password  = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin123")

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"✅ Super-usuario creado: {email}")
else:
    print(f"ℹ️  El super-usuario {email} ya existe.")
PY

echo "⏳ Recolectando archivos estáticos…"
python manage.py collectstatic --noinput

echo "🚀 Arrancando servidor…"
exec gunicorn tu_proyecto.wsgi:application --bind 0.0.0.0:8000
