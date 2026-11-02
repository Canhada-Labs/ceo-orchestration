from __future__ import annotations
from ._shared import *

# QDSAA-FUNCAO-LONGA: ordem dos braços fail-open/fail-closed é contrato de segurança; fragmentar esconderia precedência.
def _decide(
    *,
    tool_name: str,
    file_path: str,
    proposed_content: str,
    repo_root: Path,
    timeout_s: float,
    session_id: str = "",
) -> Dict[str, Any]:
    """Pure decision returning a JSON-shape dict.

    Returns:
        Dict with keys `decision` (allow|block) and optionally
        `reason` (block) or `systemMessage` (allow with note).

    ``session_id`` (PLAN-161 C5, r3 F2): the hook payload's own session id,
    threaded from main() into the `pair_rail_review_expected` denominator
    emit below (and, via `_decide_with_matrix`, into `pair_rail_case`), so
    the /ceo-boot liveness classifier can correlate expected/outcome counts
    PER session.
    """
    # Kill-switch.
    if os.environ.get("CEO_PAIR_RAIL_DISABLE", "").strip() == "1":
        _emit_audit(
            _AUDIT_KILL_SWITCH,
            tool_name=tool_name, file_path=file_path,
        )
        return {}  # schema-compliant allow (Claude Code hook schema rejects top-level "allow")

    # Out-of-scope: tool not in write set.
    write_tools = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
    if tool_name not in write_tools:
        _emit_audit(
            _AUDIT_OUT_OF_SCOPE,
            tool_name=tool_name, reason="non_write_tool",
        )
        return {}  # schema-compliant allow (Claude Code hook schema rejects top-level "allow")

    # Out-of-scope: path not L3+.
    if not _is_l3_plus_path(file_path, repo_root):
        _emit_audit(
            _AUDIT_OUT_OF_SCOPE,
            tool_name=tool_name, file_path=file_path,
            reason="not_l3_plus",
        )
        return {}  # schema-compliant allow (Claude Code hook schema rejects top-level "allow")

    # Sentinel bypass — Owner-signed approval covers this path.
    if _sentinel_grants_pair_rail_bypass(file_path, repo_root):
        _emit_audit(
            _AUDIT_SENTINEL_BYPASS,
            tool_name=tool_name, file_path=file_path,
        )
        return {
            "systemMessage": (
                f"PAIR-RAIL: bypass via Architect sentinel "
                f"({file_path})"
            ),
        }

    # PLAN-161 C5 (r3 F2 + r4 F1 + r4 F2, terminal fix r5 F2): the review
    # path is definitely ENTERED — the kill-switch, non-write-tool, not-L3+
    # and sentinel-bypass arms have ALL returned above. Generate the
    # per-invocation correlation id and emit the durable session-correlated
    # DENOMINATOR for the /ceo-boot `pair_rail` activity-conditioned
    # liveness row BEFORE the Codex invoke, so an expected-without-outcome
    # window (the S254 dead-rail class) becomes observable. r5 F2: the SAME
    # `review_id` is threaded (via the `_CURRENT_REVIEW_ID` slot) into this
    # invocation's `pair_rail_case` emit, so the /ceo-boot deficit pairs a
    # specific expected with its OWN case — bucketed COUNTING still let an
    # old completed case for the SAME (session, file) offset a later
    # expected whose hook died before its case emit. `file_path` stays
    # threaded so the emit carries the SAME `file_path_hash_prefix` as the
    # matching `pair_rail_case` (harmless secondary key + legacy fallback
    # for id-less pre-land events). Fail-OPEN + hasattr-guarded
    # (pre-ceremony audit_emit safe).
    global _CURRENT_REVIEW_ID
    review_id = os.urandom(8).hex()
    _CURRENT_REVIEW_ID = review_id
    # ADR-110-AMEND-2 §1.6 / §4(i): the EFFECTIVE post-clamp budget rides
    # both liveness emits. Without it a session exporting
    # CEO_PAIR_RAIL_TIMEOUT_S=5 produces a case F byte-indistinguishable
    # from a genuine Codex outage — the undocumented knob was stealthier
    # than the documented kill-switch (which emits its own loud event).
    _emit_pair_rail_review_expected(
        tool_name=tool_name, session_id=session_id, file_path=file_path,
        review_id=review_id, timeout_s=timeout_s,
    )

    # Invoke Codex review. `_invoke_codex_review` now returns the REDACTED
    # last-message content (one structured JSON object).
    try:
        redacted_review = _invoke_codex_review(
            tool_name=tool_name,
            file_path=file_path,
            proposed_content=proposed_content,
            timeout_s=timeout_s,
        )
    except CodexPinMismatch as e:
        # ADR-182 fail-CLOSED arm — the ONLY hard-block this hook emits.
        # A payload that fails pin verification is a possible supply-
        # chain swap (T-8): it is never executed, and the L3+ write it
        # would have reviewed is blocked rather than silently degraded
        # to advisory. `_base_to_verdicts` classifies the block as Case
        # B (codex_verdict=BLOCK), pairing this invocation's
        # pair_rail_review_expected emit (no manufactured /ceo-boot
        # liveness deficit).
        _emit_audit(
            _AUDIT_PIN_MISMATCH,
            tool_name=tool_name, file_path=file_path,
            error=str(e)[:240],
        )
        return {
            "decision": "block",
            "reason": (
                "PAIR-RAIL PIN (ADR-182): codex payload pin verification "
                f"failed — {e}. Fail-CLOSED: refusing to invoke an "
                "unverified codex binary and blocking this L3+ write. "
                "If the codex upgrade is legitimate, re-pin via the "
                "ADR-182 ceremony (codex-cli-pin-manifest.json)."
            ),
        }
    except CodexUnavailable as e:
        _emit_audit(
            _AUDIT_CODEX_UNAVAILABLE,
            tool_name=tool_name, file_path=file_path,
            error=str(e),
        )
        # Substring "Codex unavailable" PRESERVED for _base_to_verdicts.
        return {
            "systemMessage": (
                f"PAIR-RAIL: Codex unavailable ({e}); fail-OPEN "
                "advisory mode."
            ),
        }
    except CodexTimeout as e:
        _emit_audit(
            _AUDIT_CODEX_UNAVAILABLE,
            tool_name=tool_name, file_path=file_path,
            error=f"timeout:{e}",
        )
        # Substring "Codex timeout" PRESERVED for _base_to_verdicts.
        return {
            "systemMessage": (
                f"PAIR-RAIL: Codex timeout ({e}); fail-OPEN."
            ),
        }
    except CodexMalformed as e:
        _emit_audit(
            _AUDIT_CODEX_UNAVAILABLE,
            tool_name=tool_name, file_path=file_path,
            error=f"malformed:{e}",
        )
        # Substring "Codex malformed" PRESERVED for _base_to_verdicts.
        return {
            "systemMessage": (
                f"PAIR-RAIL: Codex malformed response ({e}); "
                "fail-OPEN."
            ),
        }

    # PRIMARY: structured verdict (parse_verdict_strict, fail-CLOSED-to-
    # ADVISORY). SECONDARY: _detect_write_shaped_patch annotation (D3).
    verdict, patch_grammar = _consume_codex_review(redacted_review)

    # PLAN-122 WS3 — record the completed Codex review (any verdict) as
    # codex_review_invoked (advisory; redacted PhaseReview; never blocks).
    # `grammar` keeps its historical meaning (write-shape tag). PLAN-142 V2
    # cross-model fold: a structured BLOCK with prose-only findings (no
    # write-shaped patch) has patch_grammar=None, which the WS3 driver would
    # otherwise map to 'accept' — under-reporting BLOCKs. Pass a synthetic
    # block tag so the telemetry agrees with the PRIMARY structured verdict.
    _emit_codex_review_invoked(
        redacted_review,
        patch_grammar or ("structured_block" if verdict == "BLOCK" else None),
    )

    if verdict == "BLOCK":
        # Structured BLOCK from a schema-validated object. Per PLAN-092 /
        # ADR-127 SHADOW-strip the rail stays ADVISORY-ONLY at the
        # user-facing surface (no top-level block); the matrix wrapper owns
        # any block promotion via Case-B preconditions. The "PAIR-RAIL-
        # ADVISORY" + "write-shaped" substrings are PRESERVED so
        # _base_to_verdicts classifies this as Case B (codex_verdict=BLOCK).
        _emit_audit(
            _AUDIT_CODEX_VIOLATION,
            tool_name=tool_name, file_path=file_path,
            verdict="BLOCK",
            grammar=(patch_grammar or ""),
            response_len=len(redacted_review),
        )
        return {
            "systemMessage": (
                "PAIR-RAIL-ADVISORY: Codex returned a structured BLOCK "
                "verdict (advisory-only per ADR-127). A write-shaped "
                f"secondary signal ({patch_grammar or 'none'}) was "
                f"{'also ' if patch_grammar else 'not '}detected. See "
                "routing-matrix.md §threat-model."
            ),
        }

    if patch_grammar is not None and verdict != "BLOCK":
        # Defense-in-depth ONLY: a write-shaped patch under a non-BLOCK
        # structured verdict. The structured verdict is authoritative (D3),
        # so we do NOT block; surface an advisory note + emit the violation
        # audit for forensic continuity. "PAIR-RAIL-ADVISORY" + "write-shaped"
        # keep the matrix Case-B classification stable.
        _emit_audit(
            _AUDIT_CODEX_VIOLATION,
            tool_name=tool_name, file_path=file_path,
            verdict=verdict,
            grammar=patch_grammar,
            response_len=len(redacted_review),
            note="secondary_writeshape_under_nonblock_verdict",
        )
        return {
            "systemMessage": (
                "PAIR-RAIL-ADVISORY: secondary defense-in-depth detected a "
                f"write-shaped patch ({patch_grammar}) under a non-BLOCK "
                f"structured verdict ({verdict}); advisory-only per ADR-127 "
                "+ D3 (structured verdict is authoritative)."
            ),
        }

    if verdict == "ADVISORY":
        # Parse miss / forged free-text / oversize / adapter-missing →
        # ADVISORY (fail-open). No "review clean" substring (NOT a clean
        # pass); no matrix Case-A. r6 F1: `_decide_with_matrix` pairs
        # this arm's `pair_rail_review_expected` by emitting a terminal
        # `pair_rail_case` (case=F, codex_verdict=ADVISORY) on its
        # matrix_case-is-None arm — an entered-and-answered review must
        # never register as a /ceo-boot S254 zero-case deficit.
        _emit_audit(
            _AUDIT_REVIEW_PASSED,
            tool_name=tool_name, file_path=file_path,
            verdict="ADVISORY",
            response_len=len(redacted_review),
        )
        return {
            "systemMessage": (
                "PAIR-RAIL: Codex verdict ADVISORY (no structured PASS/BLOCK "
                "parsed); fail-OPEN advisory mode."
            ),
        }

    # verdict == "PASS" — structured clean review. "review clean" substring
    # PRESERVED for _base_to_verdicts Case-A classification.
    _emit_audit(
        _AUDIT_REVIEW_PASSED,
        tool_name=tool_name, file_path=file_path,
        verdict="PASS",
        response_len=len(redacted_review),
    )
    return {
        "systemMessage": "PAIR-RAIL: Codex review clean (structured PASS verdict).",
    }

