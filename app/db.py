"""SQLite system of record: accounts, shipments, invoices, tickets, and live conversation transcripts.

This is deliberately the boring part. It's what the CRM / billing system already knows. The agent
reads it through tools; the interesting, unstructured history lives in Hindsight (see memory.py).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from . import seed_data

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    company TEXT NOT NULL,
    email TEXT NOT NULL,
    plan TEXT NOT NULL,
    mrr REAL NOT NULL,
    platform TEXT NOT NULL,
    signup_date TEXT NOT NULL,
    account_manager TEXT,
    avatar TEXT
);
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    order_ref TEXT NOT NULL,
    carrier TEXT NOT NULL,
    service TEXT NOT NULL,
    status TEXT NOT NULL,
    tracking TEXT NOT NULL,
    destination TEXT NOT NULL,
    last_event TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    period TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    subject TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL,
    summary TEXT
);
CREATE TABLE IF NOT EXISTS credits (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    invoice_id TEXT,
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS escalations (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    priority TEXT NOT NULL,
    reason TEXT NOT NULL,
    notify TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS service_status (
    component TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    note TEXT
);
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    memory_enabled INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# Credits above this need a human; the agent is told so and the tool enforces it.
MAX_AUTO_CREDIT = 200.0


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # One shared connection; FastAPI runs our sync DB calls on the event loop thread only.
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _all(self, sql: str, *args: Any) -> list[dict]:
        return [dict(r) for r in self._conn.execute(sql, args).fetchall()]

    def _one(self, sql: str, *args: Any) -> dict | None:
        row = self._conn.execute(sql, args).fetchone()
        return dict(row) if row else None

    # ---- seeding -----------------------------------------------------------------------------

    def reset_and_seed(self) -> None:
        t = now()
        with self.tx() as c:
            for table in (
                "messages", "conversations", "escalations", "credits", "tickets",
                "invoices", "shipments", "service_status", "customers",
            ):
                c.execute(f"DELETE FROM {table}")
            for cu in seed_data.CUSTOMERS:
                c.execute(
                    "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        cu["id"], cu["name"], cu["company"], cu["email"], cu["plan"], cu["mrr"],
                        cu["platform"], iso(t - timedelta(days=cu["signup_days_ago"])),
                        cu["account_manager"], cu["avatar"],
                    ),
                )
            for cid, ref, carrier, service, status, tracking, dest, event, days in seed_data.SHIPMENTS:
                c.execute(
                    "INSERT INTO shipments (customer_id, order_ref, carrier, service, status, tracking,"
                    " destination, last_event, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (cid, ref, carrier, service, status, tracking, dest, event, iso(t - timedelta(days=days))),
                )
            c.executemany("INSERT INTO invoices VALUES (?,?,?,?,?)", seed_data.INVOICES)
            for tid, cid, subject, status, prio, days in seed_data.TICKETS:
                c.execute(
                    "INSERT INTO tickets VALUES (?,?,?,?,?,?,?)",
                    (tid, cid, subject, status, prio, iso(t - timedelta(days=days)), None),
                )
            c.executemany("INSERT INTO service_status VALUES (?,?,?)", seed_data.SERVICE_STATUS)

    # ---- customers ---------------------------------------------------------------------------

    def list_customers(self) -> list[dict]:
        return self._all("SELECT * FROM customers ORDER BY id")

    def get_customer(self, customer_id: str) -> dict | None:
        return self._one("SELECT * FROM customers WHERE id = ?", customer_id)

    # ---- tool-facing queries -----------------------------------------------------------------

    def shipments(self, customer_id: str, query: str | None = None, limit: int = 10) -> list[dict]:
        if query:
            like = f"%{query.strip()}%"
            return self._all(
                "SELECT order_ref, carrier, service, status, tracking, destination, last_event, updated_at"
                " FROM shipments WHERE customer_id = ? AND (order_ref LIKE ? OR tracking LIKE ? OR destination LIKE ?)"
                " ORDER BY updated_at DESC LIMIT ?",
                customer_id, like, like, like, limit,
            )
        return self._all(
            "SELECT order_ref, carrier, service, status, tracking, destination, last_event, updated_at"
            " FROM shipments WHERE customer_id = ? ORDER BY updated_at DESC LIMIT ?",
            customer_id, limit,
        )

    def invoices(self, customer_id: str) -> list[dict]:
        return self._all("SELECT * FROM invoices WHERE customer_id = ? ORDER BY id DESC", customer_id)

    def tickets(self, customer_id: str) -> list[dict]:
        return self._all("SELECT * FROM tickets WHERE customer_id = ? ORDER BY created_at DESC", customer_id)

    def service_status(self) -> list[dict]:
        return self._all("SELECT * FROM service_status ORDER BY component")

    def create_ticket(self, customer_id: str, subject: str, priority: str, summary: str) -> dict:
        tid = f"T-{self._next_ticket_number()}"
        with self.tx() as c:
            c.execute(
                "INSERT INTO tickets VALUES (?,?,?,?,?,?,?)",
                (tid, customer_id, subject, "open", priority, iso(now()), summary),
            )
        return self._one("SELECT * FROM tickets WHERE id = ?", tid)  # type: ignore[return-value]

    def _next_ticket_number(self) -> int:
        rows = self._all("SELECT id FROM tickets")
        nums = [int(r["id"].split("-")[1]) for r in rows if r["id"].split("-")[1].isdigit()]
        return max(nums, default=5700) + 1

    def issue_credit(self, customer_id: str, amount: float, reason: str, invoice_id: str | None) -> dict:
        if amount <= 0:
            raise ValueError("Credit amount must be positive.")
        if amount > MAX_AUTO_CREDIT:
            raise ValueError(
                f"Credits above ${MAX_AUTO_CREDIT:.0f} need human approval. Escalate instead."
            )
        if invoice_id and not self._one(
            "SELECT id FROM invoices WHERE id = ? AND customer_id = ?", invoice_id, customer_id
        ):
            raise ValueError(f"Invoice {invoice_id} not found for this customer.")
        cid = f"CN-{uuid.uuid4().hex[:6].upper()}"
        with self.tx() as c:
            c.execute(
                "INSERT INTO credits VALUES (?,?,?,?,?,?)",
                (cid, customer_id, invoice_id, round(amount, 2), reason, iso(now())),
            )
        return {"credit_note": cid, "amount": round(amount, 2), "invoice_id": invoice_id, "reason": reason}

    def escalate(self, customer_id: str, priority: str, reason: str, notify: list[str] | None) -> dict:
        eid = f"ESC-{uuid.uuid4().hex[:6].upper()}"
        with self.tx() as c:
            c.execute(
                "INSERT INTO escalations VALUES (?,?,?,?,?,?)",
                (eid, customer_id, priority, reason, json.dumps(notify or []), iso(now())),
            )
        return {"escalation_id": eid, "priority": priority, "notified": notify or [], "status": "paged on-call"}

    # ---- conversations -----------------------------------------------------------------------

    def start_conversation(self, customer_id: str, memory_enabled: bool) -> dict:
        conv_id = f"conv-{uuid.uuid4().hex[:10]}"
        with self.tx() as c:
            c.execute(
                "INSERT INTO conversations VALUES (?,?,?,?,?,?)",
                (conv_id, customer_id, int(memory_enabled), "open", iso(now()), None),
            )
        return self.get_conversation(conv_id)  # type: ignore[return-value]

    def get_conversation(self, conv_id: str) -> dict | None:
        conv = self._one("SELECT * FROM conversations WHERE id = ?", conv_id)
        if conv:
            conv["memory_enabled"] = bool(conv["memory_enabled"])
        return conv

    def add_message(self, conv_id: str, role: str, content: str) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?,?,?,?)",
                (conv_id, role, content, iso(now())),
            )

    def messages(self, conv_id: str) -> list[dict]:
        return self._all(
            "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id", conv_id
        )

    def resolve_conversation(self, conv_id: str) -> None:
        with self.tx() as c:
            c.execute(
                "UPDATE conversations SET status = 'resolved', resolved_at = ? WHERE id = ?", (iso(now()), conv_id)
            )
