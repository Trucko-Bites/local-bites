#!/bin/sh
# Runs every time the backend container starts.
set -e

# Apply any new migrations before serving traffic.
# The compose healthcheck on "db" makes sure Postgres is ready first.
python manage.py migrate --noinput

# Create the database cache table (settings.CACHES). Safe to run every start:
# it skips the table if it already exists and never deletes cached rows.
python manage.py createcachetable

# Hand off to the CMD (gunicorn in prod, runserver in dev)
exec "$@"
