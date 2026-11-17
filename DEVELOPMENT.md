# Development guide

Find food trucks within a chosen radius of the user's live location.

Stack: Django + DRF + GeoDjango (PostGIS) API, React + MUI + Leaflet frontend, Docker Compose locally and on a single EC2 instance, with Caddy for HTTPS.

## How the pieces fit

```
Browser ──HTTPS──> Caddy (web container)
                    ├── /            -> built React app (static files)
                    ├── /api/*       -> Django + gunicorn (backend container)
                    └── /admin*      -> Django admin
                                         │
                                         └──> PostgreSQL + PostGIS (db container)
```

- **Radius search** runs in PostGIS: `location__dwithin` uses the GiST index, then results are sorted by distance (see `backend/trucks/views.py`).
- **Geofencing** runs in the browser: `navigator.geolocation.watchPosition` re-queries the API as the user moves (see `frontend/src/hooks/useUserLocation.js`).
- **One origin.** React calls `/api/...` on the same host, through Vite's proxy in dev and Caddy in prod, so no CORS setup is needed.

## Project layout

```
local-bites/
├── docker-compose.yml        # dev: db + Django runserver + Vite dev server
├── docker-compose.prod.yml   # EC2: db + gunicorn + Caddy (HTTPS)
├── .env.example              # template; the setup script creates .env from it
├── scripts/
│   ├── setup.sh              # one-command local setup (Mac, Linux, Git Bash, WSL)
│   └── setup.ps1             # same steps for Windows PowerShell / VS Code on Windows
├── CONTRIBUTING.md           # team workflow: branch, commit, pull request
├── .github/CODEOWNERS        # who reviews which folder
├── backend/
│   ├── Dockerfile            # python:3.13-slim + GDAL/GEOS/PROJ
│   ├── entrypoint.sh         # runs migrations on every start
│   ├── requirements.txt
│   ├── config/               # settings.py (env-driven), urls.py
│   └── trucks/               # model, serializers, views, permissions, login, tests,
│                             # management/commands/seed_food_trucks.py
└── frontend/
    ├── Dockerfile            # build React, then serve with Caddy
    ├── Caddyfile             # HTTPS + reverse proxy rules
    ├── vite.config.js        # dev proxy /api -> Django
    └── src/
        ├── api/              # apiRequest (CSRF + session), auth, foodTrucks
        ├── hooks/useUserLocation.js
        └── components/       # FoodTruckMap (Leaflet), FoodTruckList, OwnerPanel (MUI)
```

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/trucks/nearby/?latitude=34.0556&longitude=-117.1825&radius_miles=5` | Closest first, max 50 mi, optional `open_only=true` |
| GET | `/api/trucks/` | Paginated GeoJSON |
| POST | `/api/trucks/` | Login required; creator becomes owner |
| PUT/PATCH/DELETE | `/api/trucks/<id>/` | Owner or staff only |
| GET | `/api/trucks/mine/` | Trucks the logged-in user can check in (staff: all) |
| POST | `/api/trucks/<id>/check-in/` | Owner or staff. Body: `latitude`, `longitude`, `open_until` (ISO time, within 18 hours) |
| POST | `/api/trucks/<id>/check-out/` | Owner or staff. Closes now |
| GET | `/api/auth/csrf/` | Sets the `csrftoken` cookie |
| POST | `/api/auth/login/` | `username`, `password`; needs `X-CSRFToken` header |
| POST | `/api/auth/logout/` | |
| GET | `/api/auth/me/` | Current user, or 403 when logged out |
| GET | `/api/health/` | Health check |

Responses are GeoJSON. Each truck's `geometry.coordinates` is `[longitude, latitude]`. A truck is reported `is_open: false` once its `open_until` time passes, even if the owner never checked out.

## Owner check-in

1. Owner accounts are regular Django users. Create one in the admin (**Users → Add**), then open a truck and set its **Owner** to that user. Staff accounts (like the superuser) can check in any truck.
2. In the app, **Owner** (top right) opens the check-in panel. After logging in, the owner sets a closing time and taps **I'm here**: the phone's location becomes the truck's location, and the truck opens until that time.
3. Customers' maps pick up the change at their next refresh (every 30 seconds). **Close now** closes the truck immediately; otherwise it closes automatically at the closing time.

Login uses Django's session cookie. The React app and API share one origin (Vite's proxy locally, Caddy on EC2), so no tokens are stored in the browser and CSRF protection applies to every change.

Load sample trucks around Redlands for development (single command; safe to run more than once, never touches hand-entered trucks):

```bash
docker compose exec backend python manage.py seed_food_trucks
```

## Run locally

Requires Docker Desktop (running) with Compose v2. Ports 5433, 8000, and 5173 must be free. The database is published on **5433** (not the usual 5432), so a local or homebrew Postgres on 5432 can keep running; connect psql, DBeaver or DataGrip to `localhost:5433` with the `POSTGRES_USER`/`POSTGRES_PASSWORD` from `.env`. On Apple Silicon, the PostGIS container runs under amd64 emulation (pinned in the compose files): it works, but its first start is slower.

From the repo root, run the setup script for the terminal in use (single command). It creates `.env` with generated secrets, builds and starts the containers in the background, runs migrations, and loads sample trucks. It is safe to run again; it never overwrites `.env` or data.

Mac, Linux, Git Bash, or WSL:

```bash
./scripts/setup.sh
```

Windows PowerShell (including VS Code's terminal on Windows). `-ExecutionPolicy Bypass` applies to this one run only; Windows blocks script files by default:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Hot reload inside Docker uses file polling (`VITE_WATCH_USE_POLLING` in `docker-compose.yml`), because file-change events from a Windows or macOS host don't always reach the container.

Then create an admin login with this single command (it prompts for a username and password):

```bash
docker compose exec backend python manage.py createsuperuser
```

Then open:

- App: http://localhost:5173 (geolocation works on localhost)
- Admin: http://localhost:8000/admin/

Run the backend tests (single command):

```bash
docker compose exec backend python manage.py test trucks
```

## Deploy to EC2

**HTTPS is required, not optional.** Browsers only give location to pages served over HTTPS (or localhost). Over plain `http://<ec2-ip>`, the map loads but always shows the fallback location. Caddy gets the certificate automatically once a domain points at the instance.

