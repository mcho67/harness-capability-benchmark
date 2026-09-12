"""Figure 2 — the 2x2 design grid.

Orients the reader before any result appears: two harness designs crossed
with two model deployments gives four configurations. No outcome numbers
belong in this figure; the only numbers are design facts (n per cell).

Cell ids follow the analysis code: C1 deciding/cloud, C2 deciding/on-device,
C3 routing/cloud, C4 routing/on-device.

Renders to PNG (300 dpi, for drafts) and PDF (vector, for the paper).
Grayscale-safe: all four cells share one surface, because all four are
equivalent in status and any differentiation would imply a hierarchy that
does not exist.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

import _style as S

OUT = Path(__file__).resolve().parents[1]

INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"

CELLS = [
    # (x, y, id, design, deployment)
    (26, 46, "C1", "deciding", "cloud"),
    (62, 46, "C2", "deciding", "on-device"),
    (26, 10, "C3", "routing", "cloud"),
    (62, 10, "C4", "routing", "on-device"),
]

W, H = 35, 35


def build():
    fig, ax = plt.subplots(figsize=(S.WIDTH, 4.7))
    ax.set_xlim(0, 100)
    # Nothing is drawn below y=10; the axes used to run to 0 and carried
    # half an inch of blank paper under the grid.
    ax.set_ylim(7, 99.5)
    ax.axis("off")

    # --- column header band -------------------------------------------------
    ax.add_patch(Rectangle((26, 91), 71, 6, facecolor=ACCENT,
                           edgecolor="none", zorder=1))
    ax.text(61.5, 94, "M O D E L   D E P L O Y M E N T", ha="center",
            va="center", color="white", fontsize=S.SMALL, fontweight="bold",
            zorder=2)

    # --- row header band ----------------------------------------------------
    ax.add_patch(Rectangle((2, 10), 6, 71, facecolor=ACCENT,
                           edgecolor="none", zorder=1))
    ax.text(5, 45.5, "H A R N E S S   D E S I G N", ha="center", va="center",
            color="white", fontsize=S.SMALL, fontweight="bold", rotation=90,
            zorder=2)

    # --- column labels ------------------------------------------------------
    for x, label, sub in [
        (43.5, "Cloud", "claude-sonnet-4-6"),
        (79.5, "On-device", "llama3.1:8b, 4-bit"),
    ]:
        ax.text(x, 87.5, label, ha="center", va="center", color=INK,
                fontsize=10.5, fontweight="bold")
        ax.text(x, 83.5, sub, ha="center", va="center", color=MUTED,
                fontsize=S.SMALL)

    # --- row labels ---------------------------------------------------------
    for y, label, sub in [
        (63.5, "Deciding", "may revise\nafter acting"),
        (27.5, "Routing", "commits to one\naction"),
    ]:
        ax.text(23.5, y + 2.2, label, ha="right", va="center", color=INK,
                fontsize=10.5, fontweight="bold")
        ax.text(23.5, y - 3.2, sub, ha="right", va="center", color=MUTED,
                fontsize=S.SMALL, linespacing=1.5)

    # --- the four cells -----------------------------------------------------
    for x, y, cid, design, deploy in CELLS:
        ax.add_patch(FancyBboxPatch(
            (x, y), W, H,
            boxstyle="round,pad=0,rounding_size=1.2",
            facecolor=SURFACE, edgecolor=RULE, linewidth=1.0, zorder=1))
        ax.text(x + W / 2, y + H * 0.62, cid, ha="center", va="center",
                color=INK, fontsize=17, fontweight="bold", zorder=2)
        ax.text(x + W / 2, y + H * 0.38, f"{design}  ×  {deploy}",
                ha="center", va="center", color=MUTED, fontsize=S.BODY, zorder=2)
        ax.text(x + W / 2, y + H * 0.20, "240 runs", ha="center", va="center",
                color=MUTED, fontsize=S.SMALL, style="italic", zorder=2)

    # --- footer -------------------------------------------------------------

    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    S.save(fig, "fig02_design_grid")


if __name__ == "__main__":
    build()
