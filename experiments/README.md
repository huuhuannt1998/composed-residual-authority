# Running the experiments

Written after the laptop crashed with five research projects holding containers
at once. Everything here is built around one rule: **this project runs one
experiment at a time and cleans up after each one.**

## Once, before the first run

```bash
./prepare.sh                      # pulls 6 images, fetches + sha256-verifies Alloy 6.2.0
export ALLOY_TOOLS_DIR=$HOME/.tenantsafe/tools     # add to your shell profile
```

## Every time, before starting

```bash
./preflight.sh
```

It refuses to start on: Docker down, under 4 GB free memory, under 20 GB disk,
or missing Python dependencies. It *warns*, without blocking, when containers
from other research projects are running — that warning is the whole reason this
harness exists, so read it rather than skipping past it. `rka-*` containers are
this project's own infrastructure and are correctly ignored.

## Running

```bash
./run_all.sh --list          # what exists, what has already succeeded
./run_all.sh --dry-run       # the plan, touching nothing
./run_all.sh --tier 0        # formal only: no Home Assistant containers, ~10 min
./run_all.sh --tier 1        # short runtime experiments, ~1.4 h
./run_all.sh --only matrix   # a single experiment
./run_all.sh --skip lifetime_long
./run_all.sh --resume        # continue after an interruption
./run_all.sh                 # everything, ~8.4 h, longest last
```

Between every experiment the runner tears down all TenantSafe containers and
re-checks free memory. If memory drops below the floor it stops cleanly and
tells you to `--resume` later; nothing already finished is lost, because
successes are appended to `.run_state` as they happen.

A failing experiment does not abort the run. It is logged, reported, and the
next one starts.

## Suggested order on a shared machine

| When | Command | Cost |
|---|---|---|
| Anytime | `./run_all.sh --tier 0` | ~10 min, no HA containers |
| A free hour | `./run_all.sh --tier 1 --skip version_study` | ~1.1 h, 1 container at a time |
| A free evening | `./run_all.sh --only version_study` then `--only benchmark` | ~26 min |
| Overnight | `./run_all.sh --only lifetime_long` | **~6.5 h**, unattended |

## The one experiment that needs three containers

`benchmark` runs baseline, Defense A and Defense B **simultaneously**, on ports
8141–8143. That is deliberate and must not be serialized: measuring the arms at
the same time with matched restart counts is precisely what removes the confound
that invalidated the first attempt at this measurement. It is the peak footprint
of the whole project — roughly 2–3 GB — so give it a quiet machine.

Everything else uses exactly one container.

## Layout

| File | Purpose |
|---|---|
| `MANIFEST.tsv` | the registry: tier, peak containers, time estimate, outputs |
| `preflight.sh` | refuses to start a run the machine cannot carry |
| `prepare.sh` | one-time image pulls and pinned Alloy fetch |
| `run_all.sh` | sequential runner with resume, guards and teardown |
| `teardown.sh` | removes every TenantSafe container and config root |
| `.run_state` | one experiment id per line, appended on success |
| `../results/run-logs/` | full stdout per experiment |

## Reproducibility notes

- **Alloy is pinned to 6.2.0** and verified by SHA-256. The original results were
  produced with a copy that lived in a temporary directory and has since been
  deleted; 6.2.0 was checked against the recorded verdicts before being adopted,
  and reproduces the mutation suite 15/15.
- `TS_WORKDIR` (default `~/.tenantsafe/work`) holds per-container config roots.
  It is outside the repository and safe to delete between runs.
- The runner never touches `rka-*` or any container it did not create.
