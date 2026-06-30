#!/usr/bin/env python3
"""Codex CLI subprocess wrapper for Pair-Rail dispatch.

Used by the Phase 4 promotion gate + manual debug to invoke Codex with
deterministic timeout + retry semantics + audit emission. Wraps
``subprocess.run([codex, ...])`` with:

- Timeout classification per ``_lib.adapters.codex._classify_prompt_complexity``
  (R1 C7 — 75s simple / 240s audit).
- Retry-on-timeout with deadline doubling (1 retry budget per call).
- Egress redaction via ``_lib.codex_egress_redact`` (R1 S-Sec-1).
- Audit emission of ``wall_clock_s`` + ``retry_at_timeout_s`` (R1 C7).
- Argv constructed via ``codex.make_invoke_command()`` which DELEGATES to
  the non-kernel ``_lib.codex_cli_shape`` builder (PLAN-142 D2 — single
  source of truth for the codex-cli 0.139 argv shape).

PLAN-142: on codex-cli 0.139 the reviewer verdict is written to a private
last-message output file (``-o`` in the helper), NOT to stdout. This wrapper
creates a 0700 tmpdir, passes its path to the builder, reads the file back,
redacts it, and parses the verdict from that content. stdin is closed
(``DEVNULL``) — the prompt is a trailing positional in the argv, never piped.

CLI invocation (Phase 4 promotion gate, manual debug):

    python3 .claude/scripts/codex_invoke.py \\
        --model gpt-5-codex \\
        --sandbox read-only \\
        "review file foo.py for hardcoded secrets"

Exit codes:
  0  — Codex returned cleanly (verdict ∈ {PASS, ADVISORY, BLOCK})
  1  — Codex returned but parse error (advisory ADVISORY emitted)
  2  — Timeout exceeded after retry
  3  — subprocess error (binary missing, OS error)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add hook lib path for imports.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _classify_transport(kind: str) -> str:
    """PLAN-133 B5 — best-effort closed-enum transport-error class.

    codex_invoke is a SUBPROCESS wrapper (no HTTP status), so only timeout/network
    are reachable — never a quota/credit/auth ceiling (those are billing signals
    that this path cannot observe). This is an INLINE, stdlib-only re-statement of
    ``error_taxonomy.classify_transport_error`` for exactly those reachable kinds:
    cross-importing the wave3 taxonomy module would pull a non-stdlib dependency
    into this subprocess wrapper for no gain (the HTTP/billing classes it adds are
    structurally unreachable here). Byte-identical to the taxonomy for the
    timeout/network tags; anything else degrades to "unknown" (fail-open)."""
    try:
        k = str(kind or "").strip().lower()
        if k in ("timeout", "timed_out", "deadline"):
            return "timeout"
        if k in ("network", "url_error", "urlerror", "os_error", "oserror", "dns"):
            return "network"
        return "unknown"
    except Exception:
        return "unknown"


def invoke_codex(
    prompt: str,
    *,
    model: Optional[str] = None,
    sandbox_mode: str = "read-only",
    timeout_s: Optional[int] = None,
    enable_retry: bool = True,
) -> Tuple[Dict, float, Optional[float]]:
    """Invoke Codex CLI with timeout + retry semantics.

    Args:
        prompt: prompt text.
        model: Codex reviewer model. Default ``None`` → the helper OMITS
            --model so the Codex account uses its own default (PLAN-142 D5,
            smoke-resolved: the Owner's ChatGPT account serves only gpt-5.5;
            forcing a catalog id returns HTTP 400). Pass an explicit id only
            when the account is known to serve it.
        sandbox_mode: read-only / workspace-write / danger-full-access.
        timeout_s: explicit timeout. If None, derived via classifier.
        enable_retry: if True (default), retry once on timeout with doubled
            deadline. If False, single attempt.

    Returns:
        ``(verdict_envelope, wall_clock_s, retry_at_timeout_s)`` tuple:
            - verdict_envelope: dict from ``codex.parse_verdict()`` with keys
              verdict / findings / summary / parse_error.
            - wall_clock_s: total wall-clock duration in seconds.
            - retry_at_timeout_s: seconds until retry kicked, or None.

    NEVER raises — exceptions are caught and surfaced as verdict=ADVISORY
    with parse_error.
    """
    try:
        from _lib.adapters import codex as _codex
        from _lib import codex_egress_redact as _redact
    except Exception as e:
        return (
            {
                "verdict": "ADVISORY",
                "findings": [],
                "summary": "",
                "parse_error": f"[invoke] adapter import failed: {type(e).__name__}",
            },
            0.0,
            None,
        )

    # PLAN-084 Wave 0.5 (ADR-114 + AC9 — Codex egress redaction symmetry).
    # Apply redact_outgoing BEFORE the prompt reaches Codex via subprocess.
    # PLAN-112-FOLLOWUP-codex-egress-proof-telemetry (F-7.9): findings-capturing
    # form + emit positive-proof telemetry on EVERY outbound redaction.
    _egress_bytes = len(prompt.encode("utf-8", "replace")) if isinstance(prompt, str) else 0
    prompt, _egress_findings = _redact.redact_outgoing_with_findings(prompt)
    try:  # fail-OPEN — wraps ONLY the emit, never the redact above
        from _lib import audit_emit as _ae
        _ae.emit_pair_rail_outgoing_redaction_applied(
            signal="outbound",
            match_count=len(_egress_findings),
            bytes_scanned=_egress_bytes,
            callsite="codex_invoke.py:invoke_codex:outbound",
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:
        pass

    # PLAN-142: the verdict is written to a private last-message output file,
    # not stdout. Own a 0700 tmpdir; the builder receives its path. The
    # try/finally below covers ONLY the tmpfile lifecycle (subprocess + read);
    # the inbound redact + emit + parse run AFTER it, on the in-memory content,
    # so the fail-OPEN emit is never nested under a cleanup try (AC5).
    tmp_dir = tempfile.mkdtemp(prefix="ceo_codexinvoke_")
    try:
        os.chmod(tmp_dir, 0o700)
    except OSError:
        pass
    out_path = os.path.join(tmp_dir, "codex_last_message.json")

    def _cleanup() -> None:
        try:
            os.unlink(out_path)
        except OSError:
            pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    raw_last_message: Optional[str] = None
    wall_clock = 0.0
    retry_at: Optional[float] = None
    try:
        # Build argv via the canonical helper (delegates to codex_cli_shape).
        try:
            argv = _codex.make_invoke_command(
                prompt=prompt,
                model=model,
                sandbox_mode=sandbox_mode,
                timeout_s=timeout_s,
                output_last_message_path=out_path,
            )
        except Exception as e:
            return (
                {
                    "verdict": "ADVISORY",
                    "findings": [],
                    "summary": "",
                    "parse_error": f"[invoke] argv build failed: {type(e).__name__}: {e}",
                },
                0.0,
                None,
            )

        # Prepend the binary name (caller passes argv to subprocess).
        full_argv = ["codex"] + list(argv)
        deadline = timeout_s if timeout_s is not None else _codex._resolve_timeout_s(prompt)

        started_at = time.monotonic()

        try:
            proc = subprocess.run(
                full_argv,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=deadline,
                check=False,
            )
        except subprocess.TimeoutExpired:
            if enable_retry:
                retry_at = time.monotonic() - started_at
                try:
                    proc = subprocess.run(
                        full_argv,
                        stdin=subprocess.DEVNULL,
                        capture_output=True,
                        text=True,
                        timeout=deadline * 2,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    wall_clock = time.monotonic() - started_at
                    return (
                        {
                            "verdict": "ADVISORY",
                            "findings": [],
                            "summary": "",
                            "parse_error": f"[invoke] timeout after retry ({deadline*2}s)",
                            "error_class": _classify_transport("timeout"),
                        },
                        wall_clock,
                        retry_at,
                    )
                except Exception as e:
                    wall_clock = time.monotonic() - started_at
                    return (
                        {
                            "verdict": "ADVISORY",
                            "findings": [],
                            "summary": "",
                            "parse_error": f"[invoke] retry subprocess error: {type(e).__name__}",
                            "error_class": _classify_transport("network"),
                        },
                        wall_clock,
                        retry_at,
                    )
            else:
                wall_clock = time.monotonic() - started_at
                return (
                    {
                        "verdict": "ADVISORY",
                        "findings": [],
                        "summary": "",
                        "parse_error": f"[invoke] timeout ({deadline}s) — retry disabled",
                        "error_class": _classify_transport("timeout"),
                    },
                    wall_clock,
                    None,
                )
        except Exception as e:
            wall_clock = time.monotonic() - started_at
            return (
                {
                    "verdict": "ADVISORY",
                    "findings": [],
                    "summary": "",
                    "parse_error": f"[invoke] subprocess error: {type(e).__name__}",
                    "error_class": _classify_transport("network"),
                },
                wall_clock,
                None,
            )

        wall_clock = time.monotonic() - started_at

        # PLAN-142: read the verdict from the last-message output file (not
        # stdout). A non-zero exit or an unreadable file degrades to ADVISORY
        # (fail-open — never block a dispatch decision).
        if proc.returncode != 0:
            return (
                {
                    "verdict": "ADVISORY",
                    "findings": [],
                    "summary": "",
                    "parse_error": (
                        f"[invoke] codex exit={proc.returncode}; stderr_head="
                        f"{(proc.stderr or '')[:240]!r}"
                    ),
                },
                wall_clock,
                retry_at,
            )
        try:
            with open(out_path, "r", encoding="utf-8", errors="replace") as _f:
                raw_last_message = _f.read()
        except OSError as e:
            return (
                {
                    "verdict": "ADVISORY",
                    "findings": [],
                    "summary": "",
                    "parse_error": f"[invoke] last-message unreadable: {type(e).__name__}",
                },
                wall_clock,
                retry_at,
            )
    finally:
        _cleanup()

    # Tmpfile is gone; the content is captured in memory. Egress-redact the
    # last-message BEFORE parsing — defensive layering ensures secrets never
    # reach the verdict envelope. This runs OUTSIDE the cleanup try so the
    # fail-OPEN emit below is not nested under a non-except try (AC5).
    if raw_last_message is None:
        return (
            {
                "verdict": "ADVISORY",
                "findings": [],
                "summary": "",
                "parse_error": "[invoke] last-message missing after exit-0",
            },
            wall_clock,
            retry_at,
        )

    _in_bytes = len(raw_last_message.encode("utf-8", "replace"))
    redacted_last_message, _in_findings = _redact.redact_with_findings(raw_last_message)
    try:  # fail-OPEN — wraps ONLY the emit
        from _lib import audit_emit as _ae
        _ae.emit_codex_egress_redacted(
            signal="inbound",
            match_count=len(_in_findings),
            bytes_scanned=_in_bytes,
            callsite="codex_invoke.py:invoke_codex:inbound",
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:
        pass

    # Parse verdict from the structured last-message object.
    verdict = _codex.parse_verdict(redacted_last_message)
    return verdict, wall_clock, retry_at


def emit_audit(
    *,
    verdict: Dict,
    wall_clock_s: float,
    retry_at_timeout_s: Optional[float],
    pair_id: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a Pair-Rail audit event for this Codex invocation.

    Currently routes through the existing ``pair_rail_review_passed``
    or ``pair_rail_codex_unavailable`` emitters (Phase 1 narrow). The
    full Pair-Rail Cases A-F asymmetric emission lands in Phase 3
    (`pair_rail_case_emit`).
    """
    try:
        from _lib import audit_emit as _audit
    except Exception:
        return

    if verdict.get("parse_error"):
        if hasattr(_audit, "emit_pair_rail_codex_unavailable"):
            try:
                _audit.emit_pair_rail_codex_unavailable(
                    target_path="<invoke>",
                    tool_name="codex_invoke.py",
                    reason="parse_error",
                    session_id=session_id,
                    project=project,
                )
            except Exception:
                pass
        return

    # Phase 1 narrow path: emit pair_rail_review_passed for clean returns.
    # Phase 3 will replace with pair_rail_case_emit (Cases A-F).
    if verdict.get("verdict") == "PASS" and hasattr(_audit, "emit_pair_rail_review_passed"):
        try:
            import hashlib as _hashlib
            stdout_sha = _hashlib.sha256(
                str(verdict.get("summary", "")).encode("utf-8")
            ).hexdigest()
            _audit.emit_pair_rail_review_passed(
                target_path="<invoke>",
                tool_name="codex_invoke.py",
                codex_duration_ms=int(wall_clock_s * 1000),
                codex_response_sha256=stdout_sha,
                session_id=session_id,
                project=project,
            )
        except Exception:
            pass


def _main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Codex CLI subprocess wrapper")
    parser.add_argument("--model", default=None)
    parser.add_argument("--sandbox", default="read-only", dest="sandbox_mode")
    parser.add_argument("--timeout", type=int, default=None, dest="timeout_s")
    parser.add_argument("--no-retry", action="store_true", dest="no_retry")
    parser.add_argument("prompt", nargs="?", default="")
    args = parser.parse_args(argv)

    if not args.prompt:
        parser.print_usage()
        sys.stderr.write("\nERROR: prompt argument required\n")
        return 3

    verdict, wall_clock, retry_at = invoke_codex(
        prompt=args.prompt,
        model=args.model,
        sandbox_mode=args.sandbox_mode,
        timeout_s=args.timeout_s,
        enable_retry=not args.no_retry,
    )

    output = {
        "verdict": verdict,
        "wall_clock_s": round(wall_clock, 3),
        "retry_at_timeout_s": (
            round(retry_at, 3) if retry_at is not None else None
        ),
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False, indent=2) + "\n")

    if verdict.get("parse_error"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
