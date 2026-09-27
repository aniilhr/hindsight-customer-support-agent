"""Tools the support agent can call. All are scoped to the customer in the conversation."""

from __future__ import annotations

import json
from typing import Any, Callable

from .db import MAX_AUTO_CREDIT, Database

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_shipments",
            "description": "List the customer's recent shipments, or search by order reference, tracking number or city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Order ref, tracking number or city. Omit for the latest shipments."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_invoices",
            "description": "List the customer's invoices with amounts and payment status.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_service_status",
            "description": "Current status of ShipRelay components and carrier integrations (label printing, Shopify sync, FedEx rates, etc.).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Open a ticket for follow-up by the support team when the issue can't be fully solved in chat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                    "summary": {"type": "string", "description": "What's wrong, what was tried, what the customer's setup is."},
                },
                "required": ["subject", "priority", "summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_credit",
            "description": f"Issue an account credit (max ${MAX_AUTO_CREDIT:.0f} without human approval) for a billing error or SLA breach.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "reason": {"type": "string"},
                    "invoice_id": {"type": "string", "description": "Invoice the credit relates to, if any."},
                },
                "required": ["amount", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Page a human support engineer. Use for P1/urgent issues, at-risk accounts, or anything outside your authority.",
            "parameters": {
                "type": "object",
                "properties": {
                    "priority": {"type": "string", "enum": ["P1", "P2", "P3"]},
                    "reason": {"type": "string"},
                    "notify": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Extra people to copy, e.g. the account manager.",
                    },
                },
                "required": ["priority", "reason"],
            },
        },
    },
]


class ToolError(Exception):
    pass


def _args(raw: str | dict | None) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ToolError(f"Arguments were not valid JSON ({e.msg}). Call the tool again with a JSON object.")
    if not isinstance(parsed, dict):
        raise ToolError("Arguments must be a JSON object.")
    return parsed


class ToolExecutor:
    def __init__(self, db: Database, customer_id: str):
        self.db = db
        self.customer_id = customer_id
        self._handlers: dict[str, Callable[[dict], Any]] = {
            "lookup_shipments": lambda a: self.db.shipments(self.customer_id, a.get("query")),
            "list_invoices": lambda a: self.db.invoices(self.customer_id),
            "check_service_status": lambda a: self.db.service_status(),
            "create_ticket": self._create_ticket,
            "issue_credit": self._issue_credit,
            "escalate_to_human": self._escalate,
        }

    def _create_ticket(self, a: dict) -> dict:
        _require(a, "subject", "summary")
        priority = a.get("priority", "medium")
        if priority not in ("low", "medium", "high", "urgent"):
            priority = "medium"
        return self.db.create_ticket(self.customer_id, a["subject"], priority, a["summary"])

    def _issue_credit(self, a: dict) -> dict:
        _require(a, "amount", "reason")
        try:
            amount = float(a["amount"])
        except (TypeError, ValueError):
            raise ToolError("amount must be a number")
        try:
            return self.db.issue_credit(self.customer_id, amount, a["reason"], a.get("invoice_id") or None)
        except ValueError as e:
            raise ToolError(str(e))

    def _escalate(self, a: dict) -> dict:
        _require(a, "reason")
        notify = a.get("notify")
        if isinstance(notify, str):
            notify = [notify]
        return self.db.escalate(self.customer_id, a.get("priority", "P2"), a["reason"], notify)

    def run(self, name: str, raw_args: str | dict | None) -> tuple[dict | list, bool]:
        """Execute a tool call. Returns (result, ok). Errors are returned to the model, never raised."""
        handler = self._handlers.get(name)
        if handler is None:
            return {"error": f"Unknown tool '{name}'. Available: {', '.join(self._handlers)}"}, False
        try:
            return handler(_args(raw_args)), True
        except ToolError as e:
            return {"error": str(e)}, False


def _require(a: dict, *keys: str) -> None:
    missing = [k for k in keys if a.get(k) in (None, "")]
    if missing:
        raise ToolError(f"Missing required argument(s): {', '.join(missing)}")
