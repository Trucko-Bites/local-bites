# Contributing

## Who owns what

| Area | Folders and files |
|---|---|
| Geolocation / API | `backend/` (Django, PostGIS, radius search, owner check-in, tests) |
| Frontend | `frontend/src/`, `frontend/package.json`, `frontend/vite.config.js`, `frontend/index.html` |
| Scaffolding | `docker-compose*.yml`, `.env.example`, `scripts/`, both `Dockerfile`s, `backend/entrypoint.sh`, `frontend/Caddyfile`, `DEVELOPMENT.md`, this file |

Owning an area means reviewing changes to it, not being the only person allowed to touch it. `.github/CODEOWNERS` requests those reviews automatically.

## First-time setup

Requires Docker Desktop (running) and git. Any terminal works: Terminal or VS Code on a Mac, and PowerShell (VS Code's default on Windows), Git Bash, or WSL on Windows. Git and `docker compose` commands are the same in every terminal; only the setup script differs.

1. Clone. Paste as one block, in any terminal:

   ```bash
   git clone https://github.com/Trucko-Bites/local-bites.git
   cd local-bites
   ```

2. Run setup, single command.

   Mac, Linux, Git Bash, or WSL:

   ```bash
   ./scripts/setup.sh
   ```

   Windows PowerShell (including VS Code's terminal on Windows):

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
   ```

   `-ExecutionPolicy Bypass` is needed because Windows blocks running script files by default. It applies to this one run only and changes no system setting.

Both scripts do the same thing: create `.env` with a generated secret key, build and start the containers, run migrations, and load sample trucks. Running either again is safe: it never overwrites `.env` or data.

Then create an admin login (single command; it prompts for a username and password):

```bash
docker compose exec backend python manage.py createsuperuser
```

- App: http://localhost:5173
- Admin: http://localhost:8000/admin/

## Everyday workflow

1. Start from an up-to-date `main`. Paste as one block:

   ```bash
   git switch main
   git pull
   ```

2. Create a branch named for the change (single command):

   ```bash
   git switch -c feature/short-description
   ```

3. Make changes. Vite (frontend) and Django (backend) reload automatically; there's no need to restart containers for code changes.
4. Run the checks for the area that changed, one command at a time:

   ```bash
   docker compose exec backend python manage.py test trucks
   docker compose exec frontend npm run lint
   ```

5. Commit and push. Paste as one block, after editing the message:

   ```bash
   git add -A
   git commit -m "Describe what changed and why"
   git push -u origin HEAD
   ```

6. Open a pull request on GitHub into `main`. A teammate reviews and merges it.

## When something changes underneath

- **New Python package** (`backend/requirements.txt` changed): `docker compose up -d --build backend`
- **New npm package** (`frontend/package.json` changed): `docker compose exec frontend npm install`
- **New migration** (a file appeared in `backend/trucks/migrations/`): `docker compose exec backend python manage.py migrate`
- **Model change made locally**: `docker compose exec backend python manage.py makemigrations trucks`, then commit the new migration file with the model change.

## Rules that prevent most problems

- Never commit `.env`. It's in `.gitignore`; it holds secrets.
- One branch per change, kept small. Pull `main` often to stay current.
- `docker compose down -v` deletes the database volume and all local data. Plain `docker compose down` keeps it.
