"""
The harness: orchestrate, capture, score, analyze.

Kept apart from `arms/` and `core/` because it is the only part that knows
which cell is running. Nothing under `arms/` or `core/` can see a cell label
— which is what makes "the two arms saw the same instrument" structural
rather than promised — and nothing here reaches inside an arm to adjust it.

The data path is one-way and each step writes a new file (CHARTER §7):

    run_cell.py  ->  runs.jsonl
    score.py     ->  scored.jsonl      (cell-blind)
    rate_*.py    ->  rated.jsonl       (rater-blind)
    analyze.py   ->  figures/
"""

from __future__ import annotations

from .analyze import analyze, print_report
from .capture import RunLog, RunRow, baseline_commit, read_rows
from .judge import BlindCase, Judge
from .run_cell import CELLS, CellSpec, load_tasks, run_cell
from .rate import export_for_rating, import_ratings, naturalness_proxies
from .score import score_decision, score_log, score_success

__all__ = ["RunLog", "RunRow", "read_rows", "baseline_commit",
           "CELLS", "CellSpec", "run_cell", "load_tasks",
           "Judge", "BlindCase", "score_log", "score_success", "score_decision",
           "export_for_rating", "import_ratings", "naturalness_proxies",
           "analyze", "print_report"]
