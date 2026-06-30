"""Fixture: emit_generic with a dynamic action arg (no string literal).

Detector #6 should NOT flag this — there's no literal action name to
phantom-check; an AST-only scan reads only Constant string values.
"""

from __future__ import annotations


def emit_dynamic(name: str) -> None:
    from _lib import audit_emit  # type: ignore[import-not-found]
    audit_emit.emit_generic(action=name)  # variable, not literal
