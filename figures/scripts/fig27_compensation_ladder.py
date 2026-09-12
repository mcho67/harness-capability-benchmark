"""Figure 27 -- the compensation contrast across twelve model pairings.

A forest plot rather than a table: the question a reader has about each of the
twelve is whether its interval crosses zero, and that is a thing to see rather
than to check twelve times in a column of numbers.

Numbers come from `runs/study2_analysis.json`, which is produced by
`tools/analyze_study2.py` and asserts it reproduces Study 1's published
contrast before it computes anything.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import _data as D

import _style as S

REC = Path(__file__).resolve().parents[3] / "runs" / "study2_analysis.json"

# The on-device ladder, weakest first by routing-design task success. Fixed
# here rather than sorted from the data so the two panels share a row order
# and a reader can track one model straight across.
ORDER = ["llama3.1-8b", "llama3.2-3b", "mistral-7b",
         "qwen2.5-1.5b", "qwen2.5-7b", "qwen2.5-3b"]
LABEL = {"llama3.1-8b": "llama3.1:8b", "llama3.2-3b": "llama3.2:3b",
         "mistral-7b": "mistral:7b", "qwen2.5-1.5b": "qwen2.5:1.5b",
         "qwen2.5-7b": "qwen2.5:7b", "qwen2.5-3b": "qwen2.5:3b"}
PANEL = [("sonnet", "against claude-sonnet-4-6"),
         ("haiku", "against claude-haiku-4-5")]


def build():
    data = json.loads(REC.read_text(encoding="utf-8"))["pairs_by_cloud_baseline"]

    fig, axes = plt.subplots(1, 2, figsize=(S.WIDTH, 3.5), sharey=True)
    fig.subplots_adjust(left=0.135, right=0.99, top=0.90, bottom=0.155,
                        wspace=0.10)
    for ax, (key, title) in zip(axes, PANEL):
        # Which baseline this panel uses is structure, not caption: without
        # it the two panels are indistinguishable and the figure says nothing.
        ax.text(0.0, 1.04, title, transform=ax.transAxes, ha="left",
                va="bottom", fontsize=S.BODY, color=S.INK)
        rows = {p["on_device_model"]: p for p in data[key]}
        ax.axvline(0, color=D.RULE, linewidth=1.2, zorder=0)
        for i, model in enumerate(ORDER):
            p = rows[model]
            lo, hi = p["ci95"]
            clears = lo > 0 or hi < 0
            color = D.ACCENT if clears else D.MUTED
            ax.plot([lo, hi], [i, i], color=color,
                    linewidth=2.4 if clears else 1.6, solid_capstyle="round")
            ax.plot([p["compensation"]], [i], "o", color=color,
                    markersize=6 if clears else 5)
        ax.set_yticks(range(len(ORDER)))
        ax.set_yticklabels([LABEL[m] for m in ORDER], fontsize=S.BODY)
        ax.set_xlim(-0.45, 0.30)
        ax.set_xlabel("compensation contrast", color=D.MUTED)
        ax.tick_params(labelsize=8.2, colors=D.MUTED)
        # No left spine, so the y ticks were dashes floating beside the
        # model names -- and beside nothing at all on the right panel,
        # which shares its labels with the left.
        ax.tick_params(axis="y", length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(D.RULE)
    axes[0].invert_yaxis()

    S.save(fig, "fig27_compensation_ladder")


if __name__ == "__main__":
    build()
