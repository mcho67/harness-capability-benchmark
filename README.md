# The Harness–Capability Benchmark

A fixed comparison that puts one question to any pair of models: **when the
model gets weaker, does a better-built harness buy back more?**

It runs 48 tasks through two harness designs — **routing**, where the model
names one action and whatever that action returns is the reply the user reads,
and **deciding**, where the model sees each result and may act again — and
reports the difference between what the design is worth with a strong model
and what it is worth with a weak one.

Run against six on-device models and two cloud ones, the answer was no: the
deciding design is worth **+0.179** in the cloud and **+0.133** on a laptop,
and the difference between those is **−0.046**, interval [−0.196, +0.100].
Whether that holds for your models is the thing this repository exists to let
you find out.

## Run it on your own models

Two models, one you think is stronger and one you think is weaker.

```
pip install -r requirements.txt
python tools/run_study2.py --plan        # prints what it will do, runs nothing
```

The model list is `SWEEP_MODELS` in `tools/run_study2.py`, a list of
`(name, provider)` pairs. Replace it with yours. `"ollama"` runs locally
through [Ollama](https://ollama.com) and costs nothing; `"anthropic"` needs
`ANTHROPIC_API_KEY`.

```
python tools/run_study2.py --sweep --on-device   # local models, free
python tools/run_study2.py --sweep --cloud       # ~$1.25 for two models
python tools/run_study2.py --score               # grade the replies, ~$2.80
python tools/analyze_study2.py                   # the contrast, per pairing
```

Each configuration is 48 tasks × 3 repetitions = 144 runs and writes its own
file, so it resumes safely if you stop it. A local 7B model takes about an
hour per configuration; a cloud model takes minutes.

**What you get back** is one number per pairing: how much more, or less, the
deciding design is worth with the weaker model than with the stronger one.
Positive means the harness compensates. Negative means it does not.

Any model that can be asked for a tool call will run. A model that cannot —
or that describes actions instead of taking them, which `mistral:7b` did here
— produces two configurations that are the same procedure under two labels,
and the analysis will say so.

## Check the numbers in the paper

Nothing here re-runs a model, so all four finish in minutes and cost nothing.

```
python tools/analyze_study2.py          # the twelve pairings, the slope, the ablations
python tools/power_and_equivalence.py   # the power curve and the equivalence test
python tools/provenance_split.py        # the contrast on tasks that predate the study
python tools/grader_crosscheck.py       # the two graders, and how far they agree
```

Each reads the scored rows in `runs/` and rewrites its report beside them. If
your run reproduces this repository, the files come back byte-identical.

## What is here

| | |
|---|---|
| `apparatus/` | the instrument. `arms/` holds the two designs, one file each; `tasks/` holds the 48 tasks and the rules that derive each one's ideal decision; `core/` holds the simulated computer and the 21 actions |
| `runs/` | every result row from both studies, scored — 960 runs in `full-2026-08-20/`, 2,592 in `study2/` |
| `tools/` | the runner and the analysis |
| `figures/` | every figure, and the script that draws it from the rows |
| `protocol.md` | Study 1's pre-registration, 2026-06-18 |
| `protocol_ext.md` | Study 2's registration, 2026-09-04 |

## The tasks

48 tasks in six categories, frozen at sha256
`0a3ae35b1ac8343b13880f01393b82960ff6bfe2e5c5927739424b623c1d85b3`, and that
hash is on every data row. Each carries its own written standard for what
counts as done, fixed when the task was written.

Both registrations record every departure from them. One of those changed a
number: the interval on the registered slope was first computed by resampling
the six pairings rather than the 48 tasks the registration named, which made
it exclude zero; on the registered unit it covers zero. `protocol_ext.md` §7,
item 3.

## The paper

*A pre-registered 2×2 factorial crossing harness design with model deployment
in personal AI assistants*, submitted to the S.-T. Yau High School Science
Award, September 2026. It will be linked here once it can be.

## Rights

Published so the results in the paper can be checked and so the comparison can
be re-run. Rights are otherwise reserved; contact the author about re-use.
