"""Celery runs slow work (AI calls, media processing, emails) in the background.

Settings starting with CELERY_ in config/settings.py are applied here.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("clique")
app.config_from_object("django.conf:settings", namespace="CELERY")
# Finds tasks.py in every installed app.
app.autodiscover_tasks()
