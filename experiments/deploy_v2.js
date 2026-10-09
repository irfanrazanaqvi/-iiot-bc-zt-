// Compile (solc-js, offline-friendly) and deploy the V2 stack on a running Besu QBFT network:
//   IdentityRegistry -> TrustManager -> AccessControlManagerV2 (replay protection + rate limit)
// then register every benchmark identity and set the policies. Writes experiments/deployment_v2.json.
//
// Device identities have real keys: private key = keccak256("devkey:" + deviceId). The load generator
// signs requests with these keys, standing in for the device firmware.
//
// Usage: RPC_URL=http://127.0.0.1:8545 DEPLOYER_PRIVATE_KEY=0x.. node experiments/deploy_v2.js
const fs = require("fs"), path = require("path");
const solc = require("solc");
const { ethers } = require("ethers");

const RPC = process.env.RPC_URL || "http://127.0.0.1:8545";
const KEY = process.env.DEPLOYER_PRIVATE_KEY;
if (!KEY) { console.error("set DEPLOYER_PRIVATE_KEY"); process.exit(1); }
const MAX_PER_WINDOW = parseInt(process.env.MAX_PER_WINDOW || "20");
const WINDOW_S = parseInt(process.env.WINDOW_S || "60");
const root = path.join(__dirname, "..", "contracts");

function compile() {
  const sources = {};
  for (const f of fs.readdirSync(root)) if (f.endsWith(".sol")) sources[f] = { content: fs.readFileSync(path.join(root, f), "utf8") };
  const input = { language: "Solidity", sources, settings: { evmVersion: "london", optimizer: { enabled: true, runs: 200 }, outputSelection: { "*": { "*": ["abi", "evm.bytecode.object"] } } } };
  const out = JSON.parse(solc.compile(JSON.stringify(input), { import: (p) => ({ contents: fs.readFileSync(path.join(root, p), "utf8") }) }));
  const errs = (out.errors || []).filter((e) => e.severity === "error");
  if (errs.length) { console.error(errs.map((e) => e.formattedMessage).join("\n")); process.exit(1); }
  return out.contracts;
}

const devKey = (id) => ethers.keccak256(ethers.toUtf8Bytes("devkey:" + id));
const devAddr = (id) => new ethers.Wallet(devKey(id)).address;

(async () => {
  const provider = new ethers.JsonRpcProvider(RPC, undefined, { staticNetwork: true });
  const wallet = new ethers.NonceManager(new ethers.Wallet(KEY, provider));
  const C = compile();
  const opts = { gasPrice: 0, gasLimit: 8_000_000 };
  const deploy = async (file, name, args = []) => {
    const a = { abi: C[file][name].abi, bytecode: "0x" + C[file][name].evm.bytecode.object };
    const c = await new ethers.ContractFactory(a.abi, a.bytecode, wallet).deploy(...args, opts);
    await c.waitForDeployment();
    console.log(name, await c.getAddress());
    return { c, abi: a.abi };
  };
  const id = await deploy("IdentityRegistry.sol", "IdentityRegistry");
  const tm = await deploy("TrustManager.sol", "TrustManager", [await id.c.getAddress()]);
  const ac = await deploy("AccessControlV2.sol", "AccessControlManagerV2", [await id.c.getAddress(), await tm.c.getAddress(), MAX_PER_WINDOW, WINDOW_S]);

  const hour = new Date().getUTCHours();
  const closedFrom = (hour + 6) % 24, closedTo = (hour + 8) % 24;   // a window that is closed right now
  const policies = [
    ["plc-line1/setpoint", "write", 40, 0, 0],            // manufacturing, theta=40, always open
    ["relay-feeder7/firmware", "write", 70, 0, 0],        // substation tier, theta=70
    ["plc-line1/closed-window", "write", 40, closedFrom, closedTo],
  ];
  for (const p of policies) await (await ac.c.setPolicy(...p, opts)).wait();
  console.log("policies set; closed window", closedFrom, closedTo);

  const R = 40;
  const ids = [
    ...Array.from({ length: 200 }, (_, i) => `device-${i}`),
    ...Array.from({ length: R }, (_, i) => `rev-${i}`),
    ...["sec-rev", "sec-low", "sec-tam", "sec-flood", "sec-ctrl", "sec-host", "dec"].flatMap((p) => Array.from({ length: R }, (_, i) => `${p}-${i}`)),
    ...Array.from({ length: 1000 }, (_, i) => `scl-${i}`),
  ];
  for (let i = 0; i < ids.length; i += 150) {
    const rs = await Promise.all(ids.slice(i, i + 150).map((d) =>
      id.c.registerDevice(devAddr(d), ethers.keccak256(ethers.toUtf8Bytes("pk-" + d)), "sensor", "fw-hash-1", opts)));
    await Promise.all(rs.map((r) => r.wait()));
  }
  console.log("registered", ids.length, "identities");

  fs.writeFileSync(path.join(__dirname, "deployment_v2.json"), JSON.stringify({
    rpc: RPC, deployer: await wallet.getAddress(),
    identityRegistry: await id.c.getAddress(), trustManager: await tm.c.getAddress(), accessControl: await ac.c.getAddress(),
    maxPerWindow: MAX_PER_WINDOW, windowSeconds: WINDOW_S, closedWindow: [closedFrom, closedTo], policies,
    abis: { identityRegistry: id.abi, trustManager: tm.abi, accessControl: ac.abi },
  }, null, 1));
  console.log("wrote experiments/deployment_v2.json");
})().catch((e) => { console.error(e); process.exit(1); });
