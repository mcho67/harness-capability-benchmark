# Apparatus charter

**Written 2026-08-19, before anything was copied into this directory.**

That order is the point. A charter written after the trim describes what was
kept; a charter written before it constrains what may be kept. This document
exists to answer one question a judge is entitled to ask:

> *Did you shape the apparatus until it gave you the result you wanted?*

The answer has to be a rule that was fixed in advance, applied mechanically,
and logged. That rule is §3.

---

## 1. What this is, and what it is not

This directory is the **instrument of one controlled experiment**: two
assistant designs (routing, deciding) crossed with two model deployments
(cloud, local), over one fixed task set.

It is **not** a product, not a demo, and not a snapshot of one. It is
derived *from* a complete working assistant by removing everything the
experiment does not exercise.

**Why it is not called `frozen_v2`.** `frozen_v1/` is a snapshot: the product
copied whole at a commit, deliberately unselective, because a hand-picked
copy would have been silently incomplete. This directory is the opposite
operation — a deliberate reduction, built for the protocol rather than
inherited from the product. Calling it a second freeze would misdescribe it
and would imply the product moved, which is not why it exists.

**What `frozen_v1/` is for from now on: provenance.** It stays, unedited, as
dated evidence that the full assistant existed at commit `5cbd13e` and that
this apparatus is a reduction of a real system rather than a prototype
written for a paper. That distinction is load-bearing — the paper's §1
criticises research prototypes for being too narrow to stand in for a real
assistant, and this apparatus has to answer that criticism about itself.
`frozen_v1` is the answer, and it only works if it is never touched.

## 2. The structure, and the guarantee it encodes

```
apparatus/
  core/          identical for both arms — the held-constant half
    llm/         the provider seam (anthropic | ollama); one call path
    skills/      the fixed action set BOTH arms reach
    memory/      conversation context + retrieval
    metrics/     latency, cost, degradation
  arms/
    routing.py   classify -> one skill -> respond      (single pass)
    deciding.py  perceive -> decide -> tool -> repeat  (the loop)
  harness/       orchestrate, run_cell, capture, score, analyze
  tasks/         tasks.json + rubrics
  derive/        HOW THIS TREE WAS DERIVED — evidence, not apparatus
```

`derive/` is not part of the instrument and is never imported by it. It holds
the reachability trace that produced the tree (`trace_cell.py`,
`trace_all.py`), its output (`import_log.json`), the keep/cut rule applied to
that output (`plan_tree.py`), and what the trace found wrong with the
snapshot (`FINDINGS.md`). It is checked in because §3's answer to *"did you
shape the apparatus until it gave you the result you wanted?"* is worthless
unless someone else can re-run it.

**The guarantee:** the two arms differ in *control structure and nothing
else*. They share one model interface, one action set, one task input, one
response path. Everything shared lives in `core/` precisely so that sharing
is structural rather than promised.

This is the study's advantage over the closest published comparison, whose
own first-listed limitation is that its baseline arm had different tools
available than the others, leaving loop structure confounded with tool
availability (`docs/related_work.md` §6). That confound is designed out here,
and `core/` is how.

**Two arms, one tree, not two folders.** Separate trees would let every
incidental difference — prompt wording, retry behaviour, response assembly,
error handling — ride along with the architecture variable. With one tree the
answer to *"how do you know the difference is the architecture and not that
you wrote one arm better?"* is a diff between two files. With two trees there
is no answer.

## 3. The inclusion rule (fixed in advance)

> **A module belongs here only if it is reachable on the path from finalized
> text input to final response.**

The experiment begins *after* transcription: input arrives as settled text.
Anything that cannot be reached from that entry point is not apparatus.

**The rule is applied dynamically, not by reading imports.** `FROZEN.md`
records why: the runtime imports lazily in several places (`__import__` in
reset paths, skills autodiscovery, in-function imports), so a hand-picked or
statically-traced module list is silently incomplete — which is exactly why
`frozen_v1` was copied whole. The procedure instead is:

1. Run the harness over the **full task set, both arms, both deployments**.
2. Record `sys.modules` after the complete pass.
3. What was imported is apparatus. What was never imported is removed.
4. **Keep the import log** as evidence, checked in beside this charter.

Anything kept that the log does not justify must be named here, individually,
with its reason.

**Amendment, 2026-08-19 (post-trace, pre-data): the log is a ceiling, not the
keep-list.** The trace ran and showed why the rule needs a second half. Skill
autodiscovery imports every file in `skills/action/`, so 29 action skills
appear in the log while the runs exercised 13 intents. Import is not use. The
keep-list is therefore the log narrowed twice — by §5 for skills, by §4's
reason classes for removed subsystems — and both narrowings apply identically
to both arms, because a cut that touched one arm only would rebuild the
confound §2 exists to prevent. `derive/plan_tree.py` applies them
mechanically and prints every cut with its reason.

