#!/usr/bin/env python3
"""PreToolUse hook: gate canonical-path edits on Owner-signed sentinel.

Sprint 5 Phase 7 (ADR-010). Blocks Edit / Write / MultiEdit calls
against canonical governance paths unless an Owner-signed sentinel
file (`approved.md`) exists in the same Architect bundle directory
with a valid `Approved-By:` line and the target path declared in its
`Scope:` block.

## Wire-up

Registered in `.claude/settings.json` PreToolUse Edit/Write/MultiEdit:

    {
      "matcher": "Edit|Write|MultiEdit",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_canonical_edit.py",
          "timeout": 5,
          "statusMessage": "Checking canonical-path sentinel..."
        }
      ]
    }

## Decision logic

1. Parse `tool_input.file_path` from the payload.
2. If path is NOT in the canonical guard list → allow silently.
3. If path IS canonical:
   a. Look for any sibling `.claude/plans/PLAN-NNN/architect/round-N/approved.md`
      that lists this path under its `Scope:` block.
   b. If sentinel exists + `Approved-By:` line valid → allow.
   c. Otherwise → block with a clear reason.

## Fail-open contract

Any internal exception → allow. The hook never blocks the user on its
own bug. (The canonical edit is allowed; the canonical path is still
governed by CODEOWNERS / branch protection on the merge side.)
"""

from __future__ import annotations

import fnmatch
import json
import os
import hashlib  # PLAN-094 Wave C — sha256 in cache key
import re
import subprocess  # PLAN162_FIX_S2 — session-anchor proof via git
import sys
import time  # PLAN162_FIX_1 — per-invocation wall-clock budget
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple  # PLAN-094 Wave C

# Make the local _lib importable
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# PLAN-045 Wave 1 P0-01 — GPG sentinel verification.
try:
    from _lib import gpg_verify as _gpg_verify
except Exception:  # pragma: no cover
    _gpg_verify = None  # type: ignore[assignment]

# PLAN-089 Wave C.4 — sentinel signer registry (ADR-121).
# Behavior-preserving migration: if YAML registry resolves the signer
# via _lib.sentinel_signers, that result wins; otherwise the legacy
# `.claude/sentinel-signers.txt` allowlist is consulted (existing
# PLAN-045 path). Both wires fail-CLOSED on import failure.
try:
    from _lib import sentinel_signers as _sentinel_signers  # type: ignore[import]
except Exception:  # pragma: no cover
    _sentinel_signers = None  # type: ignore[assignment]

_SENTINEL_SIGNERS_REGISTRY_YAML = (
    Path(__file__).resolve().parent.parent.parent
    / ".claude" / "security" / "sentinel-signers-registry.yaml"
)

# PLAN-089 Wave C.4 — R2 Codex iter-1 Q5+Q7 fold: _BOOTSTRAP_REGISTRY_SHA256
# pin per ADR-121 §5. Pre-GENESIS this is None and registry parse failure
# falls back to legacy `.txt` (avoids Wave C.6 transition brick).
# Post-GENESIS the Wave C.6 ceremony rotates this constant via KERNEL
# HARD-DENY ceremony (CEO_KERNEL_OVERRIDE=PLAN-089-WAVE-C-SENTINEL-
# ROTATION-GENESIS) to the SHA256 of the finalized YAML. When set:
#   - Registry hash mismatch → fail-CLOSED (tamper-detect)
#   - Registry parse failure → fail-CLOSED (post-GENESIS no-fallback)
_BOOTSTRAP_REGISTRY_SHA256: Optional[str] = None  # placeholder pre-GENESIS

# PLAN-045 Wave 1 P0-01 — signer allowlist for sentinel .asc signatures.
_SENTINEL_SIGNERS_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / ".claude" / "sentinel-signers.txt"
)


