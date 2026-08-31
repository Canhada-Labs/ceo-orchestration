"""PLAN-169 wave-s330-F (OQ-E5) — the user template is DERIVED, not copied.

Oracle for ``.claude/scripts/gen-settings-user-template.py`` and for the
``_derivation`` spec embedded in ``templates/settings/settings.user.json``.

WHY THIS FILE EXISTS
--------------------
The user-ceremony template was a MANUAL copy of the base template with hooks
deleted by hand, frozen at 9777a8d. Its own ``_comment`` asserted two things
CI never read: that it removed "exactly 10" hooks, and that every retained
entry was byte-identical to base in its behavioural fields. Measured in S330,
both were false — 26 removed basenames, a hand-narrowed matcher, a silently
dropped second registration, three hand-edited annotations. A numeral in JSON
prose is watched by nothing; that is how it rotted.

So the subtraction became DATA and the copy became a GENERATOR, and this file
is the gate that makes the pair mean something. Two properties carry the
weight:

  PARITY      the shipped template is exactly what the generator produces
              from the base template plus the spec (bytes, not structure).
  INTEGRITY   the spec cannot quietly stop matching reality — a dead
              exclusion, a dead override, an unknown class or an empty
              reason is RED, not a silent no-op.

Expectations are DERIVED from the shipped artifacts wherever a derivation is
possible: re-listing the roster here would rebuild, inside the oracle, the
very second-copy defect the wave removes. The deliberate exceptions are named
anchors (the ``check_output_secrets.py`` dual registration, the frozen pre-F
fixture) and they are anchors on purpose.

stdlib-only; Python >= 3.9.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import py_compile
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATOR = REPO_ROOT / ".claude" / "scripts" / "gen-settings-user-template.py"
BASE_TEMPLATE = REPO_ROOT / "templates" / "settings" / "settings.base.json"
USER_TEMPLATE = REPO_ROOT / "templates" / "settings" / "settings.user.json"
PRE_F_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "settings.user.pre-F.json"

_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_settings_user_template", GENERATOR)
    if spec is None or spec.loader is None:  # pragma: no cover - import plumbing
        raise RuntimeError("cannot load %s" % GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = _load_generator()

#: Any member of the closed vocabulary; synthetic specs do not care WHICH.
_KLASS = GEN.EXCLUSION_CLASSES[0]


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _registrations(doc: Dict[str, Any]) -> List[Tuple[str, str]]:
    """``(event, identity)`` for every hook the document registers."""
    out: List[Tuple[str, str]] = []
    for event, groups in doc.get("hooks", {}).items():
        for group in groups:
            for entry in group.get("hooks", []):
                out.append((event, GEN.hook_basename(entry.get("command"))))
    return out


def _run(args: List[str], root: Optional[Path] = None) -> subprocess.CompletedProcess:
    argv = [sys.executable, str(GENERATOR)] + args
    if root is not None:
        argv += ["--repo-root", str(root)]
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _synth_root(tmp: Path, base: Dict[str, Any], user_text: Optional[str] = None) -> Path:
    root = tmp / "repo"
    (root / "templates" / "settings").mkdir(parents=True, exist_ok=True)
    (root / "templates" / "settings" / "settings.base.json").write_text(
        json.dumps(base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if user_text is not None:
        (root / "templates" / "settings" / "settings.user.json").write_text(
            user_text, encoding="utf-8")
    return root


def _minimal_spec(**over: Any) -> Dict[str, Any]:
    spec = {
        "source": "settings.base.json",
        "generator": ".claude/scripts/gen-settings-user-template.py",
        "criterion": "test fixture criterion",
        "top_level_exclude": [],
        "literals": {"_model_comment": "test fixture model comment"},
    }
    spec.update(over)
    return spec


def _hook(command: str, **fields: Any) -> Dict[str, Any]:
    entry = {"type": "command", "command": command}
    entry.update(fields)
    return entry


def _group(matcher: str, *entries: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    group: Dict[str, Any] = {}
    group.update(extra)
    group["matcher"] = matcher
    group["hooks"] = list(entries)
    return group


# ---------------------------------------------------------------------------
# (a) parity + idempotency
# ---------------------------------------------------------------------------

class ShippedTemplateMatchesItsDerivation(TestEnvContext):
    """The artifact on disk IS the generator's output. Bytes, not structure."""

    def test_check_mode_is_green_on_the_shipped_tree(self) -> None:
        proc = _run(["--check"], REPO_ROOT)
        self.assertEqual(
            proc.returncode, 0,
            "templates/settings/settings.user.json no longer matches the "
            "derivation declared in its own `_derivation` key.\n"
            "Remediation: python3 .claude/scripts/gen-settings-user-template.py --write\n"
            "%s" % proc.stderr,
        )

    def test_generated_bytes_equal_the_shipped_bytes(self) -> None:
        proc = _run(["--json"], REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            proc.stdout, USER_TEMPLATE.read_text(encoding="utf-8"),
            "the generator's output differs from the shipped template byte for "
            "byte — --check would be green on a structural comparison and the "
            "file would still be hand-edited",
        )

    def test_write_then_check_is_stable(self) -> None:
        """--write must be a fixed point: writing then checking is rc 0.

        Run against a COPY of the shipped pair, never the tree itself.
        """
        with tempfile.TemporaryDirectory() as td:
            root = _synth_root(Path(td), _read(BASE_TEMPLATE),
                               USER_TEMPLATE.read_text(encoding="utf-8"))
            first = _run(["--write"], root)
            self.assertEqual(first.returncode, 0, first.stderr)
            after_first = (root / "templates" / "settings" / "settings.user.json").read_bytes()
            second = _run(["--write"], root)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                (root / "templates" / "settings" / "settings.user.json").read_bytes(),
                after_first,
                "a second --write changed the file: the generator is not idempotent",
            )
            self.assertEqual(_run(["--check"], root).returncode, 0)

    def test_drift_is_named_with_a_runnable_remediation(self) -> None:
        """A hand-edit must produce rc 1, a diff, and the exact fix command."""
        with tempfile.TemporaryDirectory() as td:
            doc = _read(USER_TEMPLATE)
            doc["env"]["CEO_QUIET_MODE"] = "0"  # a hand-edit of a derived value
            root = _synth_root(Path(td), _read(BASE_TEMPLATE),
                               json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
            proc = _run(["--check"], root)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("DRIFT", proc.stderr)
            self.assertIn(
                "gen-settings-user-template.py --write", proc.stderr,
                "the drift message must name the command that fixes it",
            )
            self.assertIn("---", proc.stderr, "a unified diff must be emitted")

    def test_default_mode_is_check(self) -> None:
        self.assertEqual(_run([], REPO_ROOT).returncode, 0)


# ---------------------------------------------------------------------------
# (b) spec integrity
# ---------------------------------------------------------------------------

class ShippedSpecIsInternallyConsistent(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        self.base = _read(BASE_TEMPLATE)
        self.user = _read(USER_TEMPLATE)
        self.spec = self.user["_derivation"]

    def test_spec_validates_against_the_shipped_base(self) -> None:
        GEN.validate_spec(self.spec, self.base)  # raises SpecError on any defect

    def test_every_exclusion_names_a_live_base_registration(self) -> None:
        regs = GEN.base_registrations(self.base)
        names = set(n for _, n in regs)
        pairs = set(regs)
        for bucket in ("exclude_hooks", "exclude_hooks_pending"):
            for item in self.spec.get(bucket, []):
                if item.get("event"):
                    self.assertIn(
                        (item["event"], item["name"]), pairs,
                        "%s excludes %s under %s, which base does not register "
                        "— a dead exclusion" % (bucket, item["name"], item["event"]),
                    )
                else:
                    self.assertIn(
                        item["name"], names,
                        "%s excludes %s, which base does not register anywhere"
                        % (bucket, item["name"]),
                    )

    def test_decided_exclusions_carry_class_reason_and_evidence(self) -> None:
        for item in self.spec["exclude_hooks"]:
            self.assertIn(
                item.get("class"), GEN.EXCLUSION_CLASSES,
                "%s has class %r, outside the closed vocabulary"
                % (item.get("name"), item.get("class")),
            )
            for field in ("reason", "evidence"):
                self.assertTrue(
                    isinstance(item.get(field), str) and item[field].strip(),
                    "%s has an empty %s" % (item.get("name"), field),
                )

    def test_evidence_points_at_a_file_that_exists(self) -> None:
        """Evidence must RESOLVE. A pointer to a deleted hook is rot."""
        for item in self.spec["exclude_hooks"]:
            token = item["evidence"].split()[0]
            head = token.split(".py")[0] + ".py" if ".py" in token else token
            self.assertTrue(
                (REPO_ROOT / head).is_file(),
                "exclusion %s cites evidence at %r, which is not a file in the "
                "repo — update the spec when you move or delete a hook"
                % (item["name"], head),
            )
            self.assertEqual(
                head, ".claude/hooks/%s" % item["name"],
                "exclusion %s must cite the hook it excludes as its first "
                "evidence token" % item["name"],
            )

    def test_no_duplicate_exclusions(self) -> None:
        seen = []
        for bucket in ("exclude_hooks", "exclude_hooks_pending"):
            for item in self.spec.get(bucket, []):
                seen.append((item.get("event"), item["name"]))
        self.assertEqual(len(seen), len(set(seen)), "an exclusion is listed twice")

    def test_pending_entries_point_at_an_open_question(self) -> None:
        pending = self.spec.get("exclude_hooks_pending", [])
        if not pending:
            self.skipTest("no pending exclusions left — OQ-E5 has been resolved")
        self.assertTrue(self.spec.get("pending_note", "").strip())
        for item in pending:
            self.assertEqual(item.get("class"), GEN.PENDING_CLASS)
            self.assertTrue(item.get("oq", "").strip(),
                            "%s does not name the question that decides it" % item["name"])

    def test_provisional_flag_agrees_with_the_pending_bucket(self) -> None:
        pending = bool(self.spec.get("exclude_hooks_pending"))
        self.assertEqual(
            bool(self.spec.get("provisional")), pending,
            "`provisional` must be true exactly while entries are still "
            "awaiting a ruling (pending=%s)" % pending,
        )

    def test_the_two_buckets_cover_every_base_only_registration(self) -> None:
        """Nothing in base is dropped WITHOUT being declared.

        This is the property the frozen copy lacked: 17 registrations were
        absent from it and nothing said so.
        """
        base_regs = set(GEN.base_registrations(self.base))
        user_regs = set(_registrations(self.user))
        pairs, names = GEN.exclusion_sets(self.spec)
        undeclared = sorted(
            r for r in (base_regs - user_regs)
            if r not in pairs and r[1] not in names
        )
        self.assertEqual(
            undeclared, [],
            "these base registrations are missing from the user template with "
            "no entry in exclude_hooks or exclude_hooks_pending: %s" % undeclared,
        )

    def test_every_base_top_level_key_is_carried_or_named(self) -> None:
        """No top-level key leaves base silently — the §3 leak concern.

        The S330 classification warned that a subtraction-shaped generator
        leaks ``permissions`` / ``availableModels`` into the advisory profile.
        The cure is not a literal keep list (same rot class); it is: whatever
        base has is either in the output or NAMED in ``top_level_exclude``.
        """
        excluded = set(i["name"] for i in self.spec.get("top_level_exclude", []))
        for key in self.base:
            if key in GEN.TOP_LEVEL_COMPUTED:
                continue
            self.assertTrue(
                key in self.user or key in excluded,
                "base top-level key %r is neither in the user template nor "
                "named in top_level_exclude" % key,
            )

    def test_the_enforcing_model_keys_never_reach_the_advisory_profile(self) -> None:
        """Belt to test_template_dogfood_parity's braces, stated as intent."""
        for key in ("availableModels", "enforceAvailableModels", "fallbackModel",
                    "permissions"):
            self.assertNotIn(
                key, self.user,
                "%s leaked into the advisory user template — it would change "
                "the profile's nature (and redden "
                "test_template_dogfood_parity.py / test-install-deny-baseline.sh)"
                % key,
            )

    def test_the_criterion_is_stated(self) -> None:
        self.assertTrue(self.spec.get("criterion", "").strip())
        self.assertIn(
            "_derivation.criterion", self.user["_comment"],
            "the generated _comment must point at the criterion instead of "
            "restating it (a second copy of a rule is a rule that rots)",
        )

    def test_the_generated_comment_states_no_count(self) -> None:
        """The rotted claim was a NUMBER in prose. Keep numbers out."""
        import re
        for text in (self.user["_comment"], GEN.GENERATED_COMMENT):
            self.assertIsNone(
                re.search(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b"
                          r"[ ]+(?:governance|hook|registration|entr)", text, re.I),
                "the generated _comment counts something in prose — that claim "
                "is watched by nothing and is exactly what rotted: %r" % text[:120],
            )


# ---------------------------------------------------------------------------
# (c) RED CONTROL — the frozen pre-F copy against its own claim
# ---------------------------------------------------------------------------

class FrozenCopyFailsItsOwnClaim(TestEnvContext):
    """The pre-F fixture vs a spec that removes "exactly the 10".

    The fixture is ``git show 1c34eb5:templates/settings/settings.user.json``
    — the hand-frozen artifact as it shipped. Its ``_comment`` claimed the
    derivation was "REMOVING exactly the 10 governance/sentinel/kernel hooks"
    and that retained entries were byte-identical to base in matcher, command
    and timeout. This test takes that claim literally, hands it to the
    generator, and shows the frozen file is NOT what the claim produces.

    That is the whole justification for the wave, so it is a test and not a
    paragraph in a plan.
    """

    #: The ten names the frozen ``_comment`` itself listed. A literal on
    #: purpose: it is a QUOTATION of a historical artifact, not a roster this
    #: file maintains. It must not be "kept in sync" with anything — if the
    #: shipped spec drifts from it, that is the wave working.
    CLAIMED_TEN = (
        "check_plan_edit.py", "check_arbitration_kernel.py", "check_tier_policy.py",
        "check_canonical_edit.py", "check_protocol_semver_cascade.py",
        "check_skill_patch_sentinel.py", "check_scratchpad_access.py",
        "check_skill_reference_read.py", "check_skill_bootstrap_post.py",
        "check_bash_canonical_forensic.py",
    )

    #: Registrations the frozen copy lacked once the claim is applied.
    #: Declared with its source (S330 census, hook-classification-S330.md §0
    #: and §1.1: 26 base-only basenames = 10 claimed + 16 never received, plus
    #: the second check_output_secrets registration). Updated CONSCIOUSLY, and
    #: never relaxed.
    EXPECTED_MISSING = 17

    def setUp(self) -> None:
        super().setUp()
        self.base = _read(BASE_TEMPLATE)
        self.fixture = _read(PRE_F_FIXTURE)
        # The claim, spelled as a spec: the ten hooks the frozen _comment
        # named, and NO overrides (it said retained entries were
        # byte-identical in matcher/command/timeout).
        self.claim = _minimal_spec(exclude_hooks=[
            {"name": n, "class": GEN.EXCLUSION_CLASSES[0],
             "reason": "as claimed by the frozen _comment",
             "evidence": ".claude/hooks/%s" % n}
            for n in self.CLAIMED_TEN
        ])

    def test_the_fixture_is_the_pre_wave_artifact(self) -> None:
        self.assertNotIn("_derivation", self.fixture,
                         "the fixture must be the PRE-wave copy, un-derived")
        self.assertEqual(len(_registrations(self.fixture)), 20)

    def test_the_claim_does_not_reproduce_the_frozen_file(self) -> None:
        produced = GEN.generate(self.base, self.claim)
        self.assertNotEqual(
            _registrations(produced), _registrations(self.fixture),
            "removing exactly the ten declared hooks reproduced the frozen "
            "file — then the frozen _comment was true and this wave has no "
            "reason to exist",
        )

    def test_the_failure_names_the_registrations_the_frozen_copy_lacked(self) -> None:
        produced = GEN.generate(self.base, self.claim)
        missing = sorted(set(_registrations(produced)) - set(_registrations(self.fixture)))
        self.assertTrue(missing, "expected registrations absent from the frozen copy")
        report = ", ".join("%s %s" % (e, n) for e, n in missing)
        # Anchors: one hook the base gained after the freeze, and the second
        # registration of a hook the copy kept only once.
        self.assertIn(
            "PreToolUse check_ledger_checkpoint.py", report,
            "the anchor hook is missing from the divergence report: %s" % report,
        )
        self.assertIn(
            "PostToolUseFailure check_output_secrets.py", report,
            "the dual-registration anchor is missing from the report: %s" % report,
        )
        self.assertEqual(
            len(missing), self.EXPECTED_MISSING,
            "the S330 census counted %d registrations absent from the frozen "
            "copy under its own claim; found %d: %s"
            % (self.EXPECTED_MISSING, len(missing), report),
        )

    def test_the_failure_names_the_hand_edited_fields(self) -> None:
        """The claim said matcher/command/timeout were byte-identical."""
        produced = GEN.generate(self.base, self.claim)

        def index(doc: Dict[str, Any]) -> Dict[Tuple[str, str], Tuple[Dict, Dict]]:
            out = {}
            for event, groups in doc["hooks"].items():
                for group in groups:
                    for entry in group["hooks"]:
                        out[(event, GEN.hook_basename(entry["command"]))] = (group, entry)
            return out

        pi, fi = index(produced), index(self.fixture)
        divergent = []
        for key in sorted(set(pi) & set(fi)):
            pg, pe = pi[key]
            fg, fe = fi[key]
            if pg.get("matcher") != fg.get("matcher"):
                divergent.append("%s %s: matcher" % key)
            for field in sorted(set(pe) | set(fe)):
                if pe.get(field) != fe.get(field):
                    divergent.append("%s %s: %s" % (key[0], key[1], field))
        report = "; ".join(divergent)
        self.assertIn(
            "PreToolUse check_anti_ceo_overhead.py: matcher", report,
            "the hand-narrowed matcher is not reported: %s" % report,
        )
        self.assertIn(
            "PreToolUse check_config_protection.py: statusMessage", report,
            "the hand-edited statusMessage is not reported: %s" % report,
        )
        self.assertEqual(
            len(divergent), 2,
            "expected exactly the two behavioural/entry-field divergences the "
            "S330 census measured, found: %s" % report,
        )

    #: What the S330 classification ruled INTO the advisory profile
    #: (hook-classification-S330.md §1.1 "INCLUIR-NO-USER" + §1.2 + the one
    #: INCLUIR-COM-ENV). Declared with its source; changing the ruling means
    #: changing this list CONSCIOUSLY, in the same patch as the spec.
    #: Owner ruling 2026-08-30 (rail-round-7 P2-a; spec exclude_hooks +
    #: classification addendum): check_scratchpad_access.py was ruled back
    #: OUT — its suffix matcher would block an adopter's homonymous
    #: script with no practicable route.
    RULED_IN = (
        ("ConfigChange", "check_config_change.py"),
        ("PostToolUse", "accel_dispatch.py"),
        ("PostToolUse", "check_skill_reference_read.py"),
        ("PostToolUseFailure", "check_output_secrets.py"),
        ("SessionStart", "turbo_sessionstart.py"),
        ("Setup", "check_setup_verification.py"),
        ("Stop", "codex_review_user_code.py"),
        ("Stop", "review_loop.py"),
        ("SubagentStart", "check_subagent_start.py"),
    )

    def test_the_shipped_roster_loses_nothing_the_frozen_copy_had(self) -> None:
        """The one direction that would be a REGRESSION for an adopter.

        wave-F adds registrations by ruling; it must never silently drop one
        the advisory profile already had.
        """
        shipped = set(_registrations(_read(USER_TEMPLATE)))
        lost = sorted(set(_registrations(self.fixture)) - shipped)
        self.assertEqual(
            lost, [],
            "the derived template DROPPED registration(s) the frozen copy "
            "shipped: %s — wave-F rules hooks IN, it does not remove them" % lost,
        )

    def test_what_the_shipped_roster_gained_is_exactly_what_was_ruled_in(self) -> None:
        shipped = set(_registrations(_read(USER_TEMPLATE)))
        gained = sorted(shipped - set(_registrations(self.fixture)))
        self.assertEqual(
            gained, sorted(self.RULED_IN),
            "the roster gained something the S330 classification did not rule "
            "in (or missed something it did). Expected %s, got %s"
            % (sorted(self.RULED_IN), gained),
        )

    def test_the_env_the_frozen_copy_declared_survives(self) -> None:
        shipped = _read(USER_TEMPLATE)
        for key, value in self.fixture["env"].items():
            self.assertEqual(
                shipped["env"].get(key), value,
                "env key %s changed or vanished — the advisory switch the "
                "profile depends on must survive the derivation" % key,
            )
        self.assertEqual(shipped["model"], self.fixture["model"])


# ---------------------------------------------------------------------------
# (d)(e)(f)(g) mechanism, on synthetic bases
# ---------------------------------------------------------------------------

class DerivationMechanics(TestEnvContext):

    def test_a_new_unexcluded_base_hook_appears_and_reddens_check(self) -> None:
        """(d) base grows a hook nobody excluded -> the shipped file is stale."""
        base = _read(BASE_TEMPLATE)
        base["hooks"]["PreToolUse"].append(
            _group("Edit", _hook('"$CLAUDE_PROJECT_DIR/.claude/hooks/check_brand_new.py"')))
        with tempfile.TemporaryDirectory() as td:
            root = _synth_root(Path(td), base, USER_TEMPLATE.read_text(encoding="utf-8"))
            proc = _run(["--check"], root)
            self.assertEqual(
                proc.returncode, 1,
                "a hook added to the base template with no exclusion left the "
                "derived template green — the generator is not watching base",
            )
            self.assertIn("check_brand_new.py", proc.stderr)

    def test_model_is_copied_from_base(self) -> None:
        """(e) one pin, one source."""
        base = _read(BASE_TEMPLATE)
        user = _read(USER_TEMPLATE)
        self.assertEqual(user["model"], base["model"])
        base["model"] = "claude-sonnet-5"
        spec = copy.deepcopy(user["_derivation"])
        self.assertEqual(GEN.generate(base, spec)["model"], "claude-sonnet-5",
                         "the pin must follow the base template, not a second literal")

    def test_dual_registration_is_addressable_per_event(self) -> None:
        """(f) a basename under two events: keep both, or drop exactly one."""
        base = {
            "hooks": {
                "PostToolUse": [_group("Write", _hook("python3 .claude/hooks/dual.py"))],
                "PostToolUseFailure": [_group("Write", _hook("python3 .claude/hooks/dual.py"))],
            },
            "env": {},
        }
        keep_both = GEN.generate(base, _minimal_spec())
        self.assertEqual(
            sorted(_registrations(keep_both)),
            [("PostToolUse", "dual.py"), ("PostToolUseFailure", "dual.py")],
            "an unexcluded basename registered under two events must survive twice",
        )

        scoped = _minimal_spec(exclude_hooks=[{
            "name": "dual.py", "event": "PostToolUseFailure",
            "class": _KLASS,
            "reason": "r", "evidence": "e",
        }])
        GEN.validate_spec(scoped, base)
        self.assertEqual(
            _registrations(GEN.generate(base, scoped)), [("PostToolUse", "dual.py")],
            "an event-scoped exclusion must drop ONLY that registration",
        )

        broad = _minimal_spec(exclude_hooks=[{
            "name": "dual.py", "class": _KLASS,
            "reason": "r", "evidence": "e",
        }])
        GEN.validate_spec(broad, base)
        self.assertEqual(
            _registrations(GEN.generate(base, broad)), [],
            "an exclusion with no event must drop every registration of the name",
        )

    def test_the_shipped_template_tracks_the_spec_for_the_dual_hook(self) -> None:
        """The real corpus case, asserted against the SPEC, not a literal.

        ``check_output_secrets.py`` is registered twice in base and once in
        the frozen copy. Whether the second registration comes back is
        OQ-E5's to decide, so this asserts the template agrees with whatever
        the spec currently says — and moves with it.
        """
        base, user = _read(BASE_TEMPLATE), _read(USER_TEMPLATE)
        pairs, names = GEN.exclusion_sets(user["_derivation"])
        shipped = set(_registrations(user))
        for event, name in GEN.base_registrations(base):
            if name != "check_output_secrets.py":
                continue
            excluded = (event, name) in pairs or name in names
            self.assertEqual(
                (event, name) not in shipped, excluded,
                "%s under %s: shipped=%s but spec says excluded=%s"
                % (name, event, (event, name) in shipped, excluded),
            )

    def test_an_event_emptied_by_subtraction_disappears(self) -> None:
        """(g) no empty event arrays — an empty array is a false claim."""
        base = {
            "hooks": {
                "PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/keep.py"))],
                "PreCompact": [_group("*", _hook("python3 .claude/hooks/gone.py"))],
            },
            "env": {},
        }
        spec = _minimal_spec(exclude_hooks=[{
            "name": "gone.py", "class": _KLASS,
            "reason": "r", "evidence": "e",
        }])
        out = GEN.generate(base, spec)
        self.assertNotIn("PreCompact", out["hooks"],
                         "an event left with no blocks must be REMOVED, not emitted empty")
        self.assertIn("PreToolUse", out["hooks"])

    def test_a_partly_emptied_block_keeps_its_survivors(self) -> None:
        base = {
            "hooks": {"PreToolUse": [_group(
                "Edit",
                _hook("python3 .claude/hooks/gone.py"),
                _hook("python3 .claude/hooks/keep.py"),
            )]},
            "env": {},
        }
        spec = _minimal_spec(exclude_hooks=[{
            "name": "gone.py", "class": _KLASS,
            "reason": "r", "evidence": "e",
        }])
        out = GEN.generate(base, spec)
        self.assertEqual(_registrations(out), [("PreToolUse", "keep.py")])

    def test_retained_entries_are_byte_identical_to_base(self) -> None:
        """Only a DECLARED override may change a retained entry."""
        base, user = _read(BASE_TEMPLATE), _read(USER_TEMPLATE)
        spec = user["_derivation"]
        declared = set(spec.get("matcher_overrides", {})) | set(spec.get("annotation_overrides", {}))

        def index(doc):
            out = {}
            for event, groups in doc["hooks"].items():
                for group in groups:
                    for entry in group["hooks"]:
                        out[(event, GEN.hook_basename(entry["command"]))] = (group, entry)
            return out

        bi, ui = index(base), index(user)
        for key in sorted(set(bi) & set(ui)):
            if "%s/%s" % key in declared or key[1] in declared:
                continue
            bg, be = bi[key]
            ug, ue = ui[key]
            self.assertEqual(ue, be, "%s %s: hook entry drifted from base with no "
                                     "declared override" % key)
            self.assertEqual(
                {k: v for k, v in ug.items() if k != "hooks"},
                {k: v for k, v in bg.items() if k != "hooks"},
                "%s %s: block metadata drifted from base with no declared override" % key,
            )

    def test_env_is_base_minus_exclusions_plus_overrides(self) -> None:
        base, user = _read(BASE_TEMPLATE), _read(USER_TEMPLATE)
        spec = user["_derivation"]
        expected = {k: v for k, v in base["env"].items() if k not in spec.get("env_exclude", [])}
        expected.update(spec.get("env_overrides", {}))
        self.assertEqual(user["env"], expected)

    def test_every_registered_hook_has_a_file_install_will_copy(self) -> None:
        """A registration pointing at a missing file breaks the adopter.

        This became load-bearing in wave-F: the user roster grew by ten, so
        for the first time the advisory profile registers hooks that were
        previously only ever copied, never wired.
        ``install_hooks_selective`` (scripts/install.sh:1413) copies every
        top-level ``.claude/hooks/*.py`` with NO ceremony branch, so the file
        existing in the repo is exactly the condition for it reaching the
        adopter.
        """
        missing = []
        for event, name in _registrations(_read(USER_TEMPLATE)):
            if name.startswith("inline:"):
                continue
            if not (REPO_ROOT / ".claude" / "hooks" / name).is_file():
                missing.append("%s %s" % (event, name))
        self.assertEqual(
            missing, [],
            "the user template registers hook(s) with no file in "
            ".claude/hooks/, so a --ceremony user adopter would get a "
            "registration pointing at nothing: %s" % missing,
        )

    def test_an_inline_hook_keeps_a_stable_identity(self) -> None:
        """The base template registers an inline `echo` with no .py at all.

        Measured S330. It must be addressable (so it can be excluded) and it
        must survive when it is not.
        """
        base, user = _read(BASE_TEMPLATE), _read(USER_TEMPLATE)
        inline = [(e, n) for e, n in GEN.base_registrations(base) if n.startswith("inline:")]
        self.assertTrue(inline, "no inline hook in base — update this test's premise")
        for reg in inline:
            self.assertIn(reg, _registrations(user),
                          "the inline registration %s was dropped without a declared "
                          "exclusion" % (reg,))
        first = GEN.hook_basename("echo hello")
        self.assertEqual(first, GEN.hook_basename("echo hello"), "identity must be stable")
        self.assertNotEqual(first, GEN.hook_basename("echo goodbye"),
                            "different inline commands must not share an identity")


