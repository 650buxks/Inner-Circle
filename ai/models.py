from django.conf import settings
from django.db import models


class AIRequest(models.Model):
    """One use of Clique AI. Used for daily limits and to keep an eye on
    cost (Claude charges per token)."""

    class Feature(models.TextChoices):
        CATCH_UP = "catch_up", "Catch me up"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_requests",
    )
    feature = models.CharField(max_length=20, choices=Feature.choices)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user} · {self.get_feature_display()}"
