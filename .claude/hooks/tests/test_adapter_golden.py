"""Cross-adapter golden-fixture conformance tests.

Sprint 5 Phase 4. Locks the adapter contract via byte-exact fixtures so
adding a new IDE adapter (Gemini CLI, Codex CLI, etc.) is a
fixture-comparison exercise — not a guessing game about field naming.

## Fixture layout

    tests/fixtures/normalized/<scenario>.json
        Canonical NormalizedEvent serialization (asdict()) for the
        scenario. Adapter-agnostic (used by the claude scenarios).

    tests/fixtures/adapters/<adapter>/normalized/<scenario>.json
        PLAN-155: adapter-local normalized expectation, preferred over
        the shared dir when present (codex scenario names are wire
        events like `stop.plain.json` and live with their adapter).

    tests/fixtures/adapters/<adapter>/in/<scenario>.json
        Wire-shape input (stdin payload) the adapter receives in this
        scenario. Bytes-identical to what the IDE actually sends.

    tests/fixtures/adapters/<adapter>/out/<decision_key>.json
        Wire-shape output (stdout JSON) the adapter writes for a given
        Decision. Decision keys are stable identifiers (`allow`,
        `block_with_reason`, etc.).

A new adapter passes the suite when:
1. Its `read_event(stdin)` parses every `<scenario>.json` under
   `adapters/<adapter>/in/` into a NormalizedEvent that round-trips to
   the same dict as the canonical normalized expectation
   (`adapters/<adapter>/normalized/<scenario>.json`, falling back to
   the shared `normalized/<scenario>.json` dir used by the claude
   scenarios).
2. Its `write_decision(decision)` produces output byte-equivalent to
   the corresponding `adapters/<adapter>/out/<decision_key>.json`.

## PLAN-155 Wave 1 additions (debate A4 — kill the vacuous green)

Before this wave the codex fixture dirs held only `.gitkeep` and every
per-adapter glob loop passed VACUOUSLY (the S254 dead-gate class:
static-green over an empty set). Now:

- the round-trip is parameterized over ALL `KNOWN_ADAPTERS`;
- a minimum-fixture-count assertion per adapter makes a
  `.gitkeep`-only dir FAIL;
- codex `out/` goldens cover allow, deny-with-reason,
  `additionalContext` passthrough, and the Stop-family block shape
  (the host-mode `write_decision` shape change is DELIBERATE — noted
  in ADR-161; the old Claude-shaped output was the "symbolic parity"
  era with no host-side production caller);
- every recorded codex `in/` fixture must carry
  `_meta.codex_cli_version` INSIDE the pin range of
  `.claude/governance/codex-cli-pin.txt` (debate A12): a pin bump goes
  RED until fixtures are re-recorded or explicitly waived via the
  ADR-111 ceremony;
- the PLAN-155 dispatch seam (`_lib.adapters.resolve()`) is asserted:
  env-driven dispatch, default claude, and the debate-A2 fail-CLOSED
  contract for explicitly-set-but-unresolvable `CEO_HOOK_ADAPTER`.

ADR-012 codifies the fixture contract; ADR-161 the codex host rows.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import unittest
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest import mock

# Make _lib importable
_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib import contract  # noqa: E402
from _lib import adapters as adapters_pkg  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


_FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"
_NORMALIZED_DIR = _FIXTURES_ROOT / "normalized"
_ADAPTERS_DIR = _FIXTURES_ROOT / "adapters"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CODEX_PIN_FILE = _REPO_ROOT / ".claude" / "governance" / "codex-cli-pin.txt"

# ---------------------------------------------------------------------------
# PLAN-155 A4 — anti-vacuous minimums. A `.gitkeep`-only fixture dir counts
# ZERO *.json files and must FAIL these floors. Raise a floor when new
# scenarios are recorded; never lower one below the recorded set.
# ---------------------------------------------------------------------------
_MIN_IN_FIXTURES: Dict[str, int] = {"claude": 3, "codex": 12}
_MIN_OUT_FIXTURES: Dict[str, int] = {"claude": 2, "codex": 3}

# Adapters whose `project` field is env-dependent (CLAUDE_PROJECT_DIR) vs
# deterministic from the wire (the codex host wire carries `cwd` on every
# event, so its normalized `project` is byte-comparable).
_ENV_DEPENDENT_PROJECT: Dict[str, bool] = {"claude": True, "codex": False}


def _expected_normalized_path(adapter: str, scenario: str) -> Path:
    """Per-adapter normalized dir first; shared normalized/ as fallback."""
    per_adapter = _ADAPTERS_DIR / adapter / "normalized" / scenario
    if per_adapter.is_file():
        return per_adapter
    return _NORMALIZED_DIR / scenario


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _normalized_to_dict(ev: contract.NormalizedEvent) -> Dict[str, Any]:
    """Convert NormalizedEvent to plain dict (ignores `raw_payload`)."""
    d = asdict(ev)
    # raw_payload is adapter-implementation-detail; not part of contract
    d.pop("raw_payload", None)
    return d


class GoldenFixturesTest(TestEnvContext):
    """Verify every shipping adapter conforms to the wire-shape contract."""

    def test_known_adapters_have_in_fixtures(self):
        """Every KNOWN_ADAPTER must ship an `in/` fixture directory."""
        for name in contract.KNOWN_ADAPTERS:
            in_dir = _ADAPTERS_DIR / name / "in"
            self.assertTrue(
                in_dir.is_dir(),
                f"missing {in_dir} — adapter '{name}' has no input fixtures",
            )

    def test_known_adapters_have_out_fixtures(self):
        """Every KNOWN_ADAPTER must ship an `out/` fixture directory."""
        for name in contract.KNOWN_ADAPTERS:
            out_dir = _ADAPTERS_DIR / name / "out"
            self.assertTrue(
                out_dir.is_dir(),
                f"missing {out_dir} — adapter '{name}' has no output fixtures",
            )

    def test_normalized_fixtures_present(self):
        """Each scenario in `in/` must have a matching normalized file.

        PLAN-155: per-adapter `adapters/<name>/normalized/` is checked
        first, then the shared `normalized/` dir (claude scenarios).
        """
        for name in contract.KNOWN_ADAPTERS:
            in_dir = _ADAPTERS_DIR / name / "in"
            for in_file in sorted(in_dir.glob("*.json")):
                norm_file = _expected_normalized_path(name, in_file.name)
                self.assertTrue(
                    norm_file.is_file(),
                    f"missing canonical {norm_file} for adapter scenario "
                    f"{name}/in/{in_file.name}",
                )

    def test_minimum_fixture_counts_per_adapter(self):
        """PLAN-155 A4: a `.gitkeep`-only fixture dir must FAIL, not pass.

        Every KNOWN_ADAPTER must ship at least the floor number of real
        `*.json` fixtures in BOTH `in/` and `out/` — the vacuous-green
        hole this closes is a glob loop over an empty directory.
        """
        for name in contract.KNOWN_ADAPTERS:
            with self.subTest(adapter=name):
                self.assertIn(
                    name, _MIN_IN_FIXTURES,
                    f"adapter '{name}' has no fixture floor — add it to "
                    "_MIN_IN_FIXTURES/_MIN_OUT_FIXTURES in this file",
                )
                n_in = len(list((_ADAPTERS_DIR / name / "in").glob("*.json")))
                n_out = len(list((_ADAPTERS_DIR / name / "out").glob("*.json")))
                self.assertGreaterEqual(
                    n_in, _MIN_IN_FIXTURES[name],
                    f"adapter '{name}' ships {n_in} in-fixtures; floor is "
                    f"{_MIN_IN_FIXTURES[name]} — an empty/.gitkeep-only dir "
                    "is the S254 vacuous-green class",
                )
                self.assertGreaterEqual(
                    n_out, _MIN_OUT_FIXTURES[name],
                    f"adapter '{name}' ships {n_out} out-fixtures; floor is "
                    f"{_MIN_OUT_FIXTURES[name]}",
                )

    def test_all_adapters_in_fixtures_round_trip_to_normalized(self):
        """PLAN-155 A4: the golden round-trip, parameterized over ALL
        KNOWN_ADAPTERS (not just claude). For each `in/` scenario, parse
        with the adapter and compare against the normalized expectation."""
        for name in contract.KNOWN_ADAPTERS:
            adapter_mod = contract.load_adapter(name)
            in_dir = _ADAPTERS_DIR / name / "in"
            in_files = sorted(in_dir.glob("*.json"))
            self.assertTrue(
                in_files, f"no in-fixtures for adapter '{name}' (vacuous)"
            )
            for in_file in in_files:
                with self.subTest(adapter=name, scenario=in_file.name):
                    raw = in_file.read_text(encoding="utf-8")
                    expected = _load_json(
                        _expected_normalized_path(name, in_file.name)
                    )
                    phase = expected.get("phase", "PreToolUse")
                    # Host-wire adapters take phase from the wire itself;
                    # passing the expected phase is a no-op there and the
                    # required routing hint for the claude adapter.
                    if phase not in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
                        ev = adapter_mod.read_event(io.StringIO(raw))
                    else:
                        ev = adapter_mod.read_event(io.StringIO(raw), phase=phase)
                    self.assertIsNone(
                        ev.parse_error,
                        f"parse_error for {name}/{in_file.name}: {ev.parse_error}",
                    )
                    actual = _normalized_to_dict(ev)
                    expected.pop("raw_payload", None)
                    if _ENV_DEPENDENT_PROJECT.get(name, True):
                        expected["project"] = actual["project"]
                    self.assertEqual(
                        actual,
                        expected,
                        f"mismatch for adapter={name} scenario={in_file.name}",
                    )

    def test_claude_in_fixtures_round_trip_to_normalized(self):
        """For each `claude/in/<scenario>.json`, parse with the claude
        adapter and verify the resulting NormalizedEvent matches the
        canonical `normalized/<scenario>.json`."""
        from _lib.adapters import claude as claude_adapter
        import io

        in_dir = _ADAPTERS_DIR / "claude" / "in"
        for in_file in sorted(in_dir.glob("*.json")):
            with self.subTest(scenario=in_file.name):
                raw = in_file.read_text(encoding="utf-8")
                # PLAN-006 Phase 1 pre-work (ADR-014, R-SB1): the phase
                # parameter is now explicit. Derive it from the fixture's
                # normalized counterpart to keep fixtures self-describing.
                expected_for_phase = _load_json(_NORMALIZED_DIR / in_file.name)
                phase = expected_for_phase.get("phase", "PreToolUse")
                ev = claude_adapter.read_event(io.StringIO(raw), phase=phase)
                self.assertIsNone(
                    ev.parse_error,
                    f"adapter parse_error for {in_file.name}: {ev.parse_error}",
                )

                actual = _normalized_to_dict(ev)
                expected = _load_json(_NORMALIZED_DIR / in_file.name)
                expected.pop("raw_payload", None)

                # `project` is env-dependent (CLAUDE_PROJECT_DIR); compare
                # against whatever the adapter resolved at parse time.
                expected["project"] = actual["project"]

                self.assertEqual(
                    actual,
                    expected,
                    f"mismatch for adapter=claude scenario={in_file.name}",
                )

    def test_claude_write_decision_allow(self):
        """A vanilla allow Decision serializes to the canonical allow fixture."""
        from _lib.adapters import claude as claude_adapter

        out = claude_adapter.write_decision(contract.allow())
        expected = (_ADAPTERS_DIR / "claude" / "out" / "allow.json").read_text(
            encoding="utf-8"
        ).rstrip("\n")
        self.assertEqual(out, expected)

    def test_claude_write_decision_block_with_reason(self):
        """A block Decision with reason+systemMessage matches the fixture."""
        from _lib.adapters import claude as claude_adapter

        out = claude_adapter.write_decision(
            contract.block(
                reason="missing_skill_content",
                system_message="Spawn blocked: prompt has no ## SKILL CONTENT section",
            )
        )
        expected = (_ADAPTERS_DIR / "claude" / "out" / "block_with_reason.json").read_text(
            encoding="utf-8"
        ).rstrip("\n")
        self.assertEqual(out, expected)


class ResolveAdapterTest(TestEnvContext):
    """Sprint 5: CEO_HOOK_ADAPTER env-var dispatch."""

    def test_resolve_adapter_default(self):
        os.environ.pop("CEO_HOOK_ADAPTER", None)
        self.assertEqual(contract.resolve_adapter(), "claude")

    def test_resolve_adapter_known(self):
        os.environ["CEO_HOOK_ADAPTER"] = "claude"
        self.assertEqual(contract.resolve_adapter(), "claude")

    def test_resolve_adapter_unknown_falls_back(self):
        # PLAN-006 added gemini to KNOWN_ADAPTERS (Sprint 6 Phase 2a).
        # PLAN-081 Phase 1-full added "codex" to KNOWN_ADAPTERS (2026-05-09).
        # Pick a name that stays unknown to keep this test future-proof.
        os.environ["CEO_HOOK_ADAPTER"] = "vertex-ai-fictional"
        self.assertEqual(contract.resolve_adapter(), "claude")

    def test_resolve_adapter_empty_falls_back(self):
        os.environ["CEO_HOOK_ADAPTER"] = ""
        self.assertEqual(contract.resolve_adapter(), "claude")

    def test_resolve_adapter_explicit_env_override(self):
        # Pass env explicitly (no os.environ mutation)
        env = {"CEO_HOOK_ADAPTER": "claude"}
        self.assertEqual(contract.resolve_adapter(env=env), "claude")
        env = {}
        self.assertEqual(contract.resolve_adapter(env=env), "claude")

    def test_load_adapter_returns_claude_module(self):
        os.environ.pop("CEO_HOOK_ADAPTER", None)
        mod = contract.load_adapter()
        self.assertTrue(hasattr(mod, "read_event"))
        self.assertTrue(hasattr(mod, "write_decision"))


class CodexOutGoldensTest(TestEnvContext):
    """PLAN-155 A4: byte-exact codex host-mode decision goldens.

    Host shape is selected EXPLICITLY via `Decision.extra['hookEventName']`
    (see `_lib/adapters/codex.py` role map); these tests are the byte
    contract for the shipped `templates/codex/hooks.json` command line.
    A deliberate shape change updates the fixture AND notes it in ADR-161.
    """

    def _golden(self, key: str) -> str:
        return (
            (_ADAPTERS_DIR / "codex" / "out" / key)
            .read_text(encoding="utf-8")
            .rstrip("\n")
        )

    def test_allow_golden(self):
        from _lib.adapters import codex as codex_adapter

        out = codex_adapter.write_decision(
            contract.Decision(allow=True, extra={"hookEventName": "PreToolUse"})
        )
        self.assertEqual(out, self._golden("allow.json"))

    def test_deny_with_reason_golden(self):
        from _lib.adapters import codex as codex_adapter

        out = codex_adapter.write_decision(
            contract.Decision(
                allow=False,
                reason="unsentineled write to a canonical path (check_canonical_edit)",
                extra={"hookEventName": "PreToolUse"},
            )
        )
        self.assertEqual(out, self._golden("deny_with_reason.json"))
        parsed = json.loads(out)
        hso = parsed["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertIn("canonical path", hso["permissionDecisionReason"])

    def test_additional_context_passthrough_golden(self):
        from _lib.adapters import codex as codex_adapter

        out = codex_adapter.write_decision(
            contract.Decision(
                allow=True,
                extra={
                    "hookEventName": "SubagentStart",
                    "additionalContext": (
                        "Spawn protocol: include ## AGENT PROFILE, "
                        "## SKILL CONTENT, ## FILE ASSIGNMENT sections "
                        "in the subagent brief."
                    ),
                },
            )
        )
        self.assertEqual(out, self._golden("additional_context.json"))
        parsed = json.loads(out)
        self.assertIn(
            "## FILE ASSIGNMENT",
            parsed["hookSpecificOutput"]["additionalContext"],
        )

    def test_stop_block_golden(self):
        from _lib.adapters import codex as codex_adapter

        out = codex_adapter.write_decision(
            contract.Decision(
                allow=False,
                reason=(
                    "cross-model review has not run for the L3+ paths "
                    "touched this session; run the claude -p review "
                    "before stopping"
                ),
                extra={"hookEventName": "Stop"},
            )
        )
        self.assertEqual(out, self._golden("stop_block.json"))
        parsed = json.loads(out)
        self.assertEqual(parsed["decision"], "block")

    def test_legacy_shape_preserved_without_host_context(self):
        """No hookEventName stamp + no event → the PLAN-081 legacy shape
        (byte-compat for reviewer-context tooling and older tests)."""
        from _lib.adapters import codex as codex_adapter

        out = codex_adapter.write_decision(contract.allow())
        self.assertEqual(json.loads(out), {"decision": "allow"})

    def test_host_event_kwarg_selects_host_shape(self):
        """Passing the parsed host-wire event (no extra stamp) also selects
        the host shape — the emit path hooks actually use."""
        from _lib.adapters import codex as codex_adapter

        fixture = (
            _ADAPTERS_DIR / "codex" / "in" / "pre_tool_use.bash.echo.json"
        ).read_text(encoding="utf-8")
        ev = codex_adapter.read_event(io.StringIO(fixture))
        out = codex_adapter.write_decision(
            contract.block(reason="destructive command class"), event=ev
        )
        parsed = json.loads(out)
        self.assertEqual(
            parsed["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        self.assertEqual(
            parsed["hookSpecificOutput"]["hookEventName"], "PreToolUse"
        )


class CodexCoherenceGateTest(TestEnvContext):
    """PLAN-155 debate A2 / PLAN-152 C4 — fail-CLOSED on cross-harness or
    unparseable INPUT; fail-OPEN preserved for INFRASTRUCTURE."""

    def _host_wrap(self, **kw) -> str:
        base = {
            "session_id": "s-a2",
            "cwd": "/tmp/codex-lab/repo",
            "hook_event_name": "PreToolUse",
            "model": "gpt-5.5",
            "permission_mode": "bypassPermissions",
        }
        base.update(kw)
        return json.dumps(base)

    def test_cross_harness_claude_edit_wire_denies(self):
        """A Claude-native Edit envelope under the codex host adapter is
        recognizably cross-harness → deny at egress regardless of the
        hook's Decision."""
        from _lib.adapters import codex as codex_adapter

        raw = self._host_wrap(
            tool_name="Edit",
            tool_input={
                "file_path": "/x/y.py",
                "old_string": "a",
                "new_string": "b",
            },
        )
        ev = codex_adapter.read_event(io.StringIO(raw))
        self.assertIsNone(ev.parse_error)
        self.assertIsNotNone(codex_adapter.coherence_error(ev))
        out = json.loads(
            codex_adapter.write_decision(contract.allow(), event=ev)
        )
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        # Dual-vocabulary deny: top-level block present too.
        self.assertEqual(out["decision"], "block")

    def test_unparseable_apply_patch_denies(self):
        """apply_patch with no parseable file headers is C4 INPUT →
        fail-CLOSED."""
        from _lib.adapters import codex as codex_adapter

        raw = self._host_wrap(
            tool_name="apply_patch",
            tool_input={"command": "*** Begin Patch\ngarbage\n*** End Patch\n"},
        )
        ev = codex_adapter.read_event(io.StringIO(raw))
        self.assertIsNotNone(codex_adapter.coherence_error(ev))
        out = json.loads(
            codex_adapter.write_decision(contract.allow(), event=ev)
        )
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecision"], "deny"
        )

    def test_benign_bash_envelope_is_not_cross_harness(self):
        """The wires are deliberately compatible — a plain Bash envelope is
        valid under both harnesses and must NOT trip the gate."""
        from _lib.adapters import codex as codex_adapter

        raw = self._host_wrap(
            tool_name="Bash", tool_input={"command": "echo ok"}
        )
        ev = codex_adapter.read_event(io.StringIO(raw))
        self.assertIsNone(codex_adapter.coherence_error(ev))
        out = json.loads(
            codex_adapter.write_decision(contract.allow(), event=ev)
        )
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecision"], "allow"
        )

    def test_malformed_stdin_stays_fail_open_infrastructure(self):
        """C4 split: malformed JSON is INFRASTRUCTURE → parse_error set,
        no coherence deny (the hook's fail-open breadcrumb path owns it)."""
        from _lib.adapters import codex as codex_adapter

        ev = codex_adapter.read_event(io.StringIO("{truncated"))
        self.assertIsNotNone(ev.parse_error)
        self.assertIsNone(codex_adapter.coherence_error(ev))

    def test_multi_file_patch_surfaces_all_paths(self):
        """One apply_patch may touch MANY files — the guard must see the
        full list (deny if ANY path is guarded)."""
        from _lib.adapters import codex as codex_adapter

        patch = (
            "*** Begin Patch\n"
            "*** Update File: a.py\n@@\n-x\n+y\n"
            "*** Add File: b/c.txt\n+hello\n"
            "*** Delete File: d.md\n"
            "*** End Patch\n"
        )
        raw = self._host_wrap(
            tool_name="apply_patch", tool_input={"command": patch}
        )
        ev = codex_adapter.read_event(io.StringIO(raw))
        self.assertIsNone(codex_adapter.coherence_error(ev))
        self.assertEqual(ev.tool_name, "Edit")  # mixed ops → Edit semantics
        self.assertEqual(
            ev.tool_input["apply_patch_paths"], ["a.py", "b/c.txt", "d.md"]
        )
        self.assertEqual(ev.file_path, "a.py")


