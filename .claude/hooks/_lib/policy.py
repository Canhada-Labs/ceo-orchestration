"""Policy-as-code engine — PLAN-014 Phase A.3.

Implements SPEC/v1/policy-dsl.schema.md §3 Grammar + §4 Runtime Semantics
+ §5 Error Model + §6 Policy Identity.

Stdlib-only per ADR-002 (PyYAML FORBIDDEN). Hand-rolled YAML subset parser
per SPEC §3.1-§3.2 with all hard limits enforced (§3.3).

Public API:

    from _lib.policy import load, Policy, PolicyLoadError

    policy = load(Path(".claude/policies/bash-safety.policy.yaml"))
    decision = policy.decide({"tool": "Bash", "tool_input": {"command": "ls"}})
    # -> {"decision": "allow"}

See SPEC for normative semantics. This module is tested against the SPEC,
not the reverse (public-api-design skill rule 1).
"""

from __future__ import annotations

try:
    from _lib import redact as _redact  # noqa: E402
except Exception:  # pragma: no cover
    _redact = None  # type: ignore

import hashlib
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib import audit_emit as _audit_emit  # noqa: E402
except Exception:  # pragma: no cover
    _audit_emit = None  # type: ignore


# ---------------------------------------------------------------------------
# Limits (SPEC §3.3)
# ---------------------------------------------------------------------------

_LIMIT_FILE_BYTES = 64 * 1024  # 64 KiB raw file size
_LIMIT_DEPTH = 8
_LIMIT_TOTAL_EXPAND_BYTES = 1024 * 1024  # 1 MiB post-parse
_LIMIT_KEY_COUNT = 2000
_LIMIT_SCALAR_LEN = 16 * 1024  # 16 KiB per-scalar
_LIMIT_PARSE_CPU_MS = 500.0  # wall-clock
_LIMIT_REGEX_PATTERN = 512


# Closed enum from SPEC §5.
_ERROR_KINDS = frozenset({
    "parse_error",
    "predicate_missing",
    "import_failure",
    "depth_limit",
    "size_limit",
    "alias_rejected",
    "tag_rejected",
    "timeout",
    "field_missing",
    "regex_compile_error",
    "schema_version_mismatch",
})


# Closed set of predicate forms per SPEC §3.5.
_PREDICATE_FORMS = frozenset({
    "all", "any", "not",
    "eq", "neq", "in", "not_in",
    "regex", "starts_with", "ends_with", "contains",
    "length_le", "length_ge", "path_under",
})


# Top-level required keys per SPEC §3.4.
_TOP_LEVEL_REQUIRED = ("schema", "id", "description", "kind", "defaults",
                       "rules", "error_model")

_KIND_ENUM = frozenset({"allow_list", "deny_list", "mixed"})
_DECISION_ENUM = frozenset({"allow", "block"})


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PolicyLoadError(Exception):
    """Raised when :func:`load` cannot build a valid Policy.

    ``error_kind`` is a closed-enum value from SPEC §5. ``detail`` is
    free-text (may be surfaced in ``policy_error`` audit via redaction).
    """

    def __init__(self, error_kind: str, detail: str, policy_id: str = ""):
        if error_kind not in _ERROR_KINDS:
            # Defensive: reject unknown kinds at raise site so the enum
            # contract is enforced. Fall back to parse_error.
            error_kind = "parse_error"
        self.error_kind = error_kind
        if _redact is not None:
            try:
                self.detail = _redact.redact_secrets(detail, max_chars=200)
            except Exception:
                self.detail = (detail[:200] if detail else "")
        else:
            self.detail = (detail[:200] if detail else "")
        self.policy_id = policy_id
        super().__init__(f"{error_kind}: {detail}")


# The parser keeps its historical public/private class name while methods live
# in ordered mixins.  Their code executes with this facade as globals.
# Opt-out: CEO_POLICY_ENGINE_DISABLE=1 reverts to Python-hook fallback.
from _lib._policy_parts import install as _install_policy_parts
_install_policy_parts(globals())
del _install_policy_parts

class _YamlParser(_YamlBlocksMixin, _YamlFlowsMixin, _YamlScalarsMixin):
    """YAML subset parser assembled from bounded implementation mixins."""
    _INT_RE = re.compile(r"^-?\d+$")
    _DIRECTIVE_RE = re.compile(r"^\s*%(YAML|TAG)\b")

    def __init__(self, text: str, cpu_deadline_monotonic: float,
                 policy_id_hint: str = ""):
        self._lines = text.splitlines()
        self._i = 0
        self._n = len(self._lines)
        self._deadline = cpu_deadline_monotonic
        self._key_count = 0
        self._policy_id_hint = policy_id_hint
