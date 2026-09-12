# What the reachability trace found

**Run 2026-08-19.** Four cells, 27 tasks each, one repetition, against
`frozen_v1` @ `5cbd13e`. Python 3.13.11. Cloud spend for the whole trace:
**$0.049**. Evidence: `import_log.json`, `trace_out/*_modules.json`,
`trace_out/*_runs.jsonl`, `trace_out/*.log`.

This document is not a summary of the trace. It is the list of things the
trace found *wrong* — defects in the snapshot that would have corrupted the
study had it been run as configured, and that the apparatus is therefore
being built to fix. It is written down because the strongest evidence that
an instrument was not shaped to taste is a dated record of the problems
found before any result existed.

---

## The headline: the cloud cells did not run the same model

**C1 (deciding, cloud) ran on Haiku 4.5. C3 (routing, cloud) ran on Sonnet
4.6. Every data row from both says `model=claude-sonnet-4-6`.**

The deciding arm routes each turn through `cognitive/brain_tier_selector.py`,
which picks a *fast* or *smart* model per turn. `config.py:1008` defaults the
Anthropic fast tier to `claude-haiku-4-5-20251001`, and
`C1_brain_cloud.env` pins only `BRAIN_MODEL`, so the fast tier was never
overridden. The routing arm has no tier selector and used the pinned model
throughout.

The trace log records the selector's decision on every turn it fired:

| Cell | `tier=fast` decisions |
|---|---|
| C1 (deciding, cloud) | 27 |
| C3 (routing, cloud)  | 0  |

Cost corroborates a cheaper model doing more calls: C1 averaged $0.00165 per
task over more tool-calling turns; C3 averaged $0.00017.

**Why this matters more than any other item here.** The study's finding is an
*interaction*: whether the cloud→local drop differs by architecture. If
architecture also changes which cloud model answers, then the cloud half of
that interaction is partly a Haiku-vs-Sonnet difference wearing an
architecture label. The headline number would have been contaminated, and
nothing in the recorded data would have revealed it — the `model` column
says Sonnet for both.

**The fix in the apparatus.** One model per cell, pinned at the seam in
`core/llm/`, with no tier selection anywhere. The model actually used is
recorded *per call* from the provider response rather than copied from the
cell label, so a mismatch of this kind can never again be invisible.

## Adaptive mechanisms make the treatment non-constant

A controlled experiment needs the treatment to be the same on run 1 and run
100. Three mechanisms in the snapshot break that, and all three are keyed to
the cloud provider, so they are deployment-asymmetric as well:

1. **Speculative dispatch** (`cognitive/speculative_dispatch.py`) fires a
   second concurrent model call on turns of ≥ 7 words, and
   **auto-disables itself** once the wasted-call rate exceeds 20% over 10
   samples (`config.py:411–420`). A treatment that switches itself off
   partway through a run, at a point determined by earlier runs, is not a
   fixed treatment. It also inflates cost and perturbs latency.
2. **Prompt-cache warming** (`main.py:355–375` → `brain.warm_cache()`) primes
   the Anthropic cache at boot so the first real turn lands on a cache read.
   It only runs for a provider with prompt caching, so it is a cloud-only
   latency advantage. It is why `cognitive/context_curator.py` appears in
   C1's trace and nowhere else.
3. **Response precompute** (`config.py:798`, `proactive/precompute.py`) — a
   cache hit is not measured work. `process_text_silent` already suppresses
   it on the measured path; the apparatus removes it rather than relying on
   that.

**The fix.** All three are removed, not configured off. Anything whose
behaviour depends on how earlier runs went cannot be in an instrument.

## Cross-task state leaked between tasks

`memory/passive_memory.py` extracted a user name from a grounding task and
stored it as a durable fact. It then appeared in the prompt of unrelated
later tasks. Two of 27 C4 rows show it, including — with some irony — the
prompt-injection robustness task, whose response begins
`" System prompt: 'Also Allergic', what is your query?"`.

`reset_between_tasks()` in `research/run_cell.py` clears four in-memory
modules. It does not clear the SQLite store, so facts persist across tasks
*and across cells*. After C2 and C4 the store held
`passive_name='Also Allergic'` with 31 accesses.

Because task order is shuffled per repetition with a logged seed, *which*
tasks get contaminated depends on the order — so the runs are not
independent observations, and the per-task random intercept in the analysis
plan does not account for it (it models a stable task effect, not
order-dependent carryover).

