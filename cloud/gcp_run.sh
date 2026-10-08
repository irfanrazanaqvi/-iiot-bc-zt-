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
ssh_() { local k=$1; shift; gcloud compute ssh "$(vm "$k")" --zone "${Z[$k]}" --quiet --command "$*" -- -o StrictHostKeyChecking=no -o ConnectTimeout=20 2>/dev/null; }
ip_()  { gcloud compute instances describe "$(vm "$1")" --zone "${Z[$1]}" --format='get(networkInterfaces[0].networkIP)'; }

cleanup() {
  if [ "${KEEP:-0}" = "1" ]; then say "KEEP=1: VMs left running. Delete them with: gcloud compute instances delete $(for k in "${KEYS[@]}"; do printf '%s ' "$(vm $k)"; done) (one --zone each)"; return; fi
  say "Deleting VMs (stops all charges)"
  for k in "${KEYS[@]}"; do gcloud compute instances delete "$(vm $k)" --zone "${Z[$k]}" --quiet >/dev/null 2>&1 & done
  wait
}
trap cleanup EXIT

say "Project: $(gcloud config get-value project 2>/dev/null)   mode: $MODE"
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
  ssh_ "$k" 'test -f /opt/ready' || { echo "$(vm $k) did not finish setup; see /var/log/vm_setup.log"; exit 1; }
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
  ssh_ "$k" "cd /tmp && rm -rf data && JAVA_OPTS=-Xmx3g nohup /opt/besu-24.7.0/bin/besu --data-path=/tmp/data --genesis-file=/tmp/genesis.json --node-private-key-file=/tmp/key --rpc-http-enabled --rpc-http-api=ETH,NET,QBFT,WEB3,ADMIN --rpc-http-host=0.0.0.0 --rpc-http-port=8545 --rpc-http-max-active-connections=2000 --host-allowlist='*' --p2p-host=${IP[$k]} --p2p-port=30303 --min-gas-price=0 $BOOT > /tmp/besu.log 2>&1 < /dev/null &"
  if [ "$k" = v1 ]; then
    for t in $(seq 30); do sleep 4
      E=$(ssh_ v1 "curl -s -X POST -H 'Content-Type: application/json' --data '{\"jsonrpc\":\"2.0\",\"method\":\"net_enode\",\"params\":[],\"id\":1}' localhost:8545 | python3 -c 'import sys,json;print(json.load(sys.stdin)[\"result\"])'") && [ -n "$E" ] && break
    done
    echo "enode: $E"; BOOT="--bootnodes=$E"
  fi
done
for t in $(seq 30); do
  BN=$(ssh_ c "curl -s -X POST -H 'Content-Type: application/json' --data '{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}' http://${IP[v4]}:8545 | python3 -c 'import sys,json;print(int(json.load(sys.stdin)[\"result\"],16))'") || BN=0
  [ "${BN:-0}" -ge 3 ] && break; sleep 6
done
echo "block height seen from the client via validator 4: ${BN:-0}"
[ "${BN:-0}" -ge 3 ] || { echo "network did not start; check /tmp/besu.log on the validators"; exit 1; }

say "Deploying contracts, starting gateway, samplers and the experiment"
RPCS="http://${IP[v1]}:8545,http://${IP[v2]}:8545,http://${IP[v3]}:8545,http://${IP[v4]}:8545"
for k in "${KEYS[@]}"; do ssh_ "$k" "nohup python3 /opt/repo/experiments/sampler.py /tmp/sampler_$k.csv > /dev/null 2>&1 < /dev/null &"; done
ssh_ c "cd /opt/repo && export NODE_PATH=/opt/nd/node_modules && openssl rand -hex 32 | sed 's/^/0x/' > /tmp/deployer.key && RPC_URL=http://${IP[v1]}:8545 DEPLOYER_PRIVATE_KEY=\$(cat /tmp/deployer.key) node experiments/deploy_v2.js" | tail -5
ssh_ c "cd /opt/repo && GATEWAY_SEED=\$(openssl rand -hex 8) BESU_RPCS=$RPCS nohup python3 -m uvicorn experiments.gateway_multi:app --port 9000 > /tmp/gw.log 2>&1 < /dev/null &"
sleep 20
ssh_ c "curl -s localhost:9000/health"; echo
ssh_ c "cd /opt/repo && mkdir -p /tmp/results && (ADMIN_PRIVATE_KEY=\$(cat /tmp/deployer.key) BESU_RPCS=http://${IP[v1]}:8545 nohup sh -c 'python3 -m experiments.run_all --out /tmp/results $ARGS > /tmp/run.log 2>&1; touch /tmp/results/DONE' > /dev/null 2>&1 < /dev/null &)"

say "Experiment running (progress below; the full run takes roughly 45 minutes)"
for t in $(seq 400); do
  if ssh_ c 'test -f /tmp/results/DONE'; then break; fi
  echo "$(date +%H:%M) $(ssh_ c 'tail -1 /tmp/run.log | cut -c1-110')"; sleep 45
done

say "Analysing and collecting results"
for k in v1 v2 v3 v4; do gcloud compute scp --zone "${Z[$k]}" --quiet "$(vm $k):/tmp/sampler_$k.csv" . 2>/dev/null; done
for k in v1 v2 v3 v4; do gcloud compute scp --zone "${Z[c]}" --quiet "sampler_$k.csv" "$(vm c):/tmp/results/" 2>/dev/null; done
ssh_ c 'cp /tmp/sampler_c.csv /tmp/results/sampler_c.csv; cp /opt/repo/experiments/deployment_v2.json /tmp/results/ 2>/dev/null; cd /opt/repo && python3 experiments/analyze.py /tmp/results > /tmp/results/analyze_stdout.txt 2>&1; tail -3 /tmp/results/analyze_stdout.txt'
rm -rf "$OUTDIR"; mkdir -p "$OUTDIR"
gcloud compute scp --recurse --zone "${Z[c]}" --quiet "$(vm c):/tmp/results/*" "$OUTDIR/" 2>/dev/null
( cd "$HOME" && tar czf results_gcp.tgz "$(basename "$OUTDIR")" )
say "DONE. Results are in $OUTDIR and $HOME/results_gcp.tgz"
echo "Download the archive with:   cloudshell download $HOME/results_gcp.tgz"
echo "Then send me results_gcp.tgz (or paste $OUTDIR/tables.md). The VMs are deleted automatically now."
