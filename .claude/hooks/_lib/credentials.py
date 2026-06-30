"""Credential pattern detection and safe env access.

Sprint 12 Phase 1 / CRITICAL-2 mitigation (PLAN-012, ADR-040).

Centralizes provider-key regexes + context-aware "is this a real key?"
heuristic + no-caching env read. Downstream consumers:
- ``check_bash_safety.py`` — pre-Bash grep for leaked keys
- ``_lib/adapters/live/*.py`` (Wave 2) — safe env read
- Complementary to ``_lib/redact.py`` which owns post-hoc redaction

Design contract:
1. Stdlib-only (``re``, ``os``, ``pathlib``, ``typing``)
2. Never log the match itself — callers own disclosure
3. Zero caching: ``read_env_safely`` re-reads ``os.environ`` every call
4. Context-aware false-positive guard in ``is_likely_real_key``

Key length references (empirical, 2026-Q2):
  anthropic  sk-ant-     + 40-200 char URL-safe body
  google     AIza        + exactly 35 URL-safe chars
  openai_proj sk-proj-   + 80-256 char body
  openai_legacy sk-      + 48-256 char body (excl. sk-ant- / sk-proj-)
  aws        AKIA        + 16 uppercase alphanum
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Pattern, Tuple


class MissingCredentialError(Exception):
    """Raised when a required environment credential is absent.

    ``.var_name`` carries the variable name; the message never contains
    the (missing) value.
    """

    def __init__(self, var_name: str, message: Optional[str] = None) -> None:
        self.var_name = var_name
        super().__init__(message or f"Missing required credential: {var_name}")


# Provider → compiled regex. Narrower than ``_lib/redact.py`` on purpose:
# redaction prefers recall, detection-at-bash prefers precision.
KEY_PATTERNS: Dict[str, Pattern[str]] = {
    "anthropic": re.compile(r"sk-ant-[A-Za-z0-9\-_]{40,200}"),
    "google": re.compile(r"AIza[A-Za-z0-9\-_]{35}"),
    "openai_proj": re.compile(r"sk-proj-[A-Za-z0-9\-_]{80,256}"),
    # Negative lookahead excludes sk-ant- and sk-proj- so legacy doesn't
    # double-match the more specific Anthropic/OpenAI-proj patterns.
    "openai_legacy": re.compile(r"sk-(?!ant-|proj-)[A-Za-z0-9\-_]{48,256}"),
    "aws": re.compile(r"AKIA[0-9A-Z]{16}"),
}

# Case-insensitive tokens that, when present in context or the match
# itself, indicate documentation/placeholder intent. Heuristic, not
# exhaustive — tuned for empirical false-positive scenarios.
_DOC_TOKENS: Tuple[str, ...] = (
    "example", "your_key", "your-key", "your key", "yourkey",
    "replace", "replace_me", "placeholder", "redacted",
    "xxx", "dummy", "fake", "sample",
    "<your", "<api", "<key", "abcdef", "test_key",
)

_PROVIDER_PREFIXES: Dict[str, str] = {
    "anthropic": "sk-ant-",
    "google": "AIza",
    "openai_proj": "sk-proj-",
    "openai_legacy": "sk-",
    "aws": "AKIA",
}


def _in_non_shell_fenced_block(text: str, byte_offset: int) -> bool:
    """True iff ``byte_offset`` sits inside a fenced code block whose
    language tag is non-shell (i.e. doc example, not copy-paste shell).

    Scans backward counting fence openings; if the top of the stack is
    a non-shell language (``yaml``, ``python``, ``json``, etc.) we treat
    the match as documentation. Shell-like (``bash``, ``sh``, ``zsh``,
    ``shell``, ``console``) or unlabeled fences are treated as real.
    """
    fence_re = re.compile(r"^([`~]{3,})\s*([A-Za-z0-9_\-]*)\s*$")
    lang_stack: List[str] = []
    for line in text[:byte_offset].splitlines():
        m = fence_re.match(line)
        if not m:
            continue
        lang = m.group(2).lower()
        if lang_stack and lang_stack[-1] == "__open__":
            lang_stack.pop()  # closing fence
        else:
            lang_stack.append(lang if lang else "__open__")
    if not lang_stack:
        return False
    shell_langs = {"bash", "sh", "zsh", "shell", "console", "__open__"}
    return lang_stack[-1] not in shell_langs


def is_likely_real_key(match: str, context: str) -> bool:
    """Heuristic: True iff ``match`` looks like a live credential.

    Returns False for:
    - Matches with placeholder tokens (``EXAMPLE``, ``YOUR_KEY``, etc.)
    - Matches in multi-line context inside non-shell fenced code blocks
    - All-same-char bodies (e.g. ``sk-ant-AAAA...``)

    Errs on the side of True — false negatives here leak credentials.
    """
    if not match:
        return False
    lowered = (context + " " + match).lower()
    for tok in _DOC_TOKENS:
        if tok in lowered:
            return False
    if "\n" in context:
        idx = context.find(match)
        if idx >= 0 and _in_non_shell_fenced_block(context, idx):
            return False
    # All-same-char body almost always means placeholder.
    body = match
    for prefix in ("sk-ant-", "sk-proj-", "sk-", "AIza", "AKIA"):
        if body.startswith(prefix):
            body = body[len(prefix):]
            break
    if body and len(set(body)) <= 3:
        return False
    return True


def detect_keys(text: str) -> List[Tuple[str, str, int]]:
    """Return ``[(provider, match, byte_offset), ...]`` sorted by offset.

    Pure regex — does NOT apply the real-key heuristic. Caller runs
    ``is_likely_real_key`` per match to decide enforcement. Callers that
    log the returned tuples MUST convert via ``redacted_display`` first.
    """
    if not text:
        return []
    results: List[Tuple[str, str, int]] = []
    for provider, pattern in KEY_PATTERNS.items():
        for m in pattern.finditer(text):
            results.append((provider, m.group(0), m.start()))
    results.sort(key=lambda t: t[2])
    return results


def read_env_safely(
    var_name: str,
    *,
    required: bool = False,
    default: Optional[str] = None,
) -> Optional[str]:
    """Re-read ``os.environ.get(var_name)`` — no caching, no logging.

    Every call re-reads os.environ: ``unset ANTHROPIC_API_KEY`` takes
    effect for the next adapter call (ADR-040 §credentials).

    Args:
        var_name: environment variable name
        required: raise ``MissingCredentialError`` if unset/empty
        default: returned when absent and ``required=False``

    Raises:
        MissingCredentialError: if required and absent. The error
        contains only the var name — never the (missing) value.
    """
    value = os.environ.get(var_name)
    if value is None or value == "":
        if required:
            raise MissingCredentialError(var_name)
        return default
    return value


def redacted_display(provider: str, match: str) -> str:
    """Safe-to-log form: ``<provider>:<prefix>****``.

    The ONLY form in which callers should surface matched credentials
    in audit events, block reasons, or user-visible output.

    Examples:
        redacted_display("anthropic", "sk-ant-api03-ABC...") →
            "anthropic:sk-ant-****"
    """
    prefix = _PROVIDER_PREFIXES.get(provider, "")
    return f"{provider}:{prefix}****"