# ---------------------------------------------------------------------------
# spec integrity — the fail-closed arms
# ---------------------------------------------------------------------------

class SpecIntegrityIsFailClosed(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        self.base = {
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
            "env": {"K": "1"},
            "model": "m",
        }

    def _rejects(self, spec: Dict[str, Any], fragment: str) -> None:
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(spec, self.base)
        self.assertIn(fragment, str(ctx.exception))

    def test_dead_exclusion_is_rejected(self) -> None:
        self._rejects(_minimal_spec(exclude_hooks=[{
            "name": "nope.py", "class": _KLASS,
            "reason": "r", "evidence": "e"}]), "dead exclusion")

    def test_dead_exclusion_by_event_is_rejected(self) -> None:
        self._rejects(_minimal_spec(exclude_hooks=[{
            "name": "a.py", "event": "SessionEnd", "class": _KLASS,
            "reason": "r", "evidence": "e"}]), "dead exclusion")

    def test_unknown_class_is_rejected(self) -> None:
        self._rejects(_minimal_spec(exclude_hooks=[{
            "name": "a.py", "class": "because-i-said-so",
            "reason": "r", "evidence": "e"}]), "closed vocabulary")

    def test_empty_reason_is_rejected(self) -> None:
        self._rejects(_minimal_spec(exclude_hooks=[{
            "name": "a.py", "class": _KLASS,
            "reason": "  ", "evidence": "e"}]), "empty `reason`")

    def test_duplicate_exclusion_is_rejected(self) -> None:
        item = {"name": "a.py", "class": _KLASS, "reason": "r", "evidence": "e"}
        self._rejects(_minimal_spec(exclude_hooks=[item, dict(item)]), "duplicate exclusion")

    def test_pending_without_open_question_is_rejected(self) -> None:
        self._rejects(_minimal_spec(
            pending_note="n",
            exclude_hooks_pending=[{"name": "a.py", "class": GEN.PENDING_CLASS}],
        ), "`oq`")

    def test_pending_without_a_note_is_rejected(self) -> None:
        self._rejects(_minimal_spec(exclude_hooks_pending=[
            {"name": "a.py", "class": GEN.PENDING_CLASS, "oq": "OQ-E5"}]), "pending_note")

    def test_dead_override_is_rejected(self) -> None:
        self._rejects(_minimal_spec(matcher_overrides={"nope.py": "X"}), "dead override")

    def test_override_of_an_excluded_hook_is_rejected(self) -> None:
        self._rejects(_minimal_spec(
            exclude_hooks=[{"name": "a.py", "class": _KLASS,
                            "reason": "r", "evidence": "e"}],
            matcher_overrides={"a.py": "X"},
        ), "EXCLUDED")

    def test_ambiguous_override_key_is_rejected(self) -> None:
        base = {
            "hooks": {
                "PostToolUse": [_group("W", _hook("python3 .claude/hooks/d.py"))],
                "PostToolUseFailure": [_group("W", _hook("python3 .claude/hooks/d.py"))],
            },
            "env": {},
        }
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(_minimal_spec(matcher_overrides={"d.py": "X"}), base)
        self.assertIn("ambiguous", str(ctx.exception))

    def test_annotation_override_cannot_change_the_command(self) -> None:
        self._rejects(_minimal_spec(
            annotation_overrides={"a.py": {"hook": {"command": "rm -rf /"}}},
        ), "may not override")

    def test_dead_env_exclusion_is_rejected(self) -> None:
        self._rejects(_minimal_spec(env_exclude=["NOT_IN_BASE"]), "dead exclusion")

    def test_env_key_in_both_buckets_is_rejected(self) -> None:
        self._rejects(_minimal_spec(env_exclude=["K"], env_overrides={"K": "2"}), "does not say")

    def test_a_keep_list_is_rejected_outright(self) -> None:
        """The shape the S330 classification rejected must not come back."""
        self._rejects(_minimal_spec(top_level_keep=["hooks", "env"]),
                      "was replaced by `top_level_exclude`")

    def test_dead_top_level_exclusion_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(top_level_exclude=[{"name": "nope", "reason": "r"}]),
            "dead exclusion")

    def test_top_level_exclusion_without_reason_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(top_level_exclude=[{"name": "model", "reason": " "}]),
            "empty `reason`")

    def test_excluding_a_generator_sourced_key_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(top_level_exclude=[{"name": "hooks", "reason": "r"}]),
            "sources itself")

    def test_missing_criterion_is_rejected(self) -> None:
        spec = _minimal_spec()
        del spec["criterion"]
        self._rejects(spec, "criterion")

    def test_wrong_source_is_rejected(self) -> None:
        self._rejects(_minimal_spec(source="settings.stack.node.json"), "`source` must be")

    def test_a_hook_entry_without_a_command_is_refused(self) -> None:
        base = {"hooks": {"PreToolUse": [_group("Edit", {"type": "command"})]}, "env": {}}
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(_minimal_spec(), base)
        self.assertIn("cannot identify it", str(ctx.exception))

    def test_missing_user_template_is_infrastructure_not_drift(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = _synth_root(Path(td), _read(BASE_TEMPLATE))
            proc = _run(["--check"], root)
            self.assertEqual(proc.returncode, 2,
                             "an absent artifact is INFRA (rc 2), never drift (rc 1)")
            self.assertIn("INFRA", proc.stderr)

    def test_a_spec_defect_exits_one_and_names_the_key(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            doc = _read(USER_TEMPLATE)
            doc["_derivation"]["exclude_hooks"].append(
                {"name": "ghost.py", "class": _KLASS,
                 "reason": "r", "evidence": "e"})
            root = _synth_root(Path(td), _read(BASE_TEMPLATE),
                               json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
            proc = _run(["--check"], root)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("SPEC:", proc.stderr)
            self.assertIn("_derivation", proc.stderr)


# ---------------------------------------------------------------------------
# pair-rail round 1 — a declaration the generator would silently ignore
# ---------------------------------------------------------------------------

class DeclaredOverridesAreAppliedOrRejected(TestEnvContext):
    """An override the derivation cannot apply must be REFUSED, never dropped.

    Round 1 of the pair-rail found two ways the spec could claim an exception
    that no byte of output reflected — the exact class this generator exists to
    remove, reappearing inside the cure:

    * a `matcher` or a group `_comment` is a property of the BLOCK, but
      ``derive_hooks`` only writes it when the block narrows to ONE retained
      entry. The validator's ambiguity check counts registrations matching the
      NAME across events, which is a different question, so a legitimately
      qualified key targeting a two-entry block passed validation and was then
      dropped in silence.
    * ``annotation_overrides`` accepted an entry with no ``reason`` — against
      the contract DESIGN-F §3 states — and an entry carrying ONLY a reason,
      which changes nothing at all.

    Both are now fail-CLOSED and named. The positive control matters as much as
    the red one: when the block DOES narrow to one entry the override is
    accepted **and applied**, so this is a discriminating guard rather than a
    blanket refusal.
    """

    def setUp(self) -> None:
        super().setUp()
        # A block with TWO entries — the shape the derivation cannot attribute
        # a block-level property to.
        self.two = {
            "hooks": {"PreToolUse": [_group(
                "Edit",
                _hook("python3 .claude/hooks/a.py"),
                _hook("python3 .claude/hooks/b.py"),
            )]},
            "env": {"K": "1"},
            "model": "m",
        }

    def _rejects(self, spec: Dict[str, Any], fragment: str,
                 base: Optional[Dict[str, Any]] = None) -> None:
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(spec, base if base is not None else self.two)
        self.assertIn(fragment, str(ctx.exception))

    # -- P2-1: block-scope overrides --------------------------------------

    def test_matcher_override_on_a_multi_entry_block_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(matcher_overrides={"PreToolUse/a.py": {
                "matcher": "Edit|Write", "reason": "r", "evidence": "e"}}),
            "keeps 2 entries")

    def test_group_comment_override_on_a_multi_entry_block_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(annotation_overrides={"PreToolUse/a.py": {
                "_comment": "note", "reason": "r"}}),
            "keeps 2 entries")

    def test_a_per_entry_annotation_survives_a_multi_entry_block(self) -> None:
        """`hook` fields ARE applied per entry — they must stay allowed.

        Rejecting these too would be the over-correction: the derivation writes
        them regardless of how many entries the block keeps.
        """
        # `statusMessage`, not `timeout`: round 3 closed the annotation
        # vocabulary, and `timeout` is behaviour. The property under test is
        # unchanged — a PER-ENTRY annotation is applied regardless of how many
        # entries the block keeps.
        spec = _minimal_spec(annotation_overrides={"PreToolUse/a.py": {
            "hook": {"statusMessage": "Checking..."}, "reason": "r"}})
        GEN.validate_spec(spec, self.two)          # must not raise
        out = GEN.derive_hooks(self.two, spec)
        applied = [e for e in out["PreToolUse"][0]["hooks"]
                   if GEN.hook_basename(e["command"]) == "a.py"]
        self.assertEqual(applied[0]["statusMessage"], "Checking...",
                         "the per-entry annotation was accepted but not applied")

    def test_the_override_is_accepted_AND_applied_when_the_block_narrows(self) -> None:
        """Positive control: excluding the sibling makes the override real."""
        spec = _minimal_spec(
            exclude_hooks=[{"name": "b.py", "class": _KLASS,
                            "reason": "r", "evidence": "e"}],
            matcher_overrides={"PreToolUse/a.py": {
                "matcher": "Edit|Write", "reason": "r", "evidence": "e"}},
        )
        GEN.validate_spec(spec, self.two)          # must not raise
        out = GEN.derive_hooks(self.two, spec)
        self.assertEqual(
            out["PreToolUse"][0]["matcher"], "Edit|Write",
            "the matcher override validated but was not written — this is the "
            "silent drop the guard exists to prevent, now on the other side")

    # -- P2-2: an exception carries its justification ----------------------

    def test_annotation_override_without_a_reason_is_rejected(self) -> None:
        base = {
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
            "env": {"K": "1"}, "model": "m",
        }
        self._rejects(
            _minimal_spec(annotation_overrides={"a.py": {"_comment": "note"}}),
            "no `reason`", base=base)

    def test_annotation_override_that_changes_nothing_is_rejected(self) -> None:
        base = {
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
            "env": {"K": "1"}, "model": "m",
        }
        self._rejects(
            _minimal_spec(annotation_overrides={"a.py": {"reason": "r"}}),
            "changes nothing", base=base)

    def test_a_documented_override_that_changes_something_is_accepted(self) -> None:
        base = {
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
            "env": {"K": "1"}, "model": "m",
        }
        spec = _minimal_spec(annotation_overrides={"a.py": {
            "_comment": "note", "reason": "r"}})
        GEN.validate_spec(spec, base)              # must not raise
        out = GEN.derive_hooks(base, spec)
        self.assertEqual(out["PreToolUse"][0]["_comment"], "note")


# ---------------------------------------------------------------------------
# pair-rail round 2 — selectors, anchors, and the rule matching its own list
# ---------------------------------------------------------------------------

class SelectorsAndAnchorsAreFailClosed(TestEnvContext):
    """Two more ways a declaration could be accepted and then ignored.

    * `derive_hooks` resolves an override by preferring `Event/name` over the
      bare `name`. A spec declaring BOTH had its bare entry applied never and
      refused never — each passed validation on its own, and the defect lived
      only in their relation.
    * The generated fields ride on anchors from the base (`_derivation` after
      `_comment`, `_model_comment` before `model`). Excluding an anchor — or a
      future base dropping one — took the generated field with it. Losing
      `_derivation` is unrecoverable in the normal path: the artifact stops
      carrying its own spec and the next `--check` exits 2.
    """

    def setUp(self) -> None:
        super().setUp()
        self.base = {
            "_comment": "c",
            "model": "m",
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
            "env": {"K": "1"},
        }

    def _rejects(self, spec: Dict[str, Any], fragment: str) -> None:
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(spec, self.base)
        self.assertIn(fragment, str(ctx.exception))

    def test_bare_and_qualified_selectors_together_are_rejected(self) -> None:
        self._rejects(_minimal_spec(matcher_overrides={
            "a.py": {"matcher": "X", "reason": "r", "evidence": "e"},
            "PreToolUse/a.py": {"matcher": "Y", "reason": "r", "evidence": "e"},
        }), "declares BOTH")

    def test_a_single_qualified_selector_is_fine(self) -> None:
        GEN.validate_spec(_minimal_spec(matcher_overrides={
            "PreToolUse/a.py": {"matcher": "Y", "reason": "r", "evidence": "e"},
        }), self.base)

    def test_excluding_the_derivation_anchor_is_rejected(self) -> None:
        """Refused — but by the OLDER layer, and the distinction is worth a line.

        `_comment` is generator-sourced, so `top_level_exclude` already refused
        it before this wave; the anchor check never sees the case. Measured, not
        assumed: the message that comes back is the generator-sourced one. The
        anchor check earns its place on the OTHER anchor (`model`), which is a
        plain base key nothing else protects — see the test below.
        """
        self._rejects(
            _minimal_spec(top_level_exclude=[{"name": "_comment", "reason": "r"}]),
            "the generator sources itself")

    def test_excluding_the_model_comment_anchor_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(top_level_exclude=[{"name": "model", "reason": "r"}]),
            "drops the generated field")

    def test_a_missing_anchor_still_emits_the_generated_field(self) -> None:
        """Position is negotiable; presence is not.

        The first shape of this cure REJECTED a base without the anchor, which
        turned every synthetic base in this file into an error while doing
        nothing for the real risk. Refusing less and losing nothing is the
        better answer: the field is appended instead of dropped.
        """
        base = dict(self.base)
        del base["_comment"]
        GEN.validate_spec(_minimal_spec(), base)      # must not raise
        out = GEN.generate(base, _minimal_spec())
        self.assertIn("_derivation", out,
                      "the artifact would ship unable to read its own spec")
        self.assertIn("_model_comment", out)


