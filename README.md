# Clique

*Your people, your chats, a little help from AI.*

Clique is a private messaging app for close friends: one-on-one and group chats, photo and video sharing, and a built-in AI assistant (Claude API) that catches you up, helps you write replies, and plans hangouts, only when you ask.

**🔗 Live demo:** https://clique-qe18.onrender.com
*(Free hosting: the first visit after a quiet spell can take up to a minute while the server wakes up.)*

**Status:** Phases 0–4 done: accounts, friends, private and group chats, and real-time messaging (live messages, typing indicators, read receipts, online status, live inbox) over WebSockets. Next: photos and videos, then the AI assistant. See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for the full plan.

**Stack:** Python 3.14, Django 6, Django Channels, PostgreSQL, Redis, Celery, Bootstrap, Docker, GitHub Actions, Render. Coming later: HTMX, Cloudinary, Claude API.

## Features so far

- **Accounts:** sign up, log in with username or email, password reset, profile, privacy and account settings, delete account
- **Friends:** search people, friend requests, friends list, blocking
- **Chats:** private and group chats, edit and delete messages, load older messages, group admins and members
- **Real-time (WebSockets):** messages appear instantly, "… is typing", "Seen" read receipts, online status and "last seen", live inbox with unread counts

## Running it locally

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.

```bash
git clone https://github.com/650buxks/Inner-Circle.git
cd Inner-Circle
cp .env.example .env          # local settings; never commit this file
docker compose up --build     # first run takes a few minutes
```

Open http://localhost:8000 to see the Clique landing page. To check that the database and Redis are connected, open http://localhost:8000/health/: both should say **ok**.

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

## Deployment

The live demo runs on free tiers only:

| Part | Service |
|---|---|
| Web app (Django + Daphne, built from the `Dockerfile`) | Render free web service |
| Redis (live messaging between server processes) | Render free Key Value |
| PostgreSQL database | Neon free tier |

The hosting setup is written as code in [`render.yaml`](render.yaml) (a Render Blueprint). Every merge to `main` that passes CI is deployed automatically.

## Project layout

```
config/          Django settings, URLs, ASGI (web + WebSockets) and Celery setup
accounts/        User accounts, profiles, settings, online status
friends/         Friend requests, friends list, blocking
chats/           Private and group chats, WebSocket consumers (real-time)
core/            Home page, /health/ check, shared pieces
templates/       Site-wide HTML templates (base.html)
static/          CSS and JavaScript (live chat and live inbox)
docs/            Project plan
Dockerfile               How the app's container is built
docker-compose.yml       Local services: web, worker, db (Postgres), redis
render.yaml              Hosting setup on Render (infrastructure as code)
.github/workflows/ci.yml Lint and tests on every push
```
