"""FastAPI app: JSON API for the support console + the static single-page UI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import SupportAgent
from .config import ROOT_DIR, Settings, settings as default_settings
from .db import Database
from .llm import ChatLLM, OpenAICompatibleLLM
from .memory import HindsightMemory, SupportMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
STATIC_DIR = ROOT_DIR / "static"


class NewConversation(BaseModel):
    customer_id: str
    memory_enabled: bool = True


class NewMessage(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


def create_app(
    settings: Settings = default_settings,
    db: Database | None = None,
    memory: SupportMemory | None = None,
    llm: ChatLLM | None = None,
) -> FastAPI:
    db = db or Database(settings.db_path)
    if not db.list_customers():
        db.reset_and_seed()
    memory = memory or HindsightMemory(settings)
    llm = llm or OpenAICompatibleLLM(settings)
    agent = SupportAgent(db, memory, llm)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        if hasattr(memory, "aclose"):
            await memory.aclose()

    app = FastAPI(title="ShipRelay Support Agent", lifespan=lifespan)
    app.state.agent = agent

    @app.get("/api/health")
    async def health():
        return {
            "ok": True,
            "hindsight_url": settings.hindsight_base_url,
            "hindsight_key_set": bool(settings.hindsight_api_key),
            "llm_model": settings.llm_model,
            "llm_key_set": bool(settings.llm_api_key),
        }

    @app.get("/api/customers")
    async def customers():
        return db.list_customers()

    @app.get("/api/customers/{customer_id}")
    async def customer(customer_id: str):
        c = db.get_customer(customer_id)
        if not c:
            raise HTTPException(404, "Unknown customer")
        return {
            **c,
            "tickets": db.tickets(customer_id),
            "shipments": db.shipments(customer_id),
            "invoices": db.invoices(customer_id),
        }

    @app.get("/api/customers/{customer_id}/brief")
    async def brief(customer_id: str):
        if not db.get_customer(customer_id):
            raise HTTPException(404, "Unknown customer")
        try:
            return {"brief": await agent.brief(customer_id)}
        except Exception as e:
            raise HTTPException(502, f"Hindsight reflect failed: {e}")

    @app.post("/api/conversations")
    async def new_conversation(body: NewConversation):
        if not db.get_customer(body.customer_id):
            raise HTTPException(404, "Unknown customer")
        return db.start_conversation(body.customer_id, body.memory_enabled)

    @app.get("/api/conversations/{conversation_id}")
    async def get_conversation(conversation_id: str):
        conv = db.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(404, "Unknown conversation")
        return {**conv, "messages": db.messages(conversation_id)}

    @app.post("/api/conversations/{conversation_id}/messages")
    async def send_message(conversation_id: str, body: NewMessage):
        try:
            result = await agent.handle_turn(conversation_id, body.message.strip())
        except KeyError:
            raise HTTPException(404, "Unknown conversation")
        except ValueError as e:
            raise HTTPException(409, str(e))
        except RuntimeError as e:
            raise HTTPException(502, str(e))
        return asdict(result)

    @app.post("/api/conversations/{conversation_id}/resolve")
    async def resolve(conversation_id: str):
        try:
            return await agent.resolve(conversation_id)
        except KeyError:
            raise HTTPException(404, "Unknown conversation")
        except ValueError as e:
            raise HTTPException(409, str(e))
        except RuntimeError as e:
            raise HTTPException(502, str(e))

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
