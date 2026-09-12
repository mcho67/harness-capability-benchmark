"""
The naturalness measure: two automatic proxies, and the blind human pass
that says whether the proxies mean anything.

Protocol §6d makes this the **exploratory** measure — appendix-only, and
forbidden from carrying any conclusion. It is the least defensible thing in
the study and is included for completeness, so the honest way to build it is
to make it as hard as possible to inflate. Three ways that is done here:

1. **The canned-opener list is written before any results exist**, in this
   file, dated. A list assembled after reading transcripts is a description
   of the transcripts, not a measure of them.
2. **One rating item, not a battery.** A single 1-5 question. More items
   would mean more chances for one of them to reach significance, in the one
   measure that is not allowed to conclude anything.
3. **The rater cannot see the cell, and cannot recover it from the order.**
   Rows are exported under an opaque id, shuffled by a logged seed, and the
   id-to-row key stays behind in a separate file the rater never receives.

The human ratings' role is fixed in advance too: they **validate the
proxies** — confirm the automatic numbers track human perception — rather
than carry a claim of their own (§6d, §9).

Named `rate.py` rather than the `rate_export.py` / `rate_import.py` of the
original build list: export and import share the blinding scheme, and
splitting them across files is how the two halves drift apart.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ── the pre-registered canned openers ────────────────────────────────────
#
# Written 2026-08-19, before any scored transcript was read. A reply is
# "formulaic" if it begins with one of these, case-insensitively, after
# stripping leading punctuation and whitespace.
#
# The list is assistant-boilerplate: openers that acknowledge rather than
# answer. It is deliberately short and general. Adding an entry after seeing
# results is forbidden; if one is ever added, it is dated here and the whole
# measure is recomputed from the raw logs so that no number is ever a mix of
# two definitions.
CANNED_OPENERS = (
    "sure", "certainly", "of course", "absolutely", "no problem",
    "i'd be happy to", "i would be happy to", "happy to help",
    "great question", "good question", "let me", "i'll help",
    "i can help", "as an ai", "i'm sorry, but", "i apologize",
    "here's", "here is", "okay,", "ok,", "alright,",
)

RATING_SCALE = (1, 5)
RATING_QUESTION = ("How natural does this reply sound as something a person "
                   "would say out loud? 1 = stilted or robotic, "
                   "5 = indistinguishable from a person.")


def _first_words(text: str, n: int = 6) -> str:
    stripped = (text or "").strip().lstrip("\"'`*-—– \t\n")
    return " ".join(stripped.split()[:n]).lower()


def formulaic_opening(reply: str) -> bool:
    head = _first_words(reply)
    return any(head.startswith(o) for o in CANNED_OPENERS)


def length_fit(reply: str, expected: Optional[List[int]]) -> Dict[str, Any]:
    """Reply length against the task's pre-set band.

    The band is per task and was written with the task, so this is not a
    "shorter is better" measure — it is fit to what the request called for.
    Both the categorical verdict and the raw count are recorded: the verdict
    is what §6d reports, and the count lets a different band be applied later
    without re-running anything.
    """
    words = len((reply or "").split())
    if not expected or len(expected) != 2:
        return {"words": words, "fit": "unbanded", "expected": None}
    lo, hi = expected
    fit = "in_band" if lo <= words <= hi else ("under" if words < lo else "over")
    return {"words": words, "fit": fit, "expected": [lo, hi]}


def naturalness_proxies(reply: str,
                        expected: Optional[List[int]]) -> Dict[str, Any]:
    fit = length_fit(reply, expected)
    return {
        "formulaic_opening": formulaic_opening(reply),
        "length_words": fit["words"],
        "length_fit": fit["fit"],
        "length_expected": fit["expected"],
    }


# ── the blind export ─────────────────────────────────────────────────────

def _rating_id(row: Dict[str, Any], salt: str) -> str:
    """An opaque id the rater sees instead of a run id.

    Salted with a per-export secret so two exports of the same run get
    different ids: a rater who did an earlier pass must not be able to match
    rows across passes and infer anything from the pairing.
    """
    payload = f"{salt}|{row.get('run_id', '')}|{row.get('repetition', '')}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def export_for_rating(scored_path: str, tasks_path: str, out_csv: str,
                      key_path: str, *, seed: int = 20260819,
                      sample: int = 0, salt: str = "") -> int:
    """Write the rater's CSV and the key file that stays behind.

    The two files are separate on purpose and only the CSV is ever sent
    anywhere. `docs/harness.md` §7 requires every cell and model field
    stripped before rating; here the rater's file is *built* from a fixed
    field list rather than filtered from the row, so a new row field cannot
    leak by being forgotten.
    """
    from .capture import read_rows

    with open(tasks_path, "rb") as fh:
        tasks = {t["id"]: t for t in json.loads(fh.read().decode("utf-8"))}

    rows = [r for r in read_rows(scored_path) if not r.get("error")]
    rng = random.Random(seed)
    salt = salt or f"{seed}"

    if sample and sample < len(rows):
        rows = rng.sample(rows, sample)
    rng.shuffle(rows)

    os.makedirs(os.path.dirname(os.path.abspath(out_csv)) or ".", exist_ok=True)
    key: Dict[str, Dict[str, Any]] = {}

    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["rating_id", "conversation", "reply",
                         "naturalness_1_to_5", "notes"])
        for row in rows:
            rid = _rating_id(row, salt)
            if rid in key:                      # pragma: no cover
                raise ValueError(f"rating id collision on {rid}")
            task = tasks.get(row["task_id"], {})
            convo = "\n".join(f"user: {t}" for t in (task.get("turns") or []))
            writer.writerow([rid, convo, row.get("reply", ""), "", ""])
            key[rid] = {"run_id": row.get("run_id"),
                        "cell": row.get("cell"),
                        "task_id": row.get("task_id"),
                        "repetition": row.get("repetition")}

    with open(key_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"question": RATING_QUESTION, "scale": list(RATING_SCALE),
                   "seed": seed, "n": len(key), "key": key},
                  fh, indent=2, ensure_ascii=False)

    return len(key)


def import_ratings(filled_csv: str, key_path: str, scored_path: str,
                   out_path: str, *, rater: str = "r1") -> int:
    """Join a completed rating sheet back onto the scored rows.

    Every check here exists because a rating pass is the one step a human
    does by hand, and a hand step that fails quietly is worse than one that
    fails loudly:

    - an unknown `rating_id` means the sheet does not belong to this key
    - a duplicate means a row was rated twice, which would double-weight it
    - a value outside the scale means a typo, not a rating
    - blank is allowed and stays blank; guessing at an unrated row would
      invent data
    """
    with open(key_path, encoding="utf-8") as fh:
        key_doc = json.load(fh)
    key = key_doc["key"]
    lo, hi = key_doc.get("scale", list(RATING_SCALE))

    ratings: Dict[str, Dict[str, Any]] = {}
    with open(filled_csv, encoding="utf-8", newline="") as fh:
        for line in csv.DictReader(fh):
            rid = (line.get("rating_id") or "").strip()
            if not rid:
                continue
            if rid not in key:
                raise ValueError(
                    f"rating_id {rid!r} is not in {key_path}. This sheet was "
                    f"produced by a different export.")
            if rid in ratings:
                raise ValueError(f"rating_id {rid!r} appears twice")
            raw = (line.get("naturalness_1_to_5") or "").strip()
            if not raw:
                continue
            try:
                value = int(float(raw))
            except ValueError:
                raise ValueError(f"{rid}: {raw!r} is not a number")
            if not lo <= value <= hi:
                raise ValueError(f"{rid}: {value} is outside {lo}-{hi}")
            ratings[rid] = {"value": value,
                            "notes": (line.get("notes") or "").strip()}

    by_run = {key[rid]["run_id"]: v for rid, v in ratings.items()}

    from .capture import read_rows
    written = 0
    with open(out_path, "w", encoding="utf-8", newline="\n") as out:
        for row in read_rows(scored_path):
            rating = by_run.get(row.get("run_id"))
            merged = dict(row)
            merged.setdefault("ratings", {})
            if rating:
                merged["ratings"][rater] = rating
            out.write(json.dumps(merged, ensure_ascii=False) + "\n")
            written += 1

    print(f"imported {len(ratings)} ratings from {rater} -> {out_path} "
          f"({written} rows, {written - len(ratings)} unrated)")
    return len(ratings)


__all__ = ["CANNED_OPENERS", "RATING_QUESTION", "RATING_SCALE",
           "naturalness_proxies", "formulaic_opening", "length_fit",
           "export_for_rating", "import_ratings"]
