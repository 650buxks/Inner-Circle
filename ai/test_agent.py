"""Reply agent tests. A scripted fake Claude asks for tools in a set
order, so we can check the loop without calling the real API."""

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from chats.services import (
    create_group,
    delete_message,
    get_or_create_private_chat,
    send_message,
)

from . import agent as agent_module
from .agent import echoable, get_members, run_agent, search_messages
from .client import AIError
from .models import AIRequest

User = get_user_model()


def text(value):
    return SimpleNamespace(type="text", text=value)


def tool(name, **tool_input):
    return SimpleNamespace(type="tool_use", id=f"call-{name}", name=name, input=tool_input)


def turn(*blocks):
    return SimpleNamespace(
        content=list(blocks),
        stop_reason="tool_use",
        usage=SimpleNamespace(input_tokens=100, output_tokens=20),
    )


@pytest.fixture
def script(monkeypatch, settings):
    """Plays Claude's turns in order and remembers every request."""
    settings.ANTHROPIC_API_KEY = "test-key"
    fake = SimpleNamespace(turns=[], requests=[])

    def fake_call_claude(**request):
        # Copy the list: the agent keeps adding to the same one.
        fake.requests.append({**request, "messages": list(request["messages"])})
        return fake.turns.pop(0)

    monkeypatch.setattr(agent_module, "call_claude", fake_call_claude)
    return fake


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


def test_agent_searches_then_drafts(script, chat, francis, jordan):
    send_message(jordan, chat, "Trip idea: Tahoe in March?")
    send_message(jordan, chat, "so are you coming or not")
    script.turns = [
        turn(text("Let me check."), tool("search_messages", query="trip")),
        turn(tool("draft_reply", text="Yes! Tahoe in March sounds perfect")),
    ]

    result = run_agent(francis, chat, "help me answer Jordan about the trip")

    assert result == {
        "draft": "Yes! Tahoe in March sounds perfect",
        "steps": ["🔎 Searched the chat for “trip”"],
    }
    first, second = script.requests
    assert (
        "<request>\nhelp me answer Jordan about the trip\n</request>"
        in (first["messages"][0]["content"])
    )
    assert [t["name"] for t in first["tools"]] == [
        "search_messages",
        "get_members",
        "answer_privately",
        "draft_reply",
    ]
    # Round 2 carries Claude's tool call and our search result.
    assert second["messages"][1]["role"] == "assistant"
    result_block = second["messages"][2]["content"][0]
    assert result_block["tool_use_id"] == "call-search_messages"
    assert "jordan: Trip idea: Tahoe in March?" in result_block["content"]


def test_agent_answers_questions_privately(script, chat, francis, jordan):
    send_message(jordan, chat, "Hit 315 on squat today")
    script.turns = [
        turn(tool("search_messages", query="squat")),
        turn(tool("answer_privately", text="Jordan said 315 on squat.")),
    ]

    result = run_agent(francis, chat, "how much is he lifting?")

    assert result == {
        "answer": "Jordan said 315 on squat.",
        "steps": ["🔎 Searched the chat for “squat”"],
    }
    assert chat.messages.count() == 1  # nothing posted in the chat


def test_agent_records_tokens_from_every_round(script, chat, francis):
    script.turns = [
        turn(tool("get_members")),
        turn(tool("draft_reply", text="hey all")),
    ]

    run_agent(francis, chat, "say hi")

    request = AIRequest.objects.get()
    assert request.feature == AIRequest.Feature.AGENT
    assert (request.input_tokens, request.output_tokens) == (200, 40)


def test_agent_gives_up_after_too_many_rounds(script, chat, francis):
    script.turns = [turn(tool("get_members")) for _ in range(6)]

    with pytest.raises(AIError, match="couldn't finish"):
        run_agent(francis, chat, "say hi")
    assert len(script.requests) == 6
    assert AIRequest.objects.count() == 1  # still counted


