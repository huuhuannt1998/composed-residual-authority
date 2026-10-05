#!/bin/bash
# M9 (paper-loop round 1): the necessity test is the empirical basis for CRD=2 but
# ran n=1 per arm. Repeat it so the claim rests on a distribution, not one trial.
set -u
cd "$(dirname "$0")" || exit 2
N=${1:-30}
out=../results/necessity_reps.tsv
echo -e "trial\tfull\tminus_socket\tminus_automation\tverdict" > "$out"
for i in $(seq 1 "$N"); do
  ./run_all.sh --only necessity >/dev/null 2>&1
  log=../results/run-logs/necessity.log
  full=$(grep -oE 'full residue present *: *(True|False)' "$log" | awk '{print $NF}')
  ms=$(grep -oE 'collapses without socket *: *(True|False)' "$log" | awk '{print $NF}')
  ma=$(grep -oE 'collapses without automation: *(True|False)' "$log" | awk '{print $NF}')
  v=$(grep -oE 'A5 NECESSITY: [A-Z]+' "$log" | awk '{print $NF}')
  echo -e "$i\t$full\t$ms\t$ma\t$v" >> "$out"
  printf "  trial %2d  full=%s  -socket=%s  -automation=%s  %s\n" "$i" "$full" "$ms" "$ma" "$v"
  sed -i '' '/^necessity$/d' .run_state
done
echo
awk -F'\t' 'NR>1{n++; if($2=="True")f++; if($3=="True")s++; if($4=="True")a++; if($5=="PASS")p++}
END{printf "  n=%d  full-residue %d/%d  collapses-without-socket %d/%d  collapses-without-automation %d/%d  PASS %d/%d\n",n,f,n,s,n,a,n,p,n}' "$out"
