"""Domain exceptions for live-adapter + credential lifecycle (PLAN-085 Wave C).

Minimal, stdlib-only. Keep here only exceptions that callers outside the
declaring module need to ``except``. Adapter-internal failures already live
in ``_lib/adapters/live/__init__.py`` (LiveAdapter* hierarchy).

ADR-040-AMEND-2 (PLAN-085 Wave 0 SHIPPED S109) authorizes credential
blocking at max-age — ``CredentialExpired`` is the exception type raised
by adapter ``invoke()`` when the active credential has crossed
``credential_max_age_days`` and no emergency-override ticket is in scope.

# TARGET PATH (apply via Owner-signed sentinel ceremony):
#   .claude/hooks/_lib/exceptions.py
"""

from __future__ import annotations


class CredentialExpired(Exception):
    """Raised by live-adapter ``invoke()`` when the active credential has
    crossed ``credential_max_age_days`` per ADR-040 §4 + ADR-040-AMEND-2.

    The exception message NEVER carries the credential value. Callers
    may inspect ``.age_days`` and ``.max_age_days`` for the numeric
    thresholds; ``.provider`` for the policy provider slug.
    """

    def __init__(
        self,
        provider: str,
        age_days: int,
        max_age_days: int,
        message: str = "",
    ) -> None:
        self.provider = provider
        self.age_days = int(age_days)
        self.max_age_days = int(max_age_days)
        super().__init__(
            message
            or (
                f"credential for provider={provider!r} is {age_days}d old "
                f"(max_age_days={max_age_days}); rotate or set "
                f"CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE=<ticket-id>"
            )
        )


class RedactorImportFailed(Exception):
    """Raised by ``compute_redaction_inputs`` when the Codex egress
    redactor module fails to import (PLAN-085 Wave B.4).

    Fail-CLOSED invariant (F-A-SEC-0006-cf7d6abd + ADR-114 §AC9):
    the security-critical egress path MUST NEVER pass raw text on a
    redactor outage. The caller catches this exception and blocks the
    Codex invocation.

    The exception carries NO ``payload`` attribute. The caller MUST
    use ``raise RedactorImportFailed() from None`` to prevent the
    implicit ``__cause__`` chain from leaking the failed prompt body
    into the traceback. Audit emit (``codex_redact_import_failure``,
    advisory) is the OUT-OF-BAND breadcrumb for forensic correlation.
    """

    pass

class CodexResponseTooLarge(Exception):
    """Raised when Codex CLI stdout exceeds the strict-JSON size cap.

    PLAN-086 Wave A.6 (Sec-1 fold per handoff §9.2). Strict-JSON path
    in ``_lib/adapters/codex.py`` clamps response at 256 KB. Oversize
    response raises this exception with NO payload attribute — the
    raw stdout MUST NOT leak into the traceback via __cause__ chain.

    Caller pattern: ``raise CodexResponseTooLarge() from None``.
    """

    pass


class CodexJsonInvalid(Exception):
    """Raised when Codex strict-JSON stdout fails JSON parse OR schema.

    PLAN-086 Wave A.6 (Sec-1 fold per handoff §9.2). Carries NO payload
    attribute. Caller pattern: ``raise CodexJsonInvalid() from None``.

    Tripping conditions:
      - ``json.loads()`` ValueError / JSONDecodeError
      - JSONSchema validation failure via ``_lib/contract.py``
      - Control-character injection in untrusted strings
      - Truncated input (oversize within cap, but cut mid-token)
    """

    pass


__all__ = [
    "CredentialExpired",
    "RedactorImportFailed",
    "CodexResponseTooLarge",
    "CodexJsonInvalid",
]
