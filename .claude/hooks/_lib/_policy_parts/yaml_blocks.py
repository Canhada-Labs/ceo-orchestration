"""Extracted policy declarations: yaml_blocks."""
from __future__ import annotations

class _YamlBlocksMixin:
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
