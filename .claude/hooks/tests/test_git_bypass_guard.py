"""Unit tests for PLAN-124 WS-1 — git hook-bypass guard.

Covers:
  - the pure tokenizer / decision fn ``_lib.git_bypass.scan_command``
    (>=15 adversarial BLOCK fixtures incl. chained / combined-flag /
    env-channel / split-attack; >=12 must-ALLOW regression fixtures);
  - the ``check_bash_safety`` integration (decide_command + main emit);
  - the proven dual-auth escape hatch (MF-E) on AND off path, sourced
    from the import-time ``trusted_env`` snapshot (never live os.environ);
  - the bounded fail-CLOSED parse-failure mode (MF-L);
  - the closed-enum ``flag_class`` audit action (MF-G) with a no->=8-char-
    command-substring-leak assertion;
  - the ``emit_generic`` second-line-of-defense value coercion.

Env / HOME isolation via ``TestEnvContext`` (never the real $HOME /
audit log). Stdlib-only, Python >= 3.9, ``from __future__ annotations``.
"""

from __future__ import annotations

import io
import json
import os
import unittest.mock as mock
from pathlib import Path
from typing import Any, Dict, List, Optional

from _lib import audit_emit  # noqa: E402
from _lib import git_bypass as g  # noqa: E402
from _lib import trusted_env as _trusted_env  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

import check_bash_safety as cbs  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Pure tokenizer — adversarial BLOCK corpus (>=15)
# ---------------------------------------------------------------------------

class TestBlockCorpus(TestEnvContext):
    """Each fixture MUST block with the expected closed-enum flag_class."""

    # (command, expected_flag_class)
    _BLOCK_FIXTURES = [
        # --no-verify across the 6 subcommands (MF-C).
        ('git commit --no-verify -m "x"', g.FLAG_CLASS_NO_VERIFY_COMMIT),
        ("git push --no-verify origin main", g.FLAG_CLASS_NO_VERIFY_OTHER),
        ("git merge --no-verify feature", g.FLAG_CLASS_NO_VERIFY_OTHER),
        ("git cherry-pick --no-verify deadbeef", g.FLAG_CLASS_NO_VERIFY_OTHER),
        ("git rebase --no-verify main", g.FLAG_CLASS_NO_VERIFY_OTHER),
        ("git am --no-verify patch.eml", g.FLAG_CLASS_NO_VERIFY_OTHER),
        # commit -n / combined short flags (MF-B).
        ('git commit -n -m "x"', g.FLAG_CLASS_NO_VERIFY_COMMIT),
        ('git commit -nm "x"', g.FLAG_CLASS_NO_VERIFY_COMMIT),
        ('git commit -nFm "x"', g.FLAG_CLASS_NO_VERIFY_COMMIT),
        # inline -c core.hooksPath (case-insensitive key).
        ("git -c core.hooksPath=/dev/null commit -m x", g.FLAG_CLASS_HOOKSPATH_INLINE),
        ("git -c core.hookspath=/tmp/empty push", g.FLAG_CLASS_HOOKSPATH_INLINE),
        # git config WRITE to core.hooksPath — the split attack (MF-D).
        ("git config core.hooksPath /tmp/empty", g.FLAG_CLASS_HOOKSPATH_CONFIG_WRITE),
        ("git config --unset core.hooksPath", g.FLAG_CLASS_HOOKSPATH_CONFIG_WRITE),
        ("git config --replace-all core.hooksPath /x", g.FLAG_CLASS_HOOKSPATH_CONFIG_WRITE),
        # env-var config channel (MF-D).
        (
            "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath "
            "GIT_CONFIG_VALUE_0=/dev/null git commit -m x",
            g.FLAG_CLASS_GIT_CONFIG_ENV_CHANNEL,
        ),
        ("env GIT_CONFIG_KEY_0=core.hooksPath git commit -m x",
         g.FLAG_CLASS_GIT_CONFIG_ENV_CHANNEL),
        ("export GIT_CONFIG_KEY_2=core.hooksPath", g.FLAG_CLASS_GIT_CONFIG_ENV_CHANNEL),
        # alias smuggle (MF-D).
        ('git -c alias.x="!git commit --no-verify" x', g.FLAG_CLASS_ALIAS_ABUSE),
        ('git -c alias.y="config core.hooksPath /x" y', g.FLAG_CLASS_ALIAS_ABUSE),
        # --git-dir / -C redirect paired with a hook-bearing write (MF-D).
        ("git -C ../other commit --no-verify -m x", g.FLAG_CLASS_GIT_DIR_REDIRECT),
        ("git --git-dir=/tmp/r.git commit -m x", g.FLAG_CLASS_GIT_DIR_REDIRECT),
        # chained — trigger in a LATER git invocation (MF-F).
        ("ls && git commit --no-verify -m x", g.FLAG_CLASS_NO_VERIFY_COMMIT),
        ("cd repo; git push --no-verify", g.FLAG_CLASS_NO_VERIFY_OTHER),
        ("make build || git commit -n -m wip", g.FLAG_CLASS_NO_VERIFY_COMMIT),
        # privilege-prefixed git (MF — normalization).
        ("sudo git commit --no-verify -m x", g.FLAG_CLASS_NO_VERIFY_COMMIT),
        # absolute / escaped git binary.
        ("/usr/bin/git commit --no-verify -m x", g.FLAG_CLASS_NO_VERIFY_COMMIT),
        # DEFECT-2: --config-env channel sets core.hooksPath (=form + split).
        ("git --config-env=core.hooksPath=X commit -m ok",
         g.FLAG_CLASS_HOOKSPATH_INLINE),
        ("git --config-env core.hooksPath=X commit",
         g.FLAG_CLASS_HOOKSPATH_INLINE),
        # DEFECT-3: alias body smuggling commit short `-n` (and `-nm` bundle).
        ('git -c alias.c="!git commit -n" c', g.FLAG_CLASS_ALIAS_ABUSE),
        ('git -c alias.c="!git commit -nm m" c', g.FLAG_CLASS_ALIAS_ABUSE),
        # DEFECT-1: shell-wrapper evasion (bash -c / sh -c) — emit the
        # recursively-found flag_class.
        ('bash -c "git commit --no-verify -m x"', g.FLAG_CLASS_NO_VERIFY_COMMIT),
        ("sh -c 'git push --no-verify'", g.FLAG_CLASS_NO_VERIFY_OTHER),
        # R2-DEFECT-2: short cluster with `n` BEFORE a value-taking option IS
        # no-verify (getopt: `n` is consumed before the glued value begins).
        ("git commit -nm nope", g.FLAG_CLASS_NO_VERIFY_COMMIT),
        ("git commit -nmclean", g.FLAG_CLASS_NO_VERIFY_COMMIT),
        ("git commit -anm msg", g.FLAG_CLASS_NO_VERIFY_COMMIT),
        # R3-DEFECT: bypass EMBEDDED inside a shell-function / nested alias body
        # (leading-only scan missed these).
        ("git -c alias.c='!f() { git commit -n \"$@\"; }; f' c -m x",
         g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.c='!f() { git commit --no-verify; }; f' c",
         g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.c='!sh -c \"git commit -n\"' c",
         g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.c='!f() { git -c core.hooksPath=/tmp commit; }; f' c",
         g.FLAG_CLASS_ALIAS_ABUSE),
        # R4-DEFECT: non-`!` alias body = git-IMPLIED subcommand (git prepends
        # `git`); a bypass there must block too.
        ("git -c alias.c='commit -n' c -m x", g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.c='commit --no-verify' c", g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.p='push --no-verify' p", g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.c='-c core.hooksPath=/tmp commit' c",
         g.FLAG_CLASS_ALIAS_ABUSE),
        # R5-DEFECT: a `config core.hooksPath <val>` WRITE in an alias body must
        # still block (token-accurate, not the removed substring fast-path).
        ("git -c alias.x='config core.hooksPath /tmp' x",
         g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.x='config --global core.hooksPath /tmp' x",
         g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.c='!git config core.hooksPath /tmp' c",
         g.FLAG_CLASS_ALIAS_ABUSE),
        # R6-DEFECT: the `-C <dir>` / `--git-dir=` redirect detector now runs on
        # the alias path too (scanner-set unification). `!`-shell + non-`!`.
        ("git -c alias.c='!git -C /tmp/other commit' c -m x",
         g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.c='!git --git-dir=/tmp/o/.git commit' c",
         g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.c='-C /tmp/other commit' c -m x",
         g.FLAG_CLASS_ALIAS_ABUSE),
        ("git -c alias.c='--git-dir=/tmp/o/.git commit' c",
         g.FLAG_CLASS_ALIAS_ABUSE),
    ]

    def test_block_corpus(self):
        self.assertGreaterEqual(len(self._BLOCK_FIXTURES), 15)
        for cmd, expected in self._BLOCK_FIXTURES:
            with self.subTest(cmd=cmd):
                m = g.scan_command(cmd)
                self.assertIsNotNone(m, f"expected BLOCK, got ALLOW: {cmd!r}")
                self.assertEqual(m.flag_class, expected, f"cmd={cmd!r}")
                self.assertIn(m.flag_class, g.GIT_BYPASS_FLAG_CLASSES)
                self.assertIn("BLOCKED", m.reason)


