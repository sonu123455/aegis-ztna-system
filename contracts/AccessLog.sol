// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Aegis ZTNA AccessLog
 * @dev Decentralized, tamper-proof audit log for Zero Trust Network Access events.
 */
contract AccessLog {
    address public immutable gatewayAuthority;

    struct AccessRecord {
        string auditId;
        string userPrincipal;
        string targetResource;
        uint256 riskScorePercent; // Stored as basis points (e.g. 2140 = 21.40%)
        string decision;          // "GRANTED" or "DENIED"
        uint256 timestamp;
    }

    AccessRecord[] private records;

    event AccessLogged(
        string indexed auditId,
        string indexed userPrincipal,
        string targetResource,
        uint256 riskScorePercent,
        string decision,
        uint256 timestamp
    );

    modifier onlyAuthority() {
        require(msg.sender == gatewayAuthority, "Aegis: Caller is not the authorized gateway");
        _;
    }

    constructor() {
        gatewayAuthority = msg.sender;
    }

    /**
     * @notice Commits an immutable access decision record to the blockchain ledger.
     */
    function logAccess(
        string calldata _auditId,
        string calldata _userPrincipal,
        string calldata _targetResource,
        uint256 _riskScorePercent,
        string calldata _decision
    ) external returns (bytes32) {
        records.push(
            AccessRecord({
                auditId: _auditId,
                userPrincipal: _userPrincipal,
                targetResource: _targetResource,
                riskScorePercent: _riskScorePercent,
                decision: _decision,
                timestamp: block.timestamp
            })
        );

        emit AccessLogged(
            _auditId,
            _userPrincipal,
            _targetResource,
            _riskScorePercent,
            _decision,
            block.timestamp
        );

        return keccak256(abi.encodePacked(_auditId, block.timestamp, msg.sender));
    }

    function getTotalLogs() external view returns (uint256) {
        return records.length;
    }

    function getRecord(uint256 index)
        external
        view
        returns (
            string memory auditId,
            string memory userPrincipal,
            string memory targetResource,
            uint256 riskScorePercent,
            string memory decision,
            uint256 timestamp
        )
    {
        require(index < records.length, "Index out of bounds");
        AccessRecord storage r = records[index];
        return (
            r.auditId,
            r.userPrincipal,
            r.targetResource,
            r.riskScorePercent,
            r.decision,
            r.timestamp
        );
    }
}
