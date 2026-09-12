"""Figure 14 -- the validity gate, and the one category that failed it.

The gate was written before the pilot: if the on-device model scored below
0.15 or above 0.85 on a category, the task set was to be recalibrated rather
than run. It exists so a study cannot report an interaction that is really a
floor.

Read off the pilot, whose numbers triggered the exception. The full run's
outcome on the same gate belongs to §4.7.

Every number comes from `runs/pilot-2026-08-19/report.json`, not typed in.

Grayscale-safe: the band is a shaded span, the two categories outside it are
marked by open dots and labels.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import _style as S

OUT = Path(__file__).resolve().parents[1]
REC = Path(__file__).resolve().parents[3] / "runs" / "pilot-2026-08-19" / "report.json"

INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"


def build():
    gate = json.loads(REC.read_text(encoding="utf-8"))["validity_gate"]
    lo, hi = gate["band"]
    cats = sorted(gate["per_category"].items(), key=lambda kv: kv[1]["rate"])

    fig, ax = plt.subplots(figsize=(S.WIDTH, 4.3))
    ys = list(range(len(cats)))

    ax.axvspan(lo, hi, facecolor=SURFACE, edgecolor="none", zorder=0)
    for v in (lo, hi):
        ax.axvline(v, color=ACCENT, linewidth=1.3, linestyle=(0, (4, 2)),
                   zorder=2)
    ax.text(lo, len(cats) - 0.28, f"  floor {lo}", ha="left", va="center",
            color=ACCENT, fontsize=S.SMALL, fontweight="bold")
    ax.text(hi, len(cats) - 0.28, f"ceiling {hi}  ", ha="right", va="center",
            color=ACCENT, fontsize=S.SMALL, fontweight="bold")

    for y, (name, d) in zip(ys, cats):
        outside = not d["in_band"] or d["exempt"]
        ax.plot([0, d["rate"]], [y, y], color=RULE, linewidth=2.0, zorder=1)
        ax.plot(d["rate"], y, marker="o", markersize=11, zorder=4,
                markerfacecolor="white" if outside else ACCENT,
                markeredgecolor=ACCENT, markeredgewidth=1.8)
        # A value that lands within a whisker of a band edge is painted over
        # the dashed line rather than under it; "0.875" otherwise sits
        # astride the ceiling.
        near = min(abs(d["rate"] - lo), abs(d["rate"] - hi)) < 0.06
        ax.text(d["rate"], y + 0.30, f"{d['rate']:.3f}", ha="center",
                va="bottom", fontsize=S.BODY, fontweight="bold", color=INK,
                zorder=5,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.4)
                if near else None)
        note = ("below the floor" if not d["in_band"]
                else "exempt by design" if d["exempt"] else "")
        if note:
            # Each note is placed on the side of its marker with room for it,
            # and clear of the dashed line: to the right of the floor for the
            # category below it, to the left of the ceiling for the exempt one.
            if d["rate"] > 0.5:
                nx, ha = min(d["rate"] - 0.035, hi - 0.015), "right"
            else:
                nx, ha = max(d["rate"] + 0.035, lo + 0.015), "left"
            ax.text(nx, y - 0.30, note, ha=ha, va="center",
                    fontsize=S.SMALL, color=ACCENT, style="italic",
                    fontweight="bold", zorder=5)

    ax.set_yticks(ys)
    ax.set_yticklabels([n for n, _ in cats], fontsize=10)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(-0.62, len(cats) - 0.45)
    ax.set_xlabel("task success, on-device, both designs pooled")
    ax.tick_params(axis="x", labelsize=9)
    # No gridlines: every value is printed beside its marker, so a grid is a
    # second, worse copy of the same information (`_style.frame`).
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)


    n = next(iter(gate["per_category"].values()))["n"]

    fig.tight_layout(pad=0.3)
    S.save(fig, "fig14_validity_gate")


if __name__ == "__main__":
    build()
