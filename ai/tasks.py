"""Clique AI work that runs in the background, so nobody waits for it."""

import logging

from celery import shared_task

from chats.models import Message
from chats.realtime import show_ai_thinking
from chats.services import post_ai_message

from .client import AIError
from .services import ask_clique

logger = logging.getLogger(__name__)


@shared_task
def answer_mention(message_id):
    """Answer an @clique message with a "Clique AI" message in the chat."""
    message = (
        Message.objects.select_related("conversation", "sender")
        .filter(pk=message_id, is_deleted=False, sender__isnull=False)
        .first()
    )
    if message is None:
        return  # deleted before we got to it
    show_ai_thinking(message.conversation_id)
    try:
        answer = ask_clique(message.sender, message)
    except AIError as error:
        answer = str(error)  # e.g. the daily limit, shown in the chat
    except Exception:
        # Never leave the question hanging: log the real error for us and
        # say something in the chat.
        logger.exception("@clique answer failed")
        answer = "Clique AI ran into a problem. Try again later."
    post_ai_message(message.conversation, answer)
