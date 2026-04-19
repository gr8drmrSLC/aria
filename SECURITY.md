# SECURITY.md — ARIA

## Secrets inventory

| Secret | Storage | Gitignored? |
|--------|---------|-------------|
| `ANTHROPIC_API_KEY` | `.env` | Yes — `.env` in .gitignore |
| LinkedIn session cookies | `scripts/update_linkedin.py` (runtime) | N/A — not persisted |

No other credentials. arXiv is unauthenticated. SQLite DB is local, no external auth.

## Threat model

- **API key exposure**: `ANTHROPIC_API_KEY` is the only paid credential. Exposure means unauthorized Claude API spend. Mitigated by budget guard ($5.00 ceiling) — a leaked key can cost at most $5.00 before the process halts.
- **Database**: `data/aria.db` contains paper metadata and reports. No PII. Low sensitivity.
- **LinkedIn automation**: `scripts/update_linkedin.py` uses session cookies loaded at runtime from env. Cookie exposure would allow posting to the LinkedIn account.

## Budget guard

`core/analyst.py` and `core/reporter.py` share a session spend counter.

```
SESSION_SPEND_LIMIT_USD = 5.00
```

Every Claude API call wires `_charge(model, response.usage)` immediately after the response. If cumulative spend exceeds $5.00, `BudgetExceeded(RuntimeError)` is raised and the process halts. Restart ARIA to reset the counter.

## If a secret is exposed

1. Rotate `ANTHROPIC_API_KEY` immediately at console.anthropic.com → API Keys
2. Check usage dashboard for unauthorized spend
3. Update `.env` with the new key
4. If LinkedIn cookie is exposed: log out all LinkedIn sessions

## .gitignore coverage

`.env`, `.env.*`, `*.pem`, `*.key`, `data/*.db`, `logs/*.log` are all gitignored.
Run `git status` before every commit to verify no secrets are staged.
