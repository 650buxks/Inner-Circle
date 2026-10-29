"""Clique AI tests. A fake Claude stands in for the real one, so tests
are free, fast and never touch the internet."""

from datetime import timedelta
from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from chats.models import Message
from chats.services import (
    delete_message,
    get_or_create_private_chat,
    mark_read,
    send_message,
)

from . import client as ai_client
from .client import AIError, ask_claude
from .models import AIRequest
from .services import catch_up, chat_transcript

User = get_user_model()


class FakeClaude:
    """Pretends to be anthropic.Anthropic. Remembers what it was sent."""

    reply = "- Jordan booked dinner for Friday"
    stop_reason = "end_turn"
    error = None
    sent = None

    def __init__(self, api_key, timeout):
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        FakeClaude.sent = kwargs
        if FakeClaude.error:
            raise FakeClaude.error
        return SimpleNamespace(
            stop_reason=FakeClaude.stop_reason,
            content=[
                SimpleNamespace(type="thinking", thinking="hmm"),
                SimpleNamespace(type="text", text=FakeClaude.reply),
            ],
            usage=SimpleNamespace(input_tokens=120, output_tokens=30),
        )


@pytest.fixture
def claude(monkeypatch, settings):
    settings.ANTHROPIC_API_KEY = "test-key"
    settings.AI_MODEL = "claude-opus-5-5"
    monkeypatch.setattr(ai_client.anthropic, "Anthropic", FakeClaude)
    FakeClaude.reply = "- Jordan booked dinner for Friday"
    FakeClaude.stop_reason = "end_turn"
    FakeClaude.error = None
    FakeClaude.sent = None
    return FakeClaude


@pytest.fixture
def francis(db):
    return User.objects.create_user(username="francis", password="pass")


@pytest.fixture
def jordan(francis):
    jordan = User.objects.create_user(username="jordan", password="pass")
    francis.friends.add(jordan)
    return jordan


@pytest.fixture
def chat(francis, jordan):
    return get_or_create_private_chat(francis, jordan)


def an_hour_ago():
    return timezone.now() - timedelta(hours=1)


# --- Talking to Claude ---------------------------------------------------


def test_ask_claude_needs_an_api_key(settings):
    settings.ANTHROPIC_API_KEY = ""

    with pytest.raises(AIError, match="isn't set up"):
        ask_claude("system", "prompt")


def test_ask_claude_sends_model_effort_and_fallbacks(claude):
    text, usage = ask_claude("Be nice.", "Hello")

    assert text == "- Jordan booked dinner for Friday"  # thinking skipped
    assert usage.input_tokens == 120
    sent = claude.sent
    assert sent["model"] == "claude-opus-5-5"
    assert sent["system"] == "Be nice."
    assert sent["messages"] == [{"role": "user", "content": "Hello"}]
    assert sent["output_config"] == {"effort": "low"}
    assert sent["fallbacks"] == "default"


def test_ask_claude_skips_fallbacks_for_other_models(claude, settings):
    settings.AI_MODEL = "claude-haiku-5-5"

    ask_claude("system", "prompt")

    assert "fallbacks" not in claude.sent


def test_ask_claude_handles_refusals(claude):
    claude.stop_reason = "refusal"

    with pytest.raises(AIError, match="can't help"):
        ask_claude("system", "prompt")


def test_ask_claude_handles_api_errors(claude, caplog):
    request = httpx2.Request("POST", "https://api.anthropic.com")
    claude.error = anthropic.APIConnectionError(request=request)

    with pytest.raises(AIError, match="isn't available"):
        ask_claude("system", "prompt")
    assert "Claude request failed" in caplog.text


def test_ask_claude_handles_rate_limits(claude):
    request = httpx2.Request("POST", "https://api.anthropic.com")
    response = httpx2.Response(429, request=request)
    claude.error = anthropic.RateLimitError("slow down", response=response, body=None)

    with pytest.raises(AIError, match="busy"):
        ask_claude("system", "prompt")


# --- Catch me up ---------------------------------------------------------


def test_transcript_leaves_out_deleted_and_opted_out(chat, francis, jordan):
    send_message(jordan, chat, "Dinner Friday?")
    gone = send_message(jordan, chat, "oops")
    delete_message(jordan, gone)
    send_message(francis, chat, "Keep me out of it")
    francis.ai_opt_out = True
    francis.save()

    transcript = chat_transcript(chat.messages.order_by("created_at"))

    assert "jordan: Dinner Friday?" in transcript
    assert "oops" not in transcript
    assert "Keep me out of it" not in transcript


def test_transcript_mentions_photos(chat, jordan):
    message = send_message(jordan, chat, "Look")
    Message.objects.filter(pk=message.pk).update(photo="chat_photos/a.jpg")

    transcript = chat_transcript(chat.messages.all())

    assert "jordan: [sent a photo] Look" in transcript


