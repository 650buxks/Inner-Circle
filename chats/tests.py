import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from friends.services import block_user

from .models import Conversation, Membership, Message
from .services import (
    ChatError,
    chat_title,
    create_group,
    delete_message,
    edit_message,
    get_or_create_private_chat,
    mark_read,
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
