# Research protocol — the JARVIS 2×2 study (pre-registration, DRAFT)

> **Status:** DRAFT v0.1 (2026-06-18). This is the pre-registration of the
> experiment: hypotheses, variables, task set, and analysis plan are fixed
> *before* data is collected, so the result can't be massaged after the
> fact. **Open decisions are in §13 — lock those, then we freeze the
> baseline (`paper-baseline` tag) and run the pilot.**
>
> **Tier 2** — this methodology becomes the paper's *Methods* section. It
> describes mechanisms at the functional level and reproduces no Tier-3
> internals (persona text, fusion weights, recipe internals) per
> [private/disclosure.md](private/disclosure.md). The dated invention record is
> [private/provenance.md](private/provenance.md).

---

## 0. Aim, definitions, and how we grade — read this first

> **In one breath.** People want their AI assistant to run *on their own
> device* — it's private, cheap, and works offline. The catch: the models
> small enough to run locally are *weaker* than the giant ones in the cloud.
> This study asks one question and answers it with hard numbers: **how much
> do you actually lose by going local — and can a smarter *design* win most
> of it back?**

### The aim, stated plainly

We run **one** assistant (JARVIS) in **four** configurations — two *designs*
(a reasoning "brain" vs. a fixed "pipeline") crossed with two *models*
(cloud vs. local) — over the **same** fixed list of tasks. We then compare
how each configuration does. The point is the **interaction**: not "is cloud
better than local" (it is), but **"does a good design shrink the penalty for
going local?"**

**Privacy is the *motivation*, not a measured number.** Going local is what
buys you privacy/offline/zero-cost; we never "measure privacy." We measure
the **price** you pay for it (lost quality) and whether better design
**lowers that price**. So the reader always knows: privacy is *why the
question matters*; the data is *about the cost of getting it*.

### Key terms (so nothing is fuzzy)

- **Architecture (the design).** *Brain* = a loop that reasons, decides
  which tools to use, can ask a question or work in the background. *Pipeline*
  = a fixed path: classify the request, run one matching skill, answer. The
  Brain *decides*; the Pipeline *routes*.
- **Deployment (the model).** *Cloud* = a large hosted model
  (`claude-sonnet-4-6`). *Local* = a small on-device model (`llama3.1:8b`).
- **Task success** = *whether the task is completed correctly* (the **primary
  outcome** — the one number the headline result is computed on).
  **Decision** = *what the mind chooses to do* (which tool, ask?, background?,
  decompose?) — the **mechanism** that explains task success.
- **Compensation** — the headline term, defined exactly **in task success**:
  *going from cloud to local lowers task success for every configuration; the
  Brain **compensates** if its drop is **smaller** than the Pipeline's.* In
  numbers: `compensation = (Pipeline_cloud − Pipeline_local) − (Brain_cloud −
  Brain_local)`; **positive ⇒ the Brain recovered part of the lost task
  success.** It does **not** mean local equals cloud (it won't). *Analogy: a
  skilled driver in a slow car loses less time than a careless driver in the
  same slow car — the skill compensates for the car.*

### What counts as success (for the *study*, not a task)

The study **succeeds when it yields a clear, interpretable answer — either
way.** "The Brain recovers ~70% of the loss (CI …)", "…only on hard tasks",
and "…it barely helps" are *all* wins: each tells a builder something true.
The only real failure is *inconclusive* data — which we guard against by
calibrating tasks so the cells actually diverge (§7) and by the rigor below.

### How every run is graded (the evaluation criteria)

Measures form a **hierarchy with one primary outcome** (full detail in §6),
so the study reports a single headline rather than competing numbers:

| Role | Measure | Question it answers | Graded against |
|------|---------|---------------------|----------------|
| **PRIMARY** | task success | was the task completed correctly? | a pre-registered outcome standard per task |
| **MECHANISM** | decision accuracy | did the mind make the right call (explains the primary)? | a pre-registered, *independent* ideal decision, scored by deterministic rules over the trace |
| **SUPPORTING** | speed, cost | what did it cost? | latency / cost meters |
| **SECONDARY** | conversational naturalness | how natural did it read? | objective proxies + blind ratings (no conclusion rests on it) |

All scoring is **blind** (the scorer never sees which configuration produced a
response) and the central result is computed on the **primary** alone.
"Independent ideal" means the *right decision* for a task is written from the
*task's* needs **before** any run — never "whatever the cloud did" (that would
rig the result).

---

## 1. Research question & contribution

**Question.** In a personal AI assistant, how do *reasoning architecture*
(a deciding "brain" vs. a fixed routing pipeline) and *deployment* (a cloud
model vs. a local model) **interact** to determine **task success**?
Specifically, when the model is changed from cloud to local, does the deciding
architecture's loss differ from the routing architecture's — and **in which
direction**? The signed interaction (termed *compensation*, §0) may be
**positive** (the deciding design loses less), **zero** (no interaction), or
**negative** (it loses more); the study measures it **without assuming a
direction**. The direction is not obvious a priori: a reasoning loop may
scaffold a weak model (positive) or fail to be driven by it (negative).

**Contribution.** Most prior work studies these axes separately
(agent-architecture papers; on-device-vs-cloud systems papers). The
contribution here is the **interaction**, measured on one controlled system
in which exactly one variable changes at a time, with the **decision the mind
makes** captured as the mechanism — the layer-3 lens that explains *why* one
architecture succeeds where another cannot, which pure-systems benchmarks do
not capture.

**The direction is contested in the literature, which is why it is worth
measuring.** Recent controlled comparisons of agent architectures across
model *tiers* disagree: one pre-registered a prediction that stronger models
would be less architecture-sensitive and rejected its own hypothesis, finding
the strongest model gained *most*; another reports that scaffolding narrows
the gap between small and large backbones
([related_work.md](related_work.md) §1). Whatever this study finds, it
answers a question the field currently answers both ways — and the practical
consequence lands either way, on the deployment decision every
privacy-conscious assistant builder faces.

This is feasible because the apparatus already exists: the two axes are
single switches (§4) on one frozen codebase with built-in cost and latency
instrumentation (§6). *(An earlier draft cited a test count carried over from
the live product repository. Any figure in this study must be reproducible
from the frozen apparatus alone, so it has been removed; `frozen_v1/` ships
the research tests only — 81 at freeze time.)*

---

## 2. Hypotheses (pre-registered)

Hypotheses are stated on the **primary outcome, task success** (§6), with
decision accuracy as the **mechanism** that explains it. The manipulated
variable lives in **layer 3 (the mind)**: the architecture determines what the
mind can decide, and that shows up in task success on tasks whose correct
handling requires a decision only the Brain can make.

