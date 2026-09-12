"""Figure 22 -- asks, failures to ask, and where each question came from."""
import csv
from collections import Counter, defaultdict
from pathlib import Path
import _data as D, _table as T

CSV = Path(__file__).resolve().parents[3] / "runs" / "full-2026-08-20" / "runs.csv"
TRUE = ("True", "true", "1")


def build():
    c = defaultdict(Counter)
    with open(CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            k = r["cell"]
            if r["over_asked"] in TRUE:  c[k]["over"] += 1
            if r["under_asked"] in TRUE: c[k]["under"] += 1
            if r["ask_origin"] == "model": c[k]["model"] += 1
            if r["ask_origin"] == "rule":  c[k]["rule"] += 1
    rows = [[f"{k}  {D.DESIGN[k]} / {D.DEPLOY[k]}", c[k]["over"], c[k]["under"],
             c[k]["model"], c[k]["rule"]] for k in ["C1", "C2", "C3", "C4"]]
    T.render("fig22_asks",
             ["configuration", "asks when it\nshould not", "fails to ask\nwhen it should",
              "model-written\nasks", "rule-fired\nasks"], rows,
             "Counts over 240 runs per configuration. The deciding design's characteristic error is\n"
             "over-asking; the routing design's is under-asking.",
             widths=[3.0, 1.7, 1.8, 1.9, 1.6])


if __name__ == "__main__":
    build()
