# Composed Residual Authority

Formal model and runtime evidence for **authority that survives a household
transition** in smart homes — the capabilities a principal may no longer
exercise by policy but can still bring about along some reachable trace.

The central object is the *authority residue*. Revocation-completeness is
exactly its emptiness, which a model evaluated at an instant cannot express
because it has no transition and no post-state. A residue is **composed** when
no single surviving object is sufficient to produce the effect — its minimal
sufficient support has size two or more — and **hidden** when no surviving
object names the removed principal, so the authorization state an auditor
inspects looks clean.

## What is here

| Path | Contents |
|---|---|
| `models/` | Alloy and Tamarin sources. `tenantsafe_crd.als` is the composition-depth model; `tenantsafe_mutants.als` mutates the revocation semantics; `tenantsafe_depth.als` constructs depths 1–4 |
| `experiments/` | Runtime measurements against Home Assistant and openHAB, all software-only |
| `tools/` | `residue_finder.py` — consumes a platform transition spec and returns the witness chain, minimal support, composition depth, and audit-visible objects |
| `coding/` | Documentation-study codebook, both coding passes, reliability computation, and the frozen source corpus with hashes |
| `results/` | Alloy receipts and consolidated results |
| `build_artifact.sh` | Reassembles the full artifact package |

The manuscript is not in this repository.

## Reproducing

Requires Docker, Python 3.11+ with `aiohttp` and `websockets`, and an Alloy 6
distribution (pointed at by `ALLOY_TOOLS_DIR`). No Java install is needed —
Alloy runs through `eclipse-temurin:21-jre`. No hardware is used anywhere.

```bash
./build_artifact.sh                 # assemble artifact/ with its own README
python3 coding/verify_corpus.py     # 10/10 documentation snapshots still hash-match
```

Bring up an unpatched Home Assistant and run the operation matrix:

```bash
docker run -d --name ts-repro -p 8123:8123 -v "$PWD/cfg-repro:/config" \
  homeassistant/home-assistant:2026.8.3
python3 experiments/p1e7_matrix.py 8123 30
```

## Principal results

- **The residue is graded by role and deterministic.** Across 30 independent
  trials per arm every cell is 0/30 or 30/30. A removed member retains reading;
  a removed administrator retains six of eight operations.
- **Actuation is composed.** Direct actuation is refused 0/30 even for a removed
  administrator, while actuation induced through a household automation succeeds
  30/30 — a runtime corroboration of composition depth 2, arrived at without the
  model.
- **The defect is one transition, not the authorization model.** Deactivation,
  explicit token revocation, and new-connection authentication are all complete.
  Only deletion leaves an established connection running.
- **It is not one platform.** openHAB is clean on its request path but a stream
  opened before the transition keeps delivering after the account is deleted, in
  5 trials of 5. Validating a credential at connection establishment and never
  re-checking it is a pattern, not a quirk.
- **The model discriminates.** Eight mutated revocation semantics, 15 checks,
  all matching predicted verdicts; only the session-plus-automation mutant is
  reported as composed.
- **Closing it costs nothing measurable.** Terminating sessions on removal takes
  the residual capability count from 8 to 0, and no defense shows a latency
  difference from baseline that five runs of 10,000 operations can resolve.

## Status and scope

Home Assistant and openHAB results are runtime-confirmed. Google Home, Amazon
Alexa and Samsung SmartThings contribute **documented-semantics evidence only** —
those systems were not observed, and their results are not runtime confirmations.

The determinacy coding was performed twice by the **same analyst**, so the
reported κ measures test-retest stability, not agreement between independent
coders. A second-coder pass is open work.

## Responsible use

The Home Assistant finding is **not yet disclosed to the project**. The code here
reproduces the residue for measurement; it is not packaged as an attack tool and
carries no guidance for retaining covert access. The remediation is two lines and
is described in `RESULTS.md`. If you are affected today, deactivating a member
before deleting them terminates their sessions and requires no code change.

Please do not make this repository public while the finding remains undisclosed.