class BlockingInclusionsCarryTheirRoute(TestEnvContext):
    """A hook the profile KEEPS that can still block must name its route.

    The reviewer read the shipped criterion as a biconditional and found
    `check_scratchpad_access.py` violating it. The census that followed found
    the criterion was never a description of the PROFILE — ten of the kept
    hooks block, most of them since v1.0.0 — but also that FIVE of the nine
    hooks the census ruled in could block, not one. Naming a single exception
    would have reproduced the defect at a smaller scale. The Owner's r7
    ruling later took the scratchpad guard back out (suffix matcher, no
    route for an adopter's homonymous script), so the wave ships four
    blocking hooks among the eight it adds.

    So the criterion states its scope, and `blocking_inclusions` names every
    blocking hook the wave adds together with the adopter's actual route. The
    completeness test below is the one that matters: it re-derives the set from
    the OLD roster and the hook sources, so the next blocking addition cannot
    ship undeclared.
    """

    #: Sites that mean "this hook can refuse a call".
    _BLOCK_PATTERNS = (
        r'"decision"\s*:\s*"block"',
        r'\ballow\s*=\s*False',
    )

    def setUp(self) -> None:
        super().setUp()
        self.base = {
            "_comment": "c",
            "model": "m",
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
            "env": {"K": "1"},
        }

    def _rejects(self, entries: List[Dict[str, Any]], fragment: str) -> None:
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(_minimal_spec(blocking_inclusions=entries), self.base)
        self.assertIn(fragment, str(ctx.exception))

    # -- shape ------------------------------------------------------------

    def test_entry_without_a_route_is_rejected(self) -> None:
        self._rejects([{"hook": "a.py", "evidence": "e"}], "empty `route`")

    def test_entry_without_evidence_is_rejected(self) -> None:
        self._rejects([{"hook": "a.py", "route": "r"}], "empty `evidence`")

    def test_dead_entry_is_rejected(self) -> None:
        self._rejects([{"hook": "ghost.py", "route": "r", "evidence": "e"}],
                      "dead declaration")

    def test_duplicate_entry_is_rejected(self) -> None:
        item = {"hook": "a.py", "route": "r", "evidence": "e"}
        self._rejects([item, dict(item)], "twice")

    def test_entry_for_an_excluded_hook_is_rejected(self) -> None:
        """An excluded hook needs no route — declaring one is a dead claim."""
        spec = _minimal_spec(
            exclude_hooks=[{"name": "a.py", "class": _KLASS,
                            "reason": "r", "evidence": "e"}],
            blocking_inclusions=[{"hook": "a.py", "route": "r", "evidence": "e"}],
        )
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(spec, self.base)
        self.assertIn("ALL", str(ctx.exception))

    def test_a_documented_entry_is_accepted(self) -> None:
        GEN.validate_spec(_minimal_spec(blocking_inclusions=[
            {"hook": "a.py", "route": "run it without --plan",
             "evidence": "hooks/a.py:1"}]), self.base)

    # -- completeness, against the shipped artifact ------------------------

    def _blocking_sites(self, name: str) -> bool:
        path = REPO_ROOT / ".claude" / "hooks" / name
        if not path.is_file():
            return False
        text = path.read_text(encoding="utf-8", errors="replace")
        return any(re.search(p, text) for p in self._BLOCK_PATTERNS)

    def test_every_blocking_hook_this_wave_adds_is_declared(self) -> None:
        """Re-derived, never recalled: OLD roster vs NEW, then read the sources.

        This is the guard that survives the wave. A future spec change that
        keeps one more blocking hook turns this red with the name in the
        message, instead of shipping an undeclared refusal to adopters.
        """
        new_doc = _read(USER_TEMPLATE)
        old_path = (REPO_ROOT / ".claude" / "scripts" / "tests" / "fixtures"
                    / "settings.user.pre-F.json")
        if not old_path.is_file():
            self.skipTest("frozen pre-F roster not present in this tree")
        old_doc = _read(old_path)
        added = ({n for _e, n in _registrations(new_doc)}
                 - {n for _e, n in _registrations(old_doc)})
        should_declare = sorted(n for n in added if self._blocking_sites(n))
        declared = sorted(
            item["hook"] for item in
            new_doc["_derivation"].get("blocking_inclusions", []))
        self.assertEqual(
            declared, should_declare,
            "the declared blocking inclusions do not match what the sources "
            "say.\n  undeclared (add them, with the adopter's route): %s\n"
            "  declared but no longer blocking (drop them): %s"
            % (sorted(set(should_declare) - set(declared)),
               sorted(set(declared) - set(should_declare))))

    def test_a_partially_excluded_hook_may_still_declare_its_route(self) -> None:
        """"Excluded" has to mean EVERY registration is gone.

        A hook registered under two events with only ONE excluded still reaches
        the adopter and can still block, so its route must be documentable.
        Refusing the entry because one scoped exclusion carried the basename was
        the same over-broad reading round 4 found in the install oracle
        (pair-rail round 6).
        """
        base = {
            "_comment": "c", "model": "m", "env": {"K": "1"},
            "hooks": {
                "PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))],
                "PostToolUse": [_group("", _hook("python3 .claude/hooks/a.py"))],
            },
        }
        spec = _minimal_spec(
            exclude_hooks=[{"name": "a.py", "event": "PostToolUse",
                            "class": _KLASS, "reason": "r", "evidence": "e"}],
            blocking_inclusions=[{"hook": "a.py", "route": "run it differently",
                                  "evidence": "hooks/a.py:1"}],
        )
        GEN.validate_spec(spec, base)      # must not raise
        out = GEN.derive_hooks(base, spec)
        self.assertIn("PreToolUse", out, "the survivor is what needs the route")

    def test_a_fully_excluded_hook_may_not_declare_a_route(self) -> None:
        base = {
            "_comment": "c", "model": "m", "env": {"K": "1"},
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
        }
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(_minimal_spec(
                exclude_hooks=[{"name": "a.py", "class": _KLASS,
                                "reason": "r", "evidence": "e"}],
                blocking_inclusions=[{"hook": "a.py", "route": "r",
                                      "evidence": "e"}],
            ), base)
        self.assertIn("ALL", str(ctx.exception))

    def test_the_declared_set_is_not_vacuous(self) -> None:
        """A completeness test that compares two empty sets proves nothing."""
        declared = _read(USER_TEMPLATE)["_derivation"].get("blocking_inclusions", [])
        self.assertGreaterEqual(
            len(declared), 4,
            "the wave was measured to add 4 blocking hooks (5 until the "
            "Owner ruling in r7 took check_scratchpad_access.py back out of "
            "the roster); a shorter list means either the roster shrank or "
            "the declaration rotted")

    def test_the_criterion_states_its_own_scope(self) -> None:
        """The rule that the reviewer read as a biconditional now says it is not.

        Without this the prose could quietly revert to the unscoped form and
        the same finding would return.
        """
        criterion = _read(USER_TEMPLATE)["_derivation"]["criterion"]
        self.assertIn("EXCLUSAO", criterion)
        self.assertIn("blocking_inclusions", criterion)
        self.assertIn("rota praticavel", criterion)


