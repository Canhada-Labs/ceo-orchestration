"""PLAN-135 W2 H8 — CLAUDE_ENV_FILE allowlist + Setup-hook self-verification.

Two responsibilities (debate R1 constraints (a) + the S217 self-verify class):

A. EXCLUDED-VAR REGRESSION (the load-bearing security test). The persistence
   allowlist is an explicit INCLUDE-list; this test PROVES, by grepping the
   LIVE repo for every override / escape-hatch / kill-switch / enforcement
   family (CEO_*OVERRIDE, CEO_*ALLOW, CEO_TURBO, CEO_*DISABLE/_ENFORCE/_ACK/…),
   that NOT ONE of the enumerated vars ever slipped into the allowlist. This
   is the S185/S197 stale-override class regression
   ([[feedback-stale-kernel-override-silently-permits-canonical-edits]]).

B. SETUP-HOOK MECHANICS. The hook runs three advisory checks, never blocks,
   fails open on infra errors, and persists ONLY the allowlisted CEO_* subset
   to CLAUDE_ENV_FILE.

COUPLING RULE: imports the staged-only `_lib/env_persist_allowlist` +
`check_setup_verification` → this test is STAGED (lives under
staged/w2/files/.claude/hooks/tests/). The canonical-else-staged loader keeps
it runnable both in the assembled scratch (post apply-bundle) and standalone
against the staged tree.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Set

_THIS = Path(__file__).resolve()

# REPO_ROOT: walk up to the dir that holds CLAUDE.md (works from both the live
# .claude/hooks/tests/ and the staged staged/w2/files/.claude/hooks/tests/).
def _find_repo_root(start: Path) -> Path:
    p = start
    for _ in range(12):
        if (p / "CLAUDE.md").is_file() and (p / ".claude").is_dir():
            return p
        p = p.parent
    # Staged fallback: .../PLAN-135/staged/w2/files/.claude/hooks/tests/<file>
    parts = start.parts
    if "ceo-orchestration" in parts:
        return Path(*parts[: parts.index("ceo-orchestration") + 1])
    return start.parents[5]


REPO_ROOT = _find_repo_root(_THIS)
_STAGED_HOOKS = (
    REPO_ROOT / ".claude" / "plans" / "PLAN-135" / "staged" / "w2" / "files"
    / ".claude" / "hooks"
)
_LIVE_HOOKS = REPO_ROOT / ".claude" / "hooks"

# testing.TestEnvContext is on the LIVE hooks path (not staged) — add both.
for _d in (_LIVE_HOOKS, _STAGED_HOOKS):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))


def _load(modname: str, rel: str):
    """Load a module by canonical-else-staged path (the closeout-guard idiom)."""
    canonical = _LIVE_HOOKS / rel
    staged = _STAGED_HOOKS / rel
    path = canonical if canonical.is_file() else staged
    spec = importlib.util.spec_from_file_location(modname, path)
    assert spec and spec.loader, "cannot load %s from %s" % (modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


allowlist = _load("h8_env_persist_allowlist", "_lib/env_persist_allowlist.py")
setup_hook = _load("h8_check_setup_verification", "check_setup_verification.py")

try:
    from _lib.testing import TestEnvContext  # noqa: E402
except Exception:  # pragma: no cover - testing lib always present on live path
    TestEnvContext = unittest.TestCase  # type: ignore


# ---------------------------------------------------------------------------
# A. EXCLUDED-VAR REGRESSION — grep the live repo, enumerate every override var.
# ---------------------------------------------------------------------------
# Families an env var name can NEVER belong to and still be persistable.
# Each is a regex applied to a bare `CEO_[A-Z0-9_]+` token. Together they
# capture the override / escape-hatch / kill-switch / enforcement / credential
# universe the harvest pack + security-engineer round-1 flagged.
_FORBIDDEN_PATTERNS = [
    re.compile(r"CEO_[A-Z0-9_]*OVERRIDE[A-Z0-9_]*"),
    re.compile(r"CEO_[A-Z0-9_]*BYPASS[A-Z0-9_]*"),
    re.compile(r"CEO_[A-Z0-9_]*ALLOW[A-Z0-9_]*"),
    re.compile(r"CEO_[A-Z0-9_]*DISABLE[A-Z0-9_]*"),
    re.compile(r"CEO_[A-Z0-9_]*ENFORC[A-Z0-9_]*"),  # ENFORCE/ENFORCING/ENFORCEMENT
    re.compile(r"CEO_[A-Z0-9_]*_ACK[A-Z0-9_]*"),
    re.compile(r"CEO_[A-Z0-9_]*SKIP[A-Z0-9_]*"),
    re.compile(r"CEO_TURBO\b"),
    re.compile(r"CEO_[A-Z0-9_]*KILL[A-Z0-9_]*"),
    re.compile(r"CEO_[A-Z0-9_]*_KEY\b"),
    re.compile(r"CEO_[A-Z0-9_]*_TOKEN\b"),
    re.compile(r"CEO_[A-Z0-9_]*_SECRET\b"),
    re.compile(r"CEO_[A-Z0-9_]*_URL\b"),
    re.compile(r"CEO_[A-Z0-9_]*ENDPOINT[A-Z0-9_]*"),
    re.compile(r"CEO_[A-Z0-9_]*GODMODE[A-Z0-9_]*"),
    re.compile(r"CEO_[A-Z0-9_]*DANGEROUS[A-Z0-9_]*"),
    re.compile(r"CEO_[A-Z0-9_]*NO_VERIFY[A-Z0-9_]*"),
]

_SCAN_ROOTS = [".claude", "scripts", "templates", "PROTOCOL.md", "CLAUDE.md"]


def _grep_forbidden_ceo_vars() -> Set[str]:
    """Walk the live repo and collect every CEO_* token matching a forbidden
    family. The enumeration is the test's teeth: if the repo grows a new
    override var, it shows up here automatically and the disjointness assertion
    re-checks it against the allowlist."""
    found: Set[str] = set()
    token_re = re.compile(r"CEO_[A-Z0-9_]+")
    for root_name in _SCAN_ROOTS:
        root = REPO_ROOT / root_name
        files = []
        if root.is_file():
            files = [root]
        elif root.is_dir():
            files = [
                p for p in root.rglob("*")
                if p.is_file() and p.suffix in (".py", ".sh", ".json", ".md", ".yaml", ".yml", "")
                # skip the PLAN-135 staged tree's own copies to avoid scanning
                # this very test's fixtures, but DO scan live hooks/scripts.
                and "/staged/" not in str(p)
            ]
        for fp in files:
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for tok in token_re.findall(text):
                if any(pat.fullmatch(tok) or pat.search(tok) for pat in _FORBIDDEN_PATTERNS):
                    found.add(tok)
    return found


class ExcludedVarRegression(unittest.TestCase):
    def test_grep_finds_the_canonical_escape_hatches(self) -> None:
        """Sanity: the grep actually finds the named escape hatches (proves the
        enumeration has teeth — an empty grep would make disjointness vacuous)."""
        found = _grep_forbidden_ceo_vars()
        for canonical in (
            "CEO_KERNEL_OVERRIDE",
            "CEO_GIT_BYPASS_ALLOW",
            "CEO_GIT_BYPASS_ALLOW_ACK",
            "CEO_TURBO",
            "CEO_HOOKS_DISABLE",
        ):
            self.assertIn(
                canonical, found,
                "enumeration missing %s — the grep lost its teeth" % canonical,
            )
        self.assertGreater(len(found), 40, "expected dozens of override vars")

    def test_allowlist_disjoint_from_every_forbidden_var(self) -> None:
        """THE load-bearing assertion: not one grep-enumerated override /
        escape-hatch / kill-switch var is in the persistence allowlist."""
        found = _grep_forbidden_ceo_vars()
        leaked = found & set(allowlist.ENV_PERSIST_ALLOWLIST)
        self.assertEqual(
            set(), leaked,
            "STALE-OVERRIDE CLASS REGRESSION (S185/S197): these override/"
            "escape-hatch vars are in the CLAUDE_ENV_FILE allowlist and would "
            "be persisted across sessions: %s" % sorted(leaked),
        )

    def test_allowlist_entries_are_all_ceo_prefixed_and_benign(self) -> None:
        for key in allowlist.ENV_PERSIST_ALLOWLIST:
            self.assertTrue(key.startswith("CEO_"), "non-CEO_ key %r" % key)
            self.assertFalse(
                allowlist._is_forbidden_family(key),
                "allowlist key %r matches a forbidden family" % key,
            )

    def test_named_escape_hatches_explicitly_excluded(self) -> None:
        for key in (
            "CEO_KERNEL_OVERRIDE", "CEO_KERNEL_OVERRIDE_ACK",
            "CEO_GIT_BYPASS_ALLOW", "CEO_GIT_BYPASS_ALLOW_ACK",
            "CEO_TURBO", "CEO_HOOKS_DISABLE", "CEO_SKIP_HOOKS",
            "CEO_CANONICAL_GUARD_DISABLE", "CEO_AUDIT_HMAC_DISABLE",
            "CEO_OWNER_GPG_KEY", "CEO_ANALYTICS_ADMIN_KEY",
        ):
            self.assertNotIn(key, allowlist.ENV_PERSIST_ALLOWLIST)
            self.assertFalse(allowlist.is_persistable(key))


# ---------------------------------------------------------------------------
# B. filter_persistable / is_persistable purity
# ---------------------------------------------------------------------------
class FilterPersistableTest(unittest.TestCase):
    def test_filter_keeps_only_allowlisted(self) -> None:
        env = {
            "CEO_PROJECT_NAME": "acme",
            "CEO_DOMAIN": "fintech",
            "CEO_KERNEL_OVERRIDE": "1",      # MUST be dropped
            "CEO_GIT_BYPASS_ALLOW": "1",     # MUST be dropped
            "CEO_TURBO": "1",                # MUST be dropped
            "PATH": "/usr/bin",              # non-CEO → dropped
        }
        out = allowlist.filter_persistable(env)
        self.assertEqual(out, {"CEO_PROJECT_NAME": "acme", "CEO_DOMAIN": "fintech"})

    def test_filter_handles_empty_and_none(self) -> None:
        self.assertEqual(allowlist.filter_persistable(None), {})
        self.assertEqual(allowlist.filter_persistable({}), {})

    def test_filter_drops_nonstring_values(self) -> None:
        out = allowlist.filter_persistable({"CEO_PROJECT_NAME": 123})  # type: ignore
        self.assertEqual(out, {})

    def test_is_persistable_fail_closed_on_unknown(self) -> None:
        self.assertFalse(allowlist.is_persistable("CEO_BRAND_NEW_VAR"))
        self.assertFalse(allowlist.is_persistable("CEO_BRAND_NEW_OVERRIDE"))
        self.assertFalse(allowlist.is_persistable(None))  # type: ignore


# ---------------------------------------------------------------------------
# C. Setup-hook mechanics — fail-open, never-block, env persistence
# ---------------------------------------------------------------------------
class SetupHookTest(TestEnvContext):
    def _run_main(self, stdin_obj) -> dict:
        buf = io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(stdin_obj))
        try:
            with redirect_stdout(buf):
                setup_hook.main()
        finally:
            sys.stdin = old_stdin
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def test_killswitch_returns_empty(self) -> None:
        os.environ["CEO_SETUP_VERIFICATION"] = "0"
        self.assertEqual(setup_hook.gate({"cwd": str(REPO_ROOT)}), {})

    def test_malformed_stdin_fail_open(self) -> None:
        old_stdin = sys.stdin
        sys.stdin = io.StringIO("{not json")
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                setup_hook.main()
        finally:
            sys.stdin = old_stdin
        self.assertEqual(buf.getvalue().strip(), "{}")

    def test_non_object_stdin_fail_open(self) -> None:
        self.assertEqual(self._run_main([1, 2, 3]), {})

    def test_clean_tree_against_repo_root_does_not_block(self) -> None:
        # Against the real repo it should produce, at most, advisory context —
        # never a {"decision": "block"} / permission denial shape.
        out = self._run_main({"cwd": str(REPO_ROOT)})
        self.assertNotIn("decision", out)
        if out:
            self.assertIn("hookSpecificOutput", out)
            self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "Setup")

    def test_missing_scripts_yield_no_findings(self) -> None:
        # An empty scratch dir has none of the three check scripts → no advisory.
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".claude", "hooks"))
            with open(os.path.join(d, ".claude", "settings.json"), "w") as f:
                json.dump({"hooks": {}}, f)
            res = setup_hook.gate({"cwd": d})
            self.assertEqual(res, {})

    def test_exec_bit_check_flags_non_exec_registered_hook(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            hooks = os.path.join(d, ".claude", "hooks")
            os.makedirs(hooks)
            hook_path = os.path.join(hooks, "stub_hook.py")
            with open(hook_path, "w") as f:
                f.write("print('{}')\n")
            os.chmod(hook_path, 0o644)  # NON-exec (the S228 regression)
            settings = {
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "Bash", "hooks": [
                            {"type": "command", "command":
                             'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" stub_hook.py'}
                        ]}
                    ]
                }
            }
            with open(os.path.join(d, ".claude", "settings.json"), "w") as f:
                json.dump(settings, f)
            res = setup_hook.gate({"cwd": d})
            ctx = res.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn("exec-bit MISSING", ctx)
            self.assertIn("stub_hook.py", ctx)
            # Make it exec → finding clears.
            os.chmod(hook_path, 0o755)
            self.assertEqual(setup_hook.gate({"cwd": d}), {})

    def test_env_persist_writes_only_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            env_file = os.path.join(d, "session.env")
            # seed env file empty
            open(env_file, "w").close()
            os.environ["CLAUDE_ENV_FILE"] = env_file
            os.environ["CEO_PROJECT_NAME"] = "acme-spread-analysis"
            os.environ["CEO_KERNEL_OVERRIDE"] = "1"      # MUST NOT be persisted
            os.environ["CEO_GIT_BYPASS_ALLOW"] = "1"     # MUST NOT be persisted
            os.environ["CEO_TURBO"] = "1"                # MUST NOT be persisted
            # empty scratch project so the three checks find nothing
            os.makedirs(os.path.join(d, ".claude", "hooks"))
            with open(os.path.join(d, ".claude", "settings.json"), "w") as f:
                json.dump({"hooks": {}}, f)
            res = setup_hook.gate({"cwd": d})
            written = open(env_file, encoding="utf-8").read()
            # CLAUDE_ENV_FILE is SOURCED by the harness, so the writer single-
            # quotes values (shell-injection safe); assert the quoted form.
            self.assertIn("CEO_PROJECT_NAME='acme-spread-analysis'", written)
            self.assertNotIn("CEO_KERNEL_OVERRIDE", written)
            self.assertNotIn("CEO_GIT_BYPASS_ALLOW", written)
            self.assertNotIn("CEO_TURBO", written)
            ctx = res.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn("persisted", ctx)

    def test_env_persist_noop_without_env_file(self) -> None:
        os.environ.pop("CLAUDE_ENV_FILE", None)
        os.environ["CEO_PROJECT_NAME"] = "x"
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".claude", "hooks"))
            with open(os.path.join(d, ".claude", "settings.json"), "w") as f:
                json.dump({"hooks": {}}, f)
            res = setup_hook.gate({"cwd": d})
            self.assertEqual(res, {})

    def test_env_persist_drops_control_char_values(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            env_file = os.path.join(d, "session.env")
            open(env_file, "w").close()
            os.environ["CLAUDE_ENV_FILE"] = env_file
            os.environ["CEO_PROJECT_NAME"] = "good"
            os.environ["CEO_APP_NAME"] = "bad\nINJECTED=1"  # newline → dropped
            os.makedirs(os.path.join(d, ".claude", "hooks"))
            with open(os.path.join(d, ".claude", "settings.json"), "w") as f:
                json.dump({"hooks": {}}, f)
            setup_hook.gate({"cwd": d})
            written = open(env_file, encoding="utf-8").read()
            # Clean value persisted single-quoted (sourced-file safe); the
            # control-char value is dropped entirely (no INJECTED=1 leak).
            self.assertIn("CEO_PROJECT_NAME='good'", written)
            self.assertNotIn("INJECTED=1", written)


if __name__ == "__main__":
    unittest.main()
