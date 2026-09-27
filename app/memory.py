"""Hindsight memory for the support agent.

Two kinds of memory bank:

* ``<prefix>-customer-<id>``: one bank per customer. Everything we learn about that account:
  their setup, past problems, what fixed them, what annoyed them, promises we made. Keeping it in a
  separate bank per customer means one customer's history can never leak into another's answer.
* ``<prefix>-playbook``: one shared bank of anonymised resolutions ("symptom -> root cause -> fix
  that worked -> fix that didn't"). When a ticket is resolved we write the generalised lesson here,
  so the next customer with the same problem benefits on their first message.

Every turn: recall from both banks -> answer -> retain the transcript (async, keyed by conversation
so it's upserted rather than duplicated). On resolve: retain a distilled summary + playbook lesson.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from hindsight_client import Hindsight

from . import seed_data
from .config import Settings

log = logging.getLogger(__name__)

CUSTOMER_RETAIN_MISSION = (
    "You are building the long-term memory of a customer support team for ShipRelay, a shipping and "
    "fulfilment platform. Extract facts a support agent would need the next time this customer writes in: "
    "their technical environment (store platform, printer model, plugin/firmware versions, OS, carriers), "
    "each problem they had with its root cause, the fix that worked and any suggestion that did NOT work, "
    "their frustration level and risk of churn, promises or commitments we made to them, credits issued, "
    "and how they prefer to be communicated with. Ignore pleasantries."
)

PLAYBOOK_RETAIN_MISSION = (
    "You are building a troubleshooting playbook for ShipRelay support. Extract reusable, anonymised "
    "knowledge: the symptom as a merchant would describe it, the environment it happens in, the root cause, "
    "the exact fix that worked (menu paths, settings, versions) and fixes that did not work. Never store "
    "customer names, emails or company names."
)

CUSTOMER_REFLECT_MISSION = (
    "You brief ShipRelay support agents before they reply to a customer. Be concrete and short. Lead with "
    "anything that changes how the agent should behave (recurring issue, at-risk account, promises made, "
    "things not to suggest again)."
)

BRIEF_QUERY = (
    "Brief me before I reply to this customer. In at most 5 short bullets: their setup, recurring or open "
    "issues, what fixed things before and what I should NOT suggest again, their mood / churn risk and any "
    "promises we made, and how they like to be communicated with."
)


@dataclass
class MemoryItem:
    text: str
    type: str | None = None
    when: str | None = None
    context: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class SupportMemory(Protocol):
    """What the agent needs from a memory layer. HindsightMemory is the real one; tests use a fake."""

    async def recall_customer(self, customer_id: str, query: str) -> list[MemoryItem]: ...
    async def recall_playbook(self, query: str) -> list[MemoryItem]: ...
    async def retain_transcript(
        self, customer_id: str, conversation_id: str, transcript: str, started_at: datetime
    ) -> None: ...
    async def retain_resolution(
        self, customer_id: str, conversation_id: str, customer_summary: str, playbook_note: str | None
    ) -> None: ...
    async def brief(self, customer_id: str) -> str: ...


class HindsightMemory:
    def __init__(self, settings: Settings, client: Hindsight | None = None):
        self.settings = settings
        self.client = client or Hindsight(
            base_url=settings.hindsight_base_url,
            api_key=settings.hindsight_api_key,
            timeout=60.0,
            user_agent="shiprelay-support-agent/1.0",
        )
        self._ready_banks: set[str] = set()
        self._bank_lock = asyncio.Lock()

    # ---- bank setup --------------------------------------------------------------------------

    async def _ensure_bank(self, bank_id: str, *, playbook: bool) -> None:
        if bank_id in self._ready_banks:
            return
        async with self._bank_lock:
            if bank_id in self._ready_banks:
                return
            await self.client.acreate_bank(
                bank_id,
                retain_mission=PLAYBOOK_RETAIN_MISSION if playbook else CUSTOMER_RETAIN_MISSION,
                reflect_mission=None if playbook else CUSTOMER_REFLECT_MISSION,
                enable_observations=True,
            )
            self._ready_banks.add(bank_id)

    async def _customer_bank(self, customer_id: str) -> str:
        bank_id = self.settings.customer_bank_id(customer_id)
        await self._ensure_bank(bank_id, playbook=False)
        return bank_id

    async def _playbook_bank(self) -> str:
        bank_id = self.settings.playbook_bank_id
        await self._ensure_bank(bank_id, playbook=True)
        return bank_id

    # ---- recall ------------------------------------------------------------------------------

    @staticmethod
    def _to_items(response) -> list[MemoryItem]:
        items = []
        for r in response.results:
            items.append(
                MemoryItem(
                    text=r.text,
                    type=r.type,
                    when=r.occurred_start or r.mentioned_at,
                    context=r.context,
                )
            )
        return items

    async def recall_customer(self, customer_id: str, query: str) -> list[MemoryItem]:
        bank_id = await self._customer_bank(customer_id)
        resp = await self.client.arecall(
            bank_id=bank_id,
            query=query,
            budget="mid",
            max_tokens=2048,
            query_timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )
        return self._to_items(resp)[:12]

    async def recall_playbook(self, query: str) -> list[MemoryItem]:
        bank_id = await self._playbook_bank()
        resp = await self.client.arecall(bank_id=bank_id, query=query, budget="low", max_tokens=1024)
        return self._to_items(resp)[:6]

    # ---- retain ------------------------------------------------------------------------------

    async def retain_transcript(
        self, customer_id: str, conversation_id: str, transcript: str, started_at: datetime
    ) -> None:
        bank_id = await self._customer_bank(customer_id)
        # Same document_id every turn -> Hindsight replaces the previous version of this conversation
        # instead of stacking near-duplicate facts. Async so the customer never waits on extraction.
        await self.client.aretain(
            bank_id=bank_id,
            content=transcript,
            timestamp=started_at,
            context="live support chat transcript",
            document_id=conversation_id,
            update_mode="replace",
            tags=[f"customer:{customer_id}", "channel:chat"],
            retain_async=True,
        )

    async def retain_resolution(
        self, customer_id: str, conversation_id: str, customer_summary: str, playbook_note: str | None
    ) -> None:
        now = datetime.now(timezone.utc)
        customer_bank = await self._customer_bank(customer_id)
        jobs = [
            self.client.aretain(
                bank_id=customer_bank,
                content=customer_summary,
                timestamp=now,
                context="resolved support case summary",
                document_id=f"{conversation_id}-summary",
                tags=[f"customer:{customer_id}", "resolution"],
                retain_async=True,
            )
        ]
        if playbook_note:
            playbook_bank = await self._playbook_bank()
            jobs.append(
                self.client.aretain(
                    bank_id=playbook_bank,
                    content=playbook_note,
                    timestamp=now,
                    context="resolved issue (learned from live support)",
                    document_id=f"{conversation_id}-playbook",
                    tags=["playbook", "learned-live"],
                    retain_async=True,
                )
            )
        await asyncio.gather(*jobs)

    # ---- reflect -----------------------------------------------------------------------------

    async def brief(self, customer_id: str) -> str:
        bank_id = await self._customer_bank(customer_id)
        resp = await self.client.areflect(bank_id=bank_id, query=BRIEF_QUERY, budget="low", max_tokens=600)
        return resp.text

    # ---- seeding -----------------------------------------------------------------------------

    async def seed(self, *, wait: bool = True) -> dict[str, int]:
        """Load the synthetic history into Hindsight. Idempotent: every item has a stable document_id."""
        now = datetime.now(timezone.utc)
        counts: dict[str, int] = {}
        for customer_id, history in seed_data.CUSTOMER_HISTORY.items():
            bank_id = await self._customer_bank(customer_id)
            items = [
                {
                    "content": h["content"],
                    "timestamp": now - timedelta(days=h["days_ago"]),
                    "context": h["context"],
                    "document_id": f"seed-{customer_id}-{i}",
                    "tags": [f"customer:{customer_id}", "seed"],
                }
                for i, h in enumerate(history)
            ]
            await self.client.aretain_batch(bank_id=bank_id, items=items, retain_async=not wait)
            counts[bank_id] = len(items)

        playbook_bank = await self._playbook_bank()
        items = [
            {
                "content": p["content"],
                "timestamp": now - timedelta(days=p["days_ago"]),
                "context": p["context"],
                "document_id": f"seed-playbook-{i}",
                "tags": ["playbook", "seed"],
            }
            for i, p in enumerate(seed_data.PLAYBOOK)
        ]
        await self.client.aretain_batch(bank_id=playbook_bank, items=items, retain_async=not wait)
        counts[playbook_bank] = len(items)
        return counts

    async def delete_all_banks(self) -> None:
        bank_ids = [self.settings.customer_bank_id(c["id"]) for c in seed_data.CUSTOMERS]
        bank_ids.append(self.settings.playbook_bank_id)
        for bank_id in bank_ids:
            try:
                await self.client.banks.delete_bank(bank_id)
            except Exception as e:  # bank may not exist yet
                log.info("delete_bank(%s) skipped: %s", bank_id, e)
        self._ready_banks.clear()

    async def aclose(self) -> None:
        await self.client.aclose()
