"""Groq conversational layer (CLAUDE.md §15.9).

Thin wrapper over Groq's OpenAI-compatible chat-completions endpoint via httpx
(no `groq`/LangChain dependency — Rule #2). The model ONLY converses and extracts
intent; it never sets prices or counts (§15.2 guardrail #1). Those come from the
server-side quoting service and are rendered from structured data, not model text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx
from loguru import logger

from app.config import settings

# The assistant's whole job: hold a friendly sales chat and, once it knows the
# city, business type, and rough count, signal `ready`. It must never invent a
# price or a lead count — the backend computes those.
_SYSTEM_PROMPT = """You are LeadKar's friendly sales assistant. LeadKar sells \
verified Pakistani business leads (name, phone, address, etc.) scraped from \
Google Maps, delivered as CSV + XLSX.

Your job: in a short, warm chat, find out (1) the CITY, (2) the BUSINESS TYPE / \
vertical, and (3) roughly HOW MANY leads they want. Ask at most one question at \
a time. Keep replies to 1-2 sentences.

NEVER state a price, a lead count, or promise a specific number — the system \
calculates and shows those separately. If the user asks the price, say you're \
putting a quote together.

Always respond with a single JSON object, no prose outside it:
{
  "reply": "<your next message to the customer>",
  "city": "<city or null>",
  "vertical": "<business type in their words, or null>",
  "count_wanted": <integer or null>,
  "ready": <true only when city AND vertical are known; count optional>
}"""


@dataclass
class Intent:
    reply: str
    city: str | None
    vertical: str | None
    count_wanted: int | None
    ready: bool


class GroqError(Exception):
    """Raised on a Groq transport/parse failure. Callers degrade gracefully."""


class GroqClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self._model = settings.GROQ_MODEL
        self._base = settings.GROQ_BASE_URL.rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key) and settings.ASSISTANT_ENABLED

    async def chat(self, messages: list[dict[str, str]]) -> Intent:
        """Send conversation history, return the model's reply + extracted intent.

        `messages` is a list of {role, content} (user/assistant turns only — the
        system prompt is prepended here). Raises GroqError on failure.
        """
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": _SYSTEM_PROMPT}, *messages],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=settings.GROQ_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    f"{self._base}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Groq chat failed: {}", exc)
            raise GroqError(str(exc)) from exc

        count = data.get("count_wanted")
        return Intent(
            reply=str(data.get("reply") or "Could you tell me a bit more?"),
            city=_clean(data.get("city")),
            vertical=_clean(data.get("vertical")),
            count_wanted=int(count) if isinstance(count, (int, float)) else None,
            ready=bool(data.get("ready")),
        )


def _clean(v: object) -> str | None:
    if not v or not isinstance(v, str):
        return None
    s = v.strip()
    return s or None
