"""Figure 5 -- what each pairing of configurations isolates.

A 2x2 is only worth running if each comparison inside it answers a clean
question. Drawn against the same grid the reader already met in Figure 2, the
four comparisons make one point: every pairing moves exactly one switch, so a
difference between the two configurations in a pair has exactly one candidate
explanation.

The two vertical pairings are the ones the paper's question turns on. Their
difference is the compensation contrast.

No result numbers: this describes how the study reads, not what it found.
Grayscale-safe: the compared pair is filled, the others left empty.
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

# grid position of each configuration, matching Figure 2 exactly
POS = {"C1": (0, 1), "C2": (1, 1), "C3": (0, 0), "C4": (1, 0)}

# The second string names the level held fixed, in the paper's own words for
# it, so the four sub-labels are parallel: a deployment name under a design
# comparison, a design name under a deployment comparison.
PANELS = [
    ("C1", "C3", "the design", "cloud deployment", True),
    ("C2", "C4", "the design", "on-device deployment", True),
    ("C1", "C2", "deployment", "the deciding design", False),
    ("C3", "C4", "deployment", "the routing design", False),
]

CW, CH = 28, 22
X0, Y0 = 15, 24
GAPX, GAPY = 21, 23


def cell_xy(col, row):
    return X0 + col * (CW + GAPX), Y0 + row * (CH + GAPY)


def build():
    # Two by two, not one by four. Four panels across the house width leave
    # 1.6in each, which is narrower than the labels beneath them; in that
    # layout every panel's caption ran into its neighbour's. Stacked in pairs
    # each panel gets 3.25in and the four read as two comparisons of two.
    fig, axes = plt.subplots(2, 2, figsize=(S.WIDTH, 5.3))
    axes = axes.ravel()
    # Fill the column. At matplotlib's default margins the four grids
    # covered 4.7in of a 6.5in figure, so this figure alone read a size
    # smaller than every other one in the paper. The small left margin is
    # for the rotated axis hints, which sit outside the axes.
    fig.subplots_adjust(left=0.03, right=0.99, top=0.98, bottom=0.02,
                        hspace=0.18, wspace=0.10)

    for ax, (a, b, what, where, primary) in zip(axes, PANELS):
        ax.set_xlim(0, 100)
        ax.set_ylim(-5, 100)
        ax.axis("off")

        for cid, (col, row) in POS.items():
            x, y = cell_xy(col, row)
            on = cid in (a, b)
            ax.add_patch(FancyBboxPatch(
                (x, y), CW, CH, boxstyle="round,pad=0,rounding_size=2.5",
                facecolor=ACCENT if on else "white",
                edgecolor=ACCENT if on else RULE,
                linewidth=1.5 if on else 1.0, zorder=2))
            ax.text(x + CW / 2, y + CH / 2, cid, ha="center", va="center",
                    color="white" if on else RULE, fontsize=11.5,
                    fontweight="bold", zorder=3)

        # the arrow joining the pair
        (ca, ra), (cb, rb) = POS[a], POS[b]
        xa, ya = cell_xy(ca, ra)
        xb, yb = cell_xy(cb, rb)
        if ca == cb:                                   # vertical pairing
            ax.add_patch(FancyArrowPatch(
                (xa + CW / 2, ya), (xb + CW / 2, yb + CH), arrowstyle="<->",
                mutation_scale=11, color=INK, linewidth=1.6, zorder=4,
                shrinkA=1, shrinkB=1))
        else:                                          # horizontal pairing
            ax.add_patch(FancyArrowPatch(
                (xa + CW, ya + CH / 2), (xb, yb + CH / 2), arrowstyle="<->",
                mutation_scale=11, color=INK, linewidth=1.6, zorder=4,
                shrinkA=1, shrinkB=1))

        # axis hints, small, so the grid is readable without Figure 2 to hand
        ax.text(X0 - 3, Y0 + CH + GAPY + CH / 2, "deciding", ha="right",
                va="center", color=MUTED, fontsize=S.SMALL, rotation=90)
        ax.text(X0 - 3, Y0 + CH / 2, "routing", ha="right", va="center",
                color=MUTED, fontsize=S.SMALL, rotation=90)
        ax.text(X0 + CW / 2, Y0 - 4, "cloud", ha="center", va="top",
                color=MUTED, fontsize=S.SMALL)
        ax.text(X0 + CW + GAPX + CW / 2, Y0 - 4, "on-device", ha="center",
                va="top", color=MUTED, fontsize=S.SMALL)

        ax.text(50, 96, f"{a}  vs  {b}", ha="center", va="center", color=INK,
                fontsize=10.2, fontweight="bold")
        ax.text(50, 9, what, ha="center", va="center",
                color=ACCENT, fontsize=S.BODY, fontweight="bold")
        ax.text(50, 1, where, ha="center", va="center", color=MUTED,
                fontsize=S.BODY)


    S.save(fig, "fig05_contrasts")


if __name__ == "__main__":
    build()
