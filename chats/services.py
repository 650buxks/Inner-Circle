"""The rules for chats and messages.

Like friends/services.py, views call these functions so every rule lives in
one place.
"""

from django.db import transaction
from django.utils import timezone

from friends.services import are_friends, is_blocked_between

from .models import Conversation, Membership, Message
from .realtime import broadcast, broadcast_read


class ChatError(Exception):
    """Raised when an action breaks one of the rules. The message is shown
    to the user."""


def is_member(user, conversation):
    return conversation.memberships.filter(user=user).exists()


def other_person(conversation, user):
    """In a private chat, the person who isn't `user` (None if they deleted
    their account)."""
    membership = conversation.memberships.exclude(user=user).first()
    return membership.user if membership else None


def chat_title(conversation, user):
    """What `user` sees as the chat's name."""
    if conversation.kind == Conversation.Kind.GROUP:
        return conversation.name
    person = other_person(conversation, user)
    return person.name if person else "Deleted user"


def presence_text(conversation, user):
    """The status line under the chat's name, as `user` sees it.

    Private chats: "Online" or "Last seen 5 minutes ago".
    Groups: how many of the others are online, e.g. "2 online".
    """
    if conversation.kind == Conversation.Kind.PRIVATE:
        person = other_person(conversation, user)
        return person.presence if person else ""
    others = conversation.members.exclude(pk=user.pk)
    online = sum(1 for person in others if person.is_online)
    return f"{online} online" if online else ""


def private_key(user, other):
    low, high = sorted([user.pk, other.pk])
    return f"{low}:{high}"


@transaction.atomic
def get_or_create_private_chat(user, other):
    """Open the private chat between two people, creating it if needed."""
    if user == other:
        raise ChatError("You can't start a chat with yourself.")
    if is_blocked_between(user, other):
        raise ChatError("You can't message this person.")

    existing = Conversation.objects.filter(
        private_key=private_key(user, other),
    ).first()
    if existing:
        return existing

    if not are_friends(user, other):
        raise ChatError("You can only start chats with friends.")

    conversation = Conversation.objects.create(
        kind=Conversation.Kind.PRIVATE,
        private_key=private_key(user, other),
        created_by=user,
    )
    Membership.objects.create(conversation=conversation, user=user)
    Membership.objects.create(conversation=conversation, user=other)
    return conversation


@transaction.atomic
def create_group(creator, name, members):
    """Create a group chat. The creator becomes its admin."""
    name = name.strip()
    if not name:
        raise ChatError("Give your group a name.")
    others = [person for person in members if person != creator]
    if not others:
        raise ChatError("Add at least one friend to the group.")
    for person in others:
        if not are_friends(creator, person):
            raise ChatError(f"{person.name} isn't your friend.")

    conversation = Conversation.objects.create(
        kind=Conversation.Kind.GROUP,
        name=name,
        created_by=creator,
    )
    Membership.objects.create(
        conversation=conversation,
        user=creator,
        role=Membership.Role.ADMIN,
    )
    for person in others:
        Membership.objects.create(conversation=conversation, user=person)
    add_system_message(conversation, f"{creator.name} created the group")
    return conversation


def is_admin(user, conversation):
    return conversation.memberships.filter(
        user=user,
        role=Membership.Role.ADMIN,
    ).exists()


def _check_admin(user, conversation):
    if conversation.kind != Conversation.Kind.GROUP:
        raise ChatError("Only group chats have settings.")
    if not is_admin(user, conversation):
        raise ChatError("Only group admins can do that.")


@transaction.atomic
def rename_group(user, conversation, name):
    _check_admin(user, conversation)
    name = name.strip()
    if not name:
        raise ChatError("Give your group a name.")
    if name == conversation.name:
        return
    conversation.name = name
    conversation.save(update_fields=["name"])
    text = f"{user.name} renamed the group to {name}"
    add_system_message(conversation, text)


@transaction.atomic
def add_members(user, conversation, people):
    _check_admin(user, conversation)
    for person in people:
        if is_member(person, conversation):
            continue
        if not are_friends(user, person):
            raise ChatError(f"{person.name} isn't your friend.")
        Membership.objects.create(conversation=conversation, user=person)
        add_system_message(conversation, f"{user.name} added {person.name}")


@transaction.atomic
def remove_member(user, conversation, person):
    _check_admin(user, conversation)
    if person == user:
        raise ChatError("To leave the group, use Leave group.")
    deleted, _ = conversation.memberships.filter(user=person).delete()
    if not deleted:
        raise ChatError(f"{person.name} isn't in this group.")
    add_system_message(conversation, f"{user.name} removed {person.name}")