# Canonical paths (relative to repo root) — ADR-010 v1.1 (Sprint 9
# amendment adds conftest.py + new-hook + lessons-related scripts).
# fnmatch.fnmatch is used; `*` is treated as a single segment matcher
# below by walking the path components manually. `**` matches zero or
# more segments (used for the Sprint 9 conftest entry).
#
# PLAN-019 Phase 2 Wave 2A (P1-SEC-A) expansion: full governance surface.
# Every path listed here is sentinel-gated (editable via Owner-signed
# sentinel). The arbitration-kernel subset (hook source files enforcing
# THIS guard, _lib/policy.py, _lib/redact.py, _lib/audit_emit.py, and
# .claude/policies/*.yaml) is ALSO covered by the stricter HARD-DENY
# hook `check_arbitration_kernel.py` — that hook has no sentinel escape
# and requires `CEO_KERNEL_OVERRIDE` with an audit-logged reason. The
# overlap is intentional defense-in-depth: if the arbitration hook is
# disabled by misconfiguration, this sentinel guard still blocks the
# edits (and vice versa).
# Canonical governance surfaces: `.claude/skills/**/SKILL.md` and
# `.claude/commands/**` stay sentinel-guarded. These tokens are also the
# command/skill-hook map generator's source-scanning contract.
from _lib.canonical_edit import guards as _canonical_guard_definitions
for _guard_name in _canonical_guard_definitions.__all__:
    globals()[_guard_name] = getattr(_canonical_guard_definitions, _guard_name)
del _guard_name, _canonical_guard_definitions

# Set ONCE per invocation by ``main()`` from the parsed event, and reset
# in its ``finally`` so a value can never leak into a later in-process
# caller. Helpers deep in the call graph (``_emit_unlock_audit`` has no
# event in scope) read it through ``_blocked_tool_field()``.
_CURRENT_TOOL_NAME = ""


# Blocked-tool validation and skill-content checks are bound below.


# PLAN-025 F-perf-004 fast-path — precomputed set of top-level path
# segments that every _CANONICAL_GUARDS entry starts with. Any path NOT
# starting with one of these prefixes is non-canonical in O(1) without
# running fnmatch 30+ times. Preserves semantics — every guard pattern
# starts with one of these prefixes by construction.
_CANONICAL_PREFIXES = frozenset({
    ".claude", ".github", "scripts", "SPEC", "PROTOCOL.md",
    # PLAN-155 Wave 3b (SENT-CX-E) — first-segment prefixes for the Codex
    # kill-switch surface. Without these three the fast-path bail-out in
    # `_is_canonical` returns False BEFORE the new `_CANONICAL_GUARDS`
    # entries are ever consulted (the guard would be dead — the S254
    # dead-gate class). Every kill-switch guard pattern starts with one of
    # these by construction (`.codex/*`, `requirements.toml`, `AGENTS.md`).
    ".codex", "requirements.toml", "AGENTS.md",
    # PLAN-156 Wave 3 (SENT-GK-E) — the same dead-guard class as `.codex`
    # above, twice over (pair-rail R4 + R14). `_is_canonical()` bails out
    # BEFORE any glob matching unless the path's first segment is in this
    # set, so adding the `.grok/**` and `templates/settings/*` patterns to
    # _CANONICAL_GUARDS without adding their first segments HERE would
    # leave both guards INERT — unsentineled edits sailing straight through
    # a list that LOOKS like it protects them. The S254 dead-gate class,
    # and the reason this pair of edits can never be split across waves.
    ".grok", "templates",
})


# PLAN160_FIX_A — upper bound on candidates classified per multi-candidate
# event. Beyond this the event is fail-CLOSED (blocked) rather than risk an
# unexamined canonical candidate riding through past a truncated scan. Real
# apply_patch / MCP bulk events carry a handful of paths; this is a DoS-shape
# backstop, not a normal-path limit.
_PLAN160_MAX_CANDIDATES = 512


