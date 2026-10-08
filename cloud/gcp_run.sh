#!/usr/bin/env bash
# One-command distributed experiment on Google Cloud, run from Google Cloud Shell.
#
#   git clone https://github.com/irfanrazanaqvi/-iiot-bc-zt-.git && cd -- -iiot-bc-zt-
#   MODE=quick bash cloud/gcp_run.sh      # ~15 min smoke test first (recommended)
#   bash cloud/gcp_run.sh                 # full run, about 60-70 min
#
# Creates 4 Besu validator VMs in 4 regions (US, Belgium, Mumbai, Singapore) plus 1 client VM
# (gateway + load generator + analysis) in Belgium, all on the default VPC (internal IPs only between
# them), runs experiments/run_all.py for the 4 architectures, runs experiments/analyze.py, copies the
# results to ~/results_gcp, and DELETES every VM at exit (set KEEP=1 to keep them).
set -uo pipefail
MODE=${MODE:-full}
REPO_URL=${REPO_URL:-https://github.com/irfanrazanaqvi/-iiot-bc-zt-.git}
PFX=${PFX:-iiotbc}
VT=${VT:-e2-standard-2}      # validator machine type
CT=${CT:-e2-standard-2}      # client machine type
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTDIR=${OUTDIR:-$HOME/results_gcp}
declare -A Z=( [v1]=us-central1-a [v2]=europe-west1-b [v3]=asia-south1-a [v4]=asia-southeast1-a [c]=europe-west1-b )
KEYS=(v1 v2 v3 v4 c)
ARGS=""; [ "$MODE" = "quick" ] && ARGS="--quick"

say() { printf '\n=== %s\n' "$*"; }
vm() { echo "$PFX-$1"; }
ssh_() { local k=$1; shift; timeout 150 gcloud compute ssh "$(vm "$k")" --zone "${Z[$k]}" --quiet --command "$*" -- -o StrictHostKeyChecking=no -o ConnectTimeout=20 2>/dev/null; }
ip_()  { gcloud compute instances describe "$(vm "$1")" --zone "${Z[$1]}" --format='get(networkInterfaces[0].networkIP)'; }

cleanup() {
  if [ "${KEEP:-0}" = "1" ]; then say "KEEP=1: VMs left running. Delete them with: gcloud compute instances delete $(for k in "${KEYS[@]}"; do printf '%s ' "$(vm $k)"; done) (one --zone each)"; return; fi
  say "Deleting VMs (stops all charges)"
  for k in "${KEYS[@]}"; do gcloud compute instances delete "$(vm $k)" --zone "${Z[$k]}" --quiet >/dev/null 2>&1 & done
  wait
}
trap cleanup EXIT

PROJECT=${PROJECT:-$(gcloud config get-value project 2>/dev/null)}
[ -n "$PROJECT" ] || PROJECT=${GOOGLE_CLOUD_PROJECT:-}
[ -n "$PROJECT" ] || PROJECT=$(gcloud projects list --format='value(projectId)' 2>/dev/null | head -1)
[ -n "$PROJECT" ] || { echo "No Google Cloud project found. Run: gcloud config set project YOUR_PROJECT_ID"; exit 1; }
gcloud config set project "$PROJECT" >/dev/null 2>&1
say "Project: $PROJECT   mode: $MODE"
gcloud services enable compute.googleapis.com >/dev/null 2>&1
gcloud compute firewall-rules describe iiotbc-internal >/dev/null 2>&1 || \
  gcloud compute firewall-rules create iiotbc-internal --network default --allow tcp,udp,icmp --source-ranges 10.128.0.0/9 >/dev/null 2>&1 || true

say "Creating 5 VMs (needs about 10 vCPUs of quota)"
for k in "${KEYS[@]}"; do
  role=validator; mt=$VT; [ "$k" = c ] && { role=client; mt=$CT; }
  gcloud compute instances create "$(vm $k)" --zone "${Z[$k]}" --machine-type "$mt" \
    --image-family ubuntu-2404-lts-amd64 --image-project ubuntu-os-cloud --boot-disk-size 30GB \
    --metadata "role=$role,repo=$REPO_URL" --metadata-from-file startup-script="$HERE/vm_setup.sh" >/dev/null &
done
wait
for k in "${KEYS[@]}"; do gcloud compute instances describe "$(vm $k)" --zone "${Z[$k]}" >/dev/null 2>&1 || { echo "VM $(vm $k) was not created (quota or region problem). Aborting."; exit 1; }; done

say "Waiting for VM setup (Java, Besu, repo)"
for k in "${KEYS[@]}"; do
  for i in $(seq 60); do ssh_ "$k" 'test -f /opt/ready' && break; sleep 15; done
  ssh_ "$k" 'test -f /opt/ready' || { echo "$(vm $k) did not finish setup. Last lines of its log:"; ssh_ "$k" 'tail -40 /var/log/vm_setup.log; sudo journalctl -u google-startup-scripts --no-pager | tail -15'; exit 1; }
  echo "$(vm $k) ready"
done
declare -A IP; for k in "${KEYS[@]}"; do IP[$k]=$(ip_ "$k"); echo "$k ${IP[$k]}"; done

say "Generating validator keys and genesis (on the client VM)"
ssh_ c 'cd /tmp && rm -rf net qbft.json && cp /opt/repo/network/qbft-config.json qbft.json && /opt/besu-24.7.0/bin/besu operator generate-blockchain-config --config-file=qbft.json --to=net --private-key-file-name=key >/dev/null 2>&1 && tar czf net.tgz net'
WORK=$(mktemp -d); cd "$WORK"
gcloud compute scp --zone "${Z[c]}" --quiet "$(vm c):/tmp/net.tgz" . 2>/dev/null && tar xzf net.tgz
i=0; for d in net/keys/*/; do i=$((i+1)); k=v$i
  gcloud compute scp --zone "${Z[$k]}" --quiet net/genesis.json "$d/key" "$(vm $k):/tmp/" 2>/dev/null
done

say "Starting the four validators"
BOOT=""
for k in v1 v2 v3 v4; do
  echo "starting $k ..."
  ssh_ "$k" "cat > /tmp/start.sh <<'EOS'
#!/bin/bash
cd /tmp && rm -rf data
export JAVA_OPTS=-Xmx3g
exec /opt/besu-24.7.0/bin/besu --data-path=/tmp/data --genesis-file=/tmp/genesis.json --node-private-key-file=/tmp/key --rpc-http-enabled --rpc-http-api=ETH,NET,QBFT,WEB3,ADMIN --rpc-http-host=0.0.0.0 --rpc-http-port=8545 --rpc-http-max-active-connections=2000 --host-allowlist=* --p2p-host=${IP[$k]} --p2p-port=30303 --min-gas-price=0 $BOOT
EOS
chmod +x /tmp/start.sh; setsid nohup /tmp/start.sh > /tmp/besu.log 2>&1 < /dev/null & sleep 1; echo started"
  if [ "$k" = v1 ]; then
    E=""
    for t in $(seq 30); do sleep 5
      E=$(ssh_ v1 "curl -s -X POST -H 'Content-Type: application/json' --data '{\"jsonrpc\":\"2.0\",\"method\":\"net_enode\",\"params\":[],\"id\":1}' localhost:8545 | python3 -c 'import sys,json;print(json.load(sys.stdin)[\"result\"])'") && [ -n "$E" ] && break
      echo "  waiting for validator 1 ($t/30)"; E=""
    done
    [ -n "$E" ] || { echo "validator 1 did not start. Its log:"; ssh_ v1 'tail -30 /tmp/besu.log'; exit 1; }
    echo "enode: $E"; BOOT="--bootnodes=$E"
  fi
done
rpc_() { ssh_ "$1" "curl -s -m 5 -X POST -H 'Content-Type: application/json' --data '{\\"jsonrpc\\":\\"2.0\\",\\"method\\":\\"$2\\",\\"params\\":[],\\"id\\":1}' http://localhost:8545"; }
BN=0
for t in $(seq 40); do
  R=$(ssh_ c "curl -s -m 5 -X POST -H 'Content-Type: application/json' --data '{\\"jsonrpc\\":\\"2.0\\",\\"method\\":\\"eth_blockNumber\\",\\"params\\":[],\\"id\\":1}' http://${IP[v4]}:8545") || R=""
  BN=$(echo "$R" | python3 -c 'import sys,json;print(int(json.load(sys.stdin)["result"],16))' 2>/dev/null || echo 0)
  echo "  block height via validator 4: ${BN:-0}  (try $t/40)"
  [ "${BN:-0}" -ge 3 ] && break; sleep 5
done
[ "${BN:-0}" -ge 3 ] || {
  echo; echo "network did not start. Diagnostics per validator:"
  for k in v1 v2 v3 v4; do
    echo "---- $k peers: $(rpc_ $k net_peerCount)   block: $(rpc_ $k eth_blockNumber)"
    ssh_ "$k" 'tail -12 /tmp/besu.log | cut -c1-220'
  done
  exit 1; }
echo "network is producing blocks"

say "Deploying contracts, starting gateway, samplers and the experiment"
RPCS="http://${IP[v1]}:8545,http://${IP[v2]}:8545,http://${IP[v3]}:8545,http://${IP[v4]}:8545"
for k in "${KEYS[@]}"; do ssh_ "$k" "nohup python3 /opt/repo/experiments/sampler.py /tmp/sampler_$k.csv > /dev/null 2>&1 < /dev/null &"; done
ssh_ c "cd /opt/repo && export NODE_PATH=/opt/nd/node_modules && openssl rand -hex 32 | sed 's/^/0x/' > /tmp/deployer.key && RPC_URL=http://${IP[v1]}:8545 DEPLOYER_PRIVATE_KEY=\$(cat /tmp/deployer.key) node experiments/deploy_v2.js" | tail -5
ssh_ c "cd /opt/repo && GATEWAY_SEED=\$(openssl rand -hex 8) BESU_RPCS=$RPCS nohup /opt/venv/bin/python -m uvicorn experiments.gateway_multi:app --port 9000 > /tmp/gw.log 2>&1 < /dev/null &"
sleep 20
ssh_ c "curl -s localhost:9000/health"; echo
ssh_ c "cd /opt/repo && mkdir -p /tmp/results && (ADMIN_PRIVATE_KEY=\$(cat /tmp/deployer.key) BESU_RPCS=http://${IP[v1]}:8545 nohup sh -c '/opt/venv/bin/python -m experiments.run_all --out /tmp/results $ARGS > /tmp/run.log 2>&1; touch /tmp/results/DONE' > /dev/null 2>&1 < /dev/null &)"

say "Experiment running (progress below; the full run takes roughly 45 minutes)"
for t in $(seq 400); do
  if ssh_ c 'test -f /tmp/results/DONE'; then break; fi
  echo "$(date +%H:%M) $(ssh_ c 'tail -1 /tmp/run.log | cut -c1-110')"; sleep 45
done

say "Analysing and collecting results"
for k in v1 v2 v3 v4; do gcloud compute scp --zone "${Z[$k]}" --quiet "$(vm $k):/tmp/sampler_$k.csv" . 2>/dev/null; done
for k in v1 v2 v3 v4; do gcloud compute scp --zone "${Z[c]}" --quiet "sampler_$k.csv" "$(vm c):/tmp/results/" 2>/dev/null; done
ssh_ c 'cp /tmp/sampler_c.csv /tmp/results/sampler_c.csv; cp /opt/repo/experiments/deployment_v2.json /tmp/results/ 2>/dev/null; cd /opt/repo && /opt/venv/bin/python experiments/analyze.py /tmp/results > /tmp/results/analyze_stdout.txt 2>&1; tail -3 /tmp/results/analyze_stdout.txt'
rm -rf "$OUTDIR"; mkdir -p "$OUTDIR"
gcloud compute scp --recurse --zone "${Z[c]}" --quiet "$(vm c):/tmp/results/*" "$OUTDIR/" 2>/dev/null
( cd "$HOME" && tar czf results_gcp.tgz "$(basename "$OUTDIR")" )
say "DONE. Results are in $OUTDIR and $HOME/results_gcp.tgz"
echo "Download the archive with:   cloudshell download $HOME/results_gcp.tgz"
echo "Then send me results_gcp.tgz (or paste $OUTDIR/tables.md). The VMs are deleted automatically now."
