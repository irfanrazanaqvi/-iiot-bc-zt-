// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title IdentityRegistry
/// @notice Registers and manages verifiable device identities (DIDs) for IIoT endpoints.
///         Every device/edge-gateway is enrolled by an authorized Registrar before it can
///         participate in the zero-trust network. No implicit trust is granted at registration —
///         it only establishes a cryptographically verifiable identity.
contract IdentityRegistry {

    struct DeviceIdentity {
        address deviceAddress;   // device's blockchain account (derived from its key pair / TPM)
        bytes32 publicKeyHash;   // hash of device public key / attestation certificate
        string  deviceType;      // e.g. "PLC", "sensor", "gateway", "HMI"
        string  firmwareHash;    // hash of the currently attested firmware image
        uint256 registeredAt;
        bool    active;
    }

    mapping(address => DeviceIdentity) private devices;
    mapping(address => bool) public registrars;
    address public owner;

    event DeviceRegistered(address indexed device, string deviceType, uint256 timestamp);
    event DeviceRevoked(address indexed device, uint256 timestamp);
    event FirmwareUpdated(address indexed device, string newFirmwareHash);

    modifier onlyRegistrar() {
        require(registrars[msg.sender] || msg.sender == owner, "Not an authorized registrar");
        _;
    }

    constructor() {
        owner = msg.sender;
        registrars[msg.sender] = true;
    }

    function addRegistrar(address _registrar) external {
        require(msg.sender == owner, "Only owner");
        registrars[_registrar] = true;
    }

    function registerDevice(
        address _device,
        bytes32 _publicKeyHash,
        string calldata _deviceType,
        string calldata _firmwareHash
    ) external onlyRegistrar {
        require(devices[_device].registeredAt == 0, "Already registered");
        devices[_device] = DeviceIdentity({
            deviceAddress: _device,
            publicKeyHash: _publicKeyHash,
            deviceType: _deviceType,
            firmwareHash: _firmwareHash,
            registeredAt: block.timestamp,
            active: true
        });
        emit DeviceRegistered(_device, _deviceType, block.timestamp);
    }

    function revokeDevice(address _device) external onlyRegistrar {
        require(devices[_device].active, "Not active");
        devices[_device].active = false;
        emit DeviceRevoked(_device, block.timestamp);
    }

    function updateFirmwareHash(address _device, string calldata _newHash) external onlyRegistrar {
        require(devices[_device].active, "Not active");
        devices[_device].firmwareHash = _newHash;
        emit FirmwareUpdated(_device, _newHash);
    }

    function isActive(address _device) external view returns (bool) {
        return devices[_device].active;
    }

    function getIdentity(address _device) external view returns (DeviceIdentity memory) {
        return devices[_device];
    }
}