# ---------------------------------------------------------------------------
# 2. Pure tokenizer — must-ALLOW regression corpus (>=12)
# ---------------------------------------------------------------------------

class TestAllowCorpus(TestEnvContext):
    """Each fixture MUST pass (scan_command returns None)."""

    _ALLOW_FIXTURES = [
        # quoted commit message containing the literal trigger strings (MF-F).
        'git commit -m "remember to never use --no-verify"',
        'git commit -m "do not touch core.hooksPath"',
        'git commit -m "core.hooksPath=/x is bad"',
        # push -n is --dry-run, NOT --no-verify (MF-B).
        "git push -n origin main",
        "git push --dry-run origin main",
        # trigger only in a PRIOR non-git command (MF-F).
        "echo --no-verify && git status",
        'printf "core.hooksPath" ; git log --oneline',
        # legitimate redirect read.
        "git -C ../other-repo status",
        "git -C ../other-repo log --oneline",
        # ordinary git operations.
        'git commit -m "msg"',
        "git rebase main",
        "git push origin main",
        "git merge feature",
        # a config READ of core.hooksPath is harmless.
        "git config --get core.hooksPath",
        "git config --list",
        # non-git commands untouched.
        "rm -f foo.txt",
        "ls -la",
        # push with a combined short bundle that is NOT no-verify (dry-run+quiet).
        "git push -nq origin main",
        # FIX 1: a file literally NAMED --no-verify passed as a pathspec after
        # git's `--` end-of-options separator is a legitimate commit (hooks
        # still run) and MUST NOT be over-blocked.
        "git commit -m msg -- --no-verify",
        "git commit -- --no-verify",
        # DEFECT-4: quote-aware tokenizer — a commit MESSAGE that literally
        # contains a trigger flag or a shell operator MUST NOT be misread.
        'git commit -m "--no-verify"',
        'git commit -m "fix ; not a chain"',
        'git commit -m "use && and || in msg"',
        'git commit -m "core.hooksPath=/x in message"',
        # DEFECT-4: -C / -m VALUE skipping must not surface a bypass flag.
        "git commit -C noverify",
        'git commit -m "-n"',
        # legitimate global -C redirect on a READ subcommand.
        "git -C ../other-repo status",
        # push -n is dry-run (MF-B), not no-verify.
        "git push -n origin main",
        # ordinary clean commit.
        'git commit -m "ok"',
        # R2-DEFECT-2: a value-taking short option's GLUED value containing `n`
        # is NOT no-verify (getopt: the value consumes the rest of the token).
        "git commit -mclean",
        "git commit -mnope",
        "git commit -mn",
        "git commit -Fnotes.txt",
        "git commit -Cnoverify",
        "git commit -amn msg",
        # R3-DEFECT: innocuous alias bodies (function / non-commit / log /
        # glued-value commit) must NOT false-positive under the embedded scan.
        "git -c alias.c='!f() { git commit \"$@\"; }; f' c -m x",
        "git -c alias.c='!git status' s",
        "git -c alias.lg='log --oneline' lg",
        "git -c alias.c='!f() { git commit -mn; }; f' c",
        # R4-DEFECT: innocuous NON-`!` git-subcommand aliases must ALLOW.
        "git -c alias.lg='log --oneline' lg",
        "git -c alias.st='status' st",
        "git -c alias.ci='commit' ci",
        "git -c alias.c='commit -mn' c",
        "git -c alias.p='push -n' p",
        # R5-DEFECT: aliases that merely MENTION core.hooksPath must ALLOW —
        # a commit MESSAGE literal and a config READ are not bypasses.
        "git -c alias.c='commit -m \"core.hooksPath is bad\"' c",
        "git -c alias.ch='config --get core.hooksPath' ch",
        "git -c alias.l='config --list' l",
        # R6-DEFECT: a `-C <dir>` redirect on a READ subcommand is allowed on
        # the DIRECT path, so the alias path must AGREE (consistency).
        "git -c alias.c='!git -C /tmp/other status' c",
        "git -c alias.c='-C /tmp/other status' c",
    ]

    def test_allow_corpus(self):
        self.assertGreaterEqual(len(self._ALLOW_FIXTURES), 12)
        for cmd in self._ALLOW_FIXTURES:
            with self.subTest(cmd=cmd):
                self.assertIsNone(
                    g.scan_command(cmd),
                    f"expected ALLOW, got BLOCK: {cmd!r}",
                )

    def test_no_verify_before_dashdash_still_blocks(self):
        # A genuine --no-verify BEFORE any `--` separator must STILL block —
        # the end-of-options break must not weaken the real bypass detection.
        m = g.scan_command("git commit --no-verify -m msg -- file.txt")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_NO_VERIFY_COMMIT)
        # And the plain genuine form with no `--` at all.
        m2 = g.scan_command("git commit --no-verify -m msg")
        self.assertIsNotNone(m2)
        self.assertEqual(m2.flag_class, g.FLAG_CLASS_NO_VERIFY_COMMIT)


