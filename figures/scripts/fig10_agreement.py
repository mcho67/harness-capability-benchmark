"""Figure 10 -- what an independent second derivation agreed with.

The figure's job is not to report agreement. It is to separate the components
that can change a result from the ones that cannot, because the two weakest
numbers in the check sit on components that gate nothing: a decision counts as
correct only when the *required* parts match, and putting work in the
background and breaking a request into steps are not required.

**The action row is recomputed here rather than read.**
`runs/ideal_agreement.json` stores `action_choice` as 24 of 43. That value
cannot be reproduced from the rater's returned sheet and the task file under
any matching rule, and its cause is identifiable: the coded sheet writes the
literal string `none` in the action column for four robustness tasks, meaning
*no action*, and a computation that reads it as an action named "none"
invents disagreements. Reading `none` as the empty set gives 26 of 40 under
the any-of rule, which is what the scorer applies to the assistant and is
therefore the only defensible standard to hold the rater to. Appendix D
records the discrepancy; the stored value is not used anywhere.

Grayscale-safe: the two groups are told apart by position, weight and fill.

The caption lives in the document, not here (`_style`).
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

import _style as S

ROOT = Path(__file__).resolve().parents[3]
REC = ROOT / "runs" / "ideal_agreement.json"
SHEET = ROOT / "runs" / "second_rater_returned_coded.csv"
TASKS = ROOT / "apparatus" / "tasks" / "tasks.json"

LABEL = {
    "asked": "whether to ask for a missing detail",
    "declined": "whether to decline",
    "action": "which action to reach for",
    "backgrounded": "whether to put it in the background",
    "decomposed": "whether to break it into steps",
}
GATING = ["asked", "declined", "action"]
NON_GATING = ["backgrounded", "decomposed"]


def actions(cell):
    """The rater's or the ideal's action set. `none` means no action."""
    if str(cell).strip().lower() in ("nan", "none", "", "-"):
        return set()
    return {p.strip().lower() for p in str(cell).replace(";", ",").split(",")
            if p.strip() and p.strip().lower() != "none"}


def load():
    d = json.loads(REC.read_text(encoding="utf-8"))
    rows = {k: (v["n_agree"], v["n_rated"], v["cohens_kappa"])
            for k, v in d["per_component"].items()}

    rater = pd.read_csv(SHEET)
    tasks = {t["id"]: t for t in json.loads(TASKS.read_text(encoding="utf-8"))}
    agree = rated = 0
    for _, r in rater.iterrows():
        said = actions(r["YOUR_action"])
        want = {a.lower() for a in
                (tasks[r["task_id"]]["ideal_decision"].get("tools") or [])}
        if not (said or want):
            continue                       # neither names one: nothing to compare
        rated += 1
        agree += bool(said & want)
    rows["action"] = (agree, rated, None)
    return rows


def build():
    rows = load()

    fig, ax = plt.subplots(figsize=(S.WIDTH, 3.6))
    # The axes fills the figure. Left at matplotlib's defaults it took 77% of
    # the width, so this drawing came out an inch narrower than the drawn
    # figures either side of it in the paper.
    fig.subplots_adjust(left=0.008, right=0.992, top=0.99, bottom=0.01)
    ax.set_xlim(0, 100)
    ax.set_ylim(-8, 100)
    ax.axis("off")

    # Columns, in axis units. The label column needs more room than it
    # looks: at 9pt the longest label runs past x=50, which is where the bar
    # used to start.
    XL, XB, XW, XN, XK = 2, 56, 20, 79, 99

    ax.text(XL, 96, "what was checked", ha="left", va="center", color=S.MUTED,
            fontsize=S.SMALL, fontweight="bold")
    ax.text(XB + XW / 2, 96, "agreement", ha="center", va="center",
            color=S.MUTED, fontsize=S.SMALL, fontweight="bold")
    ax.text(XK, 96, "not due to chance", ha="right", va="center",
            color=S.MUTED, fontsize=S.SMALL, fontweight="bold")

    def band(y, title, sub, strong):
        ax.text(XL, y, title, ha="left", va="center",
                color=S.ACCENT if strong else S.MUTED, fontsize=S.BODY,
                fontweight="bold")
        ax.text(XL, y - 5.4, sub, ha="left", va="center", color=S.MUTED,
                fontsize=S.SMALL, style="italic")

    def row(y, key, strong):
        n, tot, k = rows[key]
        ax.text(XL, y, LABEL[key], ha="left", va="center",
                color=S.INK if strong else S.MUTED, fontsize=S.BODY)
        ax.add_patch(Rectangle((XB, y - 2.2), XW, 4.4, facecolor=S.SURFACE,
                               edgecolor=S.RULE, linewidth=0.7, zorder=1))
        ax.add_patch(Rectangle((XB, y - 2.2), XW * n / tot, 4.4,
                               facecolor=S.ACCENT if strong else S.RULE,
                               edgecolor="none", zorder=2))
        ax.text(XN, y, f"{n} of {tot}", ha="left", va="center",
                color=S.INK if strong else S.MUTED, fontsize=S.BODY)
        ax.text(XK, y, "—" if k is None else f"{k:.3f}", ha="right",
                va="center", color=S.INK if strong else S.MUTED,
                fontsize=S.BODY)

    band(87, "THESE GATE THE SCORE",
         "a decision counts as correct only if all of these match", True)
    for i, key in enumerate(GATING):
        row(73 - i * 9.5, key, True)

    ax.plot([XL, XK], [40, 40], color=S.RULE, linewidth=1.0)

    band(32, "THESE DO NOT",
         "credit when present, nothing lost when absent", False)
    for i, key in enumerate(NON_GATING):
        row(18 - i * 9.5, key, False)

    note = (
        "The last column is Cohen's kappa: the share of agreement left once "
        "the agreement two raters would\n"
        "reach by guessing is taken out. It is low here because these "
        "decisions are heavily skewed to one\n"
        "value, which makes guessing look good, so the counts are the more "
        "informative number."
    )
    ax.text(XL, -3, note, ha="left", va="top", color=S.MUTED,
            fontsize=S.SMALL - 0.5, linespacing=1.5)

    S.save(fig, "fig10_agreement")


if __name__ == "__main__":
    build()
