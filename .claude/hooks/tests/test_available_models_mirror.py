"""test_available_models_mirror.py — ADR-149 working set <-> settings mirror.

PLAN-135 W1 unit s1 (HARVEST-REPORT S1a/S1b; ADR-149 Amendment 1).

POST-APPLY SEMANTICS — this file ships STAGED under
``.claude/plans/PLAN-135/staged/w1/files/`` and runs green only AFTER the
Owner ceremony applies the W1 bundle (the ADR-149 Amendment 1 text + the
10-s1/11-s1 jq merges). It is staged, not live, because the live branch
must stay green standalone (COUPLING RULE): pre-ceremony, settings carry no
``availableModels``/``fallbackModel`` keys and the live ADR carries no
Amendment 1, so these assertions would redden CI.

Coverage:
- resolved ``availableModels`` (dogfood + template) == generator output from
  the (applied) ADR — single-source mirror, order included;
- ``-k fallback`` cases (the plan's S1b Check selector): chain length <= 3,
  every member inside the working set, chain == the ADR FALLBACK_MODEL_CHAIN
  block, and the three S1b amendment clauses present in the ADR text
  (never-escapes / halt-on-exhausted / pin-and-declare-confound);
- generator ``--check`` exits 0 against the applied tree.

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
ADR_PATH = REPO_ROOT / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"
SETTINGS_PATH = REPO_ROOT / ".claude" / "settings.json"
TEMPLATE_PATH = REPO_ROOT / "templates" / "settings" / "settings.base.json"
GENERATOR = REPO_ROOT / ".claude" / "scripts" / "generate-available-models.py"

FALLBACK_CHAIN_MAX = 3
_ID_RE = re.compile(r'"([A-Za-z0-9][A-Za-z0-9._\[\]-]*)"')


def _adr_text() -> str:
    return ADR_PATH.read_text(encoding="utf-8")


def _block_ids(text: str, token: str) -> list:
    """Quoted ids inside the ``token = (...)``/``{...}`` literal (ADR blocks)."""
    idx = text.find(token)
    if idx < 0:
        return []
    open_idx = -1
    open_ch = ""
    for i in range(idx, min(len(text), idx + 200)):
        if text[i] in "({":
            open_idx, open_ch = i, text[i]
            break
    if open_idx < 0:
        return []
    close_ch = ")" if open_ch == "(" else "}"
    depth, end_idx = 0, -1
    for i in range(open_idx, len(text)):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                end_idx = i
                break
    if end_idx < 0:
        return []
    seen, ids = set(), []
    for match in _ID_RE.finditer(text[open_idx : end_idx + 1]):
        mid = match.group(1)
        if mid not in seen:
            seen.add(mid)
            ids.append(mid)
    return ids


def _run_generator(*args: str) -> "subprocess.CompletedProcess":
    return subprocess.run(
        [sys.executable, str(GENERATOR)] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
    )


def _settings(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestAvailableModelsMirror(TestEnvContext):
    """availableModels (dogfood + template) == generator output from the ADR."""

    def test_adr_carries_amendment_working_set_block(self) -> None:
        ids = _block_ids(_adr_text(), "AVAILABLE_MODELS_WORKING_SET")
        self.assertTrue(
            ids,
            "ADR-149 Amendment 1 AVAILABLE_MODELS_WORKING_SET block missing — "
            "was the W1 bundle applied?",
        )
        # The working set must be a strict superset of the VETO floor,
        # preserving the floor members (A1.1: two blocks, never merged).
        floor = _block_ids(_adr_text(), "VETO_FLOOR_ALLOWED")
        self.assertTrue(floor, "base VETO_FLOOR_ALLOWED block missing")
        for member in floor:
            self.assertIn(member, ids)

    def test_generator_emits_from_amendment_not_floor_fallback(self) -> None:
        proc = _run_generator()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            "AVAILABLE_MODELS_WORKING_SET",
            proc.stderr,
            "generator should source the Amendment 1 block post-apply",
        )
        self.assertNotIn("falling back", proc.stderr)

    def test_settings_available_models_match_generator(self) -> None:
        proc = _run_generator()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        generated = json.loads(proc.stdout)["availableModels"]
        resolved = _settings(SETTINGS_PATH).get("availableModels")
        self.assertEqual(
            resolved,
            generated,
            "dogfood .claude/settings.json availableModels drifted from "
            "ADR-149 Amendment 1 (order is normative)",
        )

    def test_template_available_models_match_generator(self) -> None:
        proc = _run_generator()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        generated = json.loads(proc.stdout)["availableModels"]
        resolved = _settings(TEMPLATE_PATH).get("availableModels")
        self.assertEqual(
            resolved,
            generated,
            "templates/settings/settings.base.json availableModels drifted "
            "from ADR-149 Amendment 1 (Doctrine 2 dual-surface)",
        )

    def test_check_mode_green_post_apply(self) -> None:
        proc = _run_generator("--check")
        self.assertEqual(
            proc.returncode,
            0,
            "--check reddened post-apply:\n{}\n{}".format(proc.stdout, proc.stderr),
        )
        self.assertIn("MATCH", proc.stdout)


class TestFallbackChain(TestEnvContext):
    """S1b fallback cases — selected by ``pytest -k fallback`` (plan Check)."""

    def _chain(self, path: Path) -> list:
        value = _settings(path).get("fallbackModel")
        self.assertIsNotNone(
            value, "fallbackModel absent in {} — was the W1 bundle applied?".format(path)
        )
        return [value] if isinstance(value, str) else list(value)

    def test_fallback_chain_length_le_3(self) -> None:
        for path in (SETTINGS_PATH, TEMPLATE_PATH):
            chain = self._chain(path)
            self.assertGreaterEqual(len(chain), 1, path)
            self.assertLessEqual(
                len(chain),
                FALLBACK_CHAIN_MAX,
                "{}: chain exceeds the documented 3-model cap".format(path),
            )

    def test_fallback_members_inside_working_set(self) -> None:
        working_set = _block_ids(_adr_text(), "AVAILABLE_MODELS_WORKING_SET")
        self.assertTrue(working_set)
        for path in (SETTINGS_PATH, TEMPLATE_PATH):
            for member in self._chain(path):
                self.assertIn(
                    member,
                    working_set,
                    "{}: fallback member escapes the working set "
                    "(ADR-149 A1.3 clause (a))".format(path),
                )

    def test_fallback_chain_matches_adr_block(self) -> None:
        adr_chain = _block_ids(_adr_text(), "FALLBACK_MODEL_CHAIN")
        self.assertTrue(adr_chain, "FALLBACK_MODEL_CHAIN block missing from ADR-149")
        for path in (SETTINGS_PATH, TEMPLATE_PATH):
            self.assertEqual(
                self._chain(path),
                adr_chain,
                "{}: fallbackModel drifted from the ADR chain block".format(path),
            )

    def test_fallback_chain_stays_inside_veto_floor(self) -> None:
        # Stronger than clause (a): while the chain serves governance
        # sessions, every member must be a VETO-floor member (A1.1 rationale).
        floor = _block_ids(_adr_text(), "VETO_FLOOR_ALLOWED")
        self.assertTrue(floor)
        for member in self._chain(SETTINGS_PATH):
            self.assertIn(member, floor)

    def test_fallback_never_escapes_clause_present_in_adr(self) -> None:
        self.assertIn("Fallback NEVER escapes the allowlist", _adr_text())

    def test_fallback_halt_on_exhausted_clause_present_in_adr(self) -> None:
        text = _adr_text()
        self.assertIn("All-fallbacks-exhausted = session halts", text)
        self.assertIn("never silently un-modeled", text)

    def test_fallback_confound_clause_present_in_adr(self) -> None:
        text = _adr_text()
        self.assertIn("declare fallback as a confound", text)
        self.assertIn("pin `--model`", text)


if __name__ == "__main__":
    unittest.main()
