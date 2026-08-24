"""PLAN-183 W5-a (D2) — `_src_digest` resolves by DELIVERY ROUTE, not by existence.

Covers scripts/tests/_parity_classify.py (NOT .claude/scripts/ — the classifier
lives at repo-root scripts/tests/, which is structurally unable to host a
pytest: it is absent from pytest.ini testpaths and has no conftest.py, so a
test placed beside the module would be collected by nobody — a false green by
construction). This root IS in testpaths and runs per-PR in validate.yml,
following the precedent of test_build_plugin_idempotency.py.

The defect (PLAN-183 §8.2): `_src_digest` resolved "identity map first, then
templates/". For a path the installer delivers FROM `templates/` that also has
a homonym at the repo root, identity won and the comparison ran against a
framework artifact the adopter never received — `docs/BRANCH-PROTECTION.md`
came out UNCLASSIFIED when the truth is STALE, and `docs/rotation-log.md` was
the same defect latent.

What is asserted here, and why each assertion exists:

* the two `docs/` routes resolve from `templates/`, and the digest DIFFERS
  from the root homonym's (a cure that resolved to the root file would be
  byte-identical and this test would go red);
* the cure ENUMERATES and does not blindly invert — a path present at BOTH
  root and `templates/` but absent from the route map still resolves to the
  ROOT (identity-first preserved). Blind `templates/`-first would break every
  path legitimately delivered by the identity map;
* the `.github/*.template` routes, measured CORRECT before the cure, stay
  correct (no regression);
* the RENDERED destination `.github/CODEOWNERS` resolves to None rather than
  silently to this repository's own live CODEOWNERS;
* TWO censuses, because one is provably blind. The same-name census catches a
  new `templates/` homonym; it is BLIND whenever source and destination names
  differ or content is rendered (`CODEOWNERS.template` -> `CODEOWNERS` is the
  live proof). So the authoritative census parses install.sh's own copy calls
  and requires every DELIVERY ROUTE to be classified -- a renamed or
  transformed route fails there instead of resolving silently.
* non-vacuity guards on every map-looping test. Measured: deleting one map
  entry left the per-entry tests green (empty loop = free pass) and only the
  census went red; with the guards the same sabotage turns three tests red.

Hermetic: every mechanism assertion builds its own source trees in a tempdir.
Live-repo assertions are read-only and documented as such.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLASSIFIER = REPO / "scripts" / "tests" / "_parity_classify.py"

_HOOKS_DIR = REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_spec = importlib.util.spec_from_file_location("_parity_classify", CLASSIFIER)
pc = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec.loader is not None
_spec.loader.exec_module(pc)  # type: ignore[union-attr]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class _Tree(TestEnvContext):
    """Builds a synthetic framework-source tree under a tempdir."""

    def setUp(self) -> None:
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-plan183-w5a-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    def write(self, rel: str, body: str) -> Path:
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
        return p


class TestDeliveryRouteResolution(_Tree):
    """The MECHANISM, on synthetic trees — full control of both sides."""

    def test_mapped_route_resolves_from_templates_not_root_homonym(self) -> None:
        # Non-vacuity guard: a loop over an EMPTY map passes for free. The
        # negative control proved this class -- deleting a map entry left the
        # per-entry tests green and only the route census went red.
        self.assertTrue(pc._TEMPLATE_DELIVERED, "_TEMPLATE_DELIVERED is empty")
        # Positive control that reproduces the MECHANISM, not the appearance:
        # the destination exists at BOTH places with DIVERGENT content, and the
        # route map must pick templates/.
        for dest, src in sorted(pc._TEMPLATE_DELIVERED.items()):
            with self.subTest(dest=dest):
                self.write(dest, "ROOT-HOMONYM-%s" % dest)
                self.write(src, "TEMPLATE-%s" % dest)
                got = pc._src_digest(str(self.tmp), dest, [])
                self.assertEqual(
                    got,
                    _sha("TEMPLATE-%s" % dest),
                    "%s must resolve from %s (the bytes the adopter received); "
                    "resolving to the root homonym is defect D2" % (dest, src),
                )
                self.assertNotEqual(
                    got,
                    _sha("ROOT-HOMONYM-%s" % dest),
                    "%s resolved to the ROOT homonym — the cure was reverted "
                    "or the route map lost this entry" % dest,
                )

    def test_mapped_route_resolves_with_no_homonym_planted(self) -> None:
        self.assertTrue(pc._TEMPLATE_DELIVERED, "_TEMPLATE_DELIVERED is empty")
        # Negative control: absent the homonym, the same path still resolves
        # from templates/. Proves the map is consulted, not the collision.
        for dest, src in sorted(pc._TEMPLATE_DELIVERED.items()):
            with self.subTest(dest=dest):
                self.write(src, "ONLY-TEMPLATE-%s" % dest)
                self.assertEqual(
                    pc._src_digest(str(self.tmp), dest, []),
                    _sha("ONLY-TEMPLATE-%s" % dest),
                )

    def test_unmapped_path_keeps_identity_first(self) -> None:
        # The cure ENUMERATES; it does not invert. A path outside the map that
        # exists at BOTH places must still resolve to the ROOT — blind
        # templates/-first would break every identity-mapped delivery.
        rel = ".claude/team.md"
        self.write(rel, "ROOT-WINS")
        self.write("templates/%s" % rel, "TEMPLATE-LOSES")
        self.assertEqual(pc._src_digest(str(self.tmp), rel, []), _sha("ROOT-WINS"))

    def test_unmapped_path_falls_back_to_templates(self) -> None:
        # And the pre-existing fallback still works when only templates/ has it.
        rel = ".github/workflows/validate.yml.template"
        self.write("templates/%s" % rel, "TEMPLATE-FALLBACK")
        self.assertEqual(
            pc._src_digest(str(self.tmp), rel, []), _sha("TEMPLATE-FALLBACK")
        )

    def test_rendered_destination_is_unresolvable_not_wrong(self) -> None:
        self.assertTrue(pc._RENDERED_DELIVERED, "_RENDERED_DELIVERED is empty")
        # install.sh renders {{OWNER_HANDLE}} at install time, so the delivered
        # bytes exist nowhere in the checkout. Falling through to identity here
        # would compare against this repo's own live CODEOWNERS.
        for dest in sorted(pc._RENDERED_DELIVERED):
            with self.subTest(dest=dest):
                self.write(dest, "THIS-REPOS-OWN-LIVE-FILE")
                self.write(pc._RENDERED_DELIVERED[dest], "RAW-TEMPLATE")
                self.assertIsNone(
                    pc._src_digest(str(self.tmp), dest, []),
                    "%s must report UNRESOLVABLE, never a digest — resolving it "
                    "silently compares against bytes the adopter never had"
                    % dest,
                )


class TestLiveRepoRoutes(_Tree):
    """Read-only assertions against the real checkout (documents today's truth)."""

    def test_docs_routes_diverge_from_their_root_homonyms(self) -> None:
        self.assertTrue(pc._TEMPLATE_DELIVERED, "_TEMPLATE_DELIVERED is empty")
        # If these ever stop diverging the defect becomes unobservable and the
        # mechanism tests above are the only guard left — assert it explicitly.
        for dest, src in sorted(pc._TEMPLATE_DELIVERED.items()):
            with self.subTest(dest=dest):
                root_d = pc._digest(str(REPO / dest), [])
                tpl_d = pc._digest(str(REPO / src), [])
                self.assertIsNotNone(tpl_d, "%s missing from the checkout" % src)
                if root_d is not None:
                    self.assertNotEqual(
                        root_d,
                        tpl_d,
                        "%s and %s are byte-identical — D2 became unobservable "
                        "on this path; re-read PLAN-183 §8.2 before relaxing "
                        "anything" % (dest, src),
                    )
                self.assertEqual(pc._src_digest(str(REPO), dest, []), tpl_d)

    def test_every_declared_source_exists_at_head(self) -> None:
        self.assertTrue(pc._TEMPLATE_DELIVERED and pc._RENDERED_DELIVERED,
                        "a route map is empty -- the loop below would be vacuous")
        # `_digest` returns None for BOTH "absent" and "unreadable", so a typo
        # in a route map would resolve to None at runtime and degrade silently
        # into UNCLASSIFIED. Runtime cannot raise (an old pin legitimately may
        # not carry a source yet, and crashing the classifier there would be
        # worse), so the guard belongs HERE: every declared source must exist
        # in the working tree.
        for mapping in (pc._TEMPLATE_DELIVERED, pc._RENDERED_DELIVERED):
            for dest, src in sorted(mapping.items()):
                with self.subTest(dest=dest):
                    self.assertTrue(
                        (REPO / src).is_file(),
                        "route map declares %s -> %s but that source does not "
                        "exist; a typo here degrades silently to UNCLASSIFIED "
                        "instead of failing loudly" % (dest, src),
                    )

    def test_template_suffixed_routes_unregressed(self) -> None:
        # Measured CORRECT before the cure; must stay correct.
        for rel in (
            ".github/workflows/validate.yml.template",
            ".github/workflows/benchmarks.yml.template",
            ".github/CODEOWNERS.template",
        ):
            with self.subTest(rel=rel):
                self.assertEqual(
                    pc._src_digest(str(REPO), rel, []),
                    pc._digest(str(REPO / "templates" / rel), []),
                )

    def test_census_is_derived_from_DELIVERY_ROUTES_not_same_name_files(self) -> None:
        # The same-name census below is BLIND whenever source and destination
        # names differ or the content is rendered -- `CODEOWNERS.template` ->
        # `CODEOWNERS` is the live proof (PLAN-183 §8.2). So the authoritative
        # census derives from the installer's own copy calls: every route
        # install.sh delivers under docs/ or .github/ must be CLASSIFIED, and a
        # new or renamed route fails here instead of resolving silently against
        # the wrong file.
        installer = (REPO / "scripts" / "install.sh").read_text()
        joined = re.sub(r"\\\n\s*", " ", installer)  # join line continuations
        routes = set(
            re.findall(r'install_docs_template\s+"([^"]+)"\s+"([^"]+)"', joined)
        )
        # the rendered branch does not go through the helper (own inline sed)
        for dest in re.findall(r'local dst="\$TARGET/(\.github/CODEOWNERS)"', installer):
            routes.add(("templates/.github/CODEOWNERS.template", dest))

        self.assertTrue(routes, "no delivery routes parsed from install.sh")

        unclassified = []
        for src, dest in sorted(routes):
            if dest in pc._TEMPLATE_DELIVERED or dest in pc._RENDERED_DELIVERED:
                continue  # explicitly mapped
            if src == "templates/%s" % dest:
                continue  # identity-mapped: the existing fallback is correct
            unclassified.append("%s -> %s" % (src, dest))

        self.assertEqual(
            unclassified,
            [],
            "delivery route(s) whose SOURCE relpath differs from the "
            "destination and which are absent from both route maps: %s. Each "
            "needs an entry (or an explicit identity justification) or "
            "_src_digest will silently compare against the wrong file."
            % unclassified,
        )

    def test_route_map_census_is_closed(self) -> None:
        # The census that closes the class: every templates/ path whose
        # DESTINATION also exists at the repo root is either in the route map,
        # or declared here with its reason. A new one fails this test instead
        # of silently comparing against the wrong file.
        declared_out = {
            # not delivered by any install_template call
            "README.md",
            # absorbed by the ACCEPTED ledger (^(CLAUDE|MEMORY)\.md$)
            "CLAUDE.md",
        }
        templates = REPO / "templates"
        collisions = set()
        for p in templates.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(templates))
            if (REPO / rel).is_file():
                collisions.add(rel)
        unaccounted = collisions - set(pc._TEMPLATE_DELIVERED) - declared_out
        self.assertEqual(
            unaccounted,
            set(),
            "new templates/ path(s) whose destination collides with a repo-root "
            "file and which are NOT in _TEMPLATE_DELIVERED nor declared "
            "out-of-scope: %s. Each needs a verdict (delivered / not-delivered "
            "/ absorbed by ACCEPTED) before this test is relaxed."
            % sorted(unaccounted),
        )

    # ---- the shared route table (PLAN-183 §8.5.2 debt, closed S325) -------

    def test_route_table_is_shared_data_read_from_disk(self) -> None:
        """USE, not mention -- debate convergence C3 / finding A9.

        Verifying the promotion with `grep -l delivery-routes.tsv` proves the
        filename APPEARS in a consumer; it does not prove the consumer
        consults it. A module could grep-match and still carry a private
        constant. So this asserts the views are exactly the projection of
        what the TSV on disk currently says, at the shared path both
        consumers agree on. Paired with the removal control (deleting the
        table must make this suite red), that is behavioural proof.
        """
        tsv = Path(pc._ROUTES_TSV)
        self.assertTrue(
            tsv.is_file(),
            "the shared route table is missing at %s -- the two consumers "
            "have nothing to agree on" % tsv,
        )
        self.assertEqual(
            tsv.relative_to(REPO).as_posix(),
            "scripts/delivery-routes.tsv",
            "the table moved; `scripts/doctor.sh` resolves it by that exact "
            "relpath, so a move here silently un-shares it",
        )
        on_disk = pc._load_delivery_routes()
        self.assertEqual(
            pc._TEMPLATE_DELIVERED,
            {
                r["dest"]: r["src"]
                for r in on_disk
                if r["transform"] == pc._TRANSFORM_IDENTITY
            },
            "_TEMPLATE_DELIVERED is not the projection of the table on disk "
            "-- it has drifted back into a module-local constant",
        )
        self.assertEqual(
            pc._RENDERED_DELIVERED,
            {
                r["dest"]: r["src"]
                for r in on_disk
                if r["transform"] != pc._TRANSFORM_IDENTITY
            },
            "_RENDERED_DELIVERED is not the projection of the table on disk",
        )

    def test_table_rows_match_the_installers_own_call_sites(self) -> None:
        """Breaks the tautology that let a WRONG source pass.

        Measured in S325: repointing `docs/BRANCH-PROTECTION.md` at
        `templates/docs/rotation-log.md` -- a source that is wrong but
        present -- kept all ten pre-existing tests GREEN. The cause is
        structural: the live-route assertions compare `_src_digest` against
        the digest of the source THE TABLE ITSELF declares, so both sides of
        the equality move together and no amount of digest-checking can tell
        the right source from a wrong one.

        The only way out is an INDEPENDENT truth. That truth is the
        installer's own copy call-sites: `install_docs_template <src> <dst>`
        plus the one inline rendered branch. Both directions are asserted --
        a missing row and an invented row each fail here.
        """
        installer = (REPO / "scripts" / "install.sh").read_text()
        joined = re.sub(r"\\\n\s*", " ", installer)  # join line continuations
        pairs = set(
            re.findall(r'install_docs_template\s+"([^"]+)"\s+"([^"]+)"', joined)
        )
        # The rendered branch does not go through the helper (inline sed).
        for dest in re.findall(
            r'local dst="\$TARGET/(\.github/CODEOWNERS)"', installer
        ):
            pairs.add(("templates/.github/CODEOWNERS.template", dest))
        self.assertTrue(
            pairs,
            "no delivery routes parsed from install.sh -- the independent "
            "truth this test depends on is gone, so a green here would be "
            "vacuous",
        )

        table = {r["dest"]: r["src"] for r in pc.DELIVERY_ROUTES}

        wrong = []
        for src, dest in sorted(pairs):
            declared = table.get(dest)
            if declared is None:
                wrong.append(
                    "%s: MISSING from the table (installer delivers it from %s)"
                    % (dest, src)
                )
            elif declared != src:
                wrong.append(
                    "%s: table says %r, installer says %r" % (dest, declared, src)
                )
        self.assertEqual(
            wrong,
            [],
            "the shared table disagrees with install.sh about where these "
            "destinations come from: %s. A wrong source makes every consumer "
            "compare against the wrong bytes -- that is defect D2/D3/D4." % wrong,
        )

        invented = sorted(set(table) - {dest for _src, dest in pairs})
        self.assertEqual(
            invented,
            [],
            "the table declares destination(s) install.sh never delivers: %s. "
            "An invented row makes doctor.sh repair a file the adopter was "
            "never given." % invented,
        )

    def test_malformed_table_fails_closed(self) -> None:
        """A table we cannot parse must RAISE, never default.

        CLAUDE.md §4: fail-open on infrastructure, fail-closed on INPUT. This
        table decides which source each destination is compared against, so a
        silently-degraded read is not a degraded read -- it is the D2
        misclassification arriving quietly.
        """
        header = "\t".join(pc._ROUTE_COLUMNS)
        good = "docs/x.md\ttemplates/docs/x.md\tidentity\t-\torigin\tnote"
        cases = {
            "header drifted": "dest\tsrc\ttransform\n" + good,
            "wrong field count": header + "\ndocs/x.md\ttemplates/docs/x.md\tidentity",
            "duplicate destination": header + "\n" + good + "\n" + good,
            "empty dest": header + "\n\ttemplates/docs/x.md\tidentity\t-\to\tn",
            "no header": good,
            "no routes": "# only comments\n" + header,
        }
        for label, body in sorted(cases.items()):
            path = self.tmp / ("routes-%s.tsv" % label.replace(" ", "-"))
            path.write_text(body + "\n", encoding="utf-8")
            with self.assertRaises(RuntimeError, msg="%s parsed instead of raising" % label):
                pc._load_delivery_routes(str(path))

        # Positive control: the same reader accepts a well-formed table, so a
        # green above cannot come from a reader that rejects everything.
        ok = self.tmp / "routes-ok.tsv"
        ok.write_text(header + "\n" + good + "\n", encoding="utf-8")
        parsed = pc._load_delivery_routes(str(ok))
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["dest"], "docs/x.md")
        self.assertEqual(parsed[0]["src"], "templates/docs/x.md")


if __name__ == "__main__":
    unittest.main()
