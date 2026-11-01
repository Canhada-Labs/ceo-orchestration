"""Extracted policy declarations: yaml_scalars."""
from __future__ import annotations

class _YamlScalarsMixin:
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
