"""Figure 15 -- the compensation contrast, under both rules and both estimators.

Every row carries an interval, so a reader can see each one covering zero
rather than be told that it does. The lenient interval comes from
`runs/power_and_equivalence.json`, which resamples the same tasks under the
same seed; the third row's is the robust Wald interval on the model's own
scale, which is not the scale of the two above it.
"""
import json
from pathlib import Path
import _data as D, _table as T

ROOT = Path(__file__).resolve().parents[3]
REC = ROOT / "runs" / "full-2026-08-20"
POWER = ROOT / "runs" / "power_and_equivalence.json"


def build():
    r = json.loads((REC / "report.json").read_text(encoding="utf-8"))
    b, me = r["bootstrap"], r["mixed_effects"]
    len_ci = json.loads(POWER.read_text(encoding="utf-8"))["codings"]
    len_ci = len_ci["success_lenient"]["ci95"]
    # Robust Wald interval on the interaction. The test in the last column is
    # a score test, which is what statsmodels offers for a GEE; the interval
    # is the conventional +/- 1.96 se on the same robust standard error.
    g_lo = me["interaction_logodds"] - 1.96 * me["interaction_se"]
    g_hi = me["interaction_logodds"] + 1.96 * me["interaction_se"]
    rows = [
        ["Compensation, strict rule  (primary)", f"{b['point']:+.3f}",
         f"[{b['ci_low']:+.3f}, {b['ci_high']:+.3f}]", "—"],
        ["Compensation, lenient rule", f"{r['compensation_lenient']:+.3f}",
         f"[{len_ci[0]:+.3f}, {len_ci[1]:+.3f}]", "—"],
        ["GEE interaction (log-odds)",
         f"{me['interaction_logodds']:+.3f}  (se {me['interaction_se']:.3f})",
         f"[{g_lo:+.3f}, {g_hi:+.3f}]", f"p = {me['interaction_p']:.2f}"],
    ]
    T.render("fig15_compensation", ["", "estimate", "95% interval", "test"], rows,
             "n = 960 runs over 48 tasks. Interval from 5,000 resamples of tasks with all repetitions\n"
             "attached. GEE: binomial, exchangeable working correlation, clustered on task;\n"
             "generalized score test.",
             widths=[4.2, 2.2, 2.0, 1.2], align=["l", "r", "r", "r"],
             emphasize=(0,))


if __name__ == "__main__":
    build()