def make_admin(user, conversation, person):
    _check_admin(user, conversation)
    updated = conversation.memberships.filter(user=person).update(
        role=Membership.Role.ADMIN,
    )
    if not updated:
        raise ChatError(f"{person.name} isn't in this group.")


@transaction.atomic
def leave_group(user, conversation):
    if conversation.kind != Conversation.Kind.GROUP:
        raise ChatError("You can only leave group chats.")
    deleted, _ = conversation.memberships.filter(user=user).delete()
    if not deleted:
        raise ChatError("You're not in this group.")

    remaining = conversation.memberships.order_by("joined_at", "pk")
    if not remaining.exists():
        # Nobody left, so the group (and its messages) can go.
        conversation.delete()
        return
    add_system_message(conversation, f"{user.name} left the group")
    # A group always needs an admin: hand it to the longest-standing member.
    if not remaining.filter(role=Membership.Role.ADMIN).exists():
        oldest = remaining.first()
        oldest.role = Membership.Role.ADMIN
        oldest.save(update_fields=["role"])
        text = f"{oldest.user.name} is now an admin"
        add_system_message(conversation, text)


def add_system_message(conversation, text):
    return _save_message(
        conversation,
        sender=None,
        body=text,
        kind=Message.Kind.SYSTEM,
    )


@transaction.atomic
def send_message(user, conversation, body):
    body = body.strip()
    if not body:
        raise ChatError("You can't send an empty message.")
    if len(body) > Message.MAX_LENGTH:
        limit = Message.MAX_LENGTH
        raise ChatError(f"Messages can be at most {limit} characters.")
    if not is_member(user, conversation):
        raise ChatError("You're not in this chat.")
    if conversation.kind == Conversation.Kind.PRIVATE:
        person = other_person(conversation, user)
        if person is None or is_blocked_between(user, person):
            raise ChatError("You can't message this person.")

    message = _save_message(conversation, sender=user, body=body)
    mark_read(user, conversation)
    return message


def _save_message(conversation, sender, body, kind=Message.Kind.TEXT):
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=body,
        kind=kind,
    )
    conversation.last_activity_at = message.created_at
    conversation.save(update_fields=["last_activity_at"])
    broadcast(message, "message.new")
    return message


def edit_message(user, message, new_body):
    new_body = new_body.strip()
    if message.sender != user or message.kind != Message.Kind.TEXT:
        raise ChatError("You can only edit your own messages.")
    if message.is_deleted:
        raise ChatError("This message was deleted.")
    if not new_body:
        raise ChatError("A message can't be empty.")
    message.body = new_body
    message.edited_at = timezone.now()
    message.save(update_fields=["body", "edited_at"])
    broadcast(message, "message.changed")
    return message


def delete_message(user, message):
    """Replace the message with "Message deleted" (it keeps its place)."""
    if message.sender != user or message.kind != Message.Kind.TEXT:
        raise ChatError("You can only delete your own messages.")
    message.is_deleted = True
    message.body = ""
    message.save(update_fields=["is_deleted", "body"])
    broadcast(message, "message.changed")


def mark_read(user, conversation):
    Membership.objects.filter(conversation=conversation, user=user).update(
        last_read_at=timezone.now(),
    )
    broadcast_read(conversation.pk)


def read_receipt(conversation, user):
    """The "Seen" line under `user`'s latest message ("" if none).

    Private chats just say "Seen"; groups say who: "Seen by Jordan, Sam".
    """
    last = conversation.messages.exclude(kind=Message.Kind.SYSTEM).last()
    if last is None or last.sender != user or last.is_deleted:
        return ""
    readers = (
        conversation.memberships.exclude(user=user)
        .filter(last_read_at__gte=last.created_at)
        .select_related("user")
        .order_by("user__username")
    )
    names = [membership.user.name for membership in readers]
    if not names:
        return ""
    if conversation.kind == Conversation.Kind.PRIVATE:
        return "Seen"
    return "Seen by " + ", ".join(names)


def unread_count(user, conversation):
    """Messages from other people since `user` last read the chat."""
    membership = conversation.memberships.get(user=user)
    messages = conversation.messages.exclude(sender=user)
    if membership.last_read_at:
        messages = messages.filter(created_at__gt=membership.last_read_at)
    return messages.count()
