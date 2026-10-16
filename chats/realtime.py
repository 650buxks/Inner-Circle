"""Tells open chat pages about new and changed messages.

Each chat has a "group" on the channel layer (Redis). Every browser tab
that has the chat open joins it, so one group_send reaches all of them.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction


def group_name(conversation_id):
    return f"chat-{conversation_id}"


def _send(conversation_id, event):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(group_name(conversation_id), event)


def broadcast(message, event_type):
    """Tell everyone viewing the chat about `message`.

    `event_type` is "message.new" or "message.changed". Channels calls the
    consumer method with the dot swapped for an underscore (message_new).
    """
    event = {"type": event_type, "message_id": message.pk}
    # Wait until the message is really saved, so nobody is told about a
    # message they can't load yet (or one that gets rolled back).
    transaction.on_commit(lambda: _send(message.conversation_id, event))


def broadcast_read(conversation_id):
    """Tell everyone viewing the chat that someone has read it, so the
    "Seen" line under the last message can update."""
    event = {"type": "chat.read"}
    transaction.on_commit(lambda: _send(conversation_id, event))
