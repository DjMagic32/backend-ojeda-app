#!/bin/sh
set -e

if [ "${AUTO_MIGRATE:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi

python manage.py collectstatic --noinput

exec daphne -b 0.0.0.0 -p "${PORT:-8000}" backend_ojeda.asgi:application
