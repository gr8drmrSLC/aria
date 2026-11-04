"""
postwriter.py — grounded, de-duplicated weekly LinkedIn post text for ARIA (ADR-017).

Why this exists: every template post repeated the same intro paragraph. This module has Claude
write each weekly post from the week's actual reports, then refuses any draft that is too
similar to recent posts, contains numbers it was not given, or uses banned wording.
The checks run in code, so a bad draft cannot slip through on a judgment call.

Public API:
    build_facts(reports, now)              -> dict    # what the model is allowed to say
    validate(text, facts, history)         -> list    # problems; empty list = acceptable
    generate_post(facts, history, ...)     -> str     # draft text (raises PostRejected)
    similarity(a, b)                       -> float   # word-trigram Jaccard, 0..1
    load_history / save_history / add_to_history
Every Claude call is charged to the shared budget guard (see BUDGET_POLICY.md).
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("aria.postwriter")

MODEL = os.environ.get("ARIA_POST_MODEL", os.environ.get("ARIA_MODEL", "claude-sonnet-4-6"))

# Reports created before this date were made under the pre-ADR-016 triggers, which counted ~98%
# of papers as cross-domain. Their trigger names and stats are not trustworthy and are never shown.
LEGACY_TRIGGER_CUTOVER = "2026-11-03"

SIMILARITY_LIMIT = 0.30      # reject a draft this similar to any of the last HISTORY_WINDOW posts
HISTORY_WINDOW = 10
MAX_CHARS = 1100             # body only; the source-code line is appended by the caller
MAX_ATTEMPTS = 3
INTRO_EVERY_DAYS = 28        # the "what ARIA is" sentence appears about once a month

BANNED = [
    "autonomous", "game-changer", "game changer", "revolutionary", "groundbreaking", "breakthrough",
    "baseline still building", "0.0 out of 10", "cross-domain", "statistically", "anomal", "unusual", "*",
    "delve", "unlock", "in today's fast-paced",
]

SYSTEM_PROMPT = """You write one short LinkedIn post at a time about ARIA, a research monitor that
reads a sample of new arXiv papers, has the Claude API score each abstract for novelty and tag
its themes, and files a brief on days that stand out from its own previous month.

Rules:
- For posts about briefs: lead with ONE specific finding, naming the paper by its exact title
  as given, then one or two sentences on why it is interesting, in plain words.
- For a system-status post (no briefs given): say plainly how ARIA is doing using only the facts
  listed, and what a reader should and should not conclude from them.
- Use only the facts you are given. Do not invent numbers, results, authors or affiliations.
  Do not use any percentage or number except those listed under ALLOWED NUMBERS or inside a title.
- Say these are ARIA's model-assigned readings of abstracts, not verified results.
- Voice: a builder sharing something noticed. Plain, specific, no hype, no hashtags,
  no emoji, no questions to the audience, no "excited to share".
- Do not describe ARIA as autonomous. Do not say a day was unusual, anomalous or statistically
  notable, and do not mention trigger names or cross-domain statistics.
