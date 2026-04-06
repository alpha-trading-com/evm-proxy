// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.4;

import "./IProxy.sol";
import "./IAlpah.sol";

/// @title DelegateProxyCaller
/// @notice Minimal helper contract that can perform Proxy::proxyCall toward a
///         delegate wallet, where the real AccountId32 is provided per-call.
contract DelegateProxyCaller {
    error OnlyOwner();
    error ProxyCallFailed();
    /// @dev Reverts when ``getAlphaPrice(netuid)`` is not strictly greater than ``minPriceRaoPerAlpha``.
    error AlphaPriceNotAboveMin(uint256 currentPriceRao, uint256 minPriceRao);

    address public owner;
    
    constructor() {
        owner = msg.sender;
    }

    /// @notice Accepts native TAO transfers (plain sends with no calldata).
    receive() external payable {}


    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    /// @notice Owner-only helper to execute a proxy call with a specific proxy type.
    /// @param realAccountId32 The real on-chain AccountId32 / SS58 public key as bytes32.
    /// @param proxyType Proxy type index (e.g. 0 = Any, same as forceProxyType[0]).
    /// @param call SCALE-encoded RuntimeCall (pallet index + call index + encoded args).
    function proxyCall(
        bytes32 realAccountId32,
        uint8 proxyType,
        bytes calldata call
    ) external onlyOwner {
        _proxyCall(realAccountId32, proxyType, call);
    }

    /// @notice Like ``proxyCall``, but only runs if subnet alpha price (RAO per alpha from Alpha precompile) is strictly greater than ``minPriceRaoPerAlpha``.
    /// @param netuid Subnet id passed to ``IAlpha.getAlphaPrice``.
    /// @param minPriceRaoPerAlpha Exclusive lower bound; revert if ``getAlphaPrice(netuid) <=`` this value.
    function proxyCallIfAlphaPriceAbove(
        uint16 netuid,
        uint256 minPriceRaoPerAlpha,
        bytes32 realAccountId32,
        uint8 proxyType,
        bytes calldata call
    ) external onlyOwner {
        uint256 price = IAlpha(IALPHA_ADDRESS).getAlphaPrice(netuid);
        if (price <= minPriceRaoPerAlpha) {
            revert AlphaPriceNotAboveMin(price, minPriceRaoPerAlpha);
        }
        _proxyCall(realAccountId32, proxyType, call);
    }

    function _proxyCall(
        bytes32 realAccountId32,
        uint8 proxyType,
        bytes calldata call
    ) internal {
        uint8[] memory forceProxyType = new uint8[](1);
        forceProxyType[0] = proxyType;

        uint8[] memory callAsUint8 = new uint8[](call.length);
        for (uint256 i = 0; i < call.length; i++) {
            callAsUint8[i] = uint8(call[i]);
        }

        bytes memory data = abi.encodeWithSelector(
            IProxy.proxyCall.selector,
            realAccountId32,
            forceProxyType,
            callAsUint8
        );

        uint256 gasForward = gasleft();
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = IPROXY_ADDRESS.call{gas: gasForward}(data);
        if (!success) revert ProxyCallFailed();
    }
}

