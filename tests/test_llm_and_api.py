from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import BadRequestError

from app.config import load_settings
from app.llm import OpenAICompatibleLLM, clean_text, parse_json_object
from app.main import create_app
from tests.conftest import ScriptedLLM


class _Msg:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


class _Resp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": _Msg(content)})()]


class FlakyCompletions:
    """Fails with Groq-style tool_use_failed N times, then answers."""

    def __init__(self, failures: int):
        self.failures = failures
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) <= self.failures:
            req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
            raise BadRequestError(
                "tool_use_failed",
                response=httpx.Response(400, request=req),
                body={"error": {"code": "tool_use_failed"}},
            )
        return _Resp("<think>hmm</think>Here you go.")


def llm_with(failures: int):
    fake = type("Client", (), {})()
    fake.chat = type("Chat", (), {})()
    fake.chat.completions = FlakyCompletions(failures)
    return OpenAICompatibleLLM(load_settings(), client=fake), fake.chat.completions


async def test_llm_retries_then_falls_back_to_other_model():
    llm, calls = llm_with(failures=2)
    out = await llm.complete([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
    assert out["content"] == "Here you go."
    assert calls.calls[2]["model"] == load_settings().llm_fallback_model


async def test_llm_last_resort_drops_tools():
    llm, calls = llm_with(failures=3)
    out = await llm.complete([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
    assert "tools" not in calls.calls[3]
    assert "degraded" in out


async def test_llm_without_tools_falls_back_to_other_model():
    llm, calls = llm_with(failures=1)
    out = await llm.complete([{"role": "user", "content": "hi"}])
    assert out["content"] == "Here you go."
    assert calls.calls[1]["model"] == load_settings().llm_fallback_model


async def test_llm_gives_up_cleanly():
    llm, _ = llm_with(failures=10)
    with pytest.raises(RuntimeError):
        await llm.complete([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])


def test_parse_json_object_variants():
    assert parse_json_object('Sure! {"a": 1} hope that helps')["a"] == 1
    assert parse_json_object('```json\n{"a": 2}\n```')["a"] == 2
    assert clean_text("<think>x</think> hi ") == "hi"


def test_http_api_end_to_end(db, memory):
    llm = ScriptedLLM([{"content": "Set DPI to 203 like last time."}, {"content": '{"ticket_subject":"x","customer_summary":"s","playbook_note":null}'}])
    client = TestClient(create_app(db=db, memory=memory, llm=llm))

    customers = client.get("/api/customers").json()
    assert len(customers) == 6
    detail = client.get("/api/customers/C1001").json()
    assert detail["tickets"] and detail["shipments"] and detail["invoices"]

    conv = client.post("/api/conversations", json={"customer_id": "C1001", "memory_enabled": True}).json()
    r = client.post(f"/api/conversations/{conv['id']}/messages", json={"message": "blank labels"}).json()
    assert r["reply"].startswith("Set DPI") and r["customer_memories"]
    assert client.post(f"/api/conversations/{conv['id']}/resolve").status_code == 200
    assert client.post(f"/api/conversations/{conv['id']}/resolve").status_code == 409
    assert client.get("/api/customers/C1001/brief").json()["brief"].startswith("- Zebra")

    assert client.post("/api/conversations", json={"customer_id": "NOPE"}).status_code == 404
    assert client.post("/api/conversations/missing/messages", json={"message": "x"}).status_code == 404
    assert client.post(f"/api/conversations/{conv['id']}/messages", json={"message": ""}).status_code == 422
    assert client.get("/").status_code == 200
