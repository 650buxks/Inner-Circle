from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    A Clique user: Django's built-in user plus profile and AI settings.
    """

    display_name = models.CharField(max_length=50, blank=True)
    bio = models.TextField(max_length=300, blank=True)
    status_message = models.CharField(max_length=80, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    ai_opt_out = models.BooleanField(default=False)
    smart_replies_on = models.BooleanField(default=True)

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