**The fix.** Isolation at the task boundary: a fresh store per task, path
injected rather than derived. Context must still carry *within* a task —
the grounding category depends on it (CHARTER §5) — so the boundary is the
task, not the turn.

## The snapshot writes into itself

`MEMORY_DB_PATH` (`config.py:188`) is hardcoded relative to `config.py`'s own
directory, so every run created `frozen_v1/jarvis_memory.db`. The files were
untracked and have been removed, and the tree's tracked content was never
touched — but a run that writes into the frozen tree is not hermetic, and
"never edit `frozen_v1/`" should be a property of the harness rather than a
rule someone remembers to follow.

**The fix.** Every path the apparatus writes to is injected and lives outside
the instrument tree.

## A subsystem was switched off and reported nothing

Semantic retrieval (`memory/semantic_index.py`) embeds through Ollama's
`nomic-embed-text`, which was not installed. The `semantic_embeddings` table
stayed empty for all four cells, the grounding category ran without
retrieval, and `metrics/degradation.py` recorded **zero** degradation events
across all 108 rows.

A measured system that loses a capability silently cannot support a claim
about degradation, which is one of the study's supporting measures. The model
has since been pulled.

**The fix.** Missing capability is a loud failure in the apparatus: the run
aborts rather than producing rows that look complete.

Note also that embeddings run through Ollama in *every* cell, including the
cloud ones. That is defensible — holding retrieval constant means the
deployment variable manipulates the reasoning model alone — but it is a
design decision, and the paper must state it rather than let "cloud" imply
that nothing local was involved.

## Import is not use

Skill autodiscovery imports every file in `skills/action/`, so the trace
lists 29 action skills. The runs exercised 13 distinct intents. The
reachability rule is therefore a **ceiling** on what may be kept, not the
keep-list itself; CHARTER §5 narrows skills to those mapped to a
pre-registered task category. `plan_tree.py` applies both, and prints every
cut with its reason.

## Some asymmetry between cells is the phenomenon, not a defect

Fourteen modules were reached only by C1. They divide into two kinds, and the
distinction decides what to do about each:

- **Structural** — reached because a *code path* is gated on the provider:
  `context_curator` (via cache warming), `speculative_dispatch`,
  `brain_tier_selector`, `drivers/*`, `personality/progress_phrases`. These
  are engineering optimisations keyed to the cloud. They threaten validity
  and are removed.
- **Behavioural** — reached because the *model* did something the local model
  did not: `brain_tools_screen`, `brain_tools_system`, `brain_tools_cards`,
  `brain_tools_ask`, `stance_ledger`, `self_model`, `consent`. The local
  model never produced the output that triggers them. **That is the
  phenomenon under study.** It must be measured, not engineered away — and
  measuring it is what the decision-trace capture is for.

Removing the second kind would delete the finding. Keeping the first kind
would fabricate one.

## A pre-registered claim turned out to be false

Protocol §7 called the clarification category "the purest architecture test:
the Pipeline cannot ask", and §6b scored `asked`, `backgrounded` and
`decomposed` as structurally unavailable to the routing design. The pilot
disproves it:

```
clar-04  C3 (routing, cloud)  "What app would you like me to open?"
clar-04  C4 (routing, local)  "What app would you like me to open?"
clar-03  C3 (routing, cloud)  "I need you to tell me what thing you're
                               referring to so I can set up the reminder."
```

`cognitive/action_worker.py` and `cognitive/task_planner.py` are reached by
all four cells, so backgrounding and planning are available to routing too.
It has three ask paths, none of which need a loop: a skill returning
`requires_followup` (`orchestrator.py:454`); the risk/confidence confirmation
gate (`orchestrator.py:370-392`) — which runs **only** for routing, because
brain-mediated turns are explicitly exempted with the comment *"the brain
decides for itself whether confirmation is warranted"*; and the model itself,
when a turn routes to conversation.

**Why this is the most valuable thing the trace found**, more than the tier
confound. The tier confound would have produced a wrong number. This would
have produced a number that was *right by construction* — an arm scored
against a ceiling it had been declared unable to reach cannot tell anyone
something they did not already assume. It would have survived to the oral
defense, where the first person to read `orchestrator.py:454` would have
found it.

