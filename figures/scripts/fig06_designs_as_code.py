"""Figure 6 -- the two designs, side by side, in their own code.

Trimmed to the lines that differ. The routing design calls the model once and
returns. The deciding design loops, and one line inside that loop puts what an
action returned back in front of the model before it is called again — the
line the routing design has no equivalent of.

Taken verbatim from `apparatus/arms/routing.py` and `apparatus/arms/deciding.py`
apart from the elisions marked with an ellipsis.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import _style as S

OUT = Path(__file__).resolve().parents[1]
INK, MUTED, RULE, SURFACE, ACCENT = "#1B1B1B", "#6B6B6B", "#C9C6C0", "#F5F4F1", "#33506A"

ROUTING = """def take_turn(self, text):
    completion = self.provider.complete(
        system=SYSTEM_PROMPT,
        messages=self.conversation.user_says(text),
        tools=self.schemas(),
    )
    trace.iterations = 1

    if not completion.tool_calls:
        return TurnResult(completion.text, ...)

    call = completion.tool_calls[0]
    result = self.run_action(call)
    dropped = completion.tool_calls[1:]

    return TurnResult(result.text, ...)"""

DECIDING = """def take_turn(self, text):
    messages = self.conversation.user_says(text)

    for iteration in range(1, MAX_ITERATIONS + 1):
        completion = self.provider.complete(
            system=SYSTEM_PROMPT, messages=messages,
            tools=self.schemas())

        if not completion.tool_calls:
            reply = completion.text
            break

        messages = messages + [assistant(...)]
        for call in completion.tool_calls:
            result = self.run_action(call)
            messages = messages + [tool_result(result)]

    return TurnResult(reply, ...)"""

HILITE = {"DECIDING": ["    for iteration in range(1, MAX_ITERATIONS + 1):",
                       "            messages = messages + [tool_result(result)]"]}


def panel(ax, x, w, title, note, code, highlight=()):
    # The box follows the listing rather than a fixed height: the two
    # listings differ by five lines, and a fixed box left the shorter one
    # with an empty third.
    n = len(code.split(chr(10)))
    bottom = 84.5 - (n - 1) * 4.35 - 3.4
    ax.add_patch(Rectangle((x, bottom), w, 88 - bottom, facecolor=SURFACE,
                           edgecolor=RULE, linewidth=1.0, zorder=1))
    ax.text(x + 1.6, 95.5, title, ha="left", va="center", color=ACCENT,
            fontsize=S.BODY, fontweight="bold")
    ax.text(x + 1.6, 90.5, note, ha="left", va="center", color=MUTED,
            fontsize=S.SMALL, style="italic")
    for i, line in enumerate(code.split("\n")):
        y = 84.5 - i * 4.35
        hot = line in highlight
        if hot:
            ax.add_patch(Rectangle((x + 0.8, y - 1.9), w - 1.6, 3.9,
                                   facecolor="white", edgecolor=ACCENT,
                                   linewidth=1.1, zorder=2))
        ax.text(x + 1.9, y, line, ha="left", va="center", zorder=3,
                color=INK if line.strip() else MUTED, fontsize=S.SMALL,
                family="monospace",
                fontweight="bold" if hot else "normal")


def build():
    # Stacked, not side by side. Two monospace listings sharing the house
    # width leave 3in each, and these lines run past that, so the earlier
    # layout either clipped them or set the code at 6.8pt to fit. One above
    # the other gives each the full width at body size, and the comparison
    # survives because the two listings are short and the eye travels down
    # rather than across.
    rows = [len(ROUTING.split(chr(10))), len(DECIDING.split(chr(10)))]
    fig, axes = plt.subplots(2, 1, figsize=(S.WIDTH, 6.4),
                             gridspec_kw={"height_ratios": rows})
    # Each axes ends where its own listing does, or the shorter panel keeps
    # a block of empty axes beneath it.
    for ax, n in zip(axes, rows):
        ax.set_xlim(0, 100)
        ax.set_ylim(84.5 - (n - 1) * 4.35 - 5.4, 100)
        ax.axis("off")

    panel(axes[0], 0, 100, "Routing", "one model call, then return", ROUTING)
    panel(axes[1], 0, 100, "Deciding", "a loop, and one line that feeds it",
          DECIDING, HILITE["DECIDING"])

    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01,
                        hspace=0.16)
    S.save(fig, "fig06_designs_as_code")


if __name__ == "__main__":
    build()
