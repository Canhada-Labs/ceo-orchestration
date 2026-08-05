#!/usr/bin/env python3
# ============================================================================
# PLAN-166 / W0 item 5 — guard: NO bump-touched file may enter
# `.claude/governance/pair-rail-inputs-hash-manifest.txt`.
# ============================================================================
"""The exclusion of the release-bump surfaces from the pair-rail inputs
manifest is DELIBERATE. It is not the blindness.

THE DECISION THIS TEST PINS
---------------------------
`validate-pair-rail-verdict.py` recomputes `inputs_hash` by `git hash-object`
over every path listed in `pair-rail-inputs-hash-manifest.txt` and asserts it
equals the `inputs_hash` recorded in the signed verdict. That equality is a
REPLAY defence: it proves the verdict under review was produced over the same
trust-chain bytes that are on disk now.

Adding a bump-touched file (`VERSION`, `npm/package.json`, the four
`last-reviewed:` stamps, the two generated plugin manifests, ...) to that
manifest would make EVERY LEGITIMATE `release.sh bump` change `inputs_hash`.
The verdict would stop replaying the moment the version moved — which destroys
the only property the manifest exists to provide. So the bump surfaces stay
OUT, on purpose.

WHY THAT IS NOT THE step-15 BLINDNESS (refutes review r3 P1, plan §W0 item 5)
-----------------------------------------------------------------------------
F2's finding was that a post-preflight bump commit is INVISIBLE to release.yml
step 15 precisely because none of the bump files is in this manifest. The cure
is NOT to widen the manifest — that trades a narrow blind spot for a broken
replay. The cure lands on two other rails, both in PLAN-166:

  * F2's same-tree no-op removes the D+1 commit at the source (there is no
    extra commit to be blind to);
  * `tag()`'s restricted-delta assert (local driver AND server-side in
    release.yml, unconditional for RC and stable) kills any delta between the
    reviewed parent and the tagged commit that is not on the verdict's pinned
    allowlist.

CONTRACT OF THIS FILE
---------------------
This test FAILS if a bump path ENTERS the manifest, and the failure message
carries the reasoning above — so the next maintainer who "fixes" the step-15
blind spot by pasting `VERSION` into the manifest is stopped, and told why.

Read-only by construction: the live manifest is never mutated here (a mutation
would open a new entry inside the W1 ceremony scope). Positive controls are
run against SYNTHETIC manifests in a tempdir.

DERIVATIONS (no hand-typed closed sets — PLAN-166 rule: derive from the
authority, never recall)
  * manifest path      <- the `--inputs-hash-paths-file` argument as it appears
                          in `.github/workflows/*.yml` (the consumer).
  * manifest entries   <- `compute_inputs_hash()` of the real validator,
                          EXECUTED with `git hash-object` stubbed; the paths it
                          feeds the stub ARE the authority's parse result.
  * bump table         <- `_release_bump_sites.site_paths()`.
  * generated pair     <- `build-plugin.write_manifest_files()` RUN into a
                          tempdir; the filenames it produces are observed, not
                          recalled. Deriving only from the bump module would
                          leave the guard blind to these two, which the driver
                          regenerates via `build-plugin.py --write-manifests`.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import List
from unittest import mock

# Env-hygiene gate (check-test-env-hygiene.py): test classes subclass
# TestEnvContext, not bare unittest.TestCase, so HOME / CLAUDE_PROJECT_DIR /
# os.environ / sys.path are snapshot-restored around every test.
_HOOKS_DIR = Path(__file__).resolve().parents[2] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


def _rel(p: Path) -> str:
    """Repo-relative display path; never raises inside a failure message."""
    try:
        return p.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(p)


_VALIDATOR_SRC = REPO / ".github" / "scripts" / "validate-pair-rail-verdict.py"
_BUMP_SRC = REPO / ".claude" / "scripts" / "local" / "_release_bump_sites.py"
_BUILD_PLUGIN_SRC = REPO / "scripts" / "build-plugin.py"


def _load(src: Path, name: str):
    """Import a dashed/dotted script by path WITHOUT touching sys.modules.

    sys.modules rebinding is not CI-safe (S265 lesson); these three scripts are
    flat, import nothing relative, so exec_module on an unregistered module is
    enough.
    """
    if not src.is_file():
        raise AssertionError(
            "authority missing: %s — this guard derives its reference list "
            "from that file; a rename must update this test, never silently "
            "disable it" % src
        )
    spec = importlib.util.spec_from_file_location(name, str(src))
    if spec is None or spec.loader is None:
        raise AssertionError("cannot build import spec for %s" % src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VALIDATOR = _load(_VALIDATOR_SRC, "_ceo_t166_validate_pair_rail_verdict")
BUMP = _load(_BUMP_SRC, "_ceo_t166_release_bump_sites")
BUILD_PLUGIN = _load(_BUILD_PLUGIN_SRC, "_ceo_t166_build_plugin")

_FLAG = "--inputs-hash-paths-file"


def manifest_path_from_workflows() -> Path:
    """The manifest path as the CONSUMER spells it (release.yml step 15)."""
    wf_dir = REPO / ".github" / "workflows"
    found = set()
    for wf in sorted(wf_dir.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        for m in re.finditer(re.escape(_FLAG) + r"\s+([^\s\\]+)", text):
            found.add(m.group(1).strip("'\""))
    if not found:
        raise AssertionError(
            "no workflow passes %s — either the pair-rail replay defence was "
            "removed (a governance regression) or the flag was renamed; this "
            "guard refuses to pass vacuously" % _FLAG
        )
    if len(found) != 1:
        raise AssertionError(
            "workflows disagree on the inputs manifest: %s" % sorted(found)
        )
    return REPO / sorted(found)[0]


def manifest_entries(manifest: Path) -> List[str]:
    """Parse `manifest` with the validator's OWN parser, executed.

    `compute_inputs_hash()` is run with the module-level `subprocess` reference
    swapped for a stub, so no `git hash-object` ever runs; the argv the stub
    receives is the authority's parse result. If the validator changes its
    comment/blank-line rule, this guard follows it for free instead of drifting
    against a re-implementation.
    """
    seen: List[str] = []

    def _fake_run(cmd, **kwargs):
        if list(cmd[:2]) != ["git", "hash-object"]:
            raise AssertionError("unexpected subprocess call: %r" % (cmd,))
        seen.append(cmd[2])
        return types.SimpleNamespace(returncode=0, stdout="0" * 40 + "\n", stderr="")

    with mock.patch.object(VALIDATOR, "subprocess", types.SimpleNamespace(run=_fake_run)):
        VALIDATOR.compute_inputs_hash(REPO, manifest)
    return seen


def generated_manifest_paths() -> List[str]:
    """Run the generator; observe which manifests it writes (never recall)."""
    with tempfile.TemporaryDirectory(prefix="ceo-t166-gen-") as td:
        dest = Path(td) / "out"
        BUILD_PLUGIN.write_manifest_files(dest)
        names = sorted(p.name for p in dest.iterdir() if p.is_file())
    if not names:
        raise AssertionError("build-plugin wrote no manifests — derivation broken")
    rel = BUILD_PLUGIN.MANIFESTS.resolve().relative_to(REPO.resolve()).as_posix()
    return [rel + "/" + n for n in names]


def bump_reference_paths() -> List[str]:
    """Every path a `release.sh bump` may rewrite: module table + generated."""
    out: List[str] = list(BUMP.site_paths(include_generated=False))
    for p in generated_manifest_paths():
        if p not in out:
            out.append(p)
    return out


def offenders(manifest: Path, reference: List[str]) -> List[str]:
    """Bump paths present in `manifest`, per the authority's parse."""
    return sorted(set(manifest_entries(manifest)) & set(reference))


