import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import channel_layers
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError
from django.urls import reverse

from friends.services import block_user

from .models import Conversation, Membership, Message
from .routing import websocket_urlpatterns
from .services import (
    ChatError,
    add_members,
    chat_title,
    create_group,
    delete_message,
    edit_message,
    get_or_create_private_chat,
    is_admin,
    leave_group,
    make_admin,
    mark_read,
    read_receipt,
    remove_member,
    rename_group,
    send_message,
    unread_count,
)

User = get_user_model()


@pytest.fixture
def francis(db):
    return User.objects.create_user(username="francis", password="pass")


@pytest.fixture
def jordan(francis):
    jordan = User.objects.create_user(username="jordan", password="pass")
    francis.friends.add(jordan)
    return jordan


@pytest.fixture
def sam(francis):
    sam = User.objects.create_user(username="sam", password="pass")
    francis.friends.add(sam)
    return sam


@pytest.fixture
def chat(francis, jordan):
    """A private chat between Francis and Jordan."""
    return get_or_create_private_chat(francis, jordan)


# --- Private chats -------------------------------------------------------


def test_private_chat_has_both_people(chat, francis, jordan):
    assert set(chat.members.all()) == {francis, jordan}
    assert chat.kind == Conversation.Kind.PRIVATE


def test_same_private_chat_is_reused(chat, francis, jordan):
    # Whoever opens it, it's the same chat.
    assert get_or_create_private_chat(jordan, francis) == chat
    assert Conversation.objects.count() == 1


def test_private_chat_title_is_the_other_person(chat, francis, jordan):
    assert chat_title(chat, francis) == "jordan"
    assert chat_title(chat, jordan) == "francis"


def test_cannot_start_chat_with_non_friend(francis):
    stranger = User.objects.create_user(username="stranger", password="pass")

    with pytest.raises(ChatError, match="friends"):
        get_or_create_private_chat(francis, stranger)


def test_cannot_start_chat_with_yourself(francis):
    with pytest.raises(ChatError):
        get_or_create_private_chat(francis, francis)


def test_database_allows_one_private_chat_per_pair(chat):
    with pytest.raises(IntegrityError):
        Conversation.objects.create(
            kind=Conversation.Kind.PRIVATE,
            private_key=chat.private_key,
        )


# --- Group chats ---------------------------------------------------------


def test_create_group(francis, jordan, sam):
    group = create_group(francis, "Weekend plans", [jordan, sam])

    assert group.kind == Conversation.Kind.GROUP
    assert set(group.members.all()) == {francis, jordan, sam}
    admin = group.memberships.get(role=Membership.Role.ADMIN)
    assert admin.user == francis
    assert group.messages.get().body == "francis created the group"


def test_group_needs_a_name(francis, jordan):
    with pytest.raises(ChatError, match="name"):
        create_group(francis, "   ", [jordan])


def test_group_needs_another_member(francis):
    with pytest.raises(ChatError, match="at least one"):
        create_group(francis, "Just me", [])


def test_group_members_must_be_friends(francis, jordan):
    stranger = User.objects.create_user(username="stranger", password="pass")

    with pytest.raises(ChatError, match="isn't your friend"):
        create_group(francis, "Mixed", [jordan, stranger])


# --- Messages -------------------------------------------------------------


def test_send_message(chat, francis):
    message = send_message(francis, chat, "  Hey!  ")

    assert message.body == "Hey!"  # extra spaces trimmed
    assert message.sender == francis
    chat.refresh_from_db()
    assert chat.last_activity_at == message.created_at


def test_cannot_send_empty_message(chat, francis):
    with pytest.raises(ChatError, match="empty"):
        send_message(francis, chat, "   ")


def test_cannot_send_too_long_message(chat, francis):
    with pytest.raises(ChatError, match="at most"):
        send_message(francis, chat, "a" * (Message.MAX_LENGTH + 1))


