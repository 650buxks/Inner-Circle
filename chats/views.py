from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import User

from .forms import AddMembersForm, GroupForm
from .models import Conversation, Message
from .services import (
    ChatError,
    add_members,
    chat_title,
    create_group,
    delete_message,
    edit_message,
    get_or_create_private_chat,
    is_admin,
    is_member,
    leave_group,
    make_admin,
    mark_read,
    remove_member,
    rename_group,
    send_message,
    unread_count,
)

# How many messages the chat page shows at a time.
PAGE_SIZE = 50


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


def get_chat_for(user, pk):
    """The chat with this id, or a 404 if `user` isn't in it."""
    chat = get_object_or_404(Conversation, pk=pk)
    if not is_member(user, chat):
        # Don't reveal that the chat exists to people outside it.
        raise Http404
    return chat


def get_message_for(user, pk):
    """A message in one of `user`'s chats, or a 404."""
    return get_object_or_404(
        Message.objects.select_related("conversation"),
        pk=pk,
        conversation__memberships__user=user,
    )


def get_group_for(user, pk):
    """Like get_chat_for, but only for group chats."""
    chat = get_chat_for(user, pk)
    if chat.kind != Conversation.Kind.GROUP:
        raise Http404
    return chat


def back_to_chat(chat):
    # "#send" scrolls the page down to the message box.
    return redirect(reverse("chats:detail", args=[chat.pk]) + "#send")


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
    chat = get_chat_for(request.user, pk)
    mark_read(request.user, chat)

    # Newest messages first, so we can take the latest PAGE_SIZE of them.
    newest_first = chat.messages.select_related("sender").order_by("-pk")
    before = request.GET.get("before")
    if before and before.isdigit():
        newest_first = newest_first.filter(pk__lt=before)
    # Fetch one extra to find out whether there are older messages.
    page = list(newest_first[: PAGE_SIZE + 1])
    has_older = len(page) > PAGE_SIZE
    chat_messages = page[:PAGE_SIZE][::-1]  # back to oldest first

    context = {
        "chat": chat,
        "title": chat_title(chat, request.user),
        "chat_messages": chat_messages,
        "has_older": has_older,
        "max_length": Message.MAX_LENGTH,
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


@login_required
@require_POST
def send(request, pk):
    chat = get_chat_for(request.user, pk)
    try:
        send_message(request.user, chat, request.POST.get("body", ""))
    except ChatError as error:
        messages.error(request, str(error))
    return back_to_chat(chat)


@login_required
def edit(request, pk):
    message = get_message_for(request.user, pk)
    chat = message.conversation
    if request.method == "POST":
        try:
            edit_message(request.user, message, request.POST.get("body", ""))
        except ChatError as error:
            messages.error(request, str(error))
        else:
            return back_to_chat(chat)
    elif message.sender != request.user or message.is_deleted:
        messages.error(request, "You can only edit your own messages.")
        return back_to_chat(chat)
    context = {
        "message": message,
        "chat": chat,
        "max_length": Message.MAX_LENGTH,
    }
    return render(request, "chats/edit.html", context)


@login_required
@require_POST
def delete(request, pk):
    message = get_message_for(request.user, pk)
    try:
        delete_message(request.user, message)
    except ChatError as error:
        messages.error(request, str(error))
    return back_to_chat(message.conversation)


# --- Group chats ----------------------------------------------------------


@login_required
def new_group(request):
    form = GroupForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            chat = create_group(
                request.user,
                form.cleaned_data["name"],
                form.cleaned_data["members"],
            )
        except ChatError as error:
            form.add_error(None, str(error))
        else:
            return redirect("chats:detail", pk=chat.pk)
    return render(request, "chats/new_group.html", {"form": form})


@login_required
def group_settings(request, pk):
    chat = get_group_for(request.user, pk)
    context = {
        "chat": chat,
        # "admin" sorts before "member", so admins come first.
        "memberships": chat.memberships.select_related("user").order_by(
            "role",
            "user__username",
        ),
        "is_admin": is_admin(request.user, chat),
        "add_form": AddMembersForm(user=request.user, conversation=chat),
    }
    return render(request, "chats/group_settings.html", context)


def back_to_settings(chat):
    return redirect("chats:group_settings", pk=chat.pk)


@login_required
@require_POST
def rename(request, pk):
    chat = get_group_for(request.user, pk)
    try:
        rename_group(request.user, chat, request.POST.get("name", ""))
    except ChatError as error:
        messages.error(request, str(error))
    return back_to_settings(chat)


@login_required
@require_POST
def add_people(request, pk):
    chat = get_group_for(request.user, pk)
    form = AddMembersForm(
        request.POST,
        user=request.user,
        conversation=chat,
    )
    if not form.is_valid():
        messages.error(request, "Pick at least one friend to add.")
        return back_to_settings(chat)
    try:
        add_members(request.user, chat, form.cleaned_data["members"])
    except ChatError as error:
        messages.error(request, str(error))
    return back_to_settings(chat)


@login_required
@require_POST
def remove(request, pk, username):
    chat = get_group_for(request.user, pk)
    person = get_object_or_404(User, username=username)
    try:
        remove_member(request.user, chat, person)
    except ChatError as error:
        messages.error(request, str(error))
    return back_to_settings(chat)


@login_required
@require_POST
def promote(request, pk, username):
    chat = get_group_for(request.user, pk)
    person = get_object_or_404(User, username=username)
    try:
        make_admin(request.user, chat, person)
    except ChatError as error:
        messages.error(request, str(error))
    return back_to_settings(chat)


@login_required
@require_POST
def leave(request, pk):
    chat = get_group_for(request.user, pk)
    leave_group(request.user, chat)
    messages.success(request, "You left the group.")
    return redirect("chats:inbox")
