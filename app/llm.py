"""Thin wrapper over any OpenAI-compatible chat endpoint (Groq by default).

Open models on fast inference hosts occasionally produce malformed tool calls; Groq rejects those with
a 400 ``tool_use_failed``. We don't want a customer to see a stack trace because of that, so:

1. retry once on the primary model,
2. then try the fallback model,
3. then answer without tools (the reply is still grounded in memory + account context).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Protocol

from openai import APIError, AsyncOpenAI, BadRequestError

from .config import Settings

log = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class ChatLLM(Protocol):
    async def complete(self, messages: list[dict], tools: list[dict] | None = None) -> dict: ...


def clean_text(text: str | None) -> str:
    """Strip reasoning blocks some models (e.g. qwen3) inline into content."""
    return _THINK_RE.sub("", text or "").strip()


class OpenAICompatibleLLM:
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None):
        self.model = settings.llm_model
        self.fallback_model = settings.llm_fallback_model
        self.client = client or AsyncOpenAI(
            base_url=settings.llm_base_url, api_key=settings.llm_api_key or "missing-key", timeout=60.0
        )

    async def _call(self, model: str, messages: list[dict], tools: list[dict] | None) -> dict:
        kwargs: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.3}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = await self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        tool_calls = []
        for tc in msg.tool_calls or []:
            tool_calls.append(
                {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments or "{}"}
            )
        return {"content": clean_text(msg.content), "tool_calls": tool_calls, "model": model}

    async def complete(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        attempts: list[tuple[str, list[dict] | None]] = [(self.model, tools)]
        if tools:
            attempts.append((self.model, tools))
            if self.fallback_model and self.fallback_model != self.model:
                attempts.append((self.fallback_model, tools))
            attempts.append((self.model, None))  # last resort: no tools
        elif self.fallback_model and self.fallback_model != self.model:
            # Plain completions (resolve summaries) still deserve a second model, e.g. when the
            # primary one hits a per-model rate limit.
            attempts.append((self.fallback_model, None))
        last_error: Exception | None = None
        for model, attempt_tools in attempts:
            try:
                result = await self._call(model, messages, attempt_tools)
                if attempt_tools is None and tools:
                    result["degraded"] = "answered without tools after repeated tool-call failures"
                return result
            except BadRequestError as e:
                # tool_use_failed and friends: the model produced an invalid tool call. Try the next rung.
                log.warning("LLM bad request on %s (tools=%s): %s", model, bool(attempt_tools), e)
                last_error = e
            except APIError as e:
                log.warning("LLM API error on %s: %s", model, e)
                last_error = e
        raise RuntimeError(f"LLM unavailable: {last_error}") from last_error


def parse_json_object(text: str) -> dict:
    """Parse a JSON object defensively: models sometimes wrap it in prose or code fences."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    return json.loads(text)