# PLAN162_FIX_CASEFOLD (PLAN-162 consensus S1, P0 — BOTH rails).
#
# ``_match_segments`` matches with ``fnmatch.fnmatchcase`` (exact case)
# and ``_CANONICAL_PREFIXES`` is an exact-case frozenset. On a
# case-INSENSITIVE filesystem — APFS, the default on this repo's
# platform — ``.claude/settings.JSON`` IS ``.claude/settings.json``, and
# writing through the variant OVERWRITES the guarded file. Measured on
# HEAD: `.claude/settings.JSON`, `.claude/hooks/_lib/audit_emit.PY` and
# `.CLAUDE/settings.json` all classified NON-canonical AND non-kernel,
# reaching files the threat model assumes unreachable.
#
# Both halves must fold or the guard only LOOKS fixed: the prefix
# fast-path bails out in O(1) BEFORE any glob runs, so folding the glob
# matcher alone would leave `.CLAUDE/...` inert — the dead-gate class
# this file was already bitten by twice (the `.codex` and `.grok` prefix
# omissions).
#
# ``str.lower`` — not ``str.casefold`` — deliberately: casefold expands
# 'ß'→'ss', changing segment LENGTH and hence what a glob matches. The
# exploited class is ASCII case variance, which ``lower()`` covers
# exactly; identical inputs always fold identically, so the
# normalization can only ADD matches (over-classify = the safe
# direction), never remove one.
#
# Precomputed at import: the hot path pays one ``str.lower()`` per
# classification instead of one per (segment x pattern).
_CANONICAL_GUARDS_FOLDED = [pat.lower() for pat in _CANONICAL_GUARDS]
_CANONICAL_PREFIXES_FOLDED = frozenset(
    prefix.lower() for prefix in _CANONICAL_PREFIXES
)


# ---------------------------------------------------------------------------
# PLAN162_FIX_2: depth-independent discovery now lives in canonical_edit.paths.
# PLAN-094 Wave C — sentinel verification session cache (R-041)
# ---------------------------------------------------------------------------
# Module-scope ONLY (NEVER file-backed; PLAN-094 §3 Wave C C.1).
# Process death = cache loss (eliminates R5 stale-cache-survives-crash).
# Composite key — Codex iter-1 P0 fold: target_rel included so cache value
# (grant decision dependent on target_rel) is correct on hit; sha256_full
# transitively covers signer changes via .asc bytes (signer rotation
# window risk acknowledged + accepted trade-off per design draft §8).

_SENTINEL_CACHE_FORMAT_VERSION = 2  # bumped at iter-1 P0 fix (target_rel added)
_SENTINEL_VERIFY_CACHE: Dict[
    Tuple[str, int, int, int, str, str, int], bool
] = {}
_SENTINEL_CACHE_HITS = 0
_SENTINEL_CACHE_MISSES = 0

# PLAN162_FIX_1 (PLAN-162 findings #1 + #10, consensus C1 + C2 + C3 + S8).
#
# ## The defect (#1, re-diagnosed in debate: AMPLIFICATION, not latency)
#
# The cache above folds ``target_rel`` into its key, but
# ``_gpg_verify.verify_detached`` never RECEIVES a target — signature
# validity is target-INDEPENDENT. So the same sentinel was
# cryptographically re-verified once per distinct target: a subprocess
# count of O(candidates x sentinels). Measured in debate, gpg-agent
# healthy: 1 GPG ~ 17 ms, but a 20-path ceremony pack cost **4.16 s of a
# 5 s hook budget** with 0 cache hits and 320 misses (40 paths: 4.23 s).
#
# ## The fix — two caches, not one
#
#   * ``_SIG_VERIFY_CACHE`` — the SIGNATURE rail, keyed on the signing
#     MATERIAL and NOT on the target. 320 subprocesses collapse to 16.
#   * ``_GRANT_CACHE`` — the SCOPE rail, target-keyed and cheap. This is
#     the SAME object as ``_SENTINEL_VERIFY_CACHE`` (an alias, not a
#     copy): the PLAN-094 key shape and counters are pinned by
#     ``test_sentinel_session_cache.py`` and stay byte-compatible.
#
# ## Why the signature rail must run FIRST (this is finding #10)
#
# #10 observed that the grant key hashes only ``approved.md``'s bytes, so
# mutating the ``.asc`` / signer allowlist / ADR-121 registry left a
# stale ``True`` riding the cache in-process. Rather than smuggle a
# digest of three more files into a key shape other tests pin, the
# signature rail is consulted BEFORE the grant fast-path and keys on
# those bytes itself. A revocation in any of the three now invalidates
# the decision even when ``approved.md`` is byte-identical — closing the
# "signer rotation window" that PLAN-094 §8 had consciously accepted.
_SIG_CACHE_FORMAT_VERSION = 1
_SIG_VERIFY_CACHE: Dict[tuple, bool] = {}
_GRANT_CACHE = _SENTINEL_VERIFY_CACHE  # alias — same dict object

