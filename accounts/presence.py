"""Keeps track of who is online.

Two signals together make this reliable:
- a count of open connections, so closing the last tab shows "offline"
  straight away, and
- `last_seen`, refreshed every 30 seconds, so a tab that vanished without
  saying goodbye (crash, lost Wi-Fi) stops counting after ONLINE_WINDOW.
"""

from django.db.models import F
from django.utils import timezone

from .models import User


def connected(user):
    User.objects.filter(pk=user.pk).update(
        open_connections=F("open_connections") + 1,
        last_seen=timezone.now(),
    )


def disconnected(user):
    User.objects.filter(pk=user.pk).update(last_seen=timezone.now())
    # Never go below zero, even if a disconnect is reported twice.
    User.objects.filter(pk=user.pk, open_connections__gt=0).update(
        open_connections=F("open_connections") - 1,
    )


def still_here(user):
    User.objects.filter(pk=user.pk).update(last_seen=timezone.now())
