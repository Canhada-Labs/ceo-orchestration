"""PLAN-153 Wave B item 5 — release-workflow VERSION-consistency + idempotency asserts.

Extends the existing VERSION-consistency test family
(test_npm_rebuild.py::NpmRebuildTest.test_version_files_in_sync —
VERSION == npm/VERSION == npm/package.json.version) and the grey-box
workflow-invariant convention (test_workflow_devops_p2.py) with:

- version↔plugin-manifest sync: VERSION == .claude-plugin/plugin.json
  version == every `version` field in .claude-plugin/marketplace.json
  (skip-if-absent until PLAN-153 Wave B item 6 generates the manifests
  via build-plugin.py — same skipTest pattern test_npm_rebuild.py uses
  for the release-only npm bundle);
- RC posture pins on npm-publish.yml: RC tags stay hard-excluded from
  npm publishing (PLAN-013 anti-goals #3/#16, re-ratified by the
  PLAN-153 debate: the `next` dist-tag idea was DROPPED);
- release-notes template invariants (.github/release-notes-template.md,
  closes PLAN-152 §Deferred release-notes-hardcoded-first-release);
- dual-context asserts on the Wave B workflow edits themselves
  (npm-publish.yml `already_published` guard; release.yml
  `gh release view || gh release create` idempotency; `-rc.N` strip in
  the VERSION + CHANGELOG gates, closing PLAN-152 §Deferred
  release-gate-rc-version-mismatch / red run 28663453202): enforced
  against the STAGED copy while it exists on disk
  (.claude/plans/PLAN-153/staged/wave-B/ is gitignored → absent in CI)
  and against the LIVE workflow once Wave B lands (detected via the
  "PLAN-153 Wave B item 5" marker). They skip only in the pre-landing
  CI window where neither context is available.

PLAN-166 W1 items 1 + 4 (F1, P0) extend the same dual-context convention
(staged mirror under .claude/plans/PLAN-166/staged/ pre-landing,
"PLAN-166 W1 item 1" marker in the live file post-landing) with:

- await-gate asserts: the publish OBSERVES release.yml's `release-gate`
  job — `await-release-gate` job present, `needs:` on the publish job,
  `GH_TOKEN: ${{ github.token }}` in the await job's env (permissions:
  alone does NOT authenticate the gh CLI on a hosted runner; without the
  token every poll dies on auth = fail-closed BLOCK breaking every
  release), permissions/timeout pinned, and NO environment / NO RC
  exclusion on the await job (RC tags are the live positive control).
  Posture pins are STRENGTHENED, not relocated: NpmPublishRcPostureTest
  keeps asserting the RC exclusion + environment on the live file.
- trusted-publisher binding asserts: the npmjs OIDC registration triple
  (repository / workflow FILENAME / environment) is cross-checked by
  READING .claude/governance/npm-trusted-publisher.txt — embedding the
  values in the test would create a 4th copy of the truth. Includes
  positive controls: mutating `environment:` (or the repository slug) in
  a COPY of the workflow text must go red.

PLAN-166 W1-B (F2 server side; merged in by the ceremony assembler —
one runnable asserts file) adds the W1B* classes at the bottom:
structural asserts for release.yml's verdict delta + ancestry gate step
(no continue-on-error, fail-closed on the transition var, delegation to
_release_tag_guard.py, parent+GITHUB_SHA ancestry, pinned step order,
`release-gate` job-name pin) plus the guard-module contract pins.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from typing import Iterator, Optional, Tuple

def _find_repo() -> Path:
    """Repo root — robust to BOTH homes this file can run from.

    At its landed path (.claude/scripts/tests/) four parents reach the
    root; at its staged path (.claude/plans/PLAN-166/staged/...) they
    reach the staged mirror instead. Walk up to the first ancestor that
    actually looks like the repo (has the live workflow AND the hooks
    tree) so pre-land verification runs from the staged location give
    the same answers as post-land runs. (Merged in from the W1-B slice
    by the PLAN-166 ceremony assembler.)
    """
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (
            (candidate / ".github" / "workflows" / "release.yml").is_file()
            and (candidate / ".claude" / "hooks" / "_lib").is_dir()
        ):
            return candidate
    # Fall back to the landed-layout arithmetic; setUp guards will skip
    # or fail loudly if this is wrong.
    return here.parent.parent.parent.parent


_REPO = _find_repo()
_WF = _REPO / ".github" / "workflows"
_STAGED_WF = (
    _REPO / ".claude" / "plans" / "PLAN-153" / "staged" / "wave-B"
    / ".github" / "workflows"
)
_TEMPLATE = _REPO / ".github" / "release-notes-template.md"
_PLUGIN_DIR = _REPO / ".claude-plugin"

# Bootstrap TestEnvContext so env isolation holds (env-hygiene gate).
_HOOKS_DIR = _REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

# Marker written into both Wave B workflow edits; its presence in the
# LIVE file means Wave B has landed and the live copy is authoritative.
_MARKER = "PLAN-153 Wave B item 5"

# The load-bearing RC exclusion (PLAN-013 anti-goals #3/#16).
_RC_EXCLUSION = "!contains(github.ref, '-rc.')"

# --- PLAN-166 W1 items 1 + 4 (F1, P0) --------------------------------
# Marker written into the PLAN-166 npm-publish.yml edit; its presence in
# the LIVE file means the W1 ceremony landed and the live copy is
# authoritative (same convention as _MARKER above).
_MARKER_166 = "PLAN-166 W1 item 1"

_STAGED_166 = _REPO / ".claude" / "plans" / "PLAN-166" / "staged"
_STAGED_166_WF = _STAGED_166 / ".github" / "workflows"

# Repo-side record of the npmjs trusted-publisher OIDC binding triple.
_TRUSTED_PUBLISHER = (
    _REPO / ".claude" / "governance" / "npm-trusted-publisher.txt"
)
_STAGED_166_TRUSTED_PUBLISHER = (
    _STAGED_166 / ".claude" / "governance" / "npm-trusted-publisher.txt"
)
_TRUSTED_PUBLISHER_KEYS = frozenset({"repository", "workflow", "environment"})


def _plan166_text(name: str) -> Optional[Tuple[str, str]]:
    """Return (text, context) for a PLAN-166 workflow edit, or None pre-landing.

    Priority: live copy carrying the PLAN-166 marker (post-landing,
    authoritative) → staged copy under .claude/plans/PLAN-166/staged/
    (pre-landing, local ceremony mirror; gitignored so absent in CI) →
    None (pre-landing CI: skip). Unlike _wave_b_text this tolerates a
    missing live file — the filename-binding test reports that as a
    FAILURE, not a collection error.
    """
    live = _WF / name
    if live.is_file():
        text = live.read_text(encoding="utf-8")
        if _MARKER_166 in text:
            return text, "live"
    staged = _STAGED_166_WF / name
    if staged.is_file():
        return staged.read_text(encoding="utf-8"), "staged"
    return None


def _trusted_publisher_values() -> Optional[Tuple[dict, str]]:
    """Parse npm-trusted-publisher.txt (live → staged), or None pre-landing.

    Format contract (documented in the file itself): `key=value` lines;
    `#`-prefixed and blank lines are comments; keys are EXACTLY
    repository/workflow/environment. Malformed content raises — a
    binding record we cannot parse must never silently skip the binding
    asserts (fail-closed, ADR-186 posture).
    """
    for path, context in (
        (_TRUSTED_PUBLISHER, "live"),
        (_STAGED_166_TRUSTED_PUBLISHER, "staged"),
    ):
        if not path.is_file():
            continue
        values = {}
        for lineno, raw in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not sep or not key or not value:
                raise AssertionError(
                    "%s:%d: expected key=value, got %r" % (path, lineno, raw)
                )
            if key in values:
                raise AssertionError(
                    "%s:%d: duplicate key %r" % (path, lineno, key)
                )
            values[key] = value
        if set(values) != set(_TRUSTED_PUBLISHER_KEYS):
            raise AssertionError(
                "%s must define exactly %s, got %s"
                % (path, sorted(_TRUSTED_PUBLISHER_KEYS), sorted(values))
            )
        return values, context
    return None


def _binding_mismatches(values: dict, workflow_text: str) -> list:
    """Which parts of the trusted-publisher triple the workflow does NOT honour.

    Pure text→list (no filesystem) so the positive-control tests can run
    it against a deliberately mutated COPY of the workflow text.
    """
    mismatches = []
    if ("environment: " + values["environment"]) not in workflow_text:
        mismatches.append(
            "workflow does not gate through `environment: %s` — the npmjs "
            "trusted-publisher registration names that environment"
            % values["environment"]
        )
    if values["repository"] not in workflow_text:
        mismatches.append(
            "workflow no longer names the registered repository %r (the "
            "OIDC registration comment is the in-file record)"
            % values["repository"]
        )
    return mismatches


def _wave_b_text(name: str) -> Optional[Tuple[str, str]]:
    """Return (text, context) for a Wave B workflow, or None pre-landing.

    Priority: live copy carrying the Wave B marker (post-landing,
    authoritative) → staged copy (pre-landing, local ceremony mirror;
    gitignored so absent in CI) → None (pre-landing CI: skip).
    """
    live = (_WF / name).read_text(encoding="utf-8")
    if _MARKER in live:
        return live, "live"
    staged = _STAGED_WF / name
    if staged.is_file():
        return staged.read_text(encoding="utf-8"), "staged"
    return None


def _iter_version_fields(obj: object) -> Iterator[str]:
    """Yield every string-valued `version` field nested anywhere in obj."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "version" and isinstance(value, str):
                yield value
            else:
                yield from _iter_version_fields(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_version_fields(item)


class PluginManifestVersionSyncTest(TestEnvContext):
    """VERSION ↔ .claude-plugin manifest sync (Wave B item 5 (e)).

    Sits NEXT TO the existing family member
    test_npm_rebuild.py::test_version_files_in_sync, extending the
    equality chain to the plugin manifests generated by build-plugin.py
    (Wave B item 6). Skips while the manifests do not exist yet; becomes
    enforcing the moment item 6 lands — no test edit needed.
    """

    def setUp(self):
        super().setUp()
        self.version = (_REPO / "VERSION").read_text(encoding="utf-8").strip()

    def test_plugin_json_version_matches_version_file(self):
        plugin_json = _PLUGIN_DIR / "plugin.json"
        if not plugin_json.is_file():
            self.skipTest(
                ".claude-plugin/plugin.json not present yet "
                "(generated by PLAN-153 Wave B item 6 build-plugin.py)"
            )
        data = json.loads(plugin_json.read_text(encoding="utf-8"))
        self.assertIn(
            "version", data,
            ".claude-plugin/plugin.json must carry a version field",
        )
        self.assertEqual(
            data["version"], self.version,
            f"plugin.json version ({data['version']}) != VERSION "
            f"({self.version}) — regenerate via build-plugin.py",
        )

    def test_marketplace_json_versions_match_version_file(self):
        marketplace_json = _PLUGIN_DIR / "marketplace.json"
        if not marketplace_json.is_file():
            self.skipTest(
                ".claude-plugin/marketplace.json not present yet "
                "(generated by PLAN-153 Wave B item 6 build-plugin.py)"
            )
        data = json.loads(marketplace_json.read_text(encoding="utf-8"))
        # Schema is owned by build-plugin.py, so assert on EVERY nested
        # `version` field rather than hardcoding one JSON path.
        mismatched = [
            v for v in _iter_version_fields(data) if v != self.version
        ]
        self.assertEqual(
            mismatched, [],
            f"marketplace.json carries version field(s) {mismatched} != "
            f"VERSION ({self.version}) — regenerate via build-plugin.py",
        )


class NpmPublishRcPostureTest(TestEnvContext):
    """RC tags stay hard-excluded from npm publishing — LIVE workflow.

    PLAN-013 anti-goals #3/#16; PLAN-153 Wave B item 5 (f) explicitly
    keeps this posture UNCHANGED. These asserts run against the live
    workflow in every context (pre- and post-landing).
    """

    def setUp(self):
        super().setUp()
        self.source = (_WF / "npm-publish.yml").read_text(encoding="utf-8")

    def test_rc_exclusion_present(self):
        self.assertIn(
            _RC_EXCLUSION, self.source,
            "npm-publish.yml lost the RC tag exclusion — RC tags must "
            "NEVER trigger an npm publish (PLAN-013 anti-goals #3/#16)",
        )

    def test_rc_exclusion_precedes_publish_command(self):
        # Ordering sanity: the job-level guard must appear before any
        # `npm publish` invocation in the file.
        self.assertLess(
            self.source.index(_RC_EXCLUSION),
            self.source.index("npm publish --provenance"),
            "RC exclusion must guard the job containing the publish step",
        )

    def test_manual_approval_environment_gate_present(self):
        self.assertIn(
            "environment: production-npm", self.source,
            "the Owner-in-the-loop manual approval environment gate "
            "(PLAN-013 anti-goal #16) must stay on the publish job",
        )


class ReleaseNotesTemplateTest(TestEnvContext):
    """Template invariants for the templatized release notes (item 5 (d))."""

    def setUp(self):
        super().setUp()
        self.assertTrue(
            _TEMPLATE.is_file(),
            ".github/release-notes-template.md missing — the Wave B "
            "release.yml renders notes from it (fail-closed)",
        )
        self.source = _TEMPLATE.read_text(encoding="utf-8")

    def test_has_tag_placeholder(self):
        self.assertIn("{{TAG}}", self.source)

    def test_has_base_version_placeholder(self):
        # BASE_VERSION (= VERSION minus -rc.N) points RC notes at the
        # GA CHANGELOG section.
        self.assertIn("{{BASE_VERSION}}", self.source)

    def test_no_stale_release_specific_hardcode(self):
        # The exact stale string this template replaces (PLAN-152
        # §Deferred release-notes-hardcoded-first-release).
        self.assertNotIn("first public release", self.source)

    def test_only_known_placeholders_used(self):
        # The workflow substitutes exactly TAG/VERSION/BASE_VERSION and
        # fails closed on any '{{' left after rendering; an unknown
        # token here would brick every release.
        unknown = set(re.findall(r"\{\{([^}]*)\}\}", self.source)) - {
            "TAG", "VERSION", "BASE_VERSION",
        }
        self.assertEqual(unknown, set(), f"unknown placeholders: {unknown}")


class WorkflowHygieneTest(TestEnvContext):
    """Parse + SHA-pin discipline for both tag-triggered workflows."""

    def test_workflows_parse_as_yaml(self):
        try:
            import yaml  # type: ignore
        except ImportError:  # pragma: no cover - CI installs pyyaml
            self.skipTest("pyyaml not installed")
        for name in ("release.yml", "npm-publish.yml"):
            for path in ((_WF / name), (_STAGED_WF / name),
                         (_STAGED_166_WF / name)):
                if not path.is_file():
                    continue
                with self.subTest(path=str(path)):
                    data = yaml.safe_load(path.read_text(encoding="utf-8"))
                    self.assertIsInstance(data, dict)
                    self.assertIn("jobs", data)

    def test_all_action_uses_are_sha_pinned(self):
        # Every `uses:` in both workflows (live + staged copies) must
        # pin to a 40-hex commit SHA — no floating tags.
        pattern = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)", re.MULTILINE)
        pinned = re.compile(r".+@[0-9a-f]{40}$")
        for name in ("release.yml", "npm-publish.yml"):
            for path in ((_WF / name), (_STAGED_WF / name),
                         (_STAGED_166_WF / name)):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                for used in pattern.findall(text):
                    with self.subTest(path=str(path), uses=used):
                        self.assertRegex(
                            used, pinned,
                            f"{path.name}: `uses: {used}` is not "
                            "SHA-pinned to a 40-hex commit",
                        )


