---
name: solidity-smart-contracts
description: >
  Governance and hard-rules for authoring, reviewing, and deploying Solidity
  smart contracts on EVM-compatible chains. Covers reentrancy discipline,
  storage layout, gas optimization constraints, upgradeability pattern
  selection, access control hierarchies, and emergency circuit-breaker design.
  Anchored to Solidity ^0.8.24 and OpenZeppelin v5 as the canonical baseline;
  pin an exact patch version in foundry.toml / hardhat.config.ts for
  reproducible deployments, and benchmark gas-cost figures per compiler/EVM
  version. Use when writing or reviewing any Solidity contract, designing
  proxy upgrade architectures, selecting token standards, auditing access
  control role assignments, or assessing DeFi protocol composability risk.
  Trigger list: new contract file, proxy deployment script, ERC token
  extension, timelock configuration, or any code that transfers ERC-20/ETH
  value.
owner: Solidity Engineer (domain persona)
tier: domain:fintech
scope_tags: [evm, solidity, defi, gas-optimization, smart-contract-security, upgradeable-proxy]
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-solidity-smart-contract-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 2
risk_class: high
stack: [solidity]
context_budget_tokens: 1300
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 10}
  engine: {active: true, priority: 5}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 3}
  generic: {active: true, priority: 7}
