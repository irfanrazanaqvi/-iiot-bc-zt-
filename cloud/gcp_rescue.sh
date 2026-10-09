#!/usr/bin/env bash
# Rescue / resume for a run of cloud/gcp_run.sh whose orchestrator was interrupted (e.g. Cloud Shell reconnected)
# while the five VMs are still up.  The experiment itself runs on the client VM, so completed work is kept:
#   1. stops the current experiment and gateway on the client VM,
#   2. pulls the latest repo code onto the client VM (gateway fix: receipts fetched in parallel from the nearest validator),
#   3. restarts the gateway and re-runs ONLY the architectures that did not finish cleanly (normally the blockchain one),
#   4. merges the old and new results, analyses, downloads to ~/results_gcp and ~/results_gcp.tgz, deletes the VMs.
# Usage (Cloud Shell, project set, VMs iiotbc-* running):  bash cloud/gcp_rescue.sh      (KEEP=1 keeps the VMs)
set -uo pipefail
PFX=${PFX:-iiotbc}
OUTDIR=${OUTDIR:-$HOME/results_gcp}
declare -A Z=( [v1]=us-central1-a [v2]=europe-west1-b [v3]=asia-south1-a [v4]=asia-southeast1-a [c]=europe-west1-b )
KEYS=(v1 v2 v3 v4 c)
say() { printf '\n=== %s\n' "$*"; }
vm() { echo "$PFX-$1"; }
ssh_() { local k=$1; shift; timeout 200 gcloud compute ssh "$(vm "$k")" --zone "${Z[$k]}" --quiet --command "$*" -- -o StrictHostKeyChecking=no -o ConnectTimeout=20 2>/dev/null; }
ip_()  { gcloud compute instances describe "$(vm "$1")" --zone "${Z[$1]}" --format='get(networkInterfaces[0].networkIP)'; }
cleanup() {
  if [ "${KEEP:-0}" = "1" ]; then say "KEEP=1: VMs left running (delete them yourself to stop charges)"; return; fi
  say "Deleting VMs (stops all charges)"
  for k in "${KEYS[@]}"; do gcloud compute instances delete "$(vm $k)" --zone "${Z[$k]}" --quiet >/dev/null 2>&1 & done
  wait
}

PROJECT=${PROJECT:-$(gcloud config get-value project 2>/dev/null)}
[ -n "$PROJECT" ] && gcloud config set project "$PROJECT" >/dev/null 2>&1
for k in "${KEYS[@]}"; do
  gcloud compute instances describe "$(vm $k)" --zone "${Z[$k]}" --format='get(status)' 2>/dev/null | grep -q RUNNING || { echo "VM $(vm $k) is not running. Nothing to rescue (start a new run with cloud/gcp_run.sh). Not deleting anything."; exit 1; }
done
trap cleanup EXIT
say "All five VMs are running. Looking at the first run"
declare -A IP; for k in "${KEYS[@]}"; do IP[$k]=$(ip_ "$k"); done
ssh_ c 'tail -2 /tmp/run.log | cut -c1-120'
ARCHS=""
chk() { ssh_ c "grep -qE \"$1\" /tmp/run.log" && echo ok || echo missing; }
[ "$(chk '^b0 security 9 done')" = ok ] || ARCHS="$ARCHS b0"
[ "$(chk '^b1 revocation 29 ')" = ok ] || ARCHS="$ARCHS b1"
[ "$(chk '^b2 revocation 29 ')" = ok ] || ARCHS="$ARCHS b2"
ARCHS="$ARCHS bcz"
BACKEND=$(ssh_ c "/opt/venv/bin/python -c 'import eth_keys.backends as b;print(type(b.get_backend()).__name__)'")
echo "signature backend on the client: $BACKEND"
case "$BACKEND" in *CoinCurve*) ;; *) echo "installing the fast signature library and re-running all architectures"; ssh_ c '/opt/venv/bin/pip install --quiet coincurve' ; ARCHS="b0 b1 b2 bcz";; esac
echo "architectures to (re-)run: $ARCHS"

