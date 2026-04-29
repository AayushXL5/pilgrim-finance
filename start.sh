#!/bin/bash
set -e

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Seeding demo data ==="
python manage.py seed_demo

echo "=== Starting gunicorn ==="
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8080} \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
