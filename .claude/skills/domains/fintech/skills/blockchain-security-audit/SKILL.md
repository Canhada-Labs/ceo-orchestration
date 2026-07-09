---
name: blockchain-security-audit
description: Audit-grade security review for EVM smart contracts and DeFi protocols
  on Solidity ^0.8.24 with OpenZeppelin Contracts v5.x. Codifies EthTrust Security
  Levels + OWASP SCSVS as primary coverage with SWC + DASP Top 10 retained as
  legacy mapping, vulnerability-class detection technique, formal-verification
  workflow (Certora / Halmos / SMTChecker), severity schema with mandatory
  proof-of-exploitability for High+ findings, audit-report structure, and DeFi
  composability threat model (oracle dependence, flash-loan surface, governance
  vector, bridge trust). Operates under ADR-052 VETO floor — sign-off authority
  delegated to the existing security-engineer archetype on Opus (claude-opus-4-8);
  Critical or High findings without a verified fix BLOCK ship. Use when reviewing pre-mainnet
  contracts, pre-upgrade diffs, post-incident forensics, governance-parameter
  changes, treasury-flow code, bridge messaging code, or any contract surface where
  a single exploit transaction can drain user funds or brick the protocol.
owner: Smart Contract Auditor (domain persona; sign-off delegated to security-engineer archetype on Opus)
secondary_owner: DeFi Threat Researcher (domain persona)
tier: domain:fintech
scope_tags: [smart-contract-audit, defi-security, vulnerability-research, formal-verification, exploit-analysis, audit-reporting]
veto_floor: true
model_required: claude-opus-4-8
inspired_by:
  - source: msitarzewski/agency-agents/specialized/blockchain-security-auditor.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
  - source: affaan-m/ecc/skills/nodejs-keccak256/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 2
risk_class: high
stack: [solidity]
context_budget_tokens: 1500
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 9}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 2}
  generic: {active: true, priority: 7}
