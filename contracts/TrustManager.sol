// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IdentityRegistry.sol";

/// @title TrustManager
/// @notice Maintains a continuously-updated, on-chain trust score (0-100) per device.
///         Scores decay over time and are adjusted by verified behavioral/context evidence
///         submitted by monitoring nodes. This score feeds every access decision — trust is
///         never permanent, satisfying the zero-trust "never trust, always verify" principle.
contract TrustManager {

    IdentityRegistry public identityRegistry;

    struct TrustState {
        uint8   score;          // 0-100
        uint256 lastUpdated;
        uint32  anomalyCount;
    }

    mapping(address => TrustState) public trustOf;
    mapping(address => bool) public monitors; // authorized IDS/monitoring nodes

    uint8 public constant DEFAULT_SCORE = 50;
    uint8 public constant DECAY_PER_DAY = 2;
    uint8 public constant MIN_SCORE_FOR_ACCESS = 40;

    address public owner;
    /// @notice Length of one decay step in seconds (1 day by default). The owner may shorten it so that the decay
    ///         law can be validated in minutes instead of days; production deployments keep 1 days.
    uint256 public decayUnit = 1 days;

    event TrustUpdated(address indexed device, uint8 oldScore, uint8 newScore, string reason);

    modifier onlyMonitor() {
        require(monitors[msg.sender] || msg.sender == owner, "Not authorized monitor");
        _;
    }

    constructor(address _identityRegistry) {
        owner = msg.sender;
        identityRegistry = IdentityRegistry(_identityRegistry);
        monitors[msg.sender] = true;
    }

    function setDecayUnit(uint256 seconds_) external {
        require(msg.sender == owner, "Only owner");
        require(seconds_ > 0, "zero");
        decayUnit = seconds_;
    }

    function addMonitor(address _monitor) external {
        require(msg.sender == owner, "Only owner");
        monitors[_monitor] = true;
    }

    function _currentScore(address device) internal view returns (uint8) {
        TrustState memory t = trustOf[device];
        if (t.lastUpdated == 0) return DEFAULT_SCORE;
        uint256 daysElapsed = (block.timestamp - t.lastUpdated) / decayUnit;
        uint256 decay = daysElapsed * DECAY_PER_DAY;
        if (decay >= t.score) return 0;
        return uint8(t.score - decay);
    }

    /// @notice Submit a positive or negative trust evidence event (e.g. from anomaly detection,
    ///         successful attestation, policy violation) computed off-chain and recorded on-chain.
    function reportEvidence(address device, int16 delta, string calldata reason) external onlyMonitor {
        require(identityRegistry.isActive(device), "Device not registered/active");

        uint8 current = _currentScore(device);
        int16 updated = int16(uint16(current)) + delta;
        if (updated < 0) updated = 0;
        if (updated > 100) updated = 100;

        uint32 anomalies = trustOf[device].anomalyCount + (delta < 0 ? 1 : 0);

        emit TrustUpdated(device, current, uint8(uint16(updated)), reason);

        trustOf[device] = TrustState({
            score: uint8(uint16(updated)),
            lastUpdated: block.timestamp,
            anomalyCount: anomalies
        });
    }

    function getScore(address device) external view returns (uint8) {
        return _currentScore(device);
    }

    function isTrusted(address device) external view returns (bool) {
        return _currentScore(device) >= MIN_SCORE_FOR_ACCESS;
    }
}
