"""Build data-only ceremony summaries; never issue a signed approval."""

from __future__ import annotations

from typing import Mapping


def build_ceremony_summary(preflight: Mapping, signature: Mapping) -> dict:
    """Expose measured inputs and fail-closed readiness for downstream UI.

    ``ready`` only means both checks succeeded. Land/sign is always an
    Owner-side operation outside the toolkit.
    """
    scope = tuple(preflight.get("canonical_paths", ()))
    pinned = dict(preflight.get("sha256", {}))
    valid_scope = bool(preflight.get("valid")) and bool(scope)
    valid_sig = bool(signature.get("valid")) and bool(signature.get("fingerprint"))
    return {
        "ready_for_owner_review": valid_scope and valid_sig,
        "signed_or_landed_by_toolkit": False,
        "canonical_paths": scope,
        "sha256": pinned,
        "scope_verified": valid_scope,
        "signature_verified": valid_sig,
        "signer_fingerprint": signature.get("fingerprint", "") if valid_sig else "",
        "reason": preflight.get("reason") or signature.get("reason") or "",
    }