1. **Launch an instance.** Ubuntu 24.04 LTS. t3.small (2 GB RAM) is a sensible starting size, because 1 GB instances can run out of memory during the React build.
2. **Security group.** Inbound 22 (SSH, your IP only), 80, and 443 (TCP and UDP) from anywhere. Do not open 5432.
3. **Elastic IP.** Allocate one and attach it, so the address survives a stop or start.
4. **DNS.** Create an `A` record (e.g. `trucks.example.com`) pointing at the Elastic IP *before* first start. Caddy needs it to issue the certificate.
5. **Install Docker** with Docker's official apt repository. This block can be pasted as one block on the instance:

   ```bash
   sudo apt update
   sudo apt install -y ca-certificates curl git
   sudo install -m 0755 -d /etc/apt/keyrings
   sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
   sudo chmod a+r /etc/apt/keyrings/docker.asc
   sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
   Types: deb
   URIs: https://download.docker.com/linux/ubuntu
   Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
   Components: stable
   Architectures: $(dpkg --print-architecture)
   Signed-By: /etc/apt/keyrings/docker.asc
   EOF
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   sudo usermod -aG docker "$USER"
   ```

   Log out and back in so the `docker` group takes effect.

6. **Clone and configure.** Run these one at a time:

   ```bash
   git clone https://github.com/<your-account>/food-truck-finder.git
   cd food-truck-finder
   cp .env.example .env
   nano .env
   ```

   Set these values in `.env`:
   - `POSTGRES_PASSWORD`: a long random string
   - `DJANGO_SECRET_KEY`: generate with `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
   - `DJANGO_DEBUG=false`
   - `DJANGO_ALLOWED_HOSTS=trucks.example.com`
   - `DJANGO_CSRF_TRUSTED_ORIGINS=https://trucks.example.com`
   - `DJANGO_SECURE_COOKIES=true` (login cookies only travel over HTTPS; leave `false` if testing over plain `http://`, or owner login won't stick)
   - `SITE_ADDRESS=trucks.example.com`
   - `VITE_TILE_URL`: a hosted tile provider URL (see below)

7. **Start (single command).**

   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

8. **Create the admin user (single command).**

   ```bash
   docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
   ```

9. **Check it.** `https://trucks.example.com/api/health/` should return `{"status": "ok"}`. To watch Caddy obtain the certificate, run `docker compose -f docker-compose.prod.yml logs -f web`.

### Updating after a code change (single command, run in the project folder)

```bash
git pull && docker compose -f docker-compose.prod.yml up -d --build
```

Migrations run automatically when the backend container starts.

### Data safety

- **Warning: `docker compose down -v` permanently deletes the database and the HTTPS certificates.** The `-v` flag removes the named volumes `postgres_data` and `caddy_data`. Use plain `docker compose -f docker-compose.prod.yml down` to stop the stack and keep the data.
- The database lives only on the instance's disk. Back it up before relying on it:
  `docker compose -f docker-compose.prod.yml exec db pg_dump -U food_trucks food_trucks > backup.sql`

## Map tiles

`FoodTruckMap.jsx` uses OpenStreetMap's public tile server when `VITE_TILE_URL` is blank. That is fine for development, but the OSMF tile policy offers no SLA and blocks heavy users. For production, set `VITE_TILE_URL` to a hosted provider that serves OSM-based tiles, then rebuild the `web` image. The OpenStreetMap attribution must stay visible.

## Next steps

- Owner self-signup (today, owner accounts are created in the admin)
- Truck details editing from the owner panel (name, cuisine, description)
- Push or in-app alerts when an open truck enters the user's radius