def test_non_members_cannot_send(chat):
    outsider = User.objects.create_user(username="outsider", password="pass")

    with pytest.raises(ChatError, match="not in this chat"):
        send_message(outsider, chat, "Hi")


def test_cannot_message_after_being_blocked(chat, francis, jordan):
    block_user(jordan, francis)

    with pytest.raises(ChatError):
        send_message(francis, chat, "Hello?")


def test_edit_own_message(chat, francis):
    message = send_message(francis, chat, "Helo")

    edit_message(francis, message, "Hello")

    message.refresh_from_db()
    assert message.body == "Hello"
    assert message.edited_at is not None


def test_cannot_edit_someone_elses_message(chat, francis, jordan):
    message = send_message(jordan, chat, "Hi")

    with pytest.raises(ChatError):
        edit_message(francis, message, "Changed")


def test_delete_own_message(chat, francis):
    message = send_message(francis, chat, "Oops")

    delete_message(francis, message)

    message.refresh_from_db()
    assert message.is_deleted
    assert message.body == ""


def test_deleted_users_messages_stay(chat, francis, jordan):
    send_message(jordan, chat, "Bye")

    jordan.delete()

    message = Message.objects.get()
    assert message.sender is None
    assert message.sender_name == "Deleted user"
    assert chat_title(chat, francis) == "Deleted user"


# --- Unread counts --------------------------------------------------------


def test_unread_count(chat, francis, jordan):
    send_message(jordan, chat, "One")
    send_message(jordan, chat, "Two")

    assert unread_count(francis, chat) == 2
    assert unread_count(jordan, chat) == 0  # your own messages don't count

    mark_read(francis, chat)

    assert unread_count(francis, chat) == 0


# --- Inbox and chat page --------------------------------------------------


@pytest.fixture
def logged_in(client, francis):
    client.force_login(francis)
    return client


def test_inbox_requires_login(client):
    response = client.get(reverse("chats:inbox"))

    assert response.status_code == 302


def test_home_page_sends_logged_in_people_to_inbox(logged_in):
    response = logged_in.get(reverse("core:home"))

    assert response.url == reverse("chats:inbox")


def test_inbox_when_you_have_no_chats(logged_in):
    response = logged_in.get(reverse("chats:inbox"))

    assert "No chats yet" in response.content.decode()


def test_inbox_shows_chats_with_preview_and_unread(logged_in, chat, jordan):
    send_message(jordan, chat, "Are you coming tonight?")

    response = logged_in.get(reverse("chats:inbox"))

    page = response.content.decode()
    assert "jordan" in page
    assert "Are you coming tonight?" in page
    assert response.context["chats"][0].unread == 1


def test_inbox_preview_marks_your_own_messages(logged_in, chat, francis):
    send_message(francis, chat, "On my way")

    response = logged_in.get(reverse("chats:inbox"))

    assert "You: On my way" in response.content.decode()


def test_inbox_shows_newest_chat_first(logged_in, francis, jordan, sam):
    older = get_or_create_private_chat(francis, jordan)
    newer = get_or_create_private_chat(francis, sam)
    send_message(sam, newer, "Hi")

    response = logged_in.get(reverse("chats:inbox"))

    assert response.context["chats"] == [newer, older]


def test_message_button_starts_chat(logged_in, francis, jordan):
    response = logged_in.post(reverse("chats:start", args=["jordan"]))

    chat = Conversation.objects.get()
    assert response.url == reverse("chats:detail", args=[chat.pk])
    assert set(chat.members.all()) == {francis, jordan}


def test_message_button_for_non_friend_shows_error(logged_in):
    User.objects.create_user(username="stranger", password="pass")

    response = logged_in.post(reverse("chats:start", args=["stranger"]))

    assert response.url == reverse("accounts:profile", args=["stranger"])
    assert not Conversation.objects.exists()


def test_chat_page_shows_messages(logged_in, chat, jordan):
    send_message(jordan, chat, "See you at 7")

    response = logged_in.get(reverse("chats:detail", args=[chat.pk]))

    assert "See you at 7" in response.content.decode()


