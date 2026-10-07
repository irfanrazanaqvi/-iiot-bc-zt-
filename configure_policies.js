// Configures the two risk-tiered access policies described in the paper (Section 4.10 / 5.3):
//   - Manufacturing use case (4.10.1): PLC setpoint write, threshold θ=40, wide access window
//   - Smart-grid substation use case (4.10.2): relay firmware write, threshold θ=70, narrow window
//
// Both policies are set via the same AccessControlManager.setPolicy() function on the same
// deployed contract set -- demonstrating Eq. (3)'s claim that a single contract deployment
// supports differentiated risk tiers purely through configuration.
//
// Usage: ACCESS_CONTROL_ADDRESS=0x... npx hardhat run scripts/configure_policies.js --network besu

const hre = require("hardhat");

async function main() {
  const accessControlAddress = process.env.ACCESS_CONTROL_ADDRESS;
  if (!accessControlAddress) {
    throw new Error("Set ACCESS_CONTROL_ADDRESS to the deployed AccessControlManager address (see scripts/deploy_contracts.js output)");
  }

  const AccessControlManager = await hre.ethers.getContractFactory("AccessControlManager");
  const ac = AccessControlManager.attach(accessControlAddress);

  console.log("Configuring Use Case 1 (Manufacturing, Section 4.10.1): plc-line1/setpoint, write, theta=40, 06:00-22:00");
  let tx = await ac.setPolicy(
    "plc-line1/setpoint",   // resource
    "write",                // action
    40,                     // minTrustScore (theta)
    6,                      // validFromHour
    22                      // validToHour
  );
  await tx.wait();
  console.log("  -> tx:", tx.hash);

  console.log("Configuring Use Case 2 (Smart Grid Substation, Section 4.10.2): relay-feeder7/firmware, write, theta=70, 01:00-04:00");
  tx = await ac.setPolicy(
    "relay-feeder7/firmware", // resource
    "write",                  // action
    70,                       // minTrustScore (theta) -- higher-consequence tier
    1,                        // validFromHour -- narrow scheduled maintenance window
    4                         // validToHour
  );
  await tx.wait();
  console.log("  -> tx:", tx.hash);

  console.log("\nBoth policies configured on the same AccessControlManager instance:", accessControlAddress);
  console.log("This reproduces the two-tier configuration referenced in Eq. (3) and Tables 3-4 of the paper.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
