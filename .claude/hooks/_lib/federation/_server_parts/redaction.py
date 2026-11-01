"""Declarations extracted from federation.server; loaded by the facade."""
from __future__ import annotations

_REDACTION_FAIL_CLOSED_MARKER = object()


def _apply_redaction_pipeline(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Apply ``redact_secrets`` + ``pii_patterns.scan(...,mode="redact")``."""
    out: List[Dict[str, Any]] = []
    redact_secrets = None
    pii_scan = None
    load_error: Optional[str] = None
    try:
        try:
            from _lib import redact as _redact  # type: ignore[import]
            from _lib import pii_patterns as _pii  # type: ignore[import]
        except ImportError:
            import importlib
            _redact = importlib.import_module(".redact", package="_lib")
            _pii = importlib.import_module(".pii_patterns", package="_lib")
        redact_secrets = getattr(_redact, "redact_secrets", None)
        _pii_scan = getattr(_pii, "scan", None)
        if _pii_scan is not None:
            def _pii_redact_adapter(text: str) -> str:
                result = _pii_scan(text, mode="redact")
                return getattr(result, "redacted_text", text) or text
            pii_scan = _pii_redact_adapter
    except Exception as e:  # noqa: BLE001 — defense-in-depth
        load_error = "{0}:{1}".format(type(e).__name__, str(e)[:80])

    if redact_secrets is None or pii_scan is None:
        try:
            sys.stderr.write(
                "[federation.server] AC6 fail-CLOSED — redact_secrets={0!r} "
                "pii_scan={1!r} load_error={2!r}; refusing to serialise "
                "audit-summary events\n".format(
                    redact_secrets is not None,
                    pii_scan is not None,
                    load_error,
                )
            )
        except Exception:
            pass
        return []

    for ev in events:
        if not isinstance(ev, dict):
            continue
        try:
            blob = json.dumps(ev, ensure_ascii=False)
        except (TypeError, ValueError):
            continue
        try:
            blob = redact_secrets(blob)
        except Exception:
            continue
        try:
            blob = pii_scan(blob)
        except Exception:
            continue
        try:
            redacted = json.loads(blob)
        except (TypeError, ValueError):
            continue
        out.append(redacted)
    return out


# ---------------------------------------------------------------------------
# FederationServer — orchestrator
# ---------------------------------------------------------------------------