def test_opening_chat_marks_it_read(logged_in, chat, francis, jordan):
    send_message(jordan, chat, "Hello")

    logged_in.get(reverse("chats:detail", args=[chat.pk]))

    assert unread_count(francis, chat) == 0


def test_outsiders_cannot_open_a_chat(client, chat):
    outsider = User.objects.create_user(username="outsider", password="pass")
    client.force_login(outsider)

    response = client.get(reverse("chats:detail", args=[chat.pk]))

    assert response.status_code == 404


def test_friend_buttons_include_message(logged_in, jordan):
    response = logged_in.get(reverse("accounts:profile", args=["jordan"]))

    assert reverse("chats:start", args=["jordan"]) in response.content.decode()


# --- Sending, editing and deleting ---------------------------------------


def test_send_message_from_chat_page(logged_in, chat, francis):
    url = reverse("chats:send", args=[chat.pk])

    response = logged_in.post(url, {"body": "Hey!"})

    assert response.url == reverse("chats:detail", args=[chat.pk]) + "#send"
    message = chat.messages.get()
    assert message.sender == francis
    assert message.body == "Hey!"


def test_sending_empty_message_shows_error(logged_in, chat):
    url = reverse("chats:send", args=[chat.pk])

    response = logged_in.post(url, {"body": "   "}, follow=True)

    assert "You can&#x27;t send an empty message." in response.content.decode()
    assert not chat.messages.exists()


def test_outsiders_cannot_send(client, chat):
    outsider = User.objects.create_user(username="outsider", password="pass")
    client.force_login(outsider)

    response = client.post(
        reverse("chats:send", args=[chat.pk]),
        {"body": "Hi"},
    )

    assert response.status_code == 404
    assert not chat.messages.exists()


def test_edit_page_shows_current_text(logged_in, chat, francis):
    message = send_message(francis, chat, "Helo")

    response = logged_in.get(reverse("chats:edit", args=[message.pk]))

    assert "Helo" in response.content.decode()


def test_edit_message_from_chat_page(logged_in, chat, francis):
    message = send_message(francis, chat, "Helo")

    logged_in.post(
        reverse("chats:edit", args=[message.pk]),
        {"body": "Hello"},
    )

    message.refresh_from_db()
    assert message.body == "Hello"
    assert message.edited_at is not None


def test_cannot_edit_someone_elses_message_from_page(logged_in, chat, jordan):
    message = send_message(jordan, chat, "Mine")

    logged_in.post(
        reverse("chats:edit", args=[message.pk]),
        {"body": "Changed"},
    )

    message.refresh_from_db()
    assert message.body == "Mine"


def test_delete_message_from_chat_page(logged_in, chat, francis):
    message = send_message(francis, chat, "Oops")

    logged_in.post(reverse("chats:delete", args=[message.pk]))

    message.refresh_from_db()
    assert message.is_deleted


def test_outsiders_get_404_for_messages(client, chat, francis):
    message = send_message(francis, chat, "Private")
    outsider = User.objects.create_user(username="outsider", password="pass")
    client.force_login(outsider)

    response = client.post(reverse("chats:delete", args=[message.pk]))

    assert response.status_code == 404


def test_chat_page_shows_latest_page_of_messages(logged_in, chat, francis):
    for number in range(55):
        send_message(francis, chat, f"Message {number}")

    response = logged_in.get(reverse("chats:detail", args=[chat.pk]))

    shown = [message.body for message in response.context["chat_messages"]]
    assert len(shown) == 50
    assert shown[-1] == "Message 54"
    assert response.context["has_older"]


def test_load_older_messages(logged_in, chat, francis):
    for number in range(55):
        send_message(francis, chat, f"Message {number}")
    oldest_shown = chat.messages.order_by("-pk")[49]
    url = reverse("chats:detail", args=[chat.pk])

    response = logged_in.get(url, {"before": oldest_shown.pk})

    shown = [message.body for message in response.context["chat_messages"]]
    assert shown == [f"Message {number}" for number in range(5)]
    assert not response.context["has_older"]


