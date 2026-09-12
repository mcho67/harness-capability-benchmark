"""Figure 4 -- what varied against what was held constant.

The objection this figure exists to answer is the obvious one: surely the two
designs differ in more than the loop. Everything in the lower band is shared
by all four configurations, from one file both designs import. Only the two
switches at the top were moved.

No result numbers: this describes how the study was built.
Grayscale-safe.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

import _style as S

OUT = Path(__file__).resolve().parents[1]

INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"

HELD = [
    ("the 48 tasks", "and the order they were put in"),
    ("the 21 actions", "and the code that runs them"),
    ("the instructions", "word for word, to the model"),
    ("the sandbox", "the simulated computer acted on"),
    ("temperature 0", "no randomness in word choice"),
    ("the machine", "its load and its power state"),
    ("the scoring", "including a grader blind to configuration"),
]


def build():
    fig, ax = plt.subplots(figsize=(S.WIDTH, 4.3))
    ax.set_xlim(0, 100)
    ax.set_ylim(12, 100)
    ax.axis("off")

    # ── what varied ─────────────────────────────────────────────────────────
    ax.text(50, 97, "TWO SWITCHES WERE MOVED", ha="center", va="center",
            color=ACCENT, fontsize=S.BODY, fontweight="bold")
    for x, title, a, b in ((5, "harness design", "routing", "deciding"),
                           (52, "deployment", "cloud", "on-device")):
        ax.add_patch(FancyBboxPatch(
            (x, 74), 43, 16, boxstyle="round,pad=0,rounding_size=1.2",
            facecolor="white", edgecolor=ACCENT, linewidth=1.7, zorder=2))
        ax.text(x + 21.5, 85.5, title, ha="center", va="center", color=INK,
                fontsize=10.2, fontweight="bold", zorder=3)
        ax.text(x + 21.5, 78.5, f"{a}   /   {b}", ha="center", va="center",
                color=ACCENT, fontsize=9.2, zorder=3)

    ax.text(50, 68.5, "crossed, giving four configurations of 240 runs each",
            ha="center", va="center", color=MUTED, fontsize=S.BODY)

    # ── what was held ───────────────────────────────────────────────────────
    ax.add_patch(Rectangle((3, 14), 94, 48, facecolor=SURFACE,
                           edgecolor=RULE, linewidth=1.0, zorder=1))
    ax.text(50, 57, "EVERYTHING ELSE WAS HELD IDENTICAL", ha="center",
            va="center", color=MUTED, fontsize=S.BODY, fontweight="bold")

    for i, (name, sub) in enumerate(HELD):
        col, row = i % 2, i // 2
        x = 9 + col * 46
        y = 48 - row * 9.6
        ax.plot([x - 2.6], [y], marker="s", markersize=4.2, color=ACCENT,
                zorder=3)
        ax.text(x, y + 1.4, name, ha="left", va="center", color=INK,
                fontsize=S.BODY, fontweight="bold", zorder=3)
        ax.text(x, y - 2.6, sub, ha="left", va="center", color=MUTED,
                fontsize=S.SMALL, zorder=3)


    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    S.save(fig, "fig04_held_constant")


if __name__ == "__main__":
    build()