class WaveB5ReleaseYmlTest(TestEnvContext):
    """Wave B item 5 edits to release.yml (dual-context: staged/live)."""

    def setUp(self):
        super().setUp()
        resolved = _wave_b_text("release.yml")
        if resolved is None:
            self.skipTest(
                "Wave B release.yml not landed and staged mirror absent "
                "(pre-landing CI window)"
            )
        self.source, self.context = resolved

    def test_version_gate_strips_rc_suffix(self):
        # PLAN-152 §Deferred release-gate-rc-version-mismatch fix:
        # the tag is normalized before comparing against VERSION.
        self.assertIn('BASE="${EXPECTED%-rc.[0-9]*}"', self.source)
        self.assertIn('if [[ "$FILE" != "$BASE" ]]', self.source)

    def test_changelog_gate_strips_rc_suffix(self):
        # Without this the fixed VERSION gate would just move the RC
        # red run one step later (RC tags have no own CHANGELOG section).
        self.assertIn('VERSION="${VERSION%-rc.[0-9]*}"', self.source)

    def test_plugin_manifest_sync_step_present(self):
        self.assertIn(
            "Assert plugin manifest versions match VERSION", self.source
        )
        self.assertIn(".claude-plugin/plugin.json", self.source)
        self.assertIn(".claude-plugin/marketplace.json", self.source)

    def test_release_create_is_idempotent(self):
        # `gh release view || gh release create` shape: re-runs re-sync
        # assets instead of failing on the existing release.
        self.assertIn('if gh release view "$TAG"', self.source)
        self.assertIn("--clobber install.sh.sha256 sbom.cyclonedx.json",
                      self.source)
        self.assertIn('gh release create "$TAG"', self.source)

    def test_rc_tags_marked_prerelease(self):
        self.assertIn("--prerelease", self.source)

    def test_notes_are_templatized_not_hardcoded(self):
        self.assertIn("release-notes-template.md", self.source)
        self.assertIn("--notes-file release-notes.md", self.source)
        self.assertNotIn(
            "first public release", self.source,
            "stale per-release hardcode back in release.yml "
            "(PLAN-152 §Deferred release-notes-hardcoded-first-release)",
        )


