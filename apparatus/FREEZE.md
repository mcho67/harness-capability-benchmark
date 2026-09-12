# The apparatus is frozen — `paper-baseline`

**Frozen 2026-08-19, after Pilot M4 cleared the validity gate**
(tag: `paper-baseline`; `docs/protocol.md` §8.6, `CHARTER.md` §8)

This directory is the **instrument** the study runs on. `../frozen_v1/` is
the **provenance** — dated evidence that the full assistant existed at commit
`5cbd13e` — and nothing is run on it. The two are different objects with
different rules, and confusing them is the single easiest way to invalidate
this study.

```
git rev-parse paper-baseline^{commit}    # the commit this freeze names
git tag -n99 paper-baseline              # the pins, and what the gate said
git diff paper-baseline -- apparatus/core apparatus/arms     apparatus/harness apparatus/tasks apparatus/requirements.txt
```

That last command must print nothing for a run to count. **It names the
instrument directories rather than all of `apparatus/`, and the distinction
is load-bearing**: this file and `CHARTER.md` are *records about* the tree,
not part of it, and neither can change a number. The first draft of this
file said `-- apparatus/`, which would have made correcting a sentence in
this paragraph invalidate the study. Noted rather than quietly fixed,
because the scope of a freeze is exactly the kind of thing that should not
move silently — and because it moved within minutes of the tag, with no run
against it and no data in existence.

---

## The rule

> After this freeze, a change to `apparatus/` invalidates the run. There is
> no in-place fix. There is a new tree, a new tag, and a new run.

This is stricter than it sounds, and deliberately so. The gate that licenses
this freeze is the *pre-registered* response to a bad pilot: recalibrate the
task set, re-run the pilot, then freeze. Recalibrating **after** seeing the
full run is the same edit with none of the protection, and it is forbidden.
The freeze is what makes those two acts distinguishable from the outside.

Every data row carries its own `baseline_commit`, marked `-dirty` if the tree
had uncommitted changes when it ran. A dirty row is not automatically void —
Pilot M4's 192 rows are all dirty, because the pilot's whole job was to
provoke changes — but no row of the **full run** may be dirty, and that is
checkable from the data rather than from anyone's memory.

---

## What is frozen

| | |
|---|---|
| Instrument | `core/` (model seam, sandbox, 21 shared actions), `arms/` (28 and 40 code lines), `harness/`, `tasks/` — 4,577 lines across 29 files |
| Task set | `tasks/tasks.json`, 48 tasks, 8 per category × 6 |
| Task set sha256 | `0a3ae35b1ac8343b13880f01393b82960ff6bfe2e5c5927739424b623c1d85b3` |
| Cloud model | `claude-sonnet-4-6`, verified per call against the provider's own response |
| Local model | `llama3.1:8b`, ollama digest `46e0c10c039e0191…87ca666e`, gguf, Q4_K_M, 8.0B, ollama 0.17.1 |
| Analysis deps | pinned in `requirements.txt` — the interval and the test statistic depend on library versions |

Verify the task set and the hash together:

```
cd apparatus && python tasks/build.py --check
```

`--check` rebuilds every ideal from the task properties and compares the
result byte-for-byte with the committed file. It passing means the shipped
`tasks.json` contains no ideal that cannot be traced to a rule. It prints the
sha256, which must match the row above.

---

## What the freeze does **not** cover

- **`runs/`.** Data produced by the instrument, not part of it.
- **`docs/`.** The paper and the protocol keep being written. Amendments to
  `protocol.md` after this date are **post-data** and are held to a different
  standard — §12a is closed to new pre-data items from here.
- **`derive/`.** The import log and `FINDINGS.md` are the record of how this
  tree was built. They are append-only history, not instrument.
- **`CHARTER.md` and this file.** Records about the instrument. The charter
  says of itself that it is amended in the open, with a date, or the
  offending file is removed — a document with that rule was never frozen.

---

## The state this freeze certifies

Pilot M4, 2026-08-19: 192 runs (48 tasks × 4 cells × R=1), zero degraded
rows, $1.81, every category reached in every cell.

The validity gate returned **criterion not met, proceed yes**, on one
documented exception: local `clarification` success is 0.062, below the
0.15–0.85 band. The exception records what it forfeits — no architecture
claim within `clarification` at local deployment — and it cannot turn
`criterion_met` true, because a gate whose failures can be written away is
not a gate. The full text is in `harness/analyze.py` (`GATE_EXCEPTIONS`) and
in `docs/protocol.md` §12a item 8.

**No number from the pilot is a result.** R=1.
