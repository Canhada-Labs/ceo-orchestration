"""PLAN-182 (S325) — no TEMPLATE rebuilds the legacy project-slug literal.

Why an AFFIRMATIVE contract and not byte-parity with the live file: the
orphan template and its live counterpart differ by ~26 lines (26397 b vs
24650 b at the time of writing) for reasons that have nothing to do with path
resolution, so a byte-parity test would be born RED and would stay red for
every legitimate divergence. The contract asserted here is instead the one
that actually matters: no template CONSTRUCTS
`$HOME/.claude/projects/ceo-orchestration` unless the line carries the
documented partial-upgrade allowance marker.

Why templates need their own test at all: `derive-audit-family.py
--assert-no-local-slug` returns 0, but `templates/` is NOT in its census
scope (measured S325: zero `templates/` paths in its output). That gate asks
"do RUNTIME modules of THIS repo re-derive the slug?" — a template is runtime
of the ADOPTER's repo, so a green there says nothing about this class. This is
the "instrument green with a stale question" shape, and the gap is what let
the orphan survive PLAN-182 W1.

Blast radius of the defect being pinned: an adopter installing the orphan
wrote its statusline sidecar into a directory named after THIS framework, so
two different adopters under one $HOME shared a state directory and their
HMAC chains interleaved — the exact entanglement PLAN-182 W1 closed for the
live tree.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
TEMPLATES = REPO / "templates"
STATUSLINE_TEMPLATE = TEMPLATES / "scripts" / "statusline-ceo.py"

_HOOKS_DIR = REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# The legacy literal, matched as a CONSTRUCTED path rather than as prose.
#
# Two forms, and the second one was a FALSE GREEN until the S325 rail caught
# it: the Python idiom (`"projects" / "ceo-orchestration"`) and the SHELL
# idiom, where the segment continues into a path
# (`.../projects/ceo-orchestration/state"`). The original pattern required a
# quote immediately after the segment, so every suffixed use — including the
# two delivered pre-push gates — slipped through.
#
# The trailing boundary is therefore a path separator, a quote, or
# end-of-line; NOT "quote only". A prose mention (as in this file's own
# docstring, or a sentence ending in a period) still does not match, which is
# what keeps the guard from tripping on its own documentation.
_LITERAL_RE = re.compile(
    r"""["']projects["']\s*/\s*["']ceo-orchestration["']"""
    r"""|projects/ceo-orchestration(?=["'/]|$)"""
)
_ALLOW_MARKER = "rp-allow:"

# Debt DECLARED by path, never hidden by a blind pattern. Each entry is a
# template that still builds the legacy literal and CANNOT be cured without a
# canonical edit; the reason is recorded so the entry is auditable rather than
# an excuse. `rp-allow:` is deliberately NOT used for these — that marker
# means "documented partial-upgrade fallback", and these are neither.
_DECLARED_DEBT: dict = {}
# S326 (2026-08-24): both pre-push review gates were cured — they call the
# resolver CLI (`runtime_paths.py --state-dir`, PLAN-182 OQ-6) — so their
# entries left this dict. The machinery stays: a future template that rebuilds
# the literal lands as an OFFENDER, and a future entry here rots loudly.


