"""The guest demo: "Try the demo" makes a temporary account with chats."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.forms import SignUpForm
from ai.services import daily_limit, uses_left
from chats.models import Conversation, Message
from chats.services import unread_count
from friends.services import FriendshipError, send_friend_request

from .demo import create_guest, delete_old_guests

User = get_user_model()


@pytest.fixture
def guest(db):
    return create_guest()


def test_guest_gets_demo_friends_and_chats(guest):
    assert guest.is_guest
    assert guest.username.startswith("guest-")
    assert not guest.has_usable_password()
    assert sorted(f.name for f in guest.friends.all()) == ["Jordan", "Maya", "Sam"]
    group, private = guest.conversations.order_by("kind")
    assert group.name == "Weekend crew 🌮"
    assert group.messages.filter(kind=Message.Kind.POLL).count() == 1
    assert private.messages.last().body.startswith("Are you in for March?")


def test_demo_chats_are_unread_and_in_order(guest, settings):
    group = guest.conversations.get(kind=Conversation.Kind.GROUP)
    times = list(group.messages.values_list("created_at", flat=True))

    assert unread_count(guest, group) >= settings.CATCH_UP_MIN_UNREAD
    assert times == sorted(times)
    assert group.messages.first().body == "Jordan created the group"


def test_inbox_shows_the_newest_chat_first(guest):
    newest = guest.conversations.order_by("-last_activity_at").first()

    assert newest.kind == Conversation.Kind.PRIVATE  # Jordan wrote last


def test_poll_already_has_votes(guest):
    poll = Message.objects.get(kind=Message.Kind.POLL).poll

    assert poll.votes.count() == 3


def test_each_visitor_gets_their_own_guest(db):
    first, second = create_guest(), create_guest()

    assert first != second
    assert User.objects.filter(username__startswith="demo-").count() == 3  # shared


def test_demo_friends_cannot_log_in(guest):
    jordan = User.objects.get(username="demo-jordan")

    assert not jordan.has_usable_password()


def test_old_guests_are_deleted_with_their_chats(guest):
    User.objects.filter(pk=guest.pk).update(date_joined=timezone.now() - timedelta(days=2))
    chat_ids = list(guest.conversations.values_list("pk", flat=True))

    delete_old_guests()

    assert not User.objects.filter(pk=guest.pk).exists()
    assert not Conversation.objects.filter(pk__in=chat_ids).exists()
    assert User.objects.filter(username="demo-jordan").exists()  # kept


def test_new_guests_are_kept(guest):
    delete_old_guests()

    assert User.objects.filter(pk=guest.pk).exists()


def test_guests_get_a_smaller_ai_limit(guest, settings):
    settings.AI_GUEST_DAILY_LIMIT = 10

    assert daily_limit(guest) == 10
    assert uses_left(guest) == 10


def test_guests_cannot_add_real_people(guest):
    real = User.objects.create_user(username="francis", password="pass")

    with pytest.raises(FriendshipError, match="Demo accounts"):
        send_friend_request(guest, real)
    with pytest.raises(FriendshipError, match="Demo accounts"):
        send_friend_request(real, guest)


def test_search_hides_guests_and_demo_friends(client, guest):
    real = User.objects.create_user(username="francis", password="pass")
    client.force_login(real)

    for query in ["guest", "demo", "Jordan"]:
        page = client.get(reverse("friends:find"), {"q": query}).content.decode()
        assert guest.username not in page
        assert "demo-jordan" not in page


@pytest.mark.parametrize("username", ["guest-123", "Demo-jordan"])
def test_reserved_usernames(db, username):
    form = SignUpForm(
        data={
            "username": username,
            "email": "x@example.com",
            "password1": "a-long-password-123",
            "password2": "a-long-password-123",
        }
    )

    assert not form.is_valid()
    assert "reserved" in str(form.errors["username"])


def test_try_the_demo_button(client, db):
    page = client.get(reverse("core:home")).content.decode()
    assert "Try the demo" in page

    response = client.post(reverse("core:demo"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("chats:inbox")
    html = response.content.decode()
    assert "Welcome to the Clique demo" in html
    assert "trying Clique as a guest" in html  # the banner
    assert "Weekend crew" in html


def test_demo_needs_post(client, db):
    assert client.get(reverse("core:demo")).status_code == 405


@pytest.mark.parametrize("url", ["accounts:change_email", "accounts:change_password"])
def test_guests_cannot_change_email_or_password(client, guest, url):
    client.force_login(guest)

    response = client.post(reverse(url), {"email": "me@example.com"}, follow=True)

    guest.refresh_from_db()
    assert guest.email == ""
    assert "Demo accounts can&#x27;t change this" in response.content.decode()
