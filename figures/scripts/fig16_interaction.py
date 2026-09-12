"""Figure 16 -- the interaction, drawn as an estimation plot.

The layout follows Gardner and Altman, as revived by Ho et al. (2019): the
data on the left, and the effect size on its own axis to the right, with
**zero on that axis aligned to the reference value in the data panel**. The
alignment is the whole point of the design. The effect is read off the same
eye-line as the observation that produced it, so a reader is never asked to
carry a number between two unrelated coordinate systems.

Applied to an interaction the reference is exact rather than arbitrary. If
the deciding design's advantage were the same on-device as in the cloud, its
on-device point would sit at

    routing on-device + cloud gap  =  0.388 + 0.179  =  0.567

so that height is "no compensation", and the contrast is the signed distance
from it to the observed 0.521. Zero on the right-hand axis is drawn at that
height and the estimate lands on the observed point, because those are the
same statement twice.

An earlier version put the contrast in a strip beneath the lines. It failed
for exactly the reason this design exists: two coordinate systems, and the
strip's zero rule cut through its own label.

The bootstrap distribution is drawn behind the interval, so the interval is
visibly a summary of something rather than a bare bracket.

Grayscale-safe: the designs are told apart by line style and marker, never by
hue. The accent colour is spent only on the contrast the figure is about.

The caption lives in the document, not here (`_style`).
"""

import matplotlib.pyplot as plt
import numpy as np

import _data as D
import _style as S

STYLE = {
    "deciding": dict(linestyle="-", marker="o", markersize=6.5, linewidth=1.9),
    "routing": dict(linestyle="--", marker="s", markersize=6, linewidth=1.9),
}


def contrast_draws(per_task, resamples=D.RESAMPLES, seed=D.SEED):
    """The 5,000 resampled contrasts the interval summarises."""
    tasks = list(per_task)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(resamples):
        drawn = list(rng.choice(tasks, size=len(tasks), replace=True))
        mm = D.cell_means(per_task, drawn)
        out.append((mm["C2"] - mm["C4"]) - (mm["C1"] - mm["C3"]))
    return np.array(out)


