"""Figure 11 -- the run, as a ledger.

Section 3.8 claims no run was discarded. This is that claim in a form a reader
can check rather than accept: every row the study produced, in the order it was
produced.

The window comes from the rows themselves. All 960 carry a `started_at`, and
they run unbroken from 15:41:58 to 17:43:53 on August 20 -- the longest pause
anywhere is 2.3 minutes. The driver prints a resume count when it starts each
configuration; that count is not evidence of an interruption, and the
timestamps rule one out.

Carries no outcome number and no per-configuration timing — those belong to the
third measure and are reported in §4.8. What appears here is the shape of the
run and its totals.

Grayscale-safe: configurations are told apart by fill and label, the session
boundary by a rule.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

import _style as S

OUT = Path(__file__).resolve().parents[1]

INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"

# execution order, from the run log
SEGMENTS = [
    ("C2", "deciding × on-device", 0, 240),
    ("C4", "routing × on-device", 240, 480),
    ("C1", "deciding × cloud", 480, 720),
    ("C3", "routing × cloud", 720, 960),
]
RESUME = 112

TALLY = [
    ("960", "rows planned"),
    ("960", "rows produced"),
    ("0", "runs that failed"),
    ("0", "runs dropped"),
    ("0", "runs the grader\ncould not score"),
]

TRACK_Y, TRACK_H = 44, 15
X0, XW = 3, 94


def x(n):
    return X0 + XW * n / 960.0


def build():
    fig, ax = plt.subplots(figsize=(S.WIDTH, 2.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(6, 72)
    ax.axis("off")

    ax.text(X0, 68, "August 20, 2026", ha="left", va="center", color=ACCENT,
            fontsize=10.5, fontweight="bold")
    ax.text(X0, 62.5, "15:41:58 to 17:43:53 — 960 runs, unbroken, in the order below",
            ha="left", va="center", color=MUTED, fontsize=S.BODY)

    for i, (cid, label, lo, hi) in enumerate(SEGMENTS):
        ax.add_patch(Rectangle((x(lo), TRACK_Y), x(hi) - x(lo), TRACK_H,
                               facecolor=SURFACE if i % 2 else "white",
                               edgecolor=ACCENT, linewidth=1.2, zorder=2))
        mid = (x(lo) + x(hi)) / 2
        ax.text(mid, TRACK_Y + TRACK_H * 0.62, cid, ha="center", va="center",
                color=INK, fontsize=10, fontweight="bold", zorder=3)
        ax.text(mid, TRACK_Y + TRACK_H * 0.26, label, ha="center", va="center",
                color=MUTED, fontsize=S.SMALL, zorder=3)
        ax.text(x(hi), TRACK_Y - 3.4, f"{hi}", ha="center", va="top",
                color=MUTED, fontsize=S.SMALL)
    ax.text(x(0), TRACK_Y - 3.4, "0", ha="center", va="top", color=MUTED,
            fontsize=S.SMALL)
    ax.text(X0, TRACK_Y - 9.5, "rows written, cumulative", ha="left", va="top",
            color=MUTED, fontsize=S.SMALL, style="italic")

    # the tally
    ax.plot([X0, X0 + XW], [30, 30], color=RULE, linewidth=0.9)
    for i, (big, small) in enumerate(TALLY):
        cx = X0 + 5 + i * (XW / 5.0)
        ax.text(cx, 22, big, ha="center", va="center", color=ACCENT,
                fontsize=15, fontweight="bold")
        ax.text(cx, 16.5, small, ha="center", va="top", color=MUTED,
                fontsize=S.SMALL, linespacing=1.5)


    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    S.save(fig, "fig11_run_ledger")


if __name__ == "__main__":
    build()
