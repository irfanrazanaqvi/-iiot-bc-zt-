require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.20",
  networks: {
    besu: {
      url: "http://127.0.0.1:8545",
      chainId: 133713,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY || "0x" + "1".repeat(64)]
    }
  }
};
