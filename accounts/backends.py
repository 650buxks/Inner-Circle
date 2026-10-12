from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Lets people log in with either their username or their email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        User = get_user_model()
        # Try the exact username first, then the email (any upper/lower case).
        user = (
            User.objects.filter(username=username).first()
            or User.objects.filter(email__iexact=username).first()
        )
        if user is None:
            # Hash the password anyway so a wrong username takes as long as a
            # wrong password. Otherwise attackers could time requests to learn
            # which usernames exist.
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
