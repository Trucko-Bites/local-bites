#!/bin/sh
# Runs every time the backend container starts.
set -e

# Apply any new migrations before serving traffic.
# The compose healthcheck on "db" makes sure Postgres is ready first.
python manage.py migrate --noinput

# Hand off to the CMD (gunicorn in prod, runserver in dev)
exec "$@"
