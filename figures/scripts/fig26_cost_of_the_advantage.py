"""Figure 26 -- what the deciding design's advantage costs.

Each configuration is one point: how long a run took against how often it
succeeded. The two arrows are the same comparison the paper reports, drawn as
a purchase — from the routing design to the deciding design, at one
deployment, showing what the extra time bought.

Both arrows point up and to the right. The deciding design is never free.

Latency is the median over 240 runs; per-run cost is the mean. Both are read
from `runs/full-2026-08-20/scored.jsonl`.

Grayscale-safe: deployment is carried by fill, hollow against solid.
"""

from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

import _data as D

import _style as S

OUT = Path(__file__).resolve().parents[1]


def build():
    rows = D.load()
    lat, cost, succ = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in rows:
        lat[r["cell"]].append(float(r["latency_s"]))
        cost[r["cell"]].append(float(r.get("cost_usd") or 0))
        succ[r["cell"]].append(float(r["success_strict"]))
    L = {c: median(v) for c, v in lat.items()}
    K = {c: mean(v) for c, v in cost.items()}
    succ_mean = {c: mean(v) for c, v in succ.items()}

    fig, ax = plt.subplots(figsize=(S.WIDTH, 4.6))
    # Tighter than matplotlib's defaults, which left this plot an inch
    # narrower than the drawn figures around it in the paper.
    fig.subplots_adjust(left=0.085, right=0.985, top=0.98, bottom=0.135)

    for frm, to, label in (("C3", "C1", "cloud"), ("C4", "C2", "on-device")):
        ax.add_patch(FancyArrowPatch(
            (L[frm], succ_mean[frm]), (L[to], succ_mean[to]), arrowstyle="-|>",
            mutation_scale=15, color=D.ACCENT, linewidth=1.8, zorder=2,
            shrinkA=13, shrinkB=13))
        mx, my = (L[frm] + L[to]) / 2, (succ_mean[frm] + succ_mean[to]) / 2
        # Above the arrow, not across it. Centred on the midpoint, the second
        # line sat on the shallower of the two arrows and the line ran
        # through the words.
        ax.text(mx - 0.30, my + 0.012,
                f"+{succ_mean[to] - succ_mean[frm]:.3f}\nsuccess\n"
                f"×{L[to] / L[frm]:.1f} time", ha="right", va="bottom",
                color=D.ACCENT, fontsize=S.BODY, fontweight="bold",
                linespacing=1.5)

    for c in D.CELLS:
        cloud = D.DEPLOY[c] == "cloud"
        ax.plot(L[c], succ_mean[c], marker="o", markersize=13, zorder=4,
                markerfacecolor=D.ACCENT if cloud else "white",
                markeredgecolor=D.ACCENT, markeredgewidth=1.9)
        money = f"${K[c]:.4f}/run" if K[c] else "no per-run cost"
        ax.annotate(f"{D.DESIGN[c]}\n{money}", (L[c], succ_mean[c]),
                    textcoords="offset points", xytext=(14, -4), ha="left",
                    va="center", fontsize=S.BODY, color=D.INK, linespacing=1.5)

    ax.set_xlim(1.4, 12.4)
    ax.set_ylim(0.30, 0.93)
    ax.set_xlabel("median seconds from request to final reply")
    ax.set_ylabel("task success")
    ax.tick_params(labelsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(D.RULE)

    ax.plot([], [], marker="o", markersize=11, color=D.ACCENT, linestyle="none",
            label="cloud")
    ax.plot([], [], marker="o", markersize=11, markerfacecolor="white",
            markeredgecolor=D.ACCENT, markeredgewidth=1.9, linestyle="none",
            label="on-device")
    ax.legend(loc="lower right", frameon=False, fontsize=9.5,
              handletextpad=0.4, borderpad=0.3)


    S.save(fig, "fig26_cost_of_the_advantage")
    plt.close(fig)


if __name__ == "__main__":
    build()