# ---------------------------------------------------------------------------
# 2b. Tokenizer edge-branch coverage (defensive paths)
# ---------------------------------------------------------------------------

class TestTokenizerEdges(TestEnvContext):

    def test_env_with_u_user_flag_reaches_git(self):
        m = g.scan_command("env -u FOO GIT_CONFIG_KEY_0=core.hooksPath git commit -m x")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_GIT_CONFIG_ENV_CHANNEL)

    def test_glued_short_c_hookspath(self):
        m = g.scan_command("git -ccore.hooksPath=/x commit -m y")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_HOOKSPATH_INLINE)

    def test_git_dir_eq_redirect_with_write(self):
        m = g.scan_command("git --git-dir=/tmp/r.git push origin main")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_GIT_DIR_REDIRECT)

    def test_git_dir_redirect_with_read_passes(self):
        # redirect + a NON-hook-bearing subcommand (status) must pass.
        self.assertIsNone(g.scan_command("git --git-dir=/tmp/r.git status"))

    def test_config_read_then_write_flag_is_write(self):
        # --get (read) alongside --unset (write) → treated as a write.
        m = g.scan_command("git config --get --unset core.hooksPath")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_HOOKSPATH_CONFIG_WRITE)

    def test_alias_body_lowercase_hookspath(self):
        m = g.scan_command('git -c alias.z="config --add core.hookspath /x" z')
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_ALIAS_ABUSE)

    def test_config_other_key_write_passes(self):
        # writing a non-hookspath key must pass.
        self.assertIsNone(g.scan_command("git config user.name Bob"))

    def test_no_verify_other_subcmd_short_n_is_ignored(self):
        # `-n` on a non-commit subcommand is NOT no-verify (merge -n etc.).
        self.assertIsNone(g.scan_command("git merge -n feature"))

    def test_boolean_global_then_subcommand(self):
        # boolean global (--no-pager) before commit --no-verify still blocks.
        m = g.scan_command("git --no-pager commit --no-verify -m x")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_NO_VERIFY_COMMIT)

    def test_git_with_no_subcommand_passes(self):
        self.assertIsNone(g.scan_command("git --version"))
        self.assertIsNone(g.scan_command("git -C ../x"))

    def test_inline_c_non_hookspath_passes(self):
        self.assertIsNone(g.scan_command("git -c user.name=Bob commit -m x"))

    def test_env_u_strip_reaches_git_no_verify(self):
        # env -u VAR ... git commit --no-verify → strip env+flags, reach git.
        m = g.scan_command("env -u SOMEVAR git commit --no-verify -m x")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_NO_VERIFY_COMMIT)

    def test_env_dashdash_then_git(self):
        m = g.scan_command("env FOO=bar -- git commit --no-verify -m x")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_NO_VERIFY_COMMIT)

    def test_non_git_unparseable_in_chain_after_git_passes(self):
        # A clean git + a later non-git unparseable chunk → ALLOW (bounded).
        self.assertIsNone(g.scan_command('git status ; awk "{print'))


# ---------------------------------------------------------------------------
# 2c. PLAN-124 confirmed-defect regressions (exact Codex repros)
# ---------------------------------------------------------------------------

