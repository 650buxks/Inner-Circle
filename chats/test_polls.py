"""Polls: friends vote on a question posted in the chat."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse

from ai.services import describe

from .models import Message, PollVote
from .services import (
    ChatError,
    clean_poll,
    create_group,
    create_poll,
    delete_message,
    get_or_create_private_chat,
    poll_results,
    preview,
    send_message,
    vote,
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
def group(francis, jordan, sam):
    return create_group(francis, "Trip", [jordan, sam])


@pytest.fixture
def poll(group, francis):
    return create_poll(francis, group, "Which day?", ["Friday", "Saturday"])


def option(poll, text):
    return poll.options.get(text=text)


# --- Creating polls -------------------------------------------------------


def test_create_poll_posts_it_in_the_chat(poll, group, francis):
    message = group.messages.last()

    assert message.kind == Message.Kind.POLL
    assert message.sender == francis
    assert message.body == "Which day?"
    assert [o.text for o in poll.options.all()] == ["Friday", "Saturday"]


@pytest.mark.parametrize(
    "question, options, error",
    [
        ("", ["A", "B"], "needs a question"),
        ("Q?", ["A"], "2 to 6 different options"),
        ("Q?", ["A", "a ", "A"], "2 to 6 different options"),
        ("Q?", [str(n) for n in range(7)], "2 to 6 different options"),
        ("Q?", ["A", "x" * 81], "under 80 characters"),
        ("x" * 201, ["A", "B"], "under 200 characters"),
    ],
)
def test_clean_poll_explains_problems(question, options, error):
    with pytest.raises(ChatError, match=error):
        clean_poll(question, options)


def test_clean_poll_tidies_up():
    assert clean_poll(" Day? ", [" Fri ", "", "Sat", "Fri"]) == ("Day?", ["Fri", "Sat"])


def test_outsiders_cannot_create_polls(group):
    outsider = User.objects.create_user(username="zed", password="pass")

    with pytest.raises(ChatError, match="not in this chat"):
        create_poll(outsider, group, "Q?", ["A", "B"])


def test_no_polls_after_being_blocked(francis, jordan):
    chat = get_or_create_private_chat(francis, jordan)
    jordan.blocked_users.add(francis)

    with pytest.raises(ChatError, match="can't message"):
        create_poll(francis, chat, "Q?", ["A", "B"])


# --- Voting ---------------------------------------------------------------


def test_vote_and_results(poll, francis, jordan, sam):
    vote(jordan, poll, option(poll, "Saturday").pk)
    vote(sam, poll, option(poll, "Saturday").pk)
    vote(francis, poll, option(poll, "Friday").pk)

    results = poll_results(poll, jordan)

    assert results["total"] == 3
    assert [(o["text"], o["votes"], o["percent"], o["mine"]) for o in results["options"]] == [
        ("Friday", 1, 33, False),
        ("Saturday", 2, 67, True),
    ]


def test_changing_your_vote(poll, jordan):
    vote(jordan, poll, option(poll, "Friday").pk)
    vote(jordan, poll, option(poll, "Saturday").pk)

    assert poll.votes.get(user=jordan).option.text == "Saturday"


def test_tapping_your_choice_again_takes_the_vote_back(poll, jordan):
    vote(jordan, poll, option(poll, "Friday").pk)
    vote(jordan, poll, option(poll, "Friday").pk)

    assert not poll.votes.exists()


def test_database_allows_one_vote_per_person(poll, jordan):
    PollVote.objects.create(poll=poll, option=option(poll, "Friday"), user=jordan)

    with pytest.raises(IntegrityError):
        PollVote.objects.create(poll=poll, option=option(poll, "Saturday"), user=jordan)


@pytest.mark.parametrize("bad_option", ["999", "abc", ""])
def test_vote_needs_a_real_option(poll, jordan, bad_option):
    with pytest.raises(ChatError, match="isn't in this poll"):
        vote(jordan, poll, bad_option)


def test_outsiders_cannot_vote(poll):
    outsider = User.objects.create_user(username="zed", password="pass")

    with pytest.raises(ChatError, match="not in this chat"):
        vote(outsider, poll, option(poll, "Friday").pk)


def test_cannot_vote_in_a_deleted_poll(poll, francis, jordan):
    delete_message(francis, poll.message)
    poll.message.refresh_from_db()

    with pytest.raises(ChatError, match="deleted"):
        vote(jordan, poll, option(poll, "Friday").pk)


# --- Showing polls --------------------------------------------------------


def test_inbox_preview(poll, francis, jordan):
    assert preview(poll.message, jordan) == "📊 Which day?"
    assert preview(poll.message, francis) == "You: 📊 Which day?"


def test_clique_ai_sees_the_votes(poll, jordan):
    vote(jordan, poll, option(poll, "Saturday").pk)

    line = describe(poll.message)

    assert "francis: [poll] Which day? Votes: Friday (0), Saturday (1)" in line


@pytest.fixture
def logged_in(client, jordan):
    client.force_login(jordan)
    return client


def test_chat_page_shows_the_poll(logged_in, poll, jordan):
    vote(jordan, poll, option(poll, "Saturday").pk)

    page = logged_in.get(reverse("chats:detail", args=[poll.message.conversation_id]))

    html = page.content.decode()
    assert "📊 Which day?" in html
    assert "✓ Saturday" in html  # Jordan's own vote is marked
    assert "1 vote · tap to vote" in html
    assert "--poll-share: 100%" in html


def test_vote_view_from_javascript(logged_in, poll):
    url = reverse("chats:vote", args=[poll.message.pk])

    response = logged_in.post(
        url,
        {"option": option(poll, "Friday").pk},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.json() == {"ok": True}
    assert poll.votes.get().option.text == "Friday"


def test_vote_view_without_javascript(logged_in, poll):
    url = reverse("chats:vote", args=[poll.message.pk])

    response = logged_in.post(url, {"option": option(poll, "Friday").pk})

    assert response.status_code == 302


def test_vote_view_reports_errors(logged_in, poll):
    url = reverse("chats:vote", args=[poll.message.pk])

    response = logged_in.post(
        url, {"option": "999"}, headers={"X-Requested-With": "XMLHttpRequest"}
    )

    assert response.status_code == 400


def test_vote_view_only_for_polls(logged_in, group, jordan):
    message = send_message(jordan, group, "not a poll")

    response = logged_in.post(reverse("chats:vote", args=[message.pk]), {"option": 1})

    assert response.status_code == 404


def test_outsiders_cannot_open_the_vote_view(client, poll):
    outsider = User.objects.create_user(username="zed", password="pass")
    client.force_login(outsider)

    response = client.post(reverse("chats:vote", args=[poll.message.pk]), {"option": 1})

    assert response.status_code == 404


def test_post_poll_view(logged_in, group):
    url = reverse("chats:post_poll", args=[group.pk])

    response = logged_in.post(url, {"question": "Where?", "options": ["Beach", "Lake"]})

    assert response.json() == {"ok": True}
    assert group.messages.last().poll.options.count() == 2


def test_post_poll_view_reports_errors(logged_in, group):
    url = reverse("chats:post_poll", args=[group.pk])

    response = logged_in.post(url, {"question": "Where?", "options": ["Beach"]})

    assert response.status_code == 400
    assert "2 to 6" in response.json()["error"]


def test_poll_creator_can_delete_it(client, poll, francis):
    client.force_login(francis)

    client.post(reverse("chats:delete", args=[poll.message.pk]))

    poll.message.refresh_from_db()
    assert poll.message.is_deleted
