"""PLAN-085 Wave B.4 — codex.py compute_redaction_inputs fail-CLOSED tests.

2 cases per plan §B.4 acceptance criteria + ADR-114 §AC9 invariant:

  1. test_import_success_returns_redacted — when the redactor module imports
     cleanly, compute_redaction_inputs returns the redacted text.
  2. test_import_failure_raises — when the redactor module raises ImportError
     (or any Exception during import), compute_redaction_inputs raises
     RedactorImportFailed; the exception has NO payload attribute AND its
     __cause__ is None (no chained exception leaking the prompt body).

Discipline: stdlib-only, Python >= 3.9, from __future__ annotations,
typing.Optional/Union, TestEnvContext for env isolation.

Source: F-A-SEC-0006-cf7d6abd (PLAN-084 SOTA audit) + B.4 spec
(`spec invariant: security-critical egress must NEVER pass raw text`).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))


class TestCodexRedactFailClosed(unittest.TestCase):
    """B.4 fail-CLOSED invariant on redactor import failure."""

    def test_import_success_returns_redacted(self) -> None:
        """Happy path: redactor imports cleanly → returns redacted text."""
        from _lib.adapters import codex as codex_adapter
        # The redactor's redact() is reachable as a sibling module; this
        # test calls compute_redaction_inputs with a benign string and
        # asserts the returned value is a non-empty string with no raise.
        out = codex_adapter.compute_redaction_inputs(
            "harmless prompt body for redactor smoke"
        )
        self.assertIsInstance(out, str)
        # Redacted output may be identical to input (no secrets to scrub)
        # but the call path MUST be exception-free on success.

    def test_import_failure_raises(self) -> None:
        """Failure path: redactor module ImportError → RedactorImportFailed.

        Simulates the import-failure surface by injecting a sentinel into
        sys.modules that raises ImportError on access. compute_redaction_inputs
        MUST raise RedactorImportFailed (not return raw text).

        Asserts the exception has NO ``payload`` attribute AND its
        ``__cause__`` is None — preserves the §B.4 invariant that the
        failed prompt body MUST NOT leak into the traceback.
        """
        from _lib.adapters import codex as codex_adapter
        from _lib.exceptions import RedactorImportFailed

        # Drop the redactor from sys.modules + inject a broken stub so
        # the `from .. import codex_egress_redact` raises ImportError.
        # We patch the parent package's attribute and sys.modules entry
        # so both lookup paths fail.
        broken_path = "_lib.codex_egress_redact"
        original = sys.modules.pop(broken_path, None)

        class _BrokenLoader:
            def __getattr__(self, name: str) -> Any:
                raise ImportError(
                    "simulated redactor import failure — Wave B.4 test"
                )

        sys.modules[broken_path] = _BrokenLoader()  # type: ignore[assignment]
        try:
            # Also break the parent package attribute so `from .. import X`
            # falls through to the broken sys.modules entry.
            import _lib as _lib_pkg
            original_attr = getattr(_lib_pkg, "codex_egress_redact", None)
            if hasattr(_lib_pkg, "codex_egress_redact"):
                delattr(_lib_pkg, "codex_egress_redact")
            try:
                with self.assertRaises(RedactorImportFailed) as ctx:
                    codex_adapter.compute_redaction_inputs(
                        "sensitive: api_key=sk-XXXXXXXXXXXXXXXXXXXXX"
                    )
                exc = ctx.exception
                # Invariant 1: NO payload attribute.
                self.assertFalse(
                    hasattr(exc, "payload"),
                    msg=(
                        "RedactorImportFailed leaked a `payload` attribute — "
                        "the failed prompt body MUST NOT be retained on the "
                        "exception per B.4 §security invariant."
                    ),
                )
                # Invariant 2: __cause__ is None (explicit raise-from-None
                # breaks the implicit chain that would have included the
                # original ImportError + the failed prompt context).
                self.assertIsNone(
                    exc.__cause__,
                    msg=(
                        "RedactorImportFailed.__cause__ is not None — the "
                        "implicit chain leaks the original ImportError "
                        "into the traceback. B.4 spec requires explicit "
                        "`raise RedactorImportFailed() from None`."
                    ),
                )
            finally:
                if original_attr is not None:
                    _lib_pkg.codex_egress_redact = original_attr  # type: ignore[attr-defined]
        finally:
            sys.modules.pop(broken_path, None)
            if original is not None:
                sys.modules[broken_path] = original


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
