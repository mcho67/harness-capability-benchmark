"""Figure 25 -- latency, cost and model calls per configuration."""
from collections import defaultdict
from statistics import mean, median
import _data as D, _table as T


def build():
    lat, cost, calls = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in D.load():
        lat[r["cell"]].append(float(r["latency_s"]))
        cost[r["cell"]].append(float(r.get("cost_usd") or 0))
        calls[r["cell"]].append(int(r["model_calls"]))
    def p90(v):
        s = sorted(v); return s[int(0.9 * len(s)) - 1]
    rows = []
    for k in ["C1", "C2", "C3", "C4"]:
        m = mean(cost[k])
        rows.append([f"{k}  {D.DESIGN[k]} / {D.DEPLOY[k]}",
                     f"{median(lat[k]):.2f} s", f"{p90(lat[k]):.2f} s",
                     (f"${m:.4f}" if m else "$0"), f"{mean(calls[k]):.2f}"])
    T.render("fig25_cost_table",
             ["configuration", "median\nlatency", "90th\npercentile",
              "mean cost\nper run", "model calls\nper run"], rows,
             "240 runs per configuration. On-device cost is zero by definition — the model runs on\n"
             "hardware already owned, and energy is not metered here.",
             widths=[3.4, 1.4, 1.5, 1.6, 1.7])


if __name__ == "__main__":
    build()
