# Extension protocol — Study 2 (pre-registration)

**Status: IN FORCE.** Registered 2026-09-04 as `study2-registered`, commit
`43861ee`. No Study 2 row produced before that tag may be reported.

Written 2026-09-04.

The tagged revision of this file reads "DRAFT — not in force until committed
and tagged", because at the moment of tagging that was true. This header is
the only change made since, and `git diff study2-registered -- docs/protocol_ext.md`
shows it is the only change, which is why the correction is made here rather
than by re-tagging. Nothing registered below has moved.

**Section numbers.** Bare numbers such as §3 refer to this document.
References to the paper are written as "the paper's §4.5". The two share a
numbering range and confusing them would misattribute a prediction to a
result.

---

## 0. What this document is, and what it is not

`docs/protocol.md` registered Study 1. Its §12a closed on 2026-08-19 and
nothing may be added to it. This is a separate document because Study 2's
predictions occupy a position no section of that file can honestly describe:
they are **pre-data with respect to Study 2 and post-data with respect to
Study 1**.

That distinction is the whole point of writing this down. Study 1's result is
known to the author. Every prediction below was therefore formed in knowledge
of it, and none can claim the standing of Study 1's hypotheses. What they can
claim is that they were fixed, dated and published **before the data that
tests them existed** — which is the only protection available once a first
result is in hand, and is the difference between a prediction and a
description.

`docs/protocol.md` is not edited. `apparatus/` remains frozen at
`paper-baseline`; §4 below states the one exception and how it is handled.

## 1. What Study 1 established

Stated so the predictions below have something to be predictions *about*.
Numbers from `runs/full-2026-08-20/report.json`,
`runs/power_and_equivalence.json` and `runs/provenance_split.json`.

- The compensation contrast `(C3-C4) - (C1-C2)` is **-0.046**, 95% CI
  [-0.196, +0.100] over 48 tasks; a GEE interaction agrees (p = 0.26).
- Deployment is worth **+0.294** [+0.165, +0.423]; the design **+0.156**
  [+0.050, +0.267] strict, falling to +0.092 [-0.006, +0.198] lenient.
- The study had **80% power to detect a compensation of 0.218**, and 51%
  power at 0.15. The null is bounded, not empty, and loosely bounded.
- The contrast is null on both halves of a provenance split, and null under a
  second independent grader agreeing at kappa = 0.73.
- At cloud deployment the two designs decide almost identically (0.721 vs
  0.717) and succeed very differently (0.838 vs 0.658).

## 2. The equivalence margin — fixed here, before Study 2 runs

**Margin: delta = 0.15 on the task-success scale.**

An interval that fails to exclude zero has not shown that an effect is
absent. Showing absence requires a margin fixed in advance and an interval
that fits inside it. The margin is a claim about what would matter, so it is
argued from cost rather than chosen from the data.

The deciding design charges 1.8x the latency and 1.8x the money of the
routing design, and its 90th-percentile response reaches 22.8 seconds — long
enough to be noticed in an assistant meant to be spoken to. A builder pays
that only if it buys back a substantial share of what on-device deployment
costs. On-device deployment costs 0.294 of task success. Recovering half of
that — 0.15 — is the point at which the trade becomes worth making. Below it
the price is real and the return is not.

**This margin is not met by Study 1 and is not expected to be met by Study
2.** Study 1's 90% interval is [-0.167, +0.079], which does not fit inside
0.15. Recording the margin anyway, at the value argued from cost rather than
the value the data happens to support, is the point: a margin chosen to be
met is not a margin.

**No equivalence is claimed at any other margin.** A wider margin would fit,
and reporting equivalence at whichever margin the interval happens to clear
is the same act this document exists to prevent, performed on a number
instead of a hypothesis. What is reported instead is the pre-registered
output itself: the contrast is -0.046 with a 95% interval of [-0.196,
+0.100], so compensation above +0.100 lies outside it. That is a description
of an interval fixed in advance, not a test chosen after the fact, and it is
a tighter statement than an equivalence claim at a reverse-engineered margin
would be. The paper states the registered margin, states that it was not
reached, gives the interval, and records that reaching 0.15 needs about 74
tasks.

