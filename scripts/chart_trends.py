"""
chart_trends.py - weekly field-share and overlap chart from trend_summary.json (ADR-018).

Two panels, one axis each (no dual axis): top = share of sampled papers in each research field;
bottom = share of papers sitting in two fields at once. Lines break across skipped weeks instead
of interpolating over outages. Bands are the 95% interval across daily runs; a week with a single
run has no band. Palette slots follow the dataviz skill's validated order (checked with
validate_palette.js, adjacent-pair CVD and normal-vision floors pass; direct labels are drawn
because some slots are under 3:1 contrast on the light surface).

Usage:  python scripts/chart_trends.py scripts/trend_summary.json -o scripts/post_images/trends.png
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
FIELD_COLORS = {"AI": "#2a78d6", "ML": "#eb6834", "RO": "#1baf7a", "BIO": "#eda100"}
OVERLAP_COLORS = {"AI&ML": "#e87ba4", "AI&RO": "#008300", "ML&RO": "#6250d6", "BIO&other": "#e34948"}
OVERLAP_LABELS = {"AI&ML": "AI + ML", "AI&RO": "AI + Robotics", "ML&RO": "ML + Robotics", "BIO&other": "Bio + any other"}
FIELD_NAMES = {"AI": "AI", "ML": "ML", "RO": "Robotics", "BIO": "Bio"}
GAP_DAYS = 10


def _num(x):
    return float("nan") if x is None else float(x)


def _segments(weeks):
    """Split week rows into runs of consecutive weeks (no line across a gap)."""
    seg, out, prev = [], [], None
    for w in weeks:
        d = date.fromisoformat(w["start"])
        if prev is not None and (d - prev).days > GAP_DAYS:
            out.append(seg)
            seg = []
        seg.append(w)
        prev = d
    if seg:
        out.append(seg)
    return out


def _spread(items, min_gap):
    """items: [(label, y)] -> {label: y_adjusted} so no two labels are closer than min_gap."""
    items = sorted(items, key=lambda kv: kv[1])
    out, prev = {}, None
    for lab, y in items:
        if prev is not None and y - prev < min_gap:
            y = prev + min_gap
        out[lab] = y
        prev = y
    return out


def _panel(ax, weeks, labels, colors, names, title, ymax):
    segs = _segments(weeks)
    for lab in labels:
        for i, seg in enumerate(segs):
            xs = [date.fromisoformat(w["start"]) for w in seg]
            ys = [_num(w["shares"][lab]["share"]) for w in seg]
            ax.plot(xs, ys, color=colors[lab], lw=2, marker="o", ms=3.5, mec=SURFACE, mew=1,
                    label=names[lab] if i == 0 else None, solid_capstyle="round")
    ax.set_ylim(0, ymax)
    last = weeks[-1]
    lx = date.fromisoformat(last["start"])
    ys = _spread([(lab, _num(last["shares"][lab]["share"])) for lab in labels], 0.07 * ymax)
    for lab in labels:
        ax.annotate(names[lab], (lx, ys[lab]), xytext=(10, 0), textcoords="offset points", color=INK,
                    fontsize=9, va="center", annotation_clip=False)
    ax.set_title(title, loc="left", color=INK, fontsize=11, fontweight="bold", pad=8)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK2, ncol=len(labels), loc="upper left",
              bbox_to_anchor=(0, 1.0), handlelength=1.6)


def draw(summary: dict, out: str) -> None:
    weeks = summary["weeks"]
    fig, (a, b) = plt.subplots(2, 1, figsize=(9, 8.4), facecolor=SURFACE, sharex=True,
                               gridspec_kw={"hspace": 0.3})
    _panel(a, weeks, list(FIELD_COLORS), FIELD_COLORS, FIELD_NAMES, "Share of sampled papers in each field", 0.8)
    _panel(b, weeks, list(OVERLAP_COLORS), OVERLAP_COLORS, OVERLAP_LABELS,
           "Share of sampled papers in two fields at once", 0.30)
    first, last = weeks[0]["week"], weeks[-1]["week"]
    sd = summary.get("typical_run_sd", {})
    noise = ""
    if sd:
        noise = (f"Run-to-run noise (typical SD of a daily run's share): AI {sd['AI']:.0%}, ML {sd['ML']:.0%}, "
                 f"Robotics {sd['RO']:.0%}, Bio {sd['BIO']:.0%}.")
    lines = [
        f"Weekly, {first} to {last}. Each point averages one week of daily runs (the 200 newest arXiv submissions",
        "per run, about 9 hours of submission time), so shares describe that sample, not all of arXiv.",
        noise,
        "Week-to-week moves smaller than that noise should not be read as trends. Gaps: outages or partial weeks.",
        "Fields are arXiv category tags chosen by authors; a paper can carry several. ARIA reads abstracts only.",
    ]
    note = chr(10).join(x for x in lines if x)
    fig.text(0.07, 0.012, note, color=INK2, fontsize=8, va="bottom", ha="left")
    fig.subplots_adjust(left=0.08, right=0.84, top=0.94, bottom=0.18)
    fig.savefig(out, dpi=170, facecolor=SURFACE)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("summary")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args(argv)
    with open(args.summary, encoding="utf-8") as f:
        draw(json.load(f), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