_WHY = (
    "The exclusion is DELIBERATE, not the step-15 blind spot.\n"
    "  Any bump path inside the inputs manifest makes `inputs_hash` change on\n"
    "  every legitimate version bump, so the signed verdict stops replaying —\n"
    "  the single property the manifest exists to provide.\n"
    "  The F2 blind spot is closed elsewhere: (a) the same-tree no-op removes\n"
    "  the D+1 bump commit, (b) tag()'s restricted-delta assert (driver AND\n"
    "  release.yml, RC and stable alike) rejects any parent->tag delta outside\n"
    "  the verdict's pinned allowlist.\n"
    "  If you got here while widening step-15 coverage: widen it on those two\n"
    "  rails, not here. See PLAN-166 W0 item 5."
)


class ManifestPathDerivation(TestEnvContext):
    def test_manifest_path_comes_from_the_consuming_workflow(self):
        manifest = manifest_path_from_workflows()
        self.assertTrue(
            manifest.is_file(),
            "release.yml passes %s %s but that file does not exist — step 15 "
            "would INFRA-fail" % (_FLAG, manifest),
        )


class ReferenceListDerivation(TestEnvContext):
    """The reference list must not be able to go blind silently."""

    def test_generator_written_manifests_are_in_the_reference(self):
        generated = generated_manifest_paths()
        ref = bump_reference_paths()
        for path in generated:
            self.assertIn(
                path,
                ref,
                "build-plugin.py writes %s during the bump phase but the guard's "
                "reference list does not contain it — the guard is blind to it "
                "(plan W0 item 5: 'derivar so do modulo deixaria o guard cego')"
                % path,
            )

    def test_bump_module_export_agrees_with_the_generator(self):
        """`site_paths(include_generated=True)` must equal the observed union.

        Not a test of the bump module's taste — a test that THIS guard's two
        derivation routes agree. If build-plugin starts writing a third
        manifest, or GENERATED_BY_BUMP is dropped, this fails loudly instead of
        the guard quietly shrinking.
        """
        module_view = set(BUMP.site_paths(include_generated=True))
        observed = set(bump_reference_paths())
        self.assertEqual(
            module_view,
            observed,
            "derivation routes disagree:\n"
            "  only in _release_bump_sites.site_paths(include_generated=True): %s\n"
            "  only in table+generator observation:                            %s"
            % (
                sorted(module_view - observed),
                sorted(observed - module_view),
            ),
        )

    def test_reference_is_non_empty_and_deduplicated(self):
        ref = bump_reference_paths()
        self.assertGreater(len(ref), 1, "reference list collapsed: %s" % ref)
        self.assertEqual(len(ref), len(set(ref)), "duplicate in reference: %s" % ref)


