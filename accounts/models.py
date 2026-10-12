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

    @property
    def name(self):
        """
        The name to show in the app: display name if set, otherwise username.
        """
        if self.display_name:
            return self.display_name
        return self.username
