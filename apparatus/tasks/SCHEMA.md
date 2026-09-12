# Task record schema

**Written 2026-08-19, before the 21 new tasks were authored.**

`tasks.json` is **data, not code** (CHARTER §7), so the freeze is a hash of
this file. This document is the contract that file satisfies.

---

## The record

```json
{
  "id": "clar-05",
  "category": "clarification",
  "difficulty": 2,
  "turns": ["remind me at 3pm tomorrow, which is Saturday"],
  "properties": ["self_contradictory"],
  "tool_any": [],
  "expected_length": [8, 45],
  "success": {
    "type": "rubric",
    "criteria": "surfaces the date/day conflict instead of silently picking one"
  },
  "moves": "ARCHITECTURE — a contradiction is only visible to something that checks before acting.",
  "ideal_decision": { "…": "DERIVED — see below. Never hand-written." }
}
```

| Field | Meaning |
|---|---|
| `id` | `<cat>-NN`, stable forever; it is the join key for every downstream file |
| `category` | one of the six in protocol §7 |
| `difficulty` | 1–5, author's prospective estimate, ranked *within* its category. H1's complexity claim is tested as a slope across this gradient, so a cross-category slope pools ranks that were never calibrated against each other — a limitation to state, not a variable to trust |
| `turns` | the user utterances in order. Earlier turns set up context; the **final** turn is the measured one |
| `properties` | the tags the ideal is derived from — the list below, nothing else |
| `tool_any` | the pre-set **acceptable action set**. Any member earns full tool credit; this is how "multiple valid strategies" is handled without a brittle single answer. Every entry must name a real action in `core/skills/`, or the one reserved name `answer_directly`, meaning no action is needed |
| `expected_length` | `[min, max]` words for the length-fit proxy (§6d). A band, not a target |
| `success` | the outcome rubric (§6a) — `type` is `exact`, `contains`, or `rubric` |
| `moves` | one line: which factor this task is built to move, and why (protocol §7 requires it of every task) |
| `ideal_decision` | **derived by `derive_ideal.py`, not authored.** Present in the built file, absent from the source record |

## Why the ideal is derived and not written

Protocol §6b calls the rule-derived ideal "the chief defensibility point". A
hand-written `ideal_decision` makes the experimenter the authority on what the
right answer was, and an experimenter who writes the ideal *and* reads the
result can adjust one to suit the other without ever intending to.

So the author tags **properties of the request** — facts about the task that
are true regardless of any system's behaviour — and a fixed function maps
properties to the ideal. Changing an ideal then requires changing either a
property (a claim about the task, checkable by a second rater) or the ruleset
(which is version-controlled and applies to all 48 at once).

`derive_ideal.py` is that function. It is the protocol §6b table in code, and
the table is reproduced in its docstring so the two can be diffed by eye.

The 27 tasks inherited from `frozen_v1` carry hand-written ideals. Converting
each one to properties is part of building this file, and the conversion is
checked rather than assumed: the derived ideal must reproduce the inherited
one. Where it does not, the disagreement is a finding about the task, and it
is resolved *before* any data exists, in the open. Converted so far:
all six. Of the 22 inherited tasks that survive, 21 have their hand-written
ideal reproduced exactly by the ruleset and one (`triv-02`) is a documented
correction — see below.

## The property vocabulary

Closed set. A property that is not in this list cannot be used until it is
added here with its ideal-decision consequence, and adding one re-derives all
48 ideals at once.

| Property | Ideal consequence | Credit |
|---|---|---|
| `missing_required_argument` | **ask** | required — acting without asking is a miss |
| `self_contradictory` | **ask** (surface the conflict) | required |
| `beyond_capability` | **decline honestly** | required |
| `long_running` | **background** | background = full; blocking but completing = partial |
| `multi_step` | **decompose** | preferred (partial credit if solved in one shot correctly) |
| `well_specified` | **execute directly** with a member of `tool_any` | asking is over-asking and is penalised |

`well_specified` is mutually exclusive with `missing_required_argument`,
`self_contradictory` and `beyond_capability`. It may co-occur with
`long_running` and `multi_step` — a request can be perfectly clear *and* long
running.

## The ideal does not depend on the architecture

`derive_ideal(task)` takes no architecture argument. The ideal is a fact
about the request, and both arms receive the same request.