class WaveB5NpmPublishYmlTest(TestEnvContext):
    """Wave B item 5 edits to npm-publish.yml (dual-context: staged/live)."""

    def setUp(self):
        super().setUp()
        resolved = _wave_b_text("npm-publish.yml")
        if resolved is None:
            self.skipTest(
                "Wave B npm-publish.yml not landed and staged mirror "
                "absent (pre-landing CI window)"
            )
        self.source, self.context = resolved

    def test_already_published_guard_present(self):
        self.assertIn("id: already_published", self.source)
        self.assertIn(
            'npm view "${PKG_NAME}@${PKG_VERSION}" version', self.source
        )

    def test_publish_step_gated_on_guard(self):
        self.assertIn(
            "if: steps.already_published.outputs.published != 'true'",
            self.source,
        )

    def test_noop_success_path_is_explicit(self):
        self.assertIn(
            "if: steps.already_published.outputs.published == 'true'",
            self.source,
        )

    def test_rc_exclusion_survives_wave_b(self):
        # Item 5 (f): the Wave B edit must NOT weaken the RC posture.
        self.assertIn(_RC_EXCLUSION, self.source)
        self.assertIn("environment: production-npm", self.source)


class Plan166AwaitGateTest(TestEnvContext):
    """PLAN-166 W1 item 1 — the publish must OBSERVE release.yml's gate.

    Dual-context (staged/live) like the Wave B classes above. These pins
    STRENGTHEN the posture pins — NpmPublishRcPostureTest keeps running
    against the live file in every context.
    """

    def setUp(self):
        super().setUp()
        resolved = _plan166_text("npm-publish.yml")
        if resolved is None:
            self.skipTest(
                "PLAN-166 npm-publish.yml not landed and staged mirror "
                "absent (pre-landing CI window)"
            )
        self.source, self.context = resolved

    def _jobs(self) -> dict:
        try:
            import yaml  # type: ignore
        except ImportError:  # pragma: no cover - CI installs pyyaml
            self.skipTest("pyyaml not installed")
        return yaml.safe_load(self.source)["jobs"]

    def test_publish_needs_await_gate(self):
        # String-level (runs even without pyyaml): the load-bearing edge.
        self.assertIn(
            "needs: await-release-gate", self.source,
            "publish no longer waits for the await-release-gate job — "
            "the npm publish would stop observing release.yml's "
            "release-gate (PLAN-166 F1, P0)",
        )

    def test_publish_needs_await_gate_structurally(self):
        jobs = self._jobs()
        self.assertEqual(
            jobs["publish"].get("needs"), "await-release-gate",
            "the `needs:` must sit on the PUBLISH job itself",
        )

    def test_await_job_authenticates_gh_cli(self):
        # `permissions:` alone does NOT authenticate the gh CLI on a
        # hosted runner; without GH_TOKEN every poll dies on auth →
        # fail-closed BLOCK breaking every release, RC and GA alike.
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.source)
        jobs = self._jobs()
        env = jobs["await-release-gate"].get("env") or {}
        self.assertEqual(
            env.get("GH_TOKEN"), "${{ github.token }}",
            "await-release-gate must carry GH_TOKEN at the JOB level",
        )

    def test_await_job_permissions_and_timeout(self):
        jobs = self._jobs()
        gate = jobs["await-release-gate"]
        self.assertEqual(
            gate.get("permissions"),
            {"contents": "read", "actions": "read"},
            "await job needs exactly contents:read (checkout) + "
            "actions:read (runs/jobs REST) — and nothing more (no "
            "id-token: the gate job must not be able to publish)",
        )
        self.assertEqual(
            gate.get("timeout-minutes"), 35,
            "35 > the poller's 30-minute deadline so a timeout surfaces "
            "as the decision function's fail-CLOSED BLOCK, not an opaque "
            "runner kill",
        )

    def test_await_job_is_the_rc_positive_control(self):
        # NO environment (no manual approval before evidence) and NO RC
        # exclusion: the await job runs on rc tags, so every RC is a live
        # positive control of the gate before GA depends on it.
        jobs = self._jobs()
        gate = jobs["await-release-gate"]
        self.assertNotIn(
            "environment", gate,
            "await-release-gate must NOT gate through an environment — "
            "manual approval belongs AFTER the machine evidence",
        )
        self.assertNotIn(
            "if", gate,
            "await-release-gate must NOT exclude RC tags — RC runs are "
            "the live positive control",
        )

    def test_await_job_invokes_decision_function(self):
        self.assertIn(".claude/scripts/await_release_gate.py", self.source)
        # The deadline is what makes every non-GRANT state collapse to
        # BLOCK (fail-closed) instead of polling forever.
        self.assertIn("--deadline-epoch", self.source)

    def test_publish_posture_verbatim(self):
        jobs = self._jobs()
        pub = jobs["publish"]
        self.assertEqual(pub.get("environment"), "production-npm")
        self.assertIn(_RC_EXCLUSION, pub.get("if", ""))

    def test_already_published_guard_stays_in_publish_after_needs(self):
        # Deliberate ordering (PLAN-166 OQ-1): gate first, manual
        # approval second, last-resort idempotency guard INSIDE publish.
        self.assertLess(
            self.source.index("needs: await-release-gate"),
            self.source.index("id: already_published"),
            "already_published must remain in the publish job, after "
            "the needs: edge — do not move it into the gate job",
        )


