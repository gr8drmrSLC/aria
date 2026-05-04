# SECURITY.md — ARIA

Security is a precondition, not a feature. This file is infrastructure.
It governs every deployment decision that touches the public surface.

---

## Secrets inventory

| Secret | Storage | Gitignored? | Exposure risk |
|--------|---------|-------------|---------------|
| `ANTHROPIC_API_KEY` | `.env` | Yes | Unauthorized Claude spend — capped at $5/session by budget guard |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | `.env` | Yes | S3 backup bucket access; IAM permissions scoped to that bucket only |
| `DUCKDNS_TOKEN` | `.env` (moved from crontab 2026-05-04) | Yes | Allows updating aria-agent.duckdns.org DNS record only |
| LinkedIn session cookies | `scripts/update_linkedin.py` runtime only | N/A — not persisted | Allows posting to LinkedIn account |
| SQLite database | `data/aria.db` | Yes | Paper metadata and reports — no PII, low sensitivity |

arXiv is unauthenticated. No PostgreSQL credentials (SQLite only).

---

## Threat model

| Threat | Likelihood | Impact | Prevention |
|--------|------------|--------|------------|
| Anthropic API key exposed | Medium | High | Budget guard ($5 ceiling); rotate immediately if exposed |
| AWS credentials exposed | Medium | High | IAM scoped to S3 bucket; rotate immediately if exposed |
| DuckDNS token exposed | Low | Low | DNS record update only — no data access |
| LinkedIn cookie exposed | Low | Medium | Log out all sessions; cookies expire naturally |
| Bot abuse of public paid endpoint | High | High | Rate limiting (fail-closed) + CAPTCHA + provider spend cap |
| Notification/webhook feedback loop | Medium | High | Failure alerts must route to a different channel — never retry via the same failing path |
| SQLite data exfiltration | Low | Low | No PII; paper metadata only |
| Dependency with CVE | Low | Medium | `pip audit` before any deployment |
| Secrets committed to git | High | Critical | `.gitignore` covers all secret files; pre-commit hook enforces |

---

## Budget guard

`core/analyst.py` and `core/reporter.py` share a session spend counter.

```python
SESSION_SPEND_LIMIT_USD = 5.00
```

Every Claude API call wires `_charge(model, response.usage)` immediately after the response.
If cumulative spend exceeds $5.00, `BudgetExceeded(RuntimeError)` is raised and the process
halts. Restart ARIA to reset the counter.

**Provider-level backstop**: Set a monthly spend cap in the Anthropic Console at
console.anthropic.com → Plans & Billing. Recommended: $20/month. This is the last line
of defense if the process-level guard fails or is bypassed.

Expected daily spend: ~$0.50 (200 papers × 20 batches + 1 report call at Sonnet rates).

---

## EC2 deployment security

| Control | Current state | Required state |
|---------|---------------|----------------|
| `.env` file permissions | 600 (fixed 2026-05-04) | 600 — owner read/write only |
| Dashboard bind address | 127.0.0.1:5051 (fixed 2026-05-04) | localhost only — nginx is the public face |
| PostgreSQL bind address | 0.0.0.0:5432 — **open, not yet fixed** | localhost only — no external connections needed |
| SSH access | Key-based only, port 22 | Restrict to known IPs in AWS security group |
| nginx HTTPS | Let's Encrypt via Certbot | Certbot auto-renews; verify with `certbot renew --dry-run` |
| DuckDNS token | In `.env`, referenced by wrapper script | Never in crontab plaintext |

**PostgreSQL action required**: Port 5432 is listening on 0.0.0.0. Requires sudo to fix.
Edit `/etc/postgresql/*/main/postgresql.conf`: set `listen_addresses = 'localhost'`, restart PostgreSQL.

---

## Public endpoint security gate

Before any public route goes to production, answer three questions:

1. **Can a bot hit this endpoint in a loop?** → add rate limiting, fail-closed
2. **Does each hit trigger a paid external API call?** → add CAPTCHA
3. **What is the worst-case cost at 100,000 hits?** → set provider spend cap before enabling

ARIA's current public surface: `aria-agent.duckdns.org` serves the Flask dashboard via nginx.
The dashboard is **read-only** — no form submissions, no paid API calls per visitor request.
Bot traffic costs nothing. No CAPTCHA required for current functionality.

If a public form or API endpoint that triggers Claude is ever added, apply all three
controls before deploying.

---

## Secret handling rules

**Rule 1 — Secrets live in `.env` only.**
Never in source code, config files, comments, or crontabs. Load via `os.environ.get()`.

**Rule 2 — Never format secrets into strings.**
```python
# Wrong
raise ValueError(f"Auth failed for key: {api_key}")

# Right
raise ValueError("Auth failed — check ANTHROPIC_API_KEY in .env")
```

**Rule 3 — Rotate immediately if exposed.**
1. Revoke and rotate the key — assume it is compromised
2. Check usage logs for the exposure window
3. Update `.env` on local machine and on EC2 (`~/aria/.env`)
4. Document the incident in this file under Incident History

---

## Incident response by secret type

**`ANTHROPIC_API_KEY` exposed:**
1. Rotate at console.anthropic.com → API Keys
2. Check usage dashboard for spend in the exposure window
3. Update `.env` locally and `~/aria/.env` on EC2
4. `sudo systemctl restart aria-runner.service` on EC2

**`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` exposed:**
1. Deactivate keys in AWS IAM console immediately
2. Create new access key pair with same scoped permissions
3. Check CloudTrail for unauthorized S3 access during exposure window
4. Update `.env` locally and `~/aria/.env` on EC2
5. Confirm S3 bucket has public access blocked

**`DUCKDNS_TOKEN` exposed:**
1. Regenerate token at duckdns.org → account settings
2. Update `DUCKDNS_TOKEN` in `~/aria/.env` on EC2
3. Verify `scripts/duckdns_update.sh` runs correctly after update

**LinkedIn session cookies exposed:**
1. Log out all LinkedIn sessions at Settings → Sign in & security → Where you're signed in

---

## Pre-deployment checklist

Run before any deployment that changes the public surface.

1. Does this deployment make anything public that was not public before? If no, stop.
2. What secrets are now in scope of the public surface?
3. Are any secrets baked into build artifacts (JS bundles, config files)?
4. Is any secret one natural-next-step away from being in scope?
5. Does any public endpoint trigger a paid external API call?
   If yes: rate limiting (fail-closed) + CAPTCHA + provider spend cap required.
6. Are `.env` file permissions 600 on EC2?
7. Is PostgreSQL bound to localhost only?
8. Are systemd services set to restart on failure?
9. Run `python tests/smoke_test.py` — all 10 checks must pass.
10. Run `pip audit` — no unresolved critical CVEs.

---

## Secrets scan history

| Date | Tool | Scope | Result |
|------|------|-------|--------|
| 2026-05-04 | Manual `git log -p` grep | Full 32-commit history | CLEAN — no secrets committed |