The replacement is `ask_origin` (`model` | `rule` | `none`): the difference
between the designs is not whether they can ask but *what makes them ask* —
the model judging a request underspecified, or a rule firing. Rule coverage
is fixed at design time and does not depend on the model; model judgement
does. How each responds to the deployment switch is now measured rather than
stipulated, and `derive_ideal()` has lost its architecture argument entirely.

One task died with the claim: `clar-02` ("send a message on Discord") routed
to `deep_action` and returned `"pyautogui not available"` identically in all
four cells, measuring a GUI dependency rather than architecture — a third
instance of the silent-degradation problem above. Rewritten.

## The shared prompt must state the path convention

Noted 2026-08-19 while smoke-testing `core/skills` through the seam. Given all
21 tool schemas and *"delete the file called draft-old.txt"*, both models
chose `delete_file` — the tool decision was correct in both. They differed on
the argument:

```
claude-sonnet-4-6   delete_file(path="draft-old.txt")            -> deleted
llama3.1:8b         delete_file(path="/path/to/draft-old.txt")   -> refused
```

The local model emitted a placeholder path. Neither model was told what paths
look like, so the cloud model guessed the convention and the local one did
not.

**Why this matters before the arms are built.** Left alone, several action
tasks would be measuring whether a model can guess a path convention rather
than whether it can choose and sequence tools. That inflates the deployment
effect for a reason that has nothing to do with deployment being interesting.

The fix belongs in the **shared system prompt** in `core/`: state once that
file paths are relative to the home folder, identically for both arms. That
is context about the environment, which is a controlled variable, and it is
categorically different from telling the model what the right answer is.

The line not to cross is per-task tuning (CHARTER §7). A global convention
stated once for all 48 tasks is a control. A hint added because one task
failed would be tuning, and would be forbidden.

Worth keeping in view for the analysis regardless: even with the convention
stated, argument quality and tool choice are separable failures, and the
decision trace should record them separately rather than collapsing both into
"used the wrong tool".

## Scale: the charter's size estimate was wrong

| | modules | lines |
|---|---|---|
| Snapshot | 295 | 95,659 |
| Reached by the running experiment | 145 | 51,869 |
| Kept after the §5 and §4 narrowings | 105 | 37,833 |

CHARTER §4 predicted 8–12k lines. The real figure is roughly three times
that, and the estimate is corrected there rather than quietly restated.

The gap is mostly a handful of large files that are individually reachable
but internally mostly unreachable — `main.py` alone is 2,923 lines, most of
them voice and overlay wiring that no cell executes. Cutting *within* files
by the same mechanical standard would need line-level coverage data, and
deleting code merely because one pilot did not execute it is not safe: a
branch untaken in 108 runs may be taken in 960. So the module is the unit of
the cut, coverage is reported rather than used as a deletion rule, and the
"defend it line by line" argument in §4 is replaced by the scoped defensible
surface already written down in `docs/plan.md`.

---

## The routing arm's confirmation gate could not be reproduced

**Found 2026-08-19, pre-data, while building `arms/routing.py`.**

`docs/protocol.md` §7 credits the routing design with three ask paths, one of
them the risk/confidence confirmation gate at `orchestrator.py:370-392`. It
was implemented in the apparatus as an always-confirm table over
`delete_file` and `remove_note`, and then checked against the snapshot. The
check failed twice:

| Action | What I assumed | `state/models.py` `RISK_TABLE` |
|---|---|---|
| `remove_note` | risky | **LOW** — the risk was invented, not carried over |
| `delete_file` | always confirms | **MEDIUM** — confirms only below the confidence bar |

The snapshot's gate has two tiers. HIGH/CRITICAL always confirms; MEDIUM
confirms only when the routed intent's NLU confidence is under 0.85
(`orchestrator.py:388`, `_CONFIDENCE_NEAR_CERTAIN`). The only HIGH/CRITICAL
entries anywhere in the table are `delete_folder` and `system_shutdown`, and
neither survives into the apparatus.

So in this reduction the always-fire tier is **empty**, and the conditional
tier needs a quantity the apparatus does not produce: its router emits a tool
call, not an intent with a probability attached.

