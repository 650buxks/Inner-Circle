# The recipe for Clique's container image, used locally and in production.
FROM python:3.14-slim

# Print logs straight away and don't write .pyc files.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install packages first so Docker can reuse this layer when only code changes.
# DEV=true (set by docker-compose.yml) also installs test and lint tools.
ARG DEV=false
COPY requirements.txt requirements-dev.txt ./
RUN if [ "$DEV" = "true" ]; then pip install -r requirements-dev.txt; \
    else pip install -r requirements.txt; fi

COPY . .

# Gather CSS/JS into staticfiles/ for WhiteNoise. The key here is only for this step.
RUN SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput

# Don't run the app as root.
RUN useradd --create-home clique && chown -R clique /app
USER clique

EXPOSE 8000

# Production server. Render sets $PORT; locally it defaults to 8000.
CMD ["sh", "-c", "python manage.py migrate --noinput && daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application"]