class TrustedPublisherBindingTest(TestEnvContext):
    """PLAN-166 W1 item 4 — the npmjs OIDC trusted-publisher triple.

    npm trusted publishing binds by repository + workflow FILENAME +
    environment (oidc-failure-playbook.md:18). This class READS
    .claude/governance/npm-trusted-publisher.txt and cross-checks the
    workflow — it embeds NO values (a 4th copy of the truth).
    """

    def setUp(self):
        super().setUp()
        resolved = _trusted_publisher_values()
        if resolved is None:
            self.skipTest(
                "npm-trusted-publisher.txt not landed and staged copy "
                "absent (pre-landing CI window)"
            )
        self.values, self.txt_context = resolved
        wf_name = self.values["workflow"]
        wf = _plan166_text(wf_name)
        if wf is not None:
            self.workflow_text, self.wf_context = wf
        else:
            live = _WF / wf_name
            if not live.is_file():
                self.fail(
                    "trusted publisher registers workflow %r but "
                    ".github/workflows/%s does not exist — the OIDC "
                    "binding is by FILENAME; publishing would die "
                    "ENEEDAUTH at GA" % (wf_name, wf_name)
                )
            self.workflow_text = live.read_text(encoding="utf-8")
            self.wf_context = "live-pre-plan166"

    def test_registered_workflow_file_publishes(self):
        self.assertIn(
            "npm publish --provenance", self.workflow_text,
            "the workflow the npmjs console points at must be the one "
            "actually publishing",
        )

    def test_workflow_honours_registered_binding(self):
        self.assertEqual(
            _binding_mismatches(self.values, self.workflow_text), [],
            "npm-publish.yml drifted from the npmjs trusted-publisher "
            "registration recorded in npm-trusted-publisher.txt",
        )

    def test_positive_control_environment_mutation_goes_red(self):
        # PLAN-166 W1 item 4 required control: flipping `environment:`
        # in a COPY must be detected — otherwise this whole class is a
        # vacuous gate (registered-vacuous class, S292).
        needle = "environment: " + self.values["environment"]
        self.assertIn(needle, self.workflow_text)
        mutated = self.workflow_text.replace(
            needle, "environment: NOT-THE-REGISTERED-ENV"
        )
        self.assertNotEqual(
            _binding_mismatches(self.values, mutated), [],
            "positive control failed: a mutated environment was not "
            "flagged — the binding check is vacuous",
        )

    def test_positive_control_repository_mutation_goes_red(self):
        self.assertIn(self.values["repository"], self.workflow_text)
        mutated = self.workflow_text.replace(
            self.values["repository"], "someone-else/some-fork"
        )
        self.assertNotEqual(
            _binding_mismatches(self.values, mutated), [],
            "positive control failed: a mutated repository slug was not "
            "flagged — the binding check is vacuous",
        )