activation_triggers:
  - {event: file-edit, glob: "**/*.sol"}
  - {event: help-me-invoked, regex: "(?i)solidity|openzeppelin|upgradeab|proxy|erc.?(20|721|1155)|timelock"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/*.sol"
  - "**/contracts/**"
  - "**/foundry.toml"
  - "**/hardhat.config.*"
---

# Solidity Smart Contracts

## Cardinal Rule

Every Solidity contract MUST be authored as though an adversary with
unbounded capital has already read the deployed bytecode. The threat is
not theoretical: DAO (2016, $60M), Wormhole (2022, $320M), and Euler
Finance (2023, $197M) each exploited exactly the class of assumptions
a developer believed were safe. Correctness, not cleverness, is the
invariant. A clever contract that fails under adversarial conditions is
strictly worse than a simple contract that survives.

## Fail-Fast Rule

Stop and reject (do not proceed, do not patch around) if any of the
following conditions are detected during authoring or review:

- An external call appears before state mutation in the same function
  (checks-effects-interactions violation), EXCEPT for the disciplined
  delta-based-accounting deposit pattern documented under
  §Checks-Effects-Interactions Discipline. That exception requires
  ALL of: (a) `nonReentrant` modifier present, (b) explicit
  `balanceOf(address(this))` measurement before AND after the inbound
  transfer, (c) revert-on-mismatch when `received != requested`, and
  (d) credit only the post-transfer delta. Any other interaction-first
  pattern remains a fail-fast condition.
- `tx.origin` is used for access control anywhere in the codebase.
- `transfer()` or `send()` is used instead of `call{value:}("")`.
- A storage array is iterated without a bounded length cap.
- An upgradeable contract's `initialize()` is not guarded by
  `initializer` modifier from OpenZeppelin v5.
- A UUPS implementation contract lacks `_disableInitializers()` in its
  constructor.
- Arithmetic on token amounts uses floating-point types (`float`,
  `double`) in any off-chain computation layer (see cross-reference to
  `domains/fintech/skills/financial-correctness-and-math`).

No exception is granted for "it's internal only," "the modifier adds
gas," or "the audit didn't flag it." Fail-fast means stop-now.

## When to Apply

Apply this skill for any of the following triggers:

- Authoring a new `.sol` contract file.
- Reviewing a pull request that modifies contract logic or storage layout.
- Designing a proxy upgrade migration (storage slot compatibility check
  required before any implementation swap).
- Selecting between Transparent Proxy, UUPS, or Beacon patterns.
- Assigning or revoking AccessControl roles in deployment scripts.
- Configuring a timelock controller (minimum delay, proposer set,
  executor set).
- Writing a Foundry test suite for any protocol with >$0 TVL.
- Integrating an external price oracle or external token contract.
- Any operation that moves ETH or ERC-20 tokens across contract boundaries.

## EVM Threat Model

Named historical exploits, each illustrating a class of failure that
recurs across protocols.

| Exploit | Year | TVL Lost | Exploit Class | Lesson |
|---|---|---|---|---|
| The DAO | 2016 | $60M | Reentrancy via fallback | State must be updated before external calls; `nonReentrant` guard on all value-moving functions |
| Parity Wallet | 2017 | $30M frozen | Unguarded `delegatecall` initialization | Library contracts with shared state must not expose public initializers; use `_disableInitializers()` |
| Wormhole Bridge | 2022 | $320M | Signature verification bypass (Solana side) | Every cross-chain message MUST verify a cryptographic signature from a controlled signer set; never trust payload metadata alone |
| Ronin Bridge | 2022 | $625M | Compromised validator key set (5-of-9 threshold) | Multi-sig thresholds must be calibrated to adversarial key-compromise scenarios, not operational convenience |
| Euler Finance | 2023 | $197M | Donation attack + flawed liquidation invariant | Protocol invariants (collateral ≥ debt) must hold after every user-callable path including flash-loan-funded donations |

The table is not exhaustive. It is a minimum mandatory recall set. Every
new protocol design must explicitly map its own attack surface against
each row.

## Checks-Effects-Interactions Discipline

The ordering rule: validate inputs first (Checks), mutate all state
second (Effects), call external contracts last (Interactions). Violation
inverts the dependency graph and opens reentrancy paths.

The `nonReentrant` modifier from OpenZeppelin v5
`@openzeppelin/contracts/utils/ReentrancyGuard.sol` is mandatory on
every function that:

- transfers ETH via `call{value:}("")`,
- calls `safeTransfer` or `safeTransferFrom` on any ERC-20, or
- invokes any interface on an address not statically known at compile
  time.

The modifier alone is not sufficient if state is mutated after the
interaction; the ordering rule still applies. The one disciplined
exception is **delta-based accounting on inbound transfers** — when
the vault accepts tokens with non-1:1 transfer semantics
(fee-on-transfer, rebasing), the deposit function MUST measure
`balanceOf(address(this))` before AND after the inbound transfer and
credit the post-transfer delta. This deliberately places the inbound
interaction before the final effect; safety is preserved by
`nonReentrant` plus an explicit revert when the delta does not match
the requested amount (rejecting non-conforming tokens by default).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/// @notice Minimal vault illustrating checks-effects-interactions ordering.
contract CEIVault is ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public immutable token;
    mapping(address => uint256) public balances;

    error ZeroAmount();
    error InsufficientBalance(uint256 requested, uint256 held);
    error UnsupportedToken(uint256 sent, uint256 received);

    constructor(address token_) {
        token = IERC20(token_);
    }

    /// @notice Deposit tokens. Credits the actual amount received (delta-based)
    ///         so fee-on-transfer / rebasing tokens cannot inflate internal balances.
    function deposit(uint256 amount) external nonReentrant {
        if (amount == 0) revert ZeroAmount();
        uint256 balBefore = token.balanceOf(address(this));
        token.safeTransferFrom(msg.sender, address(this), amount);
        uint256 received = token.balanceOf(address(this)) - balBefore;
        if (received != amount) revert UnsupportedToken(amount, received);
        balances[msg.sender] += received;
    }

    /// @notice Withdraw tokens. State zeroed before transfer.
    function withdraw(uint256 amount) external nonReentrant {
        uint256 held = balances[msg.sender];
        if (amount == 0) revert ZeroAmount();
        if (held < amount) revert InsufficientBalance(amount, held);
        // Effects first — reentrancy cannot exploit stale balance
        balances[msg.sender] = held - amount;
        // Interaction last
        token.safeTransfer(msg.sender, amount);
    }
}
```

## Storage & Gas Hard-Rules

| Pattern | Gas Impact | Rule |
|---|---|---|
| Cold SLOAD (first access per tx) | 2,100 gas | Cache in `memory` variable before loop or repeated read |
| Warm SLOAD (subsequent access) | 100 gas | Still cache when called >2 times in one function |
| SSTORE new value (zero → nonzero) | 22,100 gas | Minimize distinct storage writes per user action |
| SSTORE update (nonzero → nonzero) | 5,000 gas | Batch slot writes; avoid toggling flags in hot paths |
| Struct slot packing (uint128 + uint128) | Saves 1 slot = 22,100 gas on first write | Always pack related fields; order fields small-to-large within a slot |
| Dynamic array in storage + unbounded loop | O(n) gas, DoS risk | Use `mapping` for per-user lookups; cap array growth with explicit `MAX_LENGTH` constant |
| `calldata` vs `memory` for external params | ~200 gas per reference | Use `calldata` for all read-only `external` function array/struct params |
| Custom error vs `require` string | ~50 gas per revert | Always use custom errors; never use bare `require("string")` in ^0.8.4+ |
| `immutable` for constructor-set values | 0 storage cost | Declare `immutable` for all values set once in constructor |
| `unchecked` arithmetic on post-validated values | ~30 gas per op | Apply only after a bounds check has made overflow impossible |

Solidity ^0.8.24 enables checked arithmetic by default. The `unchecked`
block is a deliberate opt-out, not a default optimization pass. Every
`unchecked` block MUST have an adjacent comment citing the invariant that
prevents overflow.

## Upgradeability Pattern Selection

| Pattern | Upgrade auth location | Per-call overhead | Key constraint | When to use |
|---|---|---|---|---|
| Transparent Proxy (EIP-1967) | ProxyAdmin contract (separate EOA/multisig) | ~200 gas (admin slot check on every call) | Admin cannot call implementation functions directly | Default for protocols requiring strict admin/user separation |
| UUPS (EIP-1822) | Implementation contract | 0 gas (no proxy-side admin check) | A bricked implementation = dead proxy; `_authorizeUpgrade` must be gated | Preferred when upgrade frequency justifies gas savings and team accepts the bricking risk |
| Beacon Proxy | BeaconProxy + UpgradeableBeacon | ~300 gas (two SLOAD: beacon + impl) | All proxies upgrade atomically on beacon update | Factory patterns deploying many identical instances (e.g., per-user vaults) |
| Diamond (EIP-2535) | DiamondCut facet | Variable (facet dispatch adds 1 SLOAD) | Storage layout complexity; requires formal slot audit per facet | Large protocols (>24KB bytecode limit) with independent upgrade domains per facet |

MUST NOT mix upgrade patterns within a single protocol's core contracts.
Choosing UUPS for the vault and Transparent for the governance module
creates dual admin surfaces.

Storage layout changes across implementation versions MUST be validated
with `@openzeppelin/upgrades-core` (Hardhat plugin) or the
`forge inspect --layout` diff before any upgrade transaction is broadcast.
Never reorder existing storage variables; never insert a variable above
an existing slot.

## Token Standards & Extensions

All token contracts MUST use OpenZeppelin v5 as the base. Do not
implement EIP logic from scratch. The table shows canonical import
paths for ^0.8.24 + OZ v5.

| Standard | Primary import | Recommended extensions | Notes |
|---|---|---|---|
| ERC-20 | `@openzeppelin/contracts/token/ERC20/ERC20.sol` | `ERC20Permit` (gasless approvals, EIP-2612), `ERC20Burnable`, `ERC20Capped` | For upgradeable: `contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol` |
| ERC-721 | `@openzeppelin/contracts/token/ERC721/ERC721.sol` | `ERC721URIStorage`, `ERC721Enumerable`, `ERC721Burnable` | Avoid `Enumerable` on high-frequency minting contracts — O(n) storage cost |
| ERC-1155 | `@openzeppelin/contracts/token/ERC1155/ERC1155.sol` | `ERC1155Supply`, `ERC1155Burnable` | Preferred for protocols managing fungible + non-fungible assets in a single contract |
| ERC-4626 | `@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol` | `ERC4626` + custom fee hooks | Standard tokenized vault interface; use for yield-bearing vaults exposed to DeFi composability |

ERC-777 is explicitly prohibited. Its `tokensReceived` hook introduces
reentrancy paths that have been exploited repeatedly. Use ERC-20 with
a permit extension instead.

## Access Control & Emergency Mechanisms

### Role-Based Access Control

Use `AccessControl` from
`@openzeppelin/contracts/access/AccessControl.sol`. Declare every role
as a `bytes32 constant` computed via `keccak256`. Never use raw address
comparisons (`require(msg.sender == owner)`) in new contracts — the
`Ownable` pattern is acceptable only for single-owner contracts with no
role hierarchy.

Minimum role set for any DeFi protocol:

- `DEFAULT_ADMIN_ROLE`: sole authority to grant/revoke all other roles;
  MUST be assigned to a multi-sig (Gnosis Safe ≥3-of-N signers), never
  to a single EOA in production.
- `PAUSER_ROLE`: authority to call `pause()`.
- `UPGRADER_ROLE` (upgradeable contracts only): authority to authorize an
  implementation upgrade.
- Protocol-specific operational roles (e.g., `MINTER_ROLE`,
  `LIQUIDATOR_ROLE`).

### Emergency Pause

Every protocol that holds user funds MUST implement `Pausable` from
`@openzeppelin/contracts/utils/Pausable.sol`. The `whenNotPaused`
modifier MUST be applied to all state-changing external functions that
accept deposits or execute transfers. Withdraw paths MAY remain
unpaused by design to allow user exit during emergencies — this choice
must be documented explicitly in NatSpec.

### Timelock

Any privileged operation that is not a direct emergency response MUST
be gated behind `TimelockController` from
`@openzeppelin/contracts/governance/TimelockController.sol`.

Minimum timelock delays by operation class:

| Operation | Minimum delay |
|---|---|
| Implementation upgrade (UUPS / Transparent) | 48 hours |
| Role grant for `DEFAULT_ADMIN_ROLE` | 72 hours |
| Parameter changes affecting user funds (fee caps, rate limits) | 24 hours |
| Protocol parameter changes with no direct fund risk | 12 hours |

These delays are floor values, not targets. A team choosing 2 hours for
an upgrade window is making an active security trade-off that requires
ADR documentation.

## Anti-patterns

| Pattern | Why wrong | What to do instead |
|---|---|---|
| `tx.origin` for auth | Delegated call or phishing contract can impersonate any EOA | Use `msg.sender` exclusively for authorization |
| `transfer()` / `send()` | Gas-limited to 2,300; fails with smart contract wallets (ERC-4337) | Use `call{value: amount}("")` wrapped in a reentrancy guard |
| Unbounded loop over storage array | Gas cost grows linearly; attacker can push array length past block gas limit | Cap array with `MAX_LENGTH` constant or use `mapping` + separate length counter |
| `selfdestruct` | Deprecated in EIP-6049; behavior undefined post-EOF; cannot be safely used | Remove; use fund-recovery admin function with timelock instead |
| Initializing upgradeable contracts in a constructor | `constructor` runs on implementation, not proxy; state is lost | Use `initialize()` with `initializer` modifier; call `_disableInitializers()` in constructor |
| Storing secrets or salts on-chain | All storage is publicly readable on any node | Commit hashes off-chain; use ZK proofs or Merkle trees for on-chain verification |
| Float arithmetic for token amounts in off-chain scripts | Precision loss causes incorrect transfer amounts | Use `BigInt` (JS) or `Decimal` library; see `domains/fintech/skills/financial-correctness-and-math` |
| Hardcoded `block.timestamp` deadline comparisons | Validators can manipulate `block.timestamp` by ~12 seconds | Use block numbers or add a tolerance window of ≥15 seconds |
| Admin role assigned to a single EOA in production | Single private-key compromise = full protocol control | Assign `DEFAULT_ADMIN_ROLE` to a Gnosis Safe with ≥3-of-N threshold |
| Reusing storage slot positions across implementation versions | Slot collision corrupts existing data on upgrade | Use append-only storage layout; validate with `forge inspect --layout` diff |

## Cross-References

- `core/security-and-auth` — JWT, API key lifecycle, and OWASP Top 10
  patterns apply at the off-chain API layer that gates admin calls
  (timelock proposer authentication, relayer key management). Reentrancy
  and authorization discipline overlaps; ADR-052 VETO floor applies to
  security review of both layers.

- `core/architecture-decisions` — Proxy pattern selection (Transparent vs
  UUPS vs Beacon) is an L3 architectural decision requiring a formal ADR
  per this skill's governance. Storage layout migrations require the same
  ADR process.

- `domains/fintech/skills/financial-correctness-and-math` — Token amounts
  computed off-chain (PnL, slippage, liquidation price) MUST use decimal
  arithmetic libraries before being passed as calldata to contracts.
  Float-computed `amount` arguments passed to `transfer` or `mint` are a
  precision defect regardless of Solidity's integer handling on-chain.

- `domains/fintech/skills/exchange-api-integration` — Relayer and
  settlement contracts that consume exchange API data (prices, order IDs)
  inherit the oracle-manipulation surface described in the EVM Threat
  Model. Price feeds consumed on-chain must be sourced from a time-weighted
  average (TWAP ≥ 30 minutes) or a Chainlink aggregator with staleness
  threshold ≤ 3600 seconds.

## ADR Anchors

- **ADR-052** (`multi-model-dispatch-by-role`): Security review of any
  Solidity contract is subject to the VETO floor defined in ADR-052.
  Code-reviewer and security-engineer archetypes flagged `veto_floor: true`
  MUST both approve before a contract change is merged. One archetype's
  approval alone is insufficient.

- **ADR-058** (`brainstorm-gate-and-two-pass-review`): All Solidity
  contracts with external value transfer MUST complete a two-pass review:
  Pass 1 is structural (architecture, storage layout, upgrade path), Pass 2
  is adversarial (reentrancy surfaces, access-control gaps, oracle
  manipulation vectors). The two passes MUST be conducted sequentially, not
  merged into a single review session.
