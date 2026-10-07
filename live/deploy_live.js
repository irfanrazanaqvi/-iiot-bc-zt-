// Offline-friendly deploy + setup for the LIVE Besu QBFT network (no Hardhat compiler download).
// Compiles contracts/*.sol with the npm `solc` package, deploys IdentityRegistry -> TrustManager ->
// AccessControlManager, registers N benchmark devices, configures both use-case policies, and
// writes live/deployment.json (addresses + ABIs) for the gateway and experiment scripts.
//
// Usage: RPC_URL=http://127.0.0.1:8545 DEPLOYER_PRIVATE_KEY=0x.. node live/deploy_live.js [numDevices]
const fs = require("fs"), path = require("path");
const solc = require("solc");
const { ethers } = require("ethers");

const RPC = process.env.RPC_URL || "http://127.0.0.1:8545";
const KEY = process.env.DEPLOYER_PRIVATE_KEY || "0x" + "11".repeat(32);
const N = parseInt(process.argv[2] || "200");
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

(async () => {
  const provider = new ethers.JsonRpcProvider(RPC, undefined, { staticNetwork: true });
  const wallet = new ethers.NonceManager(new ethers.Wallet(KEY, provider));
  const addr = await wallet.getAddress();
  const C = compile();
  const get = (file, name) => ({ abi: C[file][name].abi, bytecode: "0x" + C[file][name].evm.bytecode.object });
  const opts = { gasPrice: 0, gasLimit: 6_000_000 };
  const deploy = async (file, name, args = []) => {
    const a = get(file, name);
    const c = await new ethers.ContractFactory(a.abi, a.bytecode, wallet).deploy(...args, opts);
    await c.waitForDeployment();
    console.log(name, await c.getAddress());
    return { c, abi: a.abi };
  };
  const id = await deploy("IdentityRegistry.sol", "IdentityRegistry");
  const tm = await deploy("TrustManager.sol", "TrustManager", [await id.c.getAddress()]);
  const ac = await deploy("AccessControl.sol", "AccessControlManager", [await id.c.getAddress(), await tm.c.getAddress()]);

  // Policies (Section IV-E): manufacturing theta=40; substation theta=70. Manufacturing window is
  // set to 0-0 (always open) for the load test; the time-window attack uses its own resource.
  const tx = async (p) => (await p).wait();
  await tx(ac.c.setPolicy("plc-line1/setpoint", "write", 40, 0, 0, opts));
  await tx(ac.c.setPolicy("relay-feeder7/firmware", "write", 70, 1, 4, opts));
  await tx(ac.c.setPolicy("plc-line1/night-only", "write", 40, 1, 4, opts)); // outside window at test time (A6)
  console.log("policies set");

  // Register N benchmark devices at the same deterministic addresses the gateway derives.
  const devAddr = (d) => ethers.getAddress("0x" + ethers.keccak256(ethers.toUtf8Bytes(d)).slice(-40));
  const ids = [...Array.from({ length: N }, (_, i) => `device-${i}`), "dev-revoke", "dev-lowtrust", "dev-ok"];
  for (let i = 0; i < ids.length; i += 50) {   // chunks keep us under Besu's per-sender pool limit
    const rs = await Promise.all(ids.slice(i, i + 50).map((d) => id.c.registerDevice(devAddr(d), ethers.keccak256(ethers.toUtf8Bytes("pk-" + d)), "sensor", "fw-hash-1", opts)));
    await Promise.all(rs.map((r) => r.wait()));
  }
  console.log("registered", ids.length, "devices");

  fs.writeFileSync(path.join(__dirname, "deployment.json"), JSON.stringify({
    rpc: RPC, deployer: addr,
    identityRegistry: await id.c.getAddress(), trustManager: await tm.c.getAddress(), accessControl: await ac.c.getAddress(),
    abis: { identityRegistry: id.abi, trustManager: tm.abi, accessControl: ac.abi }, devices: ids,
  }, null, 1));
  console.log("wrote live/deployment.json");
})().catch((e) => { console.error(e); process.exit(1); });
