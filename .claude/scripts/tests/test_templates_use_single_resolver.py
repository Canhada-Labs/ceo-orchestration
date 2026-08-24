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

# The legacy literal, matched as a CONSTRUCTED path rather than as prose: a
# comment or docstring naming it (as this very file's docstring does) must not
# trip the guard. The signature is the string appearing as a path segment
# inside a quoted expression next to `projects`.
_LITERAL_RE = re.compile(
    r"""["']projects["']\s*/\s*["']ceo-orchestration["']"""
    r"""|projects/ceo-orchestration["']"""
)
_ALLOW_MARKER = "rp-allow:"


class TestTemplatesUseSingleResolver(TestEnvContext):
    def test_no_template_constructs_the_legacy_literal(self) -> None:
        """Affirmative census over the WHOLE templates/ tree, not one file.

        Scoping this to statusline-ceo.py would re-create the blindness it is
        fixing: the next template to copy the idiom would land unseen.
        """
        self.assertTrue(TEMPLATES.is_dir(), "templates/ not found at %s" % TEMPLATES)

        scanned = 0
        offenders = []
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
