from celery import shared_task


@shared_task
def ping():
    """Tiny task used to check that Celery is wired up. Try it in the Django shell:

    >>> from core.tasks import ping
    >>> ping.delay()

    Then look for "succeeded ... 'pong'" in the worker's logs.
    """
    return "pong"
