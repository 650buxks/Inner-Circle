import uuid
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.timesince import timesince

# Open chat pages "check in" every 30 seconds. If we hear nothing for this
# long, the person counts as offline even if their tab never said goodbye
# (for example, the laptop went to sleep).
ONLINE_WINDOW = timedelta(seconds=90)


def avatar_path(user, filename):
    """Where a profile photo is saved, e.g. avatars/7/3f9c…e1.jpg."""
    extension = Path(filename).suffix.lower()
    return f"avatars/{user.pk}/{uuid.uuid4().hex}{extension}"


class User(AbstractUser):
    """
    A Clique user: Django's built-in user plus profile and AI settings.
    """

    class RequestsFrom(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        FRIENDS_OF_FRIENDS = "friends_of_friends", "Friends of friends only"

    MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB

    display_name = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(
        "profile photo",
        upload_to=avatar_path,
        blank=True,
    )
    bio = models.TextField(max_length=300, blank=True)
    status_message = models.CharField(max_length=80, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    # How many live connections (open chat tabs) this person has right now.
    open_connections = models.PositiveIntegerField(default=0)
    ai_opt_out = models.BooleanField(default=False)
    smart_replies_on = models.BooleanField(default=True)
    friend_requests_from = models.CharField(
        max_length=20,
        choices=RequestsFrom.choices,
        default=RequestsFrom.EVERYONE,
    )

    # Friendship goes both ways: adding Jordan to Francis's friends also
    # adds Francis to Jordan's ("symmetrical" is on by default for "self").
    friends = models.ManyToManyField("self", blank=True)
    # Blocking only goes one way, so it isn't symmetrical. People who blocked
    # this user are available as user.blocked_by.
    blocked_users = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="blocked_by",
        blank=True,
    )

    @property
    def name(self):
        """
        The name to show in the app: display name if set, otherwise username.
        """
        if self.display_name:
            return self.display_name
        return self.username

    @property
    def is_online(self):
        if not self.open_connections or self.last_seen is None:
            return False
        return timezone.now() - self.last_seen < ONLINE_WINDOW

    @property
    def presence(self):
        """Status text for chat pages.

        "Online", "Last seen 5 minutes ago", or "" if never seen.
        """
        if self.is_online:
            return "Online"
        if self.last_seen is None:
            return ""
        if timezone.now() - self.last_seen < timedelta(minutes=1):
            return "Last seen just now"
        # depth=1 keeps it short: "2 hours", not "2 hours, 5 minutes".
        # timesince joins "2\xa0hours" with a non-breaking space; swap it
        # for a normal one.
        ago = timesince(self.last_seen, depth=1).replace("\xa0", " ")
        return f"Last seen {ago} ago"
