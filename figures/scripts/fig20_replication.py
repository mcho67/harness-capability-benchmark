"""Figure 20 -- how many distinct replies each task-and-configuration pair produced.

Drawn as bars rather than set as a table. The table version had two columns,
a label and a count, and at the house width the count sat six inches from the
label it belonged to. The shape of this distribution is the whole point — one
bar carries 135 of the 192 pairs and the other four share the rest — and a bar
shows that shape without the reader adding anything up.

Numbers from `runs/full-2026-08-20/main_effects.json`, key `replication`.
Grayscale-safe: the bar the figure is about is filled, the rest are outlined.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import blended_transform_factory

import _style as S

REC = Path(__file__).resolve().parents[3] / "runs" / "full-2026-08-20"

LABEL = {1: "every repetition identical",
         5: "every repetition different"}


def build():
    r = json.loads((REC / "main_effects.json").read_text(encoding="utf-8"))["replication"]
    d = r["distinct_replies_per_pair"]
    keys = sorted((int(k) for k in d), reverse=True)   # 1 at the top
    vals = [d[str(k)] for k in keys]
    total = r["cell_task_pairs"]

    fig, ax = plt.subplots(figsize=(S.WIDTH, 2.7))
    ax.barh(range(len(keys)), vals, height=0.62,
            color=[S.ACCENT if k == 1 else "white" for k in keys],
            edgecolor=[S.ACCENT if k == 1 else S.RULE for k in keys],
            linewidth=1.1, zorder=2)

    for i, (k, v) in enumerate(zip(keys, vals)):
        ax.text(v + 3.0, i, f"{v}", ha="left", va="center", color=S.INK,
                fontsize=S.EMPH if k == 1 else S.BODY,
                fontweight="bold" if k == 1 else "normal")

    # The row labels are drawn rather than set as tick labels. Tick labels are
    # right-aligned against the axis, which put "1  every repetition
    # identical" and a bare "2" on two different left edges.
    # x in figure fractions so the gutter is a fixed width on the page, not a
    # fraction of the axes; y in data so a label stays on its bar.
    gutter = blended_transform_factory(fig.transFigure, ax.transData)
    for i, k in enumerate(keys):
        ax.text(0.006, i, f"{k}", ha="left", va="center", color=S.INK,
                fontsize=S.BODY, transform=gutter, clip_on=False)
        if k in LABEL:
            ax.text(0.042, i, LABEL[k], ha="left", va="center", color=S.MUTED,
                    fontsize=S.BODY, transform=gutter, clip_on=False)

    # The total, drawn, so the length of a bar is read against something. The
    # right half of the axes is otherwise empty and gives no sense of scale.
    ax.axvline(total, color=S.RULE, linewidth=1.0, zorder=1)
    ax.text(total - 3.0, len(keys) - 0.55, f"all {total} pairs", ha="right",
            va="bottom", color=S.MUTED, fontsize=S.SMALL)

    ax.set_yticks([])
    ax.set_ylim(-0.62, len(keys) - 0.28)
    ax.set_xlim(0, total * 1.03)
    ax.set_xticks([])
    # Values are printed at the end of every bar, so an axis to read them off
    # would be a second copy of the same information.
    S.frame(ax, left=False, bottom=False)

    fig.subplots_adjust(left=0.305, right=0.975, top=0.96, bottom=0.04)
    S.save(fig, "fig20_replication")


if __name__ == "__main__":
    build()
