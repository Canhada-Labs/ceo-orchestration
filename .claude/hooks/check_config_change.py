#!/usr/bin/env python3
"""PLAN-135 W2 H2 — ConfigChange guard: out-of-band settings.json tamper audit.

Closes the S197 out-of-band-settings-edit observability class. The harness
``ConfigChange`` event fires when Claude Code's settings change outside the
normal in-session flow; this hook RESOLVES the multi-layer settings via the
shared ``_lib/effective_config`` resolver (the SAME forbidden-keys single
source W1 S3 uses), classifies tamper indicators on the SETTINGS-FILE
surfaces, and:

  - ALLOWS + audits a benign change (``config_change_observed``, one emit);
  - ADVISORY-BLOCKS a change that introduces a ``FORBIDDEN_KEYS`` finding
    (``config_change_forbidden_key``, ONE emit per tamper class), returning
    a ``{"decision": "block", "reason": ...}`` decision so the operator sees
    the tamper at the moment of the edit — NOT only at the next boot.

## Coverage boundary (debate R1 — stated honestly in ADR-153 §H2)

H2 is itself a hook. It is:
  - **disarmed by the very ``disableAllHooks`` it polices** — once that key
    lands, no further ConfigChange hook runs (a same-session disarm window);
  - **blind to edits made entirely outside the harness** (a text editor
    writing settings.local.json on disk fires no ConfigChange event).

Named compensators (independent channels): the W1 S3 ``/ceo-boot`` Tier-S
boot tripwires (re-scan the RESOLVED settings + the import-time env snapshot
on the NEXT boot, catching anything H2's same-session window missed) and the
W5 O10 OTEL hook-execution witness (an out-of-band record that a hook ran,
independent of the hook's own fail-open emit). This hook is a near-real-time
*detector*, not a *guarantee*.

## Surface scope (deliberately narrower than S3)

H2 polices the SETTINGS FILE surfaces only — a ConfigChange event IS a
settings-file change. The ``env`` (process-env) and ``disk`` (hook-census)
tamper surfaces are S3's at boot and are deliberately NOT block-scoped here
(``_CONFIG_CHANGE_LAYERS`` = the settings layers + ``other``; census /
process-env findings are filtered out before any block, see
``_settings_surface_findings``). A settings layer's *own* ``env`` block IS a
settings-file change and IS in scope — the resolver classifies it under the
layer's own name (``user`` / ``project`` / ``local`` / ``managed``), so it is
NOT filtered.

## Contract

- ADVISORY by default + fail-open (PLAN-091 S116 doctrine: parse errors /
  missing files / resolver failure → stderr breadcrumb + emit ``{}``). The
  ONLY non-empty decision is the forbidden-key BLOCK; every infra condition
  fails toward ``{}`` (allow), never toward a spurious block.
- Closed-enum audit only — ``config_change_observed`` /
  ``config_change_forbidden_key`` are registered in BOTH
  ``_lib/audit_emit._KNOWN_ACTIONS`` and ``SPEC/v1/audit-log.schema.md``
  (v2.43). Both route through their dedicated deny-by-default ``_scrub_``
  branch; the changed file's PATH/BODY, any settings VALUE, and the
  effective_config finding DETAIL string NEVER reach the wire.
- Kill-switch: ``CEO_CONFIG_CHANGE_GUARD=0`` → ``{}`` (no scan, no emit).
- Stdlib only, Python >= 3.9. ``from __future__ import annotations``,
  ``typing.Optional`` (no runtime PEP 604).
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

# Make the local `_lib` importable (matches existing hooks' idiom).
_HOOKS_DIR = os.path.dirname(os.path.realpath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

# effective_config: the SHARED forbidden-keys single source (W1 S0). Import
# is guarded — if the resolver is unavailable (truncated install / partial
# checkout) the hook degrades to a pure allow (fail-open §5), never blocks.
try:
    from _lib import effective_config as _eff  # noqa: E402
    _EFF_AVAILABLE = True
except Exception:  # pragma: no cover — degrade to allow
    _eff = None  # type: ignore[assignment]
    _EFF_AVAILABLE = False

# audit_emit: import-guarded. Unavailable → no audit, hook still decides.
try:
    from _lib import audit_emit as _audit_emit  # noqa: E402
    _AUDIT_AVAILABLE = True
except Exception:  # pragma: no cover
    _audit_emit = None  # type: ignore[assignment]
    _AUDIT_AVAILABLE = False


#: Settings-FILE layer surfaces H2 block-scopes (a ConfigChange IS a file
#: change). Mirrors _CONFIG_CHANGE_LAYERS in audit_emit. Process-``env`` and
#: ``disk`` (hook-census) findings are S3's surfaces and are filtered out
#: before any block decision — H2 never blocks on them.
_BLOCK_SCOPE_LAYERS = frozenset({"user", "project", "local", "managed"})

#: The closed env/disk pseudo-layer names a finding may carry (filtered out).
_NON_FILE_LAYERS = frozenset({"env", "disk"})

#: Audit-wire layer enum (settings layers + the safe sentinel). Mirrors
#: audit_emit._CONFIG_CHANGE_LAYERS.
_AUDIT_LAYERS = frozenset({"user", "project", "local", "managed", "other"})

_REASON_CAP = 600


def _breadcrumb(message: str) -> None:
    """stderr breadcrumb for degraded / fail-open paths (closeout-guard precedent)."""
    try:
        sys.stderr.write("# check_config_change: %s\n" % str(message)[:200])
    except Exception:
        pass


def _disabled() -> bool:
    return os.environ.get("CEO_CONFIG_CHANGE_GUARD", "1").strip() == "0"


def _coerce_layer(layer: Any) -> str:
    """Coerce a finding layer to the audit-wire closed enum (sentinel ``other``)."""
    return layer if layer in _AUDIT_LAYERS else "other"


def _resolve_cwd(hook_input: Dict[str, Any]) -> str:
    """Project dir from the hook payload, else CLAUDE_PROJECT_DIR, else cwd."""
    cwd = hook_input.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        return cwd
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if env_dir:
        return env_dir
    return os.getcwd()


def _settings_surface_findings(findings: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Keep only findings scoped to a settings-FILE layer (drop env/disk).

    H2 block-scopes the file surfaces a ConfigChange event represents; the
    process-``env`` snapshot and the on-disk hook census are S3's boot
    surfaces, not a settings-file change, so census/env findings are
    OBSERVE-ONLY here — never block-worthy.
    """
    out: List[Dict[str, str]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        layer = finding.get("layer")
        if layer in _NON_FILE_LAYERS:
            continue
        out.append(finding)
    return out


def _classify(cwd: str) -> List[Dict[str, str]]:
    """Resolve + classify; never raises (resolver is fail-open by contract)."""
    if not _EFF_AVAILABLE or _eff is None:
        _breadcrumb("effective_config unavailable — degraded to allow (no scan)")
        return []
    try:
        resolved = _eff.resolve_settings(cwd)
        # classify_tampering(resolved, None) consults the IMPORT-TIME env
        # snapshot (trusted_env pattern), NEVER live os.environ — a late-set
        # value injected mid-session cannot dodge the scan. We then filter
        # env/disk findings out of the BLOCK path below.
        return _eff.classify_tampering(resolved)
    except Exception as exc:  # pragma: no cover — resolver already fails open
        _breadcrumb("classify failed (%s) — degraded to allow" % type(exc).__name__)
        return []


def _emit_observed(layer: str, session_id: str, project: str) -> None:
    """Audit the benign ALLOW path (one emit). Deny-by-default scrub branch.

    No public typed wrapper (settings_tamper_detected precedent) — emit via
    emit_generic, which routes config_change_observed through its dedicated
    _scrub_ branch + _CONFIG_CHANGE_OBSERVED_ALLOWLIST. The ONLY caller field
    is the closed-enum ``layer``; the changed file's path/body and any
    settings value are NEVER passed.
    """
    if not _AUDIT_AVAILABLE or _audit_emit is None:
        return
    try:
        _audit_emit.emit_generic(
            "config_change_observed",
            layer=_coerce_layer(layer),
            session_id=session_id,
            project=project,
        )
    except Exception as exc:  # pragma: no cover — emit never blocks the hook
        _breadcrumb("emit config_change_observed failed: %s" % type(exc).__name__)


def _emit_forbidden_key(
    tamper_class: str,
    layer: str,
    finding_count: int,
    session_id: str,
    project: str,
) -> None:
    """Audit one forbidden-key tamper class on the BLOCK path.

    ONE emit per (tamper_class) on the changed layer. Caller fields are the
    closed-enum ``tamper_class`` + ``layer`` + the integer ``finding_count``;
    the forbidden key's VALUE and the effective_config finding DETAIL are
    NEVER passed (the _scrub_ branch + allowlist would drop them anyway —
    belt and braces, the producer simply never sends them).
    """
    if not _AUDIT_AVAILABLE or _audit_emit is None:
        return
    try:
        _audit_emit.emit_generic(
            "config_change_forbidden_key",
            tamper_class=str(tamper_class),
            layer=_coerce_layer(layer),
            finding_count=int(finding_count),
            session_id=session_id,
            project=project,
        )
    except Exception as exc:  # pragma: no cover
        _breadcrumb("emit config_change_forbidden_key failed: %s" % type(exc).__name__)


def _block_reason(forbidden: List[Dict[str, str]]) -> str:
    """Build the advisory-block reason.

    Names the tamper CLASS and the LAYER only — never the finding ``detail``
    (an attacker endpoint URL / off-allowlist model id / apiKeyHelper path /
    dangerously-flag value lives there; it is NEVER rendered into a
    decision-channel string the operator's terminal echoes).
    """
    pairs = sorted({(f.get("class", "other"), f.get("layer", "other")) for f in forbidden})
    listed = "; ".join("%s @ %s" % (cls, layer) for cls, layer in pairs[:8])
    return (
        "CONFIG-TAMPER: an out-of-band settings change introduced a forbidden "
        "key (S197 class). Forbidden-key tamper detected: %s. Review the "
        "settings layer named above and revert if you did not intend it; this "
        "is advisory — your edit is recorded but NOT auto-reverted. Coverage "
        "boundary: this guard is itself a hook (disarmed by disableAllHooks "
        "and blind to outside-harness edits); the /ceo-boot tripwires re-scan "
        "on the next boot." % (listed or "unclassified")
    )[:_REASON_CAP]


def gate(hook_input: Dict[str, Any]) -> Dict[str, Any]:
    """Pure decision function.

    Returns ``{}`` (allow) on every benign / infra path, or
    ``{"decision": "block", "reason": ...}`` ONLY when a forbidden-key
    finding is scoped to a settings-file layer. Never raises.
    """
    if _disabled():
        return {}
    cwd = _resolve_cwd(hook_input)
    session_id = ""
    sid = hook_input.get("session_id")
    if isinstance(sid, str):
        session_id = sid[:64]
    project = ""
    proj = hook_input.get("project")
    if isinstance(proj, str):
        project = proj[:128]

    findings = _settings_surface_findings(_classify(cwd))

    # Partition: forbidden-key findings on a block-scope settings layer
    # (FORBIDDEN_KEYS hits — every classify_tampering finding IS a
    # FORBIDDEN_KEYS hit by construction) vs. nothing-to-block.
    forbidden = [
        f for f in findings
        if isinstance(f, dict) and f.get("layer") in _BLOCK_SCOPE_LAYERS
    ]

    if not forbidden:
        # Benign change (or only env/disk findings, which are S3's surface):
        # audit one observed event. Layer is best-effort from the highest-
        # precedence settings layer that exists; default "other".
        _emit_observed(_observed_layer(cwd), session_id, project)
        return {}

    # ADVISORY-BLOCK path: one audit emit per (tamper_class, layer) pair,
    # then return a block decision. NEVER degrade a would-be block into a
    # silent allow on a partial result (the resolver is fail-open; a real
    # forbidden finding here is authoritative).
    emitted = set()
    for finding in forbidden:
        cls = finding.get("class", "other")
        layer = finding.get("layer", "other")
        key = (cls, layer)
        if key in emitted:
            continue
        emitted.add(key)
        count = sum(
            1 for f in forbidden
            if f.get("class") == cls and f.get("layer") == layer
        )
        _emit_forbidden_key(cls, layer, count, session_id, project)
    return {"decision": "block", "reason": _block_reason(forbidden)}


def _observed_layer(cwd: str) -> str:
    """Best-effort 'which layer was observed' tag for the benign path.

    A ConfigChange event does not always name the changed file; we report the
    highest-precedence settings layer that exists on disk as a coarse tag
    (audit-wire closed enum). Fail-open: any failure → ``other``.
    """
    if not _EFF_AVAILABLE or _eff is None:
        return "other"
    try:
        resolved = _eff.resolve_settings(cwd)
        layers = resolved.get("layers")
        if not isinstance(layers, list):
            return "other"
        present = [
            layer.get("name") for layer in layers
            if isinstance(layer, dict) and layer.get("exists")
            and layer.get("name") in _BLOCK_SCOPE_LAYERS
        ]
        # LAYER_MERGE_ORDER is lowest→highest precedence; the last present
        # is the highest-precedence layer in effect.
        return _coerce_layer(present[-1]) if present else "other"
    except Exception:
        return "other"


def main() -> None:
    try:
        raw = sys.stdin.read() or "{}"
        hook_input = json.loads(raw)
        if not isinstance(hook_input, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as exc:
        # PLAN-091 S116: stdin parse error is an infra condition → breadcrumb
        # + schema-compliant allow.
        _breadcrumb("fail-open (stdin): %s" % str(exc)[:120])
        print("{}")
        return
    try:
        print(json.dumps(gate(hook_input), ensure_ascii=False))
    except Exception as exc:
        _breadcrumb("fail-open: %s" % str(exc)[:120])
        print("{}")


if __name__ == "__main__":
    main()
