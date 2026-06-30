"""Effective Claude Code settings resolver + tamper-surface classifier.

PLAN-135 W1 unit S0 — the shared module built ONCE for three consumers
(debate round-1 shared-module rule): W1 S3 (`/ceo-boot` Tier-S tamper
tripwires + `/self-test`), W2 H2 (ConfigChange audit), W5 O11.

## Layer model (Claude Code documented precedence — highest wins)

    managed  >  local  >  project  >  user

    managed : OS managed-settings.json (enterprise policy; macOS
              `/Library/Application Support/ClaudeCode/`, Linux
              `/etc/claude-code/`, Windows `C:/ProgramData/ClaudeCode/`)
    local   : <project>/.claude/settings.local.json  (gitignored —
              sentinel-blind; the prime tamper layer, threat-model §2)
    project : <project>/.claude/settings.json
    user    : ~/.claude/settings.json

CLI-argument overrides sit between `managed` and `local` in the live
harness; they are not a file surface, so a file resolver cannot see
them — documented honest boundary.

The merge is per TOP-LEVEL key (the highest-precedence layer providing
a key wins it; ``sources`` records which layer won each key). NOTE the
live harness deep-merges some keys — ``hooks`` from ALL layers run, and
``permissions`` allow/deny lists concatenate — which is exactly why
every tamper check below scans EVERY layer individually, never just the
merged view.

## Fail-open contract

Advisory only. Every public reader returns a degraded-but-typed result
on parse errors (dict / list / int as declared) and NEVER raises to the
caller. Degraded paths leave a stderr breadcrumb (`mcp_routing.py`
precedent). This module is deliberately STANDALONE (no `_lib` imports,
no audit emits) so consumers can load it via importlib from any
checkout; closed-enum audit emission is owned by the consumers (S3/H2),
not by this resolver.

## Env-read doctrine

Tamper-relevant env (``ANTHROPIC_*`` + dangerously-skip flags) is
captured ONCE at import time into ``IMPORT_TIME_ENV_SNAPSHOT`` — the
trusted_env import-time snapshot pattern (`check_bash_safety.py`
precedent) — so a late-set value injected mid-session cannot dodge the
scan by mutating ``os.environ`` before the check runs. Callers may pass
their own snapshot to ``classify_tampering``; passing ``None`` uses the
import-time snapshot. ``CLAUDE_PROJECT_DIR`` is read live: it is a path
locator, not a tamper surface, and consumers pass explicit dirs anyway.

References:
    PLAN-135 W1 S3 + PLAN-135/research/THREAT-MODEL-WORKSHEET.md §2
    ADR-149 (model-id allowlist — parsed live at runtime, single source)
    ADR-003 Path C (the compensating-control story this makes observable)

Stdlib-only. Python >= 3.9. NO third-party deps.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple, Union

_PathLike = Union[str, "os.PathLike[str]"]

# ---------------------------------------------------------------------------
# Layer names (closed set)
# ---------------------------------------------------------------------------

LAYER_USER = "user"          # ~/.claude/settings.json
LAYER_PROJECT = "project"    # <project>/.claude/settings.json
LAYER_LOCAL = "local"        # <project>/.claude/settings.local.json
LAYER_MANAGED = "managed"    # OS managed-settings.json (enterprise policy)

#: Findings-only pseudo-layers (never appear in resolve_settings layers).
LAYER_ENV = "env"            # process-env findings (classify_tampering)
LAYER_DISK = "disk"          # on-disk hook-census findings

#: Merge application order, lowest precedence first (later wins).
LAYER_MERGE_ORDER: Tuple[str, ...] = (
    LAYER_USER, LAYER_PROJECT, LAYER_LOCAL, LAYER_MANAGED,
)

# ---------------------------------------------------------------------------
# Closed enum — tamper breadcrumb classes (stable snake_case; consumers
# S3 / H2 / O11 emit these verbatim)
# ---------------------------------------------------------------------------

TAMPER_DISABLE_ALL_HOOKS = "settings_tamper_disable_all_hooks"
TAMPER_MODEL_REMAP = "settings_tamper_model_remap"
TAMPER_ENDPOINT_REMAP = "settings_tamper_endpoint_remap"
TAMPER_PERMISSION_BYPASS = "settings_tamper_permission_bypass"
TAMPER_HOOK_COUNT_MISMATCH = "settings_tamper_hook_count_mismatch"
# PLAN-135-FOLLOWUP (Codex R5 P1-3) — a settings-layer `env` block setting
# CEO_STATUSLINE_SIDECAR steers the always-on statusLine sidecar writer out of
# the audit/state dir (an output/exfil-path steer — distinct from endpoint_remap
# so SOC triage routes correctly). Detected ONLY in settings layers (the attack
# surface); the Owner's legitimate launch-env override is structurally invisible
# to the env-snapshot check (_capture_tamper_env filters to ANTHROPIC_*/DANGEROUSLY*).
TAMPER_SIDECAR_REDIRECT = "settings_tamper_sidecar_redirect"

TAMPER_CLASSES = frozenset({
    TAMPER_DISABLE_ALL_HOOKS,
    TAMPER_MODEL_REMAP,
    TAMPER_ENDPOINT_REMAP,
    TAMPER_PERMISSION_BYPASS,
    TAMPER_HOOK_COUNT_MISMATCH,
    TAMPER_SIDECAR_REDIRECT,
})

# ---------------------------------------------------------------------------
# FORBIDDEN-KEYS / tamper-surface table (single source — powers S3 + W2 H2
# + W5 O11; mirrors THREAT-MODEL-WORKSHEET.md §2). ``surface`` values:
#   settings : checked in EVERY settings layer (incl. each layer's `env`
#              block, which is a settings-set env channel)
#   env      : checked in the env snapshot passed to classify_tampering
#   disk     : on-disk hook census vs registered hooks
# ---------------------------------------------------------------------------

FORBIDDEN_KEYS: Tuple[Dict[str, str], ...] = (
    {
        "surface": "settings", "key": "disableAllHooks",
        "rule": "truthy-in-any-layer", "tamper_class": TAMPER_DISABLE_ALL_HOOKS,
        "note": "one line in settings.local.json silently disarms every "
                "registered hook (threat-model §2 vector a)",
    },
    {
        "surface": "env", "key": "ANTHROPIC_MODEL",
        "rule": "set-outside-model-allowlist", "tamper_class": TAMPER_MODEL_REMAP,
        "note": "re-points the session model outside the ADR-149 allowlist, "
                "outside the repo's pin web",
    },
    {
        "surface": "env", "key": "ANTHROPIC_DEFAULT_*",
        "rule": "set-outside-model-allowlist", "tamper_class": TAMPER_MODEL_REMAP,
        "note": "prefix family (ANTHROPIC_DEFAULT_OPUS_MODEL / _SONNET_MODEL / "
                "_HAIKU_MODEL ...)",
    },
    {
        "surface": "env", "key": "ANTHROPIC_SMALL_FAST_MODEL",
        "rule": "set-outside-model-allowlist", "tamper_class": TAMPER_MODEL_REMAP,
        "note": "same remap family — S0 addition beyond the plan's minimum "
                "enumeration (same class semantics)",
    },
    {
        "surface": "env", "key": "ANTHROPIC_BASE_URL",
        "rule": "set-to-non-default-endpoint", "tamper_class": TAMPER_ENDPOINT_REMAP,
        "note": "model substitution AND transcript egress to an attacker "
                "endpoint — bypasses the allowlist check entirely",
    },
    {
        "surface": "env", "key": "ANTHROPIC_AUTH_TOKEN",
        "rule": "set (value always redacted in findings)",
        "tamper_class": TAMPER_ENDPOINT_REMAP,
        "note": "credential remap; breadcrumbs never carry the value",
    },
    {
        "surface": "settings", "key": "apiKeyHelper",
        "rule": "present-in-any-layer", "tamper_class": TAMPER_ENDPOINT_REMAP,
        "note": "custom credential helper reroutes auth out-of-band",
    },
    {
        "surface": "settings", "key": "permissions.defaultMode",
        "rule": "equals:bypassPermissions", "tamper_class": TAMPER_PERMISSION_BYPASS,
        "note": "nullifies the W1 S2 native permission floor",
    },
    {
        "surface": "settings", "key": "*dangerously*",
        "rule": "truthy-in-any-layer (top-level or permissions.*)",
        "tamper_class": TAMPER_PERMISSION_BYPASS,
        "note": "dangerously-skip flag family, matched case-insensitively",
    },
    {
        "surface": "env", "key": "*DANGEROUSLY*",
        "rule": "truthy", "tamper_class": TAMPER_PERMISSION_BYPASS,
        "note": "env-side dangerously-skip flags (best-effort family match)",
    },
    {
        "surface": "settings", "key": "CEO_STATUSLINE_SIDECAR",
        "rule": "set-in-settings-layer (NOT process-env)",
        "tamper_class": TAMPER_SIDECAR_REDIRECT,
        "note": "a settings-layer `env` block steering the always-on statusLine "
                "sidecar writer out of the audit/state dir (output/exfil-path "
                "steer); the Owner launch-env override is legitimate + invisible "
                "to the env snapshot, so only settings layers are flagged "
                "(Codex R5 P1-3)",
    },
    {
        "surface": "disk", "key": ".claude/hooks/*.py",
        "rule": "registered-basename-missing-on-disk",
        "tamper_class": TAMPER_HOOK_COUNT_MISMATCH,
        "note": "a registered hook script missing from disk degrades the rail "
                "silently (hook fail-open = allow); extra UNregistered files "
                "on disk are normal and never flagged",
    },
)

# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

#: Official default API endpoint — an explicit ANTHROPIC_BASE_URL equal to
#: this (modulo trailing slash) is NOT a remap.
_DEFAULT_BASE_URL = "https://api.anthropic.com"

_DETAIL_CAP = 240

#: Matches hook script basenames inside settings `command` strings —
#: same semantics as verify-counts.sh ("distinct *.py basenames").
_HOOK_SCRIPT_RE = re.compile(r"([A-Za-z0-9_\-]+\.py)\b")

#: Quoted model ids inside the ADR-149 allowlist block.
_MODEL_ID_DQ_RE = re.compile(r'"(claude-[A-Za-z0-9.\-]+)"')
_MODEL_ID_SQ_RE = re.compile(r"'(claude-[A-Za-z0-9.\-]+)'")
_FROZENSET_RE = re.compile(r"frozenset\(\s*\{(.*?)\}\s*\)", re.DOTALL)

_ADR_149_RELPATH = ("/".join((".claude", "adr", "ADR-149-model-id-allowlist.md")))


def _breadcrumb(message: str) -> None:
    """stderr breadcrumb for degraded paths (mcp_routing precedent)."""
    try:
        sys.stderr.write(f"[effective_config] {message}\n")
    except Exception:
        pass


def _cap(text: str, limit: int = _DETAIL_CAP) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _safe_str(value: Any) -> str:
    try:
        return str(value)
    except Exception:
        return ""


def _truthy(value: Any) -> bool:
    """JSON/env-tolerant truthiness: false/0/''/'false'/'no'/'off' = False."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(value)


