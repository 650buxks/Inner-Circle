from django.conf import settings
from django.db import models


class FriendRequest(models.Model):
    """A friend request that hasn't been answered yet.

    Accepting it makes the two users friends and deletes the request.
    Declining or cancelling it just deletes it.
    """

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friend_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Only one request from the same person to the same person.
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                name="one_request_per_pair",
            ),
            # Nobody can send a request to themselves.
            models.CheckConstraint(
                condition=~models.Q(from_user=models.F("to_user")),
                name="no_request_to_self",
            ),
        ]

    def __str__(self):
        return f"{self.from_user} → {self.to_user}"