class TestConfirmedDefectRepros(TestEnvContext):
    """One assertion per Codex-verified repro for DEFECT-1..4."""

    # --- DEFECT-4: quote-aware tokenizer (root cause) ----------------------

    def test_defect4_message_no_verify_value_allows(self):
        # `-m` VALUE literally "--no-verify" must NOT be scanned as a flag.
        self.assertIsNone(g.scan_command('git commit -m "--no-verify"'))

    def test_defect4_message_semicolon_not_a_chain_split(self):
        # `;` inside the quoted message must NOT split the chain → no
        # parse_failure, no block.
        self.assertIsNone(g.scan_command('git commit -m "fix ; not a chain"'))

    def test_defect4_message_logical_ops_allow(self):
        self.assertIsNone(g.scan_command('git commit -m "use && and || in msg"'))

    def test_defect4_message_hookspath_string_allows(self):
        self.assertIsNone(
            g.scan_command('git commit -m "core.hooksPath=/x in message"')
        )

    # --- DEFECT-2: --config-env channel ------------------------------------

    def test_defect2_config_env_eq_form_blocks(self):
        m = g.scan_command("git --config-env=core.hooksPath=HOOKS commit -m ok")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_HOOKSPATH_INLINE)

    def test_defect2_config_env_split_form_blocks(self):
        m = g.scan_command("git --config-env core.hooksPath=X commit")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_HOOKSPATH_INLINE)

    def test_defect2_config_env_non_hookspath_allows(self):
        # A --config-env that sets a benign key must pass.
        self.assertIsNone(
            g.scan_command("git --config-env=user.name=NAME_ENV commit -m ok")
        )

    # --- DEFECT-3: alias body commit short -n ------------------------------

    def test_defect3_alias_body_short_n_blocks(self):
        m = g.scan_command('git -c alias.c="!git commit -n" c')
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_ALIAS_ABUSE)

    def test_defect3_alias_body_short_nm_bundle_blocks(self):
        m = g.scan_command('git -c alias.c="!git commit -nm m" c')
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_ALIAS_ABUSE)

    def test_defect3_alias_body_m_only_does_not_false_positive(self):
        # An alias whose commit body has ONLY -m (no `n`) must NOT block.
        self.assertIsNone(g.scan_command('git -c alias.c="!git commit -m x" c'))

    # --- DEFECT-1: shell-wrapper recursion (pure-scanner view) -------------

    def test_defect1_bash_c_body_blocks(self):
        m = g.scan_command('bash -c "git commit --no-verify -m x"')
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_NO_VERIFY_COMMIT)

    def test_defect1_sh_c_push_blocks(self):
        m = g.scan_command("sh -c 'git push --no-verify'")
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_NO_VERIFY_OTHER)

    def test_defect1_eval_body_blocks(self):
        m = g.scan_command('eval "git commit --no-verify -m x"')
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_NO_VERIFY_COMMIT)

    def test_defect1_recursion_bounded_no_crash(self):
        # Deeply nested wrappers must not recurse past the cap or crash;
        # bounded scan returns a result (block or None) without raising.
        deep = 'bash -c "' * 6 + "git commit --no-verify -m x" + '"' * 6
        # Should not raise; result is allowed to be None past the depth cap.
        g.scan_command(deep)

    def test_defect1_bash_c_clean_body_allows(self):
        # A clean git inside bash -c must pass.
        self.assertIsNone(g.scan_command('bash -c "git commit -m ok"'))


# ---------------------------------------------------------------------------
# 2d. R2 review — defects introduced by the shlex refactor
# ---------------------------------------------------------------------------

class TestR2Defects(TestEnvContext):
    """R2-DEFECT-1 (depth cap must fail CLOSED) + R2-DEFECT-2 (getopt cluster)."""

    # --- R2-DEFECT-1: recursion cap fails CLOSED ---------------------------

    def test_r2d1_four_deep_wrapper_fails_closed(self):
        import shlex
        cmd = "git commit --no-verify -m x"
        for _ in range(4):
            cmd = "bash -c " + shlex.quote(cmd)
        m = g.scan_command(cmd)
        self.assertIsNotNone(m, "4-deep wrapper nest must BLOCK (fail-CLOSED)")
        self.assertEqual(m.flag_class, g.FLAG_CLASS_PARSE_FAILURE)

    def test_r2d1_three_deep_wrapper_still_finds_within_cap(self):
        # Within the cap the real no-verify is found (not a depth fail-CLOSED).
        import shlex
        cmd = "git commit --no-verify -m x"
        for _ in range(3):
            cmd = "bash -c " + shlex.quote(cmd)
        m = g.scan_command(cmd)
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_NO_VERIFY_COMMIT)

    def test_r2d1_deep_clean_wrapper_at_cap_fails_closed(self):
        # A CLEAN command nested at/beyond the cap is conservatively blocked
        # (we refuse to recurse deeper rather than silently allow).
        import shlex
        cmd = "git status"
        for _ in range(4):
            cmd = "bash -c " + shlex.quote(cmd)
        m = g.scan_command(cmd)
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_PARSE_FAILURE)

    # --- R2-DEFECT-2: getopt short-cluster value semantics -----------------

    def test_r2d2_glued_value_with_n_allows(self):
        for ok in (
            "git commit -mclean", "git commit -mnope", "git commit -mn",
            "git commit -Fnotes.txt", "git commit -Cnoverify",
            "git commit -amn msg",
        ):
            with self.subTest(cmd=ok):
                self.assertIsNone(g.scan_command(ok),
                                  f"glued value must ALLOW: {ok!r}")

    def test_r2d2_n_before_value_opt_blocks(self):
        for bad in (
            "git commit -nm nope", "git commit -nmclean",
            "git commit -anm msg", "git commit -nFm x", "git commit -n -m x",
        ):
            with self.subTest(cmd=bad):
                m = g.scan_command(bad)
                self.assertIsNotNone(m, f"n-before-value must BLOCK: {bad!r}")
                self.assertEqual(m.flag_class, g.FLAG_CLASS_NO_VERIFY_COMMIT)

    def test_r2d2_alias_body_inherits_corrected_cluster_logic(self):
        # The DEFECT-3 alias path must NOT re-introduce the false-positive.
        self.assertIsNone(g.scan_command('git -c alias.c="!git commit -mn" c'))
        self.assertIsNone(
            g.scan_command('git -c alias.c="!git commit -Cnoverify" c')
        )
        m = g.scan_command('git -c alias.c="!git commit -nm m" c')
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_ALIAS_ABUSE)


# ---------------------------------------------------------------------------
# 2e. R3 review — function-style / embedded alias-body bypass
# ---------------------------------------------------------------------------