# ---------------------------------------------------------------------------
# pair-rail round 10 — computed keys survive a base that omits their twin
# ---------------------------------------------------------------------------

class ComputedKeysSurviveABaseWithoutThem(TestEnvContext):
    """Round 10: the output loop iterates BASE keys, so a computed key whose
    passthrough twin is absent from the base never got emitted. A base without
    `env` is a shape validate_spec accepts — and losing `env` silently drops
    every declared env_override (with the shipped spec, that ships
    check_config_protection.py BLOCKING instead of advisory). Same for a
    missing base `_comment` swallowing the generated one."""

    def setUp(self) -> None:
        super().setUp()
        self.base_no_env = {
            "_comment": "c",
            "model": "m",
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
        }

    def test_env_overrides_survive_a_base_without_env(self) -> None:
        spec = _minimal_spec(env_overrides={"CEO_X_ADVISORY": "1"})
        GEN.validate_spec(spec, self.base_no_env)
        out = GEN.generate(self.base_no_env, spec)
        self.assertIn("env", out,
                      "a declared env_override vanished with the base `env` key")
        self.assertEqual(out["env"].get("CEO_X_ADVISORY"), "1")

    def test_generated_comment_survives_a_base_without_comment(self) -> None:
        base = {
            "model": "m",
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
            "env": {"K": "1"},
        }
        spec = _minimal_spec()
        GEN.validate_spec(spec, base)
        out = GEN.generate(base, spec)
        self.assertEqual(out.get("_comment"), GEN.GENERATED_COMMENT,
                         "the generated _comment vanished with the base key")