# ---------------------------------------------------------------------------
# PLAN162_FIX_1 — per-invocation wall-clock budget (consensus C2 + C3 + S8)
# ---------------------------------------------------------------------------
# C2 REMOVED the sentinel cap from the design: ``_find_sentinels`` returns
# SORTED, so the highest-numbered pack — the ceremony the Owner just
# signed — is exactly the sentinel a cap would drop. Self-DoS with the
# signature in hand, and it does not even fix a hung gpg (one hang costs
# the full timeout at cap=1). What replaces it is a global wall-clock
# deadline per INVOCATION, checked at the top of the sentinel loops.
#
# C3: the budget is a MODULE CONSTANT, never read from settings.json at
# runtime — the budget lives in the file this hook guards (circular), and
# parsing JSON on the hot path would worsen the very path being
# optimized. Drift against the registered timeout is a STATIC test
# instead (the shape verify-counts.sh already uses):
# ``test_1_repro_wall_deadline_constant_has_slack_under_registration``.
# 4.0 s under the registered 5 s leaves ~1 s to emit the decision.
#
# S8: the clock is an injectable module-level seam (``_now``). Without
# it the red-first test's only options were a multi-second real sleep
# (a documented flake class in this repo) or no deterministic coverage
# of the slow path at all. This is a requirement OF the fix.
#
# ORDER IS NOT NEGOTIABLE (C3): the deadline and the cache partition ship
# in the SAME patch under the SAME marker. A deadline without the
# partition fires on the 4.16 s measured above and denies the ceremony
# itself.
_HOOK_WALL_BUDGET_S = 4.0
_now = time.monotonic
_WALL_DEADLINE_AT = None  # type: Optional[float]
_WALL_BUDGET_EXHAUSTED = False


def _start_wall_budget() -> None:
    """Arm the per-invocation wall-clock deadline (called once by main)."""
    global _WALL_DEADLINE_AT, _WALL_BUDGET_EXHAUSTED
    _WALL_BUDGET_EXHAUSTED = False
    _WALL_DEADLINE_AT = _now() + _HOOK_WALL_BUDGET_S


def _reset_wall_budget() -> None:
    """Disarm the deadline.

    Called from ``main()``'s ``finally`` so a module-scope deadline can
    never leak into a LATER in-process caller (the test suite drives
    ``decide()`` directly in the same process; a stale expired deadline
    would fail those closed for no reason).
    """
    global _WALL_DEADLINE_AT, _WALL_BUDGET_EXHAUSTED
    _WALL_DEADLINE_AT = None
    _WALL_BUDGET_EXHAUSTED = False


def _mark_wall_budget_exhausted() -> None:
    """Latch the budget as spent (see ``_gpg_verify_timeout``).

    Set when a signature verification is REFUSED for want of budget. The
    clock has not necessarily elapsed yet, but the invocation can no
    longer reach a verdict, so every subsequent poll must report expiry —
    otherwise the loop runs to its end and the operator is handed the
    generic "declare this path in Scope" block, which misdiagnoses a
    budget fault as a missing sentinel and omits the recovery route.
    """
    global _WALL_BUDGET_EXHAUSTED
    _WALL_BUDGET_EXHAUSTED = True


def _wall_budget_expired() -> bool:
    """True once the armed invocation budget has elapsed (or is spent).

    Disarmed (``None``) => never expired, so direct ``decide()`` callers
    outside a hook invocation are unaffected.
    """
    if _WALL_DEADLINE_AT is None:
        return False
    if _WALL_BUDGET_EXHAUSTED:
        return True
    return _now() > _WALL_DEADLINE_AT