class TestR3EmbeddedAliasBypass(TestEnvContext):
    """R3-DEFECT: a bypass hidden INSIDE a shell-function (or nested wrapper)
    alias body must be caught by the whole-body embedded-invocation scan, with
    NO message/innocuous false-positives."""

    _BLOCK = [
        # the verified repro — function body hides `git commit -n`.
        "git -c alias.c='!f() { git commit -n \"$@\"; }; f' c -m x",
        # function body with explicit --no-verify.
        "git -c alias.c='!f() { git commit --no-verify; }; f' c",
        # nested shell-wrapper inside the alias body.
        "git -c alias.c='!sh -c \"git commit -n\"' c",
        # embedded inline -c core.hooksPath inside the function body.
        "git -c alias.c='!f() { git -c core.hooksPath=/tmp commit; }; f' c",
    ]

    _ALLOW = [
        # function alias with NO bypass.
        "git -c alias.c='!f() { git commit \"$@\"; }; f' c -m x",
        # non-commit alias body.
        "git -c alias.c='!git status' s",
        # innocuous git alias (no shell escape).
        "git -c alias.lg='log --oneline' lg",
        # `-mn` glued value = message "n", NOT no-verify (getopt).
        "git -c alias.c='!f() { git commit -mn; }; f' c",
    ]

    def test_r3_embedded_block(self):
        for cmd in self._BLOCK:
            with self.subTest(cmd=cmd):
                m = g.scan_command(cmd)
                self.assertIsNotNone(m, f"expected BLOCK: {cmd!r}")
                self.assertEqual(m.flag_class, g.FLAG_CLASS_ALIAS_ABUSE)

    def test_r3_embedded_allow(self):
        for cmd in self._ALLOW:
            with self.subTest(cmd=cmd):
                self.assertIsNone(
                    g.scan_command(cmd), f"expected ALLOW: {cmd!r}"
                )

    def test_r3_embedded_bypass_via_decide_command(self):
        # Integration: the repro must BLOCK through decide_command too.
        d = cbs.decide_command(
            "git -c alias.c='!f() { git commit -n \"$@\"; }; f' c -m x"
        )
        self.assertFalse(d.allow)
        # And the innocuous function alias must ALLOW.
        d2 = cbs.decide_command(
            "git -c alias.c='!f() { git commit \"$@\"; }; f' c -m x"
        )
        self.assertTrue(d2.allow)

    def test_r3_message_with_no_verify_literal_in_alias_body_allows(self):
        # A commit MESSAGE literal containing --no-verify inside an alias body
        # must NOT false-positive (token-accurate, not substring).
        self.assertIsNone(
            g.scan_command(
                "git -c alias.c='!f() { git commit -m \"about --no-verify\"; }; f' c"
            )
        )


# ---------------------------------------------------------------------------
# 2f. R4 review — non-`!` git-subcommand alias (the other half of the model)
# ---------------------------------------------------------------------------

class TestR4NonShellAlias(TestEnvContext):
    """R4-DEFECT: an alias body NOT starting with `!` is a git-IMPLIED
    subcommand (git prepends `git`); a bypass there must block, with no
    false-positives on innocuous subcommand aliases."""

    _BLOCK = [
        "git -c alias.c='commit -n' c -m x",
        "git -c alias.c='commit --no-verify' c",
        "git -c alias.p='push --no-verify' p",
        "git -c alias.c='-c core.hooksPath=/tmp commit' c",
        # other-subcommand --no-verify (merge) via the implied-git path.
        "git -c alias.m='merge --no-verify x' m",
        # `n` BEFORE the value-taking option in the implied-git commit cluster.
        "git -c alias.c='commit -nm x' c",
    ]

    _ALLOW = [
        "git -c alias.lg='log --oneline' lg",
        "git -c alias.st='status' st",
        "git -c alias.ci='commit' ci",
        "git -c alias.c='commit -mn' c",   # message "n", getopt
        "git -c alias.p='push -n' p",      # push -n = --dry-run
    ]

    def test_r4_non_shell_block(self):
        for cmd in self._BLOCK:
            with self.subTest(cmd=cmd):
                m = g.scan_command(cmd)
                self.assertIsNotNone(m, f"expected BLOCK: {cmd!r}")
                self.assertEqual(m.flag_class, g.FLAG_CLASS_ALIAS_ABUSE)

    def test_r4_non_shell_allow(self):
        for cmd in self._ALLOW:
            with self.subTest(cmd=cmd):
                self.assertIsNone(
                    g.scan_command(cmd), f"expected ALLOW: {cmd!r}"
                )

    def test_r4_non_shell_message_literal_allows(self):
        # --no-verify inside a commit MESSAGE on the implied-git path must
        # ALLOW (token-accurate, not substring).
        self.assertIsNone(
            g.scan_command("git -c alias.c='commit -m \"re --no-verify\"' c")
        )

    def test_r4_non_shell_block_via_decide_command(self):
        d = cbs.decide_command("git -c alias.c='commit -n' c -m x")
        self.assertFalse(d.allow)
        d2 = cbs.decide_command("git -c alias.st='status' st")
        self.assertTrue(d2.allow)


# ---------------------------------------------------------------------------
# 2g. R5 review — the legacy core.hooksPath substring fast-path over-blocked
# ---------------------------------------------------------------------------

class TestR5AliasHookspathSubstring(TestEnvContext):
    """R5-DEFECT: the blanket `core.hooksPath`/`hookspath` substring fast-path
    was removed; detection is now token-accurate (WRITE blocks, READ/message
    literal allow)."""

    _BLOCK = [
        # inline -c override.
        "git -c alias.c='-c core.hooksPath=/tmp commit' c",
        # config WRITE (non-`!` implied-git).
        "git -c alias.x='config core.hooksPath /tmp' x",
        "git -c alias.x='config --global core.hooksPath /tmp' x",
        # config WRITE inside a `!`-shell git invocation.
        "git -c alias.c='!git config core.hooksPath /tmp' c",
    ]

    _ALLOW = [
        # commit MESSAGE literal mentioning the key — not a bypass.
        "git -c alias.c='commit -m \"core.hooksPath is bad\"' c",
        # config READ forms.
        "git -c alias.ch='config --get core.hooksPath' ch",
        "git -c alias.l='config --list' l",
        # `!`-shell git config READ.
        "git -c alias.c='!git config --get core.hooksPath' c",
        # bare shell `config` (no git word) — not a git invocation.
        "git -c alias.x='!config core.hooksPath /tmp' x",
    ]

    def test_r5_block(self):
        for cmd in self._BLOCK:
            with self.subTest(cmd=cmd):
                m = g.scan_command(cmd)
                self.assertIsNotNone(m, f"expected BLOCK: {cmd!r}")
                self.assertEqual(m.flag_class, g.FLAG_CLASS_ALIAS_ABUSE)

    def test_r5_allow(self):
        for cmd in self._ALLOW:
            with self.subTest(cmd=cmd):
                self.assertIsNone(
                    g.scan_command(cmd), f"expected ALLOW: {cmd!r}"
                )

    def test_r5_config_write_vs_read_distinction(self):
        # The underlying scanner cleanly separates WRITE from READ.
        write = g.scan_command("git -c alias.x='config core.hooksPath /tmp' x")
        self.assertIsNotNone(write)
        self.assertIsNone(
            g.scan_command("git -c alias.ch='config --get core.hooksPath' ch")
        )

    def test_r5_via_decide_command(self):
        self.assertFalse(
            cbs.decide_command(
                "git -c alias.x='config core.hooksPath /tmp' x"
            ).allow
        )
        self.assertTrue(
            cbs.decide_command(
                "git -c alias.c='commit -m \"core.hooksPath is bad\"' c"
            ).allow
        )