def build():
    per_task = D.by_task(D.load())
    m = D.cell_means(per_task)
    ci = {c: D.bootstrap(per_task, lambda mm, c=c: mm[c]) for c in D.CELLS}

    gap_cloud = m["C1"] - m["C3"]
    gap_device = m["C2"] - m["C4"]
    inter, lo, hi = D.bootstrap(
        per_task, lambda mm: (mm["C2"] - mm["C4"]) - (mm["C1"] - mm["C3"]))
    draws = contrast_draws(per_task)

    ref = m["C4"] + gap_cloud          # the height at which the contrast is 0

    fig, (ax, bx) = plt.subplots(
        1, 2, figsize=(S.WIDTH, 4.6),
        gridspec_kw={"width_ratios": [3.0, 1], "wspace": 0.13})

    # ── left: the data ───────────────────────────────────────────────────
    x = [0, 1]
    for design, cells in (("deciding", ("C1", "C2")), ("routing", ("C3", "C4"))):
        y = [m[c] for c in cells]
        err = [[y[i] - ci[c][1] for i, c in enumerate(cells)],
               [ci[c][2] - y[i] for i, c in enumerate(cells)]]
        ax.errorbar(x, y, yerr=err, color=S.INK, ecolor=S.RULE,
                    elinewidth=1.2, capsize=3.5, capthick=1.2, zorder=3,
                    **STYLE[design])
        ax.annotate(design, (0, y[0]), textcoords="offset points",
                    xytext=(-13, 0), ha="right", va="center",
                    fontsize=S.BODY, color=S.INK)

    # where the deciding point would have landed with its cloud gap intact
    ax.plot([0, 1], [m["C1"], ref], linestyle=(0, (2, 2)), color=S.ACCENT,
            linewidth=1.2, zorder=2)
    ax.plot([1], [ref], marker="o", markersize=6.5, markerfacecolor="white",
            markeredgecolor=S.ACCENT, markeredgewidth=1.6, zorder=4)
    # Right of the marker and above it: the dotted line arrives from the
    # upper left and ends here, so this is the only clear quadrant.
    ax.annotate("if the cloud" + chr(10) + "gap held", (1, ref),
                textcoords="offset points", xytext=(11, 6), ha="left",
                va="bottom", fontsize=S.BODY, color=S.ACCENT, linespacing=1.35)

    for xi, gap, side in ((-0.15, gap_cloud, -1), (1.24, gap_device, 1)):
        top, bot = (("C1", "C3") if side < 0 else ("C2", "C4"))
        ax.annotate("", xy=(xi, m[top]), xytext=(xi, m[bot]),
                    arrowprops=dict(arrowstyle="<->", color=S.INK, lw=1.2))
        ax.text(xi + 0.055 * side, (m[top] + m[bot]) / 2, S.signs(f"{gap:+.3f}"),
                ha="left" if side > 0 else "right", va="center",
                fontsize=S.EMPH, color=S.INK)

    ax.set_xlim(-0.66, 1.70)
    ax.set_ylim(0.22, 1.00)
    ax.set_xticks(x)
    ax.set_xticklabels(["cloud\nclaude-sonnet-4-6", "on-device\nllama3.1:8b"])
    ax.set_ylabel("task success")
    S.frame(ax)

    # ── right: the contrast, on an axis whose zero is `ref` ──────────────
    counts, edges = np.histogram(draws, bins=44, density=True)
    centres = (edges[:-1] + edges[1:]) / 2
    grid = np.linspace(draws.min(), draws.max(), 240)
    w = np.interp(grid, centres, counts)
    w = 0.34 * w / w.max()
    bx.fill_betweenx(ref + grid, 0.5, 0.5 + w, color=S.ACCENT, alpha=0.15,
                     linewidth=0, zorder=1)

    bx.axhline(ref, color=S.ACCENT, linewidth=1.0, linestyle=(0, (2, 2)),
               zorder=0)
    bx.plot([0.5, 0.5], [ref + lo, ref + hi], color=S.ACCENT, linewidth=2.4,
            zorder=3)
    for end in (lo, hi):
        bx.plot([0.435, 0.565], [ref + end] * 2, color=S.ACCENT,
                linewidth=2.0, zorder=3)
    bx.plot([0.5], [ref + inter], "o", color=S.ACCENT, markersize=7,
            markeredgecolor="white", markeredgewidth=1.0, zorder=4)
    # Stacked above and below the interval, not beside it: a horizontal
    # label is wider than this panel and spills into the data panel.
    bx.annotate(S.signs(f"{inter:+.3f}"), (0.5, ref + hi), textcoords="offset points",
                xytext=(0, 11), ha="center", va="bottom", fontsize=S.EMPH,
                color=S.ACCENT)
    bx.annotate(S.signs(f"[{lo:+.3f}, {hi:+.3f}]"), (0.5, ref + lo),
                textcoords="offset points", xytext=(0, -10), ha="center",
                va="top", fontsize=S.BODY, color=S.MUTED)
    # The shaded shape is unexplained decoration until it is named. It is the
    # 5,000 resampled contrasts the interval is the middle 95% of.
    bx.annotate("5,000 resamples", (0.5, ref + lo), textcoords="offset points",
                xytext=(0, -25), ha="center", va="top", fontsize=S.SMALL,
                color=S.MUTED)

    ticks = [-0.2, -0.1, 0.0, 0.1]
    bx.set_yticks([ref + t for t in ticks])
    bx.set_yticklabels(["0" if t == 0 else f"{t:+.1f}" for t in ticks])
    bx.yaxis.tick_right()
    bx.yaxis.set_label_position("right")
    bx.set_ylabel("compensation contrast", color=S.ACCENT, labelpad=8)
    bx.tick_params(axis="y", colors=S.ACCENT, right=True, labelright=True,
                   left=False, labelleft=False)
    bx.set_ylim(0.22, 1.00)          # matched to the data panel by hand;
    bx.set_xlim(0.05, 1.02)          # sharey would overwrite its tick labels
    bx.set_xticks([])
    S.frame(bx, left=False, bottom=False)
    bx.spines["right"].set_visible(True)
    bx.spines["right"].set_color(S.ACCENT)

    S.save(fig, "fig16_interaction")


if __name__ == "__main__":
    build()