# ---------------------------------------------------------------------------
# pair-rail round 9 — declarations validated by VALUE, not presence
# ---------------------------------------------------------------------------

class NoOpDeclarationsAreRejected(TestEnvContext):
    """Round 9 of the rail: two more members of the accepted-then-ignored family.

    (a) `_derivation.generator` was checked for PRESENCE only, so an empty or
        wrong path round-tripped through `--write`/`--check` green while the
        artifact advertised a regeneration mechanism that does not exist.
    (b) an override whose declared value is byte-equal to what the base
        already carries (because the base moved underneath it) changes no
        output byte, so its reason/evidence survive as stale justification
        for an exception that no longer exists.
    """

    def setUp(self) -> None:
        super().setUp()
        self.base = {
            "_comment": "c",
            "model": "m",
            "hooks": {"PreToolUse": [_group(
                "Edit",
                _hook("python3 .claude/hooks/a.py", statusMessage="base msg"),
                _comment="base block comment",
            )]},
            "env": {"K": "1"},
        }

    def _rejects(self, spec, fragment):
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(spec, self.base)
        self.assertIn(fragment, str(ctx.exception))

    # -- (a) generator path ------------------------------------------------

    def test_wrong_generator_path_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(generator=".claude/scripts/some-other-script.py"),
            "generator")

    def test_empty_generator_is_rejected(self) -> None:
        self._rejects(_minimal_spec(generator=""), "generator")

    def test_the_shipped_generator_path_is_the_one_accepted(self) -> None:
        GEN.validate_spec(_minimal_spec(), self.base)  # must not raise

    # -- (b) no-op overrides ----------------------------------------------

    def test_noop_matcher_override_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(matcher_overrides={"a.py": {
                "matcher": "Edit", "reason": "r", "evidence": "e"}}),
            "NO-OP")

    def test_changed_matcher_override_is_accepted(self) -> None:
        GEN.validate_spec(
            _minimal_spec(matcher_overrides={"a.py": {
                "matcher": "Edit|Write", "reason": "r", "evidence": "e"}}),
            self.base)

    def test_noop_annotation_field_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(annotation_overrides={"a.py": {
                "hook": {"statusMessage": "base msg"}, "reason": "r"}}),
            "NO-OP")

    def test_changed_annotation_field_is_accepted(self) -> None:
        GEN.validate_spec(
            _minimal_spec(annotation_overrides={"a.py": {
                "hook": {"statusMessage": "new msg"}, "reason": "r"}}),
            self.base)

    def test_noop_block_comment_is_rejected(self) -> None:
        self._rejects(
            _minimal_spec(annotation_overrides={"a.py": {
                "_comment": "base block comment", "reason": "r"}}),
            "NO-OP")


