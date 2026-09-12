"""Figure 1 -- the request path, both designs, on the same request.

This is the independent variable. Everything else in the study is held still,
so the one difference drawn here is the only thing that could have produced a
difference in the results.

That difference is a single arrow: in the deciding design what an action
returned goes back in front of the model before it is called again. The
routing design has no such arrow, so the model never learns what its own
choice did, and the text the user reads was written by the action rather than
by the model.

No result numbers appear here: the reader meets the design before the finding.
Grayscale-safe: nothing depends on hue.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

import _style as S

OUT = Path(__file__).resolve().parents[1]

INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"

BOX_H = 11.0
XS = [20, 47, 74]
W = 25

ROUTING_NOTE = "commits once;\nnever sees\nwhat the action did"
DECIDING_NOTE = "sees the result,\nthen decides\nagain"


def node(ax, x, y, title, sub, accent=False):
    ax.add_patch(FancyBboxPatch(
        (x, y), W, BOX_H, boxstyle="round,pad=0,rounding_size=1.1",
        facecolor="white" if accent else SURFACE,
        edgecolor=ACCENT if accent else RULE,
        linewidth=1.6 if accent else 1.0, zorder=2))
    ax.text(x + W / 2, y + BOX_H * 0.62, title, ha="center", va="center",
            color=INK, fontsize=9.4, fontweight="bold", zorder=3)
    ax.text(x + W / 2, y + BOX_H * 0.27, sub, ha="center", va="center",
            color=MUTED, fontsize=S.SMALL, zorder=3)


def arrow(ax, x0, y0, x1, y1, rad=0.0, color=INK, lw=1.5):
    ax.add_patch(FancyArrowPatch(
        (x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=13, color=color,
        linewidth=lw, zorder=4, connectionstyle="arc3,rad=%s" % rad,
        shrinkA=0, shrinkB=0))


def lane(ax, y, label, note):
    ax.text(2, y + BOX_H * 0.80, label, ha="left", va="center", color=ACCENT,
            fontsize=10.5, fontweight="bold")
    ax.text(2, y + BOX_H * 0.32, note, ha="left", va="top", color=MUTED,
            fontsize=S.SMALL, style="italic", linespacing=1.6)


def build():
    # The axes stops just under the deciding lane's note, which is the lowest
    # thing drawn. It used to run to -2 with nothing below y=10, so the
    # figure carried half an inch of blank paper under it and everything
    # above was set smaller to compensate.
    fig, ax = plt.subplots(figsize=(S.WIDTH, 4.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(8, 100)
    ax.axis("off")

    ax.text(50, 96, "“clear out the old downloads, they’re taking up space”",
            ha="center", va="center", color=INK, fontsize=10.5, style="italic")
    ax.text(50, 89, "the same request, put to both designs",
            ha="center", va="center", color=MUTED, fontsize=S.SMALL)

    mid = (XS[0] + XS[1]) / 2 + W / 2

    # routing
    yr = 66
    lane(ax, yr, "Routing", ROUTING_NOTE)
    node(ax, XS[0], yr, "model called once", "names one action")
    node(ax, XS[1], yr, "the action runs", "delete_file")
    node(ax, XS[2], yr, "reply to the user", "the action’s own text", accent=True)
    arrow(ax, XS[0] + W, yr + BOX_H / 2, XS[1], yr + BOX_H / 2)
    arrow(ax, XS[1] + W, yr + BOX_H / 2, XS[2], yr + BOX_H / 2)

    ax.plot([XS[1] + W / 2, XS[0] + W / 2], [yr - 5.0, yr - 5.0],
            color=RULE, linewidth=1.4, linestyle=(0, (3, 3)), zorder=1)
    ax.text(mid, yr - 5.0, "×", ha="center", va="center", color=MUTED,
            fontsize=14, fontweight="bold", zorder=3,
            bbox=dict(boxstyle="circle,pad=0.10", facecolor="white",
                      edgecolor="none"))
    # At body size this note is wider than the box it sits under and ran to
    # the edge of the image; it is secondary text, so it takes the secondary
    # size the rest of the annotations use.
    ax.text(98, yr - 5.6, "nothing returns to the model",
            ha="right", va="center", color=MUTED, fontsize=S.SMALL)

    ax.plot([2, 98], [56, 56], color=RULE, linewidth=0.9)

    # deciding
    yd = 20
    lane(ax, yd, "Deciding", DECIDING_NOTE)
    node(ax, XS[0], yd, "model called", "names an action")
    node(ax, XS[1], yd, "the action runs", "list_files")
    node(ax, XS[2], yd, "reply to the user", "written by the model", accent=True)
    arrow(ax, XS[0] + W, yd + BOX_H / 2, XS[1], yd + BOX_H / 2)
    arrow(ax, XS[1] + W, yd + BOX_H / 2, XS[2], yd + BOX_H / 2)

    arrow(ax, XS[1] + W / 2, yd + BOX_H, XS[0] + W / 2, yd + BOX_H,
          rad=0.34, color=ACCENT, lw=2.0)
    ax.text(mid, yd + BOX_H + 17.0,
            "what the action returned goes back to the model,",
            ha="center", va="center", color=ACCENT, fontsize=9.0,
            fontweight="bold")
    ax.text(mid, yd + BOX_H + 12.0,
            "so it may act again, change course, or stop",
            ha="center", va="center", color=ACCENT, fontsize=9.0,
            fontweight="bold")


    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    S.save(fig, "fig01_request_path")


if __name__ == "__main__":
    build()
