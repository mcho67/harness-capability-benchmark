"""Figure 18 -- the two main effects and the four simple effects."""
import json
from pathlib import Path
import _table as T

REC = Path(__file__).resolve().parents[3] / "runs" / "full-2026-08-20"
LABEL = [("deployment", "Deployment (cloud − on-device)"),
         ("architecture", "Design (deciding − routing)"),
         ("arch_at_cloud", "Design at cloud"),
         ("arch_at_local", "Design on-device"),
         ("depl_in_deciding", "Deployment within deciding"),
         ("depl_in_routing", "Deployment within routing")]


def build():
    m = json.loads((REC / "main_effects.json").read_text(encoding="utf-8"))["marginal_effects"]
    rows = [[lab, f"{m[k]['point']:+.3f}",
             f"[{m[k]['ci_low']:+.3f}, {m[k]['ci_high']:+.3f}]"] for k, lab in LABEL]
    T.render("fig18_effects", ["effect", "estimate", "95% interval"], rows,
             "Marginal and simple effects, on the same resampling unit as Figure 15.",
             widths=[3.6, 1.5, 2.2], emphasize=(0, 1))


if __name__ == "__main__":
    build()
