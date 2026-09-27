"""The support agent: recall -> reason (with tools) -> reply -> retain.

With memory off, the same agent runs with only the CRM record, which is what most support bots have.
Comparing the two modes on the same customer is the fastest way to see what Hindsight adds.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .db import Database
from .llm import ChatLLM, parse_json_object
from .memory import MemoryItem, SupportMemory
from .tools import TOOL_SPECS, ToolExecutor

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5

BASE_PROMPT = """You are Relay, the support agent for ShipRelay, a shipping and fulfilment platform for online merchants \
(label printing via the ShipRelay Print Agent, carrier rates, Shopify/WooCommerce/Etsy order sync, tracking webhooks, billing).

Today is {today}. You are chatting with {name} from {company}.

CRM record (system of record):
{crm}

How to work:
- Be concise: 2-6 sentences or a short numbered list. Plain text, no markdown headers.
- Use tools to check facts (shipments, invoices, service status) instead of guessing.
- Credits over $200, P1 incidents and anything you can't fix: escalate_to_human.
- Never invent settings, menu paths, versions or policies you haven't been told about."""

MEMORY_PROMPT = """

What you remember about this customer (long-term memory from past tickets and chats):
{customer_memories}

Fixes that worked for other merchants (shared troubleshooting playbook, anonymised):
{playbook_memories}

How to use memory:
- Don't make the customer repeat their setup or history; refer to it naturally ("last time this was...").
- If a past fix matches the symptom, lead with it. Never re-suggest something that already failed for them.
- Honour promises and commitments recorded in memory (who to escalate to, who to copy, thresholds agreed).
- Adapt to their communication preferences and mood. Acknowledge recurring pain before troubleshooting.
- Playbook entries are about other merchants: use the fix, never mention other customers."""

NO_MEMORY_NOTE = "\n\n(You have no history for this customer beyond the CRM record above.)"

RESOLVE_PROMPT = """You are closing a ShipRelay support conversation. Read the transcript and return ONLY a JSON object:
{{
  "ticket_subject": "short subject line",
  "customer_summary": "3-6 sentences for this customer's long-term memory: their setup details learned, the problem, \
root cause, what fixed it, anything that did NOT work, their mood, and any promise or commitment we made.",
  "playbook_note": "2-4 sentences of reusable, anonymised troubleshooting knowledge (symptom, environment, root cause, \
exact fix, what did not work). No names or company names. Use null if nothing reusable was learned.",
  "sentiment": "happy | neutral | frustrated | angry"
}}

Customer: {name} ({company})
Transcript:
{transcript}"""


@dataclass
class TurnResult:
    reply: str
    memory_enabled: bool
    customer_memories: list[dict] = field(default_factory=list)
    playbook_memories: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    retained: bool = False
    warnings: list[str] = field(default_factory=list)
    model: str | None = None


def _format_memories(items: list[MemoryItem]) -> str:
    if not items:
        return "- (nothing relevant found)"
    lines = []
    for m in items:
        when = f"[{m.when[:10]}] " if m.when else ""
        lines.append(f"- {when}{m.text}")
    return "\n".join(lines)


def _format_crm(customer: dict, tickets: list[dict]) -> str:
    lines = [
        f"- Customer ID: {customer['id']}, plan: {customer['plan']} (${customer['mrr']:.0f}/mo), "
        f"platform: {customer['platform']}, customer since {customer['signup_date'][:10]}",
    ]
    if customer.get("account_manager"):
        lines.append(f"- Account manager: {customer['account_manager']}")
    if tickets:
        recent = "; ".join(f"{t['id']} '{t['subject']}' ({t['status']}, {t['created_at'][:10]})" for t in tickets[:5])
        lines.append(f"- Recent tickets: {recent}")
    return "\n".join(lines)


def format_transcript(customer: dict, messages: list[dict]) -> str:
    lines = []
    for m in messages:
        who = f"Customer ({customer['name']}, {customer['company']})" if m["role"] == "user" else "ShipRelay agent"
        lines.append(f"{who}: {m['content']}")
    return "\n".join(lines)


