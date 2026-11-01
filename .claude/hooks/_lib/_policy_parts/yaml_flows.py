"""Extracted policy declarations: yaml_flows."""
from __future__ import annotations

class _YamlFlowsMixin:
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
