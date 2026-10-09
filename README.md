# Blockchain-Based Zero-Trust Architecture for IIoT — Reference Implementation

Reference prototype accompanying the paper *"A Blockchain-Based Zero-Trust Novel
Architecture for Secure Industrial Internet of Things (IIoT)."* It implements:

- A **4-node Hyperledger Besu QBFT** permissioned blockchain (Section 5.1)
- On-chain **Identity, Trust, and Access Control** smart contracts (Sections 4.3–4.7)
- A **Zero-Trust Gateway** (Policy Enforcement Point) bridging OT devices to the chain
- A **simulated IIoT testbed** of MQTT-publishing devices, including a malicious-device
  mode for the security evaluation (Section 3.3 / 7.1)
- **Benchmark scripts** producing the latency/throughput/scalability results in Section 7

## Repository layout

```
iiot-bc-zt/
├── docker-compose.yml        # 4 Besu validators + MQTT broker
├── network/                  # genesis.json, config.toml, validator keys
├── contracts/                # IdentityRegistry.sol, TrustManager.sol, AccessControl.sol
├── scripts/                  # network setup, contract deployment, policy configuration
├── testbed/                  # device_simulator.py, gateway.py (PEP), MQTT config
├── benchmark/                # latency/throughput harness + plotting (for a LIVE network)
├── evaluation/                # simulation + all figures/results used in the paper
├── docs/RESULTS_SUMMARY.md    # maps every paper table/figure to its exact source file
└── hardhat.config.js, package.json
```

**Start here if you just want the results**: [`docs/RESULTS_SUMMARY.md`](docs/RESULTS_SUMMARY.md)
maps every table and figure in the manuscript to the exact file that produced it, and
explains precisely which numbers are from real Besu/Solidity code versus the calibrated
simulation used in place of a multi-day physical deployment.

## 1. Prerequisites

- Docker + Docker Compose
- Node.js ≥ 18 (contract compilation/deployment via Hardhat)
- Python ≥ 3.10
- (optional) Besu CLI installed locally for key generation — or run the equivalent
  commands inside the `hyperledger/besu` Docker image

## 2. Generate validator keys and genesis file

```bash
chmod +x scripts/setup_network.sh
./scripts/setup_network.sh
```

This produces 4 validator key pairs and a QBFT `genesis.json`. Copy the generated
`genesis.json` over `network/genesis.json`, and paste each validator's enode URL into
`docker-compose.yml` (`--bootnodes=...`) — the placeholders are marked
`<VALIDATOR1_ENODE>`.

## 3. Start the blockchain network + MQTT broker

```bash
docker compose up -d
docker compose logs -f validator1   # confirm block production (every ~2s)
```

Verify the network:
```bash
curl -X POST --data '{"jsonrpc":"2.0","method":"qbft_getValidatorsByBlockNumber","params":["latest"],"id":1}' \
  -H "Content-Type: application/json" http://localhost:8545
```

## 4. Deploy the smart contracts

```bash
npm install
npx hardhat compile
DEPLOYER_PRIVATE_KEY=<validator1_private_key> npm run deploy
```

Record the three printed contract addresses.

## 4b. Configure the two use-case policies (Section 4.10 / Table 3-4)

```bash
ACCESS_CONTROL_ADDRESS=<AccessControlManager address from step 4> \
  npx hardhat run scripts/configure_policies.js --network besu
```

This sets both risk tiers on the same deployed contracts: the manufacturing PLC-setpoint
policy (θ=40, wide window) and the smart-grid substation relay-firmware policy (θ=70,
narrow scheduled window), matching Eq. (3) and Tables 3-4 of the paper.

## 5. Run the Zero-Trust Gateway (Policy Enforcement Point)

```bash
cd testbed
pip install -r requirements.txt
export BESU_RPC_URL=http://127.0.0.1:8545
export ACCESS_CONTROL_ADDRESS=<AccessControlManager address from step 4>
export IDENTITY_REGISTRY_ADDRESS=<IdentityRegistry address from step 4>
uvicorn gateway:app --host 0.0.0.0 --port 9000
```

