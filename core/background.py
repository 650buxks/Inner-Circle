"""Running slow work (like asking Claude) without making anyone wait."""

import threading

from django.conf import settings
from django.db import connection


def run_in_background(task, *args):
    """Run a Celery task in the background.

    Locally, the Celery worker picks it up from Redis. Render's free plan
    has no worker (CELERY_TASK_ALWAYS_EAGER is on), so there it runs in a
    separate thread instead, which still lets the chat carry on.
    """
    if settings.CELERY_TASK_ALWAYS_EAGER:
        thread = threading.Thread(
            target=_run_then_close,
            args=(task, args),
            daemon=True,
        )
        thread.start()
    else:
        task.delay(*args)


def _run_then_close(task, args):
    try:
        task(*args)
    finally:
        # Each thread opens its own database connection; close it.
        connection.close()