# ---------------------------------------------------------------------------
# PLAN162_FIX_1 — the gpg subprocess is bounded by the REMAINING budget
# ---------------------------------------------------------------------------
# Codex pair-rail P1 (S292) against this patch, staged:
#
#   "Bound GPG verification by the remaining hook budget. When gpg or
#   gpg-agent stalls, this call can block for 15 seconds although the
#   hook is registered for 5 seconds and the new internal deadline is 4
#   seconds. Because the deadline is checked only between sentinel
#   iterations, the harness can kill the process before it emits the
#   intended fail-closed decision, recreating the silent fail-open that
#   ADR-164-AMEND-1 §3 explicitly says the patch prevents."
#
# The deadline above is POLLED: read at the top of the sentinel loops, it
# can only bound work that happens BETWEEN iterations. One
# ``verify_detached`` at the library default (``timeout=15.0``,
# ``_lib/gpg_verify.py``) is 3x the entire registration — the poll never
# gets its turn, the harness kills a hook that has emitted NOTHING, and
# "no decision" is indistinguishable from allow. ADR-164-AMEND-1 §3 D2
# already states the intended behaviour ("per-verify subprocess timeout
# bounded by remaining budget"); this is the code that makes the text
# true.
#
# Two constants, both about EMITTING rather than about gpg:
#
#   * ``_GPG_EMIT_MARGIN_S`` — wall time reserved AFTER gpg returns so the
#     rest of the decision plus the JSON emit still fit inside the
#     internal deadline. A verification bounded to land exactly ON the
#     deadline would merely have moved the kill.
#   * ``_GPG_MIN_SPAWN_S`` — the floor below which spawning is pointless:
#     a fork we cannot afford to wait out cannot tell "bad signature"
#     from "slow agent", so it must not start at all.
#
# Their sum must stay well under ``_HOOK_WALL_BUDGET_S``, or the FIRST
# sentinel of a fresh invocation could never be verified — self-DoS with
# the Owner's signature in hand, the C3 class. Pinned by
# ``test_control_gpg_bound_constants_leave_room_for_a_first_verify``.
_GPG_VERIFY_TIMEOUT_CAP_S = 15.0  # the historical _lib.gpg_verify default
_GPG_EMIT_MARGIN_S = 0.5
_GPG_MIN_SPAWN_S = 0.5


def _gpg_verify_timeout() -> Optional[float]:
    """Subprocess timeout for ONE detached-signature verification.

    ``None`` means DO NOT SPAWN — what is left of the invocation budget
    cannot cover both a meaningful verification and the emit that has to
    follow it. Callers translate that into the fail-CLOSED wall-deadline
    block, never into an allow and never into a silent zero-emit.

    With the budget disarmed (direct ``decide()`` callers, importers such
    as ``check_pair_rail``) the historical cap is returned unchanged:
    this narrows the hook-invocation path only.
    """
    if _WALL_DEADLINE_AT is None:
        return _GPG_VERIFY_TIMEOUT_CAP_S
    usable = (_WALL_DEADLINE_AT - _now()) - _GPG_EMIT_MARGIN_S
    if usable < _GPG_MIN_SPAWN_S:
        return None
    return min(_GPG_VERIFY_TIMEOUT_CAP_S, usable)


_WALL_DEADLINE_BLOCK_REASON = (
    "CANONICAL-EDIT-BLOCKED: canonical_edit_hook_fault — the hook's "
    "per-invocation wall-clock budget ({0}s) elapsed before authorization "
    "for this canonical path could be established. A security matcher that "
    "cannot finish deciding does NOT allow (PLAN-045 F-01-07 posture; "
    "PLAN-162 consensus C2). Recovery: re-issue the edit, or use the "
    "documented CEO_SENTINEL_UNLOCK / CEO_KERNEL_OVERRIDE ceremony."
).format(_HOOK_WALL_BUDGET_S)