## 6. Launch the simulated IIoT device fleet

Legitimate devices:
```bash
for i in 1 2 3 4 5; do
  python testbed/device_simulator.py --device-id sensor-$i --device-type sensor --interval 2 &
done
```

Compromised/malicious device (for the security & attack-scenario evaluation, Section 3.3):
```bash
python testbed/device_simulator.py --device-id attacker-1 --malicious --interval 0.5
```

Second use case (smart-grid substation, θ=70 policy tier, Section 4.10.2):
```bash
python testbed/device_simulator.py --device-id relay-vendor-1 --device-type plc \
  --resource relay-feeder7/firmware --action write --interval 5
```

## 7. Run the performance benchmarks (Section 6/7)

```bash
cd benchmark
pip install -r ../testbed/requirements.txt
python latency_throughput_test.py \
  --gateway-url http://localhost:9000 \
  --concurrency 1 5 10 20 50 100 \
  --requests-per-level 200 \
  --out results.csv

python plot_results.py --csv results.csv --out-prefix fig
```

`results.csv` contains, per concurrency level: `throughput_rps`,
`latency_mean_ms/p50/p95/max`, `grant_rate`, `error_rate` — the exact metrics referenced
in Sections 6.5 and 7.4–7.7. Re-run against a non-blockchain baseline (e.g. a static
ACL/RBAC gateway) to reproduce the comparative results in Section 8.4.

## Results at a glance (Google Cloud, four architectures)

Measured on four Besu QBFT validators in four regions plus a client VM (`cloud/`, `evaluation/results_gcp/`). The proposed design denied 100 % of attack requests in seven scenarios (A1-A7); the centralized zero-trust baseline denied 100 % in A1-A6 and 0 % in A7 (trust-store tampering); static RBAC 28.6 % on average; no control 0 %. Cost: about 2.0 s per decision, 3.5 s revocation, 37.6 decisions/s at 200 clients (baselines: milliseconds, 190-245 req/s). Details and caveats: [`docs/RESULTS_SUMMARY.md`](docs/RESULTS_SUMMARY.md). The older simulation (`evaluation/results/`) and single-host run (`live/`) are historical and not used in the paper.

## 8. Reproducing the paper's figures and results tables

Everything used to generate the manuscript's Figures 1-6 and Tables V-VI is in
`evaluation/` — see `evaluation/README.md`. In short:

```bash
cd evaluation
pip install -r requirements.txt
python simulate_performance.py
python gen_fig1_architecture.py
python gen_fig2_workflow.py
python gen_result_figures.py
python analyze_results.py   # headline numbers -> results/summary_stats.json
```

This reproduces `evaluation/figures/*.png` and `evaluation/results/*.csv` exactly as used
in the paper. `evaluation/README.md` also explains how to swap the simulation for real
measurements captured from the live network (steps 1-7 above) once you have hardware to
run a multi-day deployment on.

## 9. Publishing this repository to GitHub

```bash
cd iiot-bc-zt
git init
git add .
git commit -m "Initial prototype: blockchain-based zero-trust IIoT architecture"
git branch -M main
git remote add origin https://github.com/<your-username>/iiot-blockchain-zero-trust.git
git push -u origin main
```

## Notes on reproducibility

- `genesis.json` and validator keys in this repo are **placeholders** — always regenerate
  them with `scripts/setup_network.sh` per deployment; never reuse example keys in any
  network exposed beyond a local testbed.
- The `gateway.py` device→address mapping is a deterministic mock for the demo; in a real
  deployment, device blockchain addresses are bound during the attestation/enrollment flow
  (`IdentityRegistry.registerDevice`), not derived from a device-ID string.
- All numeric results in the paper's results section should be regenerated from your own run of
  `benchmark/latency_throughput_test.py` on your target hardware — the paper should report
  actual measured values, hardware spec, and number of trials/statistical treatment (see the manuscript's Methodology).
