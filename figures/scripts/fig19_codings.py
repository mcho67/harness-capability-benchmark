"""Figure 19 -- both main effects under each coding of a partial run."""
import json
from pathlib import Path
import _table as T

REC = Path(__file__).resolve().parents[3] / "runs" / "full-2026-08-20"


def build():
    m = json.loads((REC / "main_effects.json").read_text(encoding="utf-8"))
    # Estimate over interval, two lines to a cell. Set on one line, the four
    # numbers of a row filled the width and the first row's label ran into
    # them.
    def cell(block, key):
        d = m[block][key]
        return (f"{d['point']:+.3f}\n"
                f"[{d['ci_low']:+.3f}, {d['ci_high']:+.3f}]")
    rows = [
        ["strict  (primary)\npartial counts as failure",
         cell("marginal_effects", "architecture"), cell("marginal_effects", "deployment")],
        ["lenient\npartial counts as success",
         cell("marginal_effects_lenient", "architecture"),
         cell("marginal_effects_lenient", "deployment")],
    ]
    T.render("fig19_codings", ["coding", "design", "deployment"], rows,
             "Both codings were fixed before any data. Granting credit for partial completions halves\n"
             "the design effect and its interval crosses zero, while leaving deployment untouched.",
             widths=[3.0, 2.0, 2.0], emphasize=(0,))


if __name__ == "__main__":
    build()
