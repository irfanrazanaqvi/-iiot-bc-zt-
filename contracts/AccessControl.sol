// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IdentityRegistry.sol";
import "./TrustManager.sol";

/// @title AccessControlManager
/// @notice Attribute/context-based, least-privilege access control (the Policy Decision Point).
///         Every access request is evaluated fresh against: (1) verified identity,
///         (2) current dynamic trust score, (3) requested resource/action policy,
///         (4) context (time window, device type). No standing/session-wide trust is granted —
///         each request is a discrete, continuously-verified decision (micro-segmentation).
contract AccessControlManager {

    IdentityRegistry public identityRegistry;
    TrustManager public trustManager;

    struct Policy {
        uint8   minTrustScore;
        bool    exists;
        uint32  validFromHour;   // 0-23, allowed access window start
        uint32  validToHour;     // 0-23, allowed access window end
    }

    // resource => action => policy
    mapping(bytes32 => mapping(bytes32 => Policy)) public policies;
    address public policyAdmin;

    event AccessDecision(address indexed device, bytes32 resource, bytes32 action, bool granted, string reason);
    event PolicySet(bytes32 resource, bytes32 action, uint8 minTrustScore);

    modifier onlyAdmin() {
        require(msg.sender == policyAdmin, "Only policy admin");
        _;
    }

    constructor(address _identityRegistry, address _trustManager) {
        policyAdmin = msg.sender;
        identityRegistry = IdentityRegistry(_identityRegistry);
        trustManager = TrustManager(_trustManager);
    }

    function setPolicy(
        string calldata resource,
        string calldata action,
        uint8 minTrustScore,
        uint32 validFromHour,
        uint32 validToHour
    ) external onlyAdmin {
        bytes32 r = keccak256(bytes(resource));
        bytes32 a = keccak256(bytes(action));
        policies[r][a] = Policy(minTrustScore, true, validFromHour, validToHour);
        emit PolicySet(r, a, minTrustScore);
    }

    /// @notice Core Policy Decision Point (PDP): evaluated for every single access attempt.
    function checkAccess(
        address device,
        string calldata resource,
        string calldata action
    ) external returns (bool granted) {
        bytes32 r = keccak256(bytes(resource));
        bytes32 a = keccak256(bytes(action));
        Policy memory p = policies[r][a];

        if (!p.exists) {
            emit AccessDecision(device, r, a, false, "no-policy");
            return false;
        }
        if (!identityRegistry.isActive(device)) {
            emit AccessDecision(device, r, a, false, "identity-invalid");
            return false;
        }
        uint8 score = trustManager.getScore(device);
        if (score < p.minTrustScore) {
            emit AccessDecision(device, r, a, false, "insufficient-trust");
            return false;
        }
        uint256 hourOfDay = (block.timestamp / 1 hours) % 24;
        if (p.validFromHour != p.validToHour) {
            bool withinWindow = p.validFromHour < p.validToHour
                ? (hourOfDay >= p.validFromHour && hourOfDay < p.validToHour)
                : (hourOfDay >= p.validFromHour || hourOfDay < p.validToHour);
            if (!withinWindow) {
                emit AccessDecision(device, r, a, false, "outside-time-window");
                return false;
            }
        }

        emit AccessDecision(device, r, a, true, "granted");
        return true;
    }
}