class SupportAgent:
    def __init__(self, db: Database, memory: SupportMemory, llm: ChatLLM):
        self.db = db
        self.memory = memory
        self.llm = llm

    async def _recall(self, customer_id: str, query: str, result: TurnResult) -> None:
        cust, play = await asyncio.gather(
            self.memory.recall_customer(customer_id, query),
            self.memory.recall_playbook(query),
            return_exceptions=True,
        )
        if isinstance(cust, Exception):
            log.warning("customer recall failed: %s", cust)
            result.warnings.append(f"Customer memory unavailable: {cust}")
        else:
            result.customer_memories = [m.to_dict() for m in cust]
        if isinstance(play, Exception):
            log.warning("playbook recall failed: %s", play)
            result.warnings.append(f"Playbook memory unavailable: {play}")
        else:
            result.playbook_memories = [m.to_dict() for m in play]

    def _system_prompt(self, customer: dict, result: TurnResult) -> str:
        prompt = BASE_PROMPT.format(
            today=datetime.now(timezone.utc).strftime("%A %d %B %Y"),
            name=customer["name"],
            company=customer["company"],
            crm=_format_crm(customer, self.db.tickets(customer["id"])),
        )
        if not result.memory_enabled:
            return prompt + NO_MEMORY_NOTE
        return prompt + MEMORY_PROMPT.format(
            customer_memories=_format_memories([MemoryItem(**m) for m in result.customer_memories]),
            playbook_memories=_format_memories([MemoryItem(**m) for m in result.playbook_memories]),
        )

    async def handle_turn(self, conversation_id: str, user_message: str) -> TurnResult:
        conv = self.db.get_conversation(conversation_id)
        if conv is None:
            raise KeyError(conversation_id)
        if conv["status"] != "open":
            raise ValueError("Conversation is already resolved; start a new one.")
        customer = self.db.get_customer(conv["customer_id"])
        assert customer is not None

        result = TurnResult(reply="", memory_enabled=conv["memory_enabled"])
        history = self.db.messages(conversation_id)

        if result.memory_enabled:
            # Query with the new message plus the previous agent turn so short follow-ups
            # ("still broken", "yes the same printer") still retrieve the right history.
            prev = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
            query = f"{user_message}\n\n(Previous agent message: {prev[:300]})" if prev else user_message
            await self._recall(customer["id"], query, result)

        messages: list[dict] = [{"role": "system", "content": self._system_prompt(customer, result)}]
        messages += [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": user_message})

        executor = ToolExecutor(self.db, customer["id"])
        reply = ""
        for _ in range(MAX_TOOL_ROUNDS):
            out = await self.llm.complete(messages, tools=TOOL_SPECS)
            result.model = out.get("model")
            if out.get("degraded"):
                result.warnings.append(out["degraded"])
            if not out["tool_calls"]:
                reply = out["content"]
                break
            messages.append(
                {
                    "role": "assistant",
                    "content": out["content"] or None,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                        for tc in out["tool_calls"]
                    ],
                }
            )
            for tc in out["tool_calls"]:
                tool_result, ok = executor.run(tc["name"], tc["arguments"])
                result.tool_calls.append({"name": tc["name"], "arguments": tc["arguments"], "ok": ok, "result": tool_result})
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(tool_result, default=str)})
        else:
            # Too many tool rounds: force a final answer from what we have.
            out = await self.llm.complete(messages + [{"role": "user", "content": "(Answer the customer now.)"}])
            reply = out["content"]

        if not reply:
            reply = "Sorry, I didn't get that. Could you tell me a bit more about what's happening?"
            result.warnings.append("Model returned an empty reply")
        result.reply = reply

        self.db.add_message(conversation_id, "user", user_message)
        self.db.add_message(conversation_id, "assistant", reply)

        if result.memory_enabled:
            try:
                transcript = format_transcript(customer, self.db.messages(conversation_id))
                started = datetime.fromisoformat(conv["created_at"])
                await self.memory.retain_transcript(customer["id"], conversation_id, transcript, started)
                result.retained = True
            except Exception as e:  # memory write must never break the chat
                log.warning("retain failed: %s", e)
                result.warnings.append(f"Could not save to memory: {e}")
        return result

    async def resolve(self, conversation_id: str) -> dict:
        conv = self.db.get_conversation(conversation_id)
        if conv is None:
            raise KeyError(conversation_id)
        if conv["status"] != "open":
            raise ValueError("Conversation is already resolved.")
        customer = self.db.get_customer(conv["customer_id"])
        assert customer is not None
        messages = self.db.messages(conversation_id)
        if not messages:
            raise ValueError("Nothing to resolve: the conversation is empty.")
        transcript = format_transcript(customer, messages)

        out = await self.llm.complete(
            [{"role": "user", "content": RESOLVE_PROMPT.format(name=customer["name"], company=customer["company"], transcript=transcript)}]
        )
        try:
            data = parse_json_object(out["content"])
        except (ValueError, json.JSONDecodeError):
            log.warning("resolve summary was not JSON; storing raw text")
            data = {"ticket_subject": "Chat support", "customer_summary": out["content"], "playbook_note": None, "sentiment": "neutral"}

        playbook_note = data.get("playbook_note")
        if not isinstance(playbook_note, str) or playbook_note.strip().lower() in ("", "null", "none"):
            playbook_note = None

        ticket = self.db.create_ticket(
            customer["id"], str(data.get("ticket_subject") or "Chat support"), "medium", str(data.get("customer_summary", ""))
        )
        with self.db.tx() as c:
            c.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (ticket["id"],))
        self.db.resolve_conversation(conversation_id)

        learned = False
        if conv["memory_enabled"]:
            await self.memory.retain_resolution(
                customer["id"], conversation_id, str(data.get("customer_summary", "")), playbook_note
            )
            learned = True
        return {
            "ticket_id": ticket["id"],
            "summary": data.get("customer_summary"),
            "playbook_note": playbook_note,
            "sentiment": data.get("sentiment"),
            "retained": learned,
        }

    async def brief(self, customer_id: str) -> str:
        return await self.memory.brief(customer_id)