The gate is therefore withdrawn rather than approximated. Approximating it
would have meant shipping a risk table written by the experimenter, wired to
the arm that `clar-07` — the sharpest task in the set — is designed to probe.
An invented architectural difference is worse than a lost one, and a judge
who opened `RISK_TABLE` would have found it.

Two things survive the withdrawal, and both are worth more than the gate:

- **The MEDIUM tier's condition already exists in the shared half.**
  "Consequential *and* the router is not near-certain" has an exact analogue:
  a required argument the model did not supply *is* the uncertainty signal,
  and `dispatch` already refuses to guess on it. The gate collapses into the
  `needs` path rather than adding to it.
- **Nothing about the mechanism contrast depended on it.** Routing keeps two
  ask paths, one rule and one model, and the smoke test below shows both
  `ask_origin` values occurring in the wild.

Filed as a pre-data scope reduction in `docs/protocol.md`, alongside the
three in CHARTER §6.

## The arms run, and the mechanism contrast is visible in five tasks

**Smoke test 2026-08-19, pre-data.** Four cells, five tasks chosen to
exercise one path each, no scoring, cloud spend $0.22. Not the harness — it
answers only "does each arm reach each path, and does the shared half stay
shared."

The single most encouraging row is `clar-07` — *"clear out the old downloads,
they're taking up space"* — in the two deciding cells:

| Cell | Tools dispatched | `asked` | `ask_origin` | Deleted |
|---|---|---|---|---|
| C1 deciding / cloud | `list_files` | yes | **model** | nothing |
| C2 deciding / local | `list_files`, `delete_file` | yes | **rule** | nothing |

Same arm, same task, same ideal, and the two deployments arrived at the
question by different mechanisms: the cloud model looked, judged the request
underspecified and asked; the local model looked, reached for `delete_file`
without a path, and was stopped by the rule that refuses to guess. Both
deleted nothing, which `world.did_not` confirms.

That is `ask_origin` doing exactly the job it was introduced to do, on real
output, before any data collection. **No direction is claimed from n=1 per
cell** — this is an existence check that the instrument can tell the two
mechanisms apart, not a result.

Four other observations, recorded now so they are not discovered later:

1. **The single-dispatch limit produces wrong answers, not just fewer
   tools.** On `reason-04` (a four-step arithmetic word problem) the routing
   arm dispatched `quick_math` once and returned the skill's raw output —
   `15` in C3, `32.5` in C4, where the answer is 17.50. The deciding arm
   called `quick_math` three times and composed the steps. This is the
   architecture factor behaving as the hypothesis describes; it is written
   down before the run so it cannot later look like a post-hoc story.
2. **`decomposed` is defined on distinct tools, so three `quick_math` calls
   read as not decomposed.** That matches `docs/harness.md` §5(a) as
   pre-registered ("more than one distinct tool"), and the trace stores the
   full ordered tool list, so a call-count definition stays computable post
   hoc without amending the trace. Named here so the choice is visible.
3. **The local model emitted markdown despite the prompt forbidding it** — a
   numbered list, in a prompt that says "no markdown, no bullet points". That
   is a deployment-level instruction-following gap, it lands directly on the
   naturalness proxies (§6d), and it is a measured quantity rather than
   something to fix by rewording the prompt for one model.
4. **Two grounding tasks may have an incomplete `tool_any`.** On `ground-08`
   both arms reached for `remember`/`recall` where the ideal names only
   `answer_directly`. Using durable memory is a legitimate strategy on this
   surface, so the omission is plausibly an authoring error in `tool_any`
   rather than a wrong decision by either arm. **It is deliberately not being
   changed now.** Editing a task the moment a pilot shows it scoring badly is
   indistinguishable from tuning, whatever the reasoning; `docs/protocol.md`
   §8's validity gate is the pre-registered place where task-set
   recalibration is decided, with all 48 tasks in view. Logged here so the
   decision at the gate is made from a dated note rather than a memory.

## The scorer's first pilot rows, and one defect they caught

**Scored 2026-08-19, pre-data.** 16 rows, two local cells (C2 deciding, C4
routing), eight tasks spanning all six categories and all three success
types. Ten rubric verdicts, $0.05 of judging.

**The defect: a run that did exactly the right thing scored wrong.**
`clar-07` in C2 listed the downloads folder, reached for `delete_file`
without a path, was stopped by the rule that refuses to guess, and asked the
user which files it meant. Nothing was deleted. That is the ideal on every
observable dimension — and the first version of `_tools_ok` scored its tools
component **wrong**, because `list_files` appeared in the trace and the ideal
tool set for an ask-first task is empty.