- Plain text only: no markdown, no asterisks; write titles in plain quotes or as-is.
- Vary your structure and opening words from the earlier posts shown; never reuse their sentences.
- Under 900 characters. Do not include a link; one is added afterwards.
Return only the post text."""


class PostRejected(RuntimeError):
    """No acceptable draft after MAX_ATTEMPTS. Nothing should be posted."""


# ── Facts ─────────────────────────────────────────────────────────────────────

_LINK = re.compile(r"\[([^\]]+)\]\((?:[^)]+)\)")


def _strip_md(s: str) -> str:
    s = _LINK.sub(r"\1", s)
    return re.sub(r"[*_`#>]+", "", s).strip()


def _section(content: str, name: str) -> str:
    m = re.search(rf"^##\s*{re.escape(name)}\s*\n(.*?)(?=^##\s|\Z)", content or "", re.S | re.M)
    return m.group(1).strip() if m else ""


def _titles(content: str) -> list[str]:
    return [t.strip() for t in _LINK.findall(content or "") if len(t.strip()) > 12]


def _headlines(content: str) -> list[str]:
    body = _section(content, "Key Findings")
    return [h.strip().rstrip(".") for h in re.findall(r"^\s*[-*]\s+\*\*(.+?)\*\*", body, re.M)]


def build_facts(reports: list[dict], now: datetime | None = None, days: int = 7) -> dict | None:
    """Everything the model may say about the window. None when there were no reports."""
    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    window = [r for r in reports if (r.get("created_at") or "")[:10] >= cutoff]
    if not window:
        return None
    items = []
    for r in window:
        content = r.get("content") or ""
        date = (r.get("created_at") or "")[:10]
        item = {
            "id": r.get("id"),
            "date": date,
            "summary": _strip_md(_section(content, "Executive Summary"))[:900],
            "headlines": _headlines(content)[:5],
            "paper_titles": _titles(content)[:8],
        }
        if date >= LEGACY_TRIGGER_CUTOVER:
            item["triggers"] = r.get("triggers") or []
        items.append(item)
    return {
        "kind": "weekly",
        "window_days": days,
        "report_count": len(window),
        "paper_count": sum(int(r.get("paper_count") or 0) for r in window),
        "reports": items,
    }


def build_daily_facts(report: dict) -> dict | None:
    """Facts for a post about one new brief. None if the brief has no usable content."""
    content = report.get("content") or ""
    date = (report.get("created_at") or "")[:10]
    if not content or not date:
        return None
    facts = build_facts([report], datetime.fromisoformat(date + "T12:00:00+00:00"), days=1)
    if facts is None:
        return None
    facts["kind"] = "daily"
    return facts


def build_stats_facts(stats: dict) -> dict | None:
    """Facts for a system-status post. None when the numbers are missing (0 means no data)."""
    total, avg = stats.get("reports_total"), stats.get("avg_novelty")
    if not total or not avg:
        return None
    return {
        "kind": "stats", "window_days": 0, "report_count": int(total), "paper_count": 0, "reports": [],
        "stats_lines": [
            f"ARIA has filed {int(total)} briefs since launch.",
            f"Average model-assigned novelty score of the last 24 hours of papers: {float(avg):.1f} out of 10.",
            "The pipeline runs Tuesday to Friday at 07:00 UTC and reads a sample of up to 200 papers per run.",
        ],
        "extra_numbers": [f"{float(avg):.1f}", "10", "07", "00", "200", "4"],
    }


def _allowed_numbers(facts: dict) -> set[str]:
    allowed = {str(facts["report_count"]), str(facts["paper_count"]), str(facts["window_days"])}
    allowed.update(facts.get("extra_numbers", []))
    for r in facts["reports"]:
        for t in r["paper_titles"] + r["headlines"]:
            allowed.update(re.findall(r"\d+(?:\.\d+)?", t))
    return allowed


# ── History and similarity ────────────────────────────────────────────────────

def _grams(text: str, n: int = 3) -> set[tuple]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def similarity(a: str, b: str) -> float:
    ga, gb = _grams(a), _grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def load_history(path: str) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as exc:
        # A corrupt history would silently disable the repetition check: fail closed.
        raise RuntimeError(f"Post history unreadable ({exc}); fix or delete {path}")


def save_history(path: str, history: list[dict]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(history[-50:], f, indent=2)
    os.replace(tmp, path)


def add_to_history(path: str, key: str, text: str, had_intro: bool, when: datetime | None = None) -> None:
    history = load_history(path)
    history.append({
        "key": key,
        "posted_at": (when or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "had_intro": had_intro,
        "text": text,
    })
    save_history(path, history)


def wants_intro(history: list[dict], now: datetime | None = None) -> bool:
    """True when no post in the last INTRO_EVERY_DAYS days carried the 'what ARIA is' sentence."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=INTRO_EVERY_DAYS)
    for h in history:
        try:
            when = datetime.fromisoformat(h["posted_at"])
        except Exception:
            continue
        if h.get("had_intro") and when >= cutoff:
            return False
    return True


