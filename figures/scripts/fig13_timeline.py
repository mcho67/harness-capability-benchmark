"""Figure 13 -- what was fixed, and when.

The paper's rigor claim is a claim about order: the hypotheses, the thresholds
and the analysis were settled before any of the data existed. Order is the
thing prose is worst at and a timeline is best at.

The figure also carries the item that fell on the wrong side of the run,
because a timeline showing only the tidy parts would be an argument rather
than a record.

Dates come from the repository, not from the protocol's prose: the
paper-baseline tag carries 2026-08-20 15:36:45 and the first full-run commit
2026-08-20 18:01:41. Where the two disagree the timestamps win, and the
disagreement is recorded in Appendix D.

Grayscale-safe: the post-run item is marked by an open marker and a label.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import _style as S

OUT = Path(__file__).resolve().parents[1]

INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"

# The x of the first and last event sets how wide the drawing ends up, since
# each carries a two-line note centred on it. Spread to 5..98 those notes ran
# past both edges of the image.
EVENTS = [
    (5,  "Jun 18", "protocol written",
     "hypotheses, thresholds,\nanalysis, no direction", True, False),
    (37, "Aug 19", "pilot; gate fails",
     "twelve amendments,\nall before any data", False, False),
    (53, "Aug 20", "frozen",
     "instrument tagged 15:36,\ntask set fingerprinted", True, False),
    # The run's own window, not the commit that recorded it. "from 18:01" is
    # when the rows were committed, and on a figure about order it read as
    # the time the run started -- which Figure 11 gives as 15:41:58.
    (69, "Aug 20", "the run", "960 rows,\n15:42 to 17:44", False, False),
    (80, "Aug 21", "deviations recorded", "", True, False),
    (89, "Aug 25", "second rater",
     "blind to results,\nbut after the run", False, True),
]

#: Where the run begins. Everything left of it was fixed with no data in hand.
DIVIDER = 61


def build():
    # The axes stops where the drawing stops. It used to run from -26 to 100
    # with nothing below y=12, which left an inch of blank paper under the
    # figure and made everything above it smaller to fit.
    fig, ax = plt.subplots(figsize=(6.42, 3.5))
    ax.set_xlim(-9, 103)
    ax.set_ylim(9, 100)
    ax.axis("off")

    # "Before" is a region of the figure rather than a strip beside the line.
    # Shaded full height it needs no explaining, and the two band labels move
    # up out of the row the leaders run through: set at y=43.5 the longer of
    # them crossed the leader dropping from the Aug 19 marker.
    ax.add_patch(Rectangle((-7, 9), DIVIDER + 7, 82, facecolor=SURFACE,
                           edgecolor="none", zorder=0))
    ax.plot([DIVIDER, DIVIDER], [26, 74], color=ACCENT, linewidth=1.3,
            linestyle=(0, (3, 2)), zorder=3)
    ax.text(DIVIDER - 2, 94.5, "BEFORE ANY DATA EXISTED", ha="right",
            va="center", color=MUTED, fontsize=S.SMALL, fontweight="bold",
            zorder=4)
    ax.text(DIVIDER + 2, 94.5, "AFTER", ha="left", va="center", color=MUTED,
            fontsize=S.SMALL, fontweight="bold", zorder=4)

    ax.plot([-7, 101], [50, 50], color=RULE, linewidth=1.4, zorder=2)

    ax.plot([8, 34], [50, 50], color=RULE, linewidth=6.0, zorder=1,
            solid_capstyle="butt")
    ax.text(21, 56.0, "62 days", ha="center", va="center", color=MUTED,
            fontsize=S.SMALL, fontweight="bold")

    for x, date, what, detail, above, after in EVENTS:
        ax.plot(x, 50, marker="o", markersize=10, zorder=5,
                markerfacecolor="white" if after else ACCENT,
                markeredgecolor=ACCENT, markeredgewidth=1.8)
        sign = 1 if above else -1
        ax.plot([x, x], [50 + sign * 4.5, 50 + sign * 11], color=RULE,
                linewidth=1.0, zorder=3)
        y = 50 + sign * 13
        va = "bottom" if above else "top"
        ax.text(x, y, date, ha="center", va=va, color=ACCENT, fontsize=S.SMALL,
                fontweight="bold")
        ax.text(x, y + sign * 6.5, what, ha="center", va=va, color=INK,
                fontsize=S.BODY, fontweight="bold")
        if detail:
            ax.text(x, y + sign * 13.0, detail, ha="center", va=va,
                    color=MUTED, fontsize=S.SMALL, linespacing=1.5)


    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.tight_layout(pad=0.05)
    S.save(fig, "fig13_timeline")


if __name__ == "__main__":
    build()