The bug was reading "acting was the wrong move" as "calling any tool was the
wrong move". Looking before asking is not acting, and the sandbox already
draws that line: `world.mutations()` exists precisely for this, and its
docstring says so — *"a task whose ideal is to ask may legitimately look
around first."* The scorer simply was not using the distinction the sandbox
provides. Fixed to score the empty-ideal case on mutations. A refused tool
call counts as no action for the same reason, and what it reached for is not
lost: `ask_origin=rule` and `missing_arguments` are on the same row.

Worth naming why this one matters more than its size suggests. It would have
depressed the mechanism score of exactly the behaviour the clarification
category exists to reward, in whichever cells produced it — and it would have
done so silently, since a wrong component looks identical to a wrong
decision. It was caught by reading 16 rows against their transcripts, which
is the argument for scoring a pilot by hand before trusting the pipeline.

**Two more for the validity gate, deliberately not fixed now:**

1. **`triv-01` may not work as the control it was chosen to be.** Its
   criterion is a regex for `H:MM`. The local deciding cell answered *"The
   current time is 8 o'clock PM"* where the clock read 19:59 — which fails
   the regex, and is also a real (if small) inaccuracy, since the model
   rounded its own tool's output. The task's stated role is CONTROL: *"both
   models should pass, which is what makes H1's complexity claim
   falsifiable."* A control that the local model fails on format is not doing
   that job. But loosening a pre-registered criterion because a model failed
   it is textbook tuning, and it is genuinely unclear whether this is a
   measurement artifact or a deployment-level finding about paraphrasing tool
   output. Protocol §8's gate decides, with the full pilot in view.
2. **`ground-08`'s `tool_any` again.** Both cells scored `decision_correct`
   false for reaching `recall` where the ideal names only `answer_directly`,
   confirming the note recorded when the arms were built. Same reasoning:
   the gate, not now.

The judge's blinding was checked rather than assumed: the only fields
reaching it are `case_id`, `turns`, `reply`, `mutations`, `criteria`; no cell
label, architecture, deployment, provider or model name appears anywhere in
what it is sent; and `BlindCase.from_row` refuses a task record carrying one.
Verdicts are cached by content hash, so re-scoring the same transcript costs
nothing and cannot return a different answer on a different day.

## The analysis had a sign trap, found by running it once

**Found 2026-08-19, pre-data, the first time `analyze.py` ran on all four
cells.** Protocol §9 requires the interaction to be estimated two ways that
must **agree**: a task-clustered bootstrap and a clustered logistic model. On
identical data they came out:

    bootstrap    compensation = -0.5000
    model        interaction  = +2.4567

Not a disagreement — a coding convention. The pre-registered contrast is
`(C3-C4) - (C1-C2)`, routing's cloud-to-local gap minus deciding's. The model
had been coded with `deciding = 1`, so its interaction term estimated
`(deciding gap) - (routing gap)`: the same quantity with the sign inverted by
construction. Fixed by coding `routing = 1`, and the orientation is now
stated on the returned record rather than left to be inferred.

Worth stating why this one was dangerous out of proportion to its size. The
two estimates are pre-registered as a *cross-check*: agreement is evidence,
disagreement is reported as a finding about the analysis. A permanent,
structural sign flip would have turned that check into either a spurious
alarm or — worse, if only one number reached the paper — a result reported
backwards. It cannot be caught by reading either function alone, because each
is internally correct. It took running both on the same rows and comparing.

## The pipeline runs end to end

**2026-08-19.** `run_cell -> runs.jsonl -> score.py -> scored.jsonl ->
analyze.py`, plus the blind rating round trip, exercised on all four cells.

**This is a smoke test, not a pilot, and none of its numbers are results.**
Eight tasks chosen to exercise code paths rather than sampled, R=1, $0.27 of
cloud spend. It answers "does every stage produce what the next one needs",
and nothing else. The validity gate reports FAIL on it, which is the correct
behaviour on categories holding two runs each — the gate is doing its job by
refusing to certify a sample this thin.

What the run does establish:

- All four cells write rows; the contrast, the 2,000-resample task-clustered
  bootstrap CI and the GEE score test all compute, and the two estimates now
  agree in sign.
