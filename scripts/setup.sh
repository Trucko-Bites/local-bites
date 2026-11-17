#!/usr/bin/env bash
# One-command local setup for Food Truck Finder.
# Run from the repo root after cloning:   ./scripts/setup.sh
# Safe to run again: it never overwrites an existing .env or your data.
set -euo pipefail

# Always run from the repo root, even if called from elsewhere
cd "$(dirname "$0")/.."

echo "==> Checking Docker"
if ! docker info >/dev/null 2>&1; then
  echo "Docker isn't running. Start Docker Desktop, wait for it to finish starting, then run this again." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required ('docker compose', not 'docker-compose')." >&2
  exit 1
fi

echo "==> Checking that ports 5433, 8000 and 5173 are free"
# 5433 = database (host side; a local Postgres on 5432 is fine), 8000 = Django, 5173 = Vite
for required_port in 5433 8000 5173; do
  # Skip the check if this project's own containers are what's using the port
  if lsof -nP -iTCP:"$required_port" -sTCP:LISTEN >/dev/null 2>&1 \
     && ! docker compose ps --status running 2>/dev/null | grep -q "$required_port->"; then
    echo "Port $required_port is already in use by another program or container." >&2
    echo "Find it with:  lsof -nP -iTCP:$required_port -sTCP:LISTEN" >&2
    echo "         or:   docker ps --filter publish=$required_port" >&2
    exit 1
  fi
done

if [ -f .env ]; then
  echo "==> .env already exists, keeping it"
else
  echo "==> Creating .env with a generated secret key and database password"
  generate_secret() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }
  django_secret_key="$(generate_secret 50)"
  database_password="$(generate_secret 24)"
  # Copy the template, then fill in local-development values.
  # token_urlsafe only produces letters, digits, - and _, so it's safe inside sed.
  cp .env.example .env
  sed -i.bak \
    -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=${django_secret_key}|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${database_password}|" \
    -e "s|^DJANGO_DEBUG=.*|DJANGO_DEBUG=true|" \
    .env
  rm -f .env.bak  # sed -i.bak works on both macOS and Linux; remove the backup
fi

echo "==> Building and starting containers (first run takes a few minutes)"
docker compose up -d --build

echo "==> Waiting for the backend to be ready"
for attempt_number in $(seq 1 60); do
  if curl -fsS http://localhost:8000/api/health/ >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt_number" -eq 60 ]; then
    echo "Backend didn't start within 2 minutes. Check:  docker compose logs backend" >&2
    exit 1
  fi
  sleep 2
done

# Migrations already ran when the backend started (entrypoint.sh); this is a no-op
# safety net in case the database container was slow on the first start.
docker compose exec -T backend python manage.py migrate --noinput

echo "==> Loading sample trucks"
docker compose exec -T backend python manage.py seed_food_trucks

echo ""
echo "Done. Everything is running in the background."
echo "  App:    http://localhost:5173"
echo "  Admin:  http://localhost:8000/admin/"
echo ""
echo "Create your own admin login (one time):"
echo "  docker compose exec backend python manage.py createsuperuser"
echo "Watch logs:   docker compose logs -f"
echo "Stop:         docker compose down      (keeps your data)"
