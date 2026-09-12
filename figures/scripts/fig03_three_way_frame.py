"""Figure 3 -- the three shapes the answer could have taken, and the one it did.

The study's question is not whether either design is better. It is whether the
distance between them changes when the model gets weaker. That question has
exactly three answers, and a reader who cannot picture all three cannot tell
how much the observed one rules out.

The first two panels are drawn to illustrate a shape, not to report data. The
third carries the measured numbers, and is marked as the observed result.

Grayscale-safe: the designs are told apart by line style, the observed panel by
a heavier frame.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

import _data as D

import _style as S

OUT = Path(__file__).resolve().parents[1]

PANELS = [
    ("Compensation", "the design matters MORE\non-device: gap widens",
     (0.86, 0.62), (0.69, 0.30), False),
    ("No interaction", "the design is worth the same\nwherever it runs: gap holds",
     (0.86, 0.56), (0.69, 0.39), False),
    ("Negative compensation", "the design matters LESS\non-device: gap narrows",
     None, None, True),
]


def gap_marker(ax, x, lo, hi, label, side):
    ax.add_patch(FancyArrowPatch((x, lo), (x, hi), arrowstyle="<->",
                                 mutation_scale=8, color=D.ACCENT,
                                 linewidth=1.2, shrinkA=0, shrinkB=0))
    ax.text(x + (0.05 if side > 0 else -0.05), (lo + hi) / 2, label,
            ha="left" if side > 0 else "right", va="center", fontsize=S.BODY,
            fontweight="bold", color=D.ACCENT)


def build():
    m = D.cell_means(D.by_task(D.load()))
    observed = ((m["C1"], m["C2"]), (m["C3"], m["C4"]))

    fig, axes = plt.subplots(1, 3, figsize=(S.WIDTH, 3.5))

    for ax, (title, sub, dec, rou, is_obs) in zip(axes, PANELS):
        if is_obs:
            dec, rou = observed
        ax.plot([0, 1], dec, color=D.INK, linewidth=2.2, marker="o",
                markersize=6, zorder=3)
        ax.plot([0, 1], rou, color=D.INK, linewidth=2.2, marker="s",
                markersize=5.5, linestyle="--", zorder=3)

        g0, g1 = dec[0] - rou[0], dec[1] - rou[1]
        gap_marker(ax, -0.20, rou[0], dec[0],
                   f"{g0:.3f}" if is_obs else "gap", -1)
        gap_marker(ax, 1.20, rou[1], dec[1],
                   f"{g1:.3f}" if is_obs else "gap", +1)

        # Room on both sides for a gap label: the observed panel prints
        # "0.179" where the other two print "gap", and at -0.85 the wider
        # word ran out through the panel's own frame.
        ax.set_xlim(-1.15, 2.15)
        ax.set_ylim(0.18, 1.0)
        ax.set_xticks([0, 1])
        # Two tick labels cannot fit under a panel this narrow without
        # touching. The axis runs one way and one label says so.
        ax.set_xticklabels([])
        ax.set_xlabel("cloud  →  on-device")
        ax.set_yticks([])
        ax.tick_params(axis="x", length=0, pad=4)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(D.RULE)

        ax.text(0.5, -0.20, sub, transform=ax.transAxes, ha="center",
                va="top", fontsize=S.BODY, color=D.MUTED, linespacing=1.5)

        if is_obs:
            for s in ax.spines.values():
                s.set_visible(True); s.set_color(D.ACCENT); s.set_linewidth(1.6)
            ax.set_facecolor("#FBFAF8")
            ax.text(0.5, 0.955, "what happened", transform=ax.transAxes,
                    ha="center", va="top", fontsize=S.BODY, fontweight="bold",
                    color=D.ACCENT)

    axes[0].text(-0.40, 0.955, "task\nsuccess", transform=axes[0].transAxes,
                 ha="left", va="top", fontsize=S.BODY, color=D.MUTED,
                 linespacing=1.5)
    axes[0].plot([], [], color=D.INK, lw=2.2, marker="o", ms=6,
                 label="deciding design")
    axes[0].plot([], [], color=D.INK, lw=2.2, marker="s", ms=5.5, ls="--",
                 label="routing design")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center",
               ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.34))


    # Fill the column: at matplotlib's default margins the three panels
    # covered 5.7in of a 6.5in figure and were padded out with white.
    fig.subplots_adjust(left=0.10, right=0.975, wspace=0.34)
    S.save(fig, "fig03_three_way_frame")


if __name__ == "__main__":
    build()
