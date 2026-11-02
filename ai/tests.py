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
    post_ai_message,
    preview,
    send_message,
)

from . import client as ai_client
from .client import AIError, ask_claude
from .models import AIRequest
from .services import (
    ask_clique,
    catch_up,
    chat_transcript,
    mentions_clique,
    parse_replies,
    suggest_replies,
)
from .tasks import answer_mention

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


# --- Help me reply -------------------------------------------------------


def test_suggest_replies_returns_ideas_and_records_usage(claude, chat, francis, jordan):
    claude.reply = "Yes! 7pm works\nWhere should we go?\nOnly if you pay 😏"
    send_message(francis, chat, "lol same")
    send_message(jordan, chat, "Dinner Friday?")

    replies = suggest_replies(francis, chat)

    assert replies == ["Yes! 7pm works", "Where should we go?", "Only if you pay 😏"]
    prompt = claude.sent["messages"][0]["content"]
    assert "jordan: Dinner Friday?" in prompt
    assert "francis: lol same" in prompt  # their own style counts
    assert "write" in claude.sent["system"].lower()
    request = AIRequest.objects.get()
    assert request.feature == AIRequest.Feature.REPLY


def test_suggest_replies_only_reads_recent_messages(claude, chat, francis, jordan):
    send_message(jordan, chat, "Ancient history")
    for number in range(30):
        send_message(jordan, chat, f"message {number}")

    suggest_replies(francis, chat)

    prompt = claude.sent["messages"][0]["content"]
    assert "message 29" in prompt
    assert "Ancient history" not in prompt


def test_suggest_replies_needs_something_to_reply_to(claude, chat, francis):
    send_message(francis, chat, "Anyone there?")

    with pytest.raises(AIError, match="nothing to reply to"):
        suggest_replies(francis, chat)
    assert claude.sent is None


def test_suggest_replies_respects_chats_with_ai_off(claude, chat, francis, jordan):
    send_message(jordan, chat, "Hi")
    chat.ai_enabled = False
    chat.save()

    with pytest.raises(AIError, match="turned off"):
        suggest_replies(francis, chat)


def test_suggest_replies_counts_toward_daily_limit(claude, settings, chat, francis, jordan):
    settings.AI_DAILY_LIMIT = 1
    send_message(jordan, chat, "Hi")
    suggest_replies(francis, chat)

    with pytest.raises(AIError, match="1 times today"):
        catch_up(francis, chat, an_hour_ago())


@pytest.mark.parametrize(
    "text, expected",
    [
        ("- Sure\n- Nope", ["Sure", "Nope"]),
        ("1. Sure\n2) Nope\n\n3. Maybe", ["Sure", "Nope", "Maybe"]),
        ('"Sure"\n"Sure"\n7pm works', ["Sure", "7pm works"]),
        ("a\nb\nc\nd", ["a", "b", "c"]),
    ],
)
def test_parse_replies_tidies_claudes_answer(text, expected):
    assert parse_replies(text) == expected


def test_reply_ideas_button_shows_in_chats(logged_in, chat):
    page = logged_in.get(reverse("chats:detail", args=[chat.pk]))

    assert "Help me reply" in page.content.decode()


def test_no_reply_ideas_button_when_ai_is_off(logged_in, chat):
    chat.ai_enabled = False
    chat.save()

    page = logged_in.get(reverse("chats:detail", args=[chat.pk]))

    assert "Help me reply" not in page.content.decode()


def test_reply_ideas_view_returns_json(logged_in, monkeypatch, chat):
    monkeypatch.setattr("chats.views.suggest_replies", lambda user, conversation: ["Sure!", "Nah"])

    response = logged_in.post(reverse("chats:reply_ideas", args=[chat.pk]))

    assert response.json() == {"replies": ["Sure!", "Nah"]}


def test_reply_ideas_view_reports_errors(logged_in, chat):
    response = logged_in.post(reverse("chats:reply_ideas", args=[chat.pk]))

    assert response.status_code == 400
    assert response.json() == {"error": "There's nothing to reply to yet."}


def test_outsiders_cannot_get_reply_ideas(client, chat):
    outsider = User.objects.create_user(username="sam", password="pass")
    client.force_login(outsider)

    response = client.post(reverse("chats:reply_ideas", args=[chat.pk]))

    assert response.status_code == 404


def test_reply_ideas_needs_post(logged_in, chat):
    response = logged_in.get(reverse("chats:reply_ideas", args=[chat.pk]))

    assert response.status_code == 405


