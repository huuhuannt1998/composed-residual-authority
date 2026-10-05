# Composed Residual Authority — code and results (anonymized mirror)

Formal models and runtime evidence for **authority that survives a household
transition** in smart homes: the capabilities a principal may no longer exercise
by policy but can still bring about along some reachable trace. The central
object is the *authority residue*; revocation-completeness is exactly its
emptiness. A residue is **composed** when no single surviving object is
sufficient to produce the effect, and **hidden** when no surviving object names
the removed principal, so the authorization state an auditor inspects looks
clean.

This is the anonymized mirror of the code-and-results snapshot that the paper's
artifact appendix links. The manuscript is not in this repository.

## What is here

| Path | Contents |
|---|---|
| `models/` | Alloy sources (`*.als`) and Tamarin sources (`*.spthy`): the composition-depth model, the depth-1..4 constructions, the eight revocation mutants, the platform and channel models, and the prototype defense patches `tsmon_defenseA.py` (session termination) and `tsmon_patch.py` (principal re-resolution) with `tsmon_unpatch.py` |
| `experiments/` | the measurement scripts (Python and shell) and the registry `MANIFEST.tsv`; all software-only, every script drives containers on `localhost` only |
| `tools/` | `residue_finder.py` (witness, minimal support, composition depth, audit-visible objects), `ha_auditor.py` (configuration auditor), `crossval.py` (documented-reading verdicts), and the platform `specs/` |
| `coding/` | the documentation-study codebook, both coding passes, the reliability computation, and the frozen vendor-documentation corpus under `snapshots/` with its hashes; `verify_corpus.py` checks it |
| `results/` | the result logs and files behind every table and figure: `run-logs/`, the `replication_2026-10-03/` and `homebridge_setupcode_2026-10-04/` repetition sets (each with a `SHA256SUMS`), the `lifetime/` series, the Alloy/Tamarin receipts under `tenantsafe*/` and `scope_sweep/`, and the consolidated JSON/TSV |

Each paper table names the log or result file it is regenerated from.

## Reproducing

Requires Docker, Python 3.11+ with `aiohttp` and `websockets`, and an Alloy 6
distribution (pointed to by `ALLOY_TOOLS_DIR`). No hardware is used anywhere.
Every experiment uses virtual entities in its own containers and touches no
third party's system.

```bash
python3 coding/verify_corpus.py          # re-hash the frozen documentation corpus
cat experiments/README.md                # the one-experiment-at-a-time runner
```

The runtime experiments need the images `homeassistant/home-assistant`
(2024.12, 2026.6.4, 2026.7.4, 2026.8.3), `openhab/openhab` (4.3.2, 5.2.1) and a
digest-pinned `homebridge/homebridge`; the formal checks need Alloy 6.2.0 and
Tamarin.

## Integrity self-checks

- `results/replication_2026-10-03/SHA256SUMS` and
  `results/homebridge_setupcode_2026-10-04/SHA256SUMS` list the digests of the
  files produced in those runs; `shasum -a 256 -c SHA256SUMS` passes in each
  directory on the files shipped here.
- `coding/verify_corpus.py` re-hashes the archived documentation pages against
  `coding/snapshots/MANIFEST.tsv`. It reports 6 of 10 rows matched, 0 drifted,
  0 missing; the other 4 rows are URLs with no archived file (they were not
  saved), as the manifest records. No archived page has drifted.

## Anonymization

This is a curated copy for double-anonymous review. It leaves out the project's
internal process notes (venue-readiness, review-response, feedback, claim-
ratification, contribution and research-design documents), the agent planning
and specification notes, the artifact-packaging script, and the original README,
none of which a reviewer needs to reproduce the work.

The Homebridge servers' own container logs are not included here, by design;
they are carried only by the supplementary archive, in redacted form. The
Homebridge result files in this mirror (`results/replication_2026-10-03/
homebridge_*.json`, `results/homebridge_setupcode_2026-10-04/setupcode_*`)
record only event counts, HTTP statuses, and the *names* of payload fields such
as `pin` and `setupUri`; no HomeKit setup code or setup URI value appears
anywhere in this mirror.

Absolute home-directory and temporary-session paths in the result logs were
replaced by `~`, `<artifact-root>` and `<tmp>`; no measured value was changed.
Ten edited auditor logs are listed in
`results/replication_2026-10-03/SHA256SUMS`, and that manifest was updated to
their new digests (and the omitted container-log rows removed) so the self-check
still passes. Comments in `models/tenantsafe_base.spthy` and
`models/tenantsafe_channels.als` that named a separate sibling project and its
internal identifier were rewritten to "a sibling project at the Matter protocol
layer"; the substrate reuse they describe is genuine and is preserved.

`TenantSafe` is the project's internal code name; it appears in model and result
file names and is not an author or institution identity. The internal tracking
tool is referred to as `RKA`/`rka-*` in a few scripts and run-log status lines;
likewise not an identity. Both are retained because editing them would touch
file names and recorded logs without improving anonymity.

## Responsible use

Everything here runs against the researcher's own disposable Docker containers
with virtual entities; nothing targets or reaches any third party's system, and
no credentials or tokens of any third party are included. The code reproduces
the residue for measurement and is not packaged as an attack tool: it carries no
guidance for retaining covert access, captures no secret values, and the
defenses (`models/tsmon_*.py`) are included alongside the probes. The smart-home
vendor findings reproduced here are not yet disclosed to the affected projects.
