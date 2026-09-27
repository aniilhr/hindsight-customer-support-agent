"""Exercise HindsightMemory against the real hindsight_client, with the HTTP layer stubbed out.

This checks that what we send (timestamps, tags, document ids, update_mode, budgets) builds valid
request models in the official client, and that responses are mapped correctly.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hindsight_client import Hindsight
from hindsight_client_api.models.recall_response import RecallResponse
from hindsight_client_api.models.reflect_response import ReflectResponse
from hindsight_client_api.models.retain_response import RetainResponse

from app import seed_data
from app.config import load_settings
from app.memory import HindsightMemory


class StubMemoryApi:
    def __init__(self):
        self.retains = []
        self.recalls = []
        self.reflects = []

    async def retain_memories(self, bank_id, request, _request_timeout=None):
        self.retains.append((bank_id, request))
        return RetainResponse.from_dict(
            {"success": True, "bank_id": bank_id, "items_count": len(request.items), "async": request.var_async}
        )

    async def recall_memories(self, bank_id, request, _request_timeout=None):
        self.recalls.append((bank_id, request))
        return RecallResponse.from_dict(
            {
                "results": [
                    {
                        "id": "m1",
                        "text": "Zebra ZD421 reset to 203 dpi after firmware update",
                        "type": "experience",
                        "occurred_start": "2026-03-12T10:00:00Z",
                    }
                ]
            }
        )

    async def reflect(self, bank_id, request, _request_timeout=None):
        self.reflects.append((bank_id, request))
        return ReflectResponse.from_dict({"text": "- Prefers WhatsApp"})


def make_memory():
    settings = load_settings()
    client = Hindsight(base_url="http://hindsight.test", api_key="k")
    stub = StubMemoryApi()
    client._memory_api = stub
    mem = HindsightMemory(settings, client=client)
    created = []

    async def fake_create_bank(bank_id, **kwargs):
        created.append((bank_id, kwargs))

    client.acreate_bank = fake_create_bank  # type: ignore[method-assign]
    return mem, stub, created, settings


async def test_recall_maps_results_and_creates_bank_once():
    mem, stub, created, settings = make_memory()
    items = await mem.recall_customer("C1001", "blank labels")
    await mem.recall_customer("C1001", "again")

    assert items[0].text.startswith("Zebra ZD421") and items[0].when.startswith("2026-03-12")
    bank_id, req = stub.recalls[0]
    assert bank_id == settings.customer_bank_id("C1001") == "shiprelay-customer-c1001"
    assert req.query == "blank labels" and req.budget.value == "mid"
    assert [b for b, _ in created] == ["shiprelay-customer-c1001"]
    assert "technical environment" in created[0][1]["retain_mission"]


async def test_retain_transcript_upserts_by_conversation():
    mem, stub, _, _ = make_memory()
    await mem.retain_transcript("C1001", "conv-abc", "Customer: hi", datetime(2026, 9, 27, tzinfo=timezone.utc))
    bank_id, req = stub.retains[0]
    item = req.items[0]
    assert bank_id == "shiprelay-customer-c1001"
    assert req.var_async is True
    assert item.document_id == "conv-abc"
    assert item.update_mode == "replace"
    assert "customer:C1001" in item.tags


async def test_retain_resolution_writes_playbook_only_when_lesson_exists():
    mem, stub, _, settings = make_memory()
    await mem.retain_resolution("C1006", "conv-1", "summary", "lesson")
    await mem.retain_resolution("C1006", "conv-2", "summary", None)
    banks = [b for b, _ in stub.retains]
    assert banks.count(settings.playbook_bank_id) == 1
    assert banks.count("shiprelay-customer-c1006") == 2


async def test_seed_builds_valid_batches_for_every_bank():
    mem, stub, created, settings = make_memory()
    counts = await mem.seed(wait=True)
    assert counts[settings.playbook_bank_id] == len(seed_data.PLAYBOOK)
    assert len(stub.retains) == len(seed_data.CUSTOMER_HISTORY) + 1
    for _, req in stub.retains:
        assert req.var_async is False
        for item in req.items:
            assert item.timestamp is not None and item.document_id.startswith("seed-")


async def test_brief_uses_reflect():
    mem, stub, _, _ = make_memory()
    assert await mem.brief("C1003") == "- Prefers WhatsApp"
    assert stub.reflects[0][0] == "shiprelay-customer-c1003"
