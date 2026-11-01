from __future__ import annotations
from ._shared import *

# QDSAA-FUNCAO-LONGA: evento forense completo mantém campos correlatos; separar normalização poderia publicar retrato parcial.
def _emit_pair_rail_review_expected(
    *,
    tool_name: str,
    session_id: str = "",
    file_path: str = "",
    review_id: str = "",
    timeout_s: float = 0.0,
) -> None:
    """Best-effort audit emit of pair_rail_review_expected. Fail-OPEN.

    PLAN-161 C5 (r3 F2 + r4 F1): the durable session-correlated DENOMINATOR
    for the /ceo-boot `pair_rail` activity-conditioned liveness row. Called
    from `_decide()` only after the kill-switch / non-write-tool / not-L3+ /
    sentinel-bypass arms have all returned — i.e. a Codex review is
    definitely being ENTERED.

    r5 F2: ``review_id`` is the per-invocation correlation id generated at
    review entry (`os.urandom(8).hex()`, 16-hex). The SAME id rides this
    emit AND the matching `pair_rail_case` emit of the same `_decide()`
    invocation, so the /ceo-boot deficit pairs invocation-exact — counting
    (even (session, file-hash)-bucketed) cannot pair a specific expected
    with its OWN case. Forwarded only when the resolved audit_emit's
    signature accepts it (``__kwdefaults__`` probe), so a version-skewed
    audit_emit degrades to the id-less legacy emit instead of a TypeError
    that would swallow the whole event (fail-open regression class).

    r4 F2 (kept as the legacy fallback + harmless secondary key):
    ``file_path`` is hashed here with the SAME helper the
    `pair_rail_case` emit uses (`_hash_file_path_prefix` — 16-hex SHA-256
    prefix, raw path NEVER on the wire per LLM06) so id-less events can
    still pair per (session, file-hash) BUCKET.

    ADR-110-AMEND-2 §1.6: ``timeout_s`` is the EFFECTIVE post-clamp Codex
    budget for this invocation in SECONDS (resolved in `main()`, threaded
    through `_decide_with_matrix` → `_decide`). It exists so a case F
    caused by a sub-floor `CEO_PAIR_RAIL_TIMEOUT_S` export stops being
    indistinguishable from a genuine Codex outage (§4(i) residual — the
    quiet knob was stealthier than the documented kill-switch). It reaches
    the wire as the INTEGER-millisecond `timeout_ms` (see `_timeout_ms`:
    canonical_json forbids floats in HMAC-covered fields), forwarded under
    the SAME `__kwdefaults__` skew guard as `review_id`.

    Import resolution mirrors `_emit_pair_rail_case` (staged-dir override →
    canonical layout → PYTHONPATH). hasattr-guarded: a pre-ceremony
    audit_emit without `emit_pair_rail_review_expected` is a silent no-op.
    Deliberately NO `CEO_PAIR_RAIL_AUDIT_SINK` write — the sink is the
    matrix tests' `pair_rail_case` capture surface and must not grow
    extra rows under their counts.
    """
    _ae = None
    try:
        # Resolution 1: test-only staged-dir override.
        staged_dir = os.environ.get("CEO_PAIR_RAIL_STAGED_AUDIT_EMIT_DIR")
        if staged_dir:
            staged_path = Path(staged_dir)
            if staged_path.is_dir() and (staged_path / "_lib" / "audit_emit.py").exists():
                if str(staged_path) not in sys.path:
                    sys.path.insert(0, str(staged_path))
                try:
                    from _lib import audit_emit as _ae  # type: ignore
                except Exception:
                    _ae = None
        # Resolution 2: canonical layout.
        if _ae is None:
            hooks_dir = Path(__file__).resolve().parent
            if str(hooks_dir) not in sys.path:
                sys.path.insert(0, str(hooks_dir))
            try:
                from _lib import audit_emit as _ae  # type: ignore  # noqa: F811
            except Exception:
                _ae = None
        # Resolution 3: PYTHONPATH already configured.
        if _ae is None:
            try:
                from _lib import audit_emit as _ae  # type: ignore  # noqa: F811
            except Exception:
                _ae = None
        if _ae is None or not hasattr(_ae, "emit_pair_rail_review_expected"):
            return
        _kwargs = {
            "session_id": session_id,
            "tool_name": tool_name,
            "file_path_hash_prefix": _hash_file_path_prefix(file_path),
        }
        # r5 F2 — forward review_id only when the resolved audit_emit
        # accepts it (kw-only param with default → visible in
        # __kwdefaults__). A version-skewed audit_emit thus degrades to
        # the id-less legacy emit instead of a TypeError swallowed by the
        # outer fail-open (which would drop the WHOLE event).
        _kwd = getattr(
            _ae.emit_pair_rail_review_expected, "__kwdefaults__", None
        ) or {}
        if "review_id" in _kwd:
            _kwargs["review_id"] = review_id
        # ADR-110-AMEND-2 §1.6 — same skew guard: a pre-ceremony
        # audit_emit without `timeout_ms` degrades to the budget-less
        # legacy emit instead of a TypeError that would drop the WHOLE
        # denominator event (fail-open regression class).
        if "timeout_ms" in _kwd:
            _kwargs["timeout_ms"] = _timeout_ms(timeout_s)
        _ae.emit_pair_rail_review_expected(**_kwargs)
    except Exception:
        pass  # fail-OPEN — never block on audit

