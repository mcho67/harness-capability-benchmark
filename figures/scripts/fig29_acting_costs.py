"""Figure 29 -- why the routing design scores a stronger model lower.

The inversion in Figure 28 is a fact about the design, not about the models,
and the evidence for that sat in one sentence of §5.4 carrying six numbers,
none of them for the weaker model. This figure is that evidence.

**Upper band: acting costs task success, for both cloud models.** Under the
routing design the reply the user reads is what the action returned, so a run
that names an action is a run whose reply the model did not write. Both models
score far lower on the runs where they acted.

**Lower band: the stronger model acts more often, and the gap is in three
categories.** On reasoning both act on three runs in four, and on trivial and
action both act on every run, so the whole of the 64%-against-54% difference
comes from grounding, clarification and robustness -- the three categories
where the right reply is words rather than an action's return.

Every number is computed from the scored rows, using the study's own test for
whether a run acted: a non-empty `tools` list in the recorded decision
(`apparatus/harness/analyze.py`, and `tools/analyze_study2.py:routing_inversion`
which reports the same split in §5.4).

Grayscale-safe: the two models are told apart by row position and label, and
the bars by fill weight, not by hue.

The caption lives in the document, not here (`_style`).
"""

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import _style as S

ROOT = Path(__file__).resolve().parents[3]
STUDY1 = ROOT / "runs" / "full-2026-08-20" / "scored.jsonl"
HAIKU = ROOT / "runs" / "study2" / "routing@claude-haiku-4-5-20251001.scored.jsonl"

# The three categories where the two models' action rates diverge. The other
# three are equal by construction and are reported in the caption instead.
SPLIT = ["grounding", "clarification", "robustness"]


def rows(path, cell=None):
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if cell is None or r.get("cell") == cell:
            yield r


def acted(r):
    return bool((r.get("decision") or {}).get("tools"))


def won(r):
    return 1.0 if r.get("success_strict") in (True, 1, "pass") else 0.0


def summarise(records):
    """Overall split, and the per-category action rate and success-when-acted."""
    yes = [r for r in records if acted(r)]
    no = [r for r in records if not acted(r)]
    by_cat = defaultdict(lambda: {"n": 0, "acted": 0, "won_acted": 0.0})
    for r in records:
        c = by_cat[r["category"]]
        c["n"] += 1
        if acted(r):
            c["acted"] += 1
            c["won_acted"] += won(r)
    return {
        "n": len(records),
        "rate": len(yes) / len(records),
        "acted_n": len(yes),
        "acted_win": sum(won(r) for r in yes) / len(yes),
        "idle_n": len(no),
        "idle_win": sum(won(r) for r in no) / len(no),
        "by_cat": by_cat,
    }


def pct(x):
    """47.5% and 25%, not 47.5% and 25.0% -- halves matter here, zeros do not."""
    t = f"{x * 100:.1f}"
    return (t[:-2] if t.endswith(".0") else t) + "%"


def build():
    sonnet = summarise(list(rows(STUDY1, "C3")))
    haiku = summarise(list(rows(HAIKU)))

    fig, ax = plt.subplots(figsize=(S.WIDTH, 3.9))
    fig.subplots_adjust(left=0.008, right=0.992, top=0.99, bottom=0.01)
    ax.set_xlim(0, 100)
    ax.set_ylim(-4, 100)
    ax.axis("off")

    # One grid for both bands: a label column, a bar, and two number columns.
    XL, XR, XW, XA, XI, XM = 2, 30, 14, 64, 88, 37

    def band(y, title, sub):
        ax.text(XL, y, title, ha="left", va="center", color=S.ACCENT,
                fontsize=S.BODY, fontweight="bold")
        ax.text(XL, y - 5.0, sub, ha="left", va="center", color=S.MUTED,
                fontsize=S.SMALL, style="italic")

    def head(y, pairs):
        for x, t, al in pairs:
            ax.text(x, y, t, ha=al, va="center", color=S.MUTED,
                    fontsize=S.SMALL, fontweight="bold")

    # ── acting costs task success ────────────────────────────────────────
    band(96, "ACTING COSTS TASK SUCCESS", "for both cloud models, under routing")
    head(85, [(XA, "when it acted", "right"), (XI, "when it did not", "right")])
    for i, (name, d, strong) in enumerate((
            ("claude-sonnet-4-6", sonnet, True),
            ("claude-haiku-4-5", haiku, False))):
        y = 76 - i * 10
        ink = S.INK if strong else S.MUTED
        ax.text(XL, y, name, ha="left", va="center", fontsize=S.BODY,
                color=ink, style="italic")
        ax.add_patch(Rectangle((XR, y - 2.0), XW, 4.0, facecolor=S.SURFACE,
                               edgecolor=S.RULE, linewidth=0.7, zorder=1))
        ax.add_patch(Rectangle((XR, y - 2.0), XW * d["acted_win"], 4.0,
                               facecolor=S.ACCENT if strong else S.RULE,
                               edgecolor="none", zorder=2))
        ax.text(XA, y, f"{d['acted_win']:.3f}  ({d['acted_n']})", ha="right",
                va="center", fontsize=S.BODY, color=ink)
        ax.text(XI, y, f"{d['idle_win']:.3f}  ({d['idle_n']})", ha="right",
                va="center", fontsize=S.BODY, color=S.MUTED)
    ax.text(XL, 58, "The bar is task success on the runs that acted.",
            ha="left", va="center", color=S.MUTED, fontsize=S.SMALL,
            style="italic")

    ax.plot([XL, XI], [50, 50], color=S.RULE, linewidth=1.0)

    # ── and the stronger model acts more often ───────────────────────────
    band(43, "AND THE STRONGER MODEL ACTS MORE OFTEN",
         "how often each names an action, in the three categories where they differ")
    head(32, [(XM, "success when acted", "center"),
              (XA, "sonnet acts", "right"),
              (XI, "haiku acts", "right")])
    for i, cat in enumerate(SPLIT):
        y = 23 - i * 8
        s_cat, h_cat = sonnet["by_cat"][cat], haiku["by_cat"][cat]
        ax.text(XL, y, cat, ha="left", va="center", fontsize=S.BODY, color=S.INK)
        ax.text(XM, y, f"{s_cat['won_acted'] / s_cat['acted']:.3f}",
                ha="center", va="center", fontsize=S.BODY, color=S.MUTED)
        ax.text(XA, y, pct(s_cat["acted"] / s_cat["n"]), ha="right",
                va="center", fontsize=S.BODY, color=S.INK)
        ax.text(XI, y, pct(h_cat["acted"] / h_cat["n"]), ha="right",
                va="center", fontsize=S.BODY, color=S.MUTED)

    ax.text(XL, -2,
            f"Overall {sonnet['rate']:.0%} of {sonnet['n']} runs against "
            f"{haiku['rate']:.0%} of {haiku['n']}. On reasoning both act on "
            "75%,\nand on trivial and action both act on every run, so the "
            "whole of the difference is in these three.",
            ha="left", va="top", color=S.MUTED, fontsize=S.SMALL - 0.5,
            linespacing=1.5)

    S.save(fig, "fig29_acting_costs")


if __name__ == "__main__":
    build()
