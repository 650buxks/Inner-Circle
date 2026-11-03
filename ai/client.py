"""The one place Clique talks to Claude, Anthropic's AI model.

Everything else calls ask_claude() (one question, one answer) or
call_claude() (the full API, used by the reply agent), so the model, error
handling and safety settings live in one file.
"""

import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

# Models that support server-side fallbacks (see ask_claude).
FALLBACK_MODELS = {
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-fable-5-1",
    "claude-sonnet-5-5",
}


class AIError(Exception):
    """Clique AI couldn't help. The message is shown to the user."""


def ask_claude(system, prompt, max_tokens=4000, effort="low"):
    """Send one request to Claude. Returns (text, usage).

    `system` holds our instructions; `prompt` holds the chat content.
    `effort` trades depth of thinking for speed and cost: "low" suits
    short jobs like summaries.
    """
    response = call_claude(
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": effort},
    )
    texts = [block.text for block in response.content if block.type == "text"]
    text = "".join(texts).strip()
    if not text:
        raise AIError("Clique AI didn't come up with anything. Try again.")
    return text, response.usage


def call_claude(**request):
    """Send one request to Claude and return the whole response.

    `request` holds the Messages API arguments (system, messages, tools…);
    this adds the model, the safety fallbacks and the error handling.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise AIError("Clique AI isn't set up yet.")

    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=60.0,  # seconds; nobody should wait longer than this
    )
    if settings.AI_MODEL in FALLBACK_MODELS:
        # If Claude's safety checks decline a request, the API retries it
        # on a suitable fallback model instead of failing.
        request["betas"] = ["server-side-fallback-2026-07-01"]
        request["fallbacks"] = "default"

    try:
        response = client.beta.messages.create(
            model=settings.AI_MODEL,
            **request,
        )
    except anthropic.RateLimitError:
        logger.warning("Claude rate limit reached")
        raise AIError("Clique AI is busy. Try again in a minute.") from None
    except anthropic.APIError:
        logger.exception("Claude request failed")
        error = "Clique AI isn't available right now. Try again later."
        raise AIError(error) from None

    if response.stop_reason == "refusal":
        raise AIError("Clique AI can't help with this one.")
    return response