activation_triggers:
  - {event: file-edit, glob: "**/*.sol"}
  - {event: help-me-invoked, regex: "(?i)smart.?contract|audit|reentr|exploit|swc|owasp.?scsvs"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/*.sol"
  - "**/contracts/**"
  - "**/bridge/**"
  - "**/treasury/**"
source: affaan-m/ecc@81af4076 skills/nodejs-keccak256/
license: MIT
---

# Blockchain Security Audit

Smart contracts are bearer assets. A single reachable bug drains the
treasury in one transaction and the chain remembers forever. This skill
codifies the audit doctrine that turns a code-review into an audit:
named threat coverage, runnable proofs of exploitability, formal
property checks, and a report whose findings a developer can fix
directly. It operates under ADR-052 VETO floor — sign-off is delegated
to the existing `security-engineer` archetype running on Opus, and
Critical or High findings without a verified patch BLOCK ship.

## Cardinal Rule

Every Critical or High finding MUST ship with a runnable Foundry test
asserting attacker profit or invariant violation, OR a step-by-step
exploit transcript with concrete impact in USD or token-units. A
finding without proof-of-exploitability is either Medium-or-below, or
the auditor downgrades it and explains why. Severity without proof is
severity-by-feeling, and severity-by-feeling is how audit reports
become marketing copy.

## Fail-Fast Rule

Halt the audit and escalate to Owner BEFORE writing findings if ANY:

1. Deployed bytecode does not match submitted source
   (`forge verify-bytecode` mismatch or block-explorer source unverified).
2. Compiler pragma is unpinned or pinned below `0.8.x` (`pragma solidity
   >=0.7.0` rejected; `pragma solidity ^0.8.24` accepted as a minor
   range per Solidity SemVer — deployments requiring exact
   reproducibility additionally pin a specific patch in build config).
3. Test suite < 70% line coverage on contracts in scope.
4. Critical functions (admin, upgrade, withdrawal) lack any test.
5. Scope is moving — files change during the audit window without a
   frozen commit hash.

A halted audit emits a single-line gate report ("Audit blocked —
condition #N — resume after team resolves") and zero findings.
Findings written against moving scope are unfalsifiable.

## When to Apply

Trigger an audit (this skill MUST be loaded by the `security-engineer`
archetype operating on Opus) in any of the following situations:

- **Pre-mainnet deployment** of any contract handling user funds,
  governance votes, or bridge messages — mandatory regardless of TVL.
- **Pre-upgrade** of a proxy whose new implementation changes storage
  layout, access control, or external-call surface.
- **Post-incident forensics** within 24h of an exploit detection
  (incident-commander archetype owns the runbook; this skill owns
  root-cause attribution).
- **Governance-parameter change** altering fee math, oracle feeds,
  liquidation thresholds, or quorum / timelock values.
- **Regulatory or compliance review** triggered by jurisdictional
  filing (MiCA, BitLicense, TVT-rated custody) where the audit
  artifact is a legal deliverable.
- **Dependency bump** of a security-critical library (OpenZeppelin
  major, Chainlink aggregator, Uniswap router, LayerZero endpoint).
- **New external integration** (oracle, AMM pair, bridge connector)
  introducing a fresh trust assumption.

A `core/code-review-checklist` sweep is NOT a substitute for any of
the above triggers.

## ADR-052 VETO Floor — Audit Authority

This skill is registered `veto_floor: true` and
`model_required: claude-opus-4-8`. Sign-off authority is delegated to
the existing `security-engineer` archetype operating under this skill;
the same-LLM author's verdict is insufficient. Sign-off is mandatory on
any L3+ change touching the surface listed under §When to Apply. A
reviewer waiver is insufficient.

| Audit verdict | Ship action |
|---------------|-------------|
| **PASS** (no Critical, no High) | Ship with documented Medium / Low remediation plan |
| **PASS-WITH-FIXES** (High patched + re-tested) | Ship after re-audit confirms patch closes the exploit |
| **ADJUST** (open Mediums, no Critical/High) | Ship; attach Medium remediation timeline to PR |
| **SOFT REJECT** (open High) | Block ship; team patches; auditor re-runs PoC |
| **VETO** (open Critical) | Block ship; Owner override + ADR amendment + auditor amendment required |

A VETO is lifted only by: (a) verified patch where the auditor's PoC
fails on the patched contract, or (b) Owner-signed ADR amendment
explicitly acknowledging residual risk + compensating control +
monitoring rule. Reviewer override of a VETO is a governance
violation logged to audit trail.

## Severity Schema

Severity is CVSS-style impact × likelihood with a mandatory PoC gate
at High and above. Likelihood reads attacker capability (privileges,
transaction count, capital) against the threat model.

| Severity | Impact | Likelihood | PoC requirement |
|----------|--------|------------|-----------------|
| **Critical** | Direct loss of user funds; protocol insolvency; permanent DoS; sovereign-key compromise | No special privilege; single tx; capital ≤ flash-loan limit | Runnable Foundry test asserting attacker profit > 0 OR invariant violation |
| **High** | Conditional fund loss (specific state); privilege escalation; brick-by-admin; locked withdrawals | Privileged role compromise OR market state OR multi-step ≤ 5 tx | Runnable Foundry test OR step-by-step exploit transcript with on-chain trace |
| **Medium** | Griefing; temporary DoS; value leakage under specific conditions; missing access on non-fund function | Ordinary user OR adversarial market participant | Concrete scenario + impact range; PoC strongly recommended |
| **Low** | Best-practice deviation with security implication; gas-DoS-enabling inefficiency; missing forensic event | Minor; no direct exploit | Description + why-it-matters |
| **Informational** | Code quality; documentation gap; style inconsistency | n/a | Description only |

A finding without the listed PoC artifact is downgraded one level, or
the auditor explains in-finding why the artifact is infeasible.
Marking a fund-loss bug "Informational" to soften delivery is an
audit anti-pattern (§Anti-patterns).

## Coverage Standards — EthTrust + SCSVS Primary, SWC + DASP Legacy

Every audit MUST sweep the **current maintained** standards as
primary coverage:

- **EEA EthTrust Security Levels Specification** (Enterprise Ethereum
  Alliance) — actively maintained Levels [S]/[M]/[Q] classification.
- **OWASP SCSVS** (Smart Contract Security Verification Standard) —
  actively maintained verification checklist.

The **SWC Registry** (https://swcregistry.io) and **DASP Top 10** are
retained as **legacy mapping** for historical findings and
defense-in-depth — SWC is no longer actively maintained, and the EEA
project explicitly references EthTrust + SCSVS as the current baseline.
The table below maps SWC IDs (legacy) ↔ vulnerability class ↔ detection
technique. An audit that skips a class without justification fails
Pass-1 review regardless of which taxonomy surfaces it.

| SWC | DASP | Class | Primary detection |
|-----|------|-------|-------------------|
| SWC-101 | DASP-3 | Integer over/underflow | Solidity 0.8+ default check; scrutinise `unchecked { ... }` line-by-line |
| SWC-104 | DASP-4 | Unchecked call return | Slither `unchecked-lowlevel` / `unchecked-send` |
| SWC-105 | DASP-2 | Unprotected ether withdrawal | Slither `arbitrary-send-eth`; manual auth sweep |
| SWC-106 | DASP-2 | Unprotected SELFDESTRUCT | Slither `suicidal` |
| SWC-107 | DASP-1 | Reentrancy | Slither `reentrancy-eth` / `reentrancy-no-eth`; CEI review |
| SWC-112 | DASP-2 | Delegatecall to untrusted callee | Slither `controlled-delegatecall`; manual proxy review |
| SWC-114 | DASP-7 | Transaction-order dependence | Manual: tx-ordering-dependent state; commit-reveal? |
| SWC-115 | DASP-2 | tx.origin authentication | Slither `tx-origin` |
| SWC-116 / 120 | DASP-8 / DASP-6 | Block values as time + weak randomness | Manual: `block.timestamp` / `block.number` / `blockhash` in critical paths |
| SWC-118 | n/a | Initializer callable twice | Slither `uninitialized-state`; `_disableInitializers` in ctor |
| SWC-124 | n/a | Write to arbitrary storage slot | Manual: assembly `sstore` review |
| SWC-128 | DASP-5 | DoS via gas limit | Echidna fuzz unbounded loops; array-growth review |
| SWC-132 | DASP-5 | Unexpected ether balance | Manual: `address(this).balance` for accounting |
| SWC-136 | n/a | Unencrypted private data on-chain | Manual: `private` storage holding secret-by-design |

DASP categories not surfacing directly in the SWC subset above:
DASP-9 (Short Address) is a post-Constantinople non-issue; DASP-10
(Unknown Unknowns) is the residual class formal verification targets.
DASP-8 (Time Manipulation) maps onto SWC-116; DASP-6 (Bad Randomness)
maps onto SWC-120 — both are present in the table.

## Vulnerability Classes

Each class names: detection technique and a real-exploit reference
where one exists. The exploit corpus IS the audit pattern library —
the next exploit is usually a variant of a previous one.

**Reentrancy.** Slither (`reentrancy-eth`, `reentrancy-no-eth`,
`reentrancy-benign`) catches the structural pattern at high
confidence. Manual review extends to ERC-777 / ERC-1155 hook-induced
reentrancy and read-only reentrancy through view functions consumed
as oracle inputs. Findings cite: external-call site, following state
update, attacker re-entry path, victim balance-impact. References:
The DAO 2016 (~$60M ETH), Curve Finance July 2023 (Vyper compiler
reentrancy-guard miscompilation, ~$70M).

**Integer over/underflow.** Solidity 0.8.0+ enables checked arithmetic
by default; the real surface is `unchecked { ... }` blocks and
assembly. Every `unchecked` block is reviewed line-by-line and the
auditor records which invariant guarantees no wraparound. Reference:
bzx 2020 margin-trade integer issue.

**Access control.** Enumerate every state-modifying external / public
function and verify an explicit modifier OR inline auth check from
a verified token / role registry. Cross-check upgrade paths
(`_authorizeUpgrade`, `initialize` / `_disableInitializers`).
References: Parity Wallet 2017 (uninitialized library — anyone
calls `initWallet`; ~$30M + ~$150M frozen across two incidents),
Wormhole 2022 (guardian-set signature-verification bypass, ~$320M).

**Oracle manipulation.** Identify every price source (Uniswap V2 spot,
Uniswap V3 TWAP, Chainlink aggregator, custom). Spot prices from a
single AMM pool are flash-loan-manipulable in one transaction — flag
as Critical unless flash-loan-resistant (checkpointed TWAP, multi-
oracle median). Verify Chainlink staleness window + roundId
monotonicity. Reference: Mango Markets 2022 (~$117M; thin perp
market).

**Flash-loan attacks.** Model every external view or state read that
influences a financial decision against an actor renting ≥ $100M for
one block. Examples: collateral valuation reads spot price; voting
weight reads token balance at `block.timestamp`; liquidation reads
under-margin pools without TWAP smoothing. References: Euler Finance
2023 (~$197M; donate-to-reserves + liquidation-incentive math),
Beanstalk 2022 (~$182M; flash-loan governance vote).

**MEV / sandwich.** Identify swap / deposit / withdraw paths with a
slippage parameter. Verify `minAmountOut` is set from the user, not
from `getAmountsOut(...)` at call-time (current-reserves reads make
slippage ineffective against sandwiches). Verify deadline parameter
is enforced and short-bounded.

**Signature replay.** Every `permit` / EIP-712 path MUST include
`nonce`, `deadline`, and `chainId` in the signed digest. Verify
nonce-incremented-on-use and contract chainId matches
`block.chainid`. Reference: Optimism / Wintermute 2022 (~$20M;
chainId omission enabled multi-chain replay).

**Upgradeability.** Verify storage layout compatibility across
versions (`forge inspect ... storageLayout` diff or
`@openzeppelin/upgrades`). Verify `initialize()` has `initializer`
modifier; implementation has `_disableInitializers()` in constructor.
Verify `_authorizeUpgrade` is owner / multisig / timelock. Verify no
function-selector clash between proxy admin and implementation.
Reference: Audius 2022 (~$6M; storage collision in upgrade).

**Governance attacks.** Model voting-power source (snapshot vs
balance at vote time), delegation, timelock, quorum. Voting that
reads token balance at `block.timestamp` of cast (not snapshot) is
flash-loan-attackable. If attacker capital required for quorum ×
token price < typical exploit profit, flag Critical.

**Cross-chain bridge.** Verify signer-set freshness (rotated keys
honored, revoked keys rejected), per-message nonce committed on
destination, proof verification matches the attestation format,
and no source-emit / destination-redeem desync path. References:
Ronin Bridge 2022 (~$625M; 5-of-9 multisig key compromise), Wormhole
2022 (~$320M; signature-verification bypass), Nomad Bridge 2022
(~$190M; uninitialized trusted-root + replayable proofs), BNB Bridge
2022 (~$570M; IAVL Merkle proof verification flaw).

**ERC-4626 inflation (donation attack).** Any ERC-4626 vault MUST
mitigate the first-depositor share-price inflation attack — virtual
shares + virtual assets (OpenZeppelin v5 default), or deployer seed
deposit locked forever, or per-share floor enforced. Test: compute
share price after a 1 wei deposit + large direct-transfer donation;
if the next depositor receives 0 shares for any non-zero deposit,
flag Critical.

**JIT (just-in-time) liquidity.** Concentrated-liquidity AMMs
(Uniswap V3) and lending protocols with lender-rotation surface let
LPs / lenders provide liquidity for one block, capture fees /
interest, and withdraw. When protocol fee math assumes time-weighted
exposure but implementation pays per-block, JIT extracts fees from
passive LPs.

**Off-chain hash-algorithm mismatch (Keccak-256 vs NIST SHA3-256).**
The audit surface extends past on-chain bytecode to the off-chain
helpers a contract *trusts* to produce hashes byte-identical to its
own `keccak256(...)` — indexers, signing backends, allowlist / Merkle
generators, storage-slot readers. Ethereum uses original Keccak-256;
several standard libraries expose NIST FIPS-202 SHA3-256 under a
confusingly similar name (Node's `crypto.createHash('sha3-256')`
being the canonical trap), and the two return **different** digests
for the same input with no error raised. Note the scope: inside
Solidity, `keccak256(...)` is already correct — this class lives in
the JS/TS/tooling layer. Where it bites: function selectors and event
topics in an off-chain indexer; EIP-712 digests in a signing service
(the digest silently diverges from the contract's, so valid signatures
fail — or a "working" test-only path masks the divergence); Merkle
roots in an allowlist generator (an off-chain root built with the
wrong hash cannot be proven against on-chain `keccak256` — legitimate
users locked out of a mint/claim, or a wrong root committed); and
storage-slot derivation in a state reader (reads the wrong slot).
Severity tracks whether the mismatch gates funds or access: an
allowlist that controls a claim is High; a read-only indexer
inconsistency is Medium/Low. **Detection:** grep the off-chain code
(`grep -rn "createHash.*sha3"` over `*.ts`/`*.js`, excluding
`node_modules`); confirm JS/TS hashing uses a Keccak-aware helper
(ethers `keccak256` / `id` / `solidityPackedKeccak256`, viem
`keccak256`, web3 `keccak256` / `soliditySha3`); and require a
**parity test** asserting the off-chain digest equals the contract's
`keccak256` for a known vector before trusting any off-chain hash in a
fund or access path.

## Static + Dynamic Analysis Toolchain

Tools find different bug classes. Run all of them; do not assume any
single tool covers the surface.

| Tool | Author | Catches | Misses |
|------|--------|---------|--------|
| **Slither** | Trail of Bits | Reentrancy, suicidal, arbitrary-send, controlled-delegatecall, uninitialized-state, ERC-conformance, function-summary | Economic exploits, business-logic bugs, cross-contract composability |
| **Mythril** | ConsenSys | Symbolic-execution path coverage on small contracts; assertion violations; reachable selfdestruct | Scales poorly on > ~500 LOC; deep-call-graph timeouts |
| **Echidna** | Trail of Bits | Property-based fuzz on user-defined invariants; coverage-guided | Invariants the auditor did not write; rare-event paths |
| **Foundry invariants** | Paradigm | Property-based + stateful fuzz; faster than Echidna for smaller scopes | Same as Echidna; deep state-machine paths |
| **Halmos** | a16z | Symbolic execution with SMT backend; bounded-loop unrolling | Unbounded loops; non-linear arithmetic edge cases |
| **SMTChecker** | Solidity built-in | Inline assertion proof attempts; off-by-one in arithmetic | Cross-function reasoning; storage-aliased state |
| **forge verify-bytecode** | Foundry | Bytecode-vs-source mismatch | Compiler-introduced bugs (Vyper Curve case) |

The audit MUST run Slither + at least one fuzz tool (Echidna or
Foundry) + at least one symbolic tool (Mythril or Halmos) on every
contract in scope. Tool output is triaged — every flagged item is
either confirmed as a finding or annotated as a false positive with a
reason.

## Formal Verification Workflow

Formal verification proves properties hold across all inputs, not just
fuzz-explored inputs. Use it where the cost of an undiscovered bug
exceeds the cost of writing the spec.

| Tool | When to use | Spec language | Example property |
|------|-------------|---------------|------------------|
| **Certora Prover** | Critical money-flow contracts (vault accounting, AMM math, lending health-factor) | CVL (Certora Verification Language) | "totalAssets() ≥ Σ user_balances() always" |
| **Halmos** | Bounded symbolic checks during CI; faster iteration than Certora | Solidity test functions with `assert(...)` | "for all amount in [0, 2^96], deposit(amount) then withdraw(shares) returns ≤ amount" |
| **SMTChecker** | Function-local arithmetic safety; off-by-one detection | Solidity `assert` annotations | "no `unchecked` block can wrap" |

The auditor writes the property specification BEFORE running the tool;
a tool-passing run with no specs proves nothing. A passing Certora run
on three properties of a vault is more meaningful than a coverage-only
fuzz run on the same code. Properties MUST be derived from the
protocol invariants the team documents — if no invariants are
documented, the auditor extracts them and submits them as Finding
class "Informational — invariants not specified" before formal work
begins.

## Audit Report Structure

Reports the team can act on without follow-up clarifications are the
deliverable. Every report has these sections in this order:

**Front matter:** Project, Audit lead handle (domain persona) + delegated
VETO sign-off authority (`security-engineer` archetype on Opus per
ADR-052), Scope commit (40-hex SHA), Audit window (ISO start → ISO end),
Methodology pointer.

**§1 Executive Summary** — one-paragraph protocol description;
contract count and Solidity SLOC at `^0.8.24`; severity count matrix
(Critical / High / Medium / Low / Informational × Open / Fixed /
Acknowledged); verdict (PASS / PASS-WITH-FIXES / ADJUST / SOFT REJECT
/ VETO per §ADR-052 VETO Floor); one-paragraph residual-risk summary.

**§2 Scope** — per-contract SLOC and cyclomatic-complexity table;
explicit out-of-scope list with reasons.

**§3 Methodology** — numbered list: manual line-by-line review
(auditor + secondary), static analysis (Slither + Mythril symbolic),
property-based fuzz (Foundry invariants or Echidna), formal
verification (Certora / Halmos), economic and game-theory modelling,
bytecode verification (`forge verify-bytecode`).

**§4 Findings** — one subsection per finding. Mandatory fields:

- **ID:** `[C-NN]` / `[H-NN]` / `[M-NN]` / `[L-NN]` / `[I-NN]`
- **Severity / Status:** Critical|High|Medium|Low|Informational ×
  Open|Fixed|Acknowledged
- **Location:** `ContractName.sol#Lxx-Lyy`
- **Class:** EthTrust SL ([S]/[M]/[Q]) and/or SCSVS V-NN section as
  primary taxonomy; SWC-ID + DASP category as legacy mapping where
  applicable
- **Description:** concrete vulnerability narrative
- **Impact:** attacker outcome; financial estimate; affected users
- **Proof of Concept:** runnable Foundry test in
  `test/exploits/<ID>.t.sol` with `forge test --match-test <name>
  -vvvv`, asserting `profit > 0` OR invariant violation (mandatory
  for Critical / High per §Cardinal Rule)
- **Recommendation:** specific code change citing the line

**§5 Appendix** — tool output summaries, invariant catalogue, fuzz
seed list, bytecode-verification log.

Canonical Foundry PoC scaffold:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract Exploit_C_01 is Test {
    IERC20 internal constant token = IERC20(0x0000000000000000000000000000000000000000); // replace with target token address
    function setUp() public { vm.createSelectFork("mainnet", 18_500_000); }
    function test_C_01_drainsVault() public {
        address attacker = makeAddr("attacker");
        uint256 before_ = token.balanceOf(attacker);
        vm.startPrank(attacker);
        // exploit steps ...
        vm.stopPrank();
        uint256 profit = token.balanceOf(attacker) - before_;
        assertGt(profit, 0, "exploit should be net-profitable");
    }
}
```

## Threat Model — DeFi Composability

Composability is the multiplier that turns a Medium finding in
contract A into a Critical finding in protocol B that integrates A.
Every audit MUST enumerate composability dependencies.

| Dependency | Threat | Audit question |
|------------|--------|----------------|
| **Oracle (price)** | Manipulable spot, stale Chainlink, single-point failure | Flash-loan-resistant? Staleness window enforced? Round-ID monotonicity? |
| **Flash loan provider** | Attacker rents ≥ $100M for one block | Does any path compute a decision from single-block-readable state? |
| **Governance** | Voting-weight attack via flash loan, vote-buying, timelock bypass | Snapshot-based? Quorum × token price > exploitable surplus? |
| **Bridge** | Source-chain message replay; signer-set compromise | Per-message nonce committed on destination? Signer-set rotation honored? |
| **Token (ERC-20)** | Fee-on-transfer, rebasing, blacklist, custom callbacks | Protocol assumes `transfer` returns exact `amount`? Supports ERC-777 / ERC-1155 hooks? |
| **AMM pool** | Pair-creation race; liquidity-removal during settlement | Pool address pinned or factory-derived per call? |
| **Off-chain hashing helper** | NIST SHA3 vs Keccak-256 divergence in an allowlist / signing / indexer path the contract trusts | Off-chain hash proven byte-equal to on-chain `keccak256` for a known vector? |
| **Liquidator bot** | Gas-DoS in liquidation path | Liquidation gas-bounded? Partial-liquidation when full reverts? |

A protocol integrating `n` upstream protocols inherits the threat
model of all `n`; the audit MUST list those threats and confirm the
integrating contract handles each.

## Anti-patterns

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Marking a fund-loss finding "Informational" to soften delivery | Severity-by-feeling; team ships, attacker drains | Use §Severity Schema; downgrade only with documented reason |
| "Tested in testnet" treated as audit | Testnet ≠ mainnet adversary model; no flash-loan, no real capital, no MEV | Independent + adversarial review on mainnet fork (`vm.createSelectFork`) |
| Gas-cost review presented as security review | Gas optimisation can introduce bugs (storage packing, custom errors) | Separate gas from security; flag gas changes that alter access-check ordering |
| LLM-only review with no manual line-by-line | LLMs miss novel logic and economic exploits; first-pass triage only | Manual review is the floor; tools and LLMs are amplifiers |
| Slither / Mythril clean → "no findings" | Tools catch ~30% of real bugs; the other 70% are logic + economic | Manual review mandatory; tool-clean is necessary, not sufficient |
| Trusting OpenZeppelin = no review | Misuse of safe libraries is its own class (Initializable misuse, ReentrancyGuard wrong scope) | Review the integration even when the library is audited |
| `onlyOwner` accepted without checking ownership | Owner is often an EOA; one stolen key = full compromise | Verify owner is multisig OR timelock; flag EOA owner on production |
| Auditing source while deployed bytecode differs | Supply-chain attack vector | `forge verify-bytecode`; halt audit on mismatch (§Fail-Fast) |
| Off-chain helper hashes Ethereum data with `crypto.createHash('sha3-256')` | NIST SHA3-256 ≠ Keccak-256; digest diverges from on-chain `keccak256` silently — breaks allowlists, EIP-712, selectors | Keccak-aware lib (ethers / viem / web3) + a parity test vs on-chain `keccak256` for a known vector |
| High finding without runnable PoC | Unfalsifiable; team disputes; auditor loses leverage | Foundry test asserting profit > 0 OR invariant violation (§Cardinal Rule) |
| Audit window includes scope-changing commits | Findings against moving target are stale on delivery | Halt audit (§Fail-Fast #5); resume on frozen commit |
| Auditor amends own VETO without re-PoC | Defeats VETO floor purpose | Re-run PoC against patched contract; verdict only changes if PoC fails |

## Cross-References

- `core/security-and-auth` — broader OWASP / threat-model worksheet /
  detection-as-code; this skill is the EVM-smart-contract sub-domain.
- `core/code-review-checklist` — general code-review patterns; an
  audit subsumes a code-review, NOT vice-versa (see §When to Apply).
- `domains/fintech/skills/solidity-smart-contracts` — Solidity
  authoring patterns this skill audits against; auditor and author
  MUST agree on Solidity / OpenZeppelin version pin.
- `domains/fintech/skills/financial-correctness-and-math` — fixed-
  point math, round-to-protocol direction, invariant-system patterns;
  vault-accounting findings cite this skill's invariants.
- `core/incident-management` — runbook for active-exploit response;
  incident-commander owns execution, auditor owns root-cause and
  post-mortem authoring.
- `core/observability-and-ops` — audit-log shape for on-chain events
  the auditor recommends emitting; SIEM ingestion contract.

## ADR Anchors

- **ADR-052 (multi-model dispatch by role)** — registers `veto_floor`
  semantics and Opus-mandate for security archetypes. This skill
  declares `veto_floor: true` and `model_required: claude-opus-4-8`
  per ADR-052 §VETO_FLOOR_ROLES. Audit sign-off authority is delegated
  to the existing `security-engineer` archetype already in
  `_lib/agent_frontmatter.VETO_FLOOR_ROLES` (5-role floor post-Wave-1c);
  no new agent role is added in Wave 2.
- **ADR-058 (brainstorm gate and two-pass review)** — the audit
  workflow IS a two-pass review: Pass 1 inventories scope and builds
  threat model; Pass 2 generates findings against the model. A
  single-pass audit fails ADR-058 §two-pass review.
- **ADR-095 (calendar-gate retraction + Codex MCP cross-LLM gate)** —
  auditor findings are eligible for same-LLM-bias review via Codex
  MCP. Confirmations #25-#29 (S90-S93) show Codex catching ~5-10
  unique findings per ceremony that same-LLM Claude archetypes
  missed; this skill recommends Codex re-pass on every Critical /
  High finding before closeout.

Runnable parity proof (the digests differ on the SAME input — no error is
raised, which is exactly why the class survives review):

```js
// node — SHA3-256 (NIST FIPS-202) vs Keccak-256 (original, Ethereum)
const { createHash } = require("node:crypto");
const { keccak256 } = require("js-sha3");   // or ethers' keccak256

const nist = createHash("sha3-256").update("").digest("hex");
const eth  = keccak256("");

console.log(nist);
// a7ffc6f8bf1ed76651c14756a061d62683576285280f30987fda07fda0f9724c
console.log(eth);
// c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
console.log(nist === eth); // false — pin this assertion in a parity test
```

Both calls succeed; only a parity test against a known Keccak-256 vector
(e.g. the empty-string digest above, or any digest cross-checked with
Solidity's `keccak256`) catches a wrong-primitive substitution.

## References

- SWC Registry — https://swcregistry.io
- DASP Top 10 — DeFi-era class taxonomy
- Standards: EIP-712, ERC-20 / ERC-4626 / ERC-777 / ERC-1155,
  EIP-2535 (Diamond), EIP-1967 (Proxy storage), EIP-1153 (transient)
- Solidity ^0.8.24 docs — checked-arithmetic, `unchecked` block
- OpenZeppelin Contracts v5.x — Initializable, ReentrancyGuard,
  AccessControl, ERC4626 default-virtual-shares mitigation
- Off-chain Ethereum hashing — Keccak-256 (original) vs NIST FIPS-202
  SHA3-256 divergence; use ethers / viem / web3 Keccak helpers and a
  parity test against on-chain `keccak256`
- Tooling: Trail of Bits Slither + Echidna; ConsenSys Mythril;
  Foundry / Forge; a16z Halmos; Certora Prover
- Real-exploit corpus: rekt.news, DeFiHackLabs, immunefi.com/exploits
- Inspiration: `msitarzewski/agency-agents` specialized/blockchain-
  security-auditor @ `783f6a72bfd7f3135700ac273c619d92821b419a` (MIT)
- Inspiration: off-chain Keccak-256 vs NIST SHA3-256 hashing-parity

## Changelog

- **PLAN-153 Wave G (SP-031, 2026-07-09):** wrong-primitive keccak/sha3 doctrine + runnable parity proof folded in (clean-room ADAPT; provenance in frontmatter/NOTICE).
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=0f5a91f905447e711b371f13909e51864eb2e8414df2ccc6d226aff4fffe7c7f
