#!/usr/bin/env python3
"""PreToolUse hook: scan Read tool input for prompt-injection patterns.

Sprint 5 Phase 5 (B.4). Optional, advisory. Always allows the read.
Emits a `systemMessage` if matches found, plus an `injection_flag`
audit event so `audit-query.py vetoes` and `metrics` can surface the
aggregate.

## Wire-up

This hook is opt-in. To enable, add the following PreToolUse stanza to
`.claude/settings.json`:

    {
      "matcher": "Read",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_read_injection.py",
          "timeout": 5,
          "statusMessage": "Scanning read content for injection patterns..."
        }
      ]
    }

It is **not** wired into the dogfood `settings.json` by default — Read
patterns are noisy and most projects won't want the systemMessage.
Adopters who care about model-prompt safety can flip it on.

## Safety properties

1. Always allows UNLESS CEO_UNICODE_HARDBLOCK=1 and an invisible-unicode
   detection fires (PLAN-133 A2). Default (flag unset) returns `decision: allow`
   and never blocks.
2. Fail-open: any exception → allow without systemMessage.
3. Reads the `tool_input.file_path` (PreToolUse Read), opens it, scans.
4. Skips paths matching common vendor / generated prefixes (node_modules,
   vendor, third_party, *.patch, *.diff) to reduce noise.
5. Audit emission wrapped in try/except (advisory observability).

## Relationship to the G1 BLOCKING validator (PLAN-133)

This hook is **advisory** — it always allows and only emits a
``systemMessage`` + ``injection_flag``. It is NOT the trust gate for the
persistent-instructions (MOIM) channel. The MOIM channel uses a SEPARATE
**fail-CLOSED** validator, ``_lib.guardrail_validator``, which returns
``decision="block"`` on an injection hit or oversize and is consumed at
session boot by ``SessionStart.py``. Do not route MOIM content through THIS
advisory hook (it never blocks). See ``_lib/guardrail_validator.py``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Make the local `_lib` importable
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# PLAN-133 G1 — re-export the BLOCKING MOIM validator so the two injection
# surfaces (advisory-here vs blocking-there) are discoverable from one module.
# This is an import-only convenience; it changes NO behavior of this hook.
try:  # pragma: no cover — import convenience, fail-open
    from _lib import guardrail_validator as moim_validator  # noqa: F401
except Exception:  # pragma: no cover
    moim_validator = None  # type: ignore

# Make .claude/scripts/ importable for scan-injection.py
_SCRIPTS_DIR = _HOOKS_DIR.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# Paths-filter: skip noisy / vendor content
_SKIP_PREFIXES = (
    "node_modules/",
    "vendor/",
    "third_party/",
    ".git/",
    "dist/",
    "build/",
)
_SKIP_SUFFIXES = (
    ".patch",
    ".diff",
    ".min.js",
    ".min.css",
    ".lock",
)


def _should_skip(path_str: str) -> bool:
    """True if this path matches a skip rule."""
    p = path_str.replace("\\", "/")
    # Compare against suffix list
    lower = p.lower()
    if any(lower.endswith(suf) for suf in _SKIP_SUFFIXES):
        return True
    # Compare against substring of any path segment
    for prefix in _SKIP_PREFIXES:
        if f"/{prefix}" in p or p.startswith(prefix):
            return True
    return False


def _emit_allow(system_message: Optional[str] = None) -> str:
    """Build the JSON output for an allow decision.

    Top-level {"decision":"allow"} fails the Claude Code hook schema
    (decision enum is "approve"|"block"). Emit empty {} or just
    {"systemMessage": ...} for advisory banners.
    """
    out: Dict[str, Any] = {}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _scan_read_unicode(content: str, file_path: str, env=None) -> Optional[str]:
    """PLAN-133 A2 — fail-CLOSED invisible-unicode guard on Read content.

    Mirrors the §6a ``_scan_skill_content_unicode`` form for the READ direction.
    Runs the existing ``spec_context_sanitizer.sanitize`` (the SAME single filter
    as spawn / skill-write) over the read content; when CEO_UNICODE_HARDBLOCK=='1'
    AND a detection fires (control / bidi / zero-width / U+E0000–E007F Tag-block),
    returns a block-reason string. Otherwise advisory — emits the
    invisible_unicode_blocked breadcrumb with enforced=0 (measure-first) and returns
    None. Default-OFF (the flag unset preserves this hook's always-allow contract).
    Master kill CEO_SOTA_DISABLE=1 forces advisory. Fail-OPEN on any infra error.
    """
    try:
        from _lib import spec_context_sanitizer as _scs  # noqa: E402
    except Exception:  # pragma: no cover - fail-open
        return None
    try:
        if not content:
            return None
        src_env = env if env is not None else os.environ
        if (src_env.get("CEO_SOTA_DISABLE") or "").strip() == "1":
            enforce = False
        else:
            enforce = (src_env.get("CEO_UNICODE_HARDBLOCK") or "").strip() == "1"
            # Prefer the trusted_env snapshot when available (mirror A1/§5b).
            try:
                from _lib import trusted_env as _te  # noqa: E402
                _snap = _te.get_trusted("CEO_UNICODE_HARDBLOCK")
                if _snap is not None:
                    enforce = (_snap or "").strip() == "1"
            except Exception:  # pragma: no cover
                pass

        result = _scs.sanitize(content)
        count = _scs.invisible_unicode_count(result)
        if count <= 0:
            return None
        unicode_class = _scs.classify_invisible_unicode(result)

        try:
            from _lib import audit_emit as _ae  # noqa: E402
            _ae.emit_generic(
                "invisible_unicode_blocked",
                surface="skill_read",
                unicode_class=unicode_class,
                char_count=int(count),
                enforced=1 if enforce else 0,
            )
        except Exception:  # pragma: no cover - fail-open
            pass

        if not enforce:
            return None
        return (
            "READ-BLOCKED: invisible_unicode_blocked: this read content contains "
            f"{count} invisible/smuggling character(s) (class={unicode_class}: "
            "control / bidi / zero-width / Unicode-Tags-block). Read content is "
            "loaded into the model; hidden control/bidi/Tag-block characters are "
            "rejected fail-CLOSED. To run advisory-only, unset CEO_UNICODE_HARDBLOCK."
        )
    except Exception:  # pragma: no cover - fail-open invariant
        return None


def _try_emit_audit(
    *,
    source: str,
    family_counts: Dict[str, int],
    match_count: int,
    bytes_scanned: int,
    snippet: str,
    truncated: bool,
    session_id: str = "",
) -> None:
    """Best-effort audit emit. Never raises."""
    try:
        from _lib.audit_emit import emit_injection_flag
        emit_injection_flag(
            source=source,
            family_counts=family_counts,
            match_count=match_count,
            bytes_scanned=bytes_scanned,
            triggered_by_tool="Read",
            snippet_preview=snippet,
            truncated=truncated,
            session_id=session_id,
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return


def main() -> int:
    """Read PreToolUse payload, scan, emit allow + optional systemMessage.

    PLAN-006 Phase 1 migration (ADR-014): Adapter Layer I/O. Preserves
    byte-identical stdout (same key order, same JSON serializer).
    """
    from _lib.adapters import claude as _claude_adapter  # noqa: E402

    # PLAN-045 F-10-03 — kill-switch. Set CEO_READ_INJECTION_SCAN=0 to
    # short-circuit the hook (allow without scanning). Any other value
    # (including empty / unset / "1" / "true") enables scanning. This
    # matches the ADR-057 output_scan per-family kill-switch convention.
    if os.environ.get("CEO_READ_INJECTION_SCAN") == "0":
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
    except Exception:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    if event.parse_error:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    file_path = event.file_path or ""
    session_id = event.session_id or ""

    if not file_path:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    if _should_skip(file_path):
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    # Resolve to absolute path. If file doesn't exist, just allow.
    p = Path(file_path)
    if not p.is_file():
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    # PLAN-025 F-sec-010: bound the scan target to repo root. An agent
    # that somehow references a path outside the repo (e.g. via symlink
    # or absolute traversal) would otherwise leak content from unrelated
    # filesystems into the injection scanner context. Resolve + check
    # containment; if outside, allow-silently without scanning.
    try:
        resolved_p = p.resolve()
        repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()
        # Python 3.9 compat: is_relative_to is 3.9+ but simulated via
        # relative_to() + except for older environments. The framework
        # targets Python 3.9+ per ADR-002.
        try:
            resolved_p.relative_to(repo_root)
        except ValueError:
            sys.stdout.write(_emit_allow() + "\n")
            return 0
    except (OSError, RuntimeError):
        # resolve() can raise OSError on broken symlinks; RuntimeError
        # on recursive symlinks. Fail-open (advisory hook).
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    # Import scanner lazily so a packaging issue doesn't break the hook.
    # PLAN-087 Wave C.2 — sys.modules early-exit: when this module is invoked
    # from an in-process caller (tests, library callers) repeatedly, the
    # importlib machinery is pure overhead because the previously-loaded
    # module is still registered in sys.modules. Subprocess-per-call hook
    # invocations do NOT benefit (each subprocess has a fresh sys.modules),
    # but the check is free and harmless on the subprocess path.
    try:
        mod = sys.modules.get("scan_injection_mod")
        if mod is None:
            # scan-injection.py uses a dash; import via importlib.
            # NOTE: register in sys.modules BEFORE exec_module so PEP 563
            # (`from __future__ import annotations`) dataclass type
            # resolution can find the module via cls.__module__.
            import importlib.util
            scan_path_obj = _SCRIPTS_DIR / "scan-injection.py"
            spec = importlib.util.spec_from_file_location("scan_injection_mod", scan_path_obj)
            if spec is None or spec.loader is None:
                sys.stdout.write(_emit_allow() + "\n")
                return 0
            mod = importlib.util.module_from_spec(spec)
            sys.modules["scan_injection_mod"] = mod
            spec.loader.exec_module(mod)
    except Exception:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    try:
        result = mod.scan_path(p)
    except Exception:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    # PLAN-133 A2 — invisible-unicode guard on Read content. When
    # CEO_UNICODE_HARDBLOCK=1 AND the read content carries invisible/smuggling
    # unicode (control / bidi / zero-width / U+E0000–E007F Tag-block), a detection
    # becomes a fail-CLOSED block. Default behavior unchanged (advisory) when the
    # flag is unset. Fail-open.
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        _uni = _scan_read_unicode(content, file_path)  # helper mirrors §6a
        if _uni is not None:
            # block via the contract (this hook normally only advises; the
            # block is gated by CEO_UNICODE_HARDBLOCK so default behavior is
            # preserved).
            from _lib.adapters import claude as _ca
            from _lib import contract as _ct
            _ca.emit_decision(_ct.block(_uni))
            return 0
    except Exception:
        pass

    if not result.matched:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    # Build a short systemMessage describing the families that hit
    families = ", ".join(
        f"{fam}({n})"
        for fam, n in sorted(result.family_counts.items(), key=lambda kv: -kv[1])
    )
    msg = (
        f"⚠ check_read_injection: {len(result.matches)} potential injection "
        f"pattern(s) found in '{file_path}': {families}. "
        "Advisory only — proceed with caution if rendering this content into "
        "an LLM prompt."
    )

    # Emit audit event (fail-open)
    snippet = result.matches[0].snippet if result.matches else ""
    _try_emit_audit(
        source=str(p),
        family_counts=result.family_counts,
        match_count=len(result.matches),
        bytes_scanned=result.bytes_scanned,
        snippet=snippet,
        truncated=result.truncated,
        session_id=session_id,
    )

    sys.stdout.write(_emit_allow(system_message=msg) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
