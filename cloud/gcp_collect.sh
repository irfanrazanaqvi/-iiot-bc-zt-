#!/usr/bin/env bash
# Re-attach to a run of cloud/gcp_run.sh whose Cloud Shell session was disconnected while the VMs kept running.
# The experiment runs on the client VM, so it continues without the orchestrator. This script waits for it to finish
# (shows progress), then does what gcp_run.sh would have done: collects samplers, analyses, downloads to ~/results_gcp
# and ~/results_gcp.tgz, and deletes the VMs.   Usage:  bash cloud/gcp_collect.sh     (KEEP=1 keeps the VMs)
set -uo pipefail
PFX=${PFX:-iiotbc}; OUTDIR=${OUTDIR:-$HOME/results_gcp}
declare -A Z=( [v1]=us-central1-a [v2]=europe-west1-b [v3]=asia-south1-a [v4]=asia-southeast1-a [c]=europe-west1-b )
KEYS=(v1 v2 v3 v4 c)
say() { printf '\n=== %s\n' "$*"; }
vm() { echo "$PFX-$1"; }
ssh_() { local k=$1; shift; timeout 150 gcloud compute ssh "$(vm "$k")" --zone "${Z[$k]}" --quiet --command "$*" -- -o StrictHostKeyChecking=no -o ConnectTimeout=20 2>/dev/null; }
cleanup() {
  if [ "${KEEP:-0}" = "1" ]; then say "KEEP=1: VMs left running (delete them yourself to stop charges)"; return; fi
  say "Deleting VMs (stops all charges)"
  for k in "${KEYS[@]}"; do gcloud compute instances delete "$(vm $k)" --zone "${Z[$k]}" --quiet >/dev/null 2>&1 & done
  wait
}
for k in "${KEYS[@]}"; do
  gcloud compute instances describe "$(vm $k)" --zone "${Z[$k]}" --format='get(status)' 2>/dev/null | grep -q RUNNING || { echo "VM $(vm $k) is not running. Nothing to collect. Not deleting anything."; exit 1; }
done
trap cleanup EXIT
say "VMs are running. Last line of the experiment log:"
ssh_ c 'tail -1 /tmp/run.log | cut -c1-120'
for t in $(seq 400); do
  if ssh_ c 'test -f /tmp/results/DONE'; then break; fi
  echo "$(date +%H:%M) $(ssh_ c 'tail -1 /tmp/run.log | cut -c1-110')"; sleep 45
done
ssh_ c 'cp /tmp/run.log /tmp/gw0.log /tmp/results/ 2>/dev/null'
ssh_ c 'test -f /tmp/results/meta.json' || { echo "The experiment did not finish cleanly. Last log lines:"; ssh_ c 'tail -25 /tmp/run.log | cut -c1-200'; echo "Partial data will still be collected."; }
say "Analysing and collecting results"
WORK=$(mktemp -d); cd "$WORK"
for k in v1 v2 v3 v4; do gcloud compute scp --zone "${Z[$k]}" --quiet "$(vm $k):/tmp/sampler_$k.csv" . 2>/dev/null; done
for k in v1 v2 v3 v4; do gcloud compute scp --zone "${Z[c]}" --quiet "sampler_$k.csv" "$(vm c):/tmp/results/" 2>/dev/null; done
ssh_ c 'cp /tmp/sampler_c.csv /tmp/results/sampler_c.csv; cp /opt/repo/experiments/deployment_v2.json /tmp/results/ 2>/dev/null; cd /opt/repo && /opt/venv/bin/python experiments/analyze.py /tmp/results > /tmp/results/analyze_stdout.txt 2>&1; tail -3 /tmp/results/analyze_stdout.txt'
rm -rf "$OUTDIR"; mkdir -p "$OUTDIR"
gcloud compute scp --recurse --zone "${Z[c]}" --quiet "$(vm c):/tmp/results/*" "$OUTDIR/" 2>/dev/null
( cd "$HOME" && tar czf results_gcp.tgz "$(basename "$OUTDIR")" )
say "DONE. Results are in $OUTDIR and $HOME/results_gcp.tgz"
echo "Download the archive with:   cloudshell download $HOME/results_gcp.tgz"
