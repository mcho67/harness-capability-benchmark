"""Shared renderer for the tables that are figures.

Eight figures are tables, and they go through here so they share the house
palette, type and spacing with the plotted figures rather than each inventing
its own.

**Captions are not drawn.** They are typed into the document beneath the
figure, in the body typeface, so they match the paper's size and alignment
and so a figure can be cited by number (`_style`). Callers still pass their
caption text: it is recorded in `CAPTIONS` so the wording stays next to the
numbers it describes, and it is simply not painted into the image. The
captions as they appear in the paper are `docs/figure_captions.md`.

**Every table is the same width.** A page of figures that each sized
themselves to their own content read as a pile rather than a set. Column
widths are still relative; they are scaled to the one figure width.

Row heights follow their tallest cell, so a wrapped request or a two-line
header does not spill into its neighbour.

Numbers come from the record in each caller; nothing here transcribes one.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import _style as S

OUT = Path(__file__).resolve().parents[1]

# Kept as module attributes because callers import them from here.
INK, MUTED, RULE, SURFACE, ACCENT = S.INK, S.MUTED, S.RULE, S.SURFACE, S.ACCENT

# Row geometry, in axis units. A line of 9pt type at 1.45 linespacing is
# about 0.18in tall, so LINE_H has to buy at least that once scaled, and
# ROW_PAD has to leave air above and below it. The first version of this
# file used 0.40/0.34 against a 0.285 scale, which gave a single-line row
# 0.21in — tighter than the type itself, so wrapped cells ran into their
# neighbours and the header sat on the rule.
LINE_H = 0.44
ROW_PAD = 0.42

#: Inches per axis unit. A one-line row is LINE_H + ROW_PAD = 0.86 units, so
#: this sets it to 0.34in — a 9pt line with air above and below it.
SCALE = 0.40

#: {stem: caption} filled as figures render, read by the caption collector.
CAPTIONS = {}


def _lines(cell):
    return str(cell).count("\n") + 1


_signs = S.signs


def render(stem, headers, rows, caption, title=None, widths=None,
           align=None, emphasize=()):
    """headers: list[str]. rows: list[list[str]]. widths: relative column
    widths. align: 'l' or 'r' per column. emphasize: row indices drawn bold.

    `caption` and `title` are recorded, not drawn.
    """
    CAPTIONS[stem] = caption

    n_col = len(headers)
    widths = widths or [2.6] + [1.0] * (n_col - 1)
    align = align or ["l"] + ["r"] * (n_col - 1)
    total = sum(widths)

    edges, x = [], 0.0
    for w in widths:
        edges.append((x, x + w)); x += w

    hdr_lines = max(_lines(h) for h in headers)
    rule_y = 0.0
    heights = [LINE_H * max(_lines(c) for c in row) + ROW_PAD for row in rows]
    body = sum(heights)

    y_lo = rule_y - body - 0.22
    y_hi = rule_y + 0.30 + LINE_H * hdr_lines

    # One width for every figure in the paper; height follows the content.
    #
    # The axes has to be told to fill the figure. Matplotlib's default leaves
    # margins for tick labels a table does not have, which put the axes at
    # 77% of the figure's width and height; `_style.save` then trimmed to the
    # ink and padded the result back out, so every table came out as a 5.0in
    # block centred in a 6.5in image while every drawn figure used the whole
    # column. Filling the axes both widens the columns and makes SCALE mean
    # what it says.
    fig, ax = plt.subplots(figsize=(S.WIDTH, SCALE * (y_hi - y_lo)))
    fig.subplots_adjust(left=0.0062, right=0.9938, top=0.996, bottom=0.004)
    ax.set_xlim(0, total)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")

    def put(text, col, y, bold=False, color=INK, size=S.BODY, va="center"):
        lo, hi = edges[col]
        x_, ha = (lo + 0.10, "left") if align[col] == "l" else (hi - 0.10, "right")
        ax.text(x_, y, _signs(text), ha=ha, va=va, color=color, fontsize=size,
                linespacing=1.45, fontweight="bold" if bold else "normal")

    for c, h in enumerate(headers):
        put(h, c, rule_y + 0.22, bold=True, color=MUTED, size=S.SMALL,
            va="bottom")
    ax.plot([0, total], [rule_y, rule_y], color=ACCENT, linewidth=1.3)

    cursor = 0.0
    for r, row in enumerate(rows):
        h = heights[r]
        top, bot = rule_y - cursor, rule_y - cursor - h
        if r % 2 == 1:
            ax.add_patch(Rectangle((0, bot), total, h, facecolor=SURFACE,
                                   edgecolor="none", zorder=0))
        for c, cell in enumerate(row):
            put(cell, c, (top + bot) / 2, bold=(r in emphasize))
        cursor += h

    ax.plot([0, total], [rule_y - body, rule_y - body], color=RULE,
            linewidth=1.0)

    S.save(fig, stem)