# ── Validation (structural: runs on every draft) ──────────────────────────────

def validate(text: str, facts: dict, history: list[dict]) -> list[str]:
    problems: list[str] = []
    t = (text or "").strip()
    if not t:
        return ["empty draft"]
    if len(t) > MAX_CHARS:
        problems.append(f"too long ({len(t)} > {MAX_CHARS} chars)")
    low = t.lower()
    for phrase in BANNED:
        if phrase in low:
            problems.append(f"banned wording: '{phrase}'")
    allowed = _allowed_numbers(facts)
    for num in re.findall(r"\d+(?:\.\d+)?", t):
        if num not in allowed:
            problems.append(f"number not in the supplied facts: {num}")
    all_titles = [x for r in facts["reports"] for x in r["paper_titles"]]
    if facts.get("kind") != "stats" and all_titles and not any(title.lower() in low for title in all_titles):
        problems.append("does not name any supplied paper by its exact title")
    for h in history[-HISTORY_WINDOW:]:
        s = similarity(t, h.get("text", ""))
        if s >= SIMILARITY_LIMIT:
            problems.append(f"too similar to earlier post {h.get('key')} (similarity {s:.2f})")
    return sorted(set(problems))


# ── Generation ────────────────────────────────────────────────────────────────

def _build_prompt(facts: dict, history: list[dict], include_intro: bool, problems: list[str]) -> str:
    kind = facts.get("kind", "weekly")
    if kind == "stats":
        head = "POST TYPE: system status (no briefs). FACTS:" + "".join(
            chr(10) + "- " + x for x in facts["stats_lines"])
    elif kind == "daily":
        head = f"POST TYPE: one new brief just filed, covering {facts['paper_count']} papers."
    else:
        head = (f"POST TYPE: weekly. WINDOW: last {facts['window_days']} days. ARIA filed "
                f"{facts['report_count']} brief(s) covering {facts['paper_count']} papers.")
    lines = [
        head,
        "ALLOWED NUMBERS: " + ", ".join(sorted(_allowed_numbers(facts), key=lambda x: float(x))),
        "",
        "BRIEFS:" if facts["reports"] else "",
    ]
    for r in facts["reports"]:
        lines.append(f"- Brief {r['id']} ({r['date']}): {r['summary']}")
        if r["headlines"]:
            lines.append("  Key findings: " + " | ".join(r["headlines"]))
        if r["paper_titles"]:
            lines.append("  Papers (exact titles): " + " | ".join(r["paper_titles"]))
    lines.append("")
    lines.append(
        "Include one fresh sentence saying what ARIA is (reads a sample of new arXiv papers, "
        "Claude scores abstracts, tracks topic shifts). Word it differently from earlier posts."
        if include_intro else
        "Do NOT explain what ARIA is; regular readers already know. Just share the finding."
    )
    recent = [h.get("text", "") for h in history[-HISTORY_WINDOW:]]
    if recent:
        lines.append("\nEARLIER POSTS (do not reuse their wording or structure):")
        lines.extend(f"---\n{x}" for x in recent[-4:])
    if problems:
        lines.append("\nYOUR LAST DRAFT WAS REJECTED. Fix all of these:\n- " + "\n- ".join(problems))
    return "\n".join(lines)


def generate_post(facts: dict, history: list[dict], include_intro: bool, client=None) -> str:
    """Draft, validate, retry with the problems fed back. Raises PostRejected if none passes."""
    from core.analyst import _charge  # shared budget guard; BudgetExceeded must propagate

    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    problems: list[str] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        message = client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_prompt(facts, history, include_intro, problems)}],
        )
        _charge(MODEL, message.usage)
        text = message.content[0].text.strip()
        problems = validate(text, facts, history)
        if not problems:
            logger.info("Draft accepted on attempt %d", attempt)
            return text
        logger.warning("Draft rejected (attempt %d): %s", attempt, "; ".join(problems))
    raise PostRejected("No acceptable draft: " + "; ".join(problems))
