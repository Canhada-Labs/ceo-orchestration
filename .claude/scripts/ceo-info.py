#!/usr/bin/env python3
"""ceo-info — live preflight / effective-config CLI for ceo-orchestration.

PLAN-133 item [G4] (Wave G). Goose-harvest port of `goose info --check`:
a single command that resolves the framework's runtime paths, checks each is
present + writable, prints the *effective* settings (which settings.json won,
which env overrides are active), and — opt-in only — performs ONE cheap model
round-trip and reports its latency. Exits NON-ZERO for CI when any required
path is missing or non-writable, so a misconfigured adopter fails fast.

Stdlib-only; Python >= 3.9. No third-party deps (no `anthropic` SDK — the live
round-trip is a guarded `urllib` POST to the token-counting endpoint, which
bills no tokens). Fail-open on infra: a probe that cannot resolve degrades to a
descriptive status, never a traceback. The live round-trip is **default-OFF**
(behavioral / network change, doctrine §3.1) behind `CEO_INFO_LIVE_PROBE=1` or
the explicit `--live` flag.

Usage:
    python3 .claude/scripts/ceo-info.py              # human summary (paths+settings)
    python3 .claude/scripts/ceo-info.py --check      # same; exit non-zero if a path is RED
    python3 .claude/scripts/ceo-info.py --json        # machine-readable
    python3 .claude/scripts/ceo-info.py --live        # opt-in live model round-trip
    CEO_INFO_LIVE_PROBE=1 python3 .claude/scripts/ceo-info.py --check

PLAN-135 W5 (unit o8o11o12) additions — all ADVISORY, none changes exit codes:
    --verify-models   # O8: ADR-149 allowlist members vs the local rate card
                      # (static, no network). With --live + credential it ALSO
                      # GETs /v1/models/<id> per member (bills zero tokens;
                      # Owner-run — CI + agents stay no-network).
    --cache-diagnose  # O11: read local transcript usage state — latest
                      # message id (the previous_message_id for a live
                      # diagnostics call), cache_read=0 streak. The live
                      # diagnostics call itself is PENDING-OWNER (recipe in
                      # the output); this command never bills.
    --hooks-diff      # O11: effective-hook-count diff via the SHARED
                      # _lib.effective_config (W1 bundle). FAIL-SOFT import:
                      # pre-ceremony trees report SKIPPED, never a traceback.

All three are OPT-IN — the default preflight keeps its original cheap path +
JSON shape, and none of them change the exit code (advisory, like /status).

Exit codes:
    0 — all required paths present + writable (green/yellow)
    1 — at least one required path missing or non-writable (red) under --check
    2 — usage / IO error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------- #
# Doctrine §3.1: every behavioral change is default-OFF behind a named flag.
# The live model round-trip touches the network + (optionally) a credential,
# so it never runs unless the operator opts in.
# --------------------------------------------------------------------------- #
LIVE_PROBE_ENV = "CEO_INFO_LIVE_PROBE"

# Cheapest model for a minimal-cost latency probe (claude-api skill, 2026-06).
# The round-trip hits /v1/messages/count_tokens, which bills zero tokens, so the
# model id only selects the tokenizer — Haiku keeps the request maximally cheap
# and is overridable for adopters on a different tier.
_DEFAULT_PROBE_MODEL = "claude-haiku-4-5"
_COUNT_TOKENS_URL = "https://api.anthropic.com/v1/messages/count_tokens"
_ANTHROPIC_VERSION = "2023-06-01"

# --- PLAN-135 W5 O8/O11 surfaces ------------------------------------------- #
_MODELS_URL_TMPL = "https://api.anthropic.com/v1/models/{model_id}"
_ADR_149_PATH = REPO_ROOT / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"
_COST_TABLE_PATH = REPO_ROOT / ".claude" / "scripts" / "cost-table.yaml"
_PRICING_PATH = REPO_ROOT / "docs" / "provider-pricing.md"
TRANSCRIPTS_DIR_ENV = "CEO_INFO_TRANSCRIPTS_DIR"

#: Quoted model ids inside the ADR-149 allowlist block — kept REGEX-identical
#: to _lib/effective_config.py (the shared W1 parser). These locals are the
#: FALLBACK for pre-ceremony trees only; when _lib.effective_config imports,
#: its get_model_allowlist() is authoritative (one implementation, O11 rule).
_MODEL_ID_DQ_RE = re.compile(r'"(claude-[A-Za-z0-9.\-]+)"')
_MODEL_ID_SQ_RE = re.compile(r"'(claude-[A-Za-z0-9.\-]+)'")
_FROZENSET_RE = re.compile(r"frozenset\(\s*\{(.*?)\}\s*\)", re.DOTALL)


# --------------------------------------------------------------------------- #
# Path resolution — mirrors ceo-diagnose.py / status.py / audit_emit.py order.
# --------------------------------------------------------------------------- #
def _audit_log_path() -> Optional[Path]:
    """Resolve the audit-log path using the canonical override chain.

    Order (matches ceo-diagnose._resolve_audit_log_path):
      1. ``$CEO_AUDIT_LOG_PATH``           (explicit file override)
      2. ``$CEO_AUDIT_LOG_DIR/audit-log.jsonl``
      3. ``$CLAUDE_PROJECT_DIR``-derived slug under ~/.claude/projects/
      4. legacy ~/.claude/projects/ceo-orchestration/audit-log.jsonl

    Returns the FIRST candidate path (whether or not it exists) so the
    writability probe can report on the directory the framework *would* write
    to, not just a path that already happens to exist.
    """
    explicit = os.environ.get("CEO_AUDIT_LOG_PATH", "")
    if explicit:
        return Path(explicit)
    audit_dir_env = os.environ.get("CEO_AUDIT_LOG_DIR", "")
    if audit_dir_env:
        return Path(audit_dir_env) / "audit-log.jsonl"
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        try:
            abs_path = Path(project_dir).resolve()
            slug = "-" + str(abs_path).lstrip("/").replace("/", "-")
            return Path.home() / ".claude" / "projects" / slug / "audit-log.jsonl"
        except OSError:
            pass
    return Path.home() / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def _memory_dir() -> Path:
    """Resolve the native-memory directory for THIS project.

    ``$CEO_MEMORY_DIR`` overrides; otherwise the CLAUDE_PROJECT_DIR-derived
    slug under ~/.claude/projects/<slug>/memory (matches CLAUDE.md §Quick Ref).
    """
    override = os.environ.get("CEO_MEMORY_DIR", "")
    if override:
        return Path(override)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "") or str(REPO_ROOT)
    try:
        abs_path = Path(project_dir).resolve()
        slug = "-" + str(abs_path).lstrip("/").replace("/", "-")
        return Path.home() / ".claude" / "projects" / slug / "memory"
    except OSError:
        return Path.home() / ".claude" / "projects" / "ceo-orchestration" / "memory"


def _plans_dir() -> Path:
    """Resolve the plans directory (always repo-relative — never adopter-home)."""
    return REPO_ROOT / ".claude" / "plans"


# --------------------------------------------------------------------------- #
# Writability check — non-destructive (does NOT create the target file).
# --------------------------------------------------------------------------- #
def _writable_status(target: Path, *, is_dir: bool) -> Tuple[str, str]:
    """Return (status, note) for whether *target* is present + writable.

    Walks up to the nearest existing ancestor; a path is "writable" if either
    the path itself exists and is writable, or its nearest existing ancestor
    directory is writable (so the framework could create it on first write).
    Never raises — any OSError degrades to ``unknown``.
    """
    try:
        if target.exists():
            if os.access(target, os.W_OK):
                kind = "dir" if target.is_dir() else "file"
                return ("green", f"present + writable ({kind})")
            return ("red", "present but NOT writable")
        # Not present — walk to the nearest existing ancestor.
        ancestor = target.parent
        hops = 0
        while not ancestor.exists() and ancestor != ancestor.parent and hops < 64:
            ancestor = ancestor.parent
            hops += 1
        if not ancestor.exists():
            return ("red", "no existing ancestor directory")
        if os.access(ancestor, os.W_OK):
            what = "dir" if is_dir else "file"
            return ("yellow", f"absent; parent writable (would-create {what})")
        return ("red", f"absent; parent NOT writable ({ancestor})")
    except OSError as exc:
        return ("unknown", f"stat error: {exc.__class__.__name__}")


# --------------------------------------------------------------------------- #
# Effective settings — which settings file won + active env overrides.
# --------------------------------------------------------------------------- #
def _settings_candidates() -> List[Path]:
    """Settings files in precedence order (last wins at runtime)."""
    base = REPO_ROOT / ".claude"
    return [base / "settings.json", base / "settings.local.json"]


def _effective_settings() -> Dict[str, Any]:
    """Report which settings file is the effective source + a hook count.

    Reads only — never writes. A malformed JSON file degrades to an error note
    for that file rather than aborting the whole preflight.
    """
    found: List[Dict[str, Any]] = []
    effective: Optional[str] = None
    hook_count: Optional[int] = None
    for path in _settings_candidates():
        if not path.is_file():
            continue
        entry: Dict[str, Any] = {"path": str(path.relative_to(REPO_ROOT))}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            hooks = data.get("hooks") or {}
            n = 0
            for _event, regs in hooks.items():
                if isinstance(regs, list):
                    for reg in regs:
                        n += len((reg or {}).get("hooks") or [])
            entry["hook_registrations"] = n
            entry["valid_json"] = True
            # settings.local.json (if present + valid) is the effective override.
            effective = entry["path"]
            hook_count = n
        except (OSError, json.JSONDecodeError) as exc:
            entry["valid_json"] = False
            entry["error"] = exc.__class__.__name__
        found.append(entry)
    return {
        "files": found,
        "effective": effective,
        "effective_hook_registrations": hook_count,
    }


def _active_env_overrides() -> Dict[str, str]:
    """Surface the CEO_*/CLAUDE_* env vars that change path/probe resolution.

    Values are reported VERBATIM for the path keys (paths are not secret) but
    any credential-shaped key is reduced to a boolean presence flag so a
    transcript / CI log never echoes a token.
    """
    path_keys = (
        "CEO_AUDIT_LOG_PATH",
        "CEO_AUDIT_LOG_DIR",
        "CEO_MEMORY_DIR",
        "CLAUDE_PROJECT_DIR",
        LIVE_PROBE_ENV,
        "CEO_INFO_PROBE_MODEL",
    )
    out: Dict[str, str] = {}
    for key in path_keys:
        val = os.environ.get(key)
        if val is not None:
            out[key] = val
    # Credential presence ONLY — never the value (no-secret-echo property).
    for cred in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if os.environ.get(cred):
            out[cred] = "<set>"
    return out


# --------------------------------------------------------------------------- #
# Live round-trip — DEFAULT-OFF, fail-open, no-secret-echo.
# --------------------------------------------------------------------------- #
def _default_http_post(
    url: str, headers: Dict[str, str], body: bytes, timeout: float
) -> Tuple[int, bytes]:
    """POST `body` to `url`. Returns (status, body). DI seam for tests.

    Mirrors ceo-cost._http_post: any urllib exception propagates to the caller,
    which treats a raise as "endpoint unavailable" (fail-open).
    """
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() if hasattr(exc, "read") else b""


def probe_live_roundtrip(
    *,
    enabled: bool,
    timeout: float = 8.0,
    http_post: Optional[Callable[[str, Dict[str, str], bytes, float], Tuple[int, bytes]]] = None,
    now: Callable[[], float] = time.monotonic,
) -> Tuple[str, str, Dict[str, Any]]:
    """One cheap model round-trip + latency, gated default-OFF.

    Returns (status, summary, detail). NEVER raises and NEVER echoes the
    credential. The request targets ``/v1/messages/count_tokens`` (bills no
    tokens). When *enabled* is False the probe is skipped with a ``skipped``
    status — the steady state for CI and any run without the opt-in flag.
    """
    if not enabled:
        return (
            "skipped",
            f"live round-trip OFF (set {LIVE_PROBE_ENV}=1 or pass --live)",
            {"enabled": False},
        )
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        return (
            "yellow",
            "live round-trip requested but no ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN set",
            {"enabled": True, "credential": "absent"},
        )
    model = os.environ.get("CEO_INFO_PROBE_MODEL", _DEFAULT_PROBE_MODEL)
    post = http_post or _default_http_post
    # Minimal request: a single 1-token user turn. count_tokens has no
    # max_tokens / output, so this is the cheapest possible round-trip.
    payload = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": "ok"}]}
    ).encode("utf-8")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    start = now()
    try:
        status_code, raw = post(_COUNT_TOKENS_URL, headers, payload, timeout)
    except Exception as exc:  # noqa: BLE001 — fail-open on ANY network/infra error
        return (
            "yellow",
            f"live round-trip failed ({exc.__class__.__name__}) — endpoint unavailable",
            {"enabled": True, "model": model, "error": exc.__class__.__name__},
        )
    elapsed_ms = round((now() - start) * 1000.0, 1)
    detail: Dict[str, Any] = {
        "enabled": True,
        "model": model,
        "http_status": status_code,
        "latency_ms": elapsed_ms,
    }
    if 200 <= status_code < 300:
        input_tokens = None
        try:
            input_tokens = json.loads(raw.decode("utf-8")).get("input_tokens")
        except (ValueError, AttributeError):
            pass
        if input_tokens is not None:
            detail["input_tokens"] = input_tokens
        return ("green", f"round-trip OK in {elapsed_ms} ms (HTTP {status_code})", detail)
    if status_code in (401, 403):
        return ("red", f"auth rejected (HTTP {status_code}) — check credential", detail)
    return ("yellow", f"non-2xx (HTTP {status_code}) in {elapsed_ms} ms", detail)


# --------------------------------------------------------------------------- #
# PLAN-135 W5 O11 — effective-hook-count diff via the SHARED W1 module.
# FAIL-SOFT import ONLY (coupling rule): the live branch must stay green on a
# pre-ceremony tree where _lib/effective_config.py does not exist yet.
# --------------------------------------------------------------------------- #
def _import_effective_config() -> Optional[Any]:
    """try/except import of ``_lib.effective_config`` (W1 ceremony bundle).

    Returns the module or None. NEVER raises — any failure (module absent
    pre-ceremony, broken _lib, import-time error) degrades to None and the
    consumer renders a SKIPPED-pre-ceremony message.
    """
    try:
        import importlib

        hooks_dir = str(REPO_ROOT / ".claude" / "hooks")
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        return importlib.import_module("_lib.effective_config")
    except Exception:
        return None


_HOOKS_DIFF_SKIPPED_SUMMARY = (
    "SKIPPED — _lib.effective_config not importable (pre-ceremony tree; "
    "the shared resolver ships with the PLAN-135 W1 bundle)"
)


def hooks_diff_section(ec: Optional[Any] = None) -> Dict[str, Any]:
    """Diff registered hooks (settings layers) vs effective-on-disk hooks.

    S3's third tripwire surfaced on the preflight CLI — ONE implementation
    (the shared ``_lib.effective_config``), this is only a consumer. A
    registered-but-missing hook script fails open (allow) at runtime, so a
    mismatch here is a silently degraded governance rail (S217/S228 class).
    NEVER raises.
    """
    if ec is None:
        ec = _import_effective_config()
    if ec is None:
        return {"status": "skipped", "summary": _HOOKS_DIFF_SKIPPED_SUMMARY}
    try:
        resolved = ec.resolve_settings(str(REPO_ROOT))
        registered: set = set()
        for layer in resolved.get("layers", []):
            if isinstance(layer, dict) and layer.get("name") in ("project", "local"):
                registered |= set(ec.registered_hook_basenames(layer.get("data") or {}))
        effective_n = ec.count_effective_hooks(str(REPO_ROOT))
        hooks_dir = REPO_ROOT / ".claude" / "hooks"
        missing = sorted(
            name for name in registered
            if not (hooks_dir / name).is_file()
            or not os.access(str(hooks_dir / name), os.R_OK)
        )
        status = "green" if (not missing and effective_n == len(registered)) else "red"
        return {
            "status": status,
            "summary": (
                f"{effective_n}/{len(registered)} registered hooks effective "
                f"on disk" + (f" — MISSING: {missing[:8]}" if missing else "")
            ),
            "registered": len(registered),
            "effective_on_disk": effective_n,
            "missing": missing,
        }
    except Exception as exc:  # noqa: BLE001 — advisory section, fail-soft
        return {
            "status": "unknown",
            "summary": f"hooks diff degraded ({exc.__class__.__name__})",
        }


# --------------------------------------------------------------------------- #
# PLAN-135 W5 O8 — verify-models: ADR-149 allowlist vs the local rate card
# (static, default) + optional live GET /v1/models/<id> (--live + credential).
# --------------------------------------------------------------------------- #
def _parse_allowlist_fallback(text: str) -> List[str]:
    """Pre-ceremony fallback parse of ADR-149 (regex-identical to the W1
    shared parser): ids quoted inside the FIRST ``frozenset({...})`` block,
    falling back to any quoted ``claude-*`` id. Order-preserving, deduped."""
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


def _get_model_allowlist(adr_path: Optional[Path] = None) -> Tuple[List[str], str]:
    """Return (members, source). Prefers the shared W1 parser; degrades to
    the local fallback regex on pre-ceremony trees; ([], 'unavailable') when
    the ADR itself is unreadable. NEVER raises."""
    if adr_path is None:
        ec = _import_effective_config()
        if ec is not None:
            try:
                members = ec.get_model_allowlist(str(REPO_ROOT))
                if members:
                    return members, "_lib.effective_config"
            except Exception:
                pass
        adr_path = _ADR_149_PATH
    try:
        text = Path(adr_path).read_text(encoding="utf-8", errors="replace")
        members = _parse_allowlist_fallback(text)
        if members:
            return members, "local-fallback-parser"
    except OSError:
        pass
    return [], "unavailable"


def _cost_table_models(cost_table_path: Optional[Path] = None) -> List[str]:
    """Model row keys under ``models:`` in cost-table.yaml (mini-YAML: the
    section's 2-space-indented keys). [] on any failure (fail-soft)."""
    path = cost_table_path or _COST_TABLE_PATH
    models: List[str] = []
    try:
        in_models = False
        for raw in Path(path).read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if not line.startswith(" "):
                in_models = line.split(":", 1)[0].strip() == "models"
                continue
            if in_models:
                m = re.match(r"^  ([A-Za-z0-9.\-]+):\s*$", line)
                if m:
                    models.append(m.group(1))
    except OSError:
        return []
    return models


def _provider_pricing_models(pricing_path: Optional[Path] = None) -> List[str]:
    """Model slugs in the provider-pricing.md primary table rows
    (``| Provider | Model | ... |``). [] on any failure (fail-soft)."""
    path = pricing_path or _PRICING_PATH
    models: List[str] = []
    try:
        for raw in Path(path).read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4 or set(cells[0]) <= {"-", " ", ":"}:
                continue
            if cells[0].lower() in ("provider",):
                continue
            models.append(cells[1].lower())
    except OSError:
        return []
    return models


def verify_models_static(
    *,
    adr_path: Optional[Path] = None,
    cost_table_path: Optional[Path] = None,
    pricing_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """O8 static mode: every ADR-149 allowlist member must have a rate-card
    row in BOTH cost-table.yaml and provider-pricing.md (the S227 stale-pin
    pair). Advisory; no network; NEVER raises."""
    try:
        members, source = _get_model_allowlist(adr_path)
        cost_models = set(_cost_table_models(cost_table_path))
        pricing_models = set(_provider_pricing_models(pricing_path))
        rows: List[Dict[str, Any]] = []
        for member in members:
            in_ct = member in cost_models
            in_pp = member.lower() in pricing_models
            rows.append({
                "model": member,
                "in_cost_table": in_ct,
                "in_provider_pricing": in_pp,
                "status": "green" if (in_ct and in_pp) else "yellow",
            })
        if not members:
            status, summary = "yellow", (
                "allowlist unavailable (ADR-149 unreadable/unparseable) — "
                "membership check degraded"
            )
        elif all(r["status"] == "green" for r in rows):
            status = "green"
            summary = (f"{len(rows)}/{len(rows)} allowlist members priced in "
                       f"cost-table.yaml + provider-pricing.md")
        else:
            gaps = [r["model"] for r in rows if r["status"] != "green"]
            status = "yellow"
            summary = f"rate-card gap for allowlist member(s): {gaps}"
        return {
            "mode": "static",
            "status": status,
            "summary": summary,
            "allowlist_source": source,
            "members": rows,
        }
    except Exception as exc:  # noqa: BLE001 — advisory section, fail-soft
        return {
            "mode": "static",
            "status": "unknown",
            "summary": f"verify-models degraded ({exc.__class__.__name__})",
            "allowlist_source": "unavailable",
            "members": [],
        }


def _default_http_get(
    url: str, headers: Dict[str, str], timeout: float
) -> Tuple[int, bytes]:
    """GET `url`. Returns (status, body). DI seam for tests; any urllib
    exception propagates to the caller (treated as endpoint-unavailable)."""
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() if hasattr(exc, "read") else b""


def probe_verify_models_live(
    members: List[str],
    *,
    enabled: bool,
    timeout: float = 8.0,
    http_get: Optional[Callable[[str, Dict[str, str], float], Tuple[int, bytes]]] = None,
) -> Dict[str, Any]:
    """O8 live mode: GET /v1/models/<id> per allowlist member (the Models
    API bills zero tokens — pure metadata). DEFAULT-OFF behind --live +
    credential; Owner-run only (agents/CI stay no-network). NEVER raises and
    NEVER echoes the credential."""
    if not enabled:
        return {
            "status": "skipped",
            "summary": ("live model-existence probe OFF — pass --live "
                        "--verify-models with a credential (Owner-run; "
                        "GET /v1/models/<id> bills zero tokens)"),
            "models": [],
        }
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        return {
            "status": "yellow",
            "summary": ("live probe requested but no ANTHROPIC_API_KEY / "
                        "ANTHROPIC_AUTH_TOKEN set"),
            "models": [],
        }
    get = http_get or _default_http_get
    headers = {"x-api-key": api_key, "anthropic-version": _ANTHROPIC_VERSION}
    results: List[Dict[str, Any]] = []
    for member in members:
        url = _MODELS_URL_TMPL.format(model_id=member)
        row: Dict[str, Any] = {"model": member}
        try:
            status_code, raw = get(url, headers, timeout)
        except Exception as exc:  # noqa: BLE001 — fail-open per member
            row.update(status="yellow",
                       note=f"endpoint unavailable ({exc.__class__.__name__})")
            results.append(row)
            continue
        row["http_status"] = status_code
        if 200 <= status_code < 300:
            row["status"] = "green"
            try:
                payload = json.loads(raw.decode("utf-8"))
                if isinstance(payload, dict):
                    if payload.get("display_name"):
                        row["display_name"] = payload["display_name"]
                    if payload.get("max_tokens") is not None:
                        row["max_tokens"] = payload["max_tokens"]
            except (ValueError, AttributeError):
                pass
        elif status_code == 404:
            row.update(status="red",
                       note="model id NOT FOUND — allowlist member drifted off the API")
        elif status_code in (401, 403):
            row.update(status="red", note="auth rejected — check credential")
        else:
            row.update(status="yellow", note=f"non-2xx (HTTP {status_code})")
        results.append(row)
    if any(r.get("status") == "red" for r in results):
        overall = "red"
    elif any(r.get("status") == "yellow" for r in results):
        overall = "yellow"
    else:
        overall = "green"
    greens = sum(1 for r in results if r.get("status") == "green")
    return {
        "status": overall,
        "summary": f"{greens}/{len(results)} allowlist members live on /v1/models",
        "models": results,
    }


# --------------------------------------------------------------------------- #
# PLAN-135 W5 O11 — cache forensics: local transcript usage state. The
# recurring multi-hour "why is cache_read 0?" hunt (S216/S227) becomes one
# read-only call that also hands the Owner the previous_message_id a live
# diagnostics call needs. This section NEVER touches the network.
# --------------------------------------------------------------------------- #
_CACHE_DIAGNOSE_LIVE_RECIPE = (
    "PENDING-OWNER: POST /v1/messages with body.diagnostics."
    "previous_message_id=<previous_message_id below>; read response "
    "diagnostics.cache_miss_reason + usage.cache_read_input_tokens. "
    "Owner-run only (bills one minimal message; record the quota bucket per "
    "PLAN-135 W5 accounting axes). Verify the diagnostics param shape "
    "against the platform docs first (Doctrine 3: verify-the-knob-routes)."
)

_TRANSCRIPT_TAIL_BYTES = 2_000_000


def _transcripts_dir() -> Path:
    """Resolve the Claude Code transcripts dir for THIS project.

    ``$CEO_INFO_TRANSCRIPTS_DIR`` overrides (tests/ops); otherwise the
    CLAUDE_PROJECT_DIR-derived slug under ~/.claude/projects/<slug>/ —
    transcripts live NEXT TO memory/ + audit-log.jsonl.
    """
    override = os.environ.get(TRANSCRIPTS_DIR_ENV, "")
    if override:
        return Path(override)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "") or str(REPO_ROOT)
    try:
        abs_path = Path(project_dir).resolve()
        slug = "-" + str(abs_path).lstrip("/").replace("/", "-")
        return Path.home() / ".claude" / "projects" / slug
    except OSError:
        return Path.home() / ".claude" / "projects" / "ceo-orchestration"


def _iter_usage_entries(text: str) -> List[Dict[str, Any]]:
    """Extract assistant usage entries from transcript JSONL text (lenient)."""
    entries: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or '"usage"' not in line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict) or "input_tokens" not in usage:
            continue
        cache_read = usage.get("cache_read_input_tokens") or 0
        cache_creation = usage.get("cache_creation_input_tokens")
        if cache_creation is None:
            nested = usage.get("cache_creation")
            if isinstance(nested, dict):
                cache_creation = sum(
                    v for v in nested.values() if isinstance(v, (int, float))
                )
        entries.append({
            "message_id": message.get("id"),
            "request_id": obj.get("requestId"),
            "timestamp": obj.get("timestamp"),
            "input_tokens": usage.get("input_tokens"),
            "cache_read_input_tokens": int(cache_read or 0),
            "cache_creation_input_tokens": int(cache_creation or 0),
        })
    return entries