class CodexFixturePinCouplingTest(TestEnvContext):
    """PLAN-155 debate A12: fixtures follow the PIN, never upstream.

    Every recorded codex `in/` fixture carries `_meta.codex_cli_version`;
    that version must sit INSIDE the range pinned in
    `.claude/governance/codex-cli-pin.txt`. Bumping the pin without
    re-recording fixtures goes RED here — re-record on the new pin (via
    the ADR-111 ceremony) or explicitly waive.
    """

    _VER_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")

    @staticmethod
    def _parse_pin_spec(text: str) -> List[Tuple[str, Tuple[int, int, int]]]:
        """Parse the pin file's `>=X.Y.Z,<A.B.C` line into (op, version)."""
        spec_line = ""
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                spec_line = line
                break
        clauses: List[Tuple[str, Tuple[int, int, int]]] = []
        for part in spec_line.split(","):
            part = part.strip()
            m = re.match(r"(>=|<=|==|<|>)\s*(\d+)\.(\d+)\.(\d+)", part)
            if m:
                clauses.append(
                    (m.group(1), (int(m.group(2)), int(m.group(3)), int(m.group(4))))
                )
        return clauses

    @classmethod
    def _version_in_range(
        cls,
        version: Tuple[int, int, int],
        clauses: List[Tuple[str, Tuple[int, int, int]]],
    ) -> bool:
        ops = {
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: a == b,
            "<": lambda a, b: a < b,
            ">": lambda a, b: a > b,
        }
        return all(ops[op](version, bound) for op, bound in clauses)

    def test_pin_file_exists_and_parses(self):
        self.assertTrue(
            _CODEX_PIN_FILE.is_file(),
            f"missing {_CODEX_PIN_FILE} — the codex-cli pin is the A12 anchor",
        )
        clauses = self._parse_pin_spec(
            _CODEX_PIN_FILE.read_text(encoding="utf-8")
        )
        self.assertTrue(clauses, "pin file has no parseable semver clauses")

    def test_every_codex_in_fixture_carries_meta_within_pin_range(self):
        clauses = self._parse_pin_spec(
            _CODEX_PIN_FILE.read_text(encoding="utf-8")
        )
        in_files = sorted((_ADAPTERS_DIR / "codex" / "in").glob("*.json"))
        self.assertTrue(in_files, "no codex in-fixtures (vacuous)")
        for f in in_files:
            with self.subTest(fixture=f.name):
                meta = _load_json(f).get("_meta")
                self.assertIsInstance(
                    meta, dict,
                    f"{f.name}: recorded fixtures must carry _meta "
                    "(provenance, debate A12/A26)",
                )
                ver_str = str(meta.get("codex_cli_version") or "")
                m = self._VER_RE.search(ver_str)
                self.assertIsNotNone(
                    m, f"{f.name}: _meta.codex_cli_version unparseable: {ver_str!r}"
                )
                ver = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
                self.assertTrue(
                    self._version_in_range(ver, clauses),
                    f"{f.name}: recorded on codex-cli {ver_str!r} which is "
                    f"OUTSIDE the pin range in {_CODEX_PIN_FILE.name} — "
                    "re-record the fixtures on the pinned version (bump the "
                    "pin FIRST via the ADR-111 ceremony), or waive explicitly",
                )