def test_catch_up_summarizes_and_records_usage(claude, chat, francis, jordan):
    send_message(jordan, chat, "Dinner Friday at 7?")
    send_message(francis, chat, "My own message")

    summary = catch_up(francis, chat, an_hour_ago())

    assert summary == "- Jordan booked dinner for Friday"
    prompt = claude.sent["messages"][0]["content"]
    assert prompt.startswith("<messages>")
    assert "Dinner Friday at 7?" in prompt
    assert "My own message" not in prompt  # you know what you said
    assert "francis" in claude.sent["system"]
    request = AIRequest.objects.get()
    assert request.user == francis
    assert request.feature == AIRequest.Feature.CATCH_UP
    assert (request.input_tokens, request.output_tokens) == (120, 30)


def test_catch_up_only_reads_messages_after_since(claude, chat, francis, jordan):
    send_message(jordan, chat, "Old news")
    since = timezone.now()
    send_message(jordan, chat, "New news")

    catch_up(francis, chat, since)

    prompt = claude.sent["messages"][0]["content"]
    assert "New news" in prompt
    assert "Old news" not in prompt


def test_catch_up_with_nothing_new(claude, chat, francis):
    with pytest.raises(AIError, match="nothing new"):
        catch_up(francis, chat, an_hour_ago())
    assert claude.sent is None  # Claude wasn't asked


def test_catch_up_respects_chats_with_ai_off(claude, chat, francis, jordan):
    send_message(jordan, chat, "Hi")
    chat.ai_enabled = False
    chat.save()

    with pytest.raises(AIError, match="turned off"):
        catch_up(francis, chat, an_hour_ago())


def test_catch_up_has_a_daily_limit(claude, settings, chat, francis, jordan):
    settings.AI_DAILY_LIMIT = 2
    send_message(jordan, chat, "Hi")
    catch_up(francis, chat, an_hour_ago())
    catch_up(francis, chat, an_hour_ago())

    with pytest.raises(AIError, match="2 times today"):
        catch_up(francis, chat, an_hour_ago())
    assert AIRequest.objects.count() == 2


# --- The Catch me up button and page -------------------------------------


@pytest.fixture
def logged_in(client, francis):
    client.force_login(francis)
    return client


def test_button_shows_after_many_missed_messages(logged_in, settings, chat, jordan):
    settings.CATCH_UP_MIN_UNREAD = 3
    url = reverse("chats:detail", args=[chat.pk])
    send_message(jordan, chat, "one")
    send_message(jordan, chat, "two")

    assert "Catch me up" not in logged_in.get(url).content.decode()

    for word in ["three", "four", "five"]:
        send_message(jordan, chat, word)
    page = logged_in.get(url).content.decode()

    assert "You missed 3 messages" in page
    assert "Catch me up" in page


def test_no_button_when_ai_is_off(logged_in, settings, chat, jordan):
    settings.CATCH_UP_MIN_UNREAD = 1
    chat.ai_enabled = False
    chat.save()
    send_message(jordan, chat, "Hi")

    page = logged_in.get(reverse("chats:detail", args=[chat.pk]))

    assert "Catch me up" not in page.content.decode()


def test_catch_up_page_shows_summary(logged_in, monkeypatch, chat, francis, jordan):
    calls = []

    def fake_catch_up(user, conversation, since):
        calls.append(since)
        return "- Dinner is Friday\n- Bring snacks"

    monkeypatch.setattr("chats.views.summarize_missed", fake_catch_up)
    mark_read(francis, chat)
    last_read = chat.memberships.get(user=francis).last_read_at

    response = logged_in.post(
        reverse("chats:catch_up", args=[chat.pk]),
        {"since": last_read.isoformat()},
    )

    page = response.content.decode()
    assert "What you missed" in page
    assert "- Dinner is Friday<br>- Bring snacks" in page
    assert calls == [last_read]


def test_catch_up_without_since_uses_join_time(logged_in, monkeypatch, chat):
    calls = []
    monkeypatch.setattr(
        "chats.views.summarize_missed",
        lambda user, conversation, since: calls.append(since) or "- Hi",
    )

    logged_in.post(reverse("chats:catch_up", args=[chat.pk]))

    joined = chat.memberships.get(user__username="francis").joined_at
    assert calls == [joined]


def test_catch_up_error_goes_back_to_chat(logged_in, chat):

    response = logged_in.post(reverse("chats:catch_up", args=[chat.pk]), follow=True)

    assert response.redirect_chain[-1][0].startswith(reverse("chats:detail", args=[chat.pk]))
    assert "nothing new" in response.content.decode()


def test_outsiders_cannot_catch_up(client, chat):
    outsider = User.objects.create_user(username="sam", password="pass")
    client.force_login(outsider)

    response = client.post(reverse("chats:catch_up", args=[chat.pk]))

    assert response.status_code == 404


def test_catch_up_needs_post(logged_in, chat):
    response = logged_in.get(reverse("chats:catch_up", args=[chat.pk]))

    assert response.status_code == 405