# ---------------------------------------------------------------------
# PLAN-166 W1-B — structural asserts for the release.yml verdict delta +
# ancestry gate (F2 server side; re-pass r15+r17+r18, debate r3 scoped
# VETO). Merged verbatim from the W1-B slice file
# (test_release_workflow_asserts_w1b.py) by the PLAN-166 ceremony
# assembler — one runnable asserts file per the W1 pack discipline. Only
# names that would collide with the W1-A section above were renamed
# (_MARKER → _MARKER_W1B, _LIVE_WF/_STAGED_WF → _W1B_*).
#
# What is pinned here, and why each pin exists:
# - The gate step exists, carries NO continue-on-error, and FAILS CLOSED
#   on CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 — the step-15 neighbourhood has
#   two escape hatches keyed to that var (`continue-on-error:` and the
#   empty `--parent-sha ""` bind, which the validator only binds when
#   non-empty); the new gate must never inherit the switch.
# - The delta decision is DELEGATED to
#   .claude/scripts/local/_release_tag_guard.py (the reference
#   implementation) — never re-implemented in bash.
# - Ancestry covers BOTH the reviewed parent AND GITHUB_SHA (r18:
#   parent-only lets the tag-without-push / orphan-verdict scenario pass).
# - PINNED ORDER: Verify tag GPG signature → Validate pair-rail verdict →
#   delta → ancestry.
# - The job keeps the exact name `release-gate` — the W1-A
#   await-release-gate poller resolves the job BY NAME via the Actions
#   jobs endpoint; renaming the job silently breaks the npm-publish gate.
# ---------------------------------------------------------------------

