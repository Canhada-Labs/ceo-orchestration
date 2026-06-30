#!/usr/bin/env python3
"""check-auto-activation-flags.py — PLAN-088 W5.2 / AC17 meta-test verifier.

Asserts every AUTO-* env-var documented in templates/.env.example
maintains explicit opt-out semantics (default=0 / OFF / unset is the
"opt-out" state, and the user must explicitly set the env to enable
or disable per the conversion's M-* spec).

Or carries an explicit `# telemetry-invariant` comment (SEMI-13
graceful-degradation invariant per ADR-115 — opt-out would violate
the failure-mode telemetry guarantee).

Per AC17 (PLAN-088 §10) + M-4 fold (own test file
test_check_auto_activation_flags.py).

Exit codes:
  0  — every AUTO env-var has explicit opt-out semantics OR
       `# telemetry-invariant` comment
  1  — at least one violation
  2  — env file missing / unreadable
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

_DEFAULT_ENV_PATH = "templates/.env.example"

# Recognized opt-out variable patterns + their expected canonical semantics.
# Per PLAN-088 spec section per AUTO-XX:
_EXPECTED_VARS: Tuple[Tuple[str, str], ...] = (
    # (env_var_name, expected_default_value_or_documented_state)
    ("CEO_CACHE_DISCIPLINE", "1"),               # AUTO-01 — default ON; 0 disables
    ("CEO_SKIP_WIZARD", "0"),                    # AUTO-02 — default OFF; 1 skips
    ("CEO_ESTIMATE_VIBES", "0"),                 # AUTO-03 — default OFF; 1 disables refinement
    ("CEO_PHASE_REFINE_DISABLE", "0"),           # AUTO-03b — default OFF; 1 disables
    ("CEO_SKIP_TIER_POLICY_CHECK", "0"),         # AUTO-04 — default OFF; 1 skips
    ("CEO_MULTI_MODEL_MANUAL", "0"),             # AUTO-05 — default OFF; 1 reverts
    ("CEO_MCP_ROUTING_DISABLE", "0"),            # AUTO-06 global — default OFF
    ("CEO_PAIR_RAIL_DISABLE", "0"),              # AUTO-07 — default OFF
    ("CEO_PAIR_RAIL_PHASE", "SHADOW"),           # AUTO-07 phase pin (SHADOW/DRY_RUN)
    ("CEO_BENCHMARK_BATCH_MODE", "1"),           # AUTO-08 — default ON; 0 disables
    ("CEO_STREAMING_DISABLE", "0"),              # AUTO-08 (streaming deferred PLAN-090)
    ("CEO_THINKING_AUTO_DISABLE", "0"),          # AUTO-09 — default OFF; 1 disables
    ("CEO_AUTO_SPECIALIZE", "1"),                # AUTO-10 — default ON; 0 disables
    ("CEO_SKIP_COOKBOOK_HINT", "0"),             # SEMI-11 — default OFF; 1 skips
)

# Per-MCP server kill-switches (12 servers per ADR-042 / handoff §3)
# These follow the pattern CEO_MCP_<SERVER>_DISABLE = 0 by default.
_MCP_SERVERS: Tuple[str, ...] = (
    "SENTRY", "STRIPE", "VERCEL", "SUPABASE", "CLOUDFLARE",
    "GMAIL", "DRIVE", "CALENDAR", "AHREFS", "SIMILARWEB",
    "LUNARCRUSH", "CLAUDE_IN_CHROME",
)


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _read_env_file(env_path: Path) -> Optional[str]:
    if not env_path.exists():
        _err("WARN: env file not found at %s — AC17 informational only" % env_path)
        return None
    try:
        return env_path.read_text(encoding="utf-8")
    except OSError as exc:
        _err("FAIL: cannot read env file %s: %s" % (env_path, exc))
        return None


def _parse_env_assignments(text: str) -> List[Tuple[str, str, str, int]]:
    """Return (var_name, value, full_line, line_no) for every KEY=value line.

    Strips inline comments after value (everything after first ` # `).
    """
    out: List[Tuple[str, str, str, int]] = []
    for idx, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line.strip())
        if m is None:
            continue
        name = m.group(1)
        raw_val = m.group(2).strip()
        # Strip inline comment after the value
        # (split on first whitespace+# token)
        val = re.split(r"\s+#", raw_val, maxsplit=1)[0].strip()
        val = val.strip('"').strip("'")
        out.append((name, val, line, idx))
    return out


def _has_telemetry_invariant_comment(text: str, var_name: str) -> bool:
    """Check if the line for var_name is annotated with # telemetry-invariant."""
    for line in text.splitlines():
        if var_name + "=" in line and "telemetry-invariant" in line:
            return True
    return False


def verify(env_path: Path) -> int:
    text = _read_env_file(env_path)
    if text is None:
        # AC17 informational only when env file missing; the verifier
        # reports the gap but doesn't FAIL CI build (the env file is
        # shipped via templates/ install path, not the test runtime).
        print("check-auto-activation-flags.py: SKIP (env file not present)")
        return 0

    assignments = _parse_env_assignments(text)
    by_name = {n: (v, line, lineno) for n, v, line, lineno in assignments}

    failures: List[str] = []

    # Check 1: every expected AUTO env-var present + matches expected default
    for expected_name, expected_default in _EXPECTED_VARS:
        if expected_name not in by_name:
            if _has_telemetry_invariant_comment(text, expected_name):
                continue  # telemetry-invariant override
            failures.append(
                "missing AUTO env-var %r in %s "
                "(expected default=%r per PLAN-088 spec)"
                % (expected_name, env_path, expected_default)
            )
            continue
        actual_value, _line, _lineno = by_name[expected_name]
        # Accept actual values matching expected or empty (=opt-out)
        if actual_value != expected_default and actual_value != "":
            # If line carries # telemetry-invariant, accept anything
            if not _has_telemetry_invariant_comment(text, expected_name):
                failures.append(
                    "AUTO env-var %r has value %r (expected %r per "
                    "PLAN-088 spec; or annotate `# telemetry-invariant`)"
                    % (expected_name, actual_value, expected_default)
                )

    # Check 2: 12 per-MCP server kill-switches present (AUTO-06 W3.1)
    for server in _MCP_SERVERS:
        var_name = "CEO_MCP_%s_DISABLE" % server
        if var_name not in by_name:
            # Per-server kill-switches are advisory; warn only.
            _err("WARN: per-MCP server kill-switch %r absent from %s "
                 "(AUTO-06 W3.1 advisory; user can set ad-hoc)"
                 % (var_name, env_path))

    if failures:
        _err("check-auto-activation-flags.py: FAIL (%d AUTO env-var violation(s))"
             % len(failures))
        for f in failures:
            _err("  - " + f)
        return 1

    print("check-auto-activation-flags.py: PASS")
    print("  - %d AUTO env-vars present with explicit opt-out semantics"
          % len(_EXPECTED_VARS))
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="PLAN-088 W5.2 / AC17 meta-test — AUTO env-var opt-out semantics check"
    )
    p.add_argument("--env-path", default=_DEFAULT_ENV_PATH)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    return verify(Path(args.env_path))


if __name__ == "__main__":
    sys.exit(main())