# --- Group settings (services) -------------------------------------------


@pytest.fixture
def group(francis, jordan):
    """A group made by Francis (admin) with Jordan in it."""
    return create_group(francis, "Weekend plans", [jordan])


def latest_note(group):
    return group.messages.last().body


def test_admin_can_rename_group(group, francis):
    rename_group(francis, group, "Road trip")

    group.refresh_from_db()
    assert group.name == "Road trip"
    assert latest_note(group) == "francis renamed the group to Road trip"


def test_members_cannot_rename_group(group, jordan):
    with pytest.raises(ChatError, match="admins"):
        rename_group(jordan, group, "Mine now")


def test_admin_can_add_friends(group, francis, sam):
    add_members(francis, group, [sam])

    assert sam in group.members.all()
    assert latest_note(group) == "francis added sam"


def test_cannot_add_non_friends(group, francis):
    stranger = User.objects.create_user(username="stranger", password="pass")

    with pytest.raises(ChatError, match="isn't your friend"):
        add_members(francis, group, [stranger])


def test_admin_can_remove_member(group, francis, jordan):
    remove_member(francis, group, jordan)

    assert jordan not in group.members.all()
    assert latest_note(group) == "francis removed jordan"


def test_members_cannot_remove_people(group, francis, jordan):
    with pytest.raises(ChatError, match="admins"):
        remove_member(jordan, group, francis)


def test_admin_can_make_another_admin(group, francis, jordan):
    make_admin(francis, group, jordan)

    assert is_admin(jordan, group)


def test_leaving_group(group, jordan):
    leave_group(jordan, group)

    assert jordan not in group.members.all()
    assert latest_note(group) == "jordan left the group"


def test_last_admin_leaving_hands_over_admin(group, francis, jordan):
    leave_group(francis, group)

    assert is_admin(jordan, group)
    assert latest_note(group) == "jordan is now an admin"


def test_group_is_deleted_when_everyone_leaves(group, francis, jordan):
    leave_group(francis, group)
    leave_group(jordan, group)

    assert not Conversation.objects.filter(pk=group.pk).exists()


def test_cannot_leave_private_chat(chat, francis):
    with pytest.raises(ChatError, match="group"):
        leave_group(francis, chat)


# --- Group pages -----------------------------------------------------------


def test_new_group_page_lists_friends(logged_in, jordan):
    response = logged_in.get(reverse("chats:new_group"))

    assert "jordan" in response.content.decode()


def test_new_group_page_without_friends(logged_in):
    response = logged_in.get(reverse("chats:new_group"))

    assert "You need friends to make a group." in response.content.decode()


def test_create_group_from_page(logged_in, francis, jordan, sam):
    response = logged_in.post(
        reverse("chats:new_group"),
        {"name": "Movie night", "members": [jordan.pk, sam.pk]},
    )

    group = Conversation.objects.get(kind=Conversation.Kind.GROUP)
    assert response.url == reverse("chats:detail", args=[group.pk])
    assert group.name == "Movie night"
    assert set(group.members.all()) == {francis, jordan, sam}


def test_create_group_needs_a_friend(logged_in, jordan):
    response = logged_in.post(
        reverse("chats:new_group"),
        {"name": "Movie night"},
    )

    assert "Pick at least one friend." in response.content.decode()
    assert not Conversation.objects.exists()


def test_settings_page_shows_members(logged_in, group):
    response = logged_in.get(reverse("chats:group_settings", args=[group.pk]))

    page = response.content.decode()
    assert "jordan" in page
    assert "Admin" in page


def test_private_chats_have_no_settings_page(logged_in, chat):
    response = logged_in.get(reverse("chats:group_settings", args=[chat.pk]))

    assert response.status_code == 404


