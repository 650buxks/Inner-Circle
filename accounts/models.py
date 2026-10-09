from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """A Clique user.

    For now this is the same as Django's built-in user (username, email, password...).
    Profile fields like display name, bio and avatar get added in Phase 1.
    """
