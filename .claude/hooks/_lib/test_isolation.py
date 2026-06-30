"""PLAN-119 WS-A — durable suite-wide audit-dir isolation REDIRECT.

## Why this exists

This repo **dogfoods an audit-emitting framework in its own repo against the
real ``~/.claude``**. ``TestEnvContext`` (``_lib/testing.py``) isolates the
audit dir *per test*, but that isolation is **opt-in**: any process that runs a
hook / emits an audit event WITHOUT entering ``TestEnvContext`` writes to the
LIVE ``~/.claude/projects/ceo-orchestration/audit-log.jsonl``. Those events
carry HMACs computed under test conditions (or a different chain head), so
``audit-verify-chain`` later reads ``tamper`` and ``audit-log.errors`` floods.
S181 forensics: ~1690 of 1738 live-log lines were test/probe pollution.

## What this does (Axis 1 — destination redirect)

A **session-scoped autouse** fixture redirects the FULL audit/HMAC env carrier
set (Codex R1 P0-3 — NOT just the four log vars) to a per-session tmpdir
*before any test body runs*. A redirected process **physically cannot** append
to the live log. This closes ~100 % of the pytest volume (the bulk of S181
pollution) and carries **no suppression surface**: redirecting your own test's
destination cannot silence someone else's real session (that was WS-B, dropped).

A **function-scoped autouse** fixture additionally asserts (defense-in-depth)
that the *production* audit-dir resolver (``audit_emit._audit_dir`` — imported,
never re-implemented, per AC-A5) does not resolve to the snapshotted live dir,
catching a test that mutates env back to the live dir mid-run.

## Registration

All three pytest conftests import the two fixtures by name so every collected
test is covered regardless of which subtree pytest is invoked against:

  - ``<repo>/conftest.py``                    (tree-wide — all ``testpaths``)
  - ``.claude/hooks/tests/conftest.py``
  - ``.claude/scripts/tests/conftest.py``     (net-new in PLAN-119 WS-A)

The redirect is **idempotent** via a module-global guard: the first session
fixture to run performs the real redirect and records the restore snapshot;
later registrations (a sibling conftest's same-named fixture) detect the active
redirect and become a no-op, so the three registrations never stack tmpdirs nor
double-restore. Under ``pytest-xdist`` each worker is a separate process with
its own module global → its own session tmpdir (plan R4).

## Reuse by WS-C

``audit_carrier_overrides()`` is the SINGLE source of the carrier-set
enumeration; ``TestEnvContext.subprocess_env`` (WS-C) imports it so a spawned
child inherits the exact same isolated destination — no second hand-maintained
list to drift.

## Escape hatch

``@pytest.mark.allow_live_audit_dir`` (registered in ``pytest.ini``) marks the
rare test that genuinely exercises the real resolver; the function-scope assert
skips for it. Zero uses at ship; a ``validate-governance.sh`` grep gate keeps it
at zero and CODEOWNERS requires security-engineer review to add one.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# --- Carrier-set enumeration (Codex R1 P0-3) -----------------------------------
# Every env var that can steer WHERE an emit / HMAC sidecar / spool / lock /
# fallback resolves. Path-valued carriers are pointed under the session tmpdir;
# the rotate-bytes carrier is CLEARED so a stale-inherited value cannot influence
# rotation. The enumeration lives HERE, exactly once. WS-C imports it.

# Directory-level anchors we SET to the isolated tree. ``CEO_AUDIT_LOG_DIR`` is
# the PRIMARY resolver for every audit path — ``audit_emit._audit_dir`` /
# ``audit_hmac._audit_dir_from_env`` / ``spool_writer._state_dir`` all honor it
# FIRST. ``HOME`` is the *fallback* the resolvers reach when ``CEO_AUDIT_LOG_DIR``
# is absent. We redirect BOTH (plus ``CEO_PROJECT_STATE_DIR``) and CLEAR the
# per-file overrides, so the entire audit/HMAC/spool surface resolves to the
# isolated tree EVEN IF a test pops ``CEO_AUDIT_LOG_DIR`` mid-run (the fallback
# then hits the redirected HOME's ``.claude/`` — still non-live). This is the
# airtight structural guarantee (Codex pair-rail P0): a kernel resolver guard
# would be the alternative, but ``audit_emit``/``audit_hmac`` are kernel-HARD-DENY.
#
# Redirecting HOME does break subprocesses that resolve TOOLING via the real
# home (PyYAML in the macOS user-site). ``_activate_redirect`` therefore PRESERVES
# ``PYTHONUSERBASE`` (real user-site) AFTER the HOME redirect. ``GNUPGHOME`` is
# the OPPOSITE — it is CLEARED (not preserved), so gpg resolves under the
# redirected HOME's empty ``.gnupg`` and the suite cannot reach the real signing
# keyring (a real-keyring leak let sentinel ``.asc`` verification SUCCEED in
# tests that require it to fail; see TOOLING_CLEAR_VARS). Net: isolate the audit
# dir + the GPG keyring, without breaking user-site package resolution.
#
# ``CLAUDE_PROJECT_DIR`` is DELIBERATELY NOT redirected — it steers where hooks
# find the PROJECT's ``.claude/`` files (policies, team.md, cookbook patterns),
# is not an audit-location carrier, and redirecting it broke "the real repo is
# configured" tests (test_flip_closures, test_cookbook_advisor_hook) for zero
# isolation gain.
AUDIT_DIR_CARRIERS = (
    "HOME",
    "CEO_AUDIT_LOG_DIR",
    "CEO_PROJECT_STATE_DIR",
)
# Tooling env vars re-exported (to REAL values) after the HOME redirect so a
# subprocess can still resolve user-site packages (PyYAML etc.).
TOOLING_PRESERVE_VARS = ("PYTHONUSERBASE",)
# Tooling env vars CLEARED after the HOME redirect so they resolve under the
# redirected (isolated) HOME. GNUPGHOME → the redirected HOME's empty `.gnupg`,
# so the suite cannot use the real signing keyring (tests that exercise GPG set
# their own keyring_home/GNUPGHOME).
TOOLING_CLEAR_VARS = ("GNUPGHOME",)
# Carriers we explicitly CLEAR (the "or-clear" half of set-or-clear). These are
# the per-file path OVERRIDES + tunables. We do NOT set them to fixed session
# paths because ``TestEnvContext`` re-isolates per test by re-pointing only
# ``CEO_AUDIT_LOG_DIR`` (+ LOG_PATH/ERR/LOCK) and RELIES on the KEY /
# LAST_HMAC / CHAIN_LENGTH sidecars defaulting off ``CEO_AUDIT_LOG_DIR``. If the
# session redirect pinned those overrides to a session path, every
# ``TestEnvContext`` test's sidecars would stay stuck in the session dir while
# its log moved to the per-test dir → chain-length/canary mismatch. Clearing
# them (a) removes any stale parent-shell value that could point at the live
# tree and (b) lets both the session anchor and each per-test anchor drive
# resolution coherently.
AUDIT_CLEAR_CARRIERS = (
    "CEO_AUDIT_LOG_PATH",
    "CEO_AUDIT_LOG_ERR",
    "CEO_AUDIT_LOG_LOCK",
    "CEO_AUDIT_KEY_PATH",
    "CEO_AUDIT_LAST_HMAC_PATH",
    "CEO_AUDIT_CHAIN_LENGTH_PATH",
    "CEO_AUDIT_LOG_FALLBACK_PATH",
    "CEO_AUDIT_LOG_ROTATE_BYTES",
    "CEO_AUDIT_HMAC_DISABLE",
)
# The full carrier surface — used by the WS-C partial-override rejection and by
# the WS-E grep gate (every carrier must be enumerated in ONE place).
ALL_AUDIT_CARRIERS = AUDIT_DIR_CARRIERS + AUDIT_CLEAR_CARRIERS

# Sticky signals set into the (test) environment + inherited by children.
TEST_HARNESS_VAR = "CEO_TEST_HARNESS"
SYNC_MODE_VAR = "CEO_AUDIT_SYNC_MODE"
# WS-D1 live-chain comparator: the resolved LIVE audit-log path captured BEFORE
# the redirect. The drainer (which, post-redirect, cannot infer the live path
# from env) reads this to decide whether a `_origin:"test"` spool is heading for
# the live chain. Absent/unreadable ⇒ WS-D1 fails SAFE to no-quarantine.
LIVE_LOG_SNAPSHOT_VAR = "CEO_AUDIT_LIVE_LOG_PATH_SNAPSHOT"


def audit_carrier_overrides(root: Path, *, sync_mode: bool = False) -> Dict[str, str]:
    """Return the carrier env vars to SET so the FULL audit/HMAC surface resolves
    under ``root`` (an isolated tmp tree), plus the sticky test signals.

    Only the directory anchors + flags are SET; the per-file path overrides are
    CLEARED by the caller (see ``AUDIT_CLEAR_CARRIERS``) so they default off
    ``CEO_AUDIT_LOG_DIR``. Single source of truth for both the WS-A session
    redirect (``sync_mode=False``) and the WS-C subprocess-env builder
    (``sync_mode=True`` per S168 — a spawned child must write synchronously for
    the parent to read deterministically).
    """
    root = Path(root)
    home = root / "home"
    audit = home / ".claude" / "projects" / "ceo-orchestration"
    state = audit / "state"
    overrides = {
        "HOME": str(home),
        "CEO_AUDIT_LOG_DIR": str(audit),
        "CEO_PROJECT_STATE_DIR": str(state),
        TEST_HARNESS_VAR: "1",
    }
    # NOTE: CEO_AUDIT_SYNC_MODE is DELIBERATELY NOT set here. It is orthogonal to
    # *isolation* (it picks sync vs async-spool emit). TestEnvContext already
    # defaults it ON per-test (SYNC_MODE_DEFAULT=True) and the rare async tests
    # opt OUT via SYNC_MODE_DEFAULT=False — those tests rely on sync mode being
    # ABSENT. If the session redirect forced sync mode globally, the async
    # opt-out tests (e.g. the drain-cascade / async-flush probes) would run in
    # sync mode, bypass the spool, and never reach the drain path they assert on.
    # The WS-C subprocess builder sets sync mode itself (per S168) where a child
    # must write synchronously for the parent to read deterministically.
    if sync_mode:
        overrides[SYNC_MODE_VAR] = "1"
    return overrides


def _resolve_live_log_path_snapshot() -> Optional[str]:
    """Resolve the LIVE audit-log path under the CURRENT (pre-redirect) env, via
    the production resolver. Returns a realpath string, or None on any failure
    (the WS-D1 comparator fails safe to no-quarantine when absent)."""
    try:
        from _lib import audit_emit as _audit_emit
        return str(Path(_audit_emit._log_path()).resolve())
    except Exception:
        return None


# --- Idempotent redirect state -------------------------------------------------
# Holds the restore snapshot for the ONE fixture instance that performed the
# real redirect. None ⇒ no active redirect (next session fixture will activate).
_REDIRECT: Optional[Dict[str, object]] = None


def _activate_redirect() -> Optional[Dict[str, object]]:
    """Perform the real redirect once. Returns the restore-state dict for the
    activating fixture, or None if a redirect is already active (no-op)."""
    global _REDIRECT
    if _REDIRECT is not None:
        return None  # a sibling conftest's session fixture already redirected

    # 1) Snapshot the live log path BEFORE we touch env (WS-D1 comparator).
    live_log_snapshot = _resolve_live_log_path_snapshot()

    # 2) Capture the REAL PyYAML user-site BEFORE the HOME redirect so subprocess
    #    Python tooling (e.g. lint-skills' strict-YAML leg) still resolves it.
    #    Computed while HOME is still real.
    #
    #    GNUPGHOME is DELIBERATELY *not* preserved to the real keyring — it is
    #    CLEARED below so gpg resolves to the redirected HOME's (empty) `.gnupg`.
    #    Exposing the REAL keyring to the suite let sentinel `.asc` verification
    #    SUCCEED inside tests that expect it to FAIL with no key (e.g.
    #    test_mcp_canonical_guard's "PROTOCOL.md must block" — a signed PLAN-020
    #    sentinel scopes PROTOCOL.md, so a real-keyring verify wrongly ALLOWED it).
    #    Tests that genuinely exercise GPG set their own keyring_home/GNUPGHOME.
    import site as _site
    try:
        _real_userbase = _site.getuserbase()
    except Exception:
        _real_userbase = None
    tooling_overrides: Dict[str, str] = {}
    if _real_userbase:
        tooling_overrides["PYTHONUSERBASE"] = _real_userbase

    # 3) Snapshot every carrier + the sticky signals + the snapshot var + the
    #    tooling vars for exact restore at session end.
    snapshot_keys = (
        ALL_AUDIT_CARRIERS
        + (TEST_HARNESS_VAR, SYNC_MODE_VAR, LIVE_LOG_SNAPSHOT_VAR)
        + TOOLING_PRESERVE_VARS
        + TOOLING_CLEAR_VARS
    )
    env_snapshot: Dict[str, Optional[str]] = {
        k: os.environ.get(k) for k in snapshot_keys
    }

    # 4) Build the isolated tree + redirect the full carrier set.
    tmp_root = Path(tempfile.mkdtemp(prefix="ceo-suite-isolation-"))
    overrides = audit_carrier_overrides(tmp_root)
    # Materialize the dirs so writers don't fail to mkdir mid-emit.
    Path(overrides["HOME"]).mkdir(parents=True, exist_ok=True)
    Path(overrides["CEO_AUDIT_LOG_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(overrides["CEO_PROJECT_STATE_DIR"]).mkdir(parents=True, exist_ok=True)
    os.environ.update(overrides)
    # CLEAR carriers so a stale-inherited value can never point at the live tree.
    for key in AUDIT_CLEAR_CARRIERS:
        os.environ.pop(key, None)
    # Re-export the real PyYAML user-site AFTER the HOME redirect (setdefault so a
    # test that manages its own PYTHONUSERBASE keeps control).
    for key, value in tooling_overrides.items():
        os.environ.setdefault(key, value)
    # CLEAR GNUPGHOME so gpg resolves under the redirected (empty) HOME/.gnupg —
    # the suite must NOT reach the real signing keyring (see TOOLING_CLEAR_VARS).
    for key in TOOLING_CLEAR_VARS:
        os.environ.pop(key, None)
    # Publish the live-log snapshot for the WS-D1 drain comparator (children
    # inherit it). Only set when we actually resolved one.
    if live_log_snapshot is not None:
        os.environ[LIVE_LOG_SNAPSHOT_VAR] = live_log_snapshot

    # 4) Reset spool_writer dir caches so the new env resolves immediately.
    try:
        from _lib import spool_writer as _spool_writer
        _spool_writer._reset_caches_for_test()
    except Exception:
        pass  # fail-open; cache invalidation is hygiene, not correctness

    _REDIRECT = {"tmp_root": tmp_root, "env_snapshot": env_snapshot}
    return _REDIRECT


def _deactivate_redirect(state: Dict[str, object]) -> None:
    """Restore the env snapshot + remove the session tmpdir. Only the activating
    fixture calls this (no-op fixtures pass ``None`` and skip)."""
    global _REDIRECT
    env_snapshot = state.get("env_snapshot") or {}
    for key, value in env_snapshot.items():  # type: ignore[union-attr]
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    try:
        from _lib import spool_writer as _spool_writer
        _spool_writer._reset_caches_for_test()
    except Exception:
        pass
    tmp_root = state.get("tmp_root")
    if isinstance(tmp_root, Path):
        shutil.rmtree(tmp_root, ignore_errors=True)
    _REDIRECT = None


def live_log_path_snapshot() -> Optional[str]:
    """Public accessor for the captured live-log path snapshot (WS-D1)."""
    return os.environ.get(LIVE_LOG_SNAPSHOT_VAR) or None


# --- Fixtures (imported by-name into each conftest) -----------------------------

@pytest.fixture(scope="session", autouse=True)
def _ceo_audit_isolation_session():
    """Session-scoped autouse: redirect the full audit/HMAC carrier set to a
    per-session tmpdir before any test body runs; restore at session end.

    Idempotent across the three conftests that register it (see module docstring).
    """
    state = _activate_redirect()
    try:
        yield
    finally:
        if state is not None:
            _deactivate_redirect(state)


@pytest.fixture(autouse=True)
def _ceo_audit_isolation_check(request):
    """Function-scoped autouse: assert (defense-in-depth) that the PRODUCTION
    audit-dir resolver does not resolve to the snapshotted live dir.

    Sources the resolver from ``_lib.audit_emit._audit_dir`` (never a local
    re-implementation — AC-A5). Skips for ``@pytest.mark.allow_live_audit_dir``.
    Fires before ``TestEnvContext.setUp`` — by then the SESSION redirect has
    already made the dir non-live, so this never reds the ~2700 TestEnvContext
    tests (qa RC-1).
    """
    if request.node.get_closest_marker("allow_live_audit_dir") is not None:
        yield
        return
    snapshot = os.environ.get(LIVE_LOG_SNAPSHOT_VAR)
    if snapshot:
        try:
            from _lib import audit_emit as _audit_emit
            resolved_dir = str(Path(_audit_emit._audit_dir()).resolve())
            live_dir = str(Path(snapshot).resolve().parent)
        except Exception:
            resolved_dir = live_dir = None  # type: ignore[assignment]
        if resolved_dir is not None and resolved_dir == live_dir:
            pytest.fail(
                "PLAN-119 WS-A — audit-dir isolation breached: the production "
                "resolver (audit_emit._audit_dir) resolves to the LIVE audit "
                "dir during a test. A test mutated CEO_AUDIT_* back to the live "
                "tree. Use TestEnvContext or @pytest.mark.allow_live_audit_dir. "
                "(Paths intentionally not echoed — verify locally.)",
                pytrace=False,
            )
    yield
