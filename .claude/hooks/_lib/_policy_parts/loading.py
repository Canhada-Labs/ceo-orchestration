"""Extracted policy declarations: loading."""
from __future__ import annotations

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
