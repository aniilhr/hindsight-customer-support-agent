"""Seed the SQLite system of record and load customer history into Hindsight.

    python -m scripts.seed            # reset SQLite + retain history into Hindsight (waits for extraction)
    python -m scripts.seed --reset    # delete the Hindsight banks first (clean demo)
    python -m scripts.seed --db-only  # only reset SQLite
    python -m scripts.seed --check    # recall a few things to confirm memory works
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.db import Database  # noqa: E402
from app.memory import HindsightMemory  # noqa: E402


async def check(memory: HindsightMemory) -> None:
    probes = [
        ("C1001", "labels are printing blank again"),
        ("C1003", "FedEx rates are slow at checkout"),
    ]
    for customer_id, query in probes:
        print(f"\nrecall[{customer_id}] {query!r}")
        for m in await memory.recall_customer(customer_id, query):
            print(f"  - {m.text[:140]}")
    print("\nrecall[playbook] 'zebra printer blank labels after update'")
    for m in await memory.recall_playbook("zebra printer blank labels after update"):
        print(f"  - {m.text[:140]}")
    print("\nbrief[C1003]:")
    print(await memory.brief("C1003"))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="delete Hindsight banks before seeding")
    parser.add_argument("--db-only", action="store_true", help="only reset the SQLite database")
    parser.add_argument("--check", action="store_true", help="run recall/reflect probes and exit")
    parser.add_argument("--no-wait", action="store_true", help="retain asynchronously (faster, memories appear later)")
    args = parser.parse_args()

    memory = HindsightMemory(settings)
    try:
        if args.check:
            await check(memory)
            return

        Database(settings.db_path).reset_and_seed()
        print(f"SQLite seeded at {settings.db_path}")
        if args.db_only:
            return

        if not settings.hindsight_api_key and "localhost" not in settings.hindsight_base_url:
            sys.exit("HINDSIGHT_API_KEY is not set (see .env.example).")
        if args.reset:
            print("Deleting existing Hindsight banks...")
            await memory.delete_all_banks()
        print(f"Retaining history into Hindsight at {settings.hindsight_base_url} (this can take a minute)...")
        counts = await memory.seed(wait=not args.no_wait)
        for bank, n in counts.items():
            print(f"  {bank}: {n} memories")
        print("Done. Try: python -m scripts.seed --check")
    finally:
        await memory.aclose()


if __name__ == "__main__":
    asyncio.run(main())
