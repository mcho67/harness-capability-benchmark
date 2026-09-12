"""Figure 8 -- the ruleset that turns a task's properties into its ideal decision.

The author tags the left column: facts about the request, written down when
the task was written and before any run. The right column is derived, never
written by hand. This is the whole answer to "who decided what the right
decision was", and it is one file a reader can open.

Two details are drawn rather than left in prose because they are exactly the
places a hand could otherwise reach in: declining takes precedence over asking
when a task carries both kinds of property, and two of the five decisions earn
credit without being required, so disagreement about them cannot change
whether a decision counts as correct.

Mirrors `apparatus/tasks/derive_ideal.py` (PROPERTIES, CREDIT, derive_ideal).
No result numbers. Grayscale-safe.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

import _style as S

OUT = Path(__file__).resolve().parents[1]

INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"

# (label, y, decision key). Three groups, one per kind of property; the gap
# between groups is wider than the gap inside one, so the grouping is visible
# before any label is read.
PROPS = [
    ("leaves out something required",     85, "ask"),
    ("contradicts itself",                74, "ask"),
    ("asks for something it cannot do",   60, "decline"),
    ("asks for something it must refuse", 49, "decline"),
    ("will take a long time to finish",   35, "background"),
    ("has several steps",                 24, "decompose"),
    ("is complete as it stands",          10, "execute"),
]

# key: (label, y, credit)
DECS = {
    "ask":        ("ask before acting",               79.5, "required"),
    "decline":    ("decline, and say why",            54.5, "required"),
    "background": ("start it, reply without waiting",   35, "earns credit"),
    "decompose":  ("break it into steps",               24, "earns credit"),
    "execute":    ("do it, with the right action",      10, "required"),
}

# Each column is set from the longest label it has to hold at body size:
# 2.20in on the left, 1.89in on the right. The earlier 40-unit left column
# was narrower than its own longest label, so that label ran out across the
# arrow leaving its box. H buys two lines of type in the right column with
# air above and below them.
LX, LW = 1, 39
RX, RW = 56, 42
H = 9.5


def box(ax, x, y, w, text, sub=None, strong=False):
    ax.add_patch(FancyBboxPatch(
        (x, y - H / 2), w, H, boxstyle="round,pad=0,rounding_size=1.0",
        facecolor=SURFACE if not strong else "white",
        edgecolor=RULE if not strong else ACCENT,
        linewidth=1.0 if not strong else 1.5, zorder=2))
    ax.text(x + 2.4, y + (1.3 if sub else 0), text, ha="left", va="center",
            color=INK, fontsize=S.BODY, zorder=3)
    if sub:
        ax.text(x + 2.4, y - 2.3, sub, ha="left", va="center",
                color=ACCENT if sub == "required" else MUTED, fontsize=S.SMALL,
                fontweight="bold", zorder=3)


def build():
    # The axes stop where the drawing stops. The earlier limits ran to -4
    # with nothing below y=16, so a fifth of the image was blank.
    fig, ax = plt.subplots(figsize=(S.WIDTH, 4.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(3, 101)
    ax.axis("off")

    ax.text(LX, 98, "TAGGED WHEN THE TASK WAS WRITTEN", ha="left",
            va="center", color=MUTED, fontsize=S.SMALL, fontweight="bold")
    ax.text(LX, 93.5, "facts about the request, fixed before any run",
            ha="left", va="center", color=MUTED, fontsize=S.SMALL, style="italic")
    ax.text(RX, 98, "DERIVED BY RULE", ha="left", va="center", color=ACCENT,
            fontsize=S.SMALL, fontweight="bold")
    ax.text(RX, 93.5, "never written by hand, for any task",
            ha="left", va="center", color=MUTED, fontsize=S.SMALL, style="italic")

    for label, y, key in PROPS:
        box(ax, LX, y, LW, label)
        ty = DECS[key][1]
        ax.add_patch(FancyArrowPatch(
            (LX + LW, y), (RX, ty), arrowstyle="-|>", mutation_scale=10,
            color=MUTED, linewidth=1.1, zorder=1, shrinkA=1, shrinkB=1,
            connectionstyle="arc3,rad=0.0"))

    for label, y, credit in DECS.values():
        box(ax, RX, y, RW, label, sub=credit, strong=True)

    # Declining supersedes asking. Drawn inside the right column, in the gap
    # its two boxes already leave, rather than in a margin outside them: the
    # margin version had to set its label three words to a line and still ran
    # into the edge of the image.
    ax.add_patch(FancyArrowPatch(
        (RX + 3.5, 79.5 - H / 2 - 0.8), (RX + 3.5, 54.5 + H / 2 + 0.8),
        arrowstyle="-|>", mutation_scale=10, color=ACCENT, linewidth=1.3,
        zorder=4))
    ax.text(RX + 7, 67, "if a task is both,\ndeclining wins", ha="left",
            va="center", color=ACCENT, fontsize=S.SMALL, linespacing=1.6)


    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    S.save(fig, "fig08_rule_table")


if __name__ == "__main__":
    build()
