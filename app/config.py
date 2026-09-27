"""Runtime configuration, read once from the environment (and .env if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    # Hindsight (memory)
    hindsight_base_url: str
    hindsight_api_key: str | None
    bank_prefix: str

    # LLM (any OpenAI-compatible endpoint; Groq by default)
    llm_base_url: str
    llm_api_key: str | None
    llm_model: str
    llm_fallback_model: str | None

    # System of record
    db_path: Path

    @property
    def playbook_bank_id(self) -> str:
        return f"{self.bank_prefix}-playbook"

    def customer_bank_id(self, customer_id: str) -> str:
        return f"{self.bank_prefix}-customer-{customer_id.lower()}"


def load_settings() -> Settings:
    return Settings(
        hindsight_base_url=os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"),
        hindsight_api_key=os.getenv("HINDSIGHT_API_KEY") or None,
        bank_prefix=os.getenv("HINDSIGHT_BANK_PREFIX", "shiprelay"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or None,
        llm_model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
        llm_fallback_model=os.getenv("LLM_FALLBACK_MODEL", "qwen/qwen3-32b") or None,
        db_path=Path(os.getenv("DB_PATH", str(ROOT_DIR / "data" / "shiprelay.db"))),
    )


settings = load_settings()
