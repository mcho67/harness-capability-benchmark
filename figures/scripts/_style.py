"""The house style every figure in this paper is built to.

Decided 2026-09-05, after the first assembled draft showed the figures reading
as generated rather than designed. Three faults drove it: no figure carried a
number or a caption, the explanatory text was baked into the image at roughly
half the body type's size, and no two figures agreed on width, title
treatment or axis furniture.

**Captions are not in the image.** They are typed into the document beneath
each figure, in the body typeface, so they match the paper's size and
alignment and so a figure can actually be cited. Every caption is written to
one shape:

    Figure N. *The point of the figure, as a claim.* The evidence for it.
    Provenance: n, unit, resamples, seed.

That shape is the strategic part. A reader who skims only the italic sentences
collects the paper's argument in order.

**So an image carries only what has to be graphical**: the marks, the axis,
the labels a reader reads values off, and any annotation that would be absurd
in prose. No title, no caption block, no footnote.

Everything below is fixed so that the whole set looks like one set.
"""

import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1]

# ── the one width ────────────────────────────────────────────────────────
# 6.5 inches is the text column of a letter page at one-inch margins, so a
# figure drops into the document at 100% and lines up with the prose on both
# edges. Every figure is this wide; only height varies.
WIDTH = 6.5

# ── palette ──────────────────────────────────────────────────────────────
INK = "#1B1B1B"        # marks and labels that carry information
MUTED = "#6B6B6B"      # secondary labels, axis text
RULE = "#C9C6C0"       # rules, spines, reference lines
SURFACE = "#F5F4F1"    # alternating row fill
ACCENT = "#33506A"     # reserved: the one quantity the figure is about

# ── type ─────────────────────────────────────────────────────────────────
# 9pt is the floor anywhere in an image. Below that it stops being readable
# on paper next to an 11pt body.
BODY = 9.0
SMALL = 8.6            # dense table cells only
LABEL = 9.5            # axis labels
EMPH = 10.0            # the number the figure exists to show

matplotlib.rcParams.update({
    "font.size": BODY,
    "axes.titlesize": BODY,
    "axes.labelsize": LABEL,
    "xtick.labelsize": BODY,
    "ytick.labelsize": BODY,
    "axes.edgecolor": RULE,
    "axes.linewidth": 0.9,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.major.size": 0,
    "ytick.major.size": 3,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def frame(ax, left=True, bottom=True, grid=False):
    """Strip the box. Keep only the spines a reader uses.

    Gridlines are off unless a value has to be read off the axis rather than
    from a printed label; where a figure prints its values, a grid is
    decoration competing with them.
    """
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    for side in ("left", "bottom"):
        if ax.spines[side].get_visible():
            ax.spines[side].set_color(RULE)
    if grid:
        ax.grid(axis="y", color=RULE, linewidth=0.6, alpha=0.6)
        ax.set_axisbelow(True)


# Python's format codes emit an ASCII hyphen for a negative number, which is
# shorter than the plus it lines up under and shorter than the minus
# matplotlib puts on its own tick labels. Any figure that draws a signed
# number as text passes it through here first.
_MINUS = re.compile(r"(?<![A-Za-z0-9])-(?=[.\d])")


def signs(text):
    return _MINUS.sub("−", str(text))


#: Pixels at 300dpi for the one figure width.
WIDTH_PX = int(WIDTH * 300)


def save(fig, stem):
    """Save at the house width, exactly.

    `bbox_inches="tight"` is what keeps a label from being clipped, but it
    trims each figure to its own content, so every figure comes out a
    different width. Fitted to the page afterwards, each would be scaled by
    a different factor and the 9pt type floor would mean nothing — the whole
    point of a shared width is that a reader sees one size of text throughout.

    So the image is saved tight and then padded with white to the exact house
    width. Padding adds margin without rescaling, so the type stays 9pt. A
    figure whose content is *wider* than the house width cannot be fixed this
    way and is reported, because the answer there is to narrow the figure
    rather than to shrink its text.
    """
    fig.savefig(OUT / f"{stem}.pdf", facecolor="white", bbox_inches="tight",
                pad_inches=0.04)
    png = OUT / f"{stem}.png"
    fig.savefig(png, facecolor="white", bbox_inches="tight", pad_inches=0.04,
                dpi=300)
    plt.close(fig)

    from PIL import Image
    im = Image.open(png)
    if im.width > WIDTH_PX:
        print(f"wrote {stem}  -- OVER WIDTH by "
              f"{(im.width - WIDTH_PX) / 300:.2f} in; narrow its content")
        return
    if im.width < WIDTH_PX:
        canvas = Image.new("RGB", (WIDTH_PX, im.height), "white")
        canvas.paste(im, ((WIDTH_PX - im.width) // 2, 0))
        canvas.save(png)
    print(f"wrote {stem}")