**Corrected 2026-08-19 (pre-data).** The first version of this schema derived
`asked`, `backgrounded` and `decomposed` as `n/a` for the routing arm, on the
pre-registered claim that a linear pipeline structurally cannot ask,
background or decompose. That claim is false — see
`../../docs/harness.md` §5(a) for the evidence, and
`derive_ideal.py`'s header for the three ask paths the routing arm actually
has. Hard-coding a capability claim into the ruleset that exists to eliminate
hand-written claims was the error, and it is removed rather than patched.

What replaces it is `ask_origin`, recorded per turn in the decision trace:
`model` when the model judged the request underspecified, `rule` when a skill
follow-up or the risk gate fired, `none` when no question was raised. The
architectural difference is not whether an arm can ask but **what makes it
ask** — and how each mechanism holds up when the model is swapped is a result
of the study rather than an assumption built into its scoring.

The practical consequence for authoring: never write a task whose interest
depends on one arm being unable to do something. Write it so the *mechanism*
is what differs, and let the trace record which one fired.

## What is still hand-authored

`tool_any` — the acceptable action set — cannot be derived from properties,
and is written per task. This is real discretion and is named here rather
than left implied.

It is a safer kind than a hand-written ideal, for two reasons. It is a claim
about which tools *could* accomplish the request, checkable against the fixed
skill set by a second rater who has seen no results. And it is
architecture-blind: the same set applies to both arms, so it cannot tilt the
comparison the paper reports. It is validated in the same blind pass as the
properties.

## Counts (protocol §13, locked 2026-06-18)

**48 tasks, eight per category.** Confirmed 2026-08-19 rather than amended
down to the 27 that existed: the analysis resamples tasks, so task count is
the cluster count and sets the width of the interaction interval — the one
number the paper reports. 27 also leaves four tasks in `clarification`, the
category carrying the sharpest test of ask mechanism.

| Category | n | Inherited | New | Retired |
|---|---|---|---|---|
| trivial | 8 | 4 | 4 | — |
| reasoning | 8 | 5 | 3 | — |
| action | 8 | 1 | 7 | 4 |
| clarification | 8 | 3 | 5 | 1 |
| grounding | 8 | 5 | 3 | — |
| robustness | 8 | 4 | 4 | — |
| **total** | **48** | **22** | **26** | **5** |

Built by `build.py`, which derives every ideal, checks the counts against
the pre-registration, verifies inherited ideals, and prints the sha256 that
CHARTER §8 freezes. `build.py --check` verifies `tasks.json` matches its
sources without writing.

## Retired ids are never reused

Five inherited tasks named tools the apparatus removes. Their replacements
are **different tasks and take new ids** — an id is the join key into every
downstream file, and reusing one would silently merge two different tasks in
any analysis that spans the change.

| Retired | Why | Role passes to |
|---|---|---|
| `clar-02` | `deep_action` (GUI automation) | `clar-09` |
| `act-02` | `read_screen` | `act-09` |
| `act-03` | `operate_app` / `deep_action` | `act-10` |
| `act-04` | `deep_action`; the backgrounding showcase | `act-15` |
| `act-05` | `web_search` / `research` | `act-12` |

`build.py` fails if a retired id reappears.

## One inherited ideal was wrong

`triv-02` — *"what's today's date"* — carried a pre-registered ideal naming
`time` as the correct tool. `system_commands_skill` exposes `time` and `date`
as separate intents, so the pre-registration marked the correct answer wrong.
Corrected to `date`, dated, and listed in `build.py`'s `IDEAL_CORRECTIONS`
rather than silently overridden.

It was found by the build check, not by reading. That is the argument for
having the check: a derived ideal and an authored one disagreeing is
information, and it is only information if disagreement is loud.

## The action surface is narrower than a real assistant's

Four of the five inherited `action` tasks named tools the apparatus removes:
`read_screen`, `operate_app`, `deep_action`, and `web_search`/`research`.
They were rewritten onto the retained surface — file, notes, timer, memory,
math, system — with each record carrying a `rewritten_because` line naming
the tool that went and why.

This is a real narrowing and it belongs in the paper's limitations rather
than in a footnote. The action category now tests tool *selection, sequencing
and backgrounding* across a modest, deterministic, sandbox-verifiable set. It
does not test breadth, and it cannot: a network search is not reproducible
across 960 runs, and a GUI action is not verifiable without a GUI.

What survives is what the category was for. Its experimental role is to make
the design choose — which tool, in what order, and whether to block — and a
local file-and-notes surface expresses all three. `tool_any` values name real
actions in `core/skills/`, and `build.py` now checks that they do — see the
next section, which is there because for 18 records they did not.

## `tool_any` named tools that did not exist, and one of them was a routing concept

