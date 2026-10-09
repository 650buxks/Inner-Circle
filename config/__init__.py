# Load the Celery app whenever Django starts, so @shared_task functions register with it.
from .celery import app as celery_app

__all__ = ("celery_app",)
