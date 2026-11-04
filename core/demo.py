"""The guest demo: "Try the demo" gives each visitor their own temporary
account with friends, chats and a poll already in it, so they can see
Clique working without signing up.

Guests only ever talk to the demo friends (Jordan, Sam and Maya), never to
real people, and their accounts are deleted after a day.
"""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from chats.models import Conversation, Message
from chats.services import (
    create_group,
    create_poll,
    get_or_create_private_chat,
    send_message,
    vote,
)

User = get_user_model()

# Guest accounts (and their chats) are deleted after this long.
GUEST_LIFETIME = timedelta(days=1)
GUEST_PREFIX = "guest-"
DEMO_PREFIX = "demo-"

DEMO_FRIENDS = [
    ("demo-jordan", "Jordan", "Always planning the next trip ✈️"),
    ("demo-sam", "Sam", "Will cook for compliments 🍳"),
    ("demo-maya", "Maya", "Probably at the climbing gym 🧗"),
]

# The group chat: (who, minutes ago, message). "you" is the guest. There
# are enough messages for "Catch me up" to appear.
GROUP_CHAT = [
    ("jordan", 95, "Ok crew, we NEED a weekend plan 🗓️"),
    ("sam", 93, "I vote tacos. Always tacos 🌮"),
    ("maya", 90, "Tacos then climbing? There's a new gym downtown"),
    ("jordan", 88, "Climbing gym opens at 10 on Saturday"),
    ("sam", 80, "Saturday works for me, Sunday I'm working"),
    ("maya", 78, "Same, Saturday is perfect"),
    ("jordan", 70, "Should we invite the new neighbor too?"),
    ("sam", 66, "Yes!! She brought us cookies last week 🍪"),
    ("maya", 60, "I can drive, my car fits 5"),
    ("jordan", 55, "Legend. Tacos at 7 after climbing?"),
    ("sam", 50, "I'll book a table at Taqueria Luna"),
    ("maya", 42, "Someone remind me to bring chalk"),
    ("jordan", 30, "Made a poll so we can lock in the day 👇"),
]

PRIVATE_CHAT = [
    ("jordan", 20, "Hey! Did you see the Tahoe cabin I sent?"),
    ("you", 18, "Not yet, what's it like?"),
    ("jordan", 15, "Hot tub, lake view, and it sleeps 6 🏔️"),
    ("jordan", 14, "Are you in for March? I need to book by Friday"),
]


def demo_friends():
    """Jordan, Sam and Maya, created the first time they're needed.
    Nobody can log in as them: they have no usable password."""
    friends = {}
    for username, name, status in DEMO_FRIENDS:
        friend, created = User.objects.get_or_create(
            username=username,
            defaults={"display_name": name, "status_message": status},
        )
        if created:
            friend.set_unusable_password()
            friend.save()
        friends[name.lower()] = friend
    for friend in friends.values():
        friend.friends.add(*[f for f in friends.values() if f != friend])
    return friends


@transaction.atomic
def create_guest():
    """A new guest account with demo chats in it. Returns the user."""
    delete_old_guests()
    guest = User.objects.create(
        username=f"{GUEST_PREFIX}{uuid.uuid4().hex[:8]}",
        display_name="Guest",
        is_guest=True,
    )
    guest.set_unusable_password()
    guest.save()

    friends = demo_friends()
    guest.friends.add(*friends.values())
    people = {**friends, "you": guest}

    members = [guest, friends["sam"], friends["maya"]]
    group = create_group(friends["jordan"], "Weekend crew 🌮", members)
    for note in group.messages.all():  # "Jordan created the group"
        set_minutes_ago(note, 100)
    say(group, people, GROUP_CHAT)
    poll = create_poll(
        friends["jordan"], group, "Which day for climbing + tacos?", ["Saturday", "Sunday"]
    )
    saturday, sunday = poll.options.all()
    vote(friends["sam"], poll, saturday.pk)
    vote(friends["maya"], poll, saturday.pk)
    vote(friends["jordan"], poll, sunday.pk)
    set_minutes_ago(poll.message, 29)
    update_last_activity(group)

    private = get_or_create_private_chat(guest, friends["jordan"])
    say(private, people, PRIVATE_CHAT)
    update_last_activity(private)

    # The guest "joined" before the messages and hasn't read them yet, so
    # the chats show as unread and Catch me up has something to sum up.
    guest.memberships.update(
        last_read_at=None,
        joined_at=timezone.now() - timedelta(hours=2),
    )
    return guest


def say(conversation, people, script):
    for who, minutes_ago, text in script:
        message = send_message(people[who], conversation, text)
        set_minutes_ago(message, minutes_ago)


def update_last_activity(conversation):
    """Sort the chat in the inbox by its (back-dated) latest message."""
    latest = conversation.messages.order_by("-created_at").first()
    conversation.last_activity_at = latest.created_at
    conversation.save(update_fields=["last_activity_at"])


def set_minutes_ago(message, minutes):
    when = timezone.now() - timedelta(minutes=minutes)
    Message.objects.filter(pk=message.pk).update(created_at=when)


def delete_old_guests():
    """Remove guest accounts older than GUEST_LIFETIME, with their chats."""
    old = User.objects.filter(
        is_guest=True,
        date_joined__lt=timezone.now() - GUEST_LIFETIME,
    )
    Conversation.objects.filter(memberships__user__in=old).delete()
    old.delete()


def is_reserved(username):
    """Usernames real people can't sign up with."""
    return username.lower().startswith((GUEST_PREFIX, DEMO_PREFIX))
