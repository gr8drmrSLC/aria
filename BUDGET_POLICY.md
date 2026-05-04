# BUDGET_POLICY.md — ARIA

Spend limits, cost reference, and model selection rules.
The budget guard in `core/analyst.py` enforces these limits in code.

---

## Spend limits

| Limit | Value | Enforced by |
|-------|-------|-------------|
| Per session (process lifetime) | $5.00 | `SESSION_SPEND_LIMIT_USD` in `core/analyst.py` |
| Monthly (provider level) | $20.00 | Anthropic Console → Plans & Billing spend cap |

The session limit resets when the process restarts. The provider cap is the backstop
if the process-level guard fails or is bypassed by multiple restarts.

**Set the Anthropic Console cap before enabling any public endpoint or increasing usage.**

---

## Cost reference

Prices in USD per 1,000,000 tokens (as of 2026-05):

| Model | Input $/M | Output $/M | Use case |
|-------|-----------|------------|----------|
| claude-sonnet-4-6 | $3.00 | $15.00 | Default — analysis + reporting |
| claude-haiku-4-5-20251001 | $0.80 | $4.00 | Classification tasks if cost becomes concern |

---

## Expected daily spend

| Step | Calls | Avg tokens (in/out) | Cost |
|------|-------|---------------------|------|
| Paper analysis (200 papers, batches of 10) | 20 | 800 in / 200 out | ~$0.054 |
| Report generation (1 call, top 20 papers) | 1 | 3,000 in / 800 out | ~$0.021 |
| **Daily total** | 21 | — | **~$0.075** |

Pipeline runs 4 days/week (Tue–Fri). Monthly estimate: ~$1.20.
The $5.00 session cap provides ~65× headroom before the guard trips.

---

## Model selection rules

```
Batch paper scoring (10 papers/call)  → claude-sonnet-4-6
Intelligence brief generation         → claude-sonnet-4-6
Any new classification-only task      → consider claude-haiku-4-5-20251001 first
```

Never call a more expensive model when a cheaper one is sufficient for the task.
If adding a new Claude call, estimate cost and add it to the daily total table above.

---

## Budget guard implementation

The current implementation uses a module-level global in `core/analyst.py`:

```python
SESSION_SPEND_LIMIT_USD = 5.00
_session_spend_usd: float = 0.0

def _charge(model: str, usage) -> None:
    global _session_spend_usd
    ...
    if _session_spend_usd > SESSION_SPEND_LIMIT_USD:
        raise BudgetExceeded(...)
```

**Known limitation**: The counter resets on every process restart. A bad actor or
runaway loop that repeatedly restarts the process could accumulate spend across sessions.
The Anthropic Console monthly cap is the mitigation for this scenario.

**Planned upgrade**: Replace with the `BudgetGuard` class from the build-with-ai
framework (`src/core/budget_guard.py`), which provides persistent tracking, per-call
limits, and cleaner testability. Tracked in PROJECT_STATUS.md.

---

## Adding a new paid API call — checklist

Before adding any new call to a paid external API:

1. Estimate cost per call and add to the daily total table above
2. Confirm the session limit still provides adequate headroom
3. Wire `_charge()` (or `BudgetGuard.check()` after the upgrade) immediately after the call
4. Never add a paid call without a corresponding budget check
5. If the call is triggered by a public endpoint, apply the Public Endpoint Security Gate
   from `SECURITY.md` before deploying