## 4. What comes out, and why

Reasons are stated as classes, so the cut is a rule rather than a series of
judgement calls. Approximate scale, from the `frozen_v1` inventory:

| Removed | ~LOC | Reason class |
|---|---|---|
| voice, audio, TTS, end-of-turn, prosody | 9,366 | **pre-transcription** — before the experiment's entry point |
| tray, settings panels, setup wizard, overlay | 5,532 | **no surface** — no cell renders anything |
| screen reasoning, UI automation, recipe replay | ~6,000 | **unreachable + unreproducible** — deterministic side-effect checks are better evidence than driving a GUI |
| dev tooling (finetuning, voiceprints, diagnostics) | 2,811 | **not apparatus** — build-time utilities |
| vision, mood, personality, proactive, services | ~5,000 | **unreachable** from a task-driven text path |

**Amendment, 2026-08-19 (post-trace, pre-data): the size target was wrong.**
This section originally predicted 8–12k lines. The trace measured it: of the
snapshot's 295 modules and 95,659 lines, the running experiment reached 145
modules / 51,869 lines, and the narrowings in §3 and §5 leave **105 modules /
37,833 lines**. The estimate was out by roughly threefold and is corrected
here rather than quietly restated.

The gap is a handful of large files that are reachable as modules but
internally mostly unreachable — `main.py` alone is 2,923 lines, most of them
voice and overlay wiring no cell executes. Cutting *within* files by the same
mechanical standard would need line-level coverage, and deleting code because
one pilot did not execute it is not safe: a branch untaken in 108 runs may be
taken in 960. So **the module is the unit of the cut**, coverage is reported
rather than used as a deletion rule, and the original justification for the
number — "the author must defend this tree line by line" — is withdrawn. It
was the wrong standard. What must be defended is the scoped defensible
surface in `docs/plan.md`: the request path, the two designs, the model seam,
the harness, and the statistics. A 38,000-line instrument whose *reduction
rule* is mechanical and logged is more defensible than a 10,000-line one
assembled by judgement.

A side effect worth naming: removing the voice stack and the personality
layer takes most Tier 3 material (the end-of-turn fusion weights, the persona
text) out of the only tree a judge would ever see.

## 5. Skills earn their place by task category

Not by seeming necessary for a complete assistant — that is the "added for
realism" argument this project has already cut once. Each retained skill maps
to a **pre-registered task category** (`docs/protocol.md` §7):

| Category | Needs | Skill |
|---|---|---|
| Trivial | a one-step factual answer | system/time |
| Reasoning | chained inference | math, plus the model itself |
| Action | choose and use a tool | file, notes, timer, memory |
| Action (backgrounding) | a long task to dispatch | timer / long-running |
| Clarification | the ability to ask before acting | **no action** — asking does not touch the world, so it belongs to the control structure, not the shared set (amended 2026-08-19; see below) |
| Grounding | context carried across turns | conversation context + retrieval |
| Robustness | nothing extra | — |

Both arms reach this set identically. A skill available to one arm and not
the other reintroduces the confound §2 exists to prevent.

**Amendment, 2026-08-19 (pre-data).** The Clarification row read *"the ask
path (deciding arm only — the asymmetry is the finding)"*. That was the
withdrawn capability claim wearing a different hat, and it is corrected here
too.

Asking is now handled in two pieces, and the split is the point:

- **The rule-driven half is shared.** A `ToolSpec` declares its required
  arguments and `core.skills.dispatch` refuses to run without them, returning
  `needs` instead of guessing. Both arms get this identically. It reproduces
  the mechanism the pilot found in the routing arm — a skill returning
  `requires_followup` (`orchestrator.py:454`) — and it is recorded as
  `ask_origin=rule`.
- **The model-driven half lives in the arms**, because asking touches no
  part of the world and is therefore a property of control structure, not of
  the action set. Keeping it out is what lets the shared action set be
  *identical* rather than merely similar.

`core/skills/` accordingly exposes 21 actions and none of them is `ask_user`.
Clarification and Robustness contribute no actions at all — the first because
asking is structural, the second because it needs nothing extra, exactly as
the row below already said.

**Amendment, 2026-08-19 (pre-data).** The Action row read *"file, message,
timer"*. Messaging is removed — it is a network side effect, not verifiable
by a deterministic sandbox check, and §6.3 already moved action verification
in that direction. The row now reads *"file, notes, timer, memory"*, which
covers the same experimental role: choose a tool, sequence two, and decide
whether to block.

