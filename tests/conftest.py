from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Database  # noqa: E402
from app.memory import MemoryItem  # noqa: E402


class FakeMemory:
    """In-process stand-in for HindsightMemory that records every call."""

    def __init__(self):
        self.customer = {
            "C1001": [
                MemoryItem(
                    text="Labels printed blank after Zebra firmware reset the ZD421 to 203 dpi; fixed by setting DPI to 203. Reinstalling the Print Agent did not help.",
                    type="experience",
                    when="2026-03-12T10:00:00+00:00",
                )
            ]
        }
        self.playbook = [MemoryItem(text="Zebra ZD421 blank labels after firmware update: set Print Agent DPI to 203.", type="world")]
        self.recall_calls: list[tuple[str, str]] = []
        self.transcripts: list[dict] = []
        self.resolutions: list[dict] = []
        self.fail_recall = False

    async def recall_customer(self, customer_id: str, query: str):
        self.recall_calls.append((customer_id, query))
        if self.fail_recall:
            raise ConnectionError("hindsight down")
        return self.customer.get(customer_id, [])

    async def recall_playbook(self, query: str):
        return self.playbook

    async def retain_transcript(self, customer_id: str, conversation_id: str, transcript: str, started_at: datetime):
        self.transcripts.append({"customer_id": customer_id, "conversation_id": conversation_id, "transcript": transcript})

    async def retain_resolution(self, customer_id, conversation_id, customer_summary, playbook_note):
        self.resolutions.append(
            {"customer_id": customer_id, "summary": customer_summary, "playbook_note": playbook_note}
        )

    async def brief(self, customer_id: str) -> str:
        return "- Zebra ZD421, prefers WhatsApp\n- Do not suggest reinstalling the Print Agent"


class ScriptedLLM:
    """Returns queued responses in order and records the messages it was sent."""

    def __init__(self, responses: list[dict]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def complete(self, messages, tools=None):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        if not self.responses:
            return {"content": "ok", "tool_calls": [], "model": "fake"}
        r = self.responses.pop(0)
        return {"content": r.get("content", ""), "tool_calls": r.get("tool_calls", []), "model": "fake"}


@pytest.fixture
def db():
    d = Database(":memory:")
    d.reset_and_seed()
    return d


@pytest.fixture
def memory():
    return FakeMemory()
