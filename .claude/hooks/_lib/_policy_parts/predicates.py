"""Extracted policy declarations: predicates."""
from __future__ import annotations

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
