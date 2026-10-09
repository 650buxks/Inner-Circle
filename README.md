# Clique

*Your people, your chats, a little help from AI.*

Clique is a private messaging app for close friends: one-on-one and group chats, photo and video sharing, and a built-in AI assistant (Claude API) that catches you up, helps you write replies, and plans hangouts, only when you ask.

**Status:** Phase 0 (project setup) done. See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for the full feature list, tools, data model and build order.

**Stack:** Python 3.14, Django 6, Django Channels, PostgreSQL, Redis, Celery, Bootstrap, Docker, GitHub Actions. Coming later: HTMX, Cloudinary, Claude API.

## Running it locally

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.

```bash
git clone https://github.com/650buxks/Inner-Circle.git
cd Inner-Circle
cp .env.example .env          # local settings; never commit this file
docker compose up --build     # first run takes a few minutes
```

Open http://localhost:8000. You should see **"Clique is running ✅"** with the database and Redis both showing **ok**.

Press `Ctrl+C` to stop. Next time, `docker compose up` is enough (add `--build` after changing `requirements*.txt`).

### Everyday commands

Run these in a second terminal while `docker compose up` is running:

| Task | Command |
|---|---|
| Run the tests | `docker compose exec web pytest` |
| Check code style | `docker compose exec web ruff check .` |
| Auto-format code | `docker compose exec web ruff format .` |
| Create database migrations after changing models | `docker compose exec web python manage.py makemigrations` |
| Create an admin login for http://localhost:8000/admin/ | `docker compose exec web python manage.py createsuperuser` |
| Open a Django shell | `docker compose exec web python manage.py shell` |
| See logs for one service | `docker compose logs -f worker` |
| Stop and delete the local database | `docker compose down -v` |

## Project layout

```
config/          Django settings, URLs, ASGI (web + WebSockets) and Celery setup
accounts/        User accounts (custom User model)
core/            Home page, /health/ check, shared pieces
templates/       Site-wide HTML templates (base.html)
static/          CSS, JavaScript and images
docs/            Project plan
Dockerfile               How the app's container is built
docker-compose.yml       Local services: web, worker, db (Postgres), redis
.github/workflows/ci.yml Lint and tests on every push
```
