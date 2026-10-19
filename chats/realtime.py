"""Tells open pages about new and changed messages.

Each chat has a "group" on the channel layer (Redis). Every browser tab
that has the chat open joins it, so one group_send reaches all of them.
Each person also has their own group, joined by their inbox tabs.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .models import Membership


def group_name(conversation_id):
    return f"chat-{conversation_id}"


def user_group(user_id):
    return f"user-{user_id}"


def _send(group, event):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(group, event)


def broadcast(message, event_type):
    """Tell everyone viewing the chat about `message`.

    `event_type` is "message.new" or "message.changed". Channels calls the
    consumer method with the dot swapped for an underscore (message_new).
    """
    event = {"type": event_type, "message_id": message.pk}
    # Wait until the message is really saved, so nobody is told about a
    # message they can't load yet (or one that gets rolled back).
    group = group_name(message.conversation_id)
    transaction.on_commit(lambda: _send(group, event))

    # Every member's inbox needs a new preview too. A new message also
    # moves the chat to the top of the list.
    members = Membership.objects.filter(
        conversation_id=message.conversation_id,
    ).values_list("user_id", flat=True)
    update_inboxes(
        list(members),
        message.conversation_id,
        to_top=event_type == "message.new",
    )


def broadcast_read(conversation_id, user_id):
    """Someone read the chat: update the "Seen" line for people viewing
    it, and the reader's own unread count in their inbox."""
    event = {"type": "chat.read"}
    group = group_name(conversation_id)
    transaction.on_commit(lambda: _send(group, event))
    update_inboxes([user_id], conversation_id)


def update_inboxes(user_ids, conversation_id, to_top=False):
    """Ask these people's open inboxes to redraw one chat's row."""
    event = {
        "type": "inbox.changed",
        "chat_id": conversation_id,
        "to_top": to_top,
    }

    def send_all():
        for user_id in user_ids:
            _send(user_group(user_id), event)

    transaction.on_commit(send_all)