# Marker written into the W1-B step's comment block; its presence in the
# LIVE file means the ceremony landed and the live copy is authoritative.
_MARKER_W1B = "PLAN-166 W1-B"

_W1B_LIVE_WF = _WF / "release.yml"
_W1B_STAGED_WF = _STAGED_166_WF / "release.yml"

_W1B_STEP_NAME = "Verify verdict delta + ancestry (fail-closed)"
_W1B_STEP15_NAME = "Validate pair-rail verdict"
_W1B_GPG_STEP_NAME = "Verify tag GPG signature"
_GUARD_MODULE = ".claude/scripts/local/_release_tag_guard.py"


def _w1b_release_text() -> Optional[Tuple[str, str]]:
    """Return (text, context) for release.yml, or None pre-landing.

    Priority: live copy carrying the W1-B marker (post-landing,
    authoritative) → staged ceremony copy (pre-landing local mirror;
    gitignored so absent in CI) → None (pre-landing CI: skip).
    """
    if _W1B_LIVE_WF.is_file():
        live = _W1B_LIVE_WF.read_text(encoding="utf-8")
        if _MARKER_W1B in live:
            return live, "live"
    if _W1B_STAGED_WF.is_file():
        return _W1B_STAGED_WF.read_text(encoding="utf-8"), "staged"
    return None


