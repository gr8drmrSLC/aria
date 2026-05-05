"""
budget_guard.py — session spend tracking and hard cap enforcement for ARIA.

Tracks cumulative Claude API spend per process lifetime. Raises BudgetExceeded
if the session limit is exceeded, halting the pipeline before runaway spend occurs.

The module-level _guard instance in analyst.py is shared across analyst.py and
reporter.py so all Claude calls count against the same session total.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("aria.budget_guard")

_COST_PER_M: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
    "claude-sonnet-4-20250514":  {"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80,  "output":  4.00},
}
_DEFAULT_PRICING: dict[str, float] = {"input": 3.00, "output": 15.00}


class BudgetExceeded(RuntimeError):
    """Raised when a Claude API call would push session spend over the limit."""


@dataclass
class CallRecord:
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class BudgetGuard:
    """
    Tracks Claude API spend for a single process lifetime.

    Call record() immediately after every client.messages.create() response.
    Raises BudgetExceeded if cumulative spend exceeds session_limit_usd.
    Restart the process to reset the counter.
    """

    session_limit_usd: float = 5.00
    _calls: list[CallRecord] = field(default_factory=list, init=False, repr=False)

    def _pricing(self, model: str) -> dict[str, float]:
        model_lower = model.lower()
        for key, rates in _COST_PER_M.items():
            if key in model_lower:
                return rates
        logger.warning("Unknown model '%s' — using Sonnet rates", model)
        return _DEFAULT_PRICING

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """
        Record actual usage from a completed API call.
        Raises BudgetExceeded if the session total now exceeds the limit.
        """
        rates = self._pricing(model)
        cost = (
            input_tokens * rates["input"] + output_tokens * rates["output"]
        ) / 1_000_000
        self._calls.append(
            CallRecord(
                timestamp=datetime.now(timezone.utc),
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            )
        )
        logger.info(
            "API call recorded — model=%s in=%d out=%d cost=$%.4f session=$%.4f",
            model,
            input_tokens,
            output_tokens,
            cost,
            self.session_spend,
        )
        if self.session_spend > self.session_limit_usd:
            raise BudgetExceeded(
                f"Session spend ${self.session_spend:.4f} exceeded limit "
                f"${self.session_limit_usd:.2f}. Restart ARIA to reset."
            )

    @property
    def session_spend(self) -> float:
        """Total spend recorded this session in USD."""
        return sum(c.cost_usd for c in self._calls)

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def summary(self) -> str:
        lines = [
            f"Session spend: ${self.session_spend:.4f} / ${self.session_limit_usd:.2f}",
            f"Calls: {self.call_count}",
        ]
        for i, c in enumerate(self._calls, 1):
            lines.append(
                f"  {i}. {c.model} — {c.input_tokens}in/{c.output_tokens}out"
                f" — ${c.cost_usd:.4f}"
            )
        return "\n".join(lines)