# ---------------------------------------------------------------------------
# 2h. R6 review — scanner-set unification (alias path == direct path)
# ---------------------------------------------------------------------------

class TestR6ScannerUnification(TestEnvContext):
    """R6-DEFECT: the alias-body paths now run the EXACT SAME per-invocation
    detector set as the direct path. This locks in the no-divergence property
    so a future scanner cannot silently miss the alias path."""

    # A battery of git-subcommand bodies covering EVERY detector class.
    _BODIES = [
        "commit -n",
        "commit -mn",
        "commit --no-verify",
        "commit -nm x",
        "-C /tmp/o commit",
        "--git-dir=/tmp/o/.git commit",
        "-C /tmp/o status",
        "config core.hooksPath /x",
        "config --global core.hooksPath /x",
        "config --get core.hooksPath",
        "config --list",
        "-c core.hooksPath=/x commit",
        "push --no-verify",
        "push -n",
        "merge --no-verify x",
        "log --oneline",
        "status",
        "commit",
    ]

    def test_alias_path_agrees_with_direct_path(self):
        # For every body B: an alias whose body is B must block IFF the direct
        # `git B` blocks. Asserted for BOTH the non-`!` (git-implied) form and
        # the `!`-shell form (`!git B`) — both must mirror the direct path.
        for body in self._BODIES:
            direct = g.scan_command("git " + body)
            direct_blocked = direct is not None
            with self.subTest(body=body, form="non-bang"):
                alias = g.scan_command(
                    "git -c alias.x='" + body + "' x"
                )
                self.assertEqual(
                    alias is not None, direct_blocked,
                    f"non-`!` alias diverged from direct for body {body!r}: "
                    f"direct={direct_blocked} alias={alias is not None}",
                )
            with self.subTest(body=body, form="bang-shell"):
                alias_bang = g.scan_command(
                    "git -c alias.x='!git " + body + "' x"
                )
                self.assertEqual(
                    alias_bang is not None, direct_blocked,
                    f"`!`-shell alias diverged from direct for body {body!r}: "
                    f"direct={direct_blocked} alias={alias_bang is not None}",
                )

    def test_alias_flag_class_is_alias_abuse(self):
        # When the alias path blocks, the closed-enum is always alias_abuse
        # (the indirection wrapper class), regardless of the inner detector.
        for body in ("commit -n", "-C /tmp/o commit", "config core.hooksPath /x",
                     "-c core.hooksPath=/x commit", "push --no-verify"):
            with self.subTest(body=body):
                m = g.scan_command("git -c alias.x='" + body + "' x")
                self.assertIsNotNone(m)
                self.assertEqual(m.flag_class, g.FLAG_CLASS_ALIAS_ABUSE)

    def test_single_canonical_scanner_set_exists(self):
        # White-box: the unified detector tuple exists and includes the redirect
        # scanner that R6 was missing on the alias path.
        self.assertIn(g._scan_git_dir_redirect, g._GIT_INVOCATION_SCANNERS)
        self.assertIn(g._scan_no_verify, g._GIT_INVOCATION_SCANNERS)
        self.assertIn(g._scan_inline_c_and_alias, g._GIT_INVOCATION_SCANNERS)
        self.assertIn(g._scan_git_config_write, g._GIT_INVOCATION_SCANNERS)


# ---------------------------------------------------------------------------
# 3. Parse-failure fail-mode (MF-L) — bounded fail-CLOSED
# ---------------------------------------------------------------------------

class TestParseFailureFailClosed(TestEnvContext):

    def test_unparseable_git_command_fails_closed(self):
        m = g.scan_command('git commit --no-verify -m "unterminated')
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_PARSE_FAILURE)

    def test_unparseable_non_git_command_passes(self):
        # An awk one-liner with an unbalanced quote must NOT brick the session.
        self.assertIsNone(g.scan_command('awk "{print $1 unterminated'))

    def test_unparseable_git_in_chain_fails_closed(self):
        m = g.scan_command('ls ; git push "unterminated')
        self.assertIsNotNone(m)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_PARSE_FAILURE)

    def test_empty_and_blank_pass(self):
        self.assertIsNone(g.scan_command(""))
        self.assertIsNone(g.scan_command("   "))

    def test_unparseable_shell_alias_body_fails_closed(self):
        # S1: the outer `git -c alias.c='...' c` tokenizes cleanly, but the
        # `!`-shell alias BODY ('!git commit "unterminated') has an unbalanced
        # quote. The body re-tokenize raises ValueError; _alias_body_has_bypass
        # must fail-CLOSED (an unparseable git-intent alias body is a bypass),
        # not silently ALLOW.
        m = g.scan_command('git -c alias.c=\'!git commit "unterminated\' c')
        self.assertIsNotNone(m)

    def test_unparseable_nonbang_alias_body_fails_closed(self):
        # S1: same fail-CLOSE for the non-`!` git-IMPLIED alias body branch — a
        # git-subcommand alias body that cannot be lexed (unbalanced quote) is
        # treated as a bypass rather than ALLOWed.
        m = g.scan_command('git -c alias.c=\'commit "unterminated\' c')
        self.assertIsNotNone(m)


# ---------------------------------------------------------------------------
# 4. No command-byte leak (MF-G)
# ---------------------------------------------------------------------------

