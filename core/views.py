import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render


def photo_storage():
    """Where uploaded photos are saved: "cloudinary", "local", or
    "misconfigured" if the Cloudinary setting is there but written wrongly.

    Production needs "cloudinary": files saved on Render's own disk vanish
    at the next deploy.
    """
    url = settings.CLOUDINARY_URL
    if not url:
        return "local"
    # The right format is cloudinary://API_KEY:API_SECRET@CLOUD_NAME
    if not url.startswith("cloudinary://") or "@" not in url or " " in url:
        return "misconfigured"
    if "<" in url:  # placeholders like <your_api_secret> left in
        return "misconfigured"
    return "cloudinary"


def check_services():
    """Return {"database": "ok" | "error", "redis": "ok" |
    "error" | "not configured"}."""
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
    results["photos"] = photo_storage()
    results["ai"] = "ready" if settings.ANTHROPIC_API_KEY else "not set up"
    return results


def home(request):
    # Logged-in people go straight to their chats.
    if request.user.is_authenticated:
        return redirect("chats:inbox")
    return render(request, "core/home.html")


def health(request):
    """
    Used by Render (and you) to check that the app
    and its services are up.
    """
    services = check_services()
    healthy = "error" not in services.values()
    return JsonResponse(
        {"status": "ok" if healthy else "error", **services},
        status=200 if healthy else 503,
    )
