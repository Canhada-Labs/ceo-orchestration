"""Tests for the PLAN-165 W2 T2.1 night-mode posture advisory in ceo-boot.

Covers the ``008-night-mode`` recommendation rule in
``.claude/scripts/ceo-boot.py`` (design decision D3 of PLAN-165):

- the advisory derives from ``_lib/effective_config.resolve_settings()``
  — it renders iff an OVERLAY layer (local/user) wins the resolver's
  ``permissions`` key with a ``defaultMode`` differing from the
  PROJECT-layer-ratified value (NM-06: "ratified" is the tracked project
  settings' own value, fallback ``manual``; a winning project layer
  never renders), never from the marker file;
- the marker at ``.claude/state/night-mode.json`` is decoration ONLY:
  present-and-parsing enriches the text; absent or corrupt never breaks
  boot and never changes whether the line renders;
- advisory contract: a recommendation entry in BOTH hand-mirrored
  pipelines (``_make_recommendations`` + ``_recommendations_with_severity``,
  same text by shared helper), never a check row, never red, never
  gate-blocking;
- fail-OPEN: resolver exception / missing module ⇒ the rule silently
  skips (stderr breadcrumb only under ``CEO_BOOT_DEBUG=1``);
- the ``recs[:5]`` cap is respected — the rule emits one high-priority
  entry and never restructures the cap;
- NF-07 (round-4, 2026-08-03): ``_sanitize_for_recs`` collapses every
  line-boundary character (and TAB) to a single space, so a rec built
  from disk-sourced text — including a planted night-mode marker ``ts``
  — renders as exactly ONE digest line and can never forge a second one
  (``TestSanitizerNewlineCollapse``). The collapse lives in the SHARED
  sanitizer, hardening every rec consumer, not just night-mode.

Hermeticity (the PLAN-165 T1.3 class): the rule anchors its project root
in ``_night_mode_project_root()`` at CALL time, preferring
``CLAUDE_PROJECT_DIR`` — which ``TestEnvContext`` points at a sandbox —
so these tests (and every unrelated suite that exercises the
recommendations pipelines) never see the developer machine's real
night-mode state.

Env hygiene (PLAN-019 P1-QA-3): every test class subclasses
TestEnvContext; env mutation only via unittest.mock. Stdlib-only,
Python >= 3.9. Runs under pytest AND plain unittest.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"

# Seed sys.path so _lib + the hook-side modules resolve (conftest also does
# this, but keep the module self-sufficient if run in isolation).
for _p in (
    str(REPO_ROOT / ".claude" / "hooks"),
    str(REPO_ROOT / ".claude" / "scripts"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    """Load ceo-boot.py under a unique module name (hyphen in filename)."""
    spec = importlib.util.spec_from_file_location("ceo_boot_night_mode", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE exec so dataclass/annotation lookups resolve on Py3.9.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()

SORT_KEY = "008-night-mode"
RATIFIED = "manual"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


class _NightModeBase(TestEnvContext):
    """Shared harness over the TestEnvContext sandbox project.

    ``TestEnvContext.setUp`` points ``CLAUDE_PROJECT_DIR`` at
    ``self.project_dir``; ``_night_mode_project_root()`` therefore
    resolves the sandbox at call time — no module patching needed for the
    root. The managed layer is patched to [] so a real
    managed-settings.json on the runner can never leak in.
    """

    def setUp(self) -> None:
        super().setUp()
        ec = _mod._effective_config
        self.assertIsNotNone(
            ec, "effective_config must be importable for these tests"
        )
        patcher = mock.patch.object(ec, "_managed_settings_paths", lambda: [])
        patcher.start()
        self.addCleanup(patcher.stop)

    # -- sandbox project builders --------------------------------------

    def arm(self, mode: str = "acceptEdits") -> None:
        """Project ratifies manual; local overlay flips the posture."""
        self.ratify()
        _write_json(
            self.project_dir / ".claude" / "settings.local.json",
            {"permissions": {"defaultMode": mode}},
        )

    def ratify(self, mode: str = RATIFIED) -> None:
        _write_json(
            self.project_dir / ".claude" / "settings.json",
            {"permissions": {"defaultMode": mode}},
        )

    def write_marker(self, doc: Any) -> Path:
        path = self.project_dir / ".claude" / "state" / "night-mode.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(doc, str):
            path.write_text(doc, encoding="utf-8")
        else:
            _write_json(path, doc)
        return path

    # -- pipeline helpers ------------------------------------------------

    def all_green_results(self) -> List[Any]:
        return [
            _mod.CheckResult(name, "green", "ok", 1.0, None)
            for name, _fn in _mod.TIER_S_CHECKS
        ]

    def night_recs(self, results: Optional[List[Any]] = None) -> List[str]:
        recs = _mod._make_recommendations(
            results if results is not None else self.all_green_results()
        )
        return [r for r in recs if "/night-mode" in r]


# ---------------------------------------------------------------------------
# Renders iff the resolver shows a non-manual posture
# ---------------------------------------------------------------------------


class TestRendersIffResolverNonManual(_NightModeBase):

    def test_armed_local_accept_edits_renders(self):
        self.arm()
        matches = self.night_recs()
        self.assertEqual(len(matches), 1, matches)
        self.assertIn("acceptEdits", matches[0])
        self.assertIn(f"not the ratified '{RATIFIED}'", matches[0])

    def test_armed_line_names_the_layer(self):
        self.arm()
        self.assertIn("(layer: local)", self.night_recs()[0])

    def test_ratified_manual_does_not_render(self):
        self.ratify()
        self.assertEqual(self.night_recs(), [])

    def test_no_settings_at_all_does_not_render(self):
        # Sandbox project has an empty .claude/ — no permissions key.
        self.assertEqual(self.night_recs(), [])

    def test_non_string_default_mode_does_not_render(self):
        self.ratify()
        _write_json(
            self.project_dir / ".claude" / "settings.local.json",
            {"permissions": {"defaultMode": {"weird": True}}},
        )
        self.assertEqual(self.night_recs(), [])

    def test_any_non_manual_string_renders(self):
        self.arm(mode="plan")
        matches = self.night_recs()
        self.assertEqual(len(matches), 1)
        self.assertIn("plan", matches[0])

    def test_marker_alone_never_renders(self):
        # D3: the marker is NOT a trigger. Resolver says manual ⇒ silent,
        # even with a healthy marker on disk.
        self.ratify()
        self.write_marker({"version": 1, "ts": "2026-08-02T23:00:00Z"})
        self.assertEqual(self.night_recs(), [])

    def test_rendered_in_digest_recommendations_section(self):
        self.arm()
        digest = _mod.render_digest(self.all_green_results())
        self.assertIn("### Recommendations", digest)
        self.assertIn("/night-mode", digest)

    def test_env_unset_falls_back_to_repo_root(self):
        # _night_mode_project_root(): CLAUDE_PROJECT_DIR wins, REPO_ROOT
        # is the fallback (same pattern as main()).
        self.arm()
        with mock.patch.dict(
            "os.environ", {}, clear=False
        ), mock.patch.object(_mod, "REPO_ROOT", self.project_dir):
            import os as _os
            _os.environ.pop("CLAUDE_PROJECT_DIR", None)
            self.assertEqual(
                _mod._night_mode_project_root(), self.project_dir
            )
            self.assertEqual(len(self.night_recs()), 1)


# ---------------------------------------------------------------------------
# NM-06 — "ratified" comes from the PROJECT layer, not a hardcoded literal
# ---------------------------------------------------------------------------


class TestProjectLayerRatification(_NightModeBase):
    """Round-2 security finding NM-06.

    A repo whose TRACKED ``.claude/settings.json`` ratifies a non-manual
    posture must never see the advisory claim its own ratified value is
    "not the ratified 'manual'". The advisory renders only when an
    overlay layer (local/user) wins ``permissions`` AND differs from the
    project layer's own ``defaultMode``.
    """

    def test_project_ratifies_accept_edits_no_overlay_does_not_render(self):
        # The NM-06 reproduction: tracked settings ratify acceptEdits,
        # no local overlay ⇒ project layer wins ⇒ NO advisory line.
        self.ratify(mode="acceptEdits")
        self.assertEqual(self.night_recs(), [])

    def test_project_ratifies_plan_no_overlay_does_not_render(self):
        self.ratify(mode="plan")
        self.assertEqual(self.night_recs(), [])

    def test_project_winner_with_marker_still_does_not_render(self):
        # Marker is decoration, never a trigger — even when the project
        # layer ratifies a non-manual posture.
        self.ratify(mode="acceptEdits")
        self.write_marker({"version": 1, "ts": "2026-08-02T23:00:00Z"})
        self.assertEqual(self.night_recs(), [])

    def test_local_overlay_matching_ratified_value_does_not_render(self):
        # Overlay wins but AGREES with the ratified value ⇒ silent.
        self.ratify(mode="acceptEdits")
        _write_json(
            self.project_dir / ".claude" / "settings.local.json",
            {"permissions": {"defaultMode": "acceptEdits"}},
        )
        self.assertEqual(self.night_recs(), [])

    def test_local_overlay_diverging_names_the_derived_ratified_value(self):
        # Project ratifies plan; local arms acceptEdits ⇒ renders and the
        # "ratified" clause names 'plan' (derived), never 'manual'.
        self.ratify(mode="plan")
        _write_json(
            self.project_dir / ".claude" / "settings.local.json",
            {"permissions": {"defaultMode": "acceptEdits"}},
        )
        matches = self.night_recs()
        self.assertEqual(len(matches), 1, matches)
        self.assertIn("'acceptEdits'", matches[0])
        self.assertIn("not the ratified 'plan'", matches[0])
        self.assertNotIn("'manual'", matches[0])

    def test_project_without_default_mode_falls_back_to_manual(self):
        # Project layer exists but declares no defaultMode ⇒ ratified
        # falls back to the harness default 'manual'; an armed local
        # overlay still renders (the primary night-mode scenario).
        _write_json(
            self.project_dir / ".claude" / "settings.json",
            {"permissions": {"allow": ["Bash(ls:*)"]}},
        )
        _write_json(
            self.project_dir / ".claude" / "settings.local.json",
            {"permissions": {"defaultMode": "acceptEdits"}},
        )
        matches = self.night_recs()
        self.assertEqual(len(matches), 1, matches)
        self.assertIn(f"not the ratified '{RATIFIED}'", matches[0])


# ---------------------------------------------------------------------------
# Both hand-mirrored pipelines carry the rule (no drift)
# ---------------------------------------------------------------------------


class TestMirroredPipelines(_NightModeBase):

    def test_severity_pipeline_carries_same_text_high(self):
        self.arm()
        results = self.all_green_results()
        flat = _mod._make_recommendations(results)
        triples = _mod._recommendations_with_severity(results)
        self.assertEqual([t[1] for t in triples], flat)  # mirror parity
        match = [t for t in triples if t[0] == SORT_KEY]
        self.assertEqual(len(match), 1, triples)
        self.assertEqual(match[0][2], "high")

    def test_sorts_before_owner_sentinels(self):
        self.arm()
        results = self.all_green_results()
        for r in results:
            if r.name == "sentinels_pending_gpg":
                r.status = "yellow"
                r.summary = "1 pending"
                r.detail = ["PLAN-165/architect/round-1/approved.md"]
        recs = _mod._make_recommendations(results)
        night_idx = next(i for i, r in enumerate(recs) if "/night-mode" in r)
        sentinel_idx = next(
            i for i, r in enumerate(recs) if "GPG sign pending" in r
        )
        self.assertLess(night_idx, sentinel_idx)

    def test_recs_cap_of_5_is_respected_not_restructured(self):
        # Six higher-priority rules (3× 00-*, 005, 006, 007) crowd the cap:
        # the night-mode entry must simply fall off — never a 6th slot.
        self.arm()
        results = self.all_green_results()
        by_name = {r.name: r for r in results}
        special = {
            "settings_tamper_tripwires",
            "failopen_rail_liveness_7d",
            "harness_config_gate",
        }
        for name in [n for n in by_name if n not in special][:3]:
            by_name[name].status = "timeout"
            by_name[name].summary = "budget exceeded"
        tamper = by_name["settings_tamper_tripwires"]
        tamper.status = "red"
        tamper.detail = [
            {"class": "settings_tamper_disable_all_hooks", "layer": "local",
             "detail": "x"},
        ]
        by_name["failopen_rail_liveness_7d"].status = "red"
        by_name["harness_config_gate"].status = "red"
        recs = _mod._make_recommendations(results)
        self.assertEqual(len(recs), 5)
        self.assertFalse(any("/night-mode" in r for r in recs), recs)
        triples = _mod._recommendations_with_severity(results)
        self.assertEqual(len(triples), 5)
        self.assertNotIn(SORT_KEY, [t[0] for t in triples])

    def test_advisory_never_adds_a_check_row(self):
        # The rule is a recommendation, not a CheckResult: registry size
        # and statuses are untouched by arming night-mode.
        self.arm()
        names = [name for name, _fn in _mod.TIER_S_CHECKS]
        self.assertNotIn("night_mode", " ".join(names))
        results = self.all_green_results()
        _mod._make_recommendations(results)
        self.assertTrue(all(r.status == "green" for r in results))


# ---------------------------------------------------------------------------
# Marker is decoration only — absent/corrupt never breaks boot
# ---------------------------------------------------------------------------


class TestMarkerDecoration(_NightModeBase):

    def test_parsing_marker_decorates_with_armed_ts(self):
        self.arm()
        self.write_marker({
            "version": 1, "mode_written": "acceptEdits",
            "ts": "2026-08-02T23:00:00Z",
        })
        line = self.night_recs()[0]
        self.assertIn("night-mode marker present", line)
        self.assertIn("armed 2026-08-02T23", line)

    def test_marker_without_ts_still_decorates(self):
        self.arm()
        self.write_marker({"version": 1, "mode_written": "acceptEdits"})
        line = self.night_recs()[0]
        self.assertIn("night-mode marker present", line)
        self.assertNotIn("armed", line)

    def test_absent_marker_renders_without_note(self):
        self.arm()
        line = self.night_recs()[0]
        self.assertNotIn("marker", line)

    def test_corrupt_marker_renders_without_note_never_raises(self):
        self.arm()
        self.write_marker("{ not valid json !!")
        matches = self.night_recs()  # reaching here = no exception
        self.assertEqual(len(matches), 1)
        self.assertNotIn("marker", matches[0])

    def test_non_dict_marker_renders_without_note(self):
        self.arm()
        self.write_marker([1, 2, 3])
        line = self.night_recs()[0]
        self.assertNotIn("marker", line)

    def test_corrupt_marker_never_breaks_digest_render(self):
        self.arm()
        self.write_marker("\x00\x00 garbage")
        digest = _mod.render_digest(self.all_green_results())
        self.assertIn("/ceo-boot digest", digest)
        self.assertIn("/night-mode", digest)


# ---------------------------------------------------------------------------
# Fail-open — resolver failure never blocks boot
# ---------------------------------------------------------------------------


class TestFailOpen(_NightModeBase):

    def _broken_resolver(self) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            resolve_settings=mock.Mock(side_effect=RuntimeError("boom")),
        )

    def test_resolver_exception_skips_silently(self):
        self.arm()
        buf = io.StringIO()
        with mock.patch.object(
            _mod, "_effective_config", self._broken_resolver()
        ), mock.patch.object(sys, "stderr", buf):
            with mock.patch.dict("os.environ", {}, clear=False):
                import os as _os
                _os.environ.pop("CEO_BOOT_DEBUG", None)
                self.assertIsNone(_mod._night_mode_advisory_rec())
                recs = _mod._make_recommendations(self.all_green_results())
        self.assertEqual(recs, [])
        self.assertEqual(buf.getvalue(), "")  # breadcrumb only under DEBUG

    def test_resolver_exception_breadcrumbs_under_debug(self):
        self.arm()
        buf = io.StringIO()
        with mock.patch.object(
            _mod, "_effective_config", self._broken_resolver()
        ), mock.patch.object(sys, "stderr", buf), mock.patch.dict(
            "os.environ", {"CEO_BOOT_DEBUG": "1"}
        ):
            self.assertIsNone(_mod._night_mode_advisory_rec())
        self.assertIn("night-mode advisory skipped", buf.getvalue())
        self.assertIn("RuntimeError", buf.getvalue())

    def test_effective_config_none_skips(self):
        self.arm()
        with mock.patch.object(_mod, "_effective_config", None):
            self.assertIsNone(_mod._night_mode_advisory_rec())
            self.assertEqual(
                _mod._make_recommendations(self.all_green_results()), []
            )

    def test_degraded_resolver_payload_skips(self):
        # resolve_settings' own fail-open shape (effective={}) ⇒ no rec.
        degraded = types.SimpleNamespace(
            resolve_settings=mock.Mock(return_value={
                "effective": {}, "sources": {}, "ok": False,
                "errors": ["resolver_internal_error: X"],
            }),
        )
        with mock.patch.object(_mod, "_effective_config", degraded):
            self.assertIsNone(_mod._night_mode_advisory_rec())

    def test_resolver_exception_never_breaks_digest_render(self):
        self.arm()
        with mock.patch.object(
            _mod, "_effective_config", self._broken_resolver()
        ):
            digest = _mod.render_digest(self.all_green_results())
        self.assertIn("/ceo-boot digest", digest)
        self.assertNotIn("/night-mode", digest)


# ---------------------------------------------------------------------------
# NF-07 — a rec can never span two digest lines (shared-sanitizer collapse)
# ---------------------------------------------------------------------------


class TestSanitizerNewlineCollapse(_NightModeBase):
    """PLAN-165 round-4 NF-07 (2026-08-03).

    ``_sanitize_for_recs`` NUL-stripped, NFKC-normalized, bounded,
    scanned and bracket-stripped — but never collapsed line breaks, and
    recommendations render one per line (``f"{i}. {rec}"``). Verified
    end to end pre-fix: a planted night-mode marker ``ts`` produced a
    TWO-line rec whose second line read like a forged all-clear directly
    under the true line saying the opposite — in the one surface the
    Owner reads at boot. The collapse lives INSIDE the shared sanitizer,
    so every rec consumer (check summaries, audit classes, stale-plan
    names) is hardened at once, not just night-mode.
    """

    # Every character str.splitlines() treats as a boundary, plus TAB.
    # Escapes on purpose — a literal U+2028 in the source is invisible.
    _BOUNDARIES = (
        "\n", "\r", "\t", "\v", "\f",
        "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029",
    )

    def test_sanitize_collapses_newline_directly(self):
        # The exact pre-fix reproduction: the newline came back intact.
        self.assertEqual(_mod._sanitize_for_recs("x\nFORGED"), "x FORGED")

    def test_sanitize_collapses_every_line_boundary_character(self):
        for ch in self._BOUNDARIES:
            out = _mod._sanitize_for_recs("x" + ch + "y")
            self.assertNotIn(
                ch, out,
                "boundary %r survived _sanitize_for_recs (NF-07)" % ch,
            )
            self.assertEqual(len(out.splitlines()), 1)

    def test_sanitized_output_is_always_single_line(self):
        out = _mod._sanitize_for_recs("a\r\nb\u2028c\td")
        self.assertEqual(out.splitlines(), [out])

    def test_marker_ts_with_newline_renders_exactly_one_digest_line(self):
        # End to end: the planted marker field that produced the forged
        # second digest line pre-fix.
        self.arm()
        self.write_marker({
            "version": 1, "mode_written": "acceptEdits",
            "ts": "2026-08-02T23:00:00Z\nFORGED-ALL-CLEAR night-mode is off",
        })
        matches = self.night_recs()
        self.assertEqual(len(matches), 1, matches)
        self.assertNotIn(
            "\n", matches[0],
            "the rec must be ONE line; a newline here becomes a forged "
            "digest line (NF-07): %r" % matches[0],
        )

        digest = _mod.render_digest(self.all_green_results())
        forged_lines = [
            line for line in digest.splitlines()
            if line.strip().startswith("FORGED-ALL-CLEAR")
        ]
        self.assertEqual(
            forged_lines, [],
            "a planted marker ts forged its own digest line (NF-07)",
        )
        rec_lines = [
            line for line in digest.splitlines() if "/night-mode" in line
        ]
        self.assertEqual(len(rec_lines), 1, digest)

    def test_marker_note_tolerates_malformed_marker_shapes(self):
        # _night_mode_marker_note must degrade to decoration-off, never
        # trust (or crash on) a malformed document.
        self.arm()
        for doc in (
            "{ not json",            # unparseable
            [1, 2, 3],               # non-dict
            {"version": 1, "ts": 42},          # non-string ts
            {"version": 1, "ts": ""},          # empty ts
        ):
            self.write_marker(doc)
            note = _mod._night_mode_marker_note()
            self.assertNotIn("armed", note)
            self.assertEqual(len(note.splitlines()), 1 if note else 0)


# ---------------------------------------------------------------------------
# Hermeticity — the sandbox default is silent (unrelated-suite guarantee)
# ---------------------------------------------------------------------------


class TestHermeticDefault(_NightModeBase):

    def test_all_green_sandbox_yields_zero_recs(self):
        # The invariant every unrelated recs-pipeline test relies on:
        # a pristine TestEnvContext sandbox emits NO night-mode line,
        # whatever the developer machine's real posture is.
        self.assertEqual(
            _mod._make_recommendations(self.all_green_results()), []
        )

    def test_root_prefers_claude_project_dir(self):
        self.assertEqual(
            _mod._night_mode_project_root(), Path(self.project_dir)
        )


if __name__ == "__main__":
    unittest.main()