def test_add_members_from_page(logged_in, group, sam):
    logged_in.post(
        reverse("chats:add_members", args=[group.pk]),
        {"members": [sam.pk]},
    )

    assert sam in group.members.all()


def test_remove_member_from_page(logged_in, group, jordan):
    logged_in.post(reverse("chats:remove_member", args=[group.pk, "jordan"]))

    assert jordan not in group.members.all()


def test_members_cannot_remove_from_page(client, group, francis, jordan):
    client.force_login(jordan)

    client.post(reverse("chats:remove_member", args=[group.pk, "francis"]))

    assert francis in group.members.all()


def test_leave_group_from_page(logged_in, group, francis):
    response = logged_in.post(reverse("chats:leave", args=[group.pk]))

    assert response.url == reverse("chats:inbox")
    assert francis not in group.members.all()


# --- Live updates (WebSockets) ---------------------------------------------
#
# These tests use transaction=True because live updates are only sent once
# a message is really committed to the database (transaction.on_commit).


@pytest.fixture
def channel_layer(settings):
    """Use the in-memory channel layer instead of Redis while testing."""
    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
    channel_layers.backends.clear()  # forget any layer made with Redis
    yield
    channel_layers.backends.clear()


def socket_for(user, chat):
    """A pretend browser tab with `chat` open, logged in as `user`."""
    application = URLRouter(websocket_urlpatterns)
    communicator = WebsocketCommunicator(application, f"/ws/chats/{chat.pk}/")
    communicator.scope["user"] = user
    return communicator


live = pytest.mark.django_db(transaction=True)


@live
def test_members_can_connect(channel_layer, chat, francis):
    async def scenario():
        socket = socket_for(francis, chat)
        connected, _ = await socket.connect()
        await socket.disconnect()
        return connected

    assert async_to_sync(scenario)()


@live
def test_outsiders_cannot_connect(channel_layer, chat):
    outsider = User.objects.create_user(username="outsider", password="pass")

    async def scenario():
        connected, _ = await socket_for(outsider, chat).connect()
        return connected

    assert not async_to_sync(scenario)()


@live
def test_logged_out_people_cannot_connect(channel_layer, chat):
    async def scenario():
        connected, _ = await socket_for(AnonymousUser(), chat).connect()
        return connected

    assert not async_to_sync(scenario)()


@live
def test_socket_message_reaches_everyone(channel_layer, chat, francis, jordan):
    async def scenario():
        mine, theirs = socket_for(francis, chat), socket_for(jordan, chat)
        await mine.connect()
        await theirs.connect()

        await mine.send_json_to({"type": "message", "body": "On my way!"})
        received = (
            await mine.receive_json_from(),
            await theirs.receive_json_from(),
        )

        await mine.disconnect()
        await theirs.disconnect()
        return received

    for_me, for_them = async_to_sync(scenario)()

    assert chat.messages.get().body == "On my way!"
    assert for_me["type"] == for_them["type"] == "message.new"
    assert "On my way!" in for_them["html"]
    # Only the sender gets Edit and Delete links.
    assert "Edit" in for_me["html"]
    assert "Edit" not in for_them["html"]


@live
def test_empty_message_over_socket_gets_an_error(channel_layer, chat, francis):
    async def scenario():
        socket = socket_for(francis, chat)
        await socket.connect()
        await socket.send_json_to({"type": "message", "body": "   "})
        reply = await socket.receive_json_from()
        await socket.disconnect()
        return reply

    reply = async_to_sync(scenario)()

    assert reply == {
        "type": "error",
        "message": "You can't send an empty message.",
    }
    assert not chat.messages.exists()


@live
def test_form_messages_appear_live(channel_layer, chat, francis, jordan):
    async def scenario():
        socket = socket_for(jordan, chat)
        await socket.connect()
        await database_sync_to_async(send_message)(francis, chat, "Hi!")
        received = await socket.receive_json_from()
        await socket.disconnect()
        return received

    received = async_to_sync(scenario)()

    assert received["type"] == "message.new"
    assert "Hi!" in received["html"]


