"""Tests for check_harness_config.py (PLAN-153 Wave E item 1 / ADR-173).

Covers:
- the runtime-resolution model (anchored vs cwd-relative, the
  ``_python-hook.sh`` dirname rule, silent fail-open dead rails);
- the settings fixture corpus under
  ``.claude/hooks/tests/fixtures/harness-config/settings/`` in BOTH
  directions (planted violations go RED; the good fixture is green; the
  allowlisted no-op passes while the unlisted no-op fails);
- the behavioral positive-control replay from the DELIVERED default dir
  ``.claude/hooks/_lib/harness_replay/`` (PLAN-183 W7a), its redden paths
  (missing / tampered / unparseable / doubled-brace) and the
  ``CEO_SOTA_DISABLE`` skip;
- PLAN-183 W7a: the DELIVERY assertion against the real installer
  predicate (C5) and the fixture consumption invariant (C3).

STAGED with the module it asserts (PLAN-153 staging discipline): tests of
NEW behavior land together with the staged file.
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import shutil
import subprocess
import unittest
import unittest.mock as mock
from pathlib import Path

from _lib.testing import TestEnvContext  # noqa: E402

import check_harness_config as chc  # noqa: E402


def _real_repo_root() -> Path:
    """Walk up from this file until the real repo root (works from both
    the staged location and the landed .claude/hooks/tests/ location).

    Requires BOTH the hook file and `.git` — a PLAN staging mirror
    (.claude/plans/PLAN-NNN/staged/wave-X/.claude/hooks/...) can contain
    staged copies of the hooks but is never a git root."""
    d = Path(__file__).resolve().parent
    for candidate in [d, *d.parents]:
        if (
            (candidate / ".git").exists()
            and (candidate / ".claude" / "hooks" / "check_bash_safety.py").is_file()
        ):
            return candidate
    raise RuntimeError("real repo root not found from " + str(d))


_REPO = _real_repo_root()
_FIXTURES = _REPO / ".claude" / "hooks" / "tests" / "fixtures" / "harness-config"
_SETTINGS_FIXTURES = _FIXTURES / "settings"
# C4: derived from the hook's own default, never re-spelled here.
_REPLAY_FIXTURES = _REPO / chc.REPLAY_FIXTURES_REL
_MANIFEST_LIB = _REPO / "scripts" / "_framework_manifest_set.sh"
_OLD_REPLAY_REL = ".claude/hooks/tests/fixtures/harness-config/replay"  # pre-W7a home, never installed
_RETIRED_MARKER = "{{PROJECT_DIR}}"


def _reds(findings):
    return [f for f in findings if f.severity == "RED"]


def _reds_for(findings, check_id):
    return [f for f in findings if f.severity == "RED" and f.check_id == check_id]


def _json_census(source):
    """(guarded JSON reads, offending lines) by AST: ``json`` only as json.<load|loads|JSONDecoder|
    dumps>, each read CALLED in place with parse_constant=_refuse_constant; no dotted/aliased import."""
    tree = ast.parse(source)
    parent = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    reads, bad = 0, []
    for n in ast.walk(tree):
        attr = parent.get(n)
        if isinstance(n, ast.Name) and n.id == "json":  # getattr(json, ...), json.decoder: no Attribute
            if getattr(attr, "attr", None) not in ("load", "loads", "JSONDecoder", "dumps"):
                bad.append(n.lineno)
            elif attr.attr != "dumps":
                reads += 1
                call = parent.get(attr)  # an alias (_D = json.JSONDecoder) is not a Call
                guard = [getattr(k.value, "id", None) for k in getattr(call, "keywords", [])
                         if k.arg == "parse_constant"]  # the refusing guard by name: not None/float (r3x)
                if not (isinstance(call, ast.Call) and call.func is attr and guard == ["_refuse_constant"]):
                    bad.append(n.lineno)
        elif isinstance(n, ast.Import):
            bad += [n.lineno for a in n.names
                    if a.name.startswith("json.") or (a.name == "json" and a.asname)]
        elif isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "json":
            bad.append(n.lineno)
    return reads, bad


class _SyntheticTreeMixin:
    """Builds the minimal synthetic project tree the settings fixtures
    reference (shim + check_ok_hook.py)."""

    def _build_tree(self) -> Path:
        root = self.project_dir  # from TestEnvContext
        hooks = root / ".claude" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "_python-hook.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        (hooks / "check_ok_hook.py").write_text("# synthetic\n", encoding="utf-8")
        return root


class TestAnalyzeHookCommand(_SyntheticTreeMixin, TestEnvContext):
    def setUp(self):
        super().setUp()
        self.root = self._build_tree()

    def _run(self, command):
        return chc.analyze_hook_command(command, self.root, location="t")

    def test_anchored_shim_existing_script_green(self):
        f, noop = self._run(
            'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" check_ok_hook.py'
        )
        self.assertEqual(_reds(f), [])
        self.assertFalse(noop)

    def test_relative_shim_is_red_s254_class(self):
        f, _ = self._run("bash .claude/hooks/_python-hook.sh check_ok_hook.py")
        reds = _reds_for(f, "runtime_resolution")
        self.assertTrue(reds)
        self.assertIn("cwd-relative", reds[0].message)

    def test_shim_arg_resolves_via_dirname_rule_missing_is_red(self):
        f, _ = self._run(
            'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" check_missing.py'
        )
        reds = _reds_for(f, "runtime_resolution")
        self.assertTrue(reds)
        self.assertIn("fail-open", reds[0].message)

    def test_shim_without_script_arg_is_red(self):
        f, _ = self._run('bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh"')
        self.assertTrue(_reds_for(f, "runtime_resolution"))

    def test_anchored_direct_py_green(self):
        f, _ = self._run('python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/check_ok_hook.py"')
        self.assertEqual(_reds(f), [])

    def test_relative_direct_py_is_red(self):
        f, _ = self._run("python3 .claude/hooks/check_ok_hook.py")
        self.assertTrue(_reds_for(f, "runtime_resolution"))

    def test_absolute_direct_py_green(self):
        target = self.root / ".claude" / "hooks" / "check_ok_hook.py"
        f, _ = self._run(f'python3 "{target}"')
        self.assertEqual(_reds(f), [])

    def test_anchored_direct_py_missing_is_red(self):
        f, _ = self._run('python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/gone.py"')
        self.assertTrue(_reds_for(f, "runtime_resolution"))

    def test_unparseable_command_fails_closed(self):
        f, _ = self._run("bash \"$CLAUDE_PROJECT_DIR/unterminated")
        reds = _reds_for(f, "runtime_resolution")
        self.assertTrue(reds)
        self.assertIn("not shell-parseable", reds[0].message)

    def test_empty_command_is_red(self):
        f, _ = self._run("   ")
        self.assertTrue(_reds_for(f, "runtime_resolution"))

    def test_echo_constant_is_noop_candidate(self):
        f, noop = self._run("echo '{\"decision\":\"allow\"}'")
        self.assertEqual(_reds(f), [])
        self.assertTrue(noop)

    def test_echo_referencing_script_is_not_noop(self):
        _, noop = self._run('echo "$CLAUDE_PROJECT_DIR/.claude/hooks/check_ok_hook.py"')
        self.assertFalse(noop)


class TestStaticOnFixtureCorpus(_SyntheticTreeMixin, TestEnvContext):
    def setUp(self):
        super().setUp()
        self.root = self._build_tree()

    def _static(self, fixture_name, **kwargs):
        kwargs.setdefault("include_exec_bit", False)
        return chc.run_static(
            self.root, [_SETTINGS_FIXTURES / fixture_name], **kwargs
        )

    def test_good_settings_zero_red(self):
        self.assertEqual(_reds(self._static("settings_good.json")), [])

    def test_planted_runtime_unresolvable_goes_red(self):
        reds = _reds_for(
            self._static("settings_runtime_unresolvable.json"), "runtime_resolution"
        )
        self.assertTrue(reds, "the S254 planted dead rail MUST redden the gate")

    def test_inline_secret_goes_red_without_echoing_value(self):
        findings = self._static("settings_inline_secret.json")
        reds = _reds_for(findings, "inline_secret")
        self.assertTrue(reds)
        for f in reds:
            self.assertNotIn("AKIA", f.message, "matched secret must not be echoed")

    def test_unlisted_noop_goes_red(self):
        reds = _reds_for(self._static("settings_noop_unlisted.json"), "noop_hook")
        self.assertTrue(reds)

    def test_annotated_noop_passes(self):
        findings = self._static("settings_noop_allowlisted.json")
        self.assertEqual(_reds_for(findings, "noop_hook"), [])
        self.assertEqual(_reds(findings), [])

    def test_allowlist_file_direction_passes(self):
        allow = self.root / "noop-allow.txt"
        allow.write_text(
            "# harness no-op allowlist (test)\nsynthetic unlisted no-op\n",
            encoding="utf-8",
        )
        findings = self._static(
            "settings_noop_unlisted.json", noop_allowlist_path=allow
        )
        self.assertEqual(_reds_for(findings, "noop_hook"), [])

    def test_missing_deny_baseline_goes_red(self):
        reds = _reds_for(self._static("settings_missing_deny.json"), "deny_baseline")
        # fixture keeps 1 of the baseline entries → all others must be flagged
        self.assertEqual(len(reds), len(chc.DENY_BASELINE) - 1)

    def test_deny_baseline_skipped_when_no_permissions_key(self):
        self.assertEqual(chc.check_deny_baseline({}, "x"), [])

    def test_malformed_settings_raises_value_error(self):
        bad = self.root / "bad.json"
        # rail r1/r3: invalid UTF-8, parse-time recursion and non-JSON constants are input too.
        for raw in (b"{not json", b"\xff", b"[" * 100000,
                    b'{"x": NaN}', b'{"x": Infinity}', b'{"x": -Infinity}'):
            bad.write_bytes(raw)
            with self.assertRaises(ValueError):
                chc.run_static(self.root, [bad], include_exec_bit=False)

    def test_non_utf8_allowlist_falls_back_to_seed(self):
        allow = self.root / "noop-allow.txt"
        allow.write_bytes(b"\xff\n")
        self.assertEqual(chc.load_noop_allowlist(self.root, allow),
                         list(chc.DEFAULT_NOOP_ALLOWLIST_SUBSTRINGS))


class TestLiveRepoStatic(TestEnvContext):
    """The gate must be green against the LIVE dogfood settings + template
    (otherwise landing this gate reds CI on day one)."""

    def test_live_settings_green(self):
        findings = chc.run_static(
            _REPO,
            [
                _REPO / ".claude" / "settings.json",
                _REPO / "templates" / "settings" / "settings.base.json",
            ],
            include_exec_bit=False,
        )
        self.assertEqual(
            _reds(findings),
            [],
            "live settings must pass: " + "; ".join(f.message for f in _reds(findings)),
        )


class TestReplay(TestEnvContext):
    def test_placeholder_substitution(self):
        m = chc.FIXTURE_PROJECT_PLACEHOLDER
        self.assertEqual(m, "@HARNESS_REPLAY_PROJECT_DIR@")  # C6: no doubled brace
        doc = {"a": [f"x {m}/y", {"b": m}], "n": 3, "old": f"{_RETIRED_MARKER}/z"}
        out = chc._substitute_placeholders(doc, Path("/repo"))
        self.assertEqual(out["a"][0], "x /repo/y")
        self.assertEqual(out["a"][1]["b"], "/repo")
        self.assertEqual(out["n"], 3)
        self.assertEqual(out["old"], f"{_RETIRED_MARKER}/z")  # only the new form is a marker

    def test_doubled_brace_fixture_reddens_run(self):
        """C6: the retired form in the canonical fixture, and a \\u007b-escaped
        pair a raw grep cannot see (PARSED values are checked), both go RED."""
        canon = _REPLAY_FIXTURES / "canonical_edit_unauthorized.json"
        bash_fx = _REPLAY_FIXTURES / "bash_safety_destructive.json"
        retired = canon.read_text(encoding="utf-8").replace(chc.FIXTURE_PROJECT_PLACEHOLDER, _RETIRED_MARKER)
        doc = json.loads(bash_fx.read_text(encoding="utf-8"))
        doc["payload"]["tool_input"]["note"] = "{{X}}"
        escaped = json.dumps(doc).replace("{{X}}", "\\u007b\\u007bX}}")
        self.assertTrue(_RETIRED_MARKER in retired and "{{" not in escaped)
        for hook, src, text in (("check_canonical_edit.py", canon, retired),
                                ("check_bash_safety.py", bash_fx, escaped)):
            d = self.project_dir / hook
            d.mkdir(parents=True, exist_ok=True)
            (d / src.name).write_text(text, encoding="utf-8")
            reds = _reds_for(chc.run_replay(_REPO, d, controls=((hook, src.name),)), "replay")
            self.assertEqual([("doubled-brace" in f.message) for f in reds], [True], hook)

    def test_is_block_shaped(self):
        self.assertTrue(chc._is_block_shaped({"decision": "block", "reason": "r"}))
        self.assertTrue(
            chc._is_block_shaped(
                {"hookSpecificOutput": {"permissionDecision": "deny"}}
            )
        )
        self.assertFalse(chc._is_block_shaped({"decision": "allow"}))
        self.assertFalse(chc._is_block_shaped({}))
        self.assertFalse(chc._is_block_shaped("block"))

    def test_missing_fixture_reddens_run(self):
        empty = self.project_dir / "empty-fixtures"
        empty.mkdir(parents=True, exist_ok=True)
        findings = chc.run_replay(_REPO, empty)
        reds = _reds_for(findings, "replay")
        self.assertEqual(len(reds), len(chc.REQUIRED_REPLAY_CONTROLS))
        for f in reds:
            self.assertIn("MISSING", f.message)

    def test_tampered_fixture_reddens_run(self):
        tampered_dir = self.project_dir / "tampered"
        tampered_dir.mkdir(parents=True, exist_ok=True)
        src = _REPLAY_FIXTURES / "bash_safety_destructive.json"
        doc = json.loads(src.read_text(encoding="utf-8"))
        doc["expect"] = "allow"  # tamper
        (tampered_dir / src.name).write_text(json.dumps(doc), encoding="utf-8")
        findings = chc.run_replay(
            _REPO,
            tampered_dir,
            controls=(("check_bash_safety.py", src.name),),
        )
        reds = _reds_for(findings, "replay")
        self.assertTrue(reds)
        self.assertIn("tampered", reds[0].message)

    def test_unparseable_fixture_reddens_run(self):
        """Unreadable or ambiguous fixtures are NAMED REDs and the controls
        after them are still reported (rail r1: a traceback dropped them)."""
        bad_dir = self.project_dir / "badfix"
        bad_dir.mkdir(parents=True, exist_ok=True)
        deep = '{"expect": "block", "payload": {"x": ' + "[" * 400 + "]" * 400 + "}}"
        for raw, why in ((b"{nope", "JSONDecodeError"), (b"\xff", "UnicodeDecodeError"),
                         (b"[" * 100000, "RecursionError"),
                         (b'{"expect": "allow", "expect": "block", "payload": {}}', "duplicate key"),
                         (b'{"expect": "block", "payload": {"n": NaN}}', "JSON constant NaN"),
                         (deep.encode(), "nesting deeper than")):
            (bad_dir / "bash_safety_destructive.json").write_bytes(raw)
            reds = _reds_for(chc.run_replay(_REPO, bad_dir), "replay")
            locs = [f"replay:{h}" for h, _ in chc.REQUIRED_REPLAY_CONTROLS]
            self.assertEqual([f.location for f in reds], locs, why)
            self.assertTrue(why in reds[1].message and "fail-closed" in reds[1].message, reds[1].message)
            self.assertEqual([("MISSING" in f.message) for f in reds], [True, False, True])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = chc.main(["--replay", "--repo-root", str(_REPO), "--fixtures-dir", str(bad_dir)])
        self.assertEqual((rc, "FAIL: 3 RED finding(s)" in buf.getvalue()), (1, True))

    def test_undecodable_deep_or_non_json_hook_stdout_is_named_red(self):
        hooks = self.project_dir / "out-root" / ".claude" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "f.json").write_text('{"expect": "block", "payload": {}}', encoding="utf-8")
        srcs = {"bytes.py": "import sys\nsys.stdout.buffer.write(b'\\xff\\n')\n",
                "deep.py": "print('[' * 100000)\n"}
        for i, const in enumerate(("NaN", "Infinity", "-Infinity")):  # rail r3: JSON.parse rejects these
            srcs[f"const{i}.py"] = "print('{\"decision\": \"block\", \"x\": %s}')\n" % const
        # rail r3 C-B1: the decision is the WHOLE stdout as ONE JSON value, not its last line.
        srcs["preamble.py"] = "print('starting')\nprint('{\"decision\": \"block\"}')\n"
        srcs["two.py"] = "print('{\"decision\": \"allow\"}')\nprint('{\"decision\": \"block\"}')\n"
        srcs["indented.py"] = "import json\nprint(json.dumps({'decision': 'block'}, indent=2))\n"
        # rail r3x: VT, FF, NBSP and U+2028 are not JSON whitespace (str.strip() hid them), as prefix
        # or suffix; CRLF and JSON's own whitespace (space, tab, CR, LF) are.
        blk, w = '{"decision": "block"}', "import sys\nsys.stdout.buffer.write(b'%s\\n')\n"
        for name, ch in (("vt", "\\x0b"), ("ff", "\\x0c"), ("nbsp", "\\xc2\\xa0"),
                         ("u2028", "\\xe2\\x80\\xa8")):
            srcs[f"{name}_prefix.py"] = w % (ch + blk)
            srcs[f"{name}_suffix.py"] = w % (blk + ch)
        srcs["crlf.py"] = w % (blk + "\\r\\n")
        srcs["jsonws.py"] = w % (" \\t\\r\\n" + blk + " \\t\\r\\n")
        for hook, src in srcs.items():
            (hooks / hook).write_text(src, encoding="utf-8")
            findings = chc.run_replay(self.project_dir / "out-root", hooks, controls=((hook, "f.json"),))
            reds = _reds_for(findings, "replay")
            want = [] if hook in ("indented.py", "crlf.py", "jsonws.py") else [True]  # converse: valid JSON
            self.assertEqual([("NOT certified alive" in f.message) for f in reds], want, hook)

    def test_every_json_read_refuses_non_json_constants(self):
        """rail r3 census (AST) over the hook, plus lane A's escapes M7–M9 and the r3 mutants."""
        src = Path(chc.__file__).read_text(encoding="utf-8")
        reads, bad = _json_census(src)
        self.assertEqual(bad, [])
        self.assertGreaterEqual(reads, 3)  # settings, fixtures, hook decisions
        for escape in ('getattr(json, "loads")("1")',
                       'import json.decoder\njson.decoder.JSONDecoder().decode("1")',
                       '_D = json.JSONDecoder\n_D().decode("1")',
                       'json.loads("1")', "import json as _j", "json.JSONDecoder().decode('1')",
                       'json.loads("1", parse_constant=None)', 'json.loads("1", parse_constant=float)'):
            self.assertTrue(_json_census(src + "\n" + escape + "\n")[1], escape)

    def test_sota_disable_skips_replay(self):
        with mock.patch.dict(os.environ, {"CEO_SOTA_DISABLE": "1"}):
            findings = chc.run_replay(_REPO, _REPLAY_FIXTURES)
        self.assertEqual(_reds(findings), [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "WARN")
        self.assertIn("skipped", findings[0].message)

    def test_live_positive_controls_all_block(self):
        """The centerpiece: replay the three planted violations against the
        real hooks in this repo; every one must be observed BLOCKING."""
        findings = chc.run_replay(_REPO)  # C4: the DEFAULT dir, as CI and /ceo-boot use it
        self.assertEqual(
            _reds(findings),
            [],
            "positive control failed: "
            + "; ".join(f"{f.location}: {f.message}" for f in _reds(findings)),
        )

    def test_default_dir_holds_exactly_the_required_fixtures(self):
        """The delivered dir is DATA: no ``__init__.py`` (OQ-12), exactly the
        table's ``*.json`` (a stray .DS_Store is fine), no doubled brace."""
        self.assertFalse((_REPLAY_FIXTURES / "__init__.py").exists())
        names = sorted(p.name for p in _REPLAY_FIXTURES.glob("*.json"))
        self.assertEqual(names, sorted(fx for _, fx in chc.REQUIRED_REPLAY_CONTROLS))
        for name in names:
            self.assertNotIn("{{", (_REPLAY_FIXTURES / name).read_text(encoding="utf-8"), name)


#: Default reads whose absence only WARNs (or is silent) — declared, so a new
#: one is classified before it can hide; a RED-on-absence read must be DELIVERED.
_WARN_ONLY_DEFAULT_READS = (".claude/settings.json", "templates/settings/settings.base.json",
                            ".claude/scripts/check-active-hooks-executable.py",
                            ".claude/hooks/harness-noop-allowlist.txt")
# The REAL installer predicate; rc 90/91 = function missing, 92 = library unsourceable.
_BASH_DELIVERY_PROBE = r"""
. "$1" || exit 92; shift
[ "$(type -t _framework_path_excluded)" = function ] || exit 90
[ "$(type -t _framework_target_entries)" = function ] || exit 91
_framework_target_entries | while IFS= read -r _e; do printf 'ENTRY\t%s\n' "$_e"; done
for _p in "$@"; do _framework_path_excluded "$_p"; printf 'EXCL\t%s\t%s\n' "$?" "$_p"; done
"""


class TestDeliveredDefaults(TestEnvContext):
    """PLAN-183 W7a (C5): a delivered gate may only REQUIRE what the installer delivers — covered
    by ``_framework_target_entries`` AND not ``_framework_path_excluded`` (the real bash library)."""

    def _probe(self, relpaths):
        bash = shutil.which("bash")
        self.assertIsNotNone(bash, "bash is required to ask the installer predicate")
        proc = subprocess.run(
            [bash, "-c", _BASH_DELIVERY_PROBE, "probe", str(_MANIFEST_LIB), *relpaths],
            capture_output=True, text=True, cwd=str(self.project_dir), timeout=60,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"},
        )
        self.assertEqual(proc.returncode, 0, f"probe rc={proc.returncode}: {proc.stderr[-600:]}")
        rows = [line.split("\t") for line in proc.stdout.splitlines()]
        entries = [r[1] for r in rows if r[0] == "ENTRY" and len(r) == 2]
        rcs = {r[2]: r[1] for r in rows if r[0] == "EXCL" and len(r) == 3}
        self.assertEqual(len(entries) + len(rcs), len(rows), "unparseable probe line")
        self.assertTrue(entries, "_framework_target_entries emitted nothing")
        odd = {r: rcs.get(r) for r in relpaths if rcs.get(r) not in ("0", "1")}
        self.assertEqual(odd, {}, "_framework_path_excluded rc must be exactly 0 or 1")
        covered = {r: any(r == e or r.startswith(e + "/") for e in entries) for r in relpaths}
        return {r: covered[r] and rcs[r] == "1" for r in relpaths}, covered, rcs

    def test_red_on_absence_reads_are_delivered(self):
        red = [chc.REPLAY_FIXTURES_REL]
        red += [f"{chc.REPLAY_FIXTURES_REL}/{fx}" for _, fx in chc.REQUIRED_REPLAY_CONTROLS]
        red += [f".claude/hooks/{h}" for h, _ in chc.REQUIRED_REPLAY_CONTROLS]
        old = [_OLD_REPLAY_REL, f"{_OLD_REPLAY_REL}/bash_safety_destructive.json"]
        tpl = "templates/settings/settings.base.json"
        delivered, covered, rcs = self._probe(red + old + [tpl])
        # Same-run controls: the old home answers EXCLUDED; templates/ is not covered.
        self.assertEqual([rcs[r] for r in old], ["0", "0"])
        self.assertFalse(any(delivered[r] for r in old) or covered[tpl] or delivered[tpl])
        self.assertEqual([r for r in red if not delivered[r]], [], "RED-on-absence read NOT delivered")
        self.assertFalse({"tests", "fixtures"} & set(Path(chc.REPLAY_FIXTURES_REL).parts))
        # The declared WARN-only list covers the hook's other defaults, and they degrade to WARN.
        declared = set(_WARN_ONLY_DEFAULT_READS)
        self.assertTrue(set(chc.DEFAULT_SETTINGS_REL) | {chc.NOOP_ALLOWLIST_REL} <= declared)
        self.assertFalse(declared & set(red))
        empty = self.project_dir / "empty-root"
        empty.mkdir(parents=True, exist_ok=True)
        findings = chc.run_static(empty, [empty / r for r in chc.DEFAULT_SETTINGS_REL], include_exec_bit=True)
        self.assertEqual((_reds(findings), bool(findings)), ([], True))


class TestReplayConsumptionInvariant(TestEnvContext):
    """C3: a fixture is JSON data on stdin; no field of it picks the program,
    argv, env or cwd — the gate's table and ``_replay_env`` do."""

    _RECORDER = (
        "import json, os, sys\nfrom pathlib import Path\nme = Path(__file__)\n"
        "rec = {'argv': sys.argv, 'cwd': os.getcwd(), 'env': sorted(os.environ), 'stdin': sys.stdin.read()}\n"
        "(me.parent / (me.stem + '.ran.json')).write_text(json.dumps(rec))\n"
        "print(json.dumps({'decision': %r}))\n"
    )

    def test_fixture_fields_do_not_choose_what_runs(self):
        root = self.project_dir / "c3-root"
        hooks = root / ".claude" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        for name, decision in (("table_hook.py", "block"), ("fixture_hook.py", "allow")):
            (hooks / name).write_text(self._RECORDER % decision, encoding="utf-8")
        payload = {"tool_name": "Bash", "tool_input": {"command": "true"}}
        doc = {"expect": "block", "hook": "fixture_hook.py", "program": "/bin/sh",
               "argv": ["fixture_hook.py", "--planted"], "env": {"HC_C3_PLANTED": "1"},
               "cwd": "/", "payload": payload}
        (root / "c3.json").write_text(json.dumps(doc), encoding="utf-8")
        findings = chc.run_replay(root, root, controls=(("table_hook.py", "c3.json"),))
        self.assertEqual(_reds(findings), [])
        self.assertFalse((hooks / "fixture_hook.ran.json").exists())
        rec = json.loads((hooks / "table_hook.ran.json").read_text(encoding="utf-8"))
        self.assertEqual([Path(a).resolve() for a in rec["argv"]], [(hooks / "table_hook.py").resolve()])
        self.assertEqual(Path(rec["cwd"]).resolve(), root.resolve())
        self.assertNotIn("HC_C3_PLANTED", rec["env"])
        self.assertEqual(json.loads(rec["stdin"]), payload)
        # Converse control: the TABLE naming the allow hook goes RED — so the run above is told apart.
        findings = chc.run_replay(root, root, controls=(("fixture_hook.py", "c3.json"),))
        self.assertEqual(len(_reds_for(findings, "replay")), 1)
        self.assertTrue((hooks / "fixture_hook.ran.json").exists())


class TestMainExitCodes(_SyntheticTreeMixin, TestEnvContext):
    def setUp(self):
        super().setUp()
        self.root = self._build_tree()

    def _main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            rc = chc.main(argv)
        return rc, buf.getvalue()

    def test_green_static_exit_0(self):
        rc, out = self._main(
            [
                "--static",
                "--no-exec-bit",
                "--repo-root",
                str(self.root),
                "--settings",
                str(_SETTINGS_FIXTURES / "settings_good.json"),
            ]
        )
        self.assertEqual(rc, 0)
        self.assertIn("OK", out)

    def test_red_static_exit_1(self):
        rc, out = self._main(
            [
                "--static",
                "--no-exec-bit",
                "--repo-root",
                str(self.root),
                "--settings",
                str(_SETTINGS_FIXTURES / "settings_runtime_unresolvable.json"),
            ]
        )
        self.assertEqual(rc, 1)
        self.assertIn("FAIL", out)

    def test_malformed_settings_exit_2(self):
        bad = self.root / "bad.json"
        bad.write_text("{oops", encoding="utf-8")
        rc, _ = self._main(
            [
                "--static",
                "--no-exec-bit",
                "--repo-root",
                str(self.root),
                "--settings",
                str(bad),
            ]
        )
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