def test_agent_stopping_without_a_draft_is_an_error(script, chat, francis):
    script.turns = [turn(text("I'm not sure what to say."))]

    with pytest.raises(AIError, match="couldn't finish"):
        run_agent(francis, chat, "say hi")


def test_agent_reports_unknown_tools(script, chat, francis):
    script.turns = [
        turn(tool("delete_everything")),
        turn(tool("draft_reply", text="hi")),
    ]

    run_agent(francis, chat, "say hi")

    result_block = script.requests[1]["messages"][2]["content"][0]
    assert result_block["is_error"] is True


@pytest.mark.parametrize(
    "request_text, error",
    [("  ", "Say what you need"), ("x" * 301, "under 300 characters")],
)
def test_agent_checks_the_request(script, chat, francis, request_text, error):
    with pytest.raises(AIError, match=error):
        run_agent(francis, chat, request_text)
    assert script.requests == []


def test_agent_respects_chats_with_ai_off(script, chat, francis):
    chat.ai_enabled = False
    chat.save()

    with pytest.raises(AIError, match="turned off"):
        run_agent(francis, chat, "say hi")


def test_search_skips_deleted_and_opted_out(chat, francis, jordan):
    send_message(jordan, chat, "trip is on")
    gone = send_message(jordan, chat, "trip secret")
    delete_message(jordan, gone)
    send_message(francis, chat, "my trip thoughts")
    francis.ai_opt_out = True
    francis.save()

    found = search_messages(chat, "TRIP")

    assert "trip is on" in found
    assert "secret" not in found
    assert "my trip thoughts" not in found


def test_search_with_no_matches(chat):
    assert search_messages(chat, "volcano") == "No messages mention “volcano”."


def test_search_only_reads_this_chat(chat, francis, jordan):
    sam = User.objects.create_user(username="sam", password="pass")
    francis.friends.add(sam)
    other = get_or_create_private_chat(francis, sam)
    send_message(sam, other, "trip with sam")

    assert "trip with sam" not in search_messages(chat, "trip")


def test_members_list(francis, jordan):
    group = create_group(francis, "Trip", [jordan])

    members = get_members(group, francis)

    assert members == ("francis (the person you're helping) (group admin)\njordan")


def test_echoable_keeps_only_text_before_a_fallback():
    thinking = SimpleNamespace(type="thinking")
    early_call = tool("get_members")
    marker = SimpleNamespace(type="fallback")
    late_call = tool("draft_reply", text="hi")

    kept = echoable([text("a"), thinking, early_call, marker, late_call])

    assert [block.type for block in kept] == ["text", "tool_use"]
    assert kept[1] is late_call


def test_help_me_reply_view_returns_draft_and_steps(client, monkeypatch, chat, francis):
    client.force_login(francis)
    monkeypatch.setattr(
        "chats.views.run_agent",
        lambda user, conversation, request: {
            "draft": "Count me in!",
            "steps": ["👥 Checked who's in the chat"],
        },
    )

    response = client.post(
        reverse("chats:help_me_reply", args=[chat.pk]), {"request": "answer them"}
    )

    data = response.json()
    assert data["draft"] == "Count me in!"
    assert data["steps"] == ["👥 Checked who's in the chat"]
    assert "uses_left" in data


def test_agent_view_reports_errors(client, chat, francis):
    client.force_login(francis)

    response = client.post(reverse("chats:help_me_reply", args=[chat.pk]), {"request": ""})

    assert response.status_code == 400
    assert "Say what you need" in response.json()["error"]


def test_outsiders_cannot_use_the_agent(client, chat):
    outsider = User.objects.create_user(username="sam", password="pass")
    client.force_login(outsider)

    response = client.post(reverse("chats:help_me_reply", args=[chat.pk]), {"request": "hi"})

    assert response.status_code == 404


def test_chat_page_has_agent_button(client, chat, francis):
    client.force_login(francis)

    page = client.get(reverse("chats:detail", args=[chat.pk])).content.decode()

    assert "Help me reply" in page