- **H1 (architecture → task success, complexity-dependent).** The Brain
  achieves higher task success than the Pipeline, and the gap *widens with
  task difficulty* — negligible on trivial single-step tasks (both succeed),
  large on tasks whose correct handling requires backgrounding / clarifying /
  decomposing. *(Mechanism: the Brain makes the pre-registered ideal decision
  more often; decision accuracy explains the success gap. Amended 2026-08-19,
  pre-data: this clause previously read "which the Pipeline structurally
  cannot do" — the Pipeline can do all three, by rule rather than by
  judgement. See the amendment at the head of §7.)*
- **H2 (deployment → task success).** The Cloud model achieves higher task
  success than the Local model — in *both* arms (Brain reasoning AND Pipeline
  generation, which rides the same model seam) — at higher cost and
  (network-dependent) latency.
- **H3 (interaction — the headline).** Does the Brain's advantage *survive a
  weak local model*? Operationally on **task success**:
  `(Pipeline_Cloud − Pipeline_Local)` > `(Brain_Cloud − Brain_Local)` — the
  Brain narrows the cloud→local gap more than the Pipeline does (*compensation*).
  Mechanism: does brain+local keep making the right decisions, or does the
  weak model collapse it toward pipeline-like simplicity?
- **H4 (cost/latency tradeoff, descriptive).** Local removes per-query cost
  and the network round-trip but raises local compute/latency; the Brain adds
  reasoning overhead. We characterize the Pareto frontier rather than test a
  directional claim.

---

## 3. Design — 2×2 factorial

Two factors, two levels each, fully crossed → **four cells**, every cell
run on the same fixed task set (§7).

| Cell | Architecture | Deployment | Role |
|------|--------------|------------|------|
| **C1** | Brain | Cloud | ceiling |
| **C2** | Brain | Local | *the interesting cell (H3)* |
| **C3** | Pipeline | Cloud | architecture control |
| **C4** | Pipeline | Local | floor |

---

## 4. Independent variables (operationalized to code)

Both factors are existing single switches — no new code, which is what
keeps the manipulation clean.

| Factor | Level | Switch | Notes |
|--------|-------|--------|-------|
| Architecture | Brain | `config.BRAIN_ENABLED = True` | agent loop: perceive → decide → tool-call → answer, holds the turn as one entity (`cognitive/brain.py`) |
| Architecture | Pipeline | `config.BRAIN_ENABLED = False` | legacy linear prompt+LLM path: input → classify → skill → output, no dynamic reasoning loop |
| Deployment | Cloud | `LLM_PROVIDER=anthropic` | `claude-sonnet-4-6` (the configured smart tier) |
| Deployment | Local | `LLM_PROVIDER=ollama` | local model on-device (exact model = §13 open decision) |

The provider seam (`infrastructure/ai_engines/providers/`) keeps the
**routing rule identical across providers** — only the model string
changes — which the code comments already flag as a paper-integrity
requirement. The four cells are four `(BRAIN_ENABLED, LLM_PROVIDER)` config
pairs, nothing else.