def _capture_tamper_env(environ: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """Capture tamper-relevant env keys (ANTHROPIC_* + *DANGEROUSLY*)."""
    src = os.environ if environ is None else environ
    out: Dict[str, str] = {}
    try:
        for key, value in src.items():
            k = str(key)
            if k.startswith("ANTHROPIC_") or "DANGEROUSLY" in k.upper():
                out[k] = _safe_str(value)
    except Exception:
        return {}
    return out


#: Import-time snapshot of the tamper-relevant env surface (trusted_env
#: pattern). ``classify_tampering(resolved, None)`` consults THIS, never
#: live os.environ.
IMPORT_TIME_ENV_SNAPSHOT: Dict[str, str] = _capture_tamper_env()


def _managed_settings_paths() -> List[Path]:
    """Candidate managed-settings.json locations (first existing wins).

    Module-level function (not a constant) so tests can patch it to keep
    runs hermetic on machines that DO carry a real managed policy file.
    """
    return [
        Path("/Library/Application Support/ClaudeCode/managed-settings.json"),
        Path("/etc/claude-code/managed-settings.json"),
        Path("C:/ProgramData/ClaudeCode/managed-settings.json"),
    ]


def _layer_paths(project_dir: Path) -> List[Tuple[str, Optional[Path]]]:
    """(name, path) per layer in LAYER_MERGE_ORDER. Managed may be None."""
    user = Path.home() / ".claude" / "settings.json"
    project = project_dir / ".claude" / "settings.json"
    local = project_dir / ".claude" / "settings.local.json"
    managed: Optional[Path] = None
    for candidate in _managed_settings_paths():
        try:
            if Path(candidate).is_file():
                managed = Path(candidate)
                break
        except OSError:
            continue
    return [
        (LAYER_USER, user),
        (LAYER_PROJECT, project),
        (LAYER_LOCAL, local),
        (LAYER_MANAGED, managed),
    ]


def _read_json_layer(name: str, path: Optional[Path]) -> Dict[str, Any]:
    """Read one settings layer. NEVER raises — degraded-but-typed."""
    layer: Dict[str, Any] = {
        "name": name,
        "path": "" if path is None else str(path),
        "exists": False,
        "ok": True,
        "data": {},
        "error": None,
    }
    if path is None:
        return layer
    try:
        if not Path(path).is_file():
            return layer
        layer["exists"] = True
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            layer["ok"] = False
            layer["error"] = "top-level JSON is not an object"
            return layer
        layer["data"] = parsed
    except json.JSONDecodeError as exc:
        layer["ok"] = False
        layer["error"] = _cap(f"invalid JSON: {exc}", 160)
    except OSError as exc:
        layer["ok"] = False
        layer["error"] = _cap(f"unreadable: {type(exc).__name__}", 160)
    except Exception as exc:  # pragma: no cover — belt-and-braces fail-open
        layer["ok"] = False
        layer["error"] = _cap(f"parse failure: {type(exc).__name__}", 160)
    return layer


def _registered_hook_basenames(settings_dict: Any) -> Set[str]:
    """Distinct *.py basenames in hooks{} command lines (verify-counts rule)."""
    names: Set[str] = set()
    if not isinstance(settings_dict, dict):
        return names
    hooks = settings_dict.get("hooks")
    if not isinstance(hooks, dict):
        return names
    for event_entries in hooks.values():
        if not isinstance(event_entries, list):
            continue
        for entry in event_entries:
            if not isinstance(entry, dict):
                continue
            entry_hooks = entry.get("hooks")
            if not isinstance(entry_hooks, list):
                continue
            for hook in entry_hooks:
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command")
                if isinstance(command, str):
                    names.update(_HOOK_SCRIPT_RE.findall(command))
    return names


#: Census scope — only project-OWNED layers map onto <project>/.claude/hooks;
#: user/managed hooks live outside the project tree (their commands resolve
#: against the user profile), so counting them against the project's disk
#: would manufacture false mismatches.
_CENSUS_LAYERS = (LAYER_PROJECT, LAYER_LOCAL)


def _census_registered_basenames(resolved: Any) -> Set[str]:
    """Union of registered basenames across the project-owned layers."""
    names: Set[str] = set()
    if not isinstance(resolved, dict):
        return names
    layers = resolved.get("layers")
    if not isinstance(layers, list):
        return names
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        if layer.get("name") not in _CENSUS_LAYERS:
            continue
        names |= _registered_hook_basenames(layer.get("data"))
    return names


def _hook_on_disk(path: Path) -> bool:
    """Best-effort 'effective' test: present + readable.

    Exec bits are NOT required on the .py itself — hooks dispatch via the
    `_python-hook.sh` shim or bare `python3`, so presence + readability is
    the honest effectiveness signal for the script file.
    """
    try:
        return path.is_file() and os.access(str(path), os.R_OK)
    except OSError:
        return False


def _finding(tamper_class: str, layer: str, detail: str) -> Dict[str, str]:
    return {
        "class": tamper_class,
        "layer": _safe_str(layer)[:64],
        "detail": _cap(detail),
    }


_MODEL_REMAP_EXACT_KEYS = ("ANTHROPIC_MODEL", "ANTHROPIC_SMALL_FAST_MODEL")
_MODEL_REMAP_PREFIX = "ANTHROPIC_DEFAULT_"


def _check_env_mapping(
    mapping: Any,
    layer_name: str,
    allowlist: List[str],
    findings: List[Dict[str, str]],
) -> None:
    """Run the env-surface forbidden-key checks against one mapping.

    Used for BOTH the process-env snapshot (layer='env') and each settings
    layer's `env` block (layer=<layer name>) — settings-set env is the same
    tamper channel.
    """
    try:
        items = sorted(
            (_safe_str(k), "" if v is None else _safe_str(v))
            for k, v in dict(mapping).items()
        )
    except Exception:
        return
    allow_set = {m.strip() for m in allowlist if _safe_str(m).strip()}
    degraded_model_check = False
    for key, value in items:
        stripped = value.strip()
        if not stripped:
            continue
        if key in _MODEL_REMAP_EXACT_KEYS or key.startswith(_MODEL_REMAP_PREFIX):
            if allow_set:
                if stripped not in allow_set:
                    findings.append(_finding(
                        TAMPER_MODEL_REMAP, layer_name,
                        f"{key}={stripped} outside model allowlist "
                        f"{sorted(allow_set)}",
                    ))
            else:
                degraded_model_check = True
        elif key == "ANTHROPIC_BASE_URL":
            if stripped.rstrip("/") != _DEFAULT_BASE_URL:
                findings.append(_finding(
                    TAMPER_ENDPOINT_REMAP, layer_name,
                    f"ANTHROPIC_BASE_URL={stripped} (non-default endpoint — "
                    f"model substitution / transcript egress channel)",
                ))
        elif key == "ANTHROPIC_AUTH_TOKEN":
            findings.append(_finding(
                TAMPER_ENDPOINT_REMAP, layer_name,
                "ANTHROPIC_AUTH_TOKEN set (value redacted)",
            ))
        elif "DANGEROUSLY" in key.upper() and _truthy(stripped):
            findings.append(_finding(
                TAMPER_PERMISSION_BYPASS, layer_name,
                f"{key}={stripped} (dangerously-skip flag)",
            ))
        elif key == "CEO_STATUSLINE_SIDECAR" and layer_name != LAYER_ENV:
            # PLAN-135-FOLLOWUP (Codex R5 P1-3): a SETTINGS-LAYER env block (user/
            # project/local/managed) steering the always-on statusLine sidecar
            # writer is an output/exfil-path tamper. Gated on layer_name != LAYER_ENV
            # because (a) the Owner's legitimate launch-env override is invisible to
            # the env snapshot anyway (_capture_tamper_env filters to ANTHROPIC_*/
            # DANGEROUSLY*) — so a LAYER_ENV branch would be dead — and (b) flagging
            # the process-env would false-positive the documented full-path override.
            # The value (a path) is redacted; the detail names only the var + layer.
            findings.append(_finding(
                TAMPER_SIDECAR_REDIRECT, layer_name,
                "CEO_STATUSLINE_SIDECAR set in settings layer (statusLine sidecar "
                "write-path steer; value redacted)",
            ))
    if degraded_model_check:
        _breadcrumb(
            "model allowlist unavailable (ADR-149 unreadable) — model-remap "
            "membership check degraded fail-open (no finding emitted)"
        )


def _check_settings_layer(
    layer_name: str,
    data: Any,
    allowlist: List[str],
    findings: List[Dict[str, str]],
) -> None:
    """Run the settings-surface forbidden-key checks against ONE layer."""
    if not isinstance(data, dict):
        return
    # (a) disableAllHooks — truthy in any layer disarms the whole rail.
    if _truthy(data.get("disableAllHooks")):
        findings.append(_finding(
            TAMPER_DISABLE_ALL_HOOKS, layer_name,
            f"disableAllHooks={data.get('disableAllHooks')!r} disarms every "
            f"registered hook",
        ))
    # (d) permission bypass — defaultMode + dangerously-skip flag family.
    permissions = data.get("permissions")
    if isinstance(permissions, dict):
        mode = _safe_str(permissions.get("defaultMode") or "").strip()
        if mode == "bypassPermissions":
            findings.append(_finding(
                TAMPER_PERMISSION_BYPASS, layer_name,
                "permissions.defaultMode=bypassPermissions nullifies the "
                "native permission floor",
            ))
        for key in sorted(permissions, key=_safe_str):
            if "dangerously" in _safe_str(key).lower() and _truthy(permissions[key]):
                findings.append(_finding(
                    TAMPER_PERMISSION_BYPASS, layer_name,
                    f"permissions.{key}={permissions[key]!r} "
                    f"(dangerously-skip flag)",
                ))
    for key in sorted(data, key=_safe_str):
        if "dangerously" in _safe_str(key).lower() and _truthy(data[key]):
            findings.append(_finding(
                TAMPER_PERMISSION_BYPASS, layer_name,
                f"{key}={data[key]!r} (dangerously-skip flag)",
            ))
    # (c) apiKeyHelper — endpoint/credential remap.
    helper = data.get("apiKeyHelper")
    if isinstance(helper, str) and helper.strip():
        findings.append(_finding(
            TAMPER_ENDPOINT_REMAP, layer_name,
            f"apiKeyHelper={helper.strip()} (custom credential helper "
            f"reroutes auth)",
        ))
    # (b/c via settings) — the layer's env block is a settings-set env channel.
    env_block = data.get("env")
    if isinstance(env_block, dict):
        _check_env_mapping(env_block, layer_name, allowlist, findings)


def _check_hook_census(resolved: Any, findings: List[Dict[str, str]]) -> None:
    """(e) registered-vs-on-disk census. One-directional by design:
    registered-but-missing = degraded rail (flagged); extra unregistered
    files on disk = normal (never flagged)."""
    if not isinstance(resolved, dict):
        return
    project_dir = resolved.get("project_dir")
    if not isinstance(project_dir, str) or not project_dir:
        return
    registered = _census_registered_basenames(resolved)
    if not registered:
        return
    hooks_dir = Path(project_dir) / ".claude" / "hooks"
    missing = sorted(n for n in registered if not _hook_on_disk(hooks_dir / n))
    if missing:
        findings.append(_finding(
            TAMPER_HOOK_COUNT_MISMATCH, LAYER_DISK,
            f"registered={len(registered)} "
            f"effective_on_disk={len(registered) - len(missing)} "
            f"missing={missing[:8]}",
        ))


def _resolve_repo_root(project_dir: Optional[_PathLike]) -> Path:
    if project_dir:
        return Path(_safe_str(project_dir))
    env_root = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if env_root:
        return Path(env_root)
    # <root>/.claude/hooks/_lib/effective_config.py → parents[3] = <root>
    return Path(__file__).resolve().parents[3]


def _parse_allowlist_members(text: str) -> List[str]:
    """Extract model ids from ADR-149, robustly.

    Strategy: prefer ids quoted inside the first ``frozenset({...})``
    block; fall back to any quoted ``claude-*`` id in the document.
    Order-preserving, de-duplicated.
    """
    match = _FROZENSET_RE.search(text)
    chunk = match.group(1) if match else text
    members = _MODEL_ID_DQ_RE.findall(chunk) + _MODEL_ID_SQ_RE.findall(chunk)
    if not members and match:
        members = _MODEL_ID_DQ_RE.findall(text) + _MODEL_ID_SQ_RE.findall(text)
    out: List[str] = []
    for member in members:
        if member not in out:
            out.append(member)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_settings(project_dir: _PathLike) -> Dict[str, Any]:
    """Resolve the layered Claude Code settings for ``project_dir``.

    Returns (always — never raises)::

        {
          "project_dir": str,
          "layers": [  # in LAYER_MERGE_ORDER: user, project, local, managed
            {"name": str, "path": str, "exists": bool, "ok": bool,
             "data": dict, "error": Optional[str]},
            ...
          ],
          "effective": dict,   # top-level-key merge, highest precedence wins
          "sources": {top_level_key: layer_name},
          "ok": bool,          # False iff any present layer failed to parse
          "errors": [str],     # one entry per failed layer
        }

    A missing layer file is NOT an error (exists=False, ok=True, data={}).
    A corrupt layer degrades to data={} + ok=False + error, and the merge
    proceeds over the healthy layers (fail-open).
    """
    try:
        pdir = Path(_safe_str(project_dir))
        layers = [_read_json_layer(name, path) for name, path in _layer_paths(pdir)]
        effective: Dict[str, Any] = {}
        sources: Dict[str, str] = {}
        errors: List[str] = []
        for layer in layers:
            if layer["error"]:
                errors.append(f"{layer['name']}: {layer['error']}")
            if layer["ok"] and isinstance(layer["data"], dict):
                for key, value in layer["data"].items():
                    effective[key] = value
                    sources[_safe_str(key)] = layer["name"]
        return {
            "project_dir": str(pdir),
            "layers": layers,
            "effective": effective,
            "sources": sources,
            "ok": not errors,
            "errors": errors,
        }
    except Exception as exc:
        _breadcrumb(f"resolve_settings degraded fail-open: {type(exc).__name__}")
        return {
            "project_dir": _safe_str(project_dir),
            "layers": [],
            "effective": {},
            "sources": {},
            "ok": False,
            "errors": [f"resolver_internal_error: {type(exc).__name__}"],
        }


def classify_tampering(
    resolved: Dict[str, Any],
    env_snapshot: Optional[Mapping[str, str]] = None,
) -> List[Dict[str, str]]:
    """Classify tamper indicators in a ``resolve_settings`` result + env.

    ``env_snapshot=None`` consults ``IMPORT_TIME_ENV_SNAPSHOT`` (the
    trusted import-time capture) — NEVER live ``os.environ``. Pass an
    explicit mapping (possibly ``{}``) to control the env surface.

    Returns a list of closed-enum breadcrumb dicts (possibly empty)::

        {"class": <TAMPER_* member>, "layer": <layer name|env|disk>,
         "detail": <capped str, secrets redacted>}

    Deterministic ordering: layers in LAYER_MERGE_ORDER, then env, then
    disk census. NEVER raises — internal failure returns ``[]`` with a
    stderr breadcrumb (advisory fail-open).
    """
    try:
        findings: List[Dict[str, str]] = []
        if not isinstance(resolved, dict):
            return findings
        layers = resolved.get("layers")
        if not isinstance(layers, list):
            layers = []
        allowlist = get_model_allowlist(resolved.get("project_dir") or None)
        for layer in layers:
            if not isinstance(layer, dict):
                continue
            data = layer.get("data")
            if isinstance(data, dict) and data:
                _check_settings_layer(
                    _safe_str(layer.get("name", "unknown")),
                    data, allowlist, findings,
                )
        env = IMPORT_TIME_ENV_SNAPSHOT if env_snapshot is None else env_snapshot
        _check_env_mapping(env, LAYER_ENV, allowlist, findings)
        _check_hook_census(resolved, findings)
        return findings
    except Exception as exc:
        _breadcrumb(f"classify_tampering degraded fail-open: {type(exc).__name__}")
        return []


def count_registered_hooks(settings_dict: Dict[str, Any]) -> int:
    """Distinct ``*.py`` basenames in ONE settings dict's hooks{} commands.

    Same counting rule as ``verify-counts.sh`` ("registered hooks =
    distinct *.py script basenames appearing in settings.json hooks{}
    command lines"). Garbage input → 0 (fail-open, typed).
    """
    try:
        return len(_registered_hook_basenames(settings_dict))
    except Exception as exc:
        _breadcrumb(f"count_registered_hooks degraded fail-open: {type(exc).__name__}")
        return 0


def count_effective_hooks(project_dir: _PathLike) -> int:
    """Best-effort count of registered hooks that are EFFECTIVE on disk.

    Scope: union of hook basenames registered in the project-owned layers
    (project + local — user/managed hooks resolve outside the project
    tree) that exist as readable files under ``<project_dir>/.claude/hooks/``.
    Compare with ``count_registered_hooks`` per layer to detect a silently
    degraded rail (a registered script missing on disk fails open = allow).
    NEVER raises — returns 0 on internal failure.
    """
    try:
        resolved = resolve_settings(project_dir)
        registered = _census_registered_basenames(resolved)
        hooks_dir = Path(_safe_str(project_dir)) / ".claude" / "hooks"
        return sum(1 for name in registered if _hook_on_disk(hooks_dir / name))
    except Exception as exc:
        _breadcrumb(f"count_effective_hooks degraded fail-open: {type(exc).__name__}")
        return 0


def registered_hook_basenames(settings_dict: Dict[str, Any]) -> List[str]:
    """Sorted distinct hook basenames in ONE settings dict (diagnostics)."""
    try:
        return sorted(_registered_hook_basenames(settings_dict))
    except Exception:
        return []


def get_model_allowlist(project_dir: Optional[_PathLike] = None) -> List[str]:
    """Parse the ADR-149 model-id allowlist from the live repo at runtime.

    Root resolution: explicit ``project_dir`` arg, else ``CLAUDE_PROJECT_DIR``
    env, else this module's checkout root (``parents[3]``). Reads
    ``.claude/adr/ADR-149-model-id-allowlist.md`` and extracts the
    ``frozenset({...})`` members (single source — never a hardcoded mirror).

    Fail-open: missing/unreadable/unparseable ADR → ``[]``; callers MUST
    treat an empty list as "membership unknown" (skip membership checks),
    never as "everything forbidden".
    """
    try:
        root = _resolve_repo_root(project_dir)
        adr_path = root / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"
        if not adr_path.is_file():
            return []
        return _parse_allowlist_members(
            adr_path.read_text(encoding="utf-8", errors="replace")
        )
    except Exception as exc:
        _breadcrumb(f"get_model_allowlist degraded fail-open: {type(exc).__name__}")
        return []