# QDSAA-FUNCAO-LONGA: emissão principal e sink derivam o mesmo caso, severidade e correlação antes de qualquer escrita.
def _emit_pair_rail_case(
    *,
    case: str,
    claude_verdict: str,
    codex_verdict: str,
    tool_name: str,
    file_path: str,
    precondition_met: bool = False,
    rubric_violation_id: str = "",
    severity: str = "",
    jaccard_bucket: str = "",
    repo_root: Optional[Path] = None,
    session_id: str = "",
    review_id: str = "",
    timeout_s: float = 0.0,
) -> None:
    """Best-effort audit emit of pair_rail_case. Fail-OPEN.

    ADR-110-AMEND-2 §1.6: ``timeout_s`` is the EFFECTIVE post-clamp Codex
    budget this invocation ran under, in SECONDS. A case F emitted under a
    sub-floor budget (`CEO_PAIR_RAIL_TIMEOUT_S=5`) and a case F from a
    genuine Codex outage were byte-identical before this field existed —
    §4(i). It reaches the wire as the INTEGER-millisecond `timeout_ms`
    (see `_timeout_ms`), forwarded under the SAME `__kwdefaults__` skew
    guard as `review_id`.

    r5 F2: ``review_id`` is the per-invocation correlation id generated by
    `_decide()` at review entry and threaded here via `_decide_with_matrix`
    — identical on this case emit and its own `pair_rail_review_expected`.
    Forwarded only when the resolved audit_emit's signature accepts it
    (``__kwdefaults__`` probe): a version-skewed (pre-land) audit_emit
    degrades to the id-less legacy emit instead of raising TypeError into
    the outer fail-open catch, which would silently drop the whole case
    emit and MANUFACTURE a liveness deficit.

    Import resolution order (first hit wins):

    1. Test-only env override ``CEO_PAIR_RAIL_STAGED_AUDIT_EMIT_DIR``
       points at a directory containing ``_lib/audit_emit.py``. Used by
       the Phase 3 staging tests to load the staged audit_emit before
       the ceremony cp lands it canonical. Removed post-ceremony.
    2. Canonical layout: ``Path(__file__).resolve().parent`` (the
       canonical ``.claude/hooks/`` dir) contains ``_lib/audit_emit.py``.
       Standard production path post-ceremony.
    3. PYTHONPATH-discovered ``_lib.audit_emit`` (rare adopter
       scenario where the canonical hooks dir isn't this file's parent).

    Any failure → return silently (fail-OPEN per ADR-106).
    """
    _ae = None
    try:
        # Resolution 1: test-only staged-dir override.
        staged_dir = os.environ.get("CEO_PAIR_RAIL_STAGED_AUDIT_EMIT_DIR")
        if staged_dir:
            staged_path = Path(staged_dir)
            if staged_path.is_dir() and (staged_path / "_lib" / "audit_emit.py").exists():
                if str(staged_path) not in sys.path:
                    sys.path.insert(0, str(staged_path))
                try:
                    from _lib import audit_emit as _ae  # type: ignore
                except Exception:
                    _ae = None
        # Resolution 2: canonical layout.
        if _ae is None:
            hooks_dir = Path(__file__).resolve().parent
            if str(hooks_dir) not in sys.path:
                sys.path.insert(0, str(hooks_dir))
            try:
                from _lib import audit_emit as _ae  # type: ignore  # noqa: F811
            except Exception:
                _ae = None
        # Resolution 3: PYTHONPATH already configured.
        if _ae is None:
            try:
                from _lib import audit_emit as _ae  # type: ignore  # noqa: F811
            except Exception:
                _ae = None
        # Defense-in-depth: ALSO breadcrumb to CEO_PAIR_RAIL_AUDIT_SINK
        # (the spike's per-test file sink). Used by Phase 3 matrix tests
        # to capture matrix decisions in the same JSONL surface as the
        # spike's `_emit_audit`. Production deployment relies on
        # audit_emit.emit_pair_rail_case being reachable; the sink
        # breadcrumb is a forensic continuity bridge for tests + adopters
        # without canonical audit-log writability.
        sink = os.environ.get("CEO_PAIR_RAIL_AUDIT_SINK")
        if sink:
            try:
                with open(sink, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "action": "pair_rail_case",
                        "case": case,
                        "claude_verdict": claude_verdict,
                        "codex_verdict": codex_verdict,
                        "tool_name": tool_name,
                        "file_path_hash_prefix": _hash_file_path_prefix(file_path),
                        "review_id": review_id,
                        "precondition_met": precondition_met,
                        "rubric_violation_id": rubric_violation_id,
                        "severity": severity,
                        "jaccard_similarity_bucket": jaccard_bucket,
                        "human_triage_grace_h": _resolve_human_triage_grace_h(severity),
                        # ADR-110-AMEND-2 §1.6 — forensic parity with the
                        # signed row (same integer-ms encoding). The sink
                        # BYPASSES audit_emit, so the bound is applied
                        # here too — never write an unbounded caller
                        # value to a file.
                        "timeout_ms": _timeout_ms(timeout_s),
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass

        if _ae is None or not hasattr(_ae, "emit_pair_rail_case"):
            return
        _kwargs = {
            "case": case,
            "claude_verdict": claude_verdict,
            "codex_verdict": codex_verdict,
            "tool_name": tool_name,
            "file_path_hash_prefix": _hash_file_path_prefix(file_path),
            "precondition_met": precondition_met,
            "rubric_violation_id": rubric_violation_id,
            "severity": severity,
            "jaccard_similarity_bucket": jaccard_bucket,
            "human_triage_grace_h": _resolve_human_triage_grace_h(severity),
            # PLAN-161 C5 (r3 F2): the hook payload's session id, no longer
            # discarded — the typed default "" only remains for legacy
            # callers.
            "session_id": session_id,
        }
        # r5 F2 — forward review_id only when the resolved audit_emit
        # accepts it (see _emit_pair_rail_review_expected; same skew
        # guard — a TypeError here would silently DROP the case emit and
        # manufacture a /ceo-boot deficit, worse than an id-less emit).
        _kwd = getattr(
            _ae.emit_pair_rail_case, "__kwdefaults__", None
        ) or {}
        if "review_id" in _kwd:
            _kwargs["review_id"] = review_id
        # ADR-110-AMEND-2 §1.6 — same skew guard: a version-skewed
        # audit_emit without `timeout_ms` degrades to the budget-less
        # legacy emit rather than raising a TypeError that would DROP the
        # case emit and manufacture a /ceo-boot liveness deficit.
        if "timeout_ms" in _kwd:
            _kwargs["timeout_ms"] = _timeout_ms(timeout_s)
        _ae.emit_pair_rail_case(**_kwargs)
    except Exception:
        pass  # fail-OPEN — never block on audit

def _load_pair_rail_decide():  # type: ignore[no-untyped-def]
    """Resolve the canonical pure decision module `_lib.pair_rail_decide`.

    Mirrors `_emit_pair_rail_case`'s Resolution-2 (canonical layout):
    the `.claude/hooks/` dir that houses this file also houses `_lib/`.
    Returns the module or None (fail-OPEN — caller must tolerate None).
    """
    try:
        hooks_dir = Path(__file__).resolve().parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import pair_rail_decide as _prd  # type: ignore
        return _prd
    except Exception:
        return None

def _base_to_verdicts(base: Dict[str, Any]) -> Tuple[str, str, str]:
    """Translate the procedural `base` decision dict into the verdict
    triple `_lib.pair_rail_decide.detect_case()` consumes.

    PLAN-112-FOLLOWUP-pair-rail-decide-canonical (W1). PURE + fail-OPEN:
    any malformed input yields the no-case tuple `("", "", "")` (which
    `detect_case()` maps to None → no matrix emit), never raises.

    The substring contract is byte-identical to the LEGACY inline
    classification in `_decide_with_matrix` (verified against
    `_decide()` returns, source lines 595-679). Precedence MUST match
    the inline arm order: F (Codex fail) → B (write-shape/block) →
    A (review clean) → None (sentinel / kill-switch / out-of-scope).

    Returns:
        (claude_verdict, codex_verdict, jaccard_bucket).
        claude_verdict is "PASS" for every reachable matrix case
        (Claude already passed to reach a PreToolUse write). Sentinel
        bypass + non-matrix short-circuits return ("", "", "").
    """
    try:
        sysmsg = base.get("systemMessage", "")
        if not isinstance(sysmsg, str):
            sysmsg = ""
        decision = base.get("decision", "allow")
        # Arm 1 — Case F (Codex unavailable / timeout / malformed).
        if (
            "Codex unavailable" in sysmsg
            or "Codex timeout" in sysmsg
            or "Codex malformed" in sysmsg
        ):
            sysmsg_lower = sysmsg.lower()
            if "malformed" in sysmsg_lower:
                return "PASS", "MALFORMED", ""
            # timeout AND unavailable both coerce to TIMEOUT (schema-
            # compatible; precise reason stays in base[systemMessage]).
            return "PASS", "TIMEOUT", ""
        # Arm 2 — sentinel bypass is NOT a matrix case (no verdicts).
        if "bypass via Architect sentinel" in sysmsg:
            return "", "", ""
        # Arm 3 — Case B (write-shape advisory OR legacy block path).
        is_advisory_writeshape = (
            "PAIR-RAIL-ADVISORY" in sysmsg and "write-shaped" in sysmsg
        )
        if decision == "block" or is_advisory_writeshape:
            return "PASS", "BLOCK", ""
        # Arm 4 — Case A (clean review).
        if "review clean" in sysmsg:
            return "PASS", "PASS", ""
        # Arm 5 — non-matrix short-circuit (kill-switch / out-of-scope).
        return "", "", ""
    except Exception:
        # Fail-OPEN: derivation error → no-case tuple (detect_case → None).
        return "", "", ""

# QDSAA-FUNCAO-LONGA: matriz assimétrica em ordem normativa preserva precedência do VETO e emissão do caso correspondente.
def _decide_with_matrix(
    *,
    tool_name: str,
    file_path: str,
    proposed_content: str,
    repo_root: Path,
    timeout_s: float,
    session_id: str = "",
) -> Dict[str, Any]:
    """Phase 3 asymmetric VETO matrix wrapper around `_decide()`.

    Calls the canonical `_decide()` codepath to get the Phase 1 verdict
    (review-only semantics), then applies the Cases A-F matrix:

      - canonical path returns ALLOW with no matrix-relevant signal → Case A
      - canonical path returns advisory write-shape (PLAN-092 Wave B
        SHADOW-strip per ADR-127) → validate Case-B preconditions:
          + preconditions met → Case B (advisory + audit)
          + preconditions NOT met → Case B' fail-OPEN (advisory)
      - canonical path returns ALLOW with `systemMessage` containing
        "Codex unavailable" / "timeout" / "malformed" → Case F (allow)
      - canonical path returns ALLOW with sentinel bypass → not a matrix case
        (already authorized by Owner sentinel)

    Each matrix arm emits `pair_rail_case` with case + verdicts +
    preconditions + rubric metadata.

    R1 S-Perf-3: matrix lookup uses O(1) dict (NOT linear scan); the
    ``_MATRIX_DECISIONS`` table below dispatches in constant time.
    """
    # r5 F2 — reset the per-invocation correlation slot BEFORE _decide():
    # a stale id from a prior in-process invocation must never attach to
    # a case whose review path was not entered this time. _decide() sets
    # it (os.urandom(8).hex()) exactly when the review path is ENTERED,
    # in the same breath as the pair_rail_review_expected emit.
    global _CURRENT_REVIEW_ID
    _CURRENT_REVIEW_ID = ""

    # Compute base decision via spike _decide()
    base = _decide(
        tool_name=tool_name,
        file_path=file_path,
        proposed_content=proposed_content,
        repo_root=repo_root,
        timeout_s=timeout_s,
        session_id=session_id,
    )

    # r5 F2 — the id generated by THIS _decide() invocation (or "" when
    # the review path was never entered / kill-switch / out-of-scope /
    # sentinel arms returned early — those paths emit no case anyway).
    review_id = _CURRENT_REVIEW_ID

    sysmsg = base.get("systemMessage", "")

    # PLAN-112-FOLLOWUP-pair-rail-decide-canonical (W2): delegate the
    # verdict→case CLASSIFICATION to the canonical pure module
    # `_lib.pair_rail_decide.detect_case()`. The procedural shell
    # (Codex invoke, patch detect — both inside `_decide()` above), the
    # B'/precondition resolution, and every audit emit STAY INLINE.
    # `evaluate()` is DELIBERATELY NOT called: it would convert a
    # precondition-unmet Case B into B' (pair_rail_decide.py:197-204),
    # diverging from production's byte-identical `case="B"` emit.
    #
    # Fail-OPEN: any error in verdict-derivation / classification / lib
    # import returns `base` (implicit allow), never raises.
    try:
        cv, xv, jb = _base_to_verdicts(base)
        _prd = _load_pair_rail_decide()
        matrix_case = (
            _prd.detect_case(claude_verdict=cv, codex_verdict=xv, jaccard_bucket=jb)
            if _prd is not None
            else None
        )
    except Exception:
        return base  # fail-OPEN — never block the user on a classifier bug

    if matrix_case is None:
        # r6 F1 — discriminate on the invocation correlation id. A
        # non-empty `review_id` proves THIS _decide() invocation ENTERED
        # the review path (it emitted `pair_rail_review_expected`) and
        # returned a base decision that classifies to NO matrix case.
        # The only post-entry return that lands here is the ADVISORY
        # parse-miss arm (`_decide()` verdict=="ADVISORY": codex RAN and
        # ANSWERED, but the response parsed to no structured PASS/BLOCK
        # — `_base_to_verdicts` Arm 5 → detect_case None). Without a
        # case emit that expected review_id stays OUTSTANDING forever →
        # a FALSE /ceo-boot S254 deficit ("hook died between the two
        # emits") for a rail that actually answered. Emit the accounted
        # fail-open terminal case — case=F, codex_verdict=ADVISORY (both
        # already in the audit_emit closed enums; no schema change) —
        # carrying the SAME review_id so expected<->case pairs and the
        # row is LADDERED by its failopen bucket, exactly like the
        # sibling stop_review rail's parse-miss (`skipped_failopen`,
        # plan C5 r2 F2: unparseable is NEVER healthy). The deficit RED
        # stays reserved for an entered review with ZERO case emit (the
        # genuine S254 hook-death signal). An empty review_id = a
        # pre-review short-circuit (sentinel bypass / kill-switch /
        # out-of-scope / non-write tool) — byte-identical legacy
        # no-emit.
        if review_id:
            _emit_pair_rail_case(
                case="F", claude_verdict="PASS", codex_verdict="ADVISORY",
                tool_name=tool_name, file_path=file_path,
                session_id=session_id, review_id=review_id,
                timeout_s=timeout_s,
            )
        return base

    case_value = getattr(matrix_case, "value", matrix_case)

    if case_value == "F":
        # Case F — fail-OPEN. The codex_verdict sub-discrimination
        # (MALFORMED vs TIMEOUT, with UNAVAILABLE coercing to TIMEOUT)
        # is carried by `_base_to_verdicts()` in `xv`; emit it verbatim.
        _emit_pair_rail_case(
            case="F", claude_verdict="PASS", codex_verdict=xv,
            tool_name=tool_name, file_path=file_path,
            session_id=session_id, review_id=review_id,
            timeout_s=timeout_s,
        )
        return base

    if case_value == "B":
        # Procedural Case-B audit emit (advisory-only per ADR-127).
        # B'/precondition resolution stays INLINE (NOT via evaluate()).
        # precondition_met reflects whether substantive rubric evidence
        # was attached (False at Phase 3; True at Phase 4 corpus-replay).
        preconditions_met, reason_slug = _validate_provider_pair(
            codex_verdict="BLOCK",
            rubric_violation_id="",  # not extracted from procedural grammar
            severity="",
            file_line_cited=False,
            repo_root=repo_root,
        )
        _emit_pair_rail_case(
            case="B", claude_verdict="PASS", codex_verdict="BLOCK",
            tool_name=tool_name, file_path=file_path,
            precondition_met=preconditions_met,
            rubric_violation_id="",
            severity="P0",  # write-shape violation defaulted P0 procedural
            session_id=session_id, review_id=review_id,
            timeout_s=timeout_s,
        )
        # Advisory-only return — `base` already carries the advisory
        # systemMessage (Site 1). No `decision` key — schema treats
        # absence as implicit allow.
        return base

    if case_value == "A":
        _emit_pair_rail_case(
            case="A", claude_verdict="PASS", codex_verdict="PASS",
            tool_name=tool_name, file_path=file_path,
            session_id=session_id, review_id=review_id,
            timeout_s=timeout_s,
        )
        return base

    # Defensive: any other detected case (C/D/E — confirmed unreachable
    # from the procedural `base`, plan §2a.2) → no emit, fail-OPEN allow.
    return base

def _verify_pin_cli(argv: List[str]) -> int:
    """ADR-182 CLI entry — `check_pair_rail.py --verify-codex-pin
    [<launcher-path>]`. Shared verification surface for
    `pair-rail-gate.sh` Gate 4 and operator forensics: prints the
    `verify_codex_payload()` result as one JSON object.

    Exit codes (gate.sh contract):
      0 — verified (payload sha256 matches the manifest entry)
      1 — fail-CLOSED arm (mismatch / triple_missing)
      3 — INFRA arm (manifest unreadable, launcher/payload missing, ...)
    """
    launcher = argv[0] if argv else None
    res = verify_codex_payload(launcher)
    try:
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
    except Exception:
        pass
    status = res.get("status")
    if status == "verified":
        return 0
    if status in ("mismatch", "triple_missing"):
        return 1
    return 3

__all__ = (
    '_emit_pair_rail_review_expected',
    '_emit_pair_rail_case',
    '_load_pair_rail_decide',
    '_base_to_verdicts',
    '_decide_with_matrix',
    '_verify_pin_cli',
)
