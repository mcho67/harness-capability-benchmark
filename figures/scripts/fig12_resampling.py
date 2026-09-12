"""Figure 12 -- how the interval is built.

Section 3.9 has to say what the interval around the headline means, and the
procedure is three steps that read badly in one sentence: a task is drawn with
all of its runs attached, the quantity is recomputed on the drawn set, and
that repeats five thousand times.

The left panel is the point of the whole scheme -- the unit that moves is the
task, not the run, because five repetitions of one task at temperature zero
are often the same reply five times over.

The middle panel is a real draw, taken with the seed the analysis used, so a
reader can see that some tasks arrive twice and some not at all. The right
panel is schematic: the shape of the recomputed values is a result and belongs
to §4.

Each panel is titled and then said in words underneath, because "2. ONE DRAW"
over a row of tick marks is a label a reader has to guess at. The counts under
the middle panel are computed from the draw drawn, not asserted.

Grayscale-safe.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, FancyArrowPatch

import _style as S

OUT = Path(__file__).resolve().parents[1]

INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"

SEED = 20260819
N_TASKS = 48

#: Every panel's drawing starts here, so the titles line up with the drawings
#: rather than with the invisible edge of their axes.
LX = 4


def head(ax, n, title):
    # The axes stops just under the lowest thing any panel draws. Run to 0 it
    # left a band of blank paper along the bottom of all three.
    ax.set_xlim(0, 100); ax.set_ylim(16, 101); ax.axis("off")
    ax.text(LX, 98, n, ha="left", va="center", color=ACCENT, fontsize=S.BODY,
            fontweight="bold")
    ax.text(LX, 91, title, ha="left", va="center", color=MUTED,
            fontsize=S.SMALL)


def panel_unit(ax):
    head(ax, "1.  THE UNIT", "one task, all its runs")
    ax.add_patch(Rectangle((LX, 34), 80, 42, facecolor=SURFACE,
                           edgecolor=ACCENT, linewidth=1.4, zorder=1))
    for r in range(4):
        for c in range(5):
            ax.add_patch(Rectangle((LX + 8 + c * 13.5, 63 - r * 8.0), 9.5, 5.6,
                                   facecolor="white", edgecolor=ACCENT,
                                   linewidth=0.9, zorder=3))


def panel_draw(ax):
    head(ax, "2.  ONE DRAW", "drawn with replacement")
    rng = np.random.default_rng(SEED)
    counts = np.bincount(rng.integers(0, N_TASKS, N_TASKS), minlength=N_TASKS)

    x0, w, gap = LX, 1.35, 0.55
    base, unit = 40, 10.5
    for i, c in enumerate(counts):
        x = x0 + i * (w + gap)
        if c == 0:
            ax.plot([x + w / 2], [base - 3.6], marker="x", markersize=3.2,
                    color=RULE, zorder=3)
            continue
        for k in range(c):
            ax.add_patch(Rectangle((x, base + k * unit), w, unit - 1.8,
                                   facecolor=ACCENT, edgecolor="none",
                                   zorder=3))
    ax.plot([x0 - 1, 95], [base - 1.2, base - 1.2], color=RULE, linewidth=1.0)

    # What the tick marks are for. Counted from the draw above, so the two
    # numbers cannot drift from the picture.
    n0 = int((counts == 0).sum()); nrep = int((counts > 1).sum())
    ax.text(LX, 29, f"{nrep} drawn twice or more", ha="left",
            va="center", color=MUTED, fontsize=S.SMALL)
    ax.text(LX, 22, f"{n0} not drawn  (×)", ha="left", va="center",
            color=MUTED, fontsize=S.SMALL)


def panel_interval(ax):
    head(ax, "3.  × 5,000", "one value per draw")
    lo_x, hi_x = LX + 2, 94
    span = hi_x - lo_x
    xs = np.linspace(-3.2, 3.2, 400)
    ys = np.exp(-xs ** 2 / 2)
    px = lo_x + (xs + 3.2) / 6.4 * span
    py = 40 + ys * 34
    lo, hi = -1.96, 1.96
    m = (xs >= lo) & (xs <= hi)
    ax.fill_between(px[m], 40, py[m], facecolor=SURFACE, edgecolor="none",
                    zorder=1)
    ax.plot(px, py, color=INK, linewidth=1.6, zorder=3)
    for v in (lo, hi):
        vx = lo_x + (v + 3.2) / 6.4 * span
        ax.plot([vx, vx], [40, 40 + np.exp(-v ** 2 / 2) * 34], color=ACCENT,
                linewidth=1.3, linestyle=(0, (3, 2)), zorder=4)
    ax.plot([lo_x, hi_x], [40, 40], color=RULE, linewidth=1.0)

    ax.annotate("", xy=(lo_x + (lo + 3.2) / 6.4 * span, 33),
                xytext=(lo_x + (hi + 3.2) / 6.4 * span, 33),
                arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=1.2))
    ax.text((lo_x + hi_x) / 2, 25, "the middle 95%", ha="center", va="center",
            color=ACCENT, fontsize=S.BODY, fontweight="bold")


def build():
    fig, axes = plt.subplots(1, 3, figsize=(S.WIDTH, 2.9))
    panel_unit(axes[0]); panel_draw(axes[1]); panel_interval(axes[2])

    for b in (1, 2):
        axes[b].add_patch(FancyArrowPatch(
            (-0.155, 0.50), (-0.055, 0.50), transform=axes[b].transAxes,
            arrowstyle="-|>", mutation_scale=14, color=INK, linewidth=1.5,
            clip_on=False))

    # The three panels use the whole column. Left at matplotlib's defaults
    # they occupied 4.9in of a 6.5in figure and were padded out with white.
    fig.subplots_adjust(left=0.012, right=0.988, top=0.98, bottom=0.02,
                        wspace=0.45)
    S.save(fig, "fig12_resampling")


if __name__ == "__main__":
    build()