**Scoping note (architecture as a system-level intervention).** Flipping the
architecture switch changes the control structure *and* the affordances that
ride with it (looping, tool orchestration, prompting) — so "architecture" is
not an isolated causal mechanism but the **deciding/routing system as
realistically deployed**. The study claims a system-level effect ("the
deciding architecture, as built, yields X"), never "the loop *alone* causes
X." This is the standard, honest scope for a systems comparison.

---

## 5. Controlled variables (held constant across all cells)

- **Frozen apparatus:** every run cites the `paper-baseline` commit tag.
  No code or config changes mid-study except the two IV switches above.
- **Same machine**, same background load, same OS state, mains power.
- **Same task set, same order seed** (§7), same per-task prompts.
- **One shared system prompt**, byte-identical across all four cells
  (`apparatus/arms/base.py`, `SYSTEM_PROMPT`). It fixes the response register
  (spoken prose, since the length bands and §6d proxies assume it) and states
  the sandbox path convention once, globally. *Amended 2026-08-19 (pre-data):
  the path convention was added after the action set's end-to-end test showed
  the two models differing on argument format while agreeing on tool choice —
  without it, several action tasks would measure whether a model can guess an
  undocumented convention. A convention stated once for all 48 tasks is a
  control; the same sentence added because one task failed would be per-task
  tuning and is forbidden (`apparatus/CHARTER.md` §7).* The prompt says
  nothing about when to ask, refuse, decompose or defer: those are the
  measured decisions, and instructing them would replace the finding with an
  instruction-following check.
- **Warm models** — a warm-up pass before timed runs (cold-start excluded,
  noted separately).
- **Determinism where available:** temperature pinned (target 0) so model
  nondeterminism is minimized; residual cloud nondeterminism handled by
  repetition (§8) and reported.
- **Same speech I/O path** — to isolate the LLM factor, text-mode
  (`jarvis_cli.py`) is the primary harness so ASR/TTS variance doesn't
  contaminate the LLM comparison. (A secondary voice-mode pass measures the
  felt turn-taking axis where speech *is* the point — see §6/§13.)

---

## 6. Dependent variables (metrics → existing instrumentation)

The measures form a **deliberate hierarchy with a single primary outcome**,
so the study reports one headline result rather than several competing
numbers (which invites a "metric-fishing" reading). One metric is primary;
the rest support or explain it.

### 6a. PRIMARY — task success

*Whether the task is completed correctly*, judged against a per-task outcome
standard fixed in advance (§7). **The central result (§9) is computed on this
quantity alone.** Task success carries the deployment signal in both arms
(the cloud model yields better Brain reasoning AND better Pipeline generation
— the Pipeline's `conversation_skill` calls the same swappable model) and the
architecture signal where success requires a capability only the Brain has
(a clarification task succeeds only if the assistant asks). Scored
mechanically where the standard is checkable (a required value, a recognisable
completed action); a blind grader applies the fixed standard only where
judgement is unavoidable.

| Metric | Definition | Source |
|--------|------------|--------|
| **Task success** | meets the task's pre-set outcome standard | per-task rubric (pass/partial/fail) |

### 6b. MECHANISM — decision accuracy

*What the mind decided*, scored by **deterministic rules over the execution
trace** against a pre-registered, **independent** ideal decision per task
(§7). Independence is mandatory: the ideal is derived from the task, never
"whatever the cloud cell did" — the circularity trap. Each signal is a
recorded fact, not a judgement, so the measure needs no subjective grading.

| Signal | Definition | Source (trace) |
|--------|------------|----------------|
| Tool/skill choice | invoked an action from the task's pre-set acceptable set | Brain: `tool_calls`; Pipeline: NLU intent |
| Clarify | asked when the request was under-specified | `ask_user`, `state.set_pending_question`, or the confirmation gate |
| Ask origin | whether the question came from the model's judgement or a rule firing | `model` \| `rule` \| `none` (added 2026-08-19; **descriptive only** — §12a item 12) |
| Background | dispatched a worker for a long task vs. blocked | `action_worker` dispatch flag |
| Decompose | broke a multi-step goal into steps | Brain tool sequence |

Decision accuracy is **not a competing outcome**; it *explains* task-success
differences by decomposing them into the decisions that produced them.

> **Amended 2026-08-19 (pre-data).** This paragraph previously continued:
> *"— why the Brain succeeds where the linear Pipeline structurally cannot
> (its decision is the single NLU route, no loop). Reporting the Pipeline's
> lower decision ceiling is the architectural finding."* That wrote the
> direction of an unrun result and rested on the withdrawn capability claim.
> The structural fact survives and is all that is asserted: the routing arm
> commits to its actions in one model call, the deciding arm may revise
> across up to eight. Which arm that favours, and by how much, is what the
> experiment is for.

**The ideal is rule-derived, not hand-picked** (the chief defensibility
point). The ideal decision for each task follows from a **fixed ruleset over
task properties**, registered before any run, so "who defines the ideal" is
answered by the rule, not the experimenter:

| Task property (tagged in advance) | Ideal decision | Credit |
|---|---|---|
| missing a required argument | **ask** (clarify) | required — acting without asking is a miss |
| long-running / open-ended | **background** | preferred = full; blocking-but-completing = partial |
| multi-step goal | **decompose** | preferred |
| beyond capability | **decline honestly** | required |
| self-contradictory | **surface / ask** | required |
| well-specified single action | **execute directly**, correct tool | asking = over-asking, penalised |

*Multiple valid strategies* are handled by the **pre-set acceptable action
set** (`tool_any`) and by **graded credit** (full/partial/none), not a single
brittle answer. Each task's derived ideal is **validated by a second rater,
blind to results, before the run** (inter-rater agreement on the ideals
themselves).

> **Reframe against the "rules bake in the advantage" attack.** Decision
> accuracy is **not a symmetric head-to-head metric** but a *decomposition of
> the failure modes contributing to task success*. The fair, symmetric
> comparison is **task success**; decision accuracy only *explains* it.
>
> **Amended 2026-08-19 (pre-data).** This paragraph previously continued:
> *"where a task's ideal needs a capability one design structurally lacks
> (e.g. asking), a low score restates that limit."* That defence is withdrawn
> along with the capability claim it rested on — the routing design can ask,
> background and decompose (see the amendment at the head of §7). The
> objection is now answered at the root instead of deflected: the ideal is
> derived from properties of the **request**, with no architecture argument
> (`apparatus/tasks/derive_ideal.py`), so both designs are scored against the
> same ideal and no part of the mechanism result is true by construction.
> What the trace additionally records is `ask_origin` — whether a question
> came from the model's judgement or from a rule firing.
>
> **Amended again 2026-08-19 (pre-data), after Pilot M4.** This sentence
> previously ended *"— which is where the architectural difference actually
> lives."* It does not. The rule path is in the shared half of the apparatus
> and fired once in 192 runs, in the deciding arm. `ask_origin` is reported
> descriptively with its n and carries no mechanism claim (§12a item 12).

### 6c. SUPPORTING — speed and cost (trade-offs)

| Metric | Definition | Source |
|--------|------------|--------|
| Total latency | request → final response | `metrics/latency.py` |
| Time-to-first-token | request → first streamed token | `metrics/latency.py` |
| Cost per query | USD (cloud) / $0 local | `metrics/cost_meter.py` (+ generate-seam metering) |
| Robustness | error / degradation events | `metrics/degradation.py` |

Reported as the *price* of any success recovered, not as success itself.

### 6d. SECONDARY (exploratory) — conversational naturalness

Objective proxies for conversational feel, **never load-bearing for any
conclusion** (the least defensible measure; included for completeness):

| Metric | Definition | Source |
|--------|------------|--------|
| Formulaic-opening rate | replies beginning with a pre-registered canned opener | response text |
| Length fit | reply length vs. the task's pre-set expected length | response + task field |
| Turn-taking (voice subset) | end-of-turn cut-offs vs. lag | EOT traces |

Validated against blind human ratings (§13), whose role is to confirm the
proxies track human perception — not to carry a claim.

> **Execution as the realism anchor.** Decision accuracy is read from the
> trace without running heavy tasks to completion; a *subset* is executed
> end-to-end as the existence proof that decisions resolve into working
> behaviour. Decision-trace = the mechanism; execution = the validity anchor.

---

## 7. Task set (fixed, pre-registered)

> **Amendment, 2026-08-19 (pre-data). The clarification category is a test of
> ask *mechanism*, not of ask *capability*.**
>
> This section previously described category 4 as "the purest architecture
> test: the Pipeline cannot ask", and §6b scored `asked`, `backgrounded` and
> `decomposed` as structurally unavailable to the routing design. **That claim
> is false**, and it is withdrawn before any data exists.
>
> The evidence is in the pilot trace of 2026-08-19
> (`apparatus/derive/`, 108 rows, all four cells). The routing arm asked a
> clarifying question in both deployments — `clar-04` in C3 and C4, `clar-03`
> in C3 — and `cognitive/action_worker.py` and `cognitive/task_planner.py`
> are reached by all four cells, so backgrounding and planning are available
> to it as well. It has three ask paths, none of which require a loop: a
> skill returning `requires_followup` (`orchestrator.py:454`); the
> risk/confidence confirmation gate (`orchestrator.py:370-392`), which in
> fact runs **only** for routing because brain-mediated turns are explicitly
> exempted; and the model itself, when a turn routes to conversation.
>
> **What replaces it.** The architectural difference is not whether an arm
> can ask but *what makes it ask*. The deciding design asks when the model
> judges a request underspecified; the routing design asks when a rule fires
> — a fixed risk table, a confidence threshold, a per-skill follow-up. A
> rule's coverage is set at design time and does not depend on the model. A
> model's judgement does. The decision trace therefore records `ask_origin`
> (`model` | `rule` | `none`) alongside `asked`, and the question this
> category asks is **how each mechanism responds to the deployment switch**.
> No direction is asserted here; the sign comes from the data.
>
> **Why this is a stronger design, not a salvage.** The withdrawn claim made
> part of the mechanism result true by definition: an arm scored against a
> ceiling it was declared unable to reach cannot tell you anything you did
> not already assume. The ideal decision is now derived from properties of
> the *request* alone (`apparatus/tasks/derive_ideal.py`, no architecture
> argument), both arms are scored against the same ideal, and any difference
> between them is observed rather than stipulated. This also removes the
> "your rules bake in the advantage" objection at its root.
>
> **What did not change.** The category count (8), the ideal for these tasks
> (`ask`, derived from `missing_required_argument` or `self_contradictory`),
> and the principle that decision accuracy decomposes task-success failure
> modes rather than competing with them.
>
> *(Draft — Marc to revise into his own wording before submission. The
> substance is settled; the phrasing is not.)*


A **fixed, version-controlled** set (`research/tasks.json`) spanning the
capability surface. Every task earns its place by being **realism** (it is
a thing a real assistant is asked) and **control** (it isolates a factor)
— if a task can be neither-justified it is cut. Each task carries **two
pre-registered rubrics**:

- `ideal_decision` — the independent ideal at layer 3 (the §6b lens), and
- `success` — the outcome rubric (the §6a lens).

**Calibration is the make-or-break property** (the pilot taught us: a task
all four cells ace yields zero signal), and it is **prospective** — tasks are
selected before any run for their *expected* ability to discriminate, never
added or removed after results are seen. Treatment tasks are tuned so the
**local model visibly underperforms** the cloud model — hard enough
reasoning/generation that `llama3.1:8b` stumbles where `claude-sonnet-4-6`
does not — and so that the **ideal decision requires a capability the Pipeline
cannot express** (clarify / background / decompose). Each task states, in one
line, *which factor it is built to move and why*. **48 tasks, eight per
category** (§13).

The six categories (counts locked in §13), each justified by the lens it
serves:

1. **Trivial single-step** — "what time is it". *Control: both
   architectures route identically and both models succeed → the floor that
   makes H1's complexity claim falsifiable. Necessary, not filler.*
2. **Multi-step reasoning** — chained inference a small model fumbles.
   *Moves deployment (outcome, both arms) AND architecture (decompose).*
3. **Tool / action** — file search, note capture, a timed dispatch. *Moves
   architecture via decision quality: did the mind pick the right tool,
   sequence two of them, background the slow one. Scored from the decision,
   with a deterministic sandbox check on the side effect.* **Amended
   2026-08-19 (pre-data):** the example was "message X on Discord". Messaging,
   screen reading, GUI app control and web research are all removed from the
   apparatus — network tools because a live answer is not reproducible across
   960 runs, GUI tools because there is no surface to verify against
   (CHARTER §4, §6.3). Four of the five inherited action tasks named removed
   tools and were rewritten onto the retained surface; each carries a
   `rewritten_because` line. The category's experimental role is unchanged —
   choose a tool, sequence, decide whether to block — but the surface is
   narrower than a real assistant's, and that is stated as a limitation
   rather than absorbed.
4. **Ambiguous / clarification** — under-specified requests whose ideal
   decision is *ask first* (ties to the #3 clarification flow). *Moves
   architecture via ask **mechanism**: both designs can ask, but the
   deciding design asks when the model judges the request underspecified
   and the routing design asks when a rule fires. `ask_origin` records
   which. See the amendment at the head of this section.* **Amended
   2026-08-19 (pre-data):** the routing design has **two** ask paths, not the
   three listed above — the risk/confirmation gate is withdrawn as
   unreproducible (§12a item 5). Both `ask_origin` values remain reachable by
   both designs.
5. **Conversational grounding** — multi-turn context carry. *Moves
   deployment (local memory/attention limits) + feeds the felt-quality axis.*
6. **Robustness / adversarial** — malformed / trap inputs. *Tests failure
   behavior; moves architecture (graceful degradation vs. confident nonsense).*

The exact list lives in `research/tasks.json` and is frozen with
`paper-baseline`; never edited mid-study.

---

## 8. Procedure

1. Tag `paper-baseline`; record machine + model versions.
2. For each of the 4 cells: set the two switches, warm up, then run the
   full task set **R repetitions** (R = §13) to average over residual
   nondeterminism.
3. Randomize task order per repetition (fixed seed, logged) to control
   order/learning effects.
4. Log every run as raw JSONL (cell, task, repetition, all §6 metrics,
   full transcript) — append-only, never hand-edited.
5. Felt-quality ratings collected **blind** to cell (rater sees transcript
   without knowing architecture/deployment) — §13.
6. **Pilot first, with a hard VALIDITY GATE:** one full pass (R=1) across all
   four cells to shake out harness bugs and confirm every cell runs every
   category. **Acceptance criterion (non-negotiable):** the *local* model must
   show **intermediate variance** — neither floor (fails ~everything) nor
   ceiling (passes ~everything) success, across categories and difficulty.
   Without intermediate local variance there is no gradient for architecture
   to interact with, and the study collapses to a trivial main effect. If the
   local model saturates, the task set is **recalibrated before the final
   run**; the full R-repetition run proceeds *only* on passing this gate. The
   local model's per-category, per-difficulty success is reported to
   demonstrate the condition holds.

---

## 9. Analysis plan

> **Amendment, 2026-08-19 (pre-data).** The analysis below replaces an
> earlier plan that named a two-way ANOVA as the secondary lens and a
> run-level bootstrap. The change is made **before any data exists**, on
> methodological grounds, and is recorded rather than silently applied:
> the outcome is binary and the runs are clustered within task, which ANOVA
> and a run-level bootstrap both mishandle. Rationale and the field
> precedent are in [related_work.md](related_work.md) §3.

- **Primary (H3, the interaction on task success):** the pre-registered
  interaction contrast is `(C3−C4) − (C1−C2)` on **task success** (positive ⇒
  the deciding design compensates), estimated two ways that must agree:
  1. **Mixed-effects logistic regression** — `success ~ architecture *
     deployment + (1 | task)`, with the interaction term tested by
     likelihood-ratio test against the no-interaction model. Logistic
     because the outcome is binary (pass/fail per run); a **random intercept
     per task** because the R repetitions of a task are not independent
     observations, so treating 240 runs per cell as 240 independent draws
     would overstate precision.
  2. **Clustered bootstrap** — 95% CI on the contrast, **resampling tasks
     (with their repetitions attached), not individual runs**, over 5,000
     resamples. Resampling runs would reintroduce exactly the independence
     assumption the random effect exists to avoid.
  Report **effect sizes and confidence intervals, not just p-values**. If
  the two estimates disagree materially, that disagreement is reported, not
  resolved by picking one.
  *(Partial credit: task success is scored pass/partial/fail. For the
  primary analysis `partial` is collapsed to fail — the stricter,
  pre-registered choice — and the pass-or-partial coding is reported
  alongside as a robustness check. Fixed here, before any data.)*
- **Mechanism (decision accuracy):** the same 2×2 on **decision accuracy**
  (fraction of runs matching the pre-registered ideal, scored
  deterministically). This *explains* the primary result — where the two
  designs' success rates differ, decision accuracy is where the difference
  should show up — and tests whether brain+local keeps deciding well or
  collapses toward the Pipeline. Report the decision→success relationship,
  and report `ask_origin` alongside it: a rule-driven ask and a
  model-driven ask are the same event in the `asked` column and different
  mechanisms underneath.
- **H1 / H2 (main effects):** marginal comparisons with CIs; H1's
  complexity claim tested by the **task-success** *slope* across the
  difficulty gradient (the design gap should widen with difficulty).
- **H4 (tradeoffs):** descriptive Pareto plots (cost vs. success; latency
  vs. success) per cell.
- **Per-dimension decomposition:** the cloud→local gap reported **per task
  category** (reasoning / memory / instruction-following / tool-use), so the
  result identifies *where* the local model is weaker rather than asserting a
  single undifferentiated "weaker."
- **Secondary (naturalness):** reported in an appendix with inter-rater
  agreement and the proxy↔human correlation (§13); **no conclusion is drawn
  from it.**
- All analysis scripts version-controlled; run against the frozen raw logs.

---

## 10. Threats to validity & mitigations

| Threat | Mitigation |
|--------|------------|
| **Local model saturates (floor/ceiling) → no interaction signal** | **the make-or-break risk** — the pilot validity gate (§8) requires intermediate local variance across categories/difficulty, or the task set is recalibrated before the final run |
| Model nondeterminism | temperature→0; R repetitions; report variance |
| Cloud network variance (latency) | report latency with/without network leg; multiple time-of-day runs |
| Local hardware ceiling confound | fix machine; report local model + VRAM; frame as *this deployment*, not "local in general" |
| Order / learning effects | randomized task order, fixed logged seed |
| Task-set bias toward Brain | pre-register the set; include the trivial category where Brain shouldn't help |
| "Ideal decision" is subjective | ideal **rule-derived** from task properties (§6b), pre-registered, + a second rater validates each ideal blind to results |
| Synthetic tasks ≠ real usage | own it as a stated limitation; categories chosen as a taxonomy of real request types; future work = replay on real usage logs |
| Naturalness subjectivity | demoted to a secondary/appendix exploratory measure; carries no conclusion |
| Pipeline arm degraded/unfair | pilot verifies the Pipeline runs *every* task category before full runs |
| Experimenter bias | pre-registered hypotheses + analysis; raw logs retained |
| **LLM judge self-preference** *(added 2026-08-19, pre-data)* — 33 of 48 tasks are rubric-scored, and the judge is `claude-sonnet-4-6`, which is also the cloud treatment model. An LLM judge favouring output from its own family is a documented effect | The bias pushes toward **both** cloud cells, in both arms, so it is not confounded with architecture and the primary interaction contrast `(C3−C4)−(C1−C2)` is largely protected — it would have to differ *between arms* to move it. **The deployment main effect is not protected and is reported with that caveat.** Mitigations: the judge is blind to cell by construction (`apparatus/harness/judge.py`, `BlindCase`); it grades against the task's own criterion, written before any transcript existed; it sees the sandbox's effect log, so a claimed action that did not happen fails; and a blind human sample is rated with judge–human agreement reported. If agreement is poor, that is a finding about the measure and is published as one |
| **The cloud model pin is an alias, not a content hash** *(added 2026-08-19, pre-data)* — `claude-sonnet-4-6` is the strongest identifier the API exposes, so a provider-side change behind that name is undetectable from here and a re-run months later may not be running the same weights | The preflight verifies that the model *answering* is the model pinned, and every row records the model the provider named for every call, so a substitution the API discloses cannot pass silently (§12a item 11). What remains unprotected is a silent change behind a stable name. Stated as a limit on cloud reproducibility: **the local half of every comparison is reproducible from a digest; the cloud half is reproducible only to the extent the provider keeps an alias stable.** Dated raw transcripts are retained so a future divergence is at least measurable against what was actually observed |
| **Judge and grader drift across re-runs** *(added 2026-08-19, pre-data)* | Verdicts are cached by a content hash of the transcript, so re-scoring the same rows cannot return a different answer on a different day, and `scored.jsonl` does not depend on when it was produced |

---

## 11. Reproducibility

- `paper-baseline` git tag = the exact frozen apparatus. **Cut 2026-08-19**,
  after the pilot cleared the gate and before any full-run row existed;
  `apparatus/FREEZE.md` records what it covers, what it does not, and the
  one command that verifies it (`python tasks/build.py --check`).
- **Task set frozen by hash:** `apparatus/tasks/tasks.json`, sha256
  `0a3ae35b1ac8343b13880f01393b82960ff6bfe2e5c5927739424b623c1d85b3`. Note
  this is *not* `research/tasks.json`, which is the snapshot's 27-task set
  and is provenance only.
- Config snapshots (the four `(BRAIN_ENABLED, LLM_PROVIDER)` pairs) checked in.
- Raw run logs (JSONL) + analysis scripts version-controlled.
- Model versions (Claude model string; local model + quantization) recorded.
- **Every row states its own provenance** *(added 2026-08-19, pre-data)*: the
  `baseline_commit` it was produced at (marked `-dirty` if the tree had
  uncommitted changes), the `sha256` of the exact `tasks.json` bytes it ran
  against, the order seed and the task's position in that order, and the
  model **the provider reported** for every call. Reproducibility is
  therefore a property of the data rather than a claim in this section.
- **Pinned analysis dependencies** in `apparatus/requirements.txt`. The
  interval and the test statistic depend on library versions, so "run the
  scripts" is not reproducible without them.

---

## 12. Scope — deliberately out

- Not a model-quality benchmark (we fix two representative models; the
  claim is about *architecture × deployment interaction*, not "model A vs B").
- Not multi-user / personalization effects (single controlled operator).
- Not a production-cost study (cost is reported, not optimized).
- Not the Tier-3 internals (no fusion weights / persona / recipe specifics).

---

## 12a. Amendments — dated, pre-data

Every change to this pre-registration made after it was first written and
**before any data was collected**, with its reason. The list is exhaustive by
intent: pre-registration is only worth anything if the diary of departures is
kept honestly, and a change that is defensible is not made less so by being
written down.

All of the below are dated **2026-08-19** and all precede the first scored
run. Each is traceable to evidence in `apparatus/derive/FINDINGS.md` or to
`apparatus/CHARTER.md`.

**1. The voiced turn-taking subset is dropped.** (§13 item 5, §6d turn-taking
row; CHARTER §6.1.) It required the voice stack, which is removed as
pre-transcription — before this experiment's entry point. It was exploratory,
appendix-only, and forbidden from carrying a conclusion, so no result depends
on it. The text-based naturalness proxies are unaffected.

**2. The personality layer is removed.** (CHARTER §6.2.) Conversational
naturalness (§6d) now measures the model's own register rather than a tuned
persona. This is arguably a cleaner measure, but it is a change in *what is
measured* and is recorded as one rather than claimed as an improvement.

**3. Action verification moves from GUI automation to deterministic
sandboxed side-effect checks.** (CHARTER §6.3; resolves `docs/harness.md` §8
item 2.) A task is scored by asking the world what changed, not by asking a
grader whether the response sounds like it happened — and absence is
checkable, which several clarification tasks require.

**4. The action surface is narrower than the snapshot's.** Removing GUI
automation and network search left four of the five inherited `action` tasks
and one `clarification` task naming tools that no longer exist. Each was
rewritten onto the retained surface with a `rewritten_because` line and a new
id; retired ids are never reused. The category's experimental role is
unchanged — choose a tool, sequence two, decide whether to block — but it no
longer tests breadth, and cannot. Stated as a limitation, not absorbed.

**5. The routing design's risk/confirmation gate is withdrawn.** §7 credited
it with three ask paths; it has two. The gate could not be reproduced from
the snapshot rather than approximated from memory: `RISK_TABLE` classifies
`delete_file` as MEDIUM, whose confirmation is conditional on an NLU
confidence score below 0.85 that the apparatus does not produce, and the
unconditional HIGH/CRITICAL tier has no members among the retained actions.
Building an approximation would have meant an experimenter-written risk table
wired to the arm the clarification category probes hardest. The routing
design keeps a rule-driven ask (a required argument missing) and a
model-driven one (a question written on the conversation route), so both
`ask_origin` values stay reachable by both arms and the §6b mechanism
contrast is unaffected. Evidence: `FINDINGS.md`, *"The routing arm's
confirmation gate could not be reproduced"*.

**6. `tool_any` is reconciled to the real action set.** 18 of the 48 records
named tools the apparatus does not have. One was a synonym; the other two —
`general_conversation` and `recall_conversation` — were NLU *intent* names,
which is to say **routing** concepts sitting inside an ideal that §6b
requires to be architecture-blind. Both collapse to one reserved name,
`answer_directly`, which belongs to no design and is satisfied by the absence
of a tool call. The build now validates every entry against the action set.
No ideal changed: `apparatus/tasks/build.py` reconciles the rename rather
than allowlisting it as a correction. Evidence: `apparatus/tasks/SCHEMA.md`.

**7. The validity gate's per-category band exempts `trivial`.** §8 requires
the local model to show intermediate variance "across categories and
difficulty"; §7 and §10 give the trivial category the opposite job — it is the
**control**, included "where Brain shouldn't help", the category both models
are meant to pass, and the thing that makes H1's complexity claim falsifiable.
A band forcing it below 0.85 would require making the control hard, which
destroys the control. The exemption is narrow: trivial still counts in the
overall local rate, so a local model that passed everything would still fail
the gate. Only the per-category check skips it. Pilot M4 made the conflict
concrete — trivial came out at 0.875 in **all four cells identically**, the
control behaving exactly as designed and being flagged as a failure.

**8. The gate's criterion was not met on `clarification`, and the study
proceeds on a documented exception.** Recorded here in full because a gate
whose failures can be written away is not a gate, so the two facts are kept
apart: the criterion is recorded as **not met**, and the decision to continue
is recorded separately with what it costs. `apparatus/harness/analyze.py`
returns them as two booleans, `criterion_met` and `proceed`, and an exception
can never turn the first one true.

*The finding.* Pilot M4 (192 runs, R=1): local success on clarification is
**0.062 (1/16)**, below the 0.15 floor, and unchanged by re-screening four of
its records against the retained action surface. The floor is not a task
artifact. The same local model asks correctly elsewhere in the same pilot —
ten questions across robustness, grounding and trivial. Its failure mode on
this category is specific and reproducible: it **confabulates**, claiming
completed actions it has no tool for (*"You are now in your email client"*,
*"The music player is now open"*) and emitting raw tool-call JSON as prose.

*Why not recalibrate.* Rewording tasks does not move a confabulation floor,
and iterating on the task set until the gate passes is precisely the tuning
the gate exists to prevent.

*What this forfeits.* **No claim is made about architecture within the
clarification category at local deployment.** Both arms sit at the floor
there, so no gradient exists for architecture to interact with. The category
is reported descriptively, with its n. It still contributes to the overall
contrast — 6 of its 8 tasks discriminate between cells — but that
discrimination is deployment, not architecture.

**9. Four clarification records were re-screened against the retained action
surface, and one of those was reverted.** `clar-04` ("play that one again"),
`clar-06` ("send it to Dana") and `clar-08` ("email my landlord") request
capabilities the reduction removed, so their `missing_required_argument` tag —
written against the full product — became false and their ideal moved from
*ask* to *decline*. The pilot showed the cost of leaving them: the cloud model
declined correctly on capability grounds and was scored a **fail** by a
criterion that only admitted asking. The screen is a rule applied to all 48
records, not a patch to the three that failed: *name the action that would
complete the request once every ambiguity is resolved; if no retained action
can, the request is `beyond_capability`.* The rule validates against tags that
predate it — it is already what produced `robust-02`'s tag ("open the garage
door"). `derive_ideal` now also encodes that **declining supersedes asking**,
since "ask AND decline" is not a decision an assistant can make.

`clar-01` ("book it for me") was retagged with the other three and **reverted
the same day**. It names no object at all: the ambiguity *is* what is being
requested, so asking first is defensible and the rule was being stretched past
the case it was written for. Both the retag and the revert are recorded, since
a rule that had to be walked back on one of four cases is a fact about the
rule.

**10. Two hypotheses' supporting components are thinner than pre-registered.**
`backgrounded` is derived on 2 of 48 tasks, `declined` on 4, `decomposed` on
5. Each is reported descriptively with its n and carries **no test and no
conclusion**. Further, with the background worker removed and the sandbox
completing instantly, `backgrounded` measures *the stated decision to defer*
and never the benefit of deferring.

**11. The model pin is verified per call, not declared.** (§13 items 1 and 6.)
The trace found that the snapshot's cloud cells did not run the same model.
The deciding design routed each turn through a fast/smart tier selector whose
Anthropic fast tier defaults to Haiku 4.5, and `C1_brain_cloud.env` pinned
only `BRAIN_MODEL`, so all 27 logged tier decisions in C1 chose *fast* while
C3 ran Sonnet 4.6 throughout. Every row in both cells recorded
`model=claude-sonnet-4-6`, because the row was written from the cell's
configured label. Architecture was confounded with cloud model identity,
inside the very interaction this study reports, and the recorded data would
not have shown it.

Three changes, all in the apparatus:

- The tier selector is not in the reduction. One cell, one model, one call
  path (CHARTER §3).
- The model recorded on a row is the model **the provider's own response
  names** (`models_reported`, one entry per call), not the configured label.
  The two are now separable, which is the whole point of recording it.
- Each provider runs a `preflight` before a cell's first task and raises
  `ModelMismatch` if the model that answers is not the model that was
  pinned. A tier substitution found on task 1 of 48 is a bug report; found on
  task 48 it is a discarded cell. `ModelMismatch` is cell-invalid and aborts;
  an ordinary `LLMError` is task-degraded, recorded, and stepped over.

Pilot M4 (192 rows, 2026-08-19) reports exactly one model per cell and no
mismatches: `claude-sonnet-4-6` on all 96 cloud rows, `llama3.1:8b` on all 96
local rows.

**The two pins are not equally strong, and the asymmetry is stated rather
than smoothed over.** The local model pins to *content*: `llama3.1:8b`,
ollama digest `46e0c10c039e0191…87ca666e`, gguf, Q4_K_M, 8.0B, served by
ollama 0.17.1. Anyone holding that digest holds the same weights. The cloud
model pins to an *alias*: `claude-sonnet-4-6` is the strongest identifier the
API exposes, and the preflight confirms the response carries it, but it is a
name and not a hash, and a provider-side change behind that name is not
detectable from here. This discharges §13 item 1's "pin the exact version
string at freeze" for the local half and states plainly that the cloud half
cannot be discharged the same way. Added to §10 as a threat, since it is one.

**12. `ask_origin` is demoted from the mechanism contrast to a descriptive
count.** (§6b.) The pre-registration located the asking difference in the
*mechanism*: the routing design asks because a rule fires, the deciding
design asks because the model judged it should. When "the Pipeline
structurally cannot ask" was withdrawn (head of §7), `ask_origin` replaced
the claim with a measured quantity — and Pilot M4 measured it. Across 192
runs, `ask_origin=rule` fired **once**: C2/`clar-07`, the *deciding* arm at
local deployment, where the model called `delete_file` with no path and the
shared dispatcher refused to guess. `ask_origin=model` fired 33 times (C1 14,
C2 8, C3 10, C4 1).

Two facts follow, and both narrow what §6b may claim:

- **The rule path is shared, not architectural.** It lives in
  `Arm.run_action`, which both arms reach every action through, and it
  triggers on a missing required argument — a property of the call the model
  emitted, not of the control structure around it. It is symmetric by
  construction, and the one time it fired, it fired in the deciding arm.
- **In this reduction, both arms ask the same way**: the model writes a
  question. The rule-versus-model framing is true of the *snapshot*, where
  the routing arm's ask came from skill `requires_followup` and from the risk
  gate. The gate is withdrawn (item 5) and `requires_followup` is reachable
  but is not exercised by any of the 48 tasks.

`ask_origin` stays on every row and is still reported, because one out of 192
*is* the finding and it is visible only because the field exists. What it may
no longer do is carry the mechanism contrast. §6b's mechanism test is
unchanged and never depended on it: whether the recorded decision matches the
property-derived ideal, component by component, under one ruleset for both
arms.

Stated at R=1: this is a count, not a rate, and the full run may put the rule
path above one. That would not restore the claim being withdrawn, which is
about *where the mechanism lives* — the rule is in the shared half of the
apparatus regardless of how often it fires.

Amendments already filed in place, listed here for completeness: the
withdrawal of *"the Pipeline structurally cannot ask"* (head of §7, §6b, H1)
and the correction of the routing column in `docs/harness.md` §5(a).

---

## 12b. Deviations — dated, POST-data

§12a is closed. Every item in it precedes the first scored run, and nothing
may be added to it now. This section is the separate, weaker category: things
that departed from the pre-registration **after data existed**, recorded here
because a pre-registration whose failures are omitted is worth less than one
with none.

The distinction is not cosmetic. A pre-data amendment is a design decision
made in ignorance of its effect on the result. A post-data deviation is not,
and cannot be defended as one, however good the reason.

**1. The second-rater validation of the derived ideals was not performed
before the run.** (§6b, §10, `paper.md` §7.) The pre-registration commits to
it in three places: *"Each task's derived ideal is validated by a second
rater, blind to results, before the run (inter-rater agreement on the ideals
themselves)."* It did not happen, and the run is complete, so "before the
run" is no longer available.

**What is being done instead**, decided 2026-08-21: the validation is
performed *now*, still blind to results. This is possible because the ideal
derives from the task statement and its tagged properties alone — a rater
never needs to see a transcript, a score, or a cell. The rater receives the
48 task statements and the derivation rules, marks the ideal decision for
each, and agreement is reported per component and chance-corrected. The
result will be reported as **performed after the run, blind to results**, and
never as though the original timing had been met.

**What this does not recover.** A rater working before the run could have
changed the task set; a rater working now cannot, because the set is frozen
and the data is collected. So this measures whether the ideals are defensible
and no longer functions as a check that could have caught a bad ideal in time
to fix it. Any disagreement found is reported as a limitation on the affected
tasks, not corrected.

**The partial mitigation that was in place throughout**, and which is why
this is a weakness rather than a hole: the ideal is generated by a fixed rule
from tagged properties, with no architecture argument, and the build verifies
every derived ideal against the inherited hand-written ideal from the
snapshot, failing on any disagreement not listed in a dated allowlist. That
is mechanical and auditable. It does not test whether the *property tags*
themselves are right, which is precisely what a second rater would catch.

**2. The blind human naturalness ratings were not performed.** (§6d, §13
item 4.) The pre-registration commits to blind human ratings, inter-rater
agreement, and a proxy-to-human correlation. None was run. Decided
2026-08-21: the two computed proxies are reported descriptively in the
appendix, explicitly labelled **unvalidated**, and the promise of a
validation is removed from §3 and the appendix rather than left standing.

Nothing in the paper weakens as a result, because the measure was
appendix-only and pre-registered as carrying no conclusion. What is lost is
the ability to say the proxies track anything a human recognises. They are
reported as a description of the text, not as a measure of its quality.

**3. The assistant is unnamed in the paper.** Decided 2026-08-21. Not a
deviation from the protocol, which never specified a name, and recorded here
only because it is a post-data decision affecting the write-up: a product
name in the body invites the system tour the paper is arranged against.

*Items 4 to 6 were filed on 2026-09-07. All three departures date from the
full run on 2026-08-20 and were recorded in the paper's appendix on the
pre-registration and its departures (Appendix C) from the time they
happened; they were not entered here until now. Filing them
eighteen days late is itself a lapse in the record-keeping this section
exists to enforce, and it is stated rather than smoothed over.*

**4. The mitigation for cloud network variance was not carried out.** (§9,
§11.) The pre-registration answers the network-variance threat by splitting
latency into its network and compute legs and by running at several times of
day. Neither was done. Latency is one number per run, and all 960 runs fall
inside a single two-hour window on 2026-08-20, with the configurations run
one after another rather than interleaved.

**What it costs.** Task success is unaffected: temperature is pinned to zero
and the ordering is recorded. The latency figures in the paper's §4.8
describe that afternoon and not a typical one, and the paper says so where
they are reported. No claim rests on latency.

**5. The difficulty gradient is ranked within a category, not on one scale
common to all six.** (§13, H1.) The pre-registration states H1's complexity
claim as a task-success slope across a difficulty gradient, and assumes a
single scale. There is no single scale: difficulty was assigned when each
task was written, relative to the other tasks in its own category, so a level
5 in one category is not a level 5 in another. Pooling the six categories to
fit one slope treats them as though it were.

The slope was fitted on the pooled ranking anyway and is reported in the
paper's §4.4, with this objection stated where it is reported. The design
advantage by level is +0.200, +0.027, +0.127, +0.229 and +0.475; the slope is
+0.075 per level with a 95% interval of [-0.015, +0.174], which spans zero.
Four tasks sit at the highest level. `docs/results.md` §12 carries the
computation.

**What it costs.** The registered test was run, on a gradient weaker than the
one the plan assumed. It cannot separate difficulty from category, so it
neither supports nor refutes H1's complexity sub-claim; the paper reports it
as returning nothing rather than as evidence either way. The defect is in the
task set's difficulty scale, which was fixed before any data existed.

*Corrected 2026-09-08.* This item was filed on 2026-09-07 as "the
difficulty-gradient slope test was not run", which was false: the paper had
already reported the slope, in a draft written the same evening and committed
nine seconds before this section was. What was true of
`apparatus/harness/analyze.py`, which declines to fit the slope and says so in
`main_effects.json`, was written here as though it were true of the study. The
original wording is preserved in this repository's history at commit
`0e831b0`.

**6. The blind human sample that would give judge–human agreement was never
rated.** (§6b, §10, and §12a item added 2026-08-19.) The pre-registration
lists this as one of the mitigations for the LLM-judge self-preference
threat, alongside blinding the grader and grading against a pre-written
criterion. The other two were carried out; this one was not.

**What it costs.** The grader is unvalidated against human judgement. What
exists instead is narrower: a second model graded the same transcripts blind
and agreed at κ = 0.73, and the headline holds under both. That shows the
finding does not depend on which model graded it, and does not show that
either model agrees with a person. This is the deviation that reaches the
primary measure, and the paper states it in §3.7 and §7 as well as here.

---

## 13. Decisions — LOCKED 2026-06-18

1. **Local model:** `llama3.1:8b` (matches the config note, fits VRAM). Pin
   the exact version string at freeze for reproducibility. ✅
   *Discharged 2026-08-19 (§12a item 11):* ollama digest
   `46e0c10c039e0191…87ca666e`, gguf, Q4_K_M, 8.0B, served by ollama 0.17.1.
   This is a content hash, so the local half of every comparison is
   reproducible from the pin alone.
2. **Repetitions R per cell:** **R=5** (over 48 tasks ⇒ 240 runs/cell). ✅
3. **Task counts:** **8 per category × 6 categories = 48 tasks** (raised from
   ~27 for behavioural coverage — the task count, not the run count, is the
   unit of coverage, since repeated runs of one task are correlated). The
   exact frozen list lives in `research/tasks.json`; selection is prospective
   (fixed before any run). ✅
   *Confirmed and frozen 2026-08-19*, after the pilot ran all six categories
   in all four cells (§8.6). The list is `apparatus/tasks/tasks.json`, not
   `research/tasks.json` — the latter is the snapshot's 27-task set and is
   provenance only. sha256 `0a3ae35b1ac8343b13880f01393b82960ff6bfe2e5c5927739424b623c1d85b3`,
   built from the six category files by `apparatus/tasks/build.py`, which
   derives every ideal rather than reading one. Count unchanged at 48.
4. **Felt-quality raters:** **you, blind to cell** (primary); **+1–2
   recruited raters if available** → enables inter-rater agreement. The
   harness supports N raters. ✅
5. **Voice vs. text split:** **text-mode** (`jarvis_cli`) for the objective
   LLM comparison (isolates the LLM from ASR/TTS variance); a **voice-mode
   pass on a voiced subset** only for the turn-taking/felt axis. ✅
   *Amended 2026-08-19 (§12a item 1):* the voiced subset is dropped — the
   voice stack sits before this experiment's entry point and is not in the
   reduction. Text-mode is the whole study, and the entry point is a
   finalized text turn rather than `jarvis_cli`.
6. **Cloud model pin:** **`claude-sonnet-4-6`** (current smart tier). ✅
   *Amended 2026-08-19 (§12a item 11):* the pin is now **verified per call**
   against the model the provider's response names, and a mismatch aborts the
   cell. "Current smart tier" is struck — a tier is a routing decision, and
   routing between tiers is exactly the confound the trace caught. It is an
   alias, not a hash, and §10 records that limit.

*Counts (item 3) finalize after the pilot confirms every cell runs every
category — the only value deliberately left to confirm at freeze.* **Done
2026-08-19:** Pilot M4 ran 48 tasks × 4 cells with zero degraded rows, every
category reached in every cell. Counts stand; the set is frozen by hash
above and by the `paper-baseline` tag.

---
*DRAFT v0.1 — pre-registration. Companion to [private/provenance.md](private/provenance.md)
(originality) and the eventual paper. Once §13 is locked: freeze
(`paper-baseline`), write `research_tasks.md`, run the pilot.*