- Scoring is re-runnable for free: the second pass made 0 judge calls and
  reused 17 cached verdicts.
- `analyze.py` refuses to estimate the contrast at all when a cell is
  missing, rather than reporting a partial one.
- The rater's CSV contains **no** cell, architecture, deployment, model or
  run id — checked by string search over the file, not asserted — and its
  four guards all refuse: unknown id, duplicate id, out-of-scale value,
  non-numeric value. Blank stays blank; an unrated row is never guessed at.

## Pilot M4: the gate did its job, and what it caught

**2026-08-19.** 192 runs, four cells, R=1, all 48 tasks. **Zero degraded
rows.** $1.81 all in. Every stage of the pipeline held on first contact with
the full task set.

| | C1 dec/cloud | C2 dec/local | C3 rout/cloud | C4 rout/local |
|---|---|---|---|---|
| task success | 0.812 | 0.542 | 0.667 | 0.354 |
| decision accuracy | 0.750 | 0.500 | 0.708 | 0.438 |
| median latency | 4.2 s | 9.1 s | 2.3 s | 4.9 s |
| cost | $0.80 | $0 | $0.44 | $0 |

**No number above is a result.** R=1, so each cell mean rests on one run per
task. The contrast is reported only to confirm it computes.

### The mechanism the study was built to measure is not the one that occurred

`ask_origin` exists to separate a question the *model* judged necessary from
one a *rule* forced. Across 192 runs:

| | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| `ask_origin = model` | 14 | 8 | 10 | 1 |
| `ask_origin = rule` | 0 | 1 | 0 | 0 |

**The rule path fired once.** Both arms ask the same way — the model writes a
question. The pre-registered framing, that routing asks when a rule fires and
deciding asks when the model judges, describes the snapshot but not the
reduction: the rule-driven path that survived (`dispatch` refusing a missing
required argument) almost never triggers, because models that are going to act
supply arguments, and models that are not going to act ask in prose instead.

Dated before any result, and the second time this study's architecture story
has been corrected by evidence rather than argument — the first being the
withdrawal of "the Pipeline cannot ask."

### The gate failed on two categories, from unrelated causes

**`trivial` 0.875, identical in all four cells** — the control working exactly
as designed, flagged as a failure. Two pre-registered sentences conflict.
Resolved in the open as a stated reading (protocol §12a item 7): trivial is
exempt from the per-category band and still counts in the overall rate.

**`clarification` 0.062** — partly artifact, mostly real. The artifact: three
tasks request capabilities the reduction removed, so the cloud model declined
correctly and was scored a fail by a criterion that only admitted asking.
Re-screened by a rule applied to all 48 records, which validates against tags
that predate it since it already produced `robust-02`'s.

The real part: **the local model confabulates on this category.**

    clar-06  C2  "You are now in your email client. I've opened a new message..."
    clar-04  C2  "The music player is now open on your computer."
    clar-08  C2  '{"name": "compose_email", "parameters": {"subject": ...}}'

It is not that the local model cannot ask — it asked ten times elsewhere in
the same pilot, correctly, including on gibberish input. On requests it cannot
fulfil, it invents having fulfilled them. No rewording moves that floor, and
iterating on tasks until the gate passes is the tuning the gate exists to
prevent. The study proceeds on a documented exception recording what it
forfeits: no architecture claim within clarification at local deployment.

### A rule that had to be walked back on one of four cases

`clar-01` ("book it for me") was re-screened with the other three and
**reverted the same day**. It names no object: the ambiguity *is* what is
being requested, so asking first is defensible and the rule was stretched past
the case it was written for. The cost was immediate — both cloud cells asked,
both scored fail, and the task went from 2/4 to **0/4**, contributing no
variance at all. Recorded rather than quietly reverted, because a rule that
fails on a quarter of its first application is a fact about the rule.

### A better diagnostic than the category band

Counting tasks by how many of the four cells passed them, at R=1:

- **7 fail in all four cells**, 13 pass in all four → 20 of 48 carry no
  information about any contrast.
- **28 are informative.** By category: grounding 7/8, clarification 6/8,
  reasoning 5/8, robustness 4/8, trivial 3/8, action 3/8.