This forced four of the five inherited `action` tasks to be rewritten, since
they named `read_screen`, `operate_app`, `deep_action` and `web_search` —
all removed. Each rewritten record carries a `rewritten_because` line. The
resulting narrowing of the action surface is real and is stated as a
limitation in `tasks/SCHEMA.md`, not hidden.

**Adding a skill later requires a dated entry here** stating which category
demanded it. No skill is added because the assistant felt incomplete without
it.

## 6. Scope reductions to record as amendments

These change what the study can report and must be filed as **dated,
pre-data amendments** in `docs/protocol.md`, not applied silently:

1. **The voiced turn-taking subset is dropped** (protocol §13 item 5, §6d
   turn-taking row). It required the voice stack. It was exploratory,
   appendix-only, and forbidden from carrying a conclusion, so no result
   depends on it. The text-based naturalness proxies — formulaic-opening
   rate, length fit — survive unaffected.
2. **The personality layer is removed**, so conversational naturalness now
   measures the model's own register rather than a tuned persona. This is
   arguably cleaner for the measure, but it is a change in what is being
   measured and is recorded as one.
3. **Action verification moves from GUI automation to deterministic,
   sandboxed side-effect checks.** This resolves an open question
   (`docs/harness.md` §8 item 2) in the direction of reproducibility.

## 7. Standing rules for this directory

- **No per-task tuning.** No configuration, prompt, or threshold is adjusted
  in response to how a task scored.
- **No asymmetric improvement.** Any change that improves one arm must be
  applied to the other or reverted. If it cannot be applied to both, it is a
  change to the architecture variable itself and must be recorded as one.
- **No post-hoc task edits.** Tasks are fixed before the run; never added,
  removed, or reworded after results are seen.
- **The task set is data, not code** (`tasks/tasks.json`), so the freeze is a
  file hash rather than "whatever the code happened to do."
- **Raw data is immutable.** `runs → scored → rated → figures`; each step
  writes a new file and is re-runnable from the one before.

**Added 2026-08-19 after the trace** (`derive/FINDINGS.md` has the evidence
for each):

- **One model per cell, pinned at the seam.** No tier selection, no
  fast/smart routing, no fallback to a second model. The trace caught the
  deciding arm running Haiku 4.5 in the cell labelled Sonnet 4.6 while the
  routing arm ran Sonnet — architecture confounded with model identity, in
  the exact comparison the paper reports.
- **The model is recorded per call, from the provider's response**, never
  copied from the cell label. A cell label is an intention; the response is
  evidence. Every row carries what actually answered.
- **Nothing adaptive.** No mechanism whose behaviour depends on how earlier
  runs went — no self-disabling optimisation, no speculative second call, no
  cache warming, no precompute. These are removed, not switched off: a flag
  can be left in the wrong state, a deleted module cannot.
- **State is isolated at the task boundary.** A fresh store per task, paths
  injected. Context still carries *within* a task, because the grounding
  category depends on it (§5) — the boundary is the task, not the turn.
- **Nothing is written inside the instrument tree.** Every output path is
  injected and lands outside it.
- **Missing capability aborts the run.** A subsystem that cannot work must
  fail loudly. The trace ran with semantic retrieval silently inert and
  reported zero degradation events across 108 rows; rows that look complete
  while a measured capability is absent are worse than no rows.

**The test for an asymmetry between cells.** Cells will differ in what they
reach, and the difference is sometimes the result and sometimes a defect:

- **Structural** — a code path gated on the provider or the architecture
  (cache warming, tier selection, provider-specific drivers). This is an
  engineering artifact. **Remove it.**
- **Behavioural** — a path reached because the *model* did something another
  model did not. **This is the phenomenon under study. Measure it.**

Removing the behavioural kind would delete the finding; keeping the
structural kind would fabricate one. When a case is genuinely unclear, it is
recorded here with the reasoning before the run, not resolved afterwards.

## 8. Freezing

This tree is *built*, then *frozen* — it is not frozen on arrival.

- Freeze happens **after the pilot passes the validity gate**
  (`docs/protocol.md` §8), because the gate may legitimately require
  recalibrating the task set, and that recalibration must happen before the
  freeze rather than after it.
- The freeze is a **git tag** (`paper-baseline`) plus a recorded hash of
  `tasks/tasks.json`.
- Every data row carries its `baseline_commit`, so reproducibility is a
  property of the data rather than a claim in a document.
- After the freeze, a change to this tree invalidates the run. There is no
  in-place fix; there is a new tree, a new tag, and a new run.

---

*Written before the first file was copied. If this directory ever contains
something this charter does not permit, the charter is what is wrong and it
is amended in the open — with a date — or the file is removed.*