def _step_block(source: str, step_name: str) -> str:
    """The text of one step: from its `- name:` to the next step/job."""
    start = source.index("- name: %s" % step_name)
    nxt = source.find("\n      - name:", start + 1)
    job = source.find("\n  publish-release:", start + 1)
    candidates = [i for i in (nxt, job) if i != -1]
    end = min(candidates) if candidates else len(source)
    return source[start:end]


class W1BReleaseGateDeltaAncestryTest(TestEnvContext):
    """The verdict delta + ancestry gate step (dual-context)."""

    def setUp(self):
        super().setUp()
        resolved = _w1b_release_text()
        if resolved is None:
            self.skipTest(
                "PLAN-166 W1-B release.yml not landed and staged mirror "
                "absent (pre-landing CI window)"
            )
        self.source, self.context = resolved

    # -- existence + independence from the step-15 escape hatches --------

    def test_gate_step_present(self):
        self.assertIn(
            "- name: %s" % _W1B_STEP_NAME, self.source,
            "the W1-B verdict delta + ancestry gate step is missing",
        )

    def test_gate_step_has_no_continue_on_error(self):
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertNotIn(
            "continue-on-error", block,
            "the W1-B gate must NEVER carry continue-on-error — that is "
            "exactly the step-15 escape hatch it exists to be independent "
            "of (debate r3 scoped VETO)",
        )

    def test_file_carries_exactly_one_continue_on_error(self):
        # The legacy step 15 keeps its documented transition hatch
        # UNCHANGED (the plan adds a new step; it does not rewrite the
        # neighbourhood). Exactly one KEY occurrence pins both
        # directions at once: the hatch was not silently removed from
        # step 15, and no step (new or old) gained a second one. Comment
        # mentions of the phrase do not count — only the YAML key form.
        key_form = re.findall(
            r"^\s*continue-on-error:", self.source, re.MULTILINE
        )
        self.assertEqual(
            len(key_form), 1,
            "release.yml must carry exactly one continue-on-error KEY "
            "(the legacy step-15 transition hatch); found %d"
            % len(key_form),
        )

    def test_gate_fails_closed_on_transition_var(self):
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertIn(
            'if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]', block,
            "the W1-B gate must test the transition var explicitly",
        )
        guard = block.index(
            'if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]'
        )
        self.assertIn(
            "exit 1", block[guard:guard + 400],
            "the transition-var guard must FAIL CLOSED (exit 1), not skip",
        )

    def test_gate_never_builds_an_empty_parent_bind(self):
        # The step-15 hatch shape: PARENT_SHA_ARG="" under the var. The
        # W1-B block must not contain that shape in any form.
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertNotIn('PARENT_SHA_ARG=""', block)
        self.assertNotIn('--parent-sha ""', block)

    def test_gate_binds_parent_sha_independently(self):
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertIn(
            'VERDICT_FILE_COMMIT="$(git log -n1 --format=%H -- "$VERDICT_FILE")"',
            block,
            "the gate must derive the verdict-file commit itself",
        )
        self.assertIn(
            "_parse_verdict", block,
            "the verdict's parent_sha must be read with the guard "
            "module's parser — two readers of the same signed file must "
            "not be able to disagree",
        )

    # -- delegation to the reference implementation ----------------------

    def test_delta_delegates_to_guard_module(self):
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertIn(
            "%s delta" % _GUARD_MODULE, block,
            "the delta decision must be delegated to the tag-guard "
            "module (single source of the decision logic)",
        )

    def test_ancestry_delegates_to_guard_module(self):
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertIn(
            "%s ancestry" % _GUARD_MODULE, block,
            "the HEAD-ancestry judgment (fail-closed fetch included) "
            "must be delegated to the tag-guard module",
        )

    def test_delta_semantics_not_reimplemented_in_bash(self):
        # The bash body must not carry the decision vocabulary of the
        # module — reading the allowlist or hashing the manifest in
        # shell would be a second implementation of the same closed-set
        # semantics. Comment lines are excluded: the step's rationale
        # comment legitimately NAMES what the module does; only CODE
        # lines may not do it.
        block = _step_block(self.source, _W1B_STEP_NAME)
        code_lines = "\n".join(
            line for line in block.splitlines()
            if not line.lstrip().startswith("#")
        )
        for forbidden in ("delta_allowlist", "shasum -c", "shasum -a 256"):
            self.assertNotIn(
                forbidden, code_lines,
                "the W1-B step re-implements delta semantics in bash "
                "(%r found outside comments) — the module is the only "
                "implementation" % forbidden,
            )

    # -- ancestry covers parent AND GITHUB_SHA (r18) ----------------------

    def test_ancestry_covers_reviewed_parent(self):
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertIn(
            'git merge-base --is-ancestor "$PARENT_SHA" origin/main',
            block,
            "the reviewed parent must be judged against origin/main "
            "(r17: the delta alone never proves the parent was on main)",
        )

    def test_ancestry_covers_github_sha_via_head_identity(self):
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertIn(
            'if [ "$HEAD_SHA" != "${GITHUB_SHA}" ]', block,
            "HEAD == GITHUB_SHA must be asserted so the module's "
            "HEAD-ancestry check covers the tagged commit itself (r18)",
        )

    # -- pinned order (WaveB5 order-assert pattern) -----------------------

    def test_pinned_step_order(self):
        i_gpg = self.source.index("- name: %s" % _W1B_GPG_STEP_NAME)
        i_verdict = self.source.index("- name: %s" % _W1B_STEP15_NAME)
        i_gate = self.source.index("- name: %s" % _W1B_STEP_NAME)
        self.assertLess(
            i_gpg, i_verdict,
            "pinned order broken: GPG verify must precede the verdict "
            "validation",
        )
        self.assertLess(
            i_verdict, i_gate,
            "pinned order broken: the verdict validation (step 15) must "
            "precede the delta+ancestry gate",
        )

    def test_pinned_order_inside_gate_delta_before_ancestry(self):
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertLess(
            block.index("%s delta" % _GUARD_MODULE),
            block.index("%s ancestry" % _GUARD_MODULE),
            "pinned order broken inside the gate: delta before ancestry",
        )
        self.assertLess(
            block.index("%s ancestry" % _GUARD_MODULE),
            block.index('git merge-base --is-ancestor "$PARENT_SHA"'),
            "pinned order broken inside the gate: module ancestry "
            "(fetch + HEAD) before the parent merge-base judgment — the "
            "parent must be judged against the freshly fetched ref",
        )

    def test_gate_lives_inside_release_gate_job(self):
        # The step must run in the same job whose success the W1-A await
        # poller grants on — a gate in another job would not gate the
        # publish path.
        i_job = self.source.index("\n  release-gate:")
        i_next_job = self.source.index("\n  publish-release:")
        i_gate = self.source.index("- name: %s" % _W1B_STEP_NAME)
        self.assertTrue(
            i_job < i_gate < i_next_job,
            "the delta+ancestry gate must be a step of the release-gate "
            "job",
        )


