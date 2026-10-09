import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def check_services():
    """Return {"database": "ok" | "error", "redis": "ok" | "error" | "not configured"}."""
    results = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        results["database"] = "ok"
    except Exception:
        results["database"] = "error"

    if settings.REDIS_URL:
        try:
            redis.from_url(settings.REDIS_URL, socket_connect_timeout=2).ping()
            results["redis"] = "ok"
        except Exception:
            results["redis"] = "error"
    else:
        results["redis"] = "not configured"

    return results


def home(request):
    return render(request, "core/home.html", {"services": check_services()})


def health(request):
    """Used by Render (and you) to check that the app and its services are up."""
    services = check_services()
    healthy = "error" not in services.values()
    return JsonResponse(
        {"status": "ok" if healthy else "error", **services},
        status=200 if healthy else 503,
    )
