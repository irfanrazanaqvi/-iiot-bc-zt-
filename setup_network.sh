#!/usr/bin/env bash
# One-time setup: generates 4 validator key pairs and a matching QBFT genesis.json.
# Requires: besu CLI installed locally (or run via the hyperledger/besu docker image).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEYS_DIR="$ROOT_DIR/network/keys"
mkdir -p "$KEYS_DIR"

echo "Generating validator key pairs..."
for i in 1 2 3 4; do
  mkdir -p "$KEYS_DIR/validator$i"
  besu --data-path="$KEYS_DIR/validator$i" public-key export-address --to="$KEYS_DIR/validator$i/address" || true
  besu operator generate-blockchain-config \
    --config-file=/dev/null 2>/dev/null || true
done

echo "Generating QBFT genesis + node keys via Besu operator tool..."
besu operator generate-blockchain-config \
  --config-file="$ROOT_DIR/network/qbft-config.json" \
  --to="$ROOT_DIR/network/generated" \
  --private-key-file-name=key

echo "Copy the generated keys into network/keys/validatorN/key and the produced genesis.json"
echo "into network/genesis.json, then update docker-compose.yml bootnode enode URLs."
echo "Done."