# --- @clique -------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("@clique what time?", True),
        ("hey @CLIQUE, what time?", True),
        ("ok @clique.", True),
        ("email me at me@clique.com", False),
        ("@cliquey", False),
        ("clique is great", False),
    ],
)
def test_mentions_clique(text, expected):
    assert mentions_clique(text) == expected


def test_ask_clique_reads_earlier_messages(claude, chat, francis, jordan):
    claude.reply = "You agreed on 7pm at Ramen Ya."
    send_message(jordan, chat, "7pm at Ramen Ya?")
    question = send_message(francis, chat, "@clique what time did we agree on?")
    send_message(jordan, chat, "Later message")

    answer = ask_clique(francis, question)

    assert answer == "You agreed on 7pm at Ramen Ya."
    prompt = claude.sent["messages"][0]["content"]
    assert "jordan: 7pm at Ramen Ya?" in prompt
    assert "<question>\n@clique what time did we agree on?\n</question>" in prompt
    assert "Later message" not in prompt
    assert AIRequest.objects.get().feature == AIRequest.Feature.MENTION


def test_ask_clique_respects_chats_with_ai_off(claude, chat, francis):
    question = send_message(francis, chat, "@clique hi")
    chat.ai_enabled = False
    chat.save()

    with pytest.raises(AIError, match="turned off"):
        ask_clique(francis, question)


@pytest.fixture
def no_live_updates(monkeypatch):
    """Skip "Clique AI is typing…", which needs open chat pages."""
    monkeypatch.setattr("ai.tasks.show_ai_thinking", lambda chat_id: None)


def test_answer_mention_posts_an_ai_message(claude, no_live_updates, chat, francis):
    claude.reply = "Sounds like Friday!"
    question = send_message(francis, chat, "@clique when?")

    answer_mention(question.pk)

    answer = chat.messages.last()
    assert answer.kind == Message.Kind.AI
    assert answer.sender is None
    assert answer.sender_name == "Clique AI"
    assert answer.body == "Sounds like Friday!"


def test_answer_mention_explains_problems_in_the_chat(no_live_updates, settings, chat, francis):
    settings.ANTHROPIC_API_KEY = ""
    question = send_message(francis, chat, "@clique when?")

    answer_mention(question.pk)

    assert chat.messages.last().body == "Clique AI isn't set up yet."


def test_answer_mention_survives_unexpected_errors(claude, no_live_updates, chat, francis, caplog):
    claude.error = ValueError("surprise")
    question = send_message(francis, chat, "@clique when?")

    answer_mention(question.pk)

    assert "ran into a problem" in chat.messages.last().body
    assert "@clique answer failed" in caplog.text


def test_answer_mention_skips_deleted_questions(claude, no_live_updates, chat, francis):
    question = send_message(francis, chat, "@clique when?")
    delete_message(francis, question)

    answer_mention(question.pk)

    assert claude.sent is None
    assert not chat.messages.filter(kind=Message.Kind.AI).exists()


@pytest.fixture
def background(monkeypatch):
    """Records background jobs instead of running them."""
    jobs = []
    monkeypatch.setattr(
        "chats.services.run_in_background", lambda task, *args: jobs.append((task, args))
    )
    return jobs


def test_mentioning_clique_starts_an_answer(
    background, django_capture_on_commit_callbacks, chat, francis
):
    with django_capture_on_commit_callbacks(execute=True):
        question = send_message(francis, chat, "@clique what's the plan?")

    assert background == [(answer_mention, (question.pk,))]


@pytest.mark.parametrize("text, ai_on", [("no mention here", True), ("@clique hi", False)])
def test_no_answer_without_mention_or_with_ai_off(
    background, django_capture_on_commit_callbacks, chat, francis, text, ai_on
):
    chat.ai_enabled = ai_on
    chat.save()

    with django_capture_on_commit_callbacks(execute=True):
        send_message(francis, chat, text)

    assert background == []


def test_ai_messages_look_different(logged_in, chat):
    post_ai_message(chat, "Friday at 7!")

    page = logged_in.get(reverse("chats:detail", args=[chat.pk])).content.decode()

    assert "✨ Clique AI" in page
    assert "ai-bubble" in page
    assert "Edit</a>" not in page  # nobody can edit Clique AI's messages


def test_inbox_preview_of_ai_message(chat, francis):
    message = post_ai_message(chat, "Friday at 7!")

    assert preview(message, francis) == "✨ Clique AI: Friday at 7!"
