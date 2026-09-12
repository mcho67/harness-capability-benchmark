"""Figure 9 -- the two scoring paths, and the fact that they never meet.

Section 3.7 has to answer one question: could a contestable ideal decision have
produced the headline? The answer is structural rather than rhetorical. Task
success and decision accuracy are computed by two separate functions, and the
one that scores task success never reads the ideal decision at all.

Written out, that is a paragraph a reader has to take on trust. Drawn as two
lanes that visibly do not touch, it is something a reader checks in a glance.

No result numbers beyond the counts of how each run was scored.
Grayscale-safe.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

import _style as S

OUT = Path(__file__).resolve().parents[1]

INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"

BOX_H = 13.0

HIDDEN = ("which design produced it   ·   which deployment   ·   which model   ·   "
          "what it cost   ·   how many model calls")


def node(ax, x, w, y, title, sub, accent=False):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, BOX_H, boxstyle="round,pad=0,rounding_size=1.1",
        facecolor="white" if accent else SURFACE,
        edgecolor=ACCENT if accent else RULE,
        linewidth=1.6 if accent else 1.0, zorder=2))
    ax.text(x + w / 2, y + BOX_H * 0.63, title, ha="center", va="center",
            color=INK, fontsize=S.BODY, fontweight="bold", zorder=3)
    ax.text(x + w / 2, y + BOX_H * 0.26, sub, ha="center", va="center",
            color=MUTED, fontsize=S.SMALL, zorder=3, linespacing=1.4)


def arrow(ax, x0, y, x1):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>",
                                 mutation_scale=12, color=INK, linewidth=1.4,
                                 zorder=4, shrinkA=0, shrinkB=0))


def build():
    fig, ax = plt.subplots(figsize=(6.38, 3.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(25.5, 93)
    ax.axis("off")

    # ── lane 1: the decision ────────────────────────────────────────────────
    y1 = 70
    ax.text(1, y1 + BOX_H + 7.5, "DECISION ACCURACY", ha="left", va="center",
            color=ACCENT, fontsize=S.BODY, fontweight="bold")
    ax.text(1, y1 + BOX_H + 2.6, "scores the choice, whatever came of it",
            ha="left", va="center", color=MUTED, fontsize=S.SMALL, style="italic")

    # Each box is set from the longest line it holds at body size. The
    # earlier widths left about a thirtieth of an inch either side of the
    # widest title, which reads as text pressed against a border.
    lane1 = [(2, 21, "task properties", "tagged when the\ntask was written"),
             (26, 20, "the rule table", "one ruleset,\nall 48 tasks"),
             (49, 20, "ideal decision", "ask · decline ·\nbackground · …"),
             (72, 26, "all five must match", "→ decision_correct")]
    for i, (x, w, t_, s) in enumerate(lane1):
        node(ax, x, w, y1, t_, s, accent=(i == len(lane1) - 1))
    for (x, w, *_), (nx, *_) in zip(lane1, lane1[1:]):
        arrow(ax, x + w, y1 + BOX_H / 2, nx)

    # ── the gap ─────────────────────────────────────────────────────────────
    # Centred between the two lanes. Sitting at 47 it left twice as much air
    # above it as below, and the figure looked like it had a hole in it.
    ax.add_patch(Rectangle((1, 57), 98, 7, facecolor=SURFACE,
                           edgecolor=RULE, linewidth=1.0, zorder=1))
    ax.text(50, 60.5, "THE TWO PATHS NEVER MEET", ha="center", va="center",
            color=ACCENT, fontsize=S.BODY, fontweight="bold", zorder=3)

    # ── lane 2: task success ────────────────────────────────────────────────
    y2 = 28
    ax.text(1, y2 + BOX_H + 7.5, "TASK SUCCESS", ha="left", va="center",
            color=ACCENT, fontsize=S.BODY, fontweight="bold")
    ax.text(1, y2 + BOX_H + 2.6, "scores what actually happened",
            ha="left", va="center", color=MUTED, fontsize=S.SMALL, style="italic")

    # Titles sized to their boxes: at 9pt the earlier wording ran past both
    # edges and the three boxes overlapped into one another.
    lane2 = [(2, 33, "the reply, and the effects",
              "on the simulated computer"),
             (38, 29, "the task's own standard",
              "a blind grader (660 runs)\nor a fixed check (300)"),
             (72, 26, "pass · partial · fail", "→ success")]
    for i, (x, w, t_, s) in enumerate(lane2):
        node(ax, x, w, y2, t_, s, accent=(i == len(lane2) - 1))
    for (x, w, *_), (nx, *_) in zip(lane2, lane2[1:]):
        arrow(ax, x + w, y2 + BOX_H / 2, nx)


    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    S.save(fig, "fig09_scoring_lanes")


if __name__ == "__main__":
    build()
