"""Figure 21 -- the mechanism: equal judgment, unequal success.

Decision accuracy scores the choice the harness made -- whether to ask,
whether to decline, and which actions to call -- without regard to whether
the task then succeeded. Task success scores what happened.

At cloud the two designs judge almost identically (0.721 against 0.717) and
succeed 0.179 apart. So the deciding design's advantage is not that it
chooses better at the outset. It is that it sees what an action returned and
can act again on what it saw.

Grayscale-safe: the two measures are told apart by fill, hollow against solid,
never by hue.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import _data as D

import _style as S

ORDER = ["C1", "C3", "C2", "C4"]


def build():
    rows = D.load()
    success = D.cell_means(D.by_task(rows))
    decision = D.cell_means(D.by_task(rows, field="decision_correct"))

    fig, ax = plt.subplots(figsize=(S.WIDTH, 4.4))
    ys = [3, 2, 1, 0]

    for y, c in zip(ys, ORDER):
        d, s = decision[c], success[c]
        ax.plot([d, s], [y, y], color=D.RULE, linewidth=2.6, zorder=1,
                solid_capstyle="round")
        ax.plot(d, y, marker="o", markersize=11, markerfacecolor="white",
                markeredgecolor=D.INK, markeredgewidth=1.7, zorder=3)
        ax.plot(s, y, marker="o", markersize=11, color=D.ACCENT, zorder=3)
        # The label goes on the outside of whichever point is on that side, so
        # two nearby points never write over each other.
        left, right = (d, s) if d < s else (s, d)
        for value, x, ha, off in ((left, left, "right", -14),
                                  (right, right, "left", 14)):
            ax.annotate(f"{value:.3f}", (x, y), textcoords="offset points",
                        xytext=(off, 0), ha=ha, va="center", fontsize=9,
                        color=D.ACCENT if value == s else D.MUTED,
                        fontweight="bold" if value == s else "normal")

    ax.set_yticks(ys)
    ax.set_yticklabels([f"{D.DESIGN[c]} × {D.DEPLOY[c]}" for c in ORDER],
                       fontsize=10)
    ax.tick_params(axis="y", length=0)

    # --- the comparison the figure exists to make ---------------------------
    ax.axhline(1.5, color=D.RULE, linewidth=0.9, linestyle=":")  # cloud above, on-device below

    ax.plot([], [], marker="o", markersize=10, markerfacecolor="white",
            markeredgecolor=D.INK, markeredgewidth=1.7, linestyle="none",
            label="decision accuracy — the choice made")
    ax.plot([], [], marker="o", markersize=10, color=D.ACCENT, linestyle="none",
            label="task success — what happened")
    ax.legend(loc="lower right", frameon=False, fontsize=9.5,
              handletextpad=0.4, borderpad=0.2)

    ax.set_xlim(0.26, 0.94)
    # The top row is at y=3; the axes used to run to 4.05 and carried most of
    # an inch of blank paper above the first pair of points.
    ax.set_ylim(-0.85, 3.26)
    ax.set_xlabel("proportion of runs")
    ax.tick_params(axis="x", labelsize=9)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(D.RULE)


    fig.tight_layout(pad=0.3)
    S.save(fig, "fig21_decision_vs_success")
    plt.close(fig)


if __name__ == "__main__":
    build()
