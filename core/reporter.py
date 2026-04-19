"""
reporter.py — Intelligence brief generation for ARIA.

When the decider determines a report is warranted, this module calls the
Claude API to draft a structured intelligence brief — a synthesized, readable
summary of what's significant in today's research and why it matters.
"""

import logging
import os
from datetime import datetime, timezone

import anthropic

from core.analyst import _charge

logger = logging.getLogger("aria.reporter")

MODEL = os.environ.get("ARIA_MODEL", "claude-sonnet-4-6")
NOVELTY_THRESHOLD = int(os.environ.get("ARIA_NOVELTY_THRESHOLD", "7"))

SYSTEM_PROMPT = """You are ARIA — Autonomous Research Intelligence Agent. Your role is to produce
concise, authoritative intelligence briefs about emerging research activity.

Write for an audience of senior engineers and researchers who want signal, not noise.
Be direct and specific. Cite paper titles. Explain why something matters.
Never pad. Never repeat yourself. Lead with the most significant finding."""


def _select_notable_papers(papers: list[dict], max_papers: int = 20) -> list[dict]:
    """Return the top papers by novelty score for inclusion in the brief."""
    scored = [p for p in papers if p.get("novelty_score", 0) > 0]
    scored.sort(key=lambda p: p.get("novelty_score", 0), reverse=True)
    return scored[:max_papers]


def _format_paper_for_prompt(paper: dict) -> str:
    themes = ", ".join(paper.get("themes") or [])
    return (
        f"Title: {paper['title']}\n"
        f"Categories: {', '.join(paper.get('categories', []))}\n"
        f"Novelty Score: {paper.get('novelty_score', 0):.1f}/10\n"
        f"Themes: {themes}\n"
        f"Rationale: {paper.get('rationale', '')}\n"
        f"Abstract: {paper.get('abstract', '')[:400]}...\n"
        f"URL: {paper.get('arxiv_url', '')}"
    )


def generate_report(
    papers: list[dict],
    decision: dict,
    date: str | None = None,
) -> dict:
    """
    Generate an intelligence brief for today's notable research activity.

    Args:
        papers:   Analyzed papers from analyst.py (with novelty_score, themes).
        decision: Output dict from decider.decide() with triggers and stats.
        date:     Report date string (ISO). Defaults to today UTC.

    Returns:
        {
            "title": str,
            "content": str (markdown),
            "triggers": list[str],
            "paper_count": int,
        }
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = anthropic.Anthropic()
    notable = _select_notable_papers(papers)
    stats = decision.get("stats", {})
    triggers = decision.get("triggers", [])

    papers_block = "\n\n---\n\n".join(_format_paper_for_prompt(p) for p in notable)

    prompt = f"""Date: {date}
Papers analyzed: {stats.get('paper_count', len(papers))}
Average novelty: {stats.get('avg_novelty', 0):.1f}/10
High-novelty papers: {stats.get('high_novelty_count', 0)}
Cross-domain papers: {stats.get('cross_domain_count', 0)}

Anomaly triggers fired:
{chr(10).join(f'- {t}' for t in triggers)}

Top papers by novelty (for briefing):
{papers_block}

Write a structured intelligence brief in markdown with these sections:
1. **Executive Summary** (2-3 sentences: what's happening today and why it matters)
2. **Key Findings** (3-5 bullet points; for each paper cited, format its title as a markdown link: [Paper Title](arxiv_url))
3. **Emerging Themes** (paragraph identifying cross-paper patterns and what they signal)
4. **Notable Papers** (table with columns: Title | Score | Categories | Link; format each Title cell as [title](arxiv_url) and each Link cell as [arXiv](arxiv_url); top 5-8 papers)
5. **Analyst Note** (1 paragraph: ARIA's assessment of the significance and what to watch next)

Be specific. Use paper titles as markdown links throughout. Explain implications. No filler."""

    logger.info("Generating intelligence brief for %s (%d papers)", date, len(notable))

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        _charge(MODEL, message.usage)
        content = message.content[0].text
    except Exception as exc:
        logger.error("Claude API call failed for report generation: %s", exc)
        content = _fallback_report(papers, decision, date)

    title = f"ARIA Intelligence Brief — {date}"

    return {
        "title": title,
        "content": content,
        "triggers": triggers,
        "paper_count": len(papers),
    }


def _fallback_report(papers: list[dict], decision: dict, date: str) -> str:
    """Minimal report when Claude API is unavailable."""
    stats = decision.get("stats", {})
    notable = _select_notable_papers(papers, max_papers=5)
    lines = [
        f"# ARIA Intelligence Brief — {date}",
        "\n**Note:** Generated in fallback mode (Claude API unavailable)\n",
        f"**Papers analyzed:** {stats.get('paper_count', len(papers))}  ",
        f"**Avg novelty:** {stats.get('avg_novelty', 0):.1f}/10  ",
        f"**Triggers:** {', '.join(decision.get('trigger_names', []))}\n",
        "## Top Papers\n",
    ]
    for p in notable:
        lines.append(
            f"- **{p['title']}** (score: {p.get('novelty_score', 0):.1f}) — {p.get('arxiv_url', '')}"
        )
    return "\n".join(lines)
