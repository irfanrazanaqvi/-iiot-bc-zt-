// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IdentityRegistry.sol";
import "./TrustManager.sol";

/// @title AccessControlManagerV2
/// @notice Hardened Policy Decision Point. Compared with AccessControlManager (V1) it adds the two
///         protections the live V1 experiments showed to be missing:
///           * replay protection: every request carries a device signature over
///             (this contract, chain id, device, resource, action, nonce); the signer must be the device
///             address and a nonce can be used once (unordered nonces, so concurrent requests are fine);
///           * rate limiting: at most `maxPerWindow` signed requests per device per `windowSeconds`.
///         Decision order: policy exists -> identity active -> valid signature -> fresh nonce ->
///         rate limit -> trust score >= theta -> time window. Every outcome is logged as an event.
contract AccessControlManagerV2 {

    IdentityRegistry public identityRegistry;
    TrustManager public trustManager;
    address public policyAdmin;
    uint32 public maxPerWindow;
    uint32 public windowSeconds;

    struct Policy {
        uint8  minTrustScore;
        bool   exists;
        uint32 validFromHour;
        uint32 validToHour;
    }
    struct Window { uint64 start; uint32 count; }

    mapping(bytes32 => mapping(bytes32 => Policy)) public policies;
    mapping(bytes32 => bool) public usedNonce;          // keccak(device, nonce)
    mapping(address => Window) public windows;

    event AccessDecision(address indexed device, bytes32 resource, bytes32 action, bool granted, string reason);
    event PolicySet(bytes32 resource, bytes32 action, uint8 minTrustScore);

    modifier onlyAdmin() {
        require(msg.sender == policyAdmin, "Only policy admin");
        _;
    }

    constructor(address _identityRegistry, address _trustManager, uint32 _maxPerWindow, uint32 _windowSeconds) {
        policyAdmin = msg.sender;
        identityRegistry = IdentityRegistry(_identityRegistry);
        trustManager = TrustManager(_trustManager);
        maxPerWindow = _maxPerWindow;
        windowSeconds = _windowSeconds;
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

    function digest(address device, bytes32 r, bytes32 a, uint256 nonce) public view returns (bytes32) {
        return keccak256(abi.encodePacked(address(this), block.chainid, device, r, a, nonce));
    }

    function _recover(bytes32 d, bytes calldata sig) internal pure returns (address) {
        if (sig.length != 65) return address(0);
        bytes32 h = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", d));
        bytes32 rr; bytes32 ss; uint8 v;
        assembly {
            rr := calldataload(sig.offset)
            ss := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
        if (v < 27) v += 27;
        return ecrecover(h, v, rr, ss);
    }

    function _deny(address device, bytes32 r, bytes32 a, string memory reason) internal returns (bool) {
        emit AccessDecision(device, r, a, false, reason);
        return false;
    }

    function _rateOk(address device) internal returns (bool) {
        Window memory w = windows[device];
        if (block.timestamp >= uint256(w.start) + windowSeconds) { w.start = uint64(block.timestamp); w.count = 0; }
        w.count += 1;
        windows[device] = w;
        return w.count <= maxPerWindow;
    }

    function _inWindow(Policy memory p) internal view returns (bool) {
        if (p.validFromHour == p.validToHour) return true;
        uint256 h = (block.timestamp / 1 hours) % 24;
        return p.validFromHour < p.validToHour
            ? (h >= p.validFromHour && h < p.validToHour)
            : (h >= p.validFromHour || h < p.validToHour);
    }

    /// @notice Evaluated for every single request.
    function checkAccess(
        address device,
        string calldata resource,
        string calldata action,
        uint256 nonce,
        bytes calldata signature
    ) external returns (bool granted) {
        bytes32 r = keccak256(bytes(resource));
        bytes32 a = keccak256(bytes(action));
        Policy memory p = policies[r][a];

        if (!p.exists) return _deny(device, r, a, "no-policy");
        if (!identityRegistry.isActive(device)) return _deny(device, r, a, "identity-invalid");
        if (_recover(digest(device, r, a, nonce), signature) != device) return _deny(device, r, a, "bad-signature");

        bytes32 nk = keccak256(abi.encodePacked(device, nonce));
        if (usedNonce[nk]) return _deny(device, r, a, "replay");
        usedNonce[nk] = true;

        if (!_rateOk(device)) return _deny(device, r, a, "rate-limited");
        if (trustManager.getScore(device) < p.minTrustScore) return _deny(device, r, a, "insufficient-trust");
        if (!_inWindow(p)) return _deny(device, r, a, "outside-time-window");

        emit AccessDecision(device, r, a, true, "granted");
        return true;
    }
}