# ---------------------------------------------------------------------------
# pair-rail round 3 — closed vocabularies, and the write route the wave opened
# ---------------------------------------------------------------------------

class SpecVocabulariesAreClosed(TestEnvContext):
    """Three ways a spec could say something the derivation would not do.

    All three are the wave's own class, found inside the wave's own cure:

    * an unknown TOP-LEVEL key (`env_override` for `env_overrides`) was
      accepted, round-tripped into `_derivation`, and then ignored — the
      derivation used the correctly-spelled default and `--check` stayed green;
    * `annotation_overrides.hook` refused only `command`, so `timeout`, `type`
      and `prompt` passed. `timeout` IS behaviour, and a second source for it is
      what this generator exists to remove;
    * a bare exclusion plus an event-qualified one for the SAME hook both
      passed, because their tuple keys differ — the bare entry already removes
      every registration, so the scoped one is dead data.
    """

    def setUp(self) -> None:
        super().setUp()
        self.base = {
            "_comment": "c",
            "model": "m",
            "hooks": {
                "PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))],
                "PostToolUse": [_group("", _hook("python3 .claude/hooks/a.py"))],
            },
            "env": {"K": "1"},
        }

    def _rejects(self, spec: Dict[str, Any], fragment: str) -> None:
        with self.assertRaises(GEN.SpecError) as ctx:
            GEN.validate_spec(spec, self.base)
        self.assertIn(fragment, str(ctx.exception))

    # -- top-level vocabulary ---------------------------------------------

    def test_a_misspelled_top_level_key_is_rejected(self) -> None:
        self._rejects(_minimal_spec(env_override={"K": "0"}), "unknown key(s)")

    def test_every_key_the_shipped_spec_uses_is_in_the_vocabulary(self) -> None:
        """The closed set must not be narrower than the artifact it governs."""
        shipped = set(_read(USER_TEMPLATE)["_derivation"])
        self.assertEqual(
            sorted(shipped - GEN.SPEC_KEYS), [],
            "the shipped spec carries key(s) the closed vocabulary rejects — "
            "the generator could not re-read its own output")

    # -- annotation fields -------------------------------------------------

    def test_behavioural_hook_fields_are_rejected(self) -> None:
        for field, value in (("timeout", 9), ("type", "command"), ("prompt", "x")):
            with self.subTest(field=field):
                self._rejects(_minimal_spec(annotation_overrides={
                    "PreToolUse/a.py": {"hook": {field: value}, "reason": "r"}}),
                    "decide BEHAVIOUR")

    def test_a_presentation_field_is_accepted(self) -> None:
        """`statusMessage` is what an annotation override is FOR."""
        spec = _minimal_spec(annotation_overrides={
            "PreToolUse/a.py": {"hook": {"statusMessage": "Checking..."},
                                "reason": "r"}})
        GEN.validate_spec(spec, self.base)
        out = GEN.derive_hooks(self.base, spec)
        self.assertEqual(
            out["PreToolUse"][0]["hooks"][0]["statusMessage"], "Checking...")

    # -- per-entry vocabulary (the typo that WIDENS a subtraction) ---------

    def test_a_misspelled_event_field_is_rejected(self) -> None:
        """`events` validated, read as None, and became a TOTAL exclusion.

        The worst shape this family takes: every required field is present, the
        entry looks careful, and the artifact regenerates green — while a
        security hook is removed from EVERY event instead of one (pair-rail
        round 4).
        """
        self._rejects(_minimal_spec(exclude_hooks=[{
            "name": "a.py", "events": "PreToolUse", "class": _KLASS,
            "reason": "r", "evidence": "e"}]), "do not belong to it")

    def test_an_invented_entry_field_is_rejected(self) -> None:
        self._rejects(_minimal_spec(exclude_hooks=[{
            "name": "a.py", "class": _KLASS, "reason": "r", "evidence": "e",
            "why": "because"}]), "do not belong to it")

    def test_a_decided_exclusion_may_not_carry_pending_fields(self) -> None:
        """One shared vocabulary let an audit record contradict itself.

        A decided exclusion justifies itself (`reason` + `evidence` that
        resolves); a pending one names the open question instead, and its
        rationale lives once in `pending_note`. Letting either carry the
        other's fields round-tripped green (pair-rail round 5).
        """
        self._rejects(_minimal_spec(exclude_hooks=[{
            "name": "a.py", "class": _KLASS, "reason": "r", "evidence": "e",
            "oq": "OQ-1"}]), "do not belong to it")

    def test_a_pending_exclusion_may_not_carry_decided_fields(self) -> None:
        self._rejects(_minimal_spec(
            pending_note="n",
            exclude_hooks_pending=[{"name": "a.py", "class": GEN.PENDING_CLASS,
                                    "oq": "OQ-1", "reason": "r"}],
        ), "do not belong to it")

    def test_an_annotation_value_must_be_a_string(self) -> None:
        """The NAME being allowed says nothing about the VALUE.

        `{"statusMessage": {"x": 1}}` validated and was emitted straight into
        the hook entry, so a fresh install and every plugin build received
        schema-invalid configuration with `--check` green.
        """
        self._rejects(_minimal_spec(annotation_overrides={
            "PreToolUse/a.py": {"hook": {"statusMessage": {"x": 1}},
                                "reason": "r"}}), "must be a string")

    def test_the_shipped_exclusions_use_only_known_fields(self) -> None:
        """The closed set must not be narrower than the artifact it governs."""
        spec = _read(USER_TEMPLATE)["_derivation"]
        for bucket, allowed in (
            ("exclude_hooks", GEN._EXCLUSION_FIELDS_DECIDED),
            ("exclude_hooks_pending", GEN._EXCLUSION_FIELDS_PENDING),
        ):
            used = set()
            for entry in spec.get(bucket, []):
                used |= set(entry)
            self.assertEqual(
                sorted(used - allowed), [],
                "`%s` in the shipped spec uses field(s) its closed vocabulary "
                "rejects — the generator could not re-read its own output"
                % bucket)

    # -- overlapping exclusions --------------------------------------------

    def test_bare_and_scoped_exclusion_of_one_hook_is_rejected(self) -> None:
        self._rejects(_minimal_spec(exclude_hooks=[
            {"name": "a.py", "class": _KLASS, "reason": "r", "evidence": "e"},
            {"name": "a.py", "event": "PostToolUse", "class": _KLASS,
             "reason": "r", "evidence": "e"},
        ]), "BOTH bare and event-qualified")

    def test_a_scoped_exclusion_alone_is_accepted(self) -> None:
        """The scoped form is legitimate — only the OVERLAP is dead data."""
        spec = _minimal_spec(exclude_hooks=[
            {"name": "a.py", "event": "PostToolUse", "class": _KLASS,
             "reason": "r", "evidence": "e"}])
        GEN.validate_spec(spec, self.base)
        out = GEN.derive_hooks(self.base, spec)
        self.assertIn("PreToolUse", out, "the other registration must survive")
        self.assertNotIn("PostToolUse", out)


