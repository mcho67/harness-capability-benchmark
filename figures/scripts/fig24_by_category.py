"""Figure 24 -- task success by category, in all four configurations.

The single number "the on-device model is weaker" hides a range from no loss
at all to total loss. Laid out with the two cloud configurations beside the
two on-device ones, the drop is read across a row rather than inferred from a
table.

Two rows carry the section's arguments: `trivial` is the control, where the
routing design scores 1.000 in both deployments and the deciding design does
not; `clarification` is the category the validity gate failed on, where both
designs sit at the floor on-device.

Every value is computed from `runs/full-2026-08-20/scored.jsonl`.
Grayscale-safe: the scale is a single ink ramp, and every value is printed.
"""

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import _data as D

import _style as S

OUT = Path(__file__).resolve().parents[1]

ORDER = ["trivial", "grounding", "robustness", "reasoning", "action",
         "clarification"]
COLS = ["C1", "C3", "C2", "C4"]          # cloud pair, then on-device pair


def build():
    rows = D.load()
    acc = defaultdict(list)
    for r in rows:
        acc[(r["category"], r["cell"])].append(float(r["success_strict"]))
    val = {k: mean(v) for k, v in acc.items()}
    n = len(acc[(ORDER[0], "C1")])

    top = len(ORDER)

    # The axes fills the figure and the limits are set from the drawing, so
    # the grid uses the whole column instead of sitting inside matplotlib's
    # default tick margins with half an inch of white to its right.
    fig, ax = plt.subplots(figsize=(S.WIDTH, 5.0))
    fig.subplots_adjust(left=0.006, right=0.994, top=0.99, bottom=0.01)
    ax.set_xlim(-1.11, 4.35); ax.set_ylim(-0.30, top + 1.25)
    ax.axis("off")

    # The deployment is named once over each pair, not again under every
    # column and a third time along the bottom. Three copies of "cloud" is
    # what pushed the drawing up the page and left a band of nothing beneath
    # it.
    for x, name in ((0.97, "cloud"), (3.27, "on-device")):
        ax.text(x, top + 1.05, name, ha="center", va="center", color=D.ACCENT,
                fontsize=9.4, fontweight="bold")

    for j, c in enumerate(COLS):
        x = j + (0.36 if j >= 2 else 0)
        ax.text(x + 0.47, top + 0.35, D.DESIGN[c], ha="center",
                va="center", color=D.INK, fontsize=S.BODY, fontweight="bold")

    for i, cat in enumerate(ORDER):
        y = len(ORDER) - 1 - i
        label = cat + ("  (control)" if cat == "trivial" else "")
        ax.text(-0.14, y + 0.45, label, ha="right", va="center", color=D.INK,
                fontsize=9)
        for j, c in enumerate(COLS):
            x = j + (0.36 if j >= 2 else 0)
            v = val[(cat, c)]
            ax.add_patch(Rectangle((x, y), 0.94, 0.9,
                                   facecolor=D.ACCENT, alpha=0.10 + 0.85 * v,
                                   edgecolor="white", linewidth=1.4, zorder=2))
            ax.text(x + 0.47, y + 0.45, f"{v:.3f}", ha="center", va="center",
                    fontsize=S.BODY, fontweight="bold", zorder=3,
                    color="white" if v > 0.55 else D.INK)

    ax.plot([2.18, 2.18], [-0.10, top + 0.62], color=D.RULE, linewidth=1.2)


    S.save(fig, "fig24_by_category")


if __name__ == "__main__":
    build()
