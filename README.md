# The Harness–Capability Benchmark

The instrument, the task set, both registration documents and every result row
behind *A pre-registered 2×2 factorial crossing harness design with model
deployment in personal AI assistants*.

The paper asks one question. When a personal assistant has to run on the
user's own device, and the model available there is weaker than the one in the
cloud, how much of that loss does a better-built harness buy back? It crosses
two factors — **harness design** (routing or deciding) against **deployment**
(cloud or on-device) — over 48 tasks, and measures whether the design is worth
more where the model is weaker.

It is not. The deciding design is worth **+0.179** in the cloud and **+0.133**
on the device; the difference between those, which is the quantity the study
exists to measure, is **−0.046** with a 95% interval of [−0.196, +0.100]. A
second study widened the comparison to twelve pairings of six on-device models
against two cloud models and left it there.

Everything needed to check those numbers is here.

## What is in it

| | |
|---|---|
| `apparatus/` | the instrument. `arms/` holds the two designs, one file each; `tasks/` holds the 48 tasks and the rules that derive each one's ideal decision; `core/` holds the simulated computer and the 21 actions the assistant can call |
| `runs/` | every result row from both studies, scored. 960 runs in `full-2026-08-20/`, 2,592 in `study2/`, and the pilot that set the task set in `pilot-2026-08-19/` |
| `tools/` | the analysis. Every number in the paper comes out of one of these |
| `figures/` | every figure in the paper, and the script that draws it from the result rows |
| `protocol.md` | Study 1's pre-registration, written 2026-06-18, two months before the run |
| `protocol_ext.md` | Study 2's registration, written 2026-09-04, before any of its data existed |

## Checking a number

Install what the instrument needs — `pip install -r requirements.txt` — and
then:

```
python tools/analyze_study2.py          # the twelve pairings, the slope, the ablations
python tools/power_and_equivalence.py   # the power curve and the equivalence test
python tools/provenance_split.py        # the contrast on tasks that predate the study
python tools/grader_crosscheck.py       # the second grader, and agreement with the first
```

Each reads the scored rows in `runs/` and writes its report beside them. None
of them re-runs a model, so all four finish in minutes and none of them costs
anything.

**Re-running the experiment itself** needs an Anthropic API key for the cloud
half and [Ollama](https://ollama.com) for the on-device half. `tools/run_study2.py`
does it. The 960 runs of Study 1 took an afternoon; the 2,592 of Study 2 took
a night.

## Reading the two registrations

They are the reason the result is worth anything, so they are here in full
rather than summarised.

`protocol.md` fixes Study 1's hypothesis, its measures, its thresholds and its
analysis, and it does so **without asserting a direction** — the published work
is split on which way the effect should run, so assuming one would have been
both dishonest and unnecessary. `protocol_ext.md` does the same for Study 2,
and is explicit that its predictions were formed after Study 1's result was
known and so cannot claim the same standing.

Both record every departure from them, with dates. One of those departures
changed a number the paper reports: the interval on the registered slope was
first computed by resampling the six pairings rather than the 48 tasks the
registration named, which made it exclude zero. On the registered unit it
covers zero. The correction is in `protocol_ext.md` §7, item 3.

## The tasks

48 tasks in six categories. **22 of them predate this study** and could not
have been shaped by its hypotheses; 5 are adapted from that older set and 21
were written for this experiment. Every task records which it is, and
`tools/provenance_split.py` recomputes the headline on each half.

The set is frozen at sha256 `0a3ae35b1ac8343b13880f01393b82960ff6bfe2e5c5927739424b623c1d85b3`,
and that hash is carried on every one of the 960 data rows.

## What is deliberately not here

The paper's drafts, its figure captions as prose, and the working notes behind
the writing. A reader checking a number needs the protocol, the code and the
rows; the rest is how the paper was made, and putting it in a repository the
paper cites would invite reading it as part of the paper.

## Licence

The code is released for inspection and re-use. The task set and the result
rows are the study's data and are offered on the same terms.
