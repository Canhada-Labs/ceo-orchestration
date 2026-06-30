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


# ---------------------------------------------------------------------------
# YAML subset parser (hand-rolled, stdlib-only)
# ---------------------------------------------------------------------------


class _YamlParser:
    """Minimal YAML 1.2 subset parser per SPEC §3.1-§3.2.

    Accepts: block mappings, block sequences, plain scalars, double-quoted
    strings, single-quoted strings, null/true/false, integers, comments.

    Rejects: anchors/aliases, custom tags, flow-style, block scalars (|/>),
    directives (%YAML/%TAG), multi-doc streams (---), BOM.

    Enforces SPEC §3.3 limits during parse (depth, scalar length, key count,
    CPU wall-clock).
    """

    _INT_RE = re.compile(r"^-?\d+$")
    # Identifiers allowed for predicate-form / key names; permissive scalar.
    _DIRECTIVE_RE = re.compile(r"^\s*%(YAML|TAG)\b")

    def __init__(self, text: str, cpu_deadline_monotonic: float,
                 policy_id_hint: str = ""):
        self._lines = text.splitlines()
        self._i = 0
        self._n = len(self._lines)
        self._deadline = cpu_deadline_monotonic
        self._key_count = 0
        self._policy_id_hint = policy_id_hint

    # ---- top-level entry -------------------------------------------------

    def parse_document(self) -> Any:
        """Parse the single document and return its root value."""
        # Quick directive / multi-doc rejection scan (SPEC §3.2)
        for line in self._lines:
            stripped = line.rstrip("\r\n")
            if self._DIRECTIVE_RE.match(stripped):
                raise PolicyLoadError(
                    "parse_error",
                    "YAML directives (%YAML/%TAG) not allowed",
                    self._policy_id_hint,
                )
            if stripped.strip() == "---" or stripped.strip() == "...":
                raise PolicyLoadError(
                    "parse_error",
                    "multi-document streams not allowed",
                    self._policy_id_hint,
                )

        # Skip leading blank / comment lines.
        self._skip_blanks()
        if self._i >= self._n:
            # Empty doc — return empty mapping.
            return {}

        # Detect starting column / construct type by lookahead.
        line = self._current_line()
        indent = self._indent(line)
        value = self._parse_block_node(indent, depth=1)

        # Trailing non-blank lines would indicate a multi-root; forbid.
        self._skip_blanks()
        if self._i < self._n:
            raise PolicyLoadError(
                "parse_error",
                f"unexpected content at line {self._i + 1}",
                self._policy_id_hint,
            )
        return value

    # ---- block-level dispatch --------------------------------------------

    def _parse_block_node(self, indent: int, depth: int) -> Any:
        self._check_deadline()
        if depth > _LIMIT_DEPTH:
            raise PolicyLoadError(
                "depth_limit",
                f"nesting depth exceeded {_LIMIT_DEPTH}",
                self._policy_id_hint,
            )
        self._skip_blanks()
        if self._i >= self._n:
            return None
        line = self._current_line()
        body = line[indent:]
        if body.startswith("- "):
            return self._parse_block_sequence(indent, depth)
        if body == "-" or body.startswith("- "):
            return self._parse_block_sequence(indent, depth)
        # Detect mapping vs scalar. Mapping line shape: "key:" or "key: value".
        if self._looks_like_mapping_start(body):
            return self._parse_block_mapping(indent, depth)
        # Fall back to scalar line (only meaningful when caller expected a
        # value on its own line; typically mapping values inline so rare).
        self._i += 1
        return self._parse_scalar(body)

    def _parse_block_mapping(self, indent: int, depth: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        while self._i < self._n:
            self._check_deadline()
            self._skip_blanks()
            if self._i >= self._n:
                break
            line = self._current_line()
            line_indent = self._indent(line)
            if line_indent < indent:
                break
            if line_indent != indent:
                raise PolicyLoadError(
                    "parse_error",
                    f"indentation mismatch at line {self._i + 1}",
                    self._policy_id_hint,
                )
            body = line[indent:]
            if body.startswith("- "):
                raise PolicyLoadError(
                    "parse_error",
                    f"sequence item inside mapping at line {self._i + 1}",
                    self._policy_id_hint,
                )
            key, sep, rest = self._split_mapping_line(body, line_no=self._i + 1)
            if not sep:
                # Not a valid mapping line.
                raise PolicyLoadError(
                    "parse_error",
                    f"expected 'key: value' at line {self._i + 1}",
                    self._policy_id_hint,
                )
            self._key_count += 1
            if self._key_count > _LIMIT_KEY_COUNT:
                raise PolicyLoadError(
                    "size_limit",
                    f"total key count exceeded {_LIMIT_KEY_COUNT}",
                    self._policy_id_hint,
                )
            self._i += 1
            if rest.strip() == "":
                # Nested block follows on next line with deeper indent (or null).
                self._skip_blanks()
                if self._i < self._n:
                    next_line = self._current_line()
                    next_indent = self._indent(next_line)
                    if next_indent > indent:
                        value = self._parse_block_node(next_indent, depth + 1)
                    else:
                        value = None
                else:
                    value = None
            else:
                # Inline value — might be scalar or start of flow-style (forbidden).
                value = self._parse_inline_value(rest)
            if key in result:
                raise PolicyLoadError(
                    "parse_error",
                    f"duplicate key {key!r} at line {self._i}",
                    self._policy_id_hint,
                )
            result[key] = value
        return result

    def _parse_block_sequence(self, indent: int, depth: int) -> List[Any]:
        items: List[Any] = []
        while self._i < self._n:
            self._check_deadline()
            self._skip_blanks()
            if self._i >= self._n:
                break
            line = self._current_line()
            line_indent = self._indent(line)
            if line_indent < indent:
                break
            if line_indent != indent:
                raise PolicyLoadError(
                    "parse_error",
                    f"indentation mismatch at line {self._i + 1}",
                    self._policy_id_hint,
                )
            body = line[indent:]
            if not body.startswith("- "):
                break
            rest = body[2:]
            self._i += 1
            if rest.strip() == "":
                # Empty marker — nested block expected on next line.
                self._skip_blanks()
                if self._i < self._n:
                    next_line = self._current_line()
                    next_indent = self._indent(next_line)
                    if next_indent > indent:
                        value: Any = self._parse_block_node(next_indent, depth + 1)
                    else:
                        value = None
                else:
                    value = None
                items.append(value)
                continue
            # Inline: either scalar or a mapping starting on same line "- key: v"
            # For simplicity we support (a) pure scalar items, and (b) mapping
            # items whose first "key: value" lives on the dash line + remaining
            # keys indented at `indent + 2`.
            if self._looks_like_mapping_start(rest):
                # The virtual block mapping starts at column `indent + 2`
                # (post "- "). We need to feed the first line PLUS any
                # deeper-indented continuation lines back through the mapping
                # parser. We construct a fake "start line" by rewriting:
                # re-insert "- " as spaces then defer to _parse_block_mapping.
                # Simpler: parse first k/v here and then grab continuation.
                map_indent = indent + 2
                # Re-inject the line so mapping parser sees it.
                self._i -= 1
                self._lines[self._i] = (" " * map_indent) + rest
                value = self._parse_block_mapping(map_indent, depth + 1)
                items.append(value)
                continue
            # Pure scalar item (may be quoted).
            items.append(self._parse_inline_value(rest))
        return items

    # ---- mapping-line splitter -------------------------------------------

    def _split_mapping_line(self, body: str, line_no: int) -> Tuple[str, bool, str]:
        """Return (key, had_colon, rest). Respects quoted keys and ignores
        colons inside quoted strings. Strips trailing inline comments.
        """
        # Strip inline comment respecting quotes.
        body = self._strip_inline_comment(body)
        # Quoted key forms.
        if body.startswith('"'):
            key, end = self._consume_double_quoted(body, 0, line_no)
        elif body.startswith("'"):
            key, end = self._consume_single_quoted(body, 0, line_no)
        else:
            # Plain-scalar key: read up to first unquoted ':'
            end = -1
            for idx, ch in enumerate(body):
                if ch == ':':
                    end = idx
                    break
            if end == -1:
                return body.strip(), False, ""
            key = body[:end].rstrip()
            return key, True, body[end + 1:].strip()
        # After quoted key: require ':' next (possibly with leading space).
        tail = body[end:]
        if not tail.startswith(":"):
            raise PolicyLoadError(
                "parse_error",
                f"expected ':' after quoted key at line {line_no}",
                self._policy_id_hint,
            )
        return key, True, tail[1:].strip()

    # ---- inline value parse (where forbidden flow-style is caught) -------

    def _parse_inline_value(self, raw: str) -> Any:
        raw = self._strip_inline_comment(raw).strip()
        if not raw:
            return None
        # Flow-style mapping + sequence: SPEC §3.2 rejects these as top-level
        # document shapes (parser branch + escaping ambiguity), but the SPEC's
        # own Appendix A + §3.5 predicate table use single-line flow form
        # (e.g. `eq: {field: tool, value: "Bash"}`) as the canonical predicate
        # body. Resolution: accept single-line flow-mapping + flow-sequence
        # inline as sugar for a block mapping/sequence — NO multi-line flow,
        # NO nesting beyond depth-1 in flow syntax. This matches every
        # example in the SPEC and is load-bearing for the DSL's ergonomics.
        if raw[0] == "{":
            return self._parse_flow_mapping(raw)
        if raw[0] == "[":
            return self._parse_flow_sequence(raw)
        if raw[0] in ("|", ">"):
            raise PolicyLoadError(
                "parse_error",
                f"block-scalar indicator {raw[0]!r} not allowed",
                self._policy_id_hint,
            )
        if raw.startswith("&") or raw.startswith("*"):
            raise PolicyLoadError(
                "alias_rejected",
                "YAML anchors/aliases are disabled",
                self._policy_id_hint,
            )
        if raw.startswith("!"):
            raise PolicyLoadError(
                "tag_rejected",
                "YAML tags are rejected",
                self._policy_id_hint,
            )
        if raw.startswith('"'):
            s, end = self._consume_double_quoted(raw, 0, line_no=self._i)
            if raw[end:].strip() != "":
                raise PolicyLoadError(
                    "parse_error",
                    f"trailing content after quoted scalar at line {self._i}",
                    self._policy_id_hint,
                )
            return s
        if raw.startswith("'"):
            s, end = self._consume_single_quoted(raw, 0, line_no=self._i)
            if raw[end:].strip() != "":
                raise PolicyLoadError(
                    "parse_error",
                    f"trailing content after quoted scalar at line {self._i}",
                    self._policy_id_hint,
                )
            return s
        return self._parse_scalar(raw)

    # ---- flow-style mapping / sequence (single-line sugar) ---------------

    def _parse_flow_scalar(self, s: str, i: int) -> Tuple[Any, int]:
        """Parse a scalar/quoted-scalar starting at s[i]. Return (value, end_i)."""
        if s[i] == '"':
            val, end = self._consume_double_quoted(s, i, line_no=self._i)
            return val, end
        if s[i] == "'":
            val, end = self._consume_single_quoted(s, i, line_no=self._i)
            return val, end
        # Plain: read until , } ] or end.
        end = i
        while end < len(s) and s[end] not in ",}]":
            end += 1
        token = s[i:end].strip()
        return self._parse_scalar(token), end

    def _parse_flow_mapping(self, raw: str) -> Dict[str, Any]:
        assert raw[0] == "{"
        out: Dict[str, Any] = {}
        i = 1
        n = len(raw)
        while i < n:
            while i < n and raw[i] in " \t":
                i += 1
            if i < n and raw[i] == "}":
                tail = raw[i + 1:].strip()
                if tail:
                    raise PolicyLoadError(
                        "parse_error",
                        f"trailing content after flow mapping at line {self._i}",
                        self._policy_id_hint,
                    )
                return out
            # Key
            if i < n and raw[i] == '"':
                key, i = self._consume_double_quoted(raw, i, line_no=self._i)
            elif i < n and raw[i] == "'":
                key, i = self._consume_single_quoted(raw, i, line_no=self._i)
            else:
                k_end = i
                while k_end < n and raw[k_end] not in ":,}":
                    k_end += 1
                key = raw[i:k_end].strip()
                i = k_end
            while i < n and raw[i] in " \t":
                i += 1
            if i >= n or raw[i] != ":":
                raise PolicyLoadError(
                    "parse_error",
                    f"flow mapping missing ':' at line {self._i}",
                    self._policy_id_hint,
                )
            i += 1
            while i < n and raw[i] in " \t":
                i += 1
            if i < n and raw[i] == "{":
                # Nested flow mapping — find matching close.
                depth_f = 1
                j = i + 1
                while j < n and depth_f > 0:
                    c = raw[j]
                    if c == '"':
                        _, j = self._consume_double_quoted(raw, j, line_no=self._i)
                        continue
                    if c == "'":
                        _, j = self._consume_single_quoted(raw, j, line_no=self._i)
                        continue
                    if c == "{":
                        depth_f += 1
                    elif c == "}":
                        depth_f -= 1
                    j += 1
                inner = raw[i:j]
                value = self._parse_flow_mapping(inner)
                i = j
            elif i < n and raw[i] == "[":
                depth_f = 1
                j = i + 1
                while j < n and depth_f > 0:
                    c = raw[j]
                    if c == '"':
                        _, j = self._consume_double_quoted(raw, j, line_no=self._i)
                        continue
                    if c == "'":
                        _, j = self._consume_single_quoted(raw, j, line_no=self._i)
                        continue
                    if c == "[":
                        depth_f += 1
                    elif c == "]":
                        depth_f -= 1
                    j += 1
                inner = raw[i:j]
                value = self._parse_flow_sequence(inner)
                i = j
            else:
                value, i = self._parse_flow_scalar(raw, i)
            out[str(key)] = value
            while i < n and raw[i] in " \t":
                i += 1
            if i < n and raw[i] == ",":
                i += 1
                continue
            if i < n and raw[i] == "}":
                continue
        raise PolicyLoadError(
            "parse_error",
            f"unterminated flow mapping at line {self._i}",
            self._policy_id_hint,
        )

    def _parse_flow_sequence(self, raw: str) -> List[Any]:
        assert raw[0] == "["
        out: List[Any] = []
        i = 1
        n = len(raw)
        while i < n:
            while i < n and raw[i] in " \t":
                i += 1
            if i < n and raw[i] == "]":
                tail = raw[i + 1:].strip()
                if tail:
                    raise PolicyLoadError(
                        "parse_error",
                        f"trailing content after flow sequence at line {self._i}",
                        self._policy_id_hint,
                    )
                return out
            if i < n and raw[i] == "{":
                depth_f = 1
                j = i + 1
                while j < n and depth_f > 0:
                    c = raw[j]
                    if c == '"':
                        _, j = self._consume_double_quoted(raw, j, line_no=self._i)
                        continue
                    if c == "'":
                        _, j = self._consume_single_quoted(raw, j, line_no=self._i)
                        continue
                    if c == "{":
                        depth_f += 1
                    elif c == "}":
                        depth_f -= 1
                    j += 1
                value = self._parse_flow_mapping(raw[i:j])
                i = j
            elif i < n and raw[i] == "[":
                depth_f = 1
                j = i + 1
                while j < n and depth_f > 0:
                    c = raw[j]
                    if c == "[":
                        depth_f += 1
                    elif c == "]":
                        depth_f -= 1
                    j += 1
                value = self._parse_flow_sequence(raw[i:j])
                i = j
            else:
                value, i = self._parse_flow_scalar(raw, i)
            out.append(value)
            while i < n and raw[i] in " \t":
                i += 1
            if i < n and raw[i] == ",":
                i += 1
                continue
            if i < n and raw[i] == "]":
                continue
        raise PolicyLoadError(
            "parse_error",
            f"unterminated flow sequence at line {self._i}",
            self._policy_id_hint,
        )

    # ---- scalar parse ----------------------------------------------------

    def _parse_scalar(self, raw: str) -> Any:
        raw = raw.strip()
        if raw == "" or raw.lower() == "null" or raw == "~":
            return None
        if raw.lower() == "true":
            return True
        if raw.lower() == "false":
            return False
        if self._INT_RE.match(raw):
            try:
                return int(raw)
            except ValueError:  # pragma: no cover
                pass
        # Plain string — reject aliases / anchors / tags if they appear here.
        if raw.startswith("&") or raw.startswith("*"):
            raise PolicyLoadError(
                "alias_rejected",
                "YAML anchors/aliases are disabled",
                self._policy_id_hint,
            )
        if raw.startswith("!"):
            raise PolicyLoadError(
                "tag_rejected",
                "YAML tags are rejected",
                self._policy_id_hint,
            )
        # Length cap.
        if len(raw) > _LIMIT_SCALAR_LEN:
            raise PolicyLoadError(
                "size_limit",
                f"scalar exceeds {_LIMIT_SCALAR_LEN}-byte limit",
                self._policy_id_hint,
            )
        return raw

    # ---- quote helpers ---------------------------------------------------

    def _consume_double_quoted(self, s: str, start: int, line_no: int) -> Tuple[str, int]:
        """Return (decoded string, end index AFTER closing quote)."""
        assert s[start] == '"'
        i = start + 1
        out: List[str] = []
        while i < len(s):
            ch = s[i]
            if ch == '"':
                decoded = "".join(out)
                if len(decoded) > _LIMIT_SCALAR_LEN:
                    raise PolicyLoadError(
                        "size_limit",
                        f"scalar exceeds {_LIMIT_SCALAR_LEN}-byte limit",
                        self._policy_id_hint,
                    )
                return decoded, i + 1
            if ch == "\\":
                if i + 1 >= len(s):
                    raise PolicyLoadError(
                        "parse_error",
                        f"dangling escape at line {line_no}",
                        self._policy_id_hint,
                    )
                esc = s[i + 1]
                if esc == "n":
                    out.append("\n"); i += 2
                elif esc == "t":
                    out.append("\t"); i += 2
                elif esc == "r":
                    out.append("\r"); i += 2
                elif esc == '"':
                    out.append('"'); i += 2
                elif esc == "\\":
                    out.append("\\"); i += 2
                elif esc == "/":
                    out.append("/"); i += 2
                elif esc == "u":
                    if i + 6 > len(s):
                        raise PolicyLoadError(
                            "parse_error",
                            f"short \\u escape at line {line_no}",
                            self._policy_id_hint,
                        )
                    hex4 = s[i + 2:i + 6]
                    try:
                        out.append(chr(int(hex4, 16)))
                    except ValueError:
                        raise PolicyLoadError(
                            "parse_error",
                            f"invalid \\u escape at line {line_no}",
                            self._policy_id_hint,
                        )
                    i += 6
                else:
                    raise PolicyLoadError(
                        "parse_error",
                        f"unknown escape \\{esc} at line {line_no}",
                        self._policy_id_hint,
                    )
                continue
            out.append(ch)
            i += 1
        raise PolicyLoadError(
            "parse_error",
            f"unterminated double-quoted scalar at line {line_no}",
            self._policy_id_hint,
        )

    def _consume_single_quoted(self, s: str, start: int, line_no: int) -> Tuple[str, int]:
        assert s[start] == "'"
        i = start + 1
        out: List[str] = []
        while i < len(s):
            ch = s[i]
            if ch == "'":
                if i + 1 < len(s) and s[i + 1] == "'":
                    out.append("'")
                    i += 2
                    continue
                decoded = "".join(out)
                if len(decoded) > _LIMIT_SCALAR_LEN:
                    raise PolicyLoadError(
                        "size_limit",
                        f"scalar exceeds {_LIMIT_SCALAR_LEN}-byte limit",
                        self._policy_id_hint,
                    )
                return decoded, i + 1
            out.append(ch)
            i += 1
        raise PolicyLoadError(
            "parse_error",
            f"unterminated single-quoted scalar at line {line_no}",
            self._policy_id_hint,
        )

    # ---- low-level helpers -----------------------------------------------

    def _current_line(self) -> str:
        return self._lines[self._i]

    def _indent(self, line: str) -> int:
        n = 0
        for ch in line:
            if ch == " ":
                n += 1
            elif ch == "\t":
                raise PolicyLoadError(
                    "parse_error",
                    "tab indentation not allowed",
                    self._policy_id_hint,
                )
            else:
                break
        return n

    def _skip_blanks(self) -> None:
        while self._i < self._n:
            line = self._lines[self._i]
            stripped = line.strip()
            if stripped == "" or stripped.startswith("#"):
                self._i += 1
                continue
            return

    def _looks_like_mapping_start(self, body: str) -> bool:
        # Strip comment + see if we have "key:" or "key: v" shape.
        body = self._strip_inline_comment(body).rstrip()
        if not body:
            return False
        # Quoted key — only a mapping if a ':' follows the closing quote.
        if body.startswith('"'):
            # find matching close quote (respecting escapes)
            i = 1
            while i < len(body):
                if body[i] == "\\" and i + 1 < len(body):
                    i += 2
                    continue
                if body[i] == '"':
                    tail = body[i + 1:]
                    return tail.startswith(":")
                i += 1
            return False
        if body.startswith("'"):
            i = 1
            while i < len(body):
                if body[i] == "'":
                    if i + 1 < len(body) and body[i + 1] == "'":
                        i += 2
                        continue
                    tail = body[i + 1:]
                    return tail.startswith(":")
                i += 1
            return False
        # Scan up to first ':' or newline; require it exists and is followed
        # by space or end-of-line.
        for idx, ch in enumerate(body):
            if ch == ':':
                if idx + 1 == len(body) or body[idx + 1] == ' ':
                    return True
                return False
        return False

    def _strip_inline_comment(self, body: str) -> str:
        """Remove ' # ...' trailing comment but respect quotes."""
        in_s = False
        in_d = False
        for i, ch in enumerate(body):
            if ch == "'" and not in_d:
                in_s = not in_s
            elif ch == '"' and not in_s:
                in_d = not in_d
            elif ch == '#' and not in_s and not in_d:
                # Must have a whitespace before '#' (or be at start).
                if i == 0 or body[i - 1] in (" ", "\t"):
                    return body[:i].rstrip()
        return body

    def _check_deadline(self) -> None:
        if time.monotonic() > self._deadline:
            raise PolicyLoadError(
                "timeout",
                f"parse exceeded {int(_LIMIT_PARSE_CPU_MS)} ms",
                self._policy_id_hint,
            )


# ---------------------------------------------------------------------------
# Predicate compiler + evaluator
# ---------------------------------------------------------------------------


@dataclass
class _CompiledPredicate:
    """Internal AST node for an evaluator."""
    form: str
    # For all/any/not
    children: List["_CompiledPredicate"] = field(default_factory=list)
    # For leaf forms
    field_path: Optional[str] = None
    value: Any = None
    values: Optional[Tuple[Any, ...]] = None
    pattern_src: Optional[str] = None
    compiled_regex: Optional["re.Pattern[str]"] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    substring: Optional[str] = None
    root: Optional[str] = None
    length: Optional[int] = None


def _compile_predicate(raw: Any, policy_id: str,
                       path: str = "predicate") -> _CompiledPredicate:
    if not isinstance(raw, dict):
        raise PolicyLoadError(
            "predicate_missing",
            f"predicate at {path} is not a mapping",
            policy_id,
        )
    if len(raw) != 1:
        raise PolicyLoadError(
            "predicate_missing",
            f"predicate at {path} must have exactly one form key, got {sorted(raw.keys())}",
            policy_id,
        )
    form, body = next(iter(raw.items()))
    if form not in _PREDICATE_FORMS:
        raise PolicyLoadError(
            "predicate_missing",
            f"unknown predicate form {form!r} at {path}",
            policy_id,
        )
    node = _CompiledPredicate(form=form)
    if form in ("all", "any"):
        if not isinstance(body, list) or not body:
            raise PolicyLoadError(
                "parse_error",
                f"{form!r} at {path} requires a non-empty list",
                policy_id,
            )
        for idx, child in enumerate(body):
            node.children.append(_compile_predicate(child, policy_id,
                                                   f"{path}.{form}[{idx}]"))
        return node
    if form == "not":
        if not isinstance(body, dict):
            raise PolicyLoadError(
                "parse_error",
                f"'not' at {path} requires a single predicate mapping",
                policy_id,
            )
        node.children.append(_compile_predicate(body, policy_id, f"{path}.not"))
        return node
    # Leaf forms — body must be dict
    if not isinstance(body, dict):
        raise PolicyLoadError(
            "parse_error",
            f"{form!r} at {path} requires a mapping body",
            policy_id,
        )
    fld = body.get("field")
    if not isinstance(fld, str) or not fld:
        raise PolicyLoadError(
            "parse_error",
            f"{form!r} at {path} missing 'field'",
            policy_id,
        )
    node.field_path = fld
    if form in ("eq", "neq"):
        if "value" not in body:
            raise PolicyLoadError(
                "parse_error",
                f"{form!r} at {path} missing 'value'",
                policy_id,
            )
        node.value = body["value"]
    elif form in ("in", "not_in"):
        vals = body.get("values")
        if not isinstance(vals, list):
            raise PolicyLoadError(
                "parse_error",
                f"{form!r} at {path} requires 'values' list",
                policy_id,
            )
        node.values = tuple(vals)
    elif form == "regex":
        pat = body.get("pattern")
        if not isinstance(pat, str):
            raise PolicyLoadError(
                "parse_error",
                f"regex at {path} missing 'pattern'",
                policy_id,
            )
        if len(pat) > _LIMIT_REGEX_PATTERN:
            raise PolicyLoadError(
                "regex_compile_error",
                f"regex pattern length exceeds {_LIMIT_REGEX_PATTERN}",
                policy_id,
            )
        # SPEC §3.6: reject backreference-in-quantifier heuristic.
        if re.search(r"\\[0-9]+[+*?]", pat):
            raise PolicyLoadError(
                "regex_compile_error",
                "backreference in quantifier is rejected",
                policy_id,
            )
        try:
            node.compiled_regex = re.compile(pat)
        except re.error as e:
            raise PolicyLoadError(
                "regex_compile_error",
                f"regex compile failed: {e}",
                policy_id,
            )
        node.pattern_src = pat
    elif form == "starts_with":
        p = body.get("prefix")
        if not isinstance(p, str):
            raise PolicyLoadError("parse_error",
                                  f"starts_with at {path} missing 'prefix' string",
                                  policy_id)
        node.prefix = p
    elif form == "ends_with":
        p = body.get("suffix")
        if not isinstance(p, str):
            raise PolicyLoadError("parse_error",
                                  f"ends_with at {path} missing 'suffix' string",
                                  policy_id)
        node.suffix = p
    elif form == "contains":
        p = body.get("substring")
        if not isinstance(p, str):
            raise PolicyLoadError("parse_error",
                                  f"contains at {path} missing 'substring' string",
                                  policy_id)
        node.substring = p
    elif form in ("length_le", "length_ge"):
        v = body.get("value")
        if not isinstance(v, int) or isinstance(v, bool):
            raise PolicyLoadError("parse_error",
                                  f"{form!r} at {path} requires integer 'value'",
                                  policy_id)
        node.length = v
    elif form == "path_under":
        r = body.get("root")
        if not isinstance(r, str) or not r:
            raise PolicyLoadError("parse_error",
                                  f"path_under at {path} missing 'root' string",
                                  policy_id)
        node.root = r
    return node


def _get_field(event: Any, dotted: str) -> Optional[Any]:
    cur: Any = event
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _evaluate(node: _CompiledPredicate, event: Dict[str, Any]) -> bool:
    form = node.form
    if form == "all":
        for c in node.children:
            if not _evaluate(c, event):
                return False
        return True
    if form == "any":
        for c in node.children:
            if _evaluate(c, event):
                return True
        return False
    if form == "not":
        return not _evaluate(node.children[0], event)
    val = _get_field(event, node.field_path or "")
    if val is None:
        # SPEC §7.3 — field missing → predicate false (not error).
        return False
    if form == "eq":
        return val == node.value
    if form == "neq":
        return val != node.value
    if form == "in":
        return val in (node.values or ())
    if form == "not_in":
        return val not in (node.values or ())
    if form == "regex":
        assert node.compiled_regex is not None
        if not isinstance(val, str):
            return False
        return node.compiled_regex.search(val) is not None
    if form == "starts_with":
        return isinstance(val, str) and val.startswith(node.prefix or "")
    if form == "ends_with":
        return isinstance(val, str) and val.endswith(node.suffix or "")
    if form == "contains":
        return isinstance(val, str) and (node.substring or "") in val
    if form == "length_le":
        try:
            return len(val) <= int(node.length or 0)
        except TypeError:
            return False
    if form == "length_ge":
        try:
            return len(val) >= int(node.length or 0)
        except TypeError:
            return False
    if form == "path_under":
        if not isinstance(val, str):
            return False
        try:
            target = os.path.realpath(val)
            root = os.path.realpath(node.root or "")
            common = os.path.commonpath([target, root])
            return common == root
        except ValueError:
            return False
    return False


def _predicate_to_canonical(node: _CompiledPredicate) -> Any:
    """Round-trip a compiled predicate back to the normalized dict form used
    for canonical hashing. Regex appears as source string (not compiled).
    """
    form = node.form
    if form in ("all", "any"):
        return {form: [_predicate_to_canonical(c) for c in node.children]}
    if form == "not":
        return {"not": _predicate_to_canonical(node.children[0])}
    body: Dict[str, Any] = {"field": node.field_path}
    if form in ("eq", "neq"):
        body["value"] = node.value
    elif form in ("in", "not_in"):
        body["values"] = list(node.values or ())
    elif form == "regex":
        body["pattern"] = node.pattern_src
    elif form == "starts_with":
        body["prefix"] = node.prefix
    elif form == "ends_with":
        body["suffix"] = node.suffix
    elif form == "contains":
        body["substring"] = node.substring
    elif form in ("length_le", "length_ge"):
        body["value"] = node.length
    elif form == "path_under":
        body["root"] = node.root
    return {form: body}


# ---------------------------------------------------------------------------
# Compiled rule + Policy
# ---------------------------------------------------------------------------


@dataclass
class CompiledRule:
    rule_id: str
    description: str
    decision: str
    reason: Optional[str]
    predicate: _CompiledPredicate
    status: Optional[str] = None  # "deprecated" etc. (advisory only)


class Policy:
    """Immutable post-load. :meth:`decide` is pure over the frozen AST.

    Attributes:
        policy_id: slug from ``id:`` field (matches filename base).
        schema_version: ``"policy-dsl/v1"``.
        kind: ``"allow_list"`` | ``"deny_list"`` | ``"mixed"``.
        defaults: ``{"decision": ..., "reason": ...}``.
        rules: ordered list of :class:`CompiledRule`.
        error_reasons: closed enum from ``error_model.reasons``.
        canonical_hash: SHA-256 hex digest (SPEC §6.1).
    """

    def __init__(
        self,
        policy_id: str,
        schema_version: str,
        description: str,
        kind: str,
        defaults: Dict[str, Any],
        rules: List[CompiledRule],
        error_reasons: Dict[str, str],
    ):
        self.policy_id = policy_id
        self.schema_version = schema_version
        self.description = description
        self.kind = kind
        self.defaults = dict(defaults)
        self.rules = list(rules)
        self.error_reasons = dict(error_reasons)
        self._rule_locks: Dict[str, "threading.RLock"] = {
            r.rule_id: threading.RLock() for r in rules
        }
        # Compute canonical hash last.
        payload = json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        self.canonical_hash = hashlib.sha256(payload).hexdigest()

    # --- public --------------------------------------------------------

    def to_canonical_dict(self) -> Dict[str, Any]:
        """SPEC §6.1 canonical-form serialization.

        - Keys sorted at every level (enforced by ``json.dumps(..., sort_keys=True)``
          at hash time).
        - Rules preserved in declared order (first-match-wins semantic).
        - Regex patterns as source strings.
        """
        return {
            "schema": self.schema_version,
            "id": self.policy_id,
            "description": self.description,
            "kind": self.kind,
            "defaults": dict(self.defaults),
            "rules": [
                {
                    "id": r.rule_id,
                    "description": r.description,
                    "decision": r.decision,
                    "reason": r.reason,
                    "predicate": _predicate_to_canonical(r.predicate),
                }
                for r in self.rules
            ],
            "error_model": {
                "reasons": dict(self.error_reasons),
            },
        }

    def decide(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate rules in declared order; first match wins.

        Emits :func:`audit_emit.emit_policy_evaluated` (always) and
        :func:`audit_emit.emit_policy_denied` (deny path only) before
        returning. Never raises; field-missing → predicate-false per
        SPEC §7.3.
        """
        start = time.monotonic()
        matched: Optional[CompiledRule] = None
        for rule in self.rules:
            if _evaluate(rule.predicate, event):
                matched = rule
                break
        duration_ms = int((time.monotonic() - start) * 1000)
        if matched is None:
            decision = str(self.defaults.get("decision", "allow"))
            reason = self.defaults.get("reason")
            rule_id = "<default>"
            out: Dict[str, Any] = {"decision": decision}
            if decision == "block" and reason:
                out["reason"] = reason
                msg = self.error_reasons.get(str(reason))
                if msg:
                    out["message"] = msg
            self._emit_evaluated(rule_id, decision, duration_ms)
            if decision == "block":
                self._emit_denied(rule_id, str(reason or ""))
            return out
        out2: Dict[str, Any] = {"decision": matched.decision}
        if matched.decision == "block" and matched.reason:
            out2["reason"] = matched.reason
            msg = self.error_reasons.get(matched.reason)
            if msg:
                out2["message"] = msg
        self._emit_evaluated(matched.rule_id, matched.decision, duration_ms)
        if matched.decision == "block":
            self._emit_denied(matched.rule_id, matched.reason or "")
        return out2

    # --- audit helpers (fail-open) -------------------------------------

    def _emit_evaluated(self, rule_id: str, decision: str, duration_ms: int) -> None:
        if _audit_emit is None:
            return
        try:
            _audit_emit.emit_policy_evaluated(
                policy_id=self.policy_id,
                rule_id=rule_id,
                decision=decision,
                duration_ms=duration_ms,
            )
        except Exception:  # pragma: no cover
            pass

    def _emit_denied(self, rule_id: str, reason: str) -> None:
        if _audit_emit is None:
            return
        try:
            _audit_emit.emit_policy_denied(
                policy_id=self.policy_id,
                rule_id=rule_id,
                reason=reason,
            )
        except Exception:  # pragma: no cover
            pass


# ---------------------------------------------------------------------------
# load() entry point
# ---------------------------------------------------------------------------


def _estimate_size(value: Any) -> int:
    """Best-effort recursive sizeof for the post-parse structure."""
    seen: set = set()

    def walk(v: Any) -> int:
        """Recursive sizeof walker — bounds total parsed-structure memory.

        Returns an estimated byte count for ``v`` summed across any
        contained dicts / lists / strings. Uses ``id(v)`` in the ``seen``
        set to short-circuit self-referential cycles (policy docs
        shouldn't have cycles post-alias-rejection, but the defensive
        check costs nothing). Falls back to ``sys.getsizeof(v)`` on
        non-container types; returns 0 on access errors.
        """
        try:
            vid = id(v)
            if vid in seen:
                return 0
            seen.add(vid)
        except TypeError:  # pragma: no cover
            pass
        size = sys.getsizeof(v)
        if isinstance(v, dict):
            for k, vv in v.items():
                size += walk(k) + walk(vv)
        elif isinstance(v, (list, tuple, set, frozenset)):
            for item in v:
                size += walk(item)
        return size

    return walk(value)


def _load_read_raw(path: Path) -> "tuple[str, str]":
    """PLAN-023 CLOSEOUT (DYN-REFACTOR-2) helper 1/4.

    Stat + size cap + read bytes + BOM reject + UTF-8 decode.
    Returns (text, policy_id_hint); raises PolicyLoadError on any
    failure (preserving error_kind byte-identity per
    test_policy_golden_error_kinds.py).
    """
    policy_id_hint = path.stem
    if policy_id_hint.endswith(".policy"):
        policy_id_hint = policy_id_hint[: -len(".policy")]

    try:
        stat = path.stat()
    except OSError as e:
        raise PolicyLoadError(
            "parse_error",
            f"cannot stat policy file: {e}",
            policy_id_hint,
        )
    if stat.st_size > _LIMIT_FILE_BYTES:
        raise PolicyLoadError(
            "size_limit",
            f"file size {stat.st_size} exceeds {_LIMIT_FILE_BYTES}",
            policy_id_hint,
        )

    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        raise PolicyLoadError(
            "parse_error",
            f"cannot read policy file: {e}",
            policy_id_hint,
        )
    if raw.startswith(b"\xef\xbb\xbf"):
        raise PolicyLoadError(
            "parse_error",
            "UTF-8 BOM not allowed",
            policy_id_hint,
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise PolicyLoadError(
            "parse_error",
            f"UTF-8 decode error: {e}",
            policy_id_hint,
        )
    return text, policy_id_hint


def _load_parse_and_audit(text: str, policy_id_hint: str) -> Dict[str, Any]:
    """PLAN-023 CLOSEOUT (DYN-REFACTOR-2) helper 2/4.

    Parse the YAML subset + post-parse size audit. Returns the parsed
    dict or raises PolicyLoadError with byte-identical error_kind.
    """
    deadline = time.monotonic() + (_LIMIT_PARSE_CPU_MS / 1000.0)
    parser = _YamlParser(text, cpu_deadline_monotonic=deadline,
                         policy_id_hint=policy_id_hint)
    data = parser.parse_document()
    if not isinstance(data, dict):
        raise PolicyLoadError(
            "parse_error",
            "top-level must be a mapping",
            policy_id_hint,
        )
    if _estimate_size(data) > _LIMIT_TOTAL_EXPAND_BYTES:
        raise PolicyLoadError(
            "size_limit",
            f"post-parse size exceeds {_LIMIT_TOTAL_EXPAND_BYTES} bytes",
            policy_id_hint,
        )
    return data


def load(path: Path) -> Policy:
    """Parse + validate + compile a policy file.

    Raises :class:`PolicyLoadError` on any SPEC §5 violation.

    PLAN-023 CLOSEOUT decomposition: delegates to helpers
    ``_load_read_raw`` (I/O + decode) and ``_load_parse_and_audit``
    (YAML + size audit). Byte-identity preserved against
    ``test_policy_golden_error_kinds.py`` 18-case golden suite.
    """
    path = Path(path)
    text, policy_id_hint = _load_read_raw(path)
    data = _load_parse_and_audit(text, policy_id_hint)

    # --- top-level schema validation ---
    for key in _TOP_LEVEL_REQUIRED:
        if key not in data:
            raise PolicyLoadError(
                "parse_error",
                f"missing required top-level key {key!r}",
                policy_id_hint,
            )
    schema_version = data["schema"]
    if schema_version != "policy-dsl/v1":
        raise PolicyLoadError(
            "schema_version_mismatch",
            f"schema must be 'policy-dsl/v1', got {schema_version!r}",
            policy_id_hint,
        )
    policy_id = data["id"]
    if not isinstance(policy_id, str) or not policy_id:
        raise PolicyLoadError("parse_error", "'id' must be a non-empty string",
                              policy_id_hint)
    description = data["description"]
    if not isinstance(description, str):
        raise PolicyLoadError("parse_error", "'description' must be a string",
                              policy_id)
    if len(description) > 200:
        raise PolicyLoadError("size_limit",
                              "description exceeds 200 chars",
                              policy_id)
    kind = data["kind"]
    if not isinstance(kind, str) or kind not in _KIND_ENUM:
        raise PolicyLoadError("parse_error",
                              f"kind must be one of {sorted(_KIND_ENUM)}, got {kind!r}",
                              policy_id)
    defaults = data["defaults"]
    if not isinstance(defaults, dict) or "decision" not in defaults:
        raise PolicyLoadError("parse_error",
                              "'defaults' must be a mapping with 'decision'",
                              policy_id)
    dd = defaults["decision"]
    if not isinstance(dd, str) or dd not in _DECISION_ENUM:
        raise PolicyLoadError("parse_error",
                              f"defaults.decision must be allow|block, got {defaults['decision']!r}",
                              policy_id)
    rules_raw = data["rules"]
    if not isinstance(rules_raw, list):
        raise PolicyLoadError("parse_error", "'rules' must be a list", policy_id)
    error_model = data["error_model"]
    if not isinstance(error_model, dict) or "reasons" not in error_model:
        raise PolicyLoadError("parse_error",
                              "'error_model' must be a mapping with 'reasons'",
                              policy_id)
    reasons_raw = error_model["reasons"]
    if not isinstance(reasons_raw, dict):
        raise PolicyLoadError("parse_error",
                              "'error_model.reasons' must be a mapping",
                              policy_id)
    error_reasons: Dict[str, str] = {}
    for k, v in reasons_raw.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise PolicyLoadError("parse_error",
                                  "error_model.reasons entries must be string→string",
                                  policy_id)
        error_reasons[k] = v

    # --- compile rules ---
    compiled: List[CompiledRule] = []
    seen_ids: set = set()
    for idx, rule_raw in enumerate(rules_raw):
        if not isinstance(rule_raw, dict):
            raise PolicyLoadError("parse_error",
                                  f"rule[{idx}] must be a mapping",
                                  policy_id)
        rid = rule_raw.get("id")
        if not isinstance(rid, str) or not rid:
            raise PolicyLoadError("parse_error",
                                  f"rule[{idx}] missing 'id'",
                                  policy_id)
        if rid in seen_ids:
            raise PolicyLoadError("parse_error",
                                  f"duplicate rule id {rid!r}",
                                  policy_id)
        seen_ids.add(rid)
        decision = rule_raw.get("decision")
        if not isinstance(decision, str) or decision not in _DECISION_ENUM:
            raise PolicyLoadError("parse_error",
                                  f"rule {rid!r} decision must be allow|block",
                                  policy_id)
        reason = rule_raw.get("reason")
        if decision == "block":
            if not isinstance(reason, str) or not reason:
                raise PolicyLoadError("parse_error",
                                      f"rule {rid!r} decision=block requires 'reason'",
                                      policy_id)
            if reason not in error_reasons:
                raise PolicyLoadError("parse_error",
                                      f"rule {rid!r} reason {reason!r} not in error_model.reasons",
                                      policy_id)
        pred_raw = rule_raw.get("predicate")
        if pred_raw is None:
            raise PolicyLoadError("predicate_missing",
                                  f"rule {rid!r} missing 'predicate'",
                                  policy_id)
        predicate = _compile_predicate(pred_raw, policy_id,
                                       path=f"rules[{idx}].predicate")
        desc = rule_raw.get("description", "")
        if not isinstance(desc, str):
            desc = str(desc) if desc is not None else ""
        if len(desc) > 200:
            raise PolicyLoadError("size_limit",
                                  f"rule {rid!r} description exceeds 200 chars",
                                  policy_id)
        status = rule_raw.get("status")
        if status is not None and not isinstance(status, str):
            status = None
        compiled.append(CompiledRule(
            rule_id=rid,
            description=desc,
            decision=decision,
            reason=reason if decision == "block" else None,
            predicate=predicate,
            status=status,
        ))

    # Cross-check id field matches filename hint (advisory — mismatch is NOT
    # an error per SPEC; fixture naming convention only).
    _ = policy_id_hint  # retained for diagnostics.

    return Policy(
        policy_id=policy_id,
        schema_version=schema_version,
        description=description,
        kind=kind,
        defaults=defaults,
        rules=compiled,
        error_reasons=error_reasons,
    )


__all__ = [
    "Policy",
    "CompiledRule",
    "PolicyLoadError",
    "load",
]