class TestTemplatesUseSingleResolver(TestEnvContext):
    def test_no_template_constructs_the_legacy_literal(self) -> None:
        """Affirmative census over the WHOLE templates/ tree, not one file.

        Scoping this to statusline-ceo.py would re-create the blindness it is
        fixing: the next template to copy the idiom would land unseen.
        """
        self.assertTrue(TEMPLATES.is_dir(), "templates/ not found at %s" % TEMPLATES)

        scanned = 0
        offenders = []
        debt_seen = set()
        for path in sorted(TEMPLATES.rglob("*")):
            if not path.is_file() or path.suffix not in {".py", ".sh"}:
                continue
            scanned += 1
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if not _LITERAL_RE.search(line):
                    continue
                if _ALLOW_MARKER in line:
                    continue  # documented partial-upgrade fallback
                rel = path.relative_to(REPO).as_posix()
                if rel in _DECLARED_DEBT:
                    debt_seen.add(rel)
                    continue
                offenders.append(
                    "%s:%d: %s" % (path.relative_to(REPO), lineno, line.strip())
                )

        # Anti-vacuity: a census that scanned nothing passes trivially.
        self.assertGreater(
            scanned,
            0,
            "scanned zero template scripts — the census is vacuous, so a green "
            "here proves nothing",
        )
        self.assertEqual(
            offenders,
            [],
            "template(s) rebuild the legacy project literal instead of calling "
            "the single resolver (ADR-001). Each adopter installing these "
            "writes into a dir named after THIS framework, entangling their "
            "HMAC chain with every other project under the same $HOME:\n%s"
            % "\n".join(offenders),
        )

        # The declared-debt list must not rot into a permanent excuse: if a
        # listed path no longer builds the literal, it was cured and the entry
        # has to go. Failing here is the good kind of red.
        stale_debt = sorted(set(_DECLARED_DEBT) - debt_seen)
        self.assertEqual(
            stale_debt,
            [],
            "declared-debt entr(ies) no longer build the legacy literal — "
            "they were cured, so remove them from _DECLARED_DEBT instead of "
            "carrying a stale exemption: %s" % stale_debt,
        )

    def test_pre_push_gates_call_the_single_resolver(self) -> None:
        """S326 — the cure is a CALL, not just the absence of the literal: each
        delivered pre-push gate resolves its state dir through the resolver CLI
        (`runtime_paths.py --state-dir`) and never through a rebuilt path."""
        for vendor in ("codex", "grok"):
            rel = "templates/%s/pre-push-review-gate.sh" % vendor
            text = (REPO / rel).read_text(encoding="utf-8")
            self.assertIn(
                '_lib/runtime_paths.py"', text,
                "%s does not reference the single resolver" % rel)
            self.assertIn(
                "--state-dir", text,
                "%s references the resolver but not its --state-dir mode" % rel)
            self.assertNotIn(
                "projects/ceo-orchestration", text,
                "%s still rebuilds the legacy literal" % rel)

    def test_allow_marker_is_load_bearing(self) -> None:
        """Positive control for the guard itself.

        If the marker were ignored, the census above would be green for the
        wrong reason (or red on a legitimate fallback). Both directions are
        asserted on synthetic lines so the control never depends on the tree's
        current contents.
        """
        bare = '    return Path(home) / ".claude" / "projects" / "ceo-orchestration"'
        marked = bare + "  # rp-allow: partial-upgrade-fallback"
        self.assertIsNotNone(
            _LITERAL_RE.search(bare), "the guard does not match the literal it exists for"
        )
        self.assertIsNotNone(
            _LITERAL_RE.search(marked), "the marker must not hide the match itself"
        )
        self.assertNotIn(_ALLOW_MARKER, bare)
        self.assertIn(_ALLOW_MARKER, marked)

    def test_statusline_template_resolves_per_project(self) -> None:
        """Behavioural, not textual: the template must resolve BY PROJECT.

        Textual absence of the literal is necessary but not sufficient — a
        template could omit the literal and still resolve to a constant. So
        this loads the template and asserts the resolved dir carries the
        adopter's own path-derived slug.
        """
        self.assertTrue(
            STATUSLINE_TEMPLATE.is_file(),
            "statusline template missing at %s" % STATUSLINE_TEMPLATE,
        )
        spec = importlib.util.spec_from_file_location(
            "_tpl_statusline", STATUSLINE_TEMPLATE
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)

        # `TestEnvContext` PINS CEO_AUDIT_LOG_DIR to its sandbox
        # (_lib/testing.py:159), and `_audit_dir()` honours that override
        # FIRST — so inside this base class the resolver branch is
        # unreachable unless the override is lifted for the call. Lift it
        # via mock.patch.dict (never a direct env write: the corpus gate
        # `check-test-env-hygiene.py` rejects those, and it is right to).
        # HOME is already the sandboxed one, and CLAUDE_PROJECT_DIR_NATIVE
        # was already stripped by setUp, so this touches exactly one key.
        env = {k: v for k, v in os.environ.items() if k != "CEO_AUDIT_LOG_DIR"}
        env["CLAUDE_PROJECT_DIR"] = str(self.project_dir)

        with mock.patch.dict(os.environ, env, clear=True):
            spec.loader.exec_module(module)

            self.assertIsNotNone(
                getattr(module, "_rp", None),
                "the template did not import the single resolver — it fell "
                "back to the legacy path even though _lib is present in this "
                "checkout",
            )
            resolved = str(module._audit_dir())

        self.assertNotIn(
            "projects/ceo-orchestration",
            resolved,
            "the template resolved to the framework-named dir: %s" % resolved,
        )
        # The slug the harness itself derives from the project path: `/` -> `-`.
        # `os.path.abspath`, NOT `Path.resolve()`: the resolver normalises the
        # separator only and does not follow symlinks (runtime_paths.py:110),
        # and on macOS `/var` is a symlink to `/private/var` — so `resolve()`
        # would build `-private-var-...` and compare it against the resolver's
        # `-var-...`. That mismatch measures the ASSERTION, not the code.
        expected_slug = os.path.abspath(str(self.project_dir)).replace(os.sep, "-")
        self.assertIn(
            expected_slug,
            resolved,
            "the resolved dir does not carry this project's own path-derived "
            "slug (want %r inside %r)" % (expected_slug, resolved),
        )


if __name__ == "__main__":
    unittest.main()