class WriteRefusesAnUnreviewedSpec(TestEnvContext):
    """`--spec` is for bootstrap; with `--write` it was a route around the gate.

    `check_canonical_edit` matches Edit/Write/MultiEdit — not Bash — so a
    generator invoked from a shell writing a canonical path is not seen by it.
    The reviewer found this route; the WIDER class predates the wave
    (`generate-adr-index --write` rewrites the canonical `.claude/adr/README.md`
    exactly the same way), and curing one of three would be theatre. What is
    closed here is the route this wave OPENED.

    Round 3 closed it by LOCATION ("inside the repository"). Round 4 showed that
    is not provenance: an untracked `spec.json` written anywhere under the tree
    passed. The question that means something is whether git has SEEN the file.

    These run against a SYNTHETIC repository, never the live one, and the reason
    is a scar: the first version invoked `--write` against the real tree and was
    safe only because the cure it tests was present. When the red control removed
    that cure, the write went through and rewrote the shipped
    `settings.user.json` with the test's minimal spec. A test whose safety
    depends on the code it is testing is not a test.
    """

    def _synth_repo(self, tmp: str) -> Path:
        """A synthetic root that is also a real git repository."""
        base = {
            "_comment": "c",
            "model": "m",
            "hooks": {"PreToolUse": [_group("Edit", _hook("python3 .claude/hooks/a.py"))]},
            "env": {"K": "1"},
        }
        root = _synth_root(Path(tmp), base)
        for args in (["init", "-q"],
                     ["config", "user.email", "t@example.invalid"],
                     ["config", "user.name", "t"]):
            subprocess.run(["git", "-C", str(root)] + args, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return root

    @staticmethod
    def _commit(root: Path, path: Path) -> None:
        subprocess.run(["git", "-C", str(root), "add", "--", str(path)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "spec"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @staticmethod
    def _artifact(root: Path) -> Path:
        return root / "templates" / "settings" / "settings.user.json"

    # -- the three provenances --------------------------------------------

    def test_write_with_an_out_of_tree_spec_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = self._synth_repo(td)
            spec_path = Path(td) / "spec.json"          # OUTSIDE root
            spec_path.write_text(json.dumps(_minimal_spec()), encoding="utf-8")
            proc = _run(["--write", "--spec", str(spec_path)], root)
            self.assertEqual(proc.returncode, 1,
                             "policy refusal is rc 1 (drift), never rc 2 (INFRA)")
            self.assertIn("outside the repository", proc.stderr)
            self.assertFalse(self._artifact(root).exists(),
                             "the refusal must happen BEFORE any write")

    def test_write_with_an_untracked_in_tree_spec_is_refused(self) -> None:
        """Being inside the repository is not provenance (pair-rail round 4)."""
        with tempfile.TemporaryDirectory() as td:
            root = self._synth_repo(td)
            spec_path = root / "spec.json"              # INSIDE, but untracked
            spec_path.write_text(json.dumps(_minimal_spec()), encoding="utf-8")
            proc = _run(["--write", "--spec", str(spec_path)], root)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("UNTRACKED", proc.stderr)
            self.assertFalse(self._artifact(root).exists())

    def test_write_with_a_modified_tracked_spec_is_refused(self) -> None:
        """The tracked copy was reviewed; the working-tree copy drives the write."""
        with tempfile.TemporaryDirectory() as td:
            root = self._synth_repo(td)
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(_minimal_spec()), encoding="utf-8")
            self._commit(root, spec_path)
            spec_path.write_text(
                json.dumps(_minimal_spec(criterion="changed after review")),
                encoding="utf-8")
            proc = _run(["--write", "--spec", str(spec_path)], root)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("MODIFIED", proc.stderr)
            self.assertFalse(self._artifact(root).exists())

    def test_write_with_a_tracked_clean_spec_is_allowed(self) -> None:
        """The positive control: the gate is about provenance, not about --write."""
        with tempfile.TemporaryDirectory() as td:
            root = self._synth_repo(td)
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(_minimal_spec()), encoding="utf-8")
            self._commit(root, spec_path)
            proc = _run(["--write", "--spec", str(spec_path)], root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(self._artifact(root).exists())

    def test_check_with_an_external_spec_is_allowed(self) -> None:
        """Reading a proposal and reporting the diff writes nothing."""
        with tempfile.TemporaryDirectory() as td:
            root = self._synth_repo(td)
            spec_path = Path(td) / "spec.json"
            spec_path.write_text(json.dumps(_minimal_spec()), encoding="utf-8")
            proc = _run(["--check", "--spec", str(spec_path)], root)
            self.assertNotIn("outside the repository", proc.stderr)
            self.assertNotIn("UNTRACKED", proc.stderr)

# ---------------------------------------------------------------------------
# the plugin hooks source — the inverted ACCEL tripwire
# ---------------------------------------------------------------------------

#: The keys a settings.json hook block is made of. A module-level table that
#: names a template hook AND carries these is re-registering it; one that names
#: a hook without them is referencing it for some other reason.
_REGISTRATION_SHAPE = frozenset({"matcher", "hooks", "type", "command"})


class PluginHooksHaveNoParallelSource(TestEnvContext):
    """``build-plugin.py`` derives the plugin hooks from the user template ALONE.

    Wave-F drafted a tripwire here instead of a cure: ``build-plugin`` read the
    template and then EXTENDED it with its own ``ACCEL`` literal, so once the
    roster grew, four accelerator hooks were registered TWICE in the plugin
    ``hooks.json`` — with timeouts that had drifted away from what both
    ``settings.base.json`` and this repo live ``.claude/settings.json`` actually
    run (``review_loop.py`` 60 vs 15, ``turbo_sessionstart.py`` 10 vs 5). The
    Owner ratified reconciling it in the SAME patch (DESIGN-F FU-F-ACCEL), so
    the debt marker is INVERTED into the guard that keeps the cure: the
    parallel table is asserted GONE, and the plugin registrations are asserted
    to be exactly the template ones.

    Doctrine: [[feedback-widen-guard-then-declare-debt]] — a debt marker whose
    cure lands is not deleted, it becomes a permanent guard. The class it
    closes is the one wave-F was written against: a second literal copy of a
    roster that nothing compares against the first.
    """

    BUILD_PLUGIN = REPO_ROOT / "scripts" / "build-plugin.py"

    #: The four PLAN-128 accelerators. Before wave-F they lived ONLY in the
    #: ACCEL literal; now they arrive through the derivation, so their presence
    #: is asserted positively — a spec change that drops one is a named red
    #: here, never a silent loss of the accelerator loop.
    ACCELERATORS = {
        "accel_dispatch.py",
        "codex_review_user_code.py",
        "review_loop.py",
        "turbo_sessionstart.py",
    }

    def _module(self):
        """Import build-plugin.py. Module level only reads VERSION; no I/O."""
        if not self.BUILD_PLUGIN.is_file():
            self.skipTest("scripts/build-plugin.py absent")
        spec = importlib.util.spec_from_file_location(
            "_wave_f_build_plugin", self.BUILD_PLUGIN)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _triples(hooks: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """``(event, matcher, command)`` for every registration."""
        return [
            (event, group.get("matcher", ""), entry.get("command", ""))
            for event, groups in hooks.items()
            for group in groups
            for entry in group.get("hooks", [])
        ]

    # -- the parallel table is gone ---------------------------------------

    def test_no_module_level_table_names_a_template_hook(self) -> None:
        """AST: no module-level constant re-lists hooks the template registers.

        Deliberately broader than ``ACCEL``: a table that comes back under a
        new name is the same defect. Read by AST — never by import — so a
        would-be table is caught even if it is never evaluated.
        """
        if not self.BUILD_PLUGIN.is_file():
            self.skipTest("scripts/build-plugin.py absent")
        tree = ast.parse(self.BUILD_PLUGIN.read_text(encoding="utf-8"))
        template_hooks = {n for _, n in _registrations(_read(USER_TEMPLATE))}
        offenders: Dict[str, List[str]] = {}
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            label = ", ".join(
                t.id for t in targets if isinstance(t, ast.Name)) or "<expr>"
            # Naming a hook is not the defect; RE-REGISTERING one is. A table
            # that pairs a hook with something else (the CLI it guards, a
            # timeout budget, a doc path) carries no registration shape. The
            # ACCEL table did: `matcher`, `hooks`, `type`, `command` — the keys
            # a settings.json hook block is made of.
            #
            # This distinction was forced by the guard firing on `GUARDED_CLIS`
            # in build-plugin.py, which pairs `check_scratchpad_access.py` with
            # the CLI it protects and registers nothing (pair-rail round 6). A
            # guard that cannot tell those apart would push the next author to
            # rename their way around it, which is worse than a narrow guard.
            shape = {
                k.value for k in ast.walk(node)
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            } & _REGISTRATION_SHAPE
            found = set()
            for literal in ast.walk(node):
                if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                    for hit in re.findall(r"([A-Za-z0-9_.\-]+\.py)", literal.value):
                        base = hit.rsplit("/", 1)[-1]
                        if base in template_hooks:
                            found.add(base)
            if found and shape:
                offenders[label] = sorted(found)
        self.assertEqual(
            offenders, {},
            "scripts/build-plugin.py carries a module-level table naming hooks "
            "the user template already registers: %s\n"
            "That is the FU-F-ACCEL defect returning under a new name. The "
            "plugin hooks come from templates/settings/settings.user.json and "
            "nowhere else; delete the table rather than reconcile it by hand."
            % offenders,
        )

    # -- what the plugin actually emits -----------------------------------

    def test_every_registration_is_unique(self) -> None:
        """The defect, stated behaviourally: no hook registered twice.

        This is the assertion the tripwire could not make. Re-appending any
        parallel table reproduces a duplicate ``(event, matcher, command)``
        even when the timeouts differ, so the control is exact.
        """
        mod = self._module()
        triples = self._triples(mod.compose_plugin_hooks(mod.USER_TEMPLATE))
        seen: Dict[Tuple[str, str, str], int] = {}
        for t in triples:
            seen[t] = seen.get(t, 0) + 1
        dupes = sorted(
            "%s/%s %s" % (ev, matcher or "*", GEN.hook_basename(cmd))
            for (ev, matcher, cmd), n in seen.items() if n > 1
        )
        self.assertEqual(
            dupes, [],
            "the plugin registers these hooks more than once: %s" % dupes)

    def test_the_plugin_registers_exactly_the_template(self) -> None:
        """Set equality, both directions — extra AND missing are red."""
        mod = self._module()
        composed = {
            (ev, GEN.hook_basename(cmd))
            for ev, _matcher, cmd in self._triples(
                mod.compose_plugin_hooks(mod.USER_TEMPLATE))
        }
        template = set(_registrations(_read(USER_TEMPLATE)))
        self.assertEqual(
            composed, template,
            "the plugin hook set differs from the user template.\n"
            "  only in plugin:   %s\n"
            "  only in template: %s"
            % (sorted(composed - template), sorted(template - composed)),
        )

    def test_the_accelerators_survive_the_derivation(self) -> None:
        """Positive control on the cure: the four still ship, once each."""
        mod = self._module()
        triples = self._triples(mod.compose_plugin_hooks(mod.USER_TEMPLATE))
        counts = {name: 0 for name in self.ACCELERATORS}
        for _ev, _matcher, cmd in triples:
            base = GEN.hook_basename(cmd)
            if base in counts:
                counts[base] += 1
        self.assertEqual(
            counts, {name: 1 for name in self.ACCELERATORS},
            "the PLAN-128 accelerators no longer arrive exactly once through "
            "the derivation: %s. They used to come from the build-plugin ACCEL "
            "table; since wave-s330-F they come from the user template. A 0 "
            "means the derivation spec now excludes one — decide that "
            "deliberately and update this expectation; it is not a free "
            "change." % counts,
        )

    def test_paths_are_repointed_at_the_plugin_root(self) -> None:
        """No project-dir path may survive into a plugin registration."""
        mod = self._module()
        leaked = sorted(
            GEN.hook_basename(cmd) for _ev, _m, cmd in self._triples(
                mod.compose_plugin_hooks(mod.USER_TEMPLATE))
            if "$CLAUDE_PROJECT_DIR/.claude/hooks/" in cmd
        )
        self.assertEqual(
            leaked, [],
            "these plugin registrations still point at the project dir "
            "instead of the plugin root: %s" % leaked)

    def test_the_derivation_spec_does_not_ship_in_the_plugin(self) -> None:
        """Only ``.hooks`` travels — the ~20 KB ``_derivation`` stays home."""
        mod = self._module()
        blob = mod.dump_manifest_hooks(mod.compose_plugin_hooks(mod.USER_TEMPLATE))
        self.assertNotIn("_derivation", blob)
        self.assertNotIn("exclude_hooks", blob)

    # -- anti-rot ----------------------------------------------------------

    def test_the_reconciliation_is_recorded_in_the_design(self) -> None:
        """A cure nobody documented is a cure nobody can audit."""
        design = (REPO_ROOT / ".claude" / "plans" / "PLAN-169"
                  / "s330-ceremony-F" / "DESIGN-F.md")
        if not design.is_file():
            self.skipTest("DESIGN-F.md not present in this tree")
        text = design.read_text(encoding="utf-8")
        # assertTrue, not assertIn: a failing assertIn dumps the whole design.
        self.assertTrue(
            "FU-F-ACCEL" in text,
            "DESIGN-F.md does not carry the FU-F-ACCEL follow-up id")
        missing = [n for n in sorted(self.ACCELERATORS) if n not in text]
        self.assertEqual(
            missing, [],
            "these accelerators are asserted by this guard but the DESIGN "
            "does not name them: %s" % missing)


# ---------------------------------------------------------------------------
# (h) the generator itself
# ---------------------------------------------------------------------------

class UnreadableInputIsInfrastructure(TestEnvContext):
    """The documented contract: unreadable OR unparseable input => rc 2.

    `read_text()` raises `UnicodeDecodeError` BEFORE json ever sees the bytes,
    and it is not an `OSError` — so invalid UTF-8 in any input produced a
    traceback and a generic exit instead of the rc the CLI documents
    (pair-rail round 6). An exit code that only holds for the inputs someone
    thought of is not a contract.
    """

    def _rc_for(self, payload: bytes) -> int:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / "templates" / "settings").mkdir(parents=True)
            (root / "templates" / "settings" / "settings.base.json").write_bytes(payload)
            return _run(["--check"], root).returncode

    def test_invalid_utf8_exits_infra(self) -> None:
        self.assertEqual(self._rc_for(b'{"a": "\xff\xfe"}'), 2)

    def test_invalid_json_exits_infra(self) -> None:
        self.assertEqual(self._rc_for(b"{not json"), 2)

    def test_a_malformed_TARGET_under_external_spec_exits_infra(self) -> None:
        """`--check --spec` never parses the target, so this is its first read.

        Invalid UTF-8 escaped as a traceback, and invalid JSON was reported as
        DRIFT — naming the wrong problem and sending the reader to `--write`
        instead of to the corruption (pair-rail round 7).
        """
        for payload in (b"\xff\xfe{}", b"{not json"):
            with self.subTest(payload=payload[:4]):
                with tempfile.TemporaryDirectory() as td:
                    root = _synth_root(Path(td), _read(BASE_TEMPLATE))
                    (root / "templates" / "settings" / "settings.user.json"
                     ).write_bytes(payload)
                    spec_path = Path(td) / "spec.json"
                    spec_path.write_text(json.dumps(_minimal_spec()), encoding="utf-8")
                    proc = _run(["--check", "--spec", str(spec_path)], root)
                    self.assertEqual(proc.returncode, 2, proc.stderr)
                    self.assertIn("INFRA", proc.stderr)

    def test_a_missing_input_exits_infra(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / "templates" / "settings").mkdir(parents=True)
            self.assertEqual(_run(["--check"], root).returncode, 2)


class GeneratorRuntimeContract(TestEnvContext):
    """stdlib-only and Python 3.9 — the repo's floor (CLAUDE.md §4)."""

    STDLIB = {
        "__future__", "argparse", "difflib", "hashlib", "json", "re",
        "subprocess", "sys", "pathlib", "typing",
    }

    def setUp(self) -> None:
        super().setUp()
        self.tree = ast.parse(GENERATOR.read_text(encoding="utf-8"))

    def test_compiles(self) -> None:
        py_compile.compile(str(GENERATOR), doraise=True)

    def test_imports_are_stdlib_only(self) -> None:
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        extra = imported - self.STDLIB
        self.assertEqual(extra, set(), "non-stdlib import(s): %s" % sorted(extra))

    def test_uses_postponed_annotations(self) -> None:
        futures = [
            a.name
            for node in self.tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "__future__"
            for a in node.names
        ]
        self.assertIn("annotations", futures)

    def test_no_match_statement(self) -> None:
        match_node = getattr(ast, "Match", None)
        if match_node is None:
            self.skipTest("running on Python 3.9; a match statement would not parse")
        self.assertFalse(
            [n for n in ast.walk(self.tree) if isinstance(n, match_node)],
            "match statements are Python >= 3.10; the floor is 3.9",
        )

    def test_no_runtime_pep604_union(self) -> None:
        """`X | Y` is fine in an annotation (postponed) but not at runtime."""
        offenders = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                offenders.append(getattr(node, "lineno", "?"))
        self.assertEqual(offenders, [], "runtime `|` union at line(s) %s" % offenders)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
