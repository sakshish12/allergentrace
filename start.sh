#!/bin/sh
# Start-up of the web container. Each step is logged, so a slow or failing step is visible.
set -e
echo "[start] applying database migrations"
python manage.py migrate --noinput
echo "[start] giving existing rows a history snapshot if they have none (US-12)"
python manage.py populate_history --auto
echo "[start] starting web server on port ${PORT:-8000}"
exec gunicorn config.wsgi --bind "0.0.0.0:${PORT:-8000}" --workers 2
