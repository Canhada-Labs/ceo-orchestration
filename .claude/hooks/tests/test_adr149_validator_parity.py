"""test_adr149_validator_parity.py — independent-mirror parity (PLAN-163 T1.2d).

ADR-149 Decision lines 39-43: `agent_frontmatter.py` owns the canonical
VETO-floor constant, while `validate-governance.sh`, `escalation_signals.py`
(prefix-derived) and `tier_policy_cli` carry INDEPENDENT literals by
defense-in-depth doctrine. Independence means the mirrors can silently
drift — codex r2 #7 caught exactly that: the shell case-arm and
`VALID_MODEL_IDS` still accepted only the 4 pre-Claude-5 ids while the
ADR working set grew.

This test ties every independent validator to the machine-parseable
ADR-149 blocks, NON-VACUOUSLY (set equality where the surface allows it,
plus an explicit known-bad id that must be rejected — a vacuous
"contains" pass cannot go green here):

- `AVAILABLE_MODELS_WORKING_SET` / `VETO_FLOOR_ALLOWED` /
  `FALLBACK_MODEL_CHAIN` parsed from the ADR text (same tolerant block
  parser as `generate-available-models.py`).
- `_lib.agent_frontmatter.VETO_FLOOR_ALLOWED` == ADR floor block
  (name-to-name set equality — count-equality does not catch swaps).
- `validate-governance.sh` model case-arm == working set plus the
  documented dated-haiku alias (parsed from the script bytes).
- `tier_policy_cli._types.VALID_MODEL_IDS` == working set with the
  documented dated-haiku substitution.
- `_lib.model_routing._ROUTING_TABLE` values inside the working set.
- `audit_log._ADR_052_ROLE_TO_MODEL` values inside the working set
  (dated-haiku alias allowed).
- `scripts/local/smoke-install-parity.sh` ALLOWED_MODELS covers the
  working set (dated-haiku substitution) and rejects the retired id.

Known-bad sentinel: ``claude-opus-4-1`` (retires 2026-08-05) must be
REJECTED by every surface — this is the red path proving the assertions
have teeth.

POST-APPLY SEMANTICS — ships staged under
``.claude/plans/PLAN-163/staged/main-pack/`` and runs green only after
the pack lands (the live tree still carries the 4-id mirrors today).

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path
from typing import Dict, List

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib.agent_frontmatter import VETO_FLOOR_ALLOWED  # noqa: E402
from _lib.model_routing import _ROUTING_TABLE  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
ADR_PATH = REPO_ROOT / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"
VALIDATE_SH = REPO_ROOT / ".claude" / "scripts" / "validate-governance.sh"
PARITY_SH = REPO_ROOT / "scripts" / "local" / "smoke-install-parity.sh"
SCRIPTS_DIR = REPO_ROOT / ".claude" / "scripts"
AUDIT_LOG_PY = REPO_ROOT / ".claude" / "hooks" / "audit_log.py"

#: The one documented id-form divergence between the ADR working set and
#: the agent-frontmatter surfaces: agent files + tier_policy_cli carry the
#: DATED haiku id while the working set carries the alias form
#: (PLAN-045 P0-05 full-id doctrine vs harness alias). Any other
#: divergence is drift.
HAIKU_ALIAS = "claude-haiku-4-5"
HAIKU_DATED = "claude-haiku-4-5-20251001"

#: Known-bad sentinel: retired generation that every mirror must reject.
RETIRED_ID = "claude-opus-4-1"

_ID_RE = re.compile(r'"([A-Za-z0-9][A-Za-z0-9._\[\]-]*)"')


def _block_ids(text: str, token: str) -> List[str]:
    """Quoted ids inside the ``token = (...)``/``{...}`` literal."""
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


def _adr_text() -> str:
    return ADR_PATH.read_text(encoding="utf-8")


def _working_set() -> List[str]:
    return _block_ids(_adr_text(), "AVAILABLE_MODELS_WORKING_SET")


def _adr_floor() -> List[str]:
    return _block_ids(_adr_text(), "VETO_FLOOR_ALLOWED")


def _load_audit_log_module():
    spec = importlib.util.spec_from_file_location(
        "ceo_audit_log_parity_under_test", str(AUDIT_LOG_PY)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestAdrBlocksPresent(TestEnvContext):
    """The machine-parseable source blocks exist and carry the refresh."""

    def test_working_set_carries_claude5_refresh(self) -> None:
        ws = _working_set()
        self.assertTrue(ws, "AVAILABLE_MODELS_WORKING_SET block missing")
        self.assertIn("claude-opus-5", ws, "ADR-181 refresh id missing")
        self.assertIn("claude-sonnet-5", ws, "ADR-181 refresh id missing")
        self.assertIn(
            "claude-fable-5-1", ws,
            "ADR-149 Amendment 2 (S338) id missing from the working set",
        )
        self.assertEqual(ws[-1], "claude-fable-5-1", "A2 append must be LAST")
        self.assertNotIn(RETIRED_ID, ws)

    def test_floor_is_subset_of_working_set(self) -> None:
        ws, floor = _working_set(), _adr_floor()
        self.assertTrue(floor, "VETO_FLOOR_ALLOWED block missing")
        for member in floor:
            self.assertIn(member, ws)

    def test_fallback_chain_inside_floor(self) -> None:
        chain = _block_ids(_adr_text(), "FALLBACK_MODEL_CHAIN")
        self.assertTrue(chain, "FALLBACK_MODEL_CHAIN block missing")
        floor = _adr_floor()
        for member in chain:
            self.assertIn(
                member, floor,
                "fallback member escapes VETO_FLOOR_ALLOWED (A1.3 clause a)",
            )


class TestAgentFrontmatterMirror(TestEnvContext):
    """Canonical runtime constant == ADR floor block (name-to-name)."""

    def test_veto_floor_allowed_set_equality(self) -> None:
        self.assertEqual(
            set(VETO_FLOOR_ALLOWED),
            set(_adr_floor()),
            "agent_frontmatter.VETO_FLOOR_ALLOWED drifted from the ADR-149 "
            "VETO_FLOOR_ALLOWED block (set equality, not subset — swaps "
            "must redden)",
        )

    def test_retired_id_rejected(self) -> None:
        self.assertNotIn(RETIRED_ID, VETO_FLOOR_ALLOWED)


class TestValidateGovernanceMirror(TestEnvContext):
    """Shell case-arm literal == working set + dated-haiku alias."""

    def _case_ids(self) -> List[str]:
        text = VALIDATE_SH.read_text(encoding="utf-8")
        # The model-lint case arm: claude-...|...|"") — one line by
        # construction (ends with the empty-string alternative + the
        # case-arm closing paren); parse it rather than trusting line
        # numbers.
        m = re.search(r'^\s*(claude-[a-z0-9|.-]+)\|""\)\s*$', text, re.M)
        self.assertIsNotNone(
            m, "model case-arm not found in validate-governance.sh"
        )
        return [tok for tok in m.group(1).split("|") if tok and tok != '""']

    def test_case_arm_equals_working_set_plus_dated_haiku(self) -> None:
        expected = set(_working_set()) | {HAIKU_DATED}
        self.assertEqual(
            set(self._case_ids()),
            expected,
            "validate-governance.sh model case-arm drifted from the "
            "ADR-149 working set (independent mirror, ADR-149:39-43)",
        )

    def test_retired_id_rejected(self) -> None:
        self.assertNotIn(RETIRED_ID, self._case_ids())


class TestTierPolicyCliMirror(TestEnvContext):
    """tier_policy_cli VALID_MODEL_IDS == working set (dated-haiku form)."""

    def _valid_ids(self) -> List[str]:
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        from tier_policy_cli._types import VALID_MODEL_IDS  # noqa: E402
        return list(VALID_MODEL_IDS)

    def test_valid_model_ids_equal_working_set(self) -> None:
        expected = (set(_working_set()) - {HAIKU_ALIAS}) | {HAIKU_DATED}
        self.assertEqual(
            set(self._valid_ids()),
            expected,
            "tier_policy_cli VALID_MODEL_IDS drifted from the ADR-149 "
            "working set (independent mirror, ADR-149:39-43; the dated "
            "haiku substitution is the single documented divergence)",
        )

    def test_retired_id_rejected(self) -> None:
        self.assertNotIn(RETIRED_ID, self._valid_ids())


class TestRoutingSurfacesInsideWorkingSet(TestEnvContext):
    """Routing tables never advise a model outside availability."""

    def test_model_routing_table_inside_working_set(self) -> None:
        ws = set(_working_set())
        for task_class, model in sorted(_ROUTING_TABLE.items()):
            self.assertIn(
                model, ws,
                "model_routing._ROUTING_TABLE[{}] = {} escapes the ADR-149 "
                "working set".format(task_class, model),
            )

    def test_audit_log_role_map_inside_working_set(self) -> None:
        module = _load_audit_log_module()
        table: Dict[str, str] = module._ADR_052_ROLE_TO_MODEL
        allowed = set(_working_set()) | {HAIKU_DATED}
        for role, model in sorted(table.items()):
            self.assertIn(
                model, allowed,
                "audit_log._ADR_052_ROLE_TO_MODEL[{}] = {} escapes the "
                "ADR-149 working set".format(role, model),
            )


class TestSmokeParityAllowlistMirror(TestEnvContext):
    """smoke-install-parity ALLOWED_MODELS covers the working set."""

    def _allowed(self) -> List[str]:
        text = PARITY_SH.read_text(encoding="utf-8")
        m = re.search(r'^ALLOWED_MODELS="([^"]+)"\s*$', text, re.M)
        self.assertIsNotNone(
            m, "ALLOWED_MODELS not found in smoke-install-parity.sh"
        )
        return m.group(1).split()

    def test_working_set_covered(self) -> None:
        allowed = set(self._allowed())
        for mid in set(_working_set()) - {HAIKU_ALIAS}:
            self.assertIn(
                mid, allowed,
                "smoke-install-parity ALLOWED_MODELS missing working-set "
                "id {} (T1.7)".format(mid),
            )
        self.assertIn(HAIKU_DATED, allowed)

    def test_retired_id_rejected(self) -> None:
        self.assertNotIn(RETIRED_ID, self._allowed())


if __name__ == "__main__":
    unittest.main()
