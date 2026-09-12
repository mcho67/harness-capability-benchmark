"""Figure 28 -- what each of the deciding design's three properties is worth.

Each variant removes exactly one property and is measured against the routing
design at the same deployment, so the whole design's advantage and each
variant's sit on one scale. The dashed line is the full design; a variant
below it means the removed property was helping, above it means the removed
property was costing.

Numbers from `runs/study2_analysis.json` (`tools/analyze_study2.py`).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import _data as D

import _style as S

REC = Path(__file__).resolve().parents[3] / "runs" / "study2_analysis.json"

ROWS = [("deciding-no-ask", "without ask_user"),
        ("deciding-no-multi-dispatch", "without multi-dispatch"),
        ("deciding-no-iteration", "without the loop")]
PANEL = [("on-device", "on-device  (llama3.1:8b)"),
         ("cloud", "cloud  (claude-sonnet-4-6)")]


def build():
    abl = json.loads(REC.read_text(encoding="utf-8"))["ablation"]

    fig, axes = plt.subplots(1, 2, figsize=(S.WIDTH, 2.9), sharey=True)
    for ax, (key, title) in zip(axes, PANEL):
        # Deployment identifies the panel; without it the two are the same
        # picture twice.
        ax.text(0.0, 1.06, title, transform=ax.transAxes, ha="left",
                va="bottom", fontsize=S.BODY, color=S.INK)
        block = abl[key]
        full = block["deciding_advantage"]
        ax.axvline(0, color=D.RULE, linewidth=1.2, zorder=0)
        ax.axvline(full["estimate"], color=D.INK, linewidth=1.0,
                   linestyle=(0, (4, 3)), zorder=0)
        # Beside the dashed line, not on it. Centred on the estimate, the
        # line ran straight through the middle of the words.
        ax.text(full["estimate"] - 0.012, -0.72,
                S.signs(f"full design {full['estimate']:+.3f}"),
                ha="right", va="bottom", fontsize=S.SMALL, color=D.INK,
                zorder=5,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.6))
        for i, (name, _) in enumerate(ROWS):
            v = block["variants"][name]
            lo, hi = v["ci95"]
            clears = lo > 0 or hi < 0
            color = D.ACCENT if clears else D.MUTED
            ax.plot([lo, hi], [i, i], color=color,
                    linewidth=2.4 if clears else 1.6, solid_capstyle="round")
            ax.plot([v["advantage_over_routing"]], [i], "o", color=color,
                    markersize=6 if clears else 5)
        ax.set_yticks(range(len(ROWS)))
        ax.set_yticklabels([lab for _, lab in ROWS], fontsize=S.BODY)
        ax.set_ylim(len(ROWS) - 0.55, -1.0)
        ax.set_xlim(-0.20, 0.40)
        ax.set_xlabel("advantage over the routing design", fontsize=S.BODY,
                      color=D.MUTED)
        ax.tick_params(labelsize=8.2, colors=D.MUTED)
        # No left spine, so a y tick is a dash floating beside the label
        # -- beside nothing at all on the right panel, which shares them.
        ax.tick_params(axis="y", length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(D.RULE)

    # Space between the panels: butted together, the left panel's last x
    # tick label and the right panel's first ran into each other.
    fig.subplots_adjust(left=0.235, right=0.98, top=0.90, bottom=0.19,
                        wspace=0.16)
    S.save(fig, "fig29_ablation")


if __name__ == "__main__":
    build()