def _read_event_from_stdin() -> Optional[Dict[str, Any]]:
    """Parse PreToolUse JSON envelope. Returns None on parse failure."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None

def _extract_proposed_content(tool_input: Dict[str, Any]) -> str:
    """Pull the proposed-write content from tool_input.

    Edit       → `new_string`
    Write      → `content`
    MultiEdit  → concatenation of all `new_string` values
    NotebookEdit → `new_source`
    Fallback   → empty string (Codex review still proceeds with path-only context).
    """
    if not isinstance(tool_input, dict):
        return ""
    if "content" in tool_input and isinstance(tool_input["content"], str):
        return tool_input["content"]
    if "new_string" in tool_input and isinstance(tool_input["new_string"], str):
        return tool_input["new_string"]
    if "new_source" in tool_input and isinstance(tool_input["new_source"], str):
        return tool_input["new_source"]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        chunks: List[str] = []
        for e in edits:
            if isinstance(e, dict) and isinstance(e.get("new_string"), str):
                chunks.append(e["new_string"])
        if chunks:
            return "\n".join(chunks)
    return ""

def main() -> int:
    """Hook entry point — fail-OPEN on any uncaught exception."""
    try:
        event = _read_event_from_stdin()
        if event is None:
            sys.stdout.write(json.dumps({}) + "\n")  # schema-compliant allow
            return 0
        tool_name = str(event.get("tool_name") or "")
        # PLAN-161 C5 (r3 F2): stop discarding the hook payload's session
        # id — thread it into pair_rail_review_expected AND pair_rail_case
        # so /ceo-boot can correlate expected/outcome counts per session.
        session_id = str(
            event.get("session_id")
            or os.environ.get("CLAUDE_SESSION_ID")
            or ""
        )
        tool_input = event.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}
        file_path = str(tool_input.get("file_path") or "")
        proposed = _extract_proposed_content(tool_input)
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        )
        try:
            timeout_s = float(
                os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "180")
            )
        except (TypeError, ValueError):
            timeout_s = 180.0
        if timeout_s <= 0 or timeout_s > 600:
            timeout_s = 180.0

        # PLAN-081 Phase 3: route through the asymmetric VETO matrix
        # wrapper instead of the spike _decide() directly. The matrix
        # wrapper invokes _decide() internally + applies Cases A-F per
        # spec.md §11 + emits pair_rail_case per evaluation.
        decision = _decide_with_matrix(
            tool_name=tool_name,
            file_path=file_path,
            proposed_content=proposed,
            repo_root=repo_root,
            timeout_s=timeout_s,
            session_id=session_id,
        )
        sys.stdout.write(json.dumps(decision, ensure_ascii=False) + "\n")
        return 0
    except Exception as e:
        # Fail-OPEN — never block the user on hook bug. U10 contract:
        # emit a structured breadcrumb so SPIKE-VERDICT.md can audit the
        # rate of catch-all firings (a high rate = a real bug masked by
        # fail-open, not a healthy contract). The stderr write is kept
        # for human visibility during the spike.
        try:
            # Codex MCP review F3 — keep the 240-char preview AND emit
            # stable `error_type` + `error_len` fields so SPIKE-VERDICT.md
            # sampling can group by exception class without parsing the
            # truncated preview.
            err_type = type(e).__name__
            err_str = str(e)
            _emit_audit(
                _AUDIT_FATAL_FAILOPEN,
                error_type=err_type,
                error_len=len(err_str),
                error=f"{err_type}: {err_str}"[:240],
            )
        except Exception:
            pass
        try:
            sys.stderr.write(
                f"[check_pair_rail SPIKE] FATAL: {type(e).__name__}: {e}\n"
            )
        except Exception:
            pass
        sys.stdout.write(json.dumps({}) + "\n")  # schema-compliant allow
        return 0

_RUBRIC_CATALOGUE_CACHE: Optional[Dict[str, Dict[str, Any]]] = None

def _load_rubric_catalogue(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    """Load + cache the rubric violation catalogue.

    Returns an empty dict if the catalogue cannot be loaded (fail-OPEN —
    Phase 3 hook MUST NOT block on missing catalogue; it just downgrades
    Case-B to advisory because the rubric_violation_id can never be
    validated against an empty catalogue).
    """
    global _RUBRIC_CATALOGUE_CACHE
    if _RUBRIC_CATALOGUE_CACHE is not None:
        return _RUBRIC_CATALOGUE_CACHE
    catalogue_path = (
        repo_root / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
    )
    if not catalogue_path.exists():
        _RUBRIC_CATALOGUE_CACHE = {}
        return _RUBRIC_CATALOGUE_CACHE
    try:
        text = catalogue_path.read_text(encoding="utf-8")
        # Inline minimal YAML parse for the `violations:` section.
        # Matches the routing-matrix-loader pattern (stdlib only).
        catalogue: Dict[str, Dict[str, Any]] = {}
        in_violations = False
        current: Optional[Dict[str, Any]] = None
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].rstrip() if "#" in raw_line else raw_line.rstrip()
            if not line.strip():
                continue
            if line.startswith("violations:"):
                in_violations = True
                continue
            if not in_violations:
                continue
            # Detect new entry: '  - id: <slug>' at 2-space indent
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if indent == 2 and stripped.startswith("- id:"):
                if current is not None and "id" in current:
                    catalogue[current["id"]] = current
                current = {}
                _, _, val = stripped.partition(":")
                current["id"] = val.strip()
            elif indent == 4 and current is not None and ":" in stripped:
                key, _, val = stripped.partition(":")
                current[key.strip()] = val.strip()
            elif indent < 2 and current is not None and "id" in current:
                # Section ended
                catalogue[current["id"]] = current
                current = None
                in_violations = False
        if current is not None and "id" in current:
            catalogue[current["id"]] = current
        _RUBRIC_CATALOGUE_CACHE = catalogue
        return catalogue
    except Exception:
        _RUBRIC_CATALOGUE_CACHE = {}
        return _RUBRIC_CATALOGUE_CACHE

def _validate_provider_pair(
    *,
    codex_verdict: str,
    rubric_violation_id: str,
    severity: str,
    file_line_cited: bool,
    repo_root: Path,
) -> Tuple[bool, str]:
    """Validate Case-B preconditions per spec.md §11.

    A Case-B verdict from Codex (BLOCK with PASS from Claude) must carry:
      - reproducible evidence (file:line OR command cited)
      - rubric_violation_id ∈ rubric-violation-catalogue.yaml
      - severity ∈ {P0, P1}

    R1 S-CR-1 codifies: this function is a greenfield helper (NOT
    preserving any prior provider-pair grandfather entry). ADR-097 was
    "Function-length advisory-permanent + 344-function grandfather list"
    — NO LLM/dispatcher/pair-rail content per `head -1` audit.

    Returns:
        (preconditions_met: bool, reason: str). Reason is "ok" when met;
        otherwise a slug naming the specific precondition that failed
        (downstream audit emit + reason_code).
    """
    if codex_verdict != "BLOCK":
        # Not a Case-B candidate — vacuously "met" for the dispatcher
        return True, "not_case_b"
    if not file_line_cited:
        return False, "missing_file_line"
    if not rubric_violation_id or len(rubric_violation_id) > 64:
        return False, "missing_or_invalid_rubric_id"
    catalogue = _load_rubric_catalogue(repo_root)
    if not catalogue:
        return False, "catalogue_not_loaded"
    if rubric_violation_id not in catalogue:
        return False, "rubric_id_not_in_catalogue"
    if severity not in ("P0", "P1"):
        return False, "invalid_severity"
    return True, "ok"

def _compute_jaccard_bucket(claude_findings: List[str], codex_findings: List[str]) -> str:
    """Bucket the Jaccard similarity for Case-E divergence detection.

    Phase 3 uses bucketed similarity (NEVER raw float) per Sec MF-3
    `_PAIR_RAIL_CASE_EMIT_ALLOWLIST` (raw float would leak prompt
    content / response content via correlated audit-log readout).

    Buckets per spec.md §11 R1.5-4 fix:
      - "<=0.3" → low similarity = high divergence → Case-E flag
      - "0.3-0.5"
      - "0.5-0.8"
      - ">0.8" → high similarity = aligned reviews
    """
    if not claude_findings and not codex_findings:
        return ">0.8"  # both empty = perfectly aligned
    set_c = {f.strip().lower() for f in claude_findings if f.strip()}
    set_x = {f.strip().lower() for f in codex_findings if f.strip()}
    if not set_c and not set_x:
        return ">0.8"
    inter = len(set_c & set_x)
    union = len(set_c | set_x)
    if union == 0:
        return ">0.8"
    sim = inter / union
    if sim <= 0.3:
        return "<=0.3"
    if sim <= 0.5:
        return "0.3-0.5"
    if sim <= 0.8:
        return "0.5-0.8"
    return ">0.8"

def _hash_file_path_prefix(file_path: str) -> str:
    """Compute 16-hex SHA-256 prefix of file path (LLM06 side-channel guard)."""
    import hashlib
    if not file_path:
        return ""
    return hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:16]

def _resolve_human_triage_grace_h(severity: str) -> int:
    """Return human-triage grace hours per R1 S-TDE-4.

    P1 violations get a 24h grace window (env-overridable via
    CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS, clamped to [0, 24] per ADR-108
    + Codex iter 1 P1-2). P0 = 0h (immediate block).
    Outside-of-grace P1 closes-as-advisory.

    Codex iter 1 P1-2 fix: env override is clamped to ``min(value, 24)``
    so an Owner setting `CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS=1000` cannot
    extend the grace beyond the ADR-108-mandated 24h ceiling. Lower
    bound stays 0 (allows mechanical-immediate-close override).
    """
    if severity != "P1":
        return 0
    raw = os.environ.get("CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS", "24")
    try:
        h = int(raw)
        # Clamp to [0, 24] per ADR-108 §Operational labeling protocol.
        return max(0, min(h, 24))
    except (TypeError, ValueError):
        return 24

_TIMEOUT_MS_MAX = 6_000_000

def _timeout_ms(value_s: float) -> int:
    """Convert an effective-budget in SECONDS to bounded integer ms.

    Fail-safe: a non-numeric / NaN / infinite input yields 0 (the
    "unknown budget" sentinel) rather than raising into the emit
    wrappers' fail-open catch, which would drop the event.
    """
    try:
        ms = int(float(value_s) * 1000)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(_TIMEOUT_MS_MAX, ms))

__all__ = (
    '_decide',
    '_read_event_from_stdin',
    '_extract_proposed_content',
    'main',
    '_RUBRIC_CATALOGUE_CACHE',
    '_load_rubric_catalogue',
    '_validate_provider_pair',
    '_compute_jaccard_bucket',
    '_hash_file_path_prefix',
    '_resolve_human_triage_grace_h',
    '_TIMEOUT_MS_MAX',
    '_timeout_ms',
)