# ---------------------------------------------------------------------------
# PLAN162_FIX_S2 — the sentinel SET is a trust anchor (consensus S2)
# ---------------------------------------------------------------------------
# ``.claude/plans/PLAN-*/**/approved.md`` is guarded by NEITHER rail, and
# under an Owner ``CEO_SENTINEL_UNLOCK`` window the GPG rail is skipped
# entirely — so an ``approved.md`` the AGENT writes mid-window GRANTS.
# That is a bypass of AUTHORIZATION, not merely a DoS on the gate's cost.
#
# The first mitigation drafted for this ("tracked in git OR pre-existing")
# was DEFEATED by the pair-rail in one command: inside the window the
# agent writes the file and runs an ordinary ``git add``; ``ls-files
# --error-unmatch`` then calls it TRACKED, and a HEAD-based check would
# accept an agent-authored COMMIT just the same. **Git state is a
# statement about the index, not about who authorized the file.**
#
# The trust anchor is therefore SESSION START: under ``env_override``,
# accept only a sentinel that already existed in the tree at the commit
# the Owner names in ``CEO_SESSION_ANCHOR_SHA``. The anchor is an ENV
# var, which is exactly the same trust primitive the unlock itself rests
# on (a sub-agent cannot set env in the parent shell) — so requiring it
# adds no new assumption. No anchor => no proof => no grant.
#
# ## PLAN162_FIX_S2R2 — what the codex round-2 pair-rail corrected
#
# The first draft of this rail proved only that the sentinel PATH existed
# at the anchor, then parsed the CURRENT bytes. Codex defeated it in one
# move (P1-1): inside a legitimate window, take any pre-existing
# unguarded ``approved.md``, keep its ``Approved-By:`` line, ADD a target
# to ``Scope:`` — path-existence still holds, GPG is skipped, and the
# hook authorizes off attacker-modified bytes. **A trust decision must be
# made on the ANCHORED bytes, not on bytes that merely live at an
# anchored path.** ``git cat-file blob`` now supplies the text that is
# parsed; what is on disk is never consulted on this path.
#
# Two more round-2 corrections ride the same fold:
#
#   * P1-2 — the git subprocess is bounded by the REMAINING wall budget
#     (``_git_anchor_timeout``), exactly as the gpg spawn already is. A
#     5 s probe inside a 4 s budget lets the harness kill the process
#     before it emits the intended BLOCK, which is the zero-emit
#     fail-open this whole patch exists to remove.
#   * P1-3 — a fail-closed gate with no recovery route is a brick. The
#     anchor alone bricks the ONE use ADR-119 names for the unlock
#     ("ceremony authoring where the .asc is being signed in parallel"):
#     a freshly authored sentinel predates nothing. So the Owner may
#     instead PIN the sentinel's content hash
#     (``CEO_SENTINEL_UNLOCK_SHA256``, space/comma-separated for several).
#     It rests on the same trust primitive as the unlock itself — env a
#     sub-agent cannot set in the parent shell — and it is strictly
#     stronger than the anchor: it binds CONTENT, not a path. Reading the
#     value gains an attacker nothing (sha256 preimage), and it works in
#     a non-git tree, where the anchor cannot.
#
# ## RESIDUAL — read before ratifying
#
# The ANCHOR rail arms only when the project is a git work tree (``.git``
# present); otherwise no anchor proof exists and the legacy accept
# stands. Consequence: ``rm -rf .git`` disarms the anchor half. Named
# here rather than buried. The digest-pin half is unaffected by it — it
# is the git-free proof form the first draft said "is a separate
# decision", and this is that decision.
#
# DECIDED, not overlooked: in a NON-git tree a digest pin does not make
# the unpinned sentinels stricter — a pin-miss falls through to the
# residual accept there, exactly as it falls through to the anchor rail
# in a git tree. Making the pin authoritative in a non-git tree would
# mean "pin one file, reject every other sentinel in the pack" in the
# one tree shape that has no second proof form: the C3 self-DoS class,
# traded for a tightening that only bites where the legacy accept
# already applies.
#
# Landing this CHANGES a documented operator contract (ADR-119,
# SPEC/v1/sentinel-format.schema.md, docs/FAQ.md, the READMEs): an
# unlock window now needs a THIRD value. Those surfaces are updated in
# this same patch, and ``_unlock_trust_hint`` teaches both forms in the
# block reason itself — a required value that only exists in the diff is
# the lockout P1-3 named. Owner ratification: ADR-164-AMEND-1.
_SESSION_ANCHOR_ENV = "CEO_SESSION_ANCHOR_SHA"
_UNLOCK_DIGEST_ENV = "CEO_SENTINEL_UNLOCK_SHA256"
_ANCHOR_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_GIT_ANCHOR_TIMEOUT_CAP_S = 5.0
# (repo_root, anchor, rel) -> anchored text, or None for "proven absent".
# A key is absent from the map when no VERDICT was reached (budget
# refusal, git fault) — errors are never memoized, same contract as
# ``_SIG_VERIFY_CACHE``.
_ANCHOR_BLOB_CACHE = {}  # type: Dict[tuple, Optional[str]]

