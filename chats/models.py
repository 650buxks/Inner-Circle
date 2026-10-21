import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    """A private chat between two people, or a group chat."""

    class Kind(models.TextChoices):
        PRIVATE = "private", "Private"
        GROUP = "group", "Group"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    name = models.CharField(max_length=60, blank=True)  # groups only
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Membership",
        related_name="conversations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    # For private chats only: "smaller user id:bigger user id". Being unique
    # means two people can never end up with two separate private chats.
    private_key = models.CharField(
        max_length=40,
        unique=True,
        null=True,
        blank=True,
    )
    ai_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Moves forward with every new message, so the inbox can sort by it.
    last_activity_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        ordering = ["-last_activity_at"]

    def __str__(self):
        if self.kind == self.Kind.GROUP:
            return self.name
        return f"Private chat {self.private_key}"


class Membership(models.Model):
    """One person's place in a conversation."""

    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        ADMIN = "admin", "Admin"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    # Messages after this time count as unread.
    last_read_at = models.DateTimeField(null=True, blank=True)
    muted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="one_membership_per_person",
            ),
        ]

    def __str__(self):
        return f"{self.user} in {self.conversation}"


def photo_path(message, filename):
    """Where a chat photo is saved, e.g. chats/12/3f9c…e1.jpg.

    The random name means nobody can guess the address of someone else's
    photo, and two photos called "IMG_0001.jpg" never clash.
    """
    extension = Path(filename).suffix.lower()
    return f"chats/{message.conversation_id}/{uuid.uuid4().hex}{extension}"


class Message(models.Model):
    class Kind(models.TextChoices):
        TEXT = "text", "Text"
        SYSTEM = "system", "System"  # e.g. "Sam added Jordan"
        AI = "ai", "Clique AI"

    MAX_LENGTH = 4000
    MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    # SET_NULL keeps messages when an account is deleted; they then show as
    # "Deleted user".
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )
    kind = models.CharField(
        max_length=10,
        choices=Kind.choices,
        default=Kind.TEXT,
    )
    body = models.TextField(max_length=MAX_LENGTH, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    photo = models.ImageField(upload_to=photo_path, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self):
        return f"{self.sender_name}: {self.body[:40]}"

    @property
    def sender_name(self):
        if self.kind == self.Kind.AI:
            return "Clique AI"
        if self.sender is None:
            return "Deleted user"
        return self.sender.name
