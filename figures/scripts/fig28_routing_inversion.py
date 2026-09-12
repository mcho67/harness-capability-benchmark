"""Figure 29 -- why routing task success is not a measure of model capability.

Three models on one capability ordering, at two deployments but with the
comparison that matters held inside cloud: sonnet against haiku. Under the
deciding design, task success rises with capability. Under the routing design
it does not — the weaker cloud model scores higher.

The right panel is the control that rules out the obvious explanations.
Decision accuracy scores which action the model chose and never passes
through the reply, and it orders correctly under both designs. So the
inversion is in what the user is shown, not in what the model decided.

Computed from the scored rows rather than transcribed.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import _data as D

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apparatus"))
from harness.capture import read_rows                            # noqa: E402

import _style as S

STUDY1 = ROOT / "runs" / "full-2026-08-20" / "scored.jsonl"
STUDY2 = ROOT / "runs" / "study2"

# Ordered by capability as the deciding design measures it, weakest first.
# Short names on the axis: the full model strings overlap at this width and
# the caption gives them in full.
MODELS = [("llama3.1:8b", "C2", "C4"),
          ("haiku-4-5", "deciding@claude-haiku-4-5-20251001",
           "routing@claude-haiku-4-5-20251001"),
          ("sonnet-4-6", "C1", "C3")]


def frame():
    rows = pd.DataFrame(read_rows(str(STUDY1)))
    parts = [rows]
    for p in sorted(STUDY2.glob("*.scored.jsonl")):
        d = pd.read_json(p, lines=True)
        d["cell"] = p.name.replace(".scored.jsonl", "")
        parts.append(d)
    return pd.concat(parts, ignore_index=True)


def build():
    f = frame()

    def mean(cell, col):
        s = f[f["cell"] == cell]
        v = pd.to_numeric(s[col], errors="coerce")
        return float(v.groupby(s["task_id"]).mean().mean())

    fig, axes = plt.subplots(1, 2, figsize=(S.WIDTH, 3.3), sharey=True)
    # Fill the column, and leave the gutters the labels at the ends of each
    # line need. At the defaults the pair covered 5.5in of a 6.5in figure.
    fig.subplots_adjust(left=0.085, right=0.98, top=0.97, bottom=0.14,
                        wspace=0.26)
    panels = [("success_strict", "task success"),
              ("decision_correct", "decision accuracy")]
    x = range(len(MODELS))
    for ax, (col, title) in zip(axes, panels):
        for label, dec_cell, rout_cell, colour in (
                ("deciding", 1, 2, D.ACCENT), ("routing", 1, 2, D.MUTED)):
            cells = [m[1] if label == "deciding" else m[2] for m in MODELS]
            y = [mean(c, col) for c in cells]
            ax.plot(x, y, "-o", color=colour, linewidth=2.0, markersize=6,
                    label=label)
            # Where a label goes depends on where its point sits. The lines
            # here are steep, so a fixed offset straight above or below the
            # marker put half the numbers on top of a line. The end points
            # get the gutters outside the data instead, and only the middle
            # pair is offset vertically.
            up = label == "deciding"
            for xi, yi in zip(x, y):
                if xi == 0:
                    off, ha = (-9, 6 if up else -9), "right"
                elif xi == len(MODELS) - 1:
                    off, ha = (9, 6 if up else -9), "left"
                elif up:
                    off, ha = (0, 10), "center"
                else:
                    off, ha = (8, -14), "left"
                ax.annotate(f"{yi:.3f}", (xi, yi), textcoords="offset points",
                            xytext=off, ha=ha, va="center", fontsize=S.SMALL,
                            color=colour)
        ax.set_ylabel(title)
        ax.set_xticks(list(x))
        ax.set_xticklabels([m[0] for m in MODELS], fontsize=S.BODY)
        # Half a step of gutter at each end, which is what the first and last
        # value labels need to sit outside the data.
        ax.set_xlim(-0.5, len(MODELS) - 0.5)
        ax.set_ylim(0.30, 0.95)
        # sharey hides the right panel's numbers; both panels are proportions
        # on the same scale, so show them and let the pair be read either way.
        ax.tick_params(labelsize=8.2, colors=D.MUTED, labelleft=True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("bottom", "left"):
            ax.spines[side].set_color(D.RULE)
    axes[0].legend(frameon=False, fontsize=S.BODY, loc="upper left")

    S.save(fig, "fig28_routing_inversion")


if __name__ == "__main__":
    build()