# Why the unlock rail refused, for the block reason. First refusal wins;
# reset per ``decide()`` call.
_UNLOCK_TRUST_DIAG = None  # type: Optional[str]


# Sentinel decision and audit functions are bound below.


# ---------------------------------------------------------------------------
# PLAN-163 T3.1 — session-roots write-guard (DirectoryAdded consumer)
# ---------------------------------------------------------------------------
# CC 2.1.220 ships `DirectoryAdded` as a NOTIFICATION-ONLY, POST-facto hook
# event: `decision: block` is structurally ignored, and by the time the
# event dispatches the permission/sandbox surface ALREADY includes the new
# directory (full reads+writes for the rest of the session). The observer
# half (`check_directory_added.py`, PLAN-163 T3.1 thread B1) records every
# added root into `.claude/state/session-roots.json`; THIS extension is the
# enforcement half: on the existing Edit|Write|MultiEdit PreToolUse guard,
# a write whose realpath resolves INSIDE a session-registered root that is
# not explicitly allowlisted is DENIED. Deliberately an EXTENSION of
# check_canonical_edit.py (the write-path guard already wired for this
# matcher family) — NOT a new hook file (ADR-183; hook-count contract
# T6.4: only the B1 observer + the Notification telemetry hook are new
# files).
#
# Registry schema (written by check_directory_added.py):
#     {"schema": 1,
#      "sessions": {<session_id>: {"roots": [
#          {"directory": <abs>, "source": <str>, "ts": <str>,
#           "unparseable": true?}, ...]}}}
#
# Failure contract (CLAUDE.md §4):
#   - Registry ABSENT → allow silently (the registry only exists if the
#     observer ran; absence is the normal no-DirectoryAdded state, not a
#     fault).
#   - Registry PRESENT but unparseable (corrupt JSON / unknown schema /
#     malformed `sessions`) → INPUT-parse failure of a security matcher,
#     NOT an ABSENT-file INFRA condition → fail-CLOSED for writes that
#     cannot be proven repo-internal (FXγ / C3, doctrine correction). The
#     deny is SCOPED to external writes — the new surface an added root
#     could have opened — while repo-internal writes stay governed by the
#     canonical stack above (unaffected). A stderr breadcrumb AND a
#     best-effort tamper audit event fire UNCONDITIONALLY (reason_code=
#     session_roots_registry_unreadable, on the already-registered
#     `veto_triggered` action) so corrupting/truncating the registry is both
#     BLOCKED (for the external write it opened) and HMAC-observable (H5).
#   - Root entry `unparseable: true` (or structurally malformed — a root
#     was recorded but its boundary is unknowable, INCLUDING a `directory`
#     that is not an ABSOLUTE path: a relative value would resolve against
#     the process CWD and silently mis-scope the boundary, M2) →
#     fail-CLOSED: every non-repo-internal write in that session is denied.
#   - Event carries NO session_id (absent/empty) while the registry holds
#     registered sessions → fail-CLOSED (M1): the write cannot be bound to
#     a session, yet roots exist, so the boundary is unknowable; external
#     writes are denied so that clearing CLAUDE_SESSION_ID cannot
#     neutralize the guard (CLAUDE.md §4).
#   - Tool-call path that cannot be canonicalized while the guard is
#     active → DENY (security-matcher input, fail-CLOSED).
#   - Candidates whose realpath resolves INSIDE the repo root are exempt:
#     they are governed by the canonical-guard stack above; this guard
#     scopes exclusively to the NEW write surface DirectoryAdded opened.
#     The realpath comparison makes the exemption symlink-safe (a repo
#     path symlinked out to a registered root still resolves external →
#     still gated).
#
# KNOWN RESIDUAL (documented, not closable here):
#   1. Roots granted via LAUNCH-time `--add-dir` never fire DirectoryAdded
#      (CC 2.1.220 registry blind spot), so they never reach the registry
#      and this guard cannot see them. Partial mitigation is the
#      SessionStart roots snapshot (T3.1 B1).
#   2. REGISTRY-REWRITE BYPASS (H5), NARROWED by FXγ. The registry
#      (.claude/state/session-roots.json) is repo-INTERNAL, so writes to it
#      are EXEMPT from this guard (repo-internal candidates are governed by
#      the canonical stack above, not here) AND it is agent-writable. FXγ
#      closes the CORRUPTION half of this bypass: corrupting/truncating the
#      registry no longer silently allows external writes — a
#      present-but-unparseable registry now fails CLOSED for them (above).
#      The residual that REMAINS is the EMPTY-but-VALID overwrite: writing
#      `{"schema":1,"sessions":{}}` parses cleanly and legitimately means
#      "no registered sessions" → allow, so an agent can still neutralize
#      the guard that way. (The corruption signal is deliberately reserved
#      for unparseable/unknown-schema; an empty valid registry is not
#      corruption.) This guard remains a BEST-EFFORT, confused/
#      non-adversarial-deputy control, NOT a hard security boundary: it
#      stops the accidental / notification-blind write that DirectoryAdded
#      opens (S283); it does not stop an adversary who rewrites the registry
#      to an empty-valid state. Even for that residual, mitigation is
#      OBSERVABILITY layered with prevention: the corrupt-registry path
#      emits a tamper audit event AND denies the external write, so a
#      corruption-based rewrite is both blocked and visible in the HMAC
#      audit chain. The read-path residual — read access under an added root
#      remains wholly undiscovered by this write-path guard — is unchanged.
#      Never sold as prevention. See ADR-183 §Residuals.