@live
def test_live_message_is_marked_read(channel_layer, chat, francis, jordan):
    async def scenario():
        socket = socket_for(jordan, chat)
        await socket.connect()
        await database_sync_to_async(send_message)(francis, chat, "Hi!")
        await socket.receive_json_from()
        await socket.disconnect()

    async_to_sync(scenario)()

    assert unread_count(jordan, chat) == 0


@live
def test_edits_and_deletes_appear_live(channel_layer, chat, francis, jordan):
    message = send_message(francis, chat, "Helo")

    async def scenario():
        socket = socket_for(jordan, chat)
        await socket.connect()
        await database_sync_to_async(edit_message)(francis, message, "Hello")
        edited = await socket.receive_json_from()
        await database_sync_to_async(delete_message)(francis, message)
        deleted = await socket.receive_json_from()
        await socket.disconnect()
        return edited, deleted

    edited, deleted = async_to_sync(scenario)()

    assert edited["type"] == "message.changed"
    assert edited["id"] == message.pk
    assert "Hello" in edited["html"]
    assert "Message deleted" in deleted["html"]


def test_chat_page_connects_live(logged_in, chat):
    response = logged_in.get(reverse("chats:detail", args=[chat.pk]))

    assert f"/ws/chats/{chat.pk}/" in response.content.decode()


def test_older_messages_page_is_not_live(logged_in, chat):
    url = reverse("chats:detail", args=[chat.pk])

    response = logged_in.get(url, {"before": 1})

    assert "/ws/chats/" not in response.content.decode()


# --- Read receipts and typing ----------------------------------------------


def test_no_receipt_until_they_read_it(chat, francis):
    send_message(francis, chat, "Hi")

    assert read_receipt(chat, francis) == ""


def test_private_chat_receipt_says_seen(chat, francis, jordan):
    send_message(francis, chat, "Hi")
    mark_read(jordan, chat)

    assert read_receipt(chat, francis) == "Seen"


def test_group_receipt_says_who_has_seen_it(francis, jordan, sam):
    group = create_group(francis, "Weekend plans", [jordan, sam])
    send_message(francis, group, "Who's free?")
    mark_read(jordan, group)

    assert read_receipt(group, francis) == "Seen by jordan"


def test_no_receipt_when_last_message_is_theirs(chat, francis, jordan):
    send_message(francis, chat, "Hi")
    send_message(jordan, chat, "Hey!")

    assert read_receipt(chat, francis) == ""


def test_chat_page_shows_receipt(logged_in, chat, francis, jordan):
    send_message(francis, chat, "Hi")
    mark_read(jordan, chat)

    response = logged_in.get(reverse("chats:detail", args=[chat.pk]))

    assert response.context["receipt"] == "Seen"


@live
def test_typing_is_shown_to_others_only(channel_layer, chat, francis, jordan):
    async def scenario():
        mine, theirs = socket_for(francis, chat), socket_for(jordan, chat)
        await mine.connect()
        await theirs.connect()

        await mine.send_json_to({"type": "typing"})
        for_them = await theirs.receive_json_from()
        nothing_for_me = await mine.receive_nothing()

        await mine.disconnect()
        await theirs.disconnect()
        return for_them, nothing_for_me

    for_them, nothing_for_me = async_to_sync(scenario)()

    assert for_them == {"type": "typing", "name": "francis"}
    assert nothing_for_me


@live
def test_sender_sees_receipt_live(channel_layer, chat, francis, jordan):
    send_message(francis, chat, "Hi")

    async def scenario():
        socket = socket_for(francis, chat)
        await socket.connect()
        await database_sync_to_async(mark_read)(jordan, chat)
        received = await socket.receive_json_from()
        await socket.disconnect()
        return received

    assert async_to_sync(scenario)() == {"type": "receipt", "text": "Seen"}