class ResolveSeamTest(TestEnvContext):
    """PLAN-155 Wave 1 dispatch seam (`_lib.adapters.resolve()`) — debate
    A1 option (b) + debate A2 fail-CLOSED contract."""

    def test_default_resolves_claude_module(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_HOOK_ADAPTER", None)
            mod = adapters_pkg.resolve()
        from _lib.adapters import claude as claude_adapter

        self.assertIs(mod, claude_adapter)

    def test_explicit_codex_resolves_codex_module(self):
        with mock.patch.dict(os.environ, {"CEO_HOOK_ADAPTER": "codex"}):
            mod = adapters_pkg.resolve()
        from _lib.adapters import codex as codex_adapter

        self.assertIs(mod, codex_adapter)

    def test_env_mapping_argument_wins_over_environ(self):
        mod = adapters_pkg.resolve(env={"CEO_HOOK_ADAPTER": "claude"})
        from _lib.adapters import claude as claude_adapter

        self.assertIs(mod, claude_adapter)

    def test_unknown_adapter_fails_closed_not_fallback(self):
        """Explicitly-set-but-unresolvable → deny-emitting shim, NEVER a
        silent fallback to claude (debate A2, PLAN-152 C4 INPUT class)."""
        shim = adapters_pkg.resolve(env={"CEO_HOOK_ADAPTER": "not-a-real-adapter"})
        self.assertTrue(getattr(shim, "FAIL_CLOSED", False))
        # ABI surface present
        for attr in ("read_event", "read_post_event", "write_decision", "emit_decision"):
            self.assertTrue(hasattr(shim, attr))
        ev = shim.read_event(io.StringIO('{"tool_name": "Bash"}'))
        self.assertIn("ceo_coherence_error", ev.raw_payload)
        out = json.loads(shim.write_decision(contract.allow(), event=ev))
        # Dual-vocabulary deny: readable by BOTH harnesses.
        self.assertEqual(out["decision"], "block")
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        self.assertIn("CEO_HOOK_ADAPTER", out["reason"])

    def test_fail_closed_emit_decision_writes_deny_line(self):
        shim = adapters_pkg.resolve(env={"CEO_HOOK_ADAPTER": "bogus"})
        buf = io.StringIO()
        shim.emit_decision(contract.allow(), stream=buf)
        line = buf.getvalue()
        self.assertTrue(line.endswith("\n"))
        parsed = json.loads(line)
        self.assertEqual(parsed["decision"], "block")

    def test_empty_env_var_is_default_not_fail_closed(self):
        """Unset/empty is the DEFAULT path (claude), not a misconfig."""
        mod = adapters_pkg.resolve(env={"CEO_HOOK_ADAPTER": "  "})
        from _lib.adapters import claude as claude_adapter

        self.assertIs(mod, claude_adapter)

    def test_registry_matches_known_adapters(self):
        """The seam dispatches over ADAPTER_REGISTRY; contract carries the
        mirror. Divergence = an adapter reachable by one surface only."""
        self.assertEqual(adapters_pkg.ADAPTER_REGISTRY, contract.KNOWN_ADAPTERS)


if __name__ == "__main__":
    unittest.main()