say "Stopping the old experiment and gateway; updating the code"
ssh_ c "pkill -f '[e]xperiments.run_all'; pkill -f '[u]vicorn'; sleep 2; rm -rf /tmp/results_run1; cp -r /tmp/results /tmp/results_run1; sudo git -C /opt/repo pull -q 2>&1 | tail -2; sudo chmod -R a+rwX /opt/repo; echo updated"
RPCS="http://${IP[v1]}:8545,http://${IP[v2]}:8545,http://${IP[v3]}:8545,http://${IP[v4]}:8545"
ssh_ c "cd /opt/repo && ulimit -n 65535 2>/dev/null; GATEWAY_SEED=\$(openssl rand -hex 8) BESU_RPCS=$RPCS WATCH_RPC=http://${IP[v2]}:8545 nohup /opt/venv/bin/python -m uvicorn experiments.gateway_multi:app --port 9000 --timeout-keep-alive 300 --backlog 4096 > /tmp/gw2.log 2>&1 < /dev/null &"
GW=""
for t in $(seq 40); do
  GW=$(ssh_ c "curl -s -m 5 localhost:9000/health") && [ -n "$GW" ] && break
  echo "  waiting for the gateway ($t/40)"; GW=""; sleep 5
done
[ -n "$GW" ] || { echo "gateway did not start:"; ssh_ c 'tail -20 /tmp/gw2.log'; exit 1; }
echo "gateway: $GW"
ssh_ c "cd /opt/repo && rm -rf /tmp/results2 && mkdir -p /tmp/results2 && (ulimit -n 65535 2>/dev/null; ADMIN_PRIVATE_KEY=\$(cat /tmp/deployer.key) BESU_RPCS=http://${IP[v1]}:8545 nohup sh -c '/opt/venv/bin/python -m experiments.run_all --out /tmp/results2 --archs $ARCHS > /tmp/run2.log 2>&1; touch /tmp/results2/DONE' > /dev/null 2>&1 < /dev/null &)"

say "Experiment running again for: $ARCHS (progress below)"
for t in $(seq 400); do
  if ssh_ c 'test -f /tmp/results2/DONE'; then break; fi
  echo "$(date +%H:%M) $(ssh_ c 'tail -1 /tmp/run2.log | cut -c1-110')"; sleep 45
done

say "Merging, analysing and collecting results"
ssh_ c 'cp /tmp/run2.log /tmp/gw2.log /tmp/results2/ 2>/dev/null; test -f /tmp/results2/meta.json' || { echo "The second run crashed:"; ssh_ c 'tail -25 /tmp/run2.log | cut -c1-200'; }
WORK=$(mktemp -d); cd "$WORK"
for k in v1 v2 v3 v4; do gcloud compute scp --zone "${Z[$k]}" --quiet "$(vm $k):/tmp/sampler_$k.csv" . 2>/dev/null; done
for k in v1 v2 v3 v4; do gcloud compute scp --zone "${Z[c]}" --quiet "sampler_$k.csv" "$(vm c):/tmp/" 2>/dev/null; done
MERGE=$(echo $ARCHS | tr ' ' ',')
ssh_ c "rm -rf /tmp/final && cd /opt/repo && /opt/venv/bin/python experiments/merge_runs.py /tmp/results_run1 /tmp/results2 /tmp/final $MERGE && cp /tmp/sampler_*.csv /tmp/final/ && cp /opt/repo/experiments/deployment_v2.json /tmp/final/ && cp -r /tmp/results_run1 /tmp/final/run1_raw && cp -r /tmp/results2 /tmp/final/run2_raw && /opt/venv/bin/python experiments/analyze.py /tmp/final > /tmp/final/analyze_stdout.txt 2>&1; tail -3 /tmp/final/analyze_stdout.txt"
rm -rf "$OUTDIR"; mkdir -p "$OUTDIR"
gcloud compute scp --recurse --zone "${Z[c]}" --quiet "$(vm c):/tmp/final/*" "$OUTDIR/" 2>/dev/null
( cd "$HOME" && tar czf results_gcp.tgz "$(basename "$OUTDIR")" )
say "DONE. Results are in $OUTDIR and $HOME/results_gcp.tgz"
echo "Download the archive with:   cloudshell download $HOME/results_gcp.tgz"
echo "Then send me results_gcp.tgz. The VMs are deleted automatically now."