def cache_diagnose_section(
    transcripts_dir: Optional[Path] = None,
    *,
    max_entries: int = 10,
) -> Dict[str, Any]:
    """O11 static cache forensics over the NEWEST local transcript.

    Returns status green (latest turn read cache), yellow (cache_read=0 on
    the latest turn — the forensic trigger), or skipped (no transcripts).
    Degrades gracefully on every IO/parse failure; NEVER raises; reads only.
    """
    try:
        tdir = Path(transcripts_dir) if transcripts_dir else _transcripts_dir()
        if not tdir.is_dir():
            return {
                "status": "skipped",
                "summary": f"no transcripts dir at {tdir}",
                "live": {"status": "pending-owner",
                         "recipe": _CACHE_DIAGNOSE_LIVE_RECIPE},
            }
        candidates = [
            p for p in tdir.glob("*.jsonl")
            if not p.name.startswith("audit-log")
        ]
        if not candidates:
            return {
                "status": "skipped",
                "summary": f"no transcript *.jsonl under {tdir}",
                "live": {"status": "pending-owner",
                         "recipe": _CACHE_DIAGNOSE_LIVE_RECIPE},
            }
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
        size = newest.stat().st_size
        with open(newest, "rb") as fh:
            if size > _TRANSCRIPT_TAIL_BYTES:
                fh.seek(size - _TRANSCRIPT_TAIL_BYTES)
                raw = fh.read().decode("utf-8", errors="ignore")
                raw = raw.split("\n", 1)[-1]  # drop the partial first line
            else:
                raw = fh.read().decode("utf-8", errors="ignore")
        entries = _iter_usage_entries(raw)
        if not entries:
            return {
                "status": "skipped",
                "summary": f"no usage entries parsed from {newest.name}",
                "transcript": str(newest),
                "live": {"status": "pending-owner",
                         "recipe": _CACHE_DIAGNOSE_LIVE_RECIPE},
            }
        zero_streak = 0
        for entry in reversed(entries):
            if entry["cache_read_input_tokens"] == 0:
                zero_streak += 1
            else:
                break
        latest = entries[-1]
        status = "green" if latest["cache_read_input_tokens"] > 0 else "yellow"
        summary = (
            f"latest turn cache_read={latest['cache_read_input_tokens']} "
            f"cache_write={latest['cache_creation_input_tokens']} "
            f"(zero-read streak: {zero_streak} of last {len(entries)} turns)"
        )
        return {
            "status": status,
            "summary": summary,
            "transcript": str(newest),
            "previous_message_id": latest.get("message_id"),
            "zero_read_streak": zero_streak,
            "entries_scanned": len(entries),
            "recent": entries[-max_entries:],
            "live": {"status": "pending-owner",
                     "recipe": _CACHE_DIAGNOSE_LIVE_RECIPE},
        }
    except Exception as exc:  # noqa: BLE001 — advisory section, fail-soft
        return {
            "status": "unknown",
            "summary": f"cache diagnose degraded ({exc.__class__.__name__})",
            "live": {"status": "pending-owner",
                     "recipe": _CACHE_DIAGNOSE_LIVE_RECIPE},
        }


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
def build_info(
    *,
    live: bool,
    http_post: Optional[Callable] = None,
    verify_models: bool = False,
    cache_diagnose: bool = False,
    hooks_diff: bool = False,
) -> Dict[str, Any]:
    """Build the full preflight dict. Pure function of env + filesystem + DI seam.

    The PLAN-135 W5 advisory sections (``verify_models`` / ``cache_diagnose`` /
    ``hooks_diff``) are OPT-IN: they only run when their flag is set, so the
    default preflight keeps its original cheap path + JSON shape. Each is
    fail-soft — present-but-degraded is the worst case, never a traceback, and
    NONE of them change ``exit_nonzero`` (advisory, per the doctrine).
    """
    audit_path = _audit_log_path()
    memory_path = _memory_dir()
    plans_path = _plans_dir()

    paths: List[Dict[str, Any]] = []
    required_red = False
    for name, target, is_dir, required in (
        ("audit_log", audit_path, False, True),
        ("memory_dir", memory_path, True, True),
        ("plans_dir", plans_path, True, True),
    ):
        status, note = _writable_status(target, is_dir=is_dir)
        if required and status == "red":
            required_red = True
        paths.append(
            {
                "name": name,
                "path": str(target),
                "required": required,
                "status": status,
                "note": note,
            }
        )

    live_status, live_summary, live_detail = probe_live_roundtrip(
        enabled=live, http_post=http_post
    )

    overall = "red" if required_red else "green"
    if overall != "red" and any(p["status"] == "yellow" for p in paths):
        overall = "yellow"

    info: Dict[str, Any] = {
        "overall": overall,
        "exit_nonzero": required_red,
        "paths": paths,
        "settings": _effective_settings(),
        "env_overrides": _active_env_overrides(),
        "live_probe": {
            "status": live_status,
            "summary": live_summary,
            "detail": live_detail,
        },
        "repo_root": str(REPO_ROOT),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # --- PLAN-135 W5 advisory sections (opt-in; never affect exit_nonzero) --- #
    if hooks_diff:
        info["hooks_diff"] = hooks_diff_section()
    if verify_models:
        section = verify_models_static()
        # The live GET /v1/models per member is Owner-run only (--live + key);
        # default-OFF respects the no-network rule for agents + CI.
        section["live"] = probe_verify_models_live(
            [r["model"] for r in section.get("members", [])], enabled=live
        )
        info["verify_models"] = section
    if cache_diagnose:
        info["cache_diagnose"] = cache_diagnose_section()

    return info


_MARK = {"green": "OK ", "yellow": "WARN", "red": "FAIL", "unknown": "?   ", "skipped": "skip"}


def render_human(data: Dict[str, Any]) -> str:
    """Render the preflight dict as a <40-line human block."""
    out: List[str] = []
    out.append(f"## ceo info --check  ({data['generated_at']})")
    out.append(f"**Overall:** {_MARK.get(data['overall'], '?')} {data['overall']}")
    out.append("")
    out.append("### Paths")
    for p in data["paths"]:
        req = "required" if p["required"] else "optional"
        out.append(f"  [{_MARK.get(p['status'], '?')}] {p['name']:<12} {p['note']}")
        out.append(f"        {p['path']}  ({req})")
    out.append("")
    st = data["settings"]
    out.append("### Effective settings")
    if st["effective"]:
        out.append(
            f"  source: {st['effective']}  "
            f"({st['effective_hook_registrations']} hook registrations)"
        )
    else:
        out.append("  source: (none found — no settings.json)")
    for f in st["files"]:
        flag = "valid" if f.get("valid_json") else f"INVALID ({f.get('error', '?')})"
        out.append(f"    - {f['path']}: {flag}")
    out.append("")
    env = data["env_overrides"]
    out.append("### Active env overrides")
    if env:
        for k, v in env.items():
            out.append(f"  {k}={v}")
    else:
        out.append("  (none — all defaults)")
    out.append("")
    lp = data["live_probe"]
    out.append(f"### Live round-trip: [{_MARK.get(lp['status'], '?')}] {lp['summary']}")

    # --- PLAN-135 W5 advisory sections (only when their flag was passed) ----- #
    hd = data.get("hooks_diff")
    if hd is not None:
        out.append("")
        out.append(f"### Hooks diff: [{_MARK.get(hd['status'], '?')}] {hd['summary']}")
    vm = data.get("verify_models")
    if vm is not None:
        out.append("")
        out.append(f"### verify-models (static): [{_MARK.get(vm['status'], '?')}] {vm['summary']}")
        for r in vm.get("members", []):
            ct = "ct" if r["in_cost_table"] else "--"
            pp = "pp" if r["in_provider_pricing"] else "--"
            out.append(f"  [{_MARK.get(r['status'], '?')}] {r['model']:<22} {ct} {pp}")
        live = vm.get("live") or {}
        if live:
            out.append(f"  live: [{_MARK.get(live.get('status', 'skipped'), '?')}] {live.get('summary', '')}")
    cd = data.get("cache_diagnose")
    if cd is not None:
        out.append("")
        out.append(f"### cache-diagnose: [{_MARK.get(cd['status'], '?')}] {cd['summary']}")
        if cd.get("previous_message_id"):
            out.append(f"  previous_message_id: {cd['previous_message_id']}")
        live = cd.get("live") or {}
        if live.get("recipe"):
            out.append(f"  {live['recipe']}")
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint. Exit non-zero under --check when a required path is RED."""
    parser = argparse.ArgumentParser(description="ceo info — live preflight + effective config")
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if a required path is missing/non-writable")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--live", action="store_true",
                        help=f"opt into the live model round-trip (or set {LIVE_PROBE_ENV}=1)")
    parser.add_argument("--verify-models", dest="verify_models", action="store_true",
                        help="O8: ADR-149 allowlist vs the local rate card (static; "
                             "+--live GETs /v1/models/<id> per member, Owner-run)")
    parser.add_argument("--cache-diagnose", dest="cache_diagnose", action="store_true",
                        help="O11: local transcript cache forensics (previous_message_id + "
                             "cache_read=0 streak; the live diagnostics call is PENDING-OWNER)")
    parser.add_argument("--hooks-diff", dest="hooks_diff", action="store_true",
                        help="O11: registered-vs-effective hook-count diff via the shared "
                             "_lib.effective_config (SKIPPED on a pre-ceremony tree)")
    args = parser.parse_args(argv)

    live = bool(args.live) or os.environ.get(LIVE_PROBE_ENV, "") == "1"

    try:
        data = build_info(
            live=live,
            verify_models=bool(args.verify_models),
            cache_diagnose=bool(args.cache_diagnose),
            hooks_diff=bool(args.hooks_diff),
        )
    except Exception as exc:  # noqa: BLE001 — preflight must never traceback
        sys.stderr.write(f"ceo-info: internal error ({exc.__class__.__name__})\n")
        return 2

    if args.json:
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    else:
        print(render_human(data))

    # --check turns a RED required-path into a non-zero exit (CI gate). Without
    # --check the command stays advisory (always 0) like /status + /ceo-boot.
    if args.check and data["exit_nonzero"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
