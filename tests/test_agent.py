from __future__ import annotations

import json

import pytest

from app.agent import SupportAgent
from tests.conftest import ScriptedLLM


def system_prompt(llm: ScriptedLLM, call: int = 0) -> str:
    return llm.calls[call]["messages"][0]["content"]


async def test_memory_on_recalls_injects_and_retains(db, memory):
    llm = ScriptedLLM([{"content": "Last time this was the printer DPI. Set it to 203."}])
    agent = SupportAgent(db, memory, llm)
    conv = db.start_conversation("C1001", memory_enabled=True)

    r = await agent.handle_turn(conv["id"], "labels are blank again")

    assert r.reply.startswith("Last time")
    assert memory.recall_calls[0][0] == "C1001"
    prompt = system_prompt(llm)
    assert "203 dpi" in prompt and "Reinstalling the Print Agent did not help" in prompt
    assert "shared troubleshooting playbook" in prompt
    assert r.retained is True
    assert memory.transcripts[0]["conversation_id"] == conv["id"]
    assert "labels are blank again" in memory.transcripts[0]["transcript"]
    assert [m["role"] for m in db.messages(conv["id"])] == ["user", "assistant"]


async def test_memory_off_is_stateless(db, memory):
    llm = ScriptedLLM([{"content": "Please try reinstalling the Print Agent."}])
    agent = SupportAgent(db, memory, llm)
    conv = db.start_conversation("C1001", memory_enabled=False)

    r = await agent.handle_turn(conv["id"], "labels are blank again")

    assert memory.recall_calls == [] and memory.transcripts == []
    assert r.customer_memories == [] and r.retained is False
    prompt = system_prompt(llm)
    assert "203 dpi" not in prompt
    assert "no history for this customer" in prompt
    # The CRM record is still there: that's the baseline we compare against.
    assert "Growth" in prompt


async def test_followup_recall_query_includes_previous_agent_turn(db, memory):
    llm = ScriptedLLM([{"content": "Is it the Zebra ZD421?"}, {"content": "Great."}])
    agent = SupportAgent(db, memory, llm)
    conv = db.start_conversation("C1001", memory_enabled=True)
    await agent.handle_turn(conv["id"], "printing problem")
    await agent.handle_turn(conv["id"], "yes same one")
    assert "Is it the Zebra ZD421?" in memory.recall_calls[1][1]


async def test_tool_call_round_trip(db, memory):
    llm = ScriptedLLM(
        [
            {"tool_calls": [{"id": "t1", "name": "lookup_shipments", "arguments": json.dumps({"query": "KC-20917"})}]},
            {"content": "Order KC-20917 had a failed delivery attempt in Pune."},
        ]
    )
    agent = SupportAgent(db, memory, llm)
    conv = db.start_conversation("C1001", memory_enabled=True)

    r = await agent.handle_turn(conv["id"], "where is KC-20917?")

    assert r.tool_calls[0]["ok"] is True
    assert r.tool_calls[0]["result"][0]["status"] == "exception"
    tool_msg = llm.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "t1"
    assert "Pune" in r.reply


async def test_malformed_tool_args_are_reported_to_model_not_raised(db, memory):
    llm = ScriptedLLM(
        [
            {"tool_calls": [{"id": "t1", "name": "issue_credit", "arguments": "{amount: 20"}]},
            {"tool_calls": [{"id": "t2", "name": "no_such_tool", "arguments": "{}"}]},
            {"content": "Sorry about that, let me get a human to help."},
        ]
    )
    agent = SupportAgent(db, memory, llm)
    conv = db.start_conversation("C1001", memory_enabled=True)

    r = await agent.handle_turn(conv["id"], "refund me")

    assert [t["ok"] for t in r.tool_calls] == [False, False]
    assert "not valid JSON" in r.tool_calls[0]["result"]["error"]
    assert "Unknown tool" in r.tool_calls[1]["result"]["error"]
    assert r.reply


async def test_credit_limit_enforced(db, memory):
    llm = ScriptedLLM(
        [
            {"tool_calls": [{"id": "t1", "name": "issue_credit", "arguments": json.dumps({"amount": 500, "reason": "SLA"})}]},
            {"content": "I've escalated this."},
        ]
    )
    agent = SupportAgent(db, memory, llm)
    conv = db.start_conversation("C1003", memory_enabled=True)
    r = await agent.handle_turn(conv["id"], "I want a credit")
    assert r.tool_calls[0]["ok"] is False
    assert "human approval" in r.tool_calls[0]["result"]["error"]


async def test_recall_failure_degrades_gracefully(db, memory):
    memory.fail_recall = True
    llm = ScriptedLLM([{"content": "Happy to help."}])
    agent = SupportAgent(db, memory, llm)
    conv = db.start_conversation("C1001", memory_enabled=True)

    r = await agent.handle_turn(conv["id"], "hello")

    assert r.reply == "Happy to help."
    assert any("Customer memory unavailable" in w for w in r.warnings)
    assert r.playbook_memories  # playbook still worked


async def test_resolve_retains_summary_and_playbook_lesson(db, memory):
    summary = {
        "ticket_subject": "Blank labels after firmware update",
        "customer_summary": "Zebra reset to 203 dpi again after firmware update; fixed by DPI setting.",
        "playbook_note": "Zebra ZD421 firmware updates reset DPI to 203; set Print Agent DPI to 203.",
        "sentiment": "happy",
    }
    llm = ScriptedLLM([{"content": "Set DPI to 203."}, {"content": "```json\n" + json.dumps(summary) + "\n```"}])
    agent = SupportAgent(db, memory, llm)
    conv = db.start_conversation("C1006", memory_enabled=True)
    await agent.handle_turn(conv["id"], "labels blank since update")

    out = await agent.resolve(conv["id"])

    assert out["retained"] is True
    assert memory.resolutions[0]["playbook_note"].startswith("Zebra ZD421")
    ticket = next(t for t in db.tickets("C1006") if t["id"] == out["ticket_id"])
    assert ticket["status"] == "resolved"
    with pytest.raises(ValueError):
        await agent.resolve(conv["id"])
    with pytest.raises(ValueError):
        await agent.handle_turn(conv["id"], "one more thing")


async def test_resolve_null_playbook_and_non_json(db, memory):
    llm = ScriptedLLM([{"content": "Done."}, {"content": "The customer asked about invoices. Nothing else."}])
    agent = SupportAgent(db, memory, llm)
    conv = db.start_conversation("C1001", memory_enabled=True)
    await agent.handle_turn(conv["id"], "invoice?")
    out = await agent.resolve(conv["id"])
    assert out["playbook_note"] is None
    assert "invoices" in memory.resolutions[0]["summary"]
