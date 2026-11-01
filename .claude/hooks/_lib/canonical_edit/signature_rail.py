"""Signature verification rail for canonical-edit sentinel checks."""
from __future__ import annotations

__all__ = ("_verify_signature_rail",)

def _verify_signature_rail(sentinel_path: Path) -> bool:
    """The full detached-GPG + dual signer-registry rail for ONE sentinel.

    Extracted verbatim from ``_sentinel_grants_path`` (PLAN162_FIX_1) so
    the decision it produces — which is INDEPENDENT of the edit target —
    can be cached target-free. Behaviour is unchanged: fail-CLOSED on a
    missing helper, bad signature, unlisted fingerprint, bootstrap-SHA
    mismatch, or (post-GENESIS) a registry parse failure.
    """
    if _gpg_verify is None:
        # _lib.gpg_verify is unavailable — fail-CLOSED. No sentinel
        # can grant canonical edits without the verification helper.
        return False
    sig_path = sentinel_path.with_name(sentinel_path.name + ".asc")
    # PLAN-089 Wave C.4 — dual-rail signer verification (ADR-121).
    # First-class path: legacy `.claude/sentinel-signers.txt` (existing).
    # Defense-in-depth: if YAML registry exists, re-check fingerprint via
    # _lib.sentinel_signers + bootstrap-SHA pin. Either rail rejecting
    # → fail-CLOSED. Post-GENESIS (_BOOTSTRAP_REGISTRY_SHA256 set),
    # parse/hash failure → fail-CLOSED (R2 Codex iter-1 Q5+Q7 fold);
    # pre-GENESIS (None), parse failure → legacy-only fallback.
    # PLAN162_FIX_1 (Codex P1 fold) — the subprocess is bounded by what is
    # LEFT of the invocation budget, minus the margin needed to still emit
    # a decision. ``None`` => not enough budget to verify AND emit: refuse
    # the spawn and latch, so the caller's next deadline poll produces the
    # fail-closed wall-deadline block instead of a harness kill.
    _timeout = _gpg_verify_timeout()
    if _timeout is None:
        _mark_wall_budget_exhausted()
        return False
    ok, _fpr, _reason = _gpg_verify.verify_detached(
        sentinel_path,
        sig_path,
        allowlist_path=_SENTINEL_SIGNERS_FILE,
        timeout=_timeout,
    )
    if not ok:
        return False
    if (
        _sentinel_signers is not None
        and _SENTINEL_SIGNERS_REGISTRY_YAML.exists()
        and _fpr
    ):
        _post_genesis = _BOOTSTRAP_REGISTRY_SHA256 is not None
        try:
            # Bootstrap SHA pin verification (post-GENESIS only).
            if _post_genesis:
                import hashlib as _hashlib
                _yaml_bytes = _SENTINEL_SIGNERS_REGISTRY_YAML.read_bytes()
                _computed_sha = _hashlib.sha256(_yaml_bytes).hexdigest()
                if _computed_sha != _BOOTSTRAP_REGISTRY_SHA256:
                    try:
                        from _lib import audit_emit as _audit_emit
                        if hasattr(_audit_emit, "emit_sentinel_signer_quorum_failed"):
                            _audit_emit.emit_sentinel_signer_quorum_failed(
                                key_id=_fpr,
                                reason="bootstrap_sha_mismatch",
                                source="canonical_edit_bootstrap_pin",
                            )
                    except Exception:  # pragma: no cover
                        pass
                    return False
            _registry = _sentinel_signers.load_registry(
                _SENTINEL_SIGNERS_REGISTRY_YAML
            )
            _valid, _why = _sentinel_signers.is_valid_signer(
                _fpr, registry=_registry
            )
            # PLAN-113 WIRE-AUDIT: emit quorum_attempted on EVERY
            # signer verification attempt (success + failure).
            try:
                from _lib import audit_emit as _audit_emit_qa
                if hasattr(_audit_emit_qa, "emit_sentinel_signer_quorum_attempted"):
                    _audit_emit_qa.emit_sentinel_signer_quorum_attempted(
                        distinct_signers=1,
                        threshold_required=1,
                        outcome="valid" if _valid else "failed",
                        source="canonical_edit_sentinel_verify",
                    )
            except Exception:  # pragma: no cover
                pass
            if not _valid:
                try:
                    from _lib import audit_emit as _audit_emit
                    if hasattr(_audit_emit, "emit_sentinel_signer_quorum_failed"):
                        _audit_emit.emit_sentinel_signer_quorum_failed(
                            key_id=_fpr,
                            reason=_why,
                            source="canonical_edit_sentinel_verify",
                        )
                except Exception:  # pragma: no cover
                    pass
                return False
        except Exception:  # pragma: no cover
            # Pre-GENESIS (constant None) — degrade to legacy-only.
            # Post-GENESIS — fail-CLOSED (R2 Codex Q7 fold).
            if _BOOTSTRAP_REGISTRY_SHA256 is not None:
                return False
    return True



