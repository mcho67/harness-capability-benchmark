"""Figure 23 -- task success split by whether the run's decision matched the ideal."""
import json
from pathlib import Path
import _data as D, _table as T

REC = Path(__file__).resolve().parents[3] / "runs" / "full-2026-08-20"


def build():
    d = json.loads((REC / "main_effects.json").read_text(encoding="utf-8"))["decision_to_success"]
    rows = [[f"{k}  {D.DESIGN[k]} / {D.DEPLOY[k]}",
             f"{d[k]['success_when_decision_correct']:.3f}  (n={d[k]['n_correct']})",
             f"{d[k]['success_when_decision_wrong']:.3f}  (n={d[k]['n_wrong']})"]
            for k in ["C1", "C2", "C3", "C4"]]
    T.render("fig23_decision_to_success",
             ["configuration", "success when the decision\nmatched the ideal", "when it did not"],
             rows,
             "Decision accuracy predicts success inside every configuration. The gap is widest\n"
             "on-device, where a wrong decision is close to fatal.",
             widths=[3.4, 2.9, 2.2])


if __name__ == "__main__":
    build()