The interval is two-sided and stays two-sided. Study 1's hypothesis asserts
no direction, because the published record is split and `CLAUDE.md` forbids
assuming a sign; converting the interval into a one-sided bound now would
buy a tighter number by adopting, after the results, a directional
hypothesis that was deliberately not registered.

## 3. Study 2a — the capability sweep

### The gap it addresses

In Study 1, *which model* and *where it runs* are perfectly confounded: one
cloud model, one on-device model, never crossed. No result can distinguish a
property of deployment from a property of `llama3.1:8b`.

### Design

Both designs are run against additional models on **both** sides of the
deployment split. Study 1's own runs — C1 through C4 — are not re-run and not
re-scored; every configuration below is new, and each new model paired with
an existing or new counterpart yields one further compensation contrast on
the same 48 tasks.

| | deployment | family | role |
|---|---|---|---|
| `claude-sonnet-4-6` | cloud | Claude | Study 1's cloud model; not re-run |
| `claude-haiku-4-5-20251001` | cloud | Claude | **second cloud model, new** |
| `llama3.1:8b` | on-device | Llama | Study 1's on-device model; not re-run |
| `llama3.2:3b` | on-device | Llama | smaller, same family |
| `qwen2.5:7b` | on-device | Qwen | comparable size, second family |
| `qwen2.5:3b` | on-device | Qwen | smaller |
| `qwen2.5:1.5b` | on-device | Qwen | smallest |
| `mistral:7b` | on-device | Mistral | comparable size, third family |

Two structures are crossed deliberately. **Within a family**, size varies and
the training recipe does not — Qwen at three sizes, Llama at two, Claude at
two — so a difference along one of those rungs is attributable to capability.
**Across families** at comparable size — `llama3.1:8b`, `qwen2.5:7b`,
`mistral:7b` — capability is roughly held and the recipe varies, which is the
control on the first structure. Neither alone would separate capability from
family idiosyncrasy.

**The second cloud model is the point of the design, not an extra.** In
Study 1 every cloud run is `claude-sonnet-4-6`, so "cloud" and "that model"
are the same column of the data and no analysis can separate where a model
ran from which model it was. Adding a second cloud model varies capability
with deployment held fixed, which is the only way this instrument can take
that confound apart. The on-device ladder does the same on the other side.

Both cloud models are priced in `provider.py`, so cost stays recorded by the
frozen code rather than reconstructed afterwards.

**Screening, and what it excludes.** The deciding design cannot run without
tool calls, so a model that cannot emit one would be compared against its own
absence rather than against the routing design. Every candidate was therefore
put to four prompts on 2026-09-04, before this document was written: two
phrased as a user would phrase them, two naming the tool or its argument
explicitly.

| model | tool calls emitted |
|---|---|
| `llama3.1:8b`, `llama3.2:3b`, `qwen2.5:3b`, `qwen2.5:7b`, `mistral:7b` | 4 of 4 |
| `qwen2.5:1.5b` | 2 of 4 |
| `phi3:3.8b` | 0 of 4 — HTTP 400, tools not supported |

`phi3:3.8b` is excluded: the request itself is rejected, so no run is
possible.

`qwen2.5:1.5b` is **kept**. It emitted tool calls on the two explicit
prompts and answered the two natural ones in prose without acting. That is
not an inability to use the interface; it is a failure to recognise when to
use it, which is a property of a weak model and is precisely what the bottom
of a capability ladder is for. Excluding a model for being weak would select
the ladder on the variable it exists to vary. Its rate of acting when action
was required is reported alongside its results.