_SESSION_ROOTS_SCHEMA = 1
_SESSION_ROOTS_ALLOW_ENV = "CEO_SESSION_ROOTS_ALLOW"


_SESSION_ROOTS_UNCANON_EMPTY = (
    "SESSION-ROOTS-WRITE-BLOCKED: session_root_path_uncanonicalizable "
    "— a write-target path in this event is empty, not a string, or "
    "carries an embedded NUL while session-registered workspace "
    "roots are active; a path the guard cannot canonicalize cannot "
    "be proven outside the registered roots. Security-matcher "
    "input → fail-closed (CLAUDE.md §4; PLAN-163 T3.1 / ADR-183)."
)


# Adapter/CLI/hook entry implementations are bound below.


# Bind extracted implementations to this facade's globals. Existing callers can
# still patch dependencies here, and each import owns its caches and counters.
# PLAN162_FIX_7: local file-URI normalization lives in canonical_edit.paths.
_COMPONENT_IMPORT_ERROR = None
_COMPONENT_IMPORT_IS_INTEGRITY_FAILURE = False
try:
    from _lib.canonical_edit import bind as _bind_canonical_edit
    _bind_canonical_edit(globals())
    del _bind_canonical_edit
except Exception as _component_exc:  # partial install / infrastructure failure
    _COMPONENT_IMPORT_ERROR = type(_component_exc).__name__
    _COMPONENT_IMPORT_IS_INTEGRITY_FAILURE = isinstance(_component_exc, ImportError)

    def main() -> int:
        print("check_canonical_edit: component import unavailable (" +
              str(_COMPONENT_IMPORT_ERROR) + ")", file=sys.stderr)
        if _COMPONENT_IMPORT_IS_INTEGRITY_FAILURE:
            print(_emit_block("CANONICAL-EDIT-BLOCKED: canonical_edit integrity "
                              "failure: component import unavailable."))
            return 0
        print(_emit_allow())
        return 0


if __name__ == "__main__":
    # PLAN-156-FOLLOWUP F5 — oracle CLI mode is gated on an EXPLICIT argv
    # sentinel so hook invocations (argv always empty: `_python-hook.sh`
    # execs `$FOUND_PY $HOOK_SCRIPT "$@"` with no extra args from
    # settings.json) can never reach it. Any other argv shape falls
    # through to the unchanged hook entry.
    if len(sys.argv) >= 2 and sys.argv[1] == "--is-canonical":
        sys.exit(_cli_is_canonical(sys.argv[2:]))
    sys.exit(main())