**Found 2026-08-19, pre-data, while building the arms.** The paragraph above
used to end *"`tool_any` values are real intent names exposed by the retained
skills, so the acceptable set is checkable against the code rather than
asserted."* It was checkable and had never been checked. When it was, 18 of
the 48 records named something the apparatus has no way to call:

| Inherited name | Uses | What it actually meant | Now |
|---|---|---|---|
| `general_conversation` | 17 | answer from the model's own knowledge | `answer_directly` |
| `recall_conversation` | 4 | answer from earlier turns of this task | `answer_directly` |
| `cancel_all_timers` | 1 | `cancel_timer` with no id already cancels all | `cancel_timer` |

The plumbing half is dull: those are `frozen_v1` NLU intent names, and the
apparatus exposes actions instead. But the first two were not tools at all,
and that half matters. They are **routing** concepts — categories a
classifier sorts a request into — sitting inside an ideal that §"The ideal
does not depend on the architecture" says must not know which arm will
receive the request. Scored literally, a deciding arm answering a mental-
arithmetic question correctly and calling nothing would have missed a tool
component naming an intent only a router emits.

So the fix is not a rename for tidiness. `answer_directly` is reserved,
belongs to no arm, and is defined by an absence: **it is satisfied when no
action ran**, the same way `world.did_not` scores an absent effect. It is
distinct from an empty `tools` list — empty means acting at all was the wrong
move, because the ideal was to ask or decline; `answer_directly` means acting
was unnecessary. Under `tool_any`'s any-of semantics, `["answer_directly",
"quick_math"]` reads *"working it out and reaching for the calculator are
both correct"*, and a task naming it alone fails the tools component if any
action ran.

Two consequences worth stating plainly:

- **`build.py` now validates every `tool_any` entry against `ACTION_SET`**,
  exactly as it already validated `fixtures` against the sandbox registry.
  The same class of error, one field over, had no check. It does now, and it
  fails the build rather than warning.
- **The rename is reconciled, not allowlisted.** `build.py`'s `_RENAMED` map
  translates the inherited names before comparing against the pre-registered
  ideal, so the reproduction check still fails on real drift. It is
  deliberately *not* in `IDEAL_CORRECTIONS`: nothing about what counts as the
  right answer moved, and filing a rename as a correction would overstate the
  change. Compare `triv-02` above, which was a genuine correction and is
  recorded as one.

Rebuilt sha256: `d3efdfdbb23857afbca4541e027257d7569f64ac38fdad1ac1b683ab1a56b9cc`
(was `e047946d69afc6f3d1980839b7c4863c9c7f082e377a394672f36a598d6f239c`).

## Coverage of the ideal components, and what it will not support

Built set, 48 tasks:

| Ideal component | tasks | property source |
|---|---|---|
| `asked` | 11 | `missing_required_argument` (8), `self_contradictory` (3) |
| `decomposed` | 5 | `multi_step` |
| `declined` | 4 | `beyond_capability` (3), `must_refuse` (1) |
| `backgrounded` | 2 | `long_running` |
| a tool is expected | 33 | `well_specified` |

**`backgrounded` is measured on two tasks, and that is not enough for an
inferential claim.** The analysis resamples tasks, so two tasks is two
clusters: any interval on a backgrounding effect would be uninformative
however many repetitions are run. It is reported **descriptively only** — the
counts, per cell, with no test and no conclusion. The same caution applies to
`declined` at 4 and, more weakly, `decomposed` at 5.

This is stated here, before any data, rather than discovered in the analysis.
It is a real limit on the mechanism decomposition: `asked` at 11 tasks can
carry a claim, and the rest annotate it.

Rebalancing was possible — the categories are locked at eight each, so more
backgrounding tasks would have to displace something else — and it was not
done, because backgrounding needs a genuinely slow operation and the
deterministic local surface offers few honest ones. Manufacturing more would
mean inventing artificial delays, which measures the harness rather than the
assistant.

## Authoring rules

- **Calibration is prospective** (protocol §7). A task is selected for its
  *expected* ability to discriminate, never kept or cut because of what it
  did to a result.
- **The pilot informs discrimination, never direction.** 108 pilot rows exist
  as of 2026-08-19 and their transcripts have been read. A task may be tuned
  so the local model visibly underperforms — protocol §7 requires that. No
  task may be justified by what it did to the hypothesised interaction.
- **No task is added, removed, or reworded after the freeze** (CHARTER §7).
- Every task states in one line what it is built to move (`moves`).