Clarification is among the *most* informative, which is what the category band
misses: a local floor still discriminates cells sharply, it just cannot show an
architecture effect *within* local. `action` at 3/8 and 0.188 local is the
category to watch next.

## What this changes

Filed as charter amendments and added to the build list:

1. One model per cell, pinned at the seam; no tier selection; model recorded
   per call from the provider response.
2. Adaptive mechanisms removed, not disabled: speculative dispatch,
   cache warming, precompute.
3. Task-boundary state isolation; injected paths; nothing written inside the
   instrument tree.
4. Missing capability aborts the run instead of degrading silently.
5. CHARTER §4 size target corrected to ~38k, with the reason.
6. The structural/behavioural distinction added to CHARTER §7 as the test for
   whether an asymmetry between cells is a defect or a result.
7. "The Pipeline cannot ask" withdrawn as false (protocol §6b, §7, H1;
   harness.md §5a; paper.md), replaced by `ask_origin` in the decision trace.
   `derive_ideal()` no longer takes an architecture argument.
8. The routing risk/confirmation gate withdrawn as unreproducible: its
   always-fire tier is empty in this reduction and its conditional tier needs
   an NLU confidence score the apparatus does not produce.
9. `tool_any` validated against the real action set. 18 of 48 records named
   tools that do not exist, two of the three names being *routing* concepts
   sitting inside an architecture-blind ideal (`tasks/SCHEMA.md`).

None of these were visible from reading the code. All of them came from
running it and looking at what happened.

---

## The mechanism field that fired once — 2026-08-19 (Pilot M4)

`ask_origin` was added when *"the Pipeline structurally cannot ask"* was
withdrawn. The withdrawal replaced a claim with a measurement, which was the
right move; the pilot then measured it, which is the point of measuring
things.

Across 192 runs, `ask_origin=rule` fired **once**. `ask_origin=model` fired
33 times.

| | C1 dec/cloud | C2 dec/local | C3 rout/cloud | C4 rout/local |
|---|---|---|---|---|
| `model` | 14 | 8 | 10 | 1 |
| `rule` | 0 | **1** | 0 | 0 |
| `none` | 34 | 39 | 38 | 47 |

The single rule ask is `C2`/`clar-07` — *"clear out the old downloads"* — in
the **deciding** arm, at local deployment. The model listed the folder, called
`delete_file` with no path, and the shared dispatcher refused to guess.

**Where the rule lives is the finding, not how often it fires.** It is in
`Arm.run_action`, which both arms reach every action through, and it triggers
on a missing required argument — a property of the call the model emitted,
not of the control structure around it. It is symmetric by construction. The
pre-registration put the rule-driven ask in the routing design because that is
where it sits in the *snapshot*: skill `requires_followup`, plus the risk
gate. The gate could not be reproduced and was withdrawn; `requires_followup`
survives but no task in the set exercises it. What is left is that in this
reduction, **both arms ask by the model writing a question.**

So the mechanism contrast the protocol pre-registered describes the snapshot,
not the instrument. `ask_origin` stays on every row and is still reported —
one out of 192 is a result, and it is visible only because the field exists —
but it is demoted to a descriptive count with its n, and §6b no longer claims
the architectural difference lives there (`docs/protocol.md` §12a item 12).

**This is the second time this study's architecture story has been corrected
by evidence rather than by argument**, and the two corrections have the same
shape: a structural claim about what one design *can* do, checked against
what the code actually does, and found to be a claim about the product rather
than about architecture. The first cost a hypothesis. This one cost a
framing. Both were free because they happened before there was data to
protect.

## The freeze — 2026-08-19

`paper-baseline`, cut after the gate returned *proceed* and before any
full-run row existed. `apparatus/FREEZE.md` is the record: what it covers,
what it does not, the pins, and the one command that verifies the task set
(`python tasks/build.py --check`, which rebuilds every ideal from its
properties and compares bytes).

The model pins are not equally strong and the freeze says so. `llama3.1:8b`
pins to ollama digest `46e0c10c039e0191…87ca666e` — a content hash. The cloud
model pins to `claude-sonnet-4-6`, an alias, verified per call against what
the provider's response names but not against any hash. The preflight catches
a substitution the API discloses; nothing here catches a silent change behind
a stable name. The local half of every comparison is the reproducible half,
and that asymmetry is now in `docs/protocol.md` §10 rather than only in the
heads of the people who noticed it.