class TestNoSecretLeak(TestEnvContext):

    def test_reason_never_contains_secret_substring(self):
        secret = "SECRETTOKEN12345"
        cmd = (
            'git -c http.extraHeader="Bearer ' + secret + '" '
            "-c core.hooksPath=/dev/null commit -m x"
        )
        m = g.scan_command(cmd)
        self.assertIsNotNone(m)
        self.assertNotIn(secret, m.reason)
        self.assertEqual(m.flag_class, g.FLAG_CLASS_HOOKSPATH_INLINE)

    def test_no_8char_command_substring_in_emitted_event(self):
        """The emitted git_hook_bypass_blocked event must not carry any
        >=8-char substring of the malicious command (MF-G)."""
        secret = "Bearer SECRETTOKEN12345"
        cmd = (
            'git -c http.extraHeader="' + secret + '" '
            "-c core.hooksPath=/dev/null commit -m x"
        )
        audit_emit.emit_git_hook_bypass_blocked(
            flag_class=g.FLAG_CLASS_HOOKSPATH_INLINE,
            session_id="s",
            project="p",
        )
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        body = log.read_text(encoding="utf-8") if log.exists() else ""
        self.assertTrue(body, "expected an emitted event")
        # No >=8-char window of the command appears anywhere in the event.
        leaked = []
        for i in range(0, max(0, len(cmd) - 8 + 1)):
            window = cmd[i:i + 8]
            if window.strip() and window in body:
                leaked.append(window)
        self.assertEqual(leaked, [], f"command substrings leaked: {leaked[:5]}")
        # Sanity: the closed-enum flag_class IS present (and is not a command byte).
        event = json.loads(body.strip().splitlines()[-1])
        self.assertEqual(event["action"], "git_hook_bypass_blocked")
        self.assertEqual(event["flag_class"], g.FLAG_CLASS_HOOKSPATH_INLINE)
        self.assertNotIn("command", event)


# ---------------------------------------------------------------------------
# 5. emit_git_hook_bypass_blocked — closed-enum coercion + allowlist
# ---------------------------------------------------------------------------

class TestEmitterClosedEnum(TestEnvContext):

    def _last_event(self) -> Dict[str, Any]:
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        body = log.read_text(encoding="utf-8")
        return json.loads(body.strip().splitlines()[-1])

    def test_typed_emitter_accepts_every_flag_class(self):
        for fc in sorted(g.GIT_BYPASS_FLAG_CLASSES):
            audit_emit.emit_git_hook_bypass_blocked(flag_class=fc, session_id="s")
            self.assertEqual(self._last_event()["flag_class"], fc)

    def test_typed_emitter_coerces_unknown_flag_class(self):
        # A raw smuggled value must be coerced to parse_failure (never echoed).
        audit_emit.emit_git_hook_bypass_blocked(
            flag_class="rm -rf / --no-preserve-root", session_id="s",
        )
        ev = self._last_event()
        self.assertEqual(ev["flag_class"], "parse_failure")

    def test_emit_generic_path_scrubs_and_coerces(self):
        # Direct emit_generic caller smuggling a command body + raw flag value.
        audit_emit.emit_generic(
            "git_hook_bypass_blocked",
            session_id="s",
            project="p",
            flag_class="git push --no-verify SECRET",
            command="git push --no-verify SECRETTOKEN12345",
        )
        ev = self._last_event()
        self.assertEqual(ev["flag_class"], "parse_failure")
        self.assertNotIn("command", ev)
        body = json.dumps(ev)
        self.assertNotIn("SECRETTOKEN12345", body)

    def test_action_registered_and_count(self):
        self.assertIn("git_hook_bypass_blocked", audit_emit._KNOWN_ACTIONS)
        self.assertEqual(len(audit_emit._KNOWN_ACTIONS), 303)  # +2 PLAN-128 §7 (S217); +19 PLAN-133; +1 PLAN-135 W1 S3 (settings_tamper_detected); +6 PLAN-135 W2 (config_change ×2 + compaction ×2 + bash_input_rewritten [H5/ADR-154] + subagent_lifecycle_observed [H3]); +3 PLAN-135 ARC W5 (admin_key_lifecycle_event [o9] + statusline_sidecar_write [o4] + model_refusal_observed [o7]) — arc-consolidated 302; +1 PLAN-153 Wave E / ADR-159 (spawn_prompt_defense_gate) = 303

    def test_flag_class_sets_match_between_modules(self):
        # git_bypass.GIT_BYPASS_FLAG_CLASSES MUST equal the audit_emit mirror.
        self.assertEqual(
            set(g.GIT_BYPASS_FLAG_CLASSES),
            set(audit_emit._GIT_HOOK_BYPASS_FLAG_CLASSES),
        )

    def test_not_in_emit_generic_passthrough(self):
        # MF-G: must NEVER be a passthrough action.
        self.assertNotIn(
            "git_hook_bypass_blocked", audit_emit._EMIT_GENERIC_PASSTHROUGH,
        )


# ---------------------------------------------------------------------------
# 6. Dual-auth escape hatch (MF-E) — on AND off path
# ---------------------------------------------------------------------------

class _SnapshotPatch:
    """Context manager: override the trusted_env import-time snapshot."""

    def __init__(self, **kv: str) -> None:
        self._kv = kv
        self._saved: Optional[Dict[str, str]] = None

    def __enter__(self) -> "_SnapshotPatch":
        self._saved = dict(_trusted_env.ORIGINAL_CEO_ENV)
        _trusted_env.ORIGINAL_CEO_ENV.clear()
        _trusted_env.ORIGINAL_CEO_ENV.update(self._kv)
        return self

    def __exit__(self, *exc: Any) -> None:
        _trusted_env.ORIGINAL_CEO_ENV.clear()
        if self._saved is not None:
            _trusted_env.ORIGINAL_CEO_ENV.update(self._saved)


