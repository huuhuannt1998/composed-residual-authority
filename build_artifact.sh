#!/bin/bash
# Assemble the artifact package in the structure the mock review specifies (sec 24).
set -e
R=$(cd "$(dirname "$0")" && pwd); A=$R/artifact
rm -rf "$A"; mkdir -p "$A"/{models/{mutants,expected-results},home-assistant/{docker,versions,scripts,probes,patch-session-revoke,patch-principal-reresolve},experiments/{version-study,operation-matrix,lifetime,performance,regression,second-ecosystem},docs-corpus,coding,analysis,results,tools}

# --- models -----------------------------------------------------------------
cp "$R"/models/tenantsafe.als "$R"/models/tenantsafe_crd.als "$R"/models/tenantsafe_platforms.als \
   "$R"/models/tenantsafe_time_transfer.als "$R"/models/tenantsafe_channels.als "$A"/models/
cp "$R"/models/tenantsafe_mutants.als "$R"/models/tenantsafe_depth.als "$A"/models/mutants/
cp "$R"/models/*.spthy "$A"/models/ 2>/dev/null || true
cp -r "$R"/results/tenantsafe_mutants "$R"/results/tenantsafe_depth "$R"/results/tenantsafe_crd \
      "$R"/results/scope_sweep "$A"/models/expected-results/ 2>/dev/null || true

# --- home assistant ---------------------------------------------------------
cp "$R"/models/tsmon_defenseA.py "$A"/home-assistant/patch-session-revoke/
cp "$R"/models/tsmon_patch.py    "$A"/home-assistant/patch-principal-reresolve/
cp "$R"/models/tsmon_unpatch.py  "$A"/home-assistant/scripts/
cp "$R"/experiments/r3_probe.py "$R"/experiments/r3_read_probe.py "$R"/experiments/e76_deputy.py \
   "$R"/experiments/e76b_admin_surface.py "$A"/home-assistant/probes/ 2>/dev/null || true
cat > "$A"/home-assistant/docker/run.sh <<'SH'
#!/bin/bash
# Bring up an unpatched Home Assistant on $2 (default 8123) at version $1.
V=${1:-2026.8.3}; P=${2:-8123}; N=${3:-tenantsafe-repro}
docker rm -f "$N" 2>/dev/null
mkdir -p ./cfg-$N
docker run -d --name "$N" -p $P:8123 -v "$PWD/cfg-$N:/config" -e TZ=UTC homeassistant/home-assistant:$V
until [ "$(curl -s -m 3 -o /dev/null -w '%{http_code}' http://localhost:$P/)" = "302" ]; do sleep 5; done
echo "$N up on :$P (version $V)"
SH
chmod +x "$A"/home-assistant/docker/run.sh
printf '2024.12.0\n2026.6.4\n2026.7.4\n2026.8.3\n' > "$A"/home-assistant/versions/tested.txt

# --- experiments ------------------------------------------------------------
cp "$R"/experiments/p1e6_version_study.py "$R"/experiments/run_version_study.sh "$A"/experiments/version-study/
cp "$R"/experiments/p1e7_matrix.py "$R"/experiments/p1e7b_sessions.py "$A"/experiments/operation-matrix/
cp "$R"/experiments/p1e8_lifetime.py "$R"/experiments/p1e8b_lifetime_long.py "$A"/experiments/lifetime/
cp "$R"/experiments/p1e11_benchmark.py "$R"/experiments/p1e11b_micro.py "$A"/experiments/performance/
cp "$R"/experiments/p1e12_regression.py "$A"/experiments/regression/
cp "$R"/experiments/p2e16_openhab.py "$R"/experiments/p2e16b_openhab_sse.py \
   "$R"/experiments/p2e16c_openhab_reps.py "$A"/experiments/second-ecosystem/
cp "$R"/experiments/p0e3_capability_matrix.py "$R"/experiments/e34_necessity.py \
   "$R"/experiments/e63_closure.py "$R"/experiments/e66_false_positive.py \
   "$R"/experiments/p1e9_deputy_generality.py "$A"/experiments/
cp "$R"/experiments/p1e15_scope_sweep.sh "$A"/experiments/

# --- tools ------------------------------------------------------------------
cp -r "$R"/tools/residue_finder.py "$R"/tools/specs "$A"/tools/
cp "$R"/experiments/p2e19_severity.py "$A"/analysis/

# --- docs corpus ------------------------------------------------------------
cp -r "$R"/coding/snapshots "$A"/docs-corpus/
cp "$R"/coding/sources.txt "$R"/coding/snapshot.sh "$R"/coding/verify_corpus.py "$A"/docs-corpus/

# --- coding -----------------------------------------------------------------
cp "$R"/coding/codebook.md "$R"/coding/kappa.py "$R"/coding/conformance.py "$R"/coding/gate.py "$A"/coding/
python3 - "$R" "$A" <<'PY'
import importlib.util,sys,csv,pathlib
R,A=sys.argv[1],sys.argv[2]
spec=importlib.util.spec_from_file_location("k",f"{R}/coding/kappa.py")
m=importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(m)
except SystemExit: pass
out=pathlib.Path(A)/"coding"
def dump(d,name):
    with open(out/name,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["platform","transition","label"])
        for (p,t),v in sorted(d.items()): w.writerow([p,t,v])
# NOTE the file names: both passes are by the SAME analyst, so nothing here is
# called coder1/coder2, which would imply two independent humans.
dump(m.pass1,"pass1_original.csv")
dump(m.pass2,"pass2_blind_recode.csv")
dump(m.pass2,"adjudicated.csv")
print("  coding csvs written")
PY

# --- analysis / results -----------------------------------------------------
cp "$R"/RESULTS.md "$R"/EXPERIMENTS.md "$R"/FEEDBACK_COMPLIANCE.md "$R"/REVIEW.md \
   "$R"/research_design_detailed.md "$R"/m1_jobb_semantics_harvest.md "$A"/results/ 2>/dev/null || true
cp "$R"/results/scale_samples.csv "$A"/results/ 2>/dev/null || true
for f in /tmp/matrix_p1e7.json /tmp/p1e7b.json /tmp/p1e11_bench.json /tmp/p1e11_micro.json \
         /tmp/p1e12_8141.json /tmp/p1e12_8142.json /tmp/p2e16_openhab.json /tmp/p2e16b_sse.json \
         /tmp/p2e16c_reps.json /tmp/p2e19_severity.json /tmp/p1e8b_rows.json; do
  [ -f "$f" ] && cp "$f" "$A"/results/ || true
done
echo "artifact assembled at $A"
du -sh "$A"
