#!/usr/bin/env bash
# Run the 4-validator Besu 24.7.0 QBFT network WITHOUT Docker (e.g. on a cloud VM or sandbox with Java 21).
# Usage: live/start_besu_native.sh [workdir]      (default /tmp/besu)
set -euo pipefail
W=${1:-/tmp/besu}; mkdir -p "$W"; cd "$W"
if [ ! -d besu-24.7.0 ]; then
  curl -sL -o besu.tgz https://github.com/hyperledger/besu/releases/download/24.7.0/besu-24.7.0.tar.gz && tar xzf besu.tgz
fi
BESU="$W/besu-24.7.0/bin/besu"; export JAVA_OPTS="${JAVA_OPTS:--Xmx700m}"
cp "$(dirname "$(readlink -f "$0")")/../network/qbft-config.json" qbft.json
[ -d net ] || "$BESU" operator generate-blockchain-config --config-file=qbft.json --to=net --private-key-file-name=key
i=0
for k in net/keys/*; do
  i=$((i+1)); mkdir -p n$i; cp "$k/key" n$i/key
  BOOT=""; [ $i -gt 1 ] && BOOT="--bootnodes=$(cat n1.enode)"
  nohup "$BESU" --data-path=n$i/data --genesis-file=net/genesis.json --node-private-key-file=n$i/key \
    --rpc-http-enabled --rpc-http-api=ETH,NET,QBFT,WEB3,ADMIN --rpc-http-host=127.0.0.1 --rpc-http-port=$((8544+i)) \
    --rpc-http-max-active-connections=2000 --host-allowlist='*' --p2p-port=$((30302+i)) --p2p-host=127.0.0.1 \
    --min-gas-price=0 $BOOT > n$i.log 2>&1 &
  if [ $i -eq 1 ]; then
    for _ in $(seq 40); do sleep 3
      E=$(curl -s -X POST -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","method":"net_enode","params":[],"id":1}' localhost:8545 | python3 -c "import sys,json;print(json.load(sys.stdin)['result'])" 2>/dev/null) && [ -n "$E" ] && break
    done; echo "$E" > n1.enode
  fi
done
echo "4 validators started; RPC on 8545-8548"