class TestEscapeHatch(TestEnvContext):

    _BYPASS_CMD = 'git commit --no-verify -m "x"'

    def test_off_path_no_env_still_blocks(self):
        with _SnapshotPatch():  # empty snapshot
            d = cbs.decide_command(self._BYPASS_CMD)
        self.assertFalse(d.allow)

    def test_off_path_missing_ack_still_blocks(self):
        with _SnapshotPatch(CEO_GIT_BYPASS_ALLOW="PLAN-124-ecc-harvest"):
            d = cbs.decide_command(self._BYPASS_CMD)
        self.assertFalse(d.allow)

    def test_off_path_wrong_ack_still_blocks(self):
        with _SnapshotPatch(
            CEO_GIT_BYPASS_ALLOW="PLAN-124-ecc-harvest",
            CEO_GIT_BYPASS_ALLOW_ACK="yes",
        ):
            d = cbs.decide_command(self._BYPASS_CMD)
        self.assertFalse(d.allow)

    def test_off_path_bad_ticket_still_blocks(self):
        with _SnapshotPatch(
            CEO_GIT_BYPASS_ALLOW="just because",
            CEO_GIT_BYPASS_ALLOW_ACK="I-ACCEPT",
        ):
            d = cbs.decide_command(self._BYPASS_CMD)
        self.assertFalse(d.allow)

    def test_on_path_valid_dual_auth_allows(self):
        for ticket in ("PLAN-124-ecc-harvest", "ADR-143-git-hook-bypass-guard"):
            with self.subTest(ticket=ticket):
                with _SnapshotPatch(
                    CEO_GIT_BYPASS_ALLOW=ticket,
                    CEO_GIT_BYPASS_ALLOW_ACK="I-ACCEPT",
                ):
                    d = cbs.decide_command(self._BYPASS_CMD)
                self.assertTrue(d.allow, f"valid dual-auth should ALLOW ({ticket})")

    def test_escape_hatch_does_not_unblock_non_git_destructive(self):
        # The escape hatch is git-bypass-only; rm -rf still blocked.
        with _SnapshotPatch(
            CEO_GIT_BYPASS_ALLOW="PLAN-124-ecc-harvest",
            CEO_GIT_BYPASS_ALLOW_ACK="I-ACCEPT",
        ):
            d = cbs.decide_command("rm -rf /tmp/x")
        self.assertFalse(d.allow)

    def test_live_os_environ_does_not_grant(self):
        # A late-set value in live os.environ (absent from the snapshot) must
        # NOT grant the bypass (ADR-040-AMEND-2 §Layer-1).
        # mock.patch.dict auto-restores os.environ so the live-env mutation
        # neither trips the test-env-hygiene checker nor leaks into later tests.
        with _SnapshotPatch():  # empty snapshot
            with mock.patch.dict(
                os.environ,
                {
                    "CEO_GIT_BYPASS_ALLOW": "PLAN-124-ecc-harvest",
                    "CEO_GIT_BYPASS_ALLOW_ACK": "I-ACCEPT",
                },
            ):
                d = cbs.decide_command(self._BYPASS_CMD)
        self.assertFalse(d.allow, "live os.environ must not grant the bypass")


# ---------------------------------------------------------------------------
# 7. check_bash_safety integration — decide_command + main emit
# ---------------------------------------------------------------------------

class TestDecideCommandIntegration(TestEnvContext):

    def test_decide_blocks_no_verify(self):
        d = cbs.decide_command('git commit --no-verify -m "x"')
        self.assertFalse(d.allow)
        self.assertIn("--no-verify", d.reason)

    def test_decide_allows_clean_commit(self):
        d = cbs.decide_command('git commit -m "clean"')
        self.assertTrue(d.allow)

    def test_decide_allows_push_dry_run(self):
        d = cbs.decide_command("git push -n origin main")
        self.assertTrue(d.allow)

    def test_decide_blocks_bash_c_shell_wrapper(self):
        # DEFECT-1: bash -c "git commit --no-verify ..." must block.
        d = cbs.decide_command('bash -c "git commit --no-verify -m x"')
        self.assertFalse(d.allow)

    def test_decide_blocks_sh_c_shell_wrapper(self):
        d = cbs.decide_command("sh -c 'git push --no-verify'")
        self.assertFalse(d.allow)

    def test_decide_blocks_config_env_channel(self):
        # DEFECT-2: --config-env core.hooksPath channel.
        d = cbs.decide_command("git --config-env=core.hooksPath=X commit -m ok")
        self.assertFalse(d.allow)

    def test_decide_allows_message_with_trigger_text(self):
        # DEFECT-4: a commit message containing trigger text must commit.
        self.assertTrue(cbs.decide_command('git commit -m "--no-verify"').allow)
        self.assertTrue(
            cbs.decide_command('git commit -m "fix ; not a chain"').allow
        )

    def test_credential_block_precedence_over_git_bypass(self):
        # A real-looking key + a bypass: credential block wins (and the git
        # emit is skipped so we don't double-handle). Just assert it blocks.
        d = cbs.decide_command(
            'git commit --no-verify -m "sk-ant-api03-' + "A" * 95 + '"'
        )
        self.assertFalse(d.allow)


class TestMainEmit(TestEnvContext):
    """End-to-end main(): stdin JSON -> decision + audit emit."""

    def _run_main(self, command: str) -> Dict[str, Any]:
        payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": command},
        })
        with mock.patch("sys.stdin", io.StringIO(payload)):
            out = io.StringIO()
            with mock.patch("sys.stdout", out):
                rc = cbs.main()
        self.assertEqual(rc, 0)
        return json.loads(out.getvalue().strip())

    def _events(self) -> List[Dict[str, Any]]:
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        out = []
        for line in log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def test_main_blocks_and_emits_flag_class(self):
        decision = self._run_main('git commit --no-verify -m "x"')
        self.assertEqual(decision.get("decision"), "block")
        events = [e for e in self._events()
                  if e.get("action") == "git_hook_bypass_blocked"]
        self.assertTrue(events, "expected a git_hook_bypass_blocked event")
        self.assertEqual(events[-1]["flag_class"], g.FLAG_CLASS_NO_VERIFY_COMMIT)

    def test_main_allows_clean_and_no_emit(self):
        decision = self._run_main('git commit -m "clean"')
        self.assertNotIn("decision", decision)  # allow == {}
        events = [e for e in self._events()
                  if e.get("action") == "git_hook_bypass_blocked"]
        self.assertEqual(events, [])

    def test_main_escape_hatch_allows_and_emits_escape_used(self):
        with _SnapshotPatch(
            CEO_GIT_BYPASS_ALLOW="PLAN-124-ecc-harvest",
            CEO_GIT_BYPASS_ALLOW_ACK="I-ACCEPT",
        ):
            decision = self._run_main('git commit --no-verify -m "x"')
            self.assertNotIn("decision", decision)  # allowed
            events = [e for e in self._events()
                      if e.get("action") == "git_hook_bypass_blocked"]
        self.assertTrue(events)
        self.assertEqual(events[-1]["flag_class"], g.FLAG_CLASS_ESCAPE_HATCH)


if __name__ == "__main__":
    import unittest
    unittest.main()
