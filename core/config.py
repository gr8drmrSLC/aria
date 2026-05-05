"""
config.py — centralized environment configuration for ARIA.

Single source of truth for every setting. New code should read from
`settings` here instead of calling os.environ.get() directly.

Existing modules (analyst, decider, store, reporter) continue to use
their own os.environ calls — they are not broken by this module.
New modules and future additions should import from here.

Usage:
    from core.config import settings

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    db = Database(settings.db_path)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    root = Path(__file__).resolve().parent.parent
    env_file = root / ".env"
    if env_file.exists():
        load_dotenv(env_file)


_load_env()


def _require(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Required environment variable {name!r} is not set. "
            "Copy .env.example to .env and fill in the value."
        )
    return val


@dataclass(frozen=True)
class Settings:
    # ── Anthropic ──────────────────────────────────────────────────────────────
    anthropic_api_key: str
    aria_model: str

    # ── Pipeline ───────────────────────────────────────────────────────────────
    db_path: str
    log_level: str
    novelty_threshold: int

    # ── Anomaly thresholds ─────────────────────────────────────────────────────
    volume_spike: float
    novelty_burst_pct: float
    significance_surge: float
    cross_domain_min: int

    # ── Dashboard ──────────────────────────────────────────────────────────────
    dashboard_port: int
    dashboard_url: str

    # ── Budget ─────────────────────────────────────────────────────────────────
    session_budget_usd: float


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.
    Cached after first call — environment is read once at startup.
    Call get_settings.cache_clear() in tests to reset between cases.
    """
    return Settings(
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        aria_model=os.environ.get("ARIA_MODEL", "claude-sonnet-4-6"),
        db_path=os.environ.get("ARIA_DB_PATH", "data/aria.db"),
        log_level=os.environ.get("ARIA_LOG_LEVEL", "INFO").upper(),
        novelty_threshold=int(os.environ.get("ARIA_NOVELTY_THRESHOLD", "7")),
        volume_spike=float(os.environ.get("ARIA_VOLUME_SPIKE", "1.5")),
        novelty_burst_pct=float(os.environ.get("ARIA_NOVELTY_BURST_PCT", "0.30")),
        significance_surge=float(os.environ.get("ARIA_SIGNIFICANCE_SURGE", "1.3")),
        cross_domain_min=int(os.environ.get("ARIA_CROSS_DOMAIN_MIN", "3")),
        dashboard_port=int(os.environ.get("ARIA_DASHBOARD_PORT", "5051")),
        dashboard_url=os.environ.get(
            "ARIA_DASHBOARD_URL", "https://aria-agent.duckdns.org"
        ),
        session_budget_usd=float(os.environ.get("ARIA_SESSION_BUDGET_USD", "5.00")),
    )


# Module-level singleton — import this directly in new code
settings = get_settings()
