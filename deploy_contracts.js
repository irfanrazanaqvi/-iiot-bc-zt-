// Deploys IdentityRegistry -> TrustManager -> AccessControlManager to the Besu QBFT network.
// Usage: npx hardhat run scripts/deploy_contracts.js --network besu

const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  const IdentityRegistry = await hre.ethers.getContractFactory("IdentityRegistry");
  const identity = await IdentityRegistry.deploy();
  await identity.waitForDeployment();
  console.log("IdentityRegistry deployed to:", await identity.getAddress());

  const TrustManager = await hre.ethers.getContractFactory("TrustManager");
  const trust = await TrustManager.deploy(await identity.getAddress());
  await trust.waitForDeployment();
  console.log("TrustManager deployed to:", await trust.getAddress());

  const AccessControlManager = await hre.ethers.getContractFactory("AccessControlManager");
  const ac = await AccessControlManager.deploy(await identity.getAddress(), await trust.getAddress());
  await ac.waitForDeployment();
  console.log("AccessControlManager deployed to:", await ac.getAddress());

  console.log("\nDeployment summary:");
  console.log(JSON.stringify({
    identityRegistry: await identity.getAddress(),
    trustManager: await trust.getAddress(),
    accessControl: await ac.getAddress()
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
