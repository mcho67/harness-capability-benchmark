"""Figure 7 -- six of the 48 tasks, one from each category.

Chosen to span the difficulty range and to show the two shapes a task can
take: a single request, or several turns where something said early is needed
later. Two of them are the examples the paper returns to — the downloads
request from §1.1, and the task §3.6 uses for a run that lands between done
and not done.

Read verbatim from `apparatus/tasks/tasks.json`; the full set is Appendix A.
"""

import json
import textwrap
from pathlib import Path

import _table as T

TASKS = Path(__file__).resolve().parents[3] / "apparatus" / "tasks" / "tasks.json"
PICK = ["triv-01", "reason-05", "act-13", "clar-07", "ground-01", "robust-04"]


def build():
    raw = json.loads(TASKS.read_text(encoding="utf-8"))
    ts = {t["id"]: t for t in (raw["tasks"] if isinstance(raw, dict) else raw)}
    rows = []
    for i in PICK:
        t = ts[i]
        req = t["turns"][0]
        if len(req) > 62:
            req = textwrap.fill(req, 62)
        turns = "1" if len(t["turns"]) == 1 else f"{len(t['turns'])}"
        rows.append([t["category"], f'"{req}"', str(t["difficulty"]), turns])
    T.render("fig07_task_sample",
             ["category", "the request", "difficulty", "turns"], rows,
             "Six of the 48, one from each category. Difficulty is ranked within a category, so a 5\n"
             "in one is not a 5 in another. Every task also carries what counts as success and the\n"
             "factor it was written to move; the full set is in Appendix A.",
             widths=[1.7, 6.8, 1.4, 0.8], align=["l", "l", "r", "r"])


if __name__ == "__main__":
    build()