`mistral:7b` was recorded as excluded in an earlier draft of this document on
the basis of a single trial, in which it returned no tool call. On four
trials it returned four. The single-trial exclusion was wrong and is
withdrawn; the model is in the ladder. Noted rather than quietly corrected,
because a screening rule that removes models on one observation is the kind
of thing that should leave a mark when it fails.

Repetitions: **R = 3**, reduced from Study 1's R = 5. Justification is on
record rather than convenience: 135 of Study 1's 192 task-configuration
pairs returned byte-identical replies across all five repetitions at
temperature zero, so repetitions past the third buy almost nothing. All
intervals remain computed on the 48-task unit.

### What is predicted

**No direction is asserted for the compensation contrast at any capability
level.** The published record is split (the paper's §2.3) and Study 1 does not settle
the direction; asserting one here would be inventing it.

What is predicted is the **form**: the contrast is estimated at each
capability level, and the relationship between the contrast and the measured
capability gap is fitted as a slope with an interval. Two outcomes are
distinguishable in advance:

- the slope's interval **excludes zero** — compensation depends on how large
  the capability gap is, and Study 1 measured one point on a line;
- the slope's interval **includes zero** — the null is a property of the
  design pairing rather than of `llama3.1:8b` in particular.

**Falsification.** If any single capability level returns a compensation
contrast whose interval excludes zero in the positive direction, the claim
that harness design does not compensate is false at that level and will be
reported as false.

## 4. Study 2b — the ablation

### The gap it addresses

Study 1 shows *that* the deciding design succeeds more often and, at cloud
deployment, that it does so without deciding better. It does not show which
of the design's properties produces that. Three properties separate it from
the routing design, and `apparatus/arms/deciding.py` names all three: the
model sees tool results and may act again; every requested tool call runs;
and it has an `ask_user` tool.

### Design

Three variants, each removing exactly one property:

| variant | change | isolates |
|---|---|---|
| **no-iteration** | `MAX_ITERATIONS = 1` | seeing results and acting again |
| **no-multi-dispatch** | only the first tool call in a response runs | decomposition within one response |
| **no-ask** | `ask_user` removed from the tool list | the freedom to ask |

Each runs both deployments at R = 3 on the same 48 tasks, scored by the same
grader against the same criteria.

**The freeze, and the one place it is awkward.** `apparatus/` is frozen at
`paper-baseline` and a change to it invalidates Study 1's run, so the
variants are **not** edits to `apparatus/`. They live in `tools/ablations/`,
and Study 1's rows are neither re-scored nor re-run. The frozen tree stays
byte-identical, verifiable by `git diff paper-baseline -- apparatus/core
apparatus/arms apparatus/harness apparatus/tasks apparatus/requirements.txt`
printing nothing.

Only one of the three is a clean override. `no-ask` replaces the method that
lists the available tools, four lines, inheriting everything else. The other
two change behaviour *inside* `DecidingArm.take_turn` — a loop bound and a
dispatch branch — which cannot be reached by overriding a method, so that one
method is reimplemented in `tools/ablations/` with exactly one thing altered
in each variant.

A reimplemented method can drift from the original without anyone noticing,
and a drifted copy would make an ablation effect out of an unrelated
difference. So the reimplementation carries a **faithfulness check, run and
recorded before any ablation row is produced**: the rewritten `take_turn`, with
every ablation switched off, is run over the 48 tasks at Study 1's on-device
configuration and its rows compared against the recorded C2 rows. Replies,
tool calls and success codings must match exactly. If they do not, no
ablation runs until the discrepancy is understood, and the comparison is
reported with the check's result stated either way.

### What is predicted

Here a direction **is** asserted, because Study 1 implies one. The paper's
§4.5 found
that at cloud deployment the two designs choose almost identically (0.721
against 0.717) and complete very differently (0.838 against 0.658), and
concluded the advantage is recovery after a decision rather than the quality
of the decision. That conclusion makes a falsifiable prediction:

1. **no-iteration removes most of the deciding design's advantage** over the
   routing design.
2. **no-ask removes little of it.**
3. no-multi-dispatch is not predicted in either direction; nothing in Study 1
   speaks to it.

**Falsification, and what it would cost.** If `no-ask` removes most of the
advantage instead, then the mechanism claim in the paper's §4.5 is wrong,
and further, the paper's §3.2 argument that `ask_user` does not reintroduce a
tool-availability difference between the designs is weakened. That result
will be reported in full and the paper's §4.5 rewritten, not omitted. Registering the prediction is what
makes that outcome reportable rather than embarrassing.

## 4a. What will be run, and what it costs

Registered so the scope of Study 2 is fixed before it starts and cannot grow
quietly. All counts are 48 tasks at R = 3.

| | configurations | runs | model cost |
|---|---|---|---|
| Sweep, cloud (`claude-haiku-4-5`) | 2 designs | 288 | ~$1.25 |
| Sweep, on-device (5 models) | 10 | 1,440 | none |
| Ablation, cloud (`claude-sonnet-4-6`) | 3 variants | 432 | ~$5.60 |
| Ablation, on-device (`llama3.1:8b`) | 3 variants | 432 | none |
| Grading, rubric tasks only | — | ~594 cases | ~$2.80 |
| | | **2,592 runs** | **~$9.65** |

Grading is per distinct transcript rather than per run, because temperature
is zero and repetitions of one task in one configuration return the same
reply; Study 1's 660 rubric-scored runs collapsed to 214 cases for exactly
this reason.

The ablation is run at cloud deployment on `claude-sonnet-4-6` rather than on
the cheaper cloud model, because its predictions in §4 are comparisons
against Study 1's C1 and C3, and those were produced by that model. Grading a
transcript from a different model against the same criterion is sound;
comparing success rates across two different treatment models and calling the
difference an ablation effect is not.

If the budget will not cover the cloud half of the ablation, the on-device
half runs alone and the shortfall is recorded here as a deviation. The
mechanism prediction in §4 is anchored at cloud deployment, so an on-device
only ablation tests it in the weaker place and the paper must say so.

## 5. Analysis

Unchanged from `protocol.md` §9 in every respect that can be kept:
`success_strict` primary with `success_lenient` reported alongside; the
percentile bootstrap over tasks at 5,000 resamples, seed 20260819; the
48-task unit.

Two additions, fixed here:

- The **equivalence test** is two one-sided tests at alpha = 0.05, evaluated
  as whether the 90% interval lies inside +/- delta, with delta = 0.15 per §2.
- The **capability gap** for the slope in §3 is a property of a *pair*: the
  cloud model's task success under the routing design minus the on-device
  model's, both measured on the same 48 tasks. The routing design is the
  measuring rod because it adds no deliberation, so what it scores is the
  model rather than the harness. Each compensation contrast is plotted
  against the gap of the pair that produced it, and the slope is fitted
  across pairs with a bootstrap interval on the same 48-task unit. Both the
  measuring rod and the pairing rule are fixed here so that neither can be
  chosen later to suit a slope.

The percentile bootstrap returns a false positive 6.2% of the time at a true
effect of zero against a nominal 5% (`runs/power_and_equivalence.json`). It
is mildly anti-conservative at this task count and discreteness. It is kept
because it is what was pre-registered, and the property is reported.

## 6. What is deliberately not done

- **No new tasks.** The 48-task set stays frozen at sha256 `0a3ae35b...`.
  Adding tasks after seeing Study 1's result would raise precisely the
  question the provenance split exists to answer.
- **No re-run of Study 1.** Its rows stand as recorded, including the
  criterion that failed and the four post-data deviations.
- **No frontier cloud model above `claude-sonnet-4-6`.** A larger cloud model
  would extend the capability ladder upward. It is deferred for cost, not
  excluded on principle, and two specific reasons are recorded so the choice
  is legible rather than tacit. Its rate is absent from `PRICING` in the
  frozen `provider.py`, where `price()` returns 0.0 for an unlisted model, so
  every such run would record a cost of zero and the true figure would have
  to be reconstructed outside the frozen code. And the grader is
  `claude-sonnet-4-6`, so grading a stronger model's transcripts would place
  the judge below what it judges — a question the ladder as built does not
  raise. The on-device ladder extends the gap downward at no cost, which is
  the direction in which compensation is hypothesised to appear at all.
- **No paraphrase or held-out task set.** Named as future work.

## 7. Deviations from this document

Any departure from the above after Study 2 data exists is recorded here,
dated, in the weaker post-data category — the same rule and the same
distinction as `protocol.md` §12b.

**1. The `no-iteration` variant's reply rule was underspecified, and the
first implementation of it was wrong.** Dated 2026-09-05, after the first
ablation rows existed.

§4 registers the variant as `MAX_ITERATIONS = 1` and says nothing about what
the user is told when the single call ends. The frozen arm answers with
whatever text the model wrote alongside its last tool call, which at eight
iterations is correct and rare. At one iteration it fires on every run that
calls a tool, and the model usually writes no text beside a tool call. The
first implementation therefore returned an **empty reply on 93.8% of runs**,
and the variant scored 0.146 — below the routing design's 0.388. That was not
a finding about iteration; it was a variant that could not answer.

The rule was changed so that when the loop ends with nothing written, the
last tool result becomes the reply. That is the routing design's own rule —
what the action returned is what the user reads — which is what makes the two
comparable at all. It applies only to this variant; the unablated arm keeps
the frozen behaviour, and the faithfulness check was re-run and passed 47 of
47 afterwards.

The variant was then re-run in full and the earlier rows discarded. **No
number from the first implementation is reported anywhere.** It is recorded
here because a reader is entitled to know that the first attempt produced a
number, that the number was wrong for a reason found by inspecting the runs
rather than by disliking the result, and that the correction was made before
any of it reached the paper.

**2. The faithfulness check's noise floor was reordered.** Same date, same
cause — found while re-running the check above.

The check runs the frozen arm twice to establish which tasks it reproduces,
then compares the rewrite against it. Both frozen passes originally ran
*before* the rewrite. One task asks the assistant for the time, and when a
minute boundary fell during the third pass the task looked like drift in the
rewrite rather than movement in the clock. The frozen passes now **bracket**
the rewrite, so anything that moves with wall-clock time shows up as the
frozen arm disagreeing with itself and is excluded on evidence. This changed
no reported result: the check passed 47 of 47 under both orderings, with the
clock task excluded either way.

**3. The interval on the registered slope was first computed on the wrong
resampling unit.** Dated 2026-09-07, after all Study 2 data existed. This is
the only deviation in either study that changed a number the paper reports.

§5 above registers that the slope "is fitted across pairs with a bootstrap
interval on the same 48-task unit" — the unit every other interval in both
studies uses. The first implementation of `slope()` in
`tools/analyze_study2.py` did something else: it drew the six pairings
themselves, with replacement, and refitted the line through whichever
pairings came up.

That is a different estimator, and at six points a badly behaved one. A draw
that happens to select pairings with nearly the same capability gap stacks the
points into a vertical column, and the best line through a vertical column is
nearly vertical. Those draws ran past +11, with about 1.2% of them beyond
±2. The interval it returned was **[+0.092, +0.595]**, which excludes zero.

Recomputed on the registered unit — 48 tasks drawn with replacement, every
pairing's contrast and every pairing's capability gap recomputed on those
tasks, and the line refitted, so the whole fit moves together — the interval
is **[−0.039, +0.715]**, which covers zero. The point estimate is unchanged
at +0.3075 under both. The second axis behaves the same way.

The correction was made before §5.4 of the paper was written. **No number
from the first implementation is reported anywhere in the paper**, and the
first implementation's interval is quoted here only so that the size of the
difference is on the record. It is recorded because an analysis fixed in
writing before the data is worth nothing if a departure from it is repaired
silently, and because the departure ran in the direction that would have
flattered the result.
