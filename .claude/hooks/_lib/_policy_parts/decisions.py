"""Extracted policy declarations: decisions."""
from __future__ import annotations

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

    # PLAN-182 W2 (S321) — atribuicao de projeto nos emissores de policy.
    #
    # Medido: `policy_evaluated` + `policy_denied` respondiam por 15.128 dos
    # 15.208 eventos NAO-ATRIBUIVEIS pos-W1. A causa nao era o scrub
    # (`project` esta em `_FEDERATION_ENVELOPE`, logo nas allowlists) nem o
    # env: era o CHAMADOR omitindo o kwarg, com o default do emissor em "".
    # A W1 curou ONDE o evento e gravado; isto cura O QUE ele carrega.
    #
    # Fail-open por construcao: qualquer falha na resolucao devolve "" e o
    # evento sai como saia antes — atribuicao e observabilidade, nunca um
    # motivo para derrubar uma decisao de policy.
    @staticmethod
    def _project_label() -> str:
        try:
            from _lib import runtime_paths as _rp

            return str(_rp.project_dir())
        except Exception:  # pragma: no cover - fail-open
            return ""

    def _emit_evaluated(self, rule_id: str, decision: str, duration_ms: int) -> None:
        if _audit_emit is None:
            return
        try:
            _audit_emit.emit_policy_evaluated(
                policy_id=self.policy_id,
                rule_id=rule_id,
                decision=decision,
                duration_ms=duration_ms,
                project=self._project_label(),
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
                project=self._project_label(),
            )
        except Exception:  # pragma: no cover
            pass


# ---------------------------------------------------------------------------
# load() entry point