class LiveManifestGuard(TestEnvContext):
    def test_no_bump_touched_file_is_listed_in_the_inputs_manifest(self):
        manifest = manifest_path_from_workflows()
        ref = bump_reference_paths()
        entries = manifest_entries(manifest)
        # INPUTS of the measurement, printed (a verdict-bearing check that hides
        # its inputs is a licence to drift).
        print(
            "\n[T166-W0-5] manifest      : %s"
            "\n[T166-W0-5] entries parsed: %d (by validate-pair-rail-verdict."
            "compute_inputs_hash)"
            "\n[T166-W0-5] bump reference: %d paths"
            "\n%s"
            % (
                _rel(manifest),
                len(entries),
                len(ref),
                "".join("[T166-W0-5]   - %s\n" % p for p in ref),
            )
        )
        self.assertGreater(len(entries), 0, "manifest parsed to zero entries")
        bad = sorted(set(entries) & set(ref))
        self.assertEqual(
            bad,
            [],
            "bump-touched path(s) found in %s: %s\n%s"
            % (_rel(manifest), bad, _WHY),
        )


class PositiveControls(TestEnvContext):
    """A green fixture is not proof of enforcement — plant the violation."""

    def setUp(self):
        super().setUp()
        self._td = tempfile.TemporaryDirectory(prefix="ceo-t166-ctl-")
        self.tmp = Path(self._td.name)
        self.ref = bump_reference_paths()
        self.addCleanup(self._td.cleanup)
        # Vacuity guard: the fixture filler must NOT itself be a bump path, or
        # the negative controls below would be green for the wrong reason.
        filler = [ln for ln in self._HEADER.splitlines() if ln and not ln.startswith("#")]
        self.assertEqual(
            sorted(set(filler) & set(self.ref)),
            [],
            "fixture filler collides with the bump reference: %s" % filler,
        )

    def _write(self, body: str) -> Path:
        p = self.tmp / "synthetic-manifest.txt"
        p.write_text(body, encoding="utf-8")
        return p

    _HEADER = (
        "# synthetic manifest (test fixture)\n"
        "\n"
        ".claude/hooks/check_pair_rail.py\n"
        "SPEC/v1/audit-log.schema.md\n"
    )

    def test_control_every_single_bump_path_is_detected(self):
        """Plant each reference path in turn; each must be caught."""
        for path in self.ref:
            with self.subTest(planted=path):
                m = self._write(self._HEADER + path + "\n")
                self.assertEqual(
                    offenders(m, self.ref),
                    [path],
                    "planted %s but the guard did not flag it" % path,
                )

    def test_control_inline_trailing_comment_does_not_hide_an_entry(self):
        planted = generated_manifest_paths()[0]
        m = self._write(self._HEADER + planted + "   # regenerated by build-plugin\n")
        self.assertEqual(
            offenders(m, self.ref),
            [planted],
            "an entry with a trailing comment escaped the guard — the parse "
            "must strip the comment BEFORE comparing",
        )

    def test_control_clean_synthetic_manifest_is_green(self):
        """Negative control: the detector is not simply always-red."""
        m = self._write(self._HEADER)
        self.assertEqual(offenders(m, self.ref), [])

    def test_control_commented_out_bump_path_is_not_flagged(self):
        """Over-sensitivity control: a commented line is not an entry.

        Mirrors the authority's own parse (`line.split('#', 1)[0].strip()`),
        which this guard executes rather than re-implements.
        """
        planted = self.ref[0]
        m = self._write(self._HEADER + "# " + planted + "\n\n   \n")
        self.assertEqual(
            offenders(m, self.ref),
            [],
            "a COMMENTED bump path was flagged as an entry — the guard is not "
            "using the validator's parse",
        )


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