class W1BReleaseGateJobNameTest(TestEnvContext):
    """The exact job name `release-gate` is load-bearing (W1-A await)."""

    def setUp(self):
        super().setUp()
        resolved = _w1b_release_text()
        if resolved is None:
            self.skipTest(
                "PLAN-166 W1-B release.yml not landed and staged mirror "
                "absent (pre-landing CI window)"
            )
        self.source, self.context = resolved

    def test_release_gate_job_name_exact(self):
        self.assertRegex(
            self.source, re.compile(r"^  release-gate:$", re.MULTILINE),
            "the job MUST keep the exact name `release-gate` — the "
            "W1-A await-release-gate poller resolves it BY NAME via the "
            "Actions jobs endpoint",
        )

    def test_publish_release_still_needs_release_gate(self):
        self.assertIn(
            "needs: release-gate", self.source,
            "publish-release must stay gated on release-gate",
        )


class W1BGuardModuleContractTest(TestEnvContext):
    """The live module surface the workflow step depends on.

    These asserts pin the CONTRACT the W1-B step consumes, so a module
    refactor that renames a subcommand or the parser is caught by the
    suite before it bricks a release run.
    """

    def setUp(self):
        super().setUp()
        self.module_path = _REPO / _GUARD_MODULE
        if not self.module_path.is_file():
            self.fail(
                "%s missing — the W1-B release.yml step invokes it; "
                "landing the workflow without the module bricks every "
                "release run" % _GUARD_MODULE
            )
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "release_tag_guard_w1b_contract", str(self.module_path)
        )
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_module_exposes_the_consumed_surface(self):
        for attr in ("_parse_verdict", "delta", "ancestry", "main"):
            self.assertTrue(
                hasattr(self.mod, attr),
                "module lost %r — the W1-B workflow step consumes it"
                % attr,
            )

    def test_parse_verdict_reads_parent_sha(self):
        fields = self.mod._parse_verdict(
            "# t\n\n```yaml\nparent_sha: "
            "4111a115190d375c39c90cc33ac1d9d5899c1cf2\n```\n"
        )
        self.assertEqual(
            fields.get("parent_sha"),
            "4111a115190d375c39c90cc33ac1d9d5899c1cf2",
        )

    def test_module_exit_codes_are_distinct_nonzero(self):
        # The workflow relies on ANY non-zero exit failing the step
        # (set -euo pipefail); pin that the module's failure codes are
        # non-zero and mutually distinct so the failure MODE stays
        # testable.
        codes = [
            self.mod.E_USAGE, self.mod.E_FETCH, self.mod.E_NOT_ANCESTOR,
            self.mod.E_REMOTE_REF, self.mod.E_DELTA,
            self.mod.E_MANIFEST_PIN, self.mod.E_MANIFEST_CONTENT,
            self.mod.E_MANIFEST_SET, self.mod.E_VERDICT, self.mod.E_VACUOUS,
        ]
        self.assertNotIn(0, codes)
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
