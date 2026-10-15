from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User

from .models import Conversation, Message
from .services import (
    ChatError,
    chat_title,
    get_or_create_private_chat,
    is_member,
    mark_read,
    unread_count,
)


def preview(message, user):
    """A short line of text for the inbox, like "You: see you at 7"."""
    if message is None:
        return "No messages yet"
    if message.is_deleted:
        return "Message deleted"
    if message.kind == Message.Kind.SYSTEM:
        return message.body
    if message.sender == user:
        return f"You: {message.body}"
    return message.body


@login_required
def inbox(request):
    me = request.user
    chats = list(me.conversations.all())
    for chat in chats:
        chat.title = chat_title(chat, me)
        chat.last_message = chat.messages.last()
        chat.preview = preview(chat.last_message, me)
        chat.unread = unread_count(me, chat)
    return render(request, "chats/inbox.html", {"chats": chats})


@login_required
def chat_detail(request, pk):
    chat = get_object_or_404(Conversation, pk=pk)
    if not is_member(request.user, chat):
        # Don't reveal that the chat exists to people outside it.
        raise Http404
    mark_read(request.user, chat)
    context = {
        "chat": chat,
        "title": chat_title(chat, request.user),
        "chat_messages": chat.messages.select_related("sender"),
    }
    return render(request, "chats/detail.html", context)


@login_required
@require_POST
def start_chat(request, username):
    person = get_object_or_404(User, username=username)
    try:
        chat = get_or_create_private_chat(request.user, person)
    except ChatError as error:
        messages.error(request, str(error))
        return redirect("accounts:profile", username=username)
    return redirect("chats:detail", pk=chat.pk)
