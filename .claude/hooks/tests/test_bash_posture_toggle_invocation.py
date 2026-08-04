"""PLAN-165 NF-08 — posture-toggle INVOCATION guard (OQ1-redo).

The round-3 security review proved that `_e3_check_canonical_path_write`
matches only WRITE shapes: a canonical path in the *script* position of an
interpreter is not a write, so

    python3 .claude/scripts/night-mode.py on
    ./.claude/scripts/night-mode.py on

both returned ALLOW while three signed comments claimed the model rail
could not invoke the toggle. This file is the behavioral contract for the
new `_e4_check_posture_toggle_invocation` matcher that makes the claim
true.

Three test classes, in the order the review demanded:

* ``TestInvocationBlocked``  — POSITIVE controls: every plausible spelling
  of "run the toggle" is denied.
* ``TestWriteFormsStillBlocked`` — REGRESSION: the pre-existing Wave E.3
  write matchers keep blocking what they blocked before (the new matcher
  must not shadow or displace them).
* ``TestBenignAllowed`` — NEGATIVE controls: reading, testing, staging and
  discussing the file stay ALLOWED. `check_bash_safety` runs on EVERY Bash
  command, so a false positive here is operator DoS, not a safe default.

Author: NF-08 option-(a) implementation agent (S292).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# The hook lives at `.claude/hooks/check_bash_safety.py`; tests live at
# `.claude/hooks/tests/`.
_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from check_bash_safety import decide_command  # noqa: E402

# The posture toggle, as it is spelled in `_CANONICAL_GUARDS`.
TOGGLE = ".claude/scripts/night-mode.py"

# Non-quote helpers — keep the test source readable (mirrors the
# convention in test_check_bash_safety_canonical_matrix.py).
DQ = chr(34)  # "
SQ = chr(39)  # '

# A plausible absolute spelling. The matcher is suffix-based, so it does
# NOT depend on CLAUDE_PROJECT_DIR being set (deliberate: the hook must
# not need env state to recognise its own governance surface).
ABS = "/Users/dev/repo/" + TOGGLE


# ---------------------------------------------------------------------------
# POSITIVE controls — invocation must be DENIED.
# Each tuple: (slug, command).
# ---------------------------------------------------------------------------
INVOCATION_VECTORS = [
    # --- the three forms the round-3 review probed ---------------------
    ("review_form_1_python3_relative", "python3 " + TOGGLE + " on"),
    ("review_form_2_dot_slash_exec", "./" + TOGGLE + " on"),
    ("review_form_3_bash_c_body", 'bash -c "python3 ' + TOGGLE + ' on"'),
    # --- subcommand does not matter: the SCRIPT is the surface ---------
    ("subcommand_off", "python3 " + TOGGLE + " off"),
    ("subcommand_status", "python " + TOGGLE + " status"),
    ("subcommand_discard", "python3 " + TOGGLE + " off --discard-snapshot"),
    ("no_subcommand", "python3 " + TOGGLE),
    # --- interpreter spellings -----------------------------------------
    ("python_versioned", "python3.11 " + TOGGLE + " on"),
    ("interpreter_abs_path", "/usr/bin/python3 " + TOGGLE + " on"),
    ("interpreter_flag_no_value", "python3 -u " + TOGGLE + " on"),
    ("interpreter_flag_with_value", "python3 -X importtime " + TOGGLE + " on"),
    ("interpreter_ddash", "python3 -- " + TOGGLE + " on"),
    ("interpreter_runpy", "python3 -m runpy " + TOGGLE + " on"),
    ("shell_runner_bash", "bash " + TOGGLE + " on"),
    ("shell_runner_sh", "sh " + TOGGLE),
    # --- path spellings -------------------------------------------------
    ("bare_relative_cmd_word", TOGGLE + " on"),
    ("absolute_direct_exec", ABS + " on"),
    ("absolute_via_interpreter", "python3 " + ABS + " on"),
    ("dotdot_normalised", "python3 .claude/scripts/../scripts/night-mode.py on"),
    ("double_quoted_path", "python3 " + DQ + TOGGLE + DQ + " on"),
    ("single_quoted_path", "python3 " + SQ + TOGGLE + SQ + " on"),
    ("partially_quoted_path", "python3 .claude/scripts/" + DQ + "night-mode.py" + DQ + " on"),
    ("basename_after_cd", "cd .claude/scripts && python3 night-mode.py on"),
    # --- prefix runners --------------------------------------------------
    ("prefix_exec", "exec python3 " + TOGGLE + " on"),
    ("prefix_command", "command python3 " + TOGGLE + " on"),
    ("prefix_nohup", "nohup python3 " + TOGGLE + " on"),
    ("prefix_nohup_direct_bg", "nohup ./" + TOGGLE + " off &"),
    ("prefix_env_assignment", "env FOO=1 python3 " + TOGGLE + " on"),
    ("prefix_bare_env_assignment", "FOO=1 python3 " + TOGGLE + " on"),
    ("prefix_sudo", "sudo python3 " + TOGGLE + " on"),
    ("prefix_timeout_duration", "timeout 5 python3 " + TOGGLE + " on"),
    ("prefix_nice", "nice -n 10 python3 " + TOGGLE + " on"),
    ("prefix_stacked", "nohup env FOO=1 python3 " + TOGGLE + " on"),
    # --- chaining / segment position ------------------------------------
    ("second_segment_and", "echo hi && python3 " + TOGGLE + " on"),
    ("second_segment_semicolon", "echo hi ; python3 " + TOGGLE + " on"),
    ("second_segment_or", "false || python3 " + TOGGLE + " on"),
    ("pipe_into_xargs", "echo on | xargs python3 " + TOGGLE),
    ("subshell", "(python3 " + TOGGLE + " on)"),
    # --- shell body forms (division of labour: _e3 blob-scan owns -c) ----
    ("sh_c_body", "sh -c " + SQ + "python3 " + TOGGLE + " on" + SQ),
    ("eval_body", "eval " + SQ + "python3 " + TOGGLE + " on" + SQ),
    ("shell_heredoc", "bash <<EOF\npython3 " + TOGGLE + " on\nEOF"),
    # --- variable indirection: shlex does not expand, so the path is only
    #     visible in the ASSIGNMENT. Blocked ONLY together with an execution
    #     position — see the ALLOW twin `var_assigned_then_read` below.
    ("var_then_interpreter", "S=" + TOGGLE + " ; python3 $S on"),
    ("var_then_direct_exec", "S=" + TOGGLE + " ; $S on"),
    ("var_same_command", "S=" + TOGGLE + " python3 $S on"),
]

# ---------------------------------------------------------------------------
# CODEX S292 P1-A — spellings that name the script WITHOUT the raw command
# containing the literal basename. The first implementation short-circuited on
# a raw-substring pre-filter, so every one of these returned ALLOW while the
# shell resolved them to the real file.
#
# Two sub-classes:
#   • concatenation — the shell glues the token back together (quotes,
#     empty quotes, backslash escapes). shlex normalises it; the raw string
#     never contains `night-mode.py`.
#   • case variance — on APFS (this repo's default platform, and the
#     platform PLAN-162 S1 `PLAN162_FIX_CASEFOLD` was raised against),
#     `NIGHT-MODE.PY` IS `night-mode.py`.
#   • glob — `night-mod?.py` is a THIRD spelling of the same file. Not in
#     the codex finding, folded in here because it is the same class: a
#     token that resolves to the guarded script without spelling it.
# ---------------------------------------------------------------------------
CONCAT_AND_CASE_VECTORS = [
    # --- concatenation ---------------------------------------------------
    ("concat_double_quotes", "python3 .claude/scripts/night" + DQ + "-" + DQ + "mode.py on"),
    ("concat_single_quotes", "python3 .claude/scripts/night" + SQ + "-" + SQ + "mode.py on"),
    ("concat_empty_quotes", "python3 .claude/scripts/night" + SQ + SQ + "-mode.py on"),
    ("concat_backslash_escape", "python3 .claude/scripts/night\\-mode.py on"),
    ("concat_quoted_dir_half", "python3 " + DQ + ".claude/scr" + DQ + "ipts/night-mode.py on"),
    ("concat_direct_exec", "./.claude/scripts/night" + DQ + "-" + DQ + "mode.py off"),
    # --- case variance (APFS) --------------------------------------------
    ("case_upper_basename", "python3 .claude/scripts/NIGHT-MODE.PY on"),
    ("case_mixed_basename", "python3 .claude/scripts/Night-Mode.py on"),
    ("case_upper_whole_path", "python3 .CLAUDE/SCRIPTS/NIGHT-MODE.PY on"),
    ("case_direct_exec", "./.claude/scripts/Night-Mode.py on"),
    ("case_bare_basename_after_cd", "cd .claude/scripts && python3 NIGHT-MODE.py on"),
    ("case_plus_concat", "python3 .claude/scripts/NIGHT" + DQ + "-" + DQ + "MODE.PY on"),
    # --- glob (same class, folded in deliberately) ------------------------
    ("glob_question_mark", "python3 .claude/scripts/night-mod?.py on"),
    ("glob_star_in_stem", "python3 .claude/scripts/night-*.py on"),
    ("glob_bracket_class", "python3 .claude/scripts/night-mod[de].py on"),
]

# ---------------------------------------------------------------------------
# CODEX S292 P1-B — value-bearing flags on a PREFIX RUNNER. The first
# implementation skipped the flag but then treated the flag's VALUE as the
# command word and stopped examining the rest of the chain, so everything
# after it (the interpreter, the script) was never looked at.
#
# `env -u FOO` and `sudo -u root` are the two codex named; the others are the
# same defect reached through other runners, and the `--unknown-*` pair pins
# the FAIL-CLOSED default for a flag the table does not know.
# ---------------------------------------------------------------------------
PREFIX_VALUE_FLAG_VECTORS = [
    ("env_unset_flag", "env -u FOO python3 " + TOGGLE + " on"),
    ("env_unset_long", "env --unset FOO python3 " + TOGGLE + " on"),
    ("env_chdir_flag", "env -C /tmp python3 " + TOGGLE + " on"),
    ("env_unset_direct_exec", "env -u FOO ./" + TOGGLE + " on"),
    ("sudo_user_flag", "sudo -u root python3 " + TOGGLE + " on"),
    ("sudo_user_long", "sudo --user=root python3 " + TOGGLE + " on"),
    ("sudo_user_direct_exec", "sudo -u root ./" + TOGGLE + " off"),
    ("sudo_group_flag", "sudo -g wheel python3 " + TOGGLE + " on"),
    ("timeout_signal_flag", "timeout -s KILL 5 python3 " + TOGGLE + " on"),
    ("xargs_replstr_flag", "echo on | xargs -I {} python3 " + TOGGLE + " {}"),
    ("stdbuf_bufdef_flag", "stdbuf -o L python3 " + TOGGLE + " on"),
    ("stacked_runners_with_values",
     "nohup sudo -u root env -u FOO python3 " + TOGGLE + " on"),
    # FAIL-CLOSED default: a flag the table does not carry is AMBIGUOUS, so
    # the token after it is examined as a command word too.
    ("unknown_flag_then_interpreter", "env --frobnicate VAL python3 " + TOGGLE + " on"),
    ("unknown_flag_then_direct_exec", "sudo --frobnicate VAL ./" + TOGGLE + " on"),
]

# ---------------------------------------------------------------------------
# SELF-REVIEW of the codex fix (S292) — the other half of the P1-A class, and
# the indirection the original matcher never covered. All EIGHT were verified
# to actually execute on this platform before being pinned here (`PYTHON3
# probe.py` runs, `$(echo probe.py)` runs), so they are bypasses, not theory.
#
#   • command-NAME case variance: folding the PATH but not the interpreter or
#     the prefix runner closes half the class — PATH lookup is case-insensitive
#     on APFS too.
#   • command SUBSTITUTION: `python3 $(echo <toggle>) on` executes the toggle,
#     but the walk saw `echo` settle as a command word and the path became its
#     argument. Same conjunctive shape as the `$S` variable rule the matcher
#     already had: substitution in an EXECUTION position + toggle inside it.
# ---------------------------------------------------------------------------
CASE_FOLDED_COMMAND_VECTORS = [
    ("upper_interpreter", "PYTHON3 " + TOGGLE + " on"),
    ("mixed_interpreter", "Python3 " + TOGGLE + " on"),
    ("upper_absolute_interpreter", "/usr/bin/PYTHON3 " + TOGGLE + " on"),
    ("upper_shell_runner", "BASH " + TOGGLE + " on"),
    ("upper_prefix_runner", "SUDO -u root python3 " + TOGGLE + " on"),
    ("upper_env_runner", "ENV -u FOO python3 " + TOGGLE + " on"),
]

SUBSTITUTION_VECTORS = [
    ("subst_operand_of_interpreter", "python3 $(echo " + TOGGLE + ") on"),
    ("subst_backticks", "python3 " + chr(96) + "echo " + TOGGLE + chr(96) + " on"),
    ("subst_in_command_position", "$(echo ./" + TOGGLE + ") off"),
    ("subst_under_prefix_runner", "sudo python3 $(echo " + TOGGLE + ") on"),
]

# ---------------------------------------------------------------------------
# CODEX S292 r2 P1 — EXECUTABLE ALIASES of the toggle.
#
# The matcher above recognises tokens whose SPELLING resolves to the guarded
# path. A LINK defeats spelling by construction: after
# `ln -s .claude/scripts/night-mode.py /tmp/nm`, the command `python3 /tmp/nm
# on` names nothing the matcher can recognise — and it WORKS, because
# `REPO_ROOT = Path(__file__).resolve().parents[2]` follows the link back into
# this repository. Measured, not theorised (S292 r2 probe): the alias wrote
# `permissions.defaultMode: acceptEdits` into the target repo's overlay and
# printed `result=applied`.
#
# The EXECUTION side of that bypass cannot be closed here — the matcher would
# have to `stat()` an attacker-supplied path on every Bash command (symlink
# loops, TOCTOU, network mounts), which this hook deliberately does not do.
# It is closed in the script itself by the self-path guard
# (`nf08-self-path-guard.patch`). What this matcher owns is the CREATION of a
# second live entry point, which is the only half a string matcher can see.
#
# Scope, deliberately narrow: LINKS only (`ln`, `ln -s`). A COPY is a
# SNAPSHOT, not a second entry point — the copy is inert (the self-path guard
# refuses to run it), and blocking `cp` would break two real workflows that
# were observed in this repo: backing the file up before editing it, and
# `install.sh`/`upgrade.sh` copying the toggle into an ADOPTER repo's own
# canonical location, where it is legitimately that repo's toggle.
# ---------------------------------------------------------------------------
ALIAS_CREATION_VECTORS = [
    ("alias_symlink", "ln -s " + TOGGLE + " /tmp/nm"),
    ("alias_symlink_force", "ln -sf " + TOGGLE + " /tmp/nm"),
    ("alias_symlink_long_flag", "ln --symbolic " + TOGGLE + " /tmp/nm"),
    ("alias_hardlink", "ln " + TOGGLE + " /tmp/nm"),
    ("alias_symlink_into_path", "ln -s " + ABS + " /usr/local/bin/night-mode"),
    ("alias_then_run", "ln -s " + TOGGLE + " /tmp/nm && python3 /tmp/nm on"),
    ("alias_basename_after_cd", "cd .claude/scripts && ln -s night-mode.py /tmp/nm"),
    ("alias_under_prefix_runner", "sudo ln -s " + TOGGLE + " /usr/local/bin/nm"),
    ("alias_case_folded_ln", "LN -s " + TOGGLE + " /tmp/nm"),
    ("alias_case_folded_path", "ln -s .claude/scripts/NIGHT-MODE.PY /tmp/nm"),
    ("alias_concat_path", "ln -s .claude/scripts/night" + DQ + "-" + DQ + "mode.py /tmp/nm"),
    ("alias_var_indirection", "S=" + TOGGLE + " ; ln -s $S /tmp/nm"),
    ("alias_second_segment", "echo hi ; ln -s " + TOGGLE + " /tmp/nm"),
    # The toggle as the LINK TARGET (replacing it with a link) is a WRITE to a
    # canonical path — already denied by `_e3`. Pinned here so a refactor that
    # narrows `_e3` cannot silently open it.
    ("alias_toggle_as_destination", "ln -s /tmp/evil.py " + TOGGLE),
]

# ---------------------------------------------------------------------------
# CODEX S292 r3 P1-A — NEWLINE is a Bash command separator.
#
# `shlex` classifies a newline as WHITESPACE, and the walk reset
# `at_cmd_word` only on `_E3_TERMINATORS`. So a second LINE — which Bash
# executes as its own command — was flattened into the first command's
# argument list and its command word was never examined:
#
#     echo ok
#     python3 .claude/scripts/night-mode.py on      <- returned ALLOW
#
# Measured before the fix: 3 of the newline vectors below returned ALLOW.
#
# The same normalisation pass covers the OTHER half of the class, found while
# probing the finding: `\<newline>` is a LINE CONTINUATION that Bash REMOVES,
# but shlex's escape handling turns it into a literal-newline WORD, which
# settled as a bogus command word and pushed the real script operand into a
# non-command position (`python3 \<NL> <toggle> on` — also ALLOW).
#
# Newlines INSIDE quotes stay literal — see `newline_inside_single_quotes`
# and `newline_inside_double_quotes` in ALLOW_VECTORS, which are the negative
# controls proving the normaliser is quote-aware rather than a blind
# `str.replace`.
# ---------------------------------------------------------------------------
NEWLINE_SEPARATOR_VECTORS = [
    # --- the finding's own vector ----------------------------------------
    ("newline_second_line_interpreter", "echo ok\npython3 " + TOGGLE + " on"),
    ("newline_second_line_direct_exec", "ls -la\n./" + TOGGLE + " on"),
    ("newline_crlf_line_ending", "echo ok\r\npython3 " + TOGGLE + " on"),
    # --- the toggle on a line that is neither first nor last --------------
    ("newline_third_line", "cd /tmp\necho hi\npython3 " + TOGGLE + " on"),
    ("newline_first_line", "python3 " + TOGGLE + " on\necho done"),
    ("newline_after_and_operator", "echo hi &&\npython3 " + TOGGLE + " on"),
    ("newline_after_semicolon", "echo hi ;\npython3 " + TOGGLE + " on"),
    # --- every OTHER rail must survive the line boundary too --------------
    ("newline_then_prefix_runner", "echo ok\nsudo -u root python3 " + TOGGLE + " on"),
    ("newline_then_alias_creation", "echo ok\nln -s " + TOGGLE + " /tmp/nm"),
    ("newline_then_substitution", "echo ok\npython3 $(echo " + TOGGLE + ") on"),
    ("newline_then_var_indirection", "S=" + TOGGLE + "\npython3 $S on"),
    ("newline_then_case_folded", "echo ok\nPYTHON3 " + TOGGLE + " on"),
    # --- line CONTINUATION: Bash removes `\<newline>` entirely -------------
    ("line_continuation_before_script", "python3 \\\n  " + TOGGLE + " on"),
    ("line_continuation_in_prefix_chain", "sudo -u root \\\n  python3 " + TOGGLE + " on"),
    ("line_continuation_before_direct_exec", "nohup \\\n  ./" + TOGGLE + " on"),
]

# ---------------------------------------------------------------------------
# CODEX S292 r3 P1-B — paths BUILT BY EXPANSION.
#
# The execution-position check recognised literal paths, and variables whose
# assigned value was ALREADY the complete toggle path. It did not recognise a
# token that the SHELL assembles into the toggle path at expansion time:
#
#     X=; python3 .claude/scripts/night${X}-mode.py on    <- returned ALLOW
#
# Bash expands `${X}` to the empty string, runs the canonical file, and the
# script's own self-path guard accepts it because it IS the canonical file.
#
# A hook cannot evaluate expansions, so the rule is fail-CLOSED on the shape,
# per CLAUDE.md §"fail-closed on input" and the `_e3` whole-command parse gate
# (PLAN-152 debate C4): the matcher re-scans an EXPANSION SKELETON in which
# every expansion is replaced by a `*` wildcard, and denies when the skeleton
# could still resolve to the toggle. "Could resolve" reuses the glob rule
# already in the matcher, LITERAL FLOOR included — which is what keeps
# `python3 $SCRIPT` (skeleton `python3 *`) allowed instead of denying every
# variable-driven interpreter call in the repo.
#
# The skeleton pass runs ONLY after the literal pass returns allow, and it
# walks the SAME execution-position discipline — so reads stay reads. The
# ALLOW twins below are the controls for that.
# ---------------------------------------------------------------------------
EXPANSION_BUILT_PATH_VECTORS = [
    # --- the finding's own vector -----------------------------------------
    ("expansion_empty_var_in_basename",
     "X=; python3 .claude/scripts/night${X}-mode.py on"),
    ("expansion_var_in_basename_as_cmd_word",
     "X=; ./.claude/scripts/night${X}-mode.py on"),
    # --- the other expansion syntaxes, same class -------------------------
    ("expansion_backtick_in_basename",
     "python3 .claude/scripts/night" + chr(96) + "echo -" + chr(96) + "mode.py on"),
    ("expansion_dollar_paren_in_basename",
     "python3 .claude/scripts/night$(echo -)mode.py on"),
    ("expansion_bare_var_in_basename",
     "python3 .claude/scripts/night$Xmode.py on"),
    ("expansion_braced_var_mid_stem",
     "python3 .claude/scripts/${P}night-mode.py on"),
    # --- through every other rail -----------------------------------------
    ("expansion_under_prefix_runner",
     "X=; sudo -u root python3 .claude/scripts/night${X}-mode.py on"),
    ("expansion_in_alias_creation",
     "X=; ln -s .claude/scripts/night${X}-mode.py /tmp/nm"),
    ("expansion_after_newline",
     "echo ok\nX=; python3 .claude/scripts/night${X}-mode.py on"),
    ("expansion_plus_case_variance",
     "X=; python3 .claude/scripts/NIGHT${X}-MODE.PY on"),
    ("expansion_plus_glob",
     "X=; python3 .claude/scripts/night${X}-mod?.py on"),
    # --- expansion in the DIRECTORY half. Already denied by the basename
    #     rule before this fix; pinned so a refactor of the skeleton pass
    #     cannot quietly narrow it.
    ("expansion_in_directory_half",
     "python3 ${D}/.claude/scripts/night-mode.py on"),
    # --- ANSI-C quoting. NOT in the codex finding: found by adversarially
    #     probing this fix, and verified by EXECUTION before being pinned —
    #     `python3 .claude/scripts/night$'\x2d'mode.py on` printed
    #     "TOGGLE RAN" on this platform. Bash decodes `\x2d` to `-`; shlex
    #     does not implement ANSI-C quoting, so the walk saw a literal
    #     `night$-mode.py` and matched nothing.
    ("ansi_c_quoting_builds_the_dash",
     "python3 .claude/scripts/night$" + SQ + "\\x2d" + SQ + "mode.py on"),
    ("ansi_c_quoting_as_cmd_word",
     "./.claude/scripts/night$" + SQ + "\\055" + SQ + "mode.py on"),
    ("ansi_c_quoting_whole_basename",
     "python3 .claude/scripts/$" + SQ + "night-mode.py" + SQ + " on"),
    ("locale_translation_quoting",
     "python3 .claude/scripts/night$" + DQ + "-" + DQ + "mode.py on"),
]

# ---------------------------------------------------------------------------
# CODEX S292 r4 P1 — BRACE EXPANSION.
#
# The matcher handled `$`-expansions by wildcarding them. It did not handle
# `{…}` at all, and bash rewrites braces BEFORE anything runs. Every vector
# below was executed against GNU bash 3.2.57 (arm64-apple-darwin25) in a
# sandbox repo whose toggle appends to a marker FILE, and every one of them
# ran the toggle while the matcher returned ALLOW.
#
# The sharpest is `night-mode.p{y..y}`, which was NOT in the finding: a range
# whose endpoints are equal expands to ONE word, so the command bash executes
# is byte-identical to the plain literal deny case — measured argv
# `['.claude/scripts/night-mode.py', 'on']` from BOTH spellings. Nothing about
# the bypass survives to run time for a matcher to notice afterwards.
#
# Wildcarding `{…}` the way `${…}` is wildcarded does NOT work here and the
# floor is why: `{night-mode,other}.py` -> `*.py` carries 3 literal characters,
# under `_E4_GLOB_MIN_LITERALS`, and would be ALLOWED. Brace expansion is
# static text, so the matcher EXPANDS it instead — the same call the `$'…'`
# decode branch makes, for the same reason.
# ---------------------------------------------------------------------------
BRACE_EXPANSION_VECTORS = [
    # --- one word out, byte-identical argv (the strongest form) -----------
    ("brace_range_single_word",
     "python3 .claude/scripts/night-mode.p{y..y} on"),
    ("brace_range_single_word_cmd_word",
     "./.claude/scripts/night-mode.p{y..y} on"),
    # --- the finding's own forms ------------------------------------------
    ("brace_comma_list_with_decoy",
     "python3 .claude/scripts/{night-mode,other}.py on"),
    ("brace_empty_pair",
     "python3 .claude/scripts/night-mode{,}.py on"),
    ("brace_infix_alternation",
     "python3 .claude/scripts/night{-,x}mode.py on"),
    ("brace_extension_alternation",
     "python3 .claude/scripts/night-mode.{py,txt} on"),
    # --- the toggle is NOT the first expanded word. Conservative deny: which
    #     expanded word becomes the script depends on the runner and its
    #     flags, and being wrong there permissively is the unsafe direction.
    ("brace_toggle_not_first",
     "python3 .claude/scripts/{other,night-mode}.py on"),
    ("brace_nested_group",
     "python3 .claude/scripts/{a,{b,night-mode}}.py on"),
    # --- through every other rail -----------------------------------------
    ("brace_under_prefix_runner",
     "env -u FOO python3 .claude/scripts/night-mode{,}.py on"),
    ("brace_under_sudo_value_flag",
     "sudo -u root python3 .claude/scripts/night-mode{,}.py on"),
    ("brace_in_alias_creation",
     "ln -s .claude/scripts/night-mode{,}.py /tmp/nm"),
    ("brace_after_newline",
     "echo ok\npython3 .claude/scripts/night-mode{,}.py on"),
    ("brace_plus_case_variance",
     "python3 .claude/scripts/NIGHT-MODE.P{Y..Y} on"),
    ("brace_plus_glob",
     "python3 .claude/scripts/night-mod{?,x}.py on"),
    ("brace_in_directory_half",
     "python3 {.,x}/.claude/scripts/night-mode.py on"),
    ("brace_bare_basename_after_cd",
     "cd .claude/scripts && python3 night-mode{,}.py on"),
    # --- BUDGET: a token engineered to blow the enumeration budget is
    #     refused rather than guessed at (fail-CLOSED on input).
    ("brace_bomb_exceeds_word_budget",
     "python3 .claude/scripts/{%s}.py on"
     % ",".join("d%d" % i for i in range(5000))),
]

# ---------------------------------------------------------------------------
# UNKNOWN LAUNCHERS — codex S292 review round 5, P1.
#
# `xcrun python3 <toggle> on` was ALLOWED: `xcrun` is not in
# `_E4_PREFIX_RUNNERS`, so the walk settled on it and never looked at
# `python3` again. That is the THIRD failure of the same closed set in three
# rounds (r2 `env`/`sudo`, r4 braces, r5 `xcrun`), which is the S291 lesson
# arriving on schedule — and it errs toward ALLOW, the silent direction.
#
# Measured on this machine before the fix (probe output in the ceremony
# NOTES): 22/22 of these returned ALLOW. Of the launchers that EXIST here,
# every one executes its operand — `xcrun python3 x.py`, `xcrun ./x.py`,
# `arch -x86_64 python3 x.py`, `caffeinate python3 x.py`,
# `script -q /dev/null python3 x.py` all printed the dummy's output — and
# the toggle ships mode 100755, so the direct-exec spellings are live too.
# The script's own NF-08b self-path guard PASSES for all of them (the file
# that runs IS the canonical one), so this matcher is the ONLY rail here.
#
# The fix is structural: after an unrecognised command word the walk keeps
# testing tokens for INTERPRETER family, so the launcher's NAME stops
# mattering. The absent-here launchers below (`unbuffer`, `taskset`,
# `firejail`, `parallel`, `systemd-run`, …) are pinned precisely because
# nobody enumerated them — they are the next round's finding, pre-empted.
# ---------------------------------------------------------------------------
UNKNOWN_LAUNCHER_VECTORS = [
    # present + measured on this platform
    ("xcrun_python3", "xcrun python3 " + TOGGLE + " on"),
    ("xcrun_sdk_long_flag", "xcrun --sdk macosx python3 " + TOGGLE + " on"),
    ("xcrun_sdk_short_flag", "xcrun -sdk macosx python3 " + TOGGLE + " on"),
    ("xcrun_run_mode", "xcrun -run python3 " + TOGGLE + " on"),
    ("xcrun_direct_exec", "xcrun ./" + TOGGLE + " on"),
    ("xcrun_shell_runner", "xcrun bash -x " + TOGGLE + " on"),
    ("arch_python3", "arch -x86_64 python3 " + TOGGLE + " on"),
    ("arch_direct_exec", "arch -arm64 ./" + TOGGLE + " on"),
    ("caffeinate_python3", "caffeinate python3 " + TOGGLE + " on"),
    ("caffeinate_timeout_flag", "caffeinate -t 60 python3 " + TOGGLE + " on"),
    ("script_python3", "script -q /dev/null python3 " + TOGGLE + " on"),
    ("sandbox_exec_python3", "sandbox-exec -f p.sb python3 " + TOGGLE + " on"),
    # NOT present here, deliberately NOT enumerated in the runner set — the
    # structural rail is what must catch these.
    ("unbuffer_python3", "unbuffer python3 " + TOGGLE + " on"),
    ("proxychains_python3", "proxychains4 python3 " + TOGGLE + " on"),
    ("torify_python3", "torify python3 " + TOGGLE + " on"),
    ("taskset_python3", "taskset -c 0 python3 " + TOGGLE + " on"),
    ("firejail_python3", "firejail --quiet python3 " + TOGGLE + " on"),
    ("systemd_run_python3", "systemd-run --user python3 " + TOGGLE + " on"),
    ("watch_python3", "watch -n 1 python3 " + TOGGLE + " on"),
    ("parallel_python3", "parallel python3 " + TOGGLE + " ::: on"),
    ("flock_python3", "flock /tmp/l python3 " + TOGGLE + " on"),
    ("gdb_args_python3", "gdb --args python3 " + TOGGLE + " on"),
    ("strace_python3", "strace -f python3 " + TOGGLE + " on"),
    ("valgrind_python3", "valgrind --leak-check=full python3 " + TOGGLE + " on"),
    ("chroot_python3", "chroot /jail python3 " + TOGGLE + " on"),
    ("numactl_python3", "numactl --cpunodebind=0 python3 " + TOGGLE + " on"),
    # `git` is BOTH a reader and a launcher — the single most important
    # vector here, because it is the reason no "reader" allow-list was added
    # to soften the false positive below. `git bisect run` executes its
    # operand; a carve-out that treated `git` as a reader would have handed
    # back exactly the bypass this round closes.
    ("git_bisect_run", "git bisect run python3 " + TOGGLE + " on"),
    # chained launchers, known and unknown mixed in both orders
    ("xcrun_then_env", "xcrun env -u FOO python3 " + TOGGLE + " on"),
    ("env_then_xcrun", "env -u FOO xcrun python3 " + TOGGLE + " on"),
    ("nohup_then_unknown", "nohup frobnicate-9000 python3 " + TOGGLE + " on"),
    # a launcher that reaches the shell through a VARIABLE — the name is not
    # even in the command text.
    ("launcher_in_variable", "R=xcrun ; $R python3 " + TOGGLE + " on"),
]

INVOCATION_VECTORS = (
    INVOCATION_VECTORS
    + CONCAT_AND_CASE_VECTORS
    + PREFIX_VALUE_FLAG_VECTORS
    + CASE_FOLDED_COMMAND_VECTORS
    + SUBSTITUTION_VECTORS
    + ALIAS_CREATION_VECTORS
    + NEWLINE_SEPARATOR_VECTORS
    + EXPANSION_BUILT_PATH_VECTORS
    + BRACE_EXPANSION_VECTORS
    + UNKNOWN_LAUNCHER_VECTORS
)

# ---------------------------------------------------------------------------
# REGRESSION — the Wave E.3 WRITE matchers must keep blocking.
# ---------------------------------------------------------------------------
WRITE_VECTORS = [
    ("redirect_writer", "echo x > " + TOGGLE),
    ("redirect_overlay", "echo x > .claude/settings.local.json"),
    ("redirect_marker", "echo x > .claude/state/night-mode.json"),
    ("cp_over_writer", "cp /tmp/evil " + TOGGLE),
    ("rm_writer", "rm " + TOGGLE),
    ("sed_inplace_writer", "sed -i s/a/b/ " + TOGGLE),
    ("tee_writer", "echo x | tee " + TOGGLE),
    ("mv_writer", "mv /tmp/evil " + TOGGLE),
]

# ---------------------------------------------------------------------------
# NEGATIVE controls — must stay ALLOWED.
# check_bash_safety runs on EVERY Bash command; a false positive here is
# operator DoS.
# ---------------------------------------------------------------------------
ALLOW_VECTORS = [
    # reading the writer
    ("cat_the_writer", "cat " + TOGGLE),
    ("less_the_writer", "less " + TOGGLE),
    ("head_the_writer", "head -50 " + TOGGLE),
    ("wc_the_writer", "wc -l " + TOGGLE),
    ("grep_in_the_writer", "grep -n _RESTORABLE_MODES " + TOGGLE),
    ("grep_recursive_for_path", "grep -rn night-mode.py .claude/"),
    # git plumbing over the writer + the command doc
    ("git_add_command_doc", "git add .claude/commands/night-mode.md"),
    ("git_add_writer", "git add " + TOGGLE),
    ("git_log_writer", "git log --oneline -- " + TOGGLE),
    ("git_diff_writer", "git diff " + TOGGLE),
    ("git_show_writer", "git show HEAD:" + TOGGLE),
    # testing
    ("pytest_night_mode_tests", "python3 -m pytest .claude/scripts/tests/test_night_mode.py"),
    ("pytest_night_mode_tests_k", "python3 -m pytest .claude/scripts/tests/test_night_mode.py -k on"),
    ("pytest_ceo_boot_night_mode", "python3 -m pytest .claude/scripts/tests/test_ceo_boot_night_mode.py"),
    ("pytest_hooks_dir", "python3 -m pytest .claude/hooks/tests/ -q"),
    ("pytest_module_on_writer_path", "python3 -m pytest " + TOGGLE),
    # a DIFFERENT script under the same directory
    ("other_script_invocation", "python3 .claude/scripts/ceo-boot.py"),
    ("other_script_nightly", "python3 .claude/scripts/nightly-proposals.py"),
    # merely talking about it
    ("echo_the_command", "echo " + SQ + "python3 " + TOGGLE + " on" + SQ),
    # variable indirection WITHOUT an execution position — reading is not
    # invoking. The twin of `var_then_interpreter` above; together they pin
    # the conjunctive rule (assignment AND execution), not a path blocklist.
    ("var_assigned_then_read", "S=" + TOGGLE + " ; cat $S"),
    ("var_assigned_then_grep", "S=" + TOGGLE + " ; grep -n MODES $S"),
    ("var_holds_other_script", "S=.claude/scripts/ceo-boot.py ; grep -n night-mode.py $S"),
    # unrelated traffic
    ("ls_scripts", "ls .claude/scripts/"),
    ("plain_echo", "echo hello"),
    ("git_status", "git status --porcelain"),
    # --- FP twins of the codex P1-B fix ---------------------------------
    # Reading the writer THROUGH a prefix runner with a value-bearing flag.
    # These are the exact shapes the chain-walk must not over-block: the
    # flag's value is consumed, the READER settles as the command word, and
    # its operand is never examined as an execution position.
    ("sudo_user_flag_then_cat", "sudo -u root cat " + TOGGLE),
    ("sudo_user_flag_then_grep", "sudo -u root grep -n MODES " + TOGGLE),
    ("env_unset_flag_then_cat", "env -u FOO cat " + TOGGLE),
    ("env_chdir_then_head", "env -C /tmp head -20 " + TOGGLE),
    # A KNOWN BOOLEAN flag must not be mistaken for a value-bearing one —
    # otherwise the reader gets skipped and its operand reads as a command.
    ("sudo_bool_flag_then_cat", "sudo -E cat " + TOGGLE),
    ("sudo_bool_cluster_then_cat", "sudo -En cat " + TOGGLE),
    ("xargs_replstr_then_cat", "echo x | xargs -I {} cat " + TOGGLE),
    ("nohup_then_cat", "nohup cat " + TOGGLE),
    ("sudo_user_flag_then_git", "sudo -u root git log --oneline -- " + TOGGLE),
    ("timeout_then_pytest", "timeout -s KILL 60 python3 -m pytest " + TOGGLE),
    # --- FP twin of the glob rule ----------------------------------------
    # A GENERIC glob is not a spelling of the toggle: it names whatever is
    # in the directory. Denying it would break ordinary interpreter use for
    # no security gain (the shell would not resolve it to the toggle unless
    # the operator is already inside .claude/scripts). Documented residual:
    # `python3 .claude/scripts/*.py` stays ALLOWED — see the matcher note.
    ("bare_generic_glob", "python3 *.py"),
    ("dir_generic_glob", "python3 .claude/scripts/*.py"),
    ("unrelated_glob", "python3 tools/*.py --check"),
    # --- FP twins of the substitution rule --------------------------------
    # The substitution must be in an EXECUTION position. Capturing the file's
    # CONTENT is a read, and denying it would break ordinary shell work.
    ("subst_capture_into_var", "X=$(cat " + TOGGLE + ")"),
    ("subst_into_echo", "echo $(cat " + TOGGLE + ")"),
    ("subst_wc_redirect", "N=$(wc -l < " + TOGGLE + ")"),
    ("subst_grep_count", "echo $(grep -c _RESTORABLE_MODES " + TOGGLE + ")"),
    ("subst_unrelated_operand", "python3 $(echo tool.py) --check"),
    # --- FP twins of the alias rule (codex S292 r2 P1) --------------------
    # A COPY is a snapshot, not a second entry point. It is inert: the
    # self-path guard in night-mode.py refuses to run any file that is not
    # AT the canonical path of the repo it resolves into. Blocking `cp` here
    # would cost two real workflows for zero security — backing the file up
    # before editing it (done in THIS ceremony), and `install.sh` copying the
    # toggle into an adopter repo's own `.claude/scripts/night-mode.py`,
    # where it is legitimately that repo's toggle.
    ("cp_backup_of_the_writer", "cp " + TOGGLE + " /tmp/backup/night-mode.py.bak"),
    ("cp_into_adopter_install", "cp " + TOGGLE + " /other/repo/" + TOGGLE),
    ("cp_directory_of_scripts", "cp -R .claude/scripts /tmp/dest/"),
    ("rsync_the_writer", "rsync -a " + TOGGLE + " /tmp/dest/"),
    # Linking a DIFFERENT script is ordinary work.
    ("ln_other_script", "ln -s .claude/scripts/ceo-boot.py /tmp/cb"),
    ("ln_unrelated", "ln -s /tmp/a /tmp/b"),
    # Reading through `ln`'s own read-only inspection is not a link creation.
    ("ls_link_of_scripts_dir", "ls -la .claude/scripts/"),
    # --- FP twins of the NEWLINE rule (codex S292 r3 P1-A) ----------------
    # A line boundary makes MORE command words, so the risk is over-blocking.
    # A second line that READS the toggle is still a read.
    ("newline_benign_multiline", "echo one\necho two\nls -la"),
    ("newline_then_cat_the_writer", "echo ok\ncat " + TOGGLE),
    ("newline_then_grep_the_writer", "ls -la\ngrep -n MODES " + TOGGLE),
    ("newline_then_pytest", "echo ok\npython3 -m pytest " + TOGGLE),
    ("newline_then_other_script", "echo ok\npython3 .claude/scripts/ceo-boot.py"),
    ("newline_heredoc_benign", "cat <<EOF\nhello\nEOF"),
    ("line_continuation_benign", "echo one \\\n  two"),
    ("line_continuation_then_reader", "cat \\\n  " + TOGGLE),
    # QUOTE-AWARENESS controls. A newline inside quotes is literal DATA in
    # Bash, not a separator — a blind `str.replace` would deny both of these
    # and break ordinary multi-line `echo`/`git commit -m` traffic.
    ("newline_inside_single_quotes",
     "echo " + SQ + "line1\npython3 " + TOGGLE + " on" + SQ),
    ("newline_inside_double_quotes",
     "echo " + DQ + "line1\npython3 " + TOGGLE + " on" + DQ),
    ("newline_in_commit_message",
     "git commit -m " + DQ + "subject\n\nbody mentions " + TOGGLE + DQ),
    # --- FP twins of the EXPANSION-SKELETON rule (codex S292 r3 P1-B) -----
    # The skeleton pass walks the SAME execution-position discipline, so a
    # read stays a read even when the path is expansion-built.
    ("expansion_read_the_writer", "cat .claude/scripts/night${X}-mode.py"),
    ("expansion_grep_the_writer", "grep -n MODES .claude/scripts/night${X}-mode.py"),
    ("expansion_echo_the_path", "echo .claude/scripts/night${X}-mode.py"),
    # An expansion with NO kinship to the toggle must not be denied — this is
    # the shape that would DoS the operator if the skeleton rule dropped its
    # literal floor. `python3 $SCRIPT` skeletonises to `python3 *`, which
    # names every script in the tree and therefore names none of them.
    ("expansion_unrelated_script_dir", "python3 $SCRIPT_DIR/other.py"),
    ("expansion_home_build_script", "python3 $HOME/tools/build.py --fast"),
    ("expansion_whole_path_in_var", "python3 $SCRIPT --check"),
    ("expansion_braced_whole_path", "python3 ${SCRIPT} --check"),
    ("expansion_shell_runner_var", "bash $HOME/scripts/deploy.sh"),
    ("expansion_other_script_var_dir", "python3 ${D}/.claude/scripts/ceo-boot.py"),
    ("expansion_subst_unrelated", "bash $(which setup.sh)"),
    ("expansion_pytest_module", "python3 -m pytest ${T}/test_night_mode.py"),
    # ANSI-C quoting in an ARGUMENT position is not an invocation: bash gives
    # `echo` one argument containing a newline, it does not start a command.
    ("ansi_c_newline_inside_echo_arg",
     "echo ok$" + SQ + "\\n" + SQ + "python3 " + TOGGLE + " on"),
    ("ansi_c_unrelated_script", "python3 tools/build$" + SQ + "\\x2d" + SQ + "fast.py"),
    # --- FP twins of the BRACE rule (codex S292 r4 P1) --------------------
    # Braces are everywhere in ordinary shell work, and this hook runs on
    # EVERY Bash command — so the negative controls matter more here than for
    # any earlier round. Each of these was executed against real bash in the
    # sandbox: none of them runs the toggle.
    ("brace_read_the_writer", "cat .claude/scripts/{night-mode,other}.py"),
    ("brace_grep_the_writer", "grep -n MODES .claude/scripts/night-mode{,}.py"),
    ("brace_echo_the_path", "echo .claude/scripts/night-mode{,}.py"),
    ("brace_unrelated_scripts", "python3 {tool,other}.py --flag"),
    ("brace_mkdir_tree", "mkdir -p build/{a,b}"),
    ("brace_cp_backup_idiom", "cp file.txt{,.bak}"),
    ("brace_mv_rename_idiom", "mv report{,-old}.md"),
    # A large-but-SANE range must expand exactly and stay allowed — the word
    # budget exists to stop a bomb, not ordinary fan-out.
    ("brace_large_sane_range", "bash deploy.sh {srv001..srv300}"),
    ("brace_numeric_range_args", "python3 tools/gen.py --shard {1..64}"),
    # Bash does NOT expand a group with no top-level comma and no range, so
    # this token stays literal and names a file that does not exist. Denying
    # it would be a false positive on an ordinary — if strange — filename.
    ("brace_literal_group_not_expanded",
     "python3 .claude/scripts/night{weird}mode.py on"),
    # `${…}` is parameter expansion, NOT a brace group. The brace scanner must
    # not claim it; the skeleton rule already owns it, and its literal floor
    # is what keeps this allowed.
    ("brace_vs_parameter_expansion", "python3 ${SCRIPT} --check"),
    ("brace_param_expansion_in_arg", "echo ${HOME}/x"),
    ("brace_unbalanced_open", "echo 'a { b'"),
    ("brace_in_commit_message", "git commit -m 'fix {a,b} handling'"),
    # --- FP twins of the UNKNOWN-LAUNCHER rule (codex S292 r5) ------------
    # Reading the toggle THROUGH one of the newly enumerated launchers stays
    # a read: the reader settles as the command word and its operands are
    # never examined. These are the rows the derived flag tables buy — with
    # an empty table every flag classifies as unknown, the fail-closed
    # `ambiguous` step holds the command-word position open one token too
    # long, and `caffeinate -t 60 cat <toggle>` denies. Measured: it did,
    # before the man-page-derived tables were added.
    ("xcrun_then_cat", "xcrun cat " + TOGGLE),
    ("xcrun_sdk_then_grep", "xcrun --sdk macosx grep -n MODES " + TOGGLE),
    ("xcrun_sdk_short_then_head", "xcrun -sdk macosx head -20 " + TOGGLE),
    ("arch_then_cat", "arch -x86_64 cat " + TOGGLE),
    ("caffeinate_timeout_then_cat", "caffeinate -t 60 cat " + TOGGLE),
    ("caffeinate_wait_pid_then_git", "caffeinate -w 123 git log --oneline -- " + TOGGLE),
    ("script_then_cat", "script -q /dev/null cat " + TOGGLE),
    ("sandbox_exec_then_cat", "sandbox-exec -f p.sb cat " + TOGGLE),
    ("sandbox_exec_profile_string_then_wc", "sandbox-exec -p PROFILE wc -l " + TOGGLE),
    # An unknown launcher in front of a READER is still a read — the hop only
    # re-opens the interpreter rule, never the direct-exec rule.
    ("unknown_launcher_then_cat", "frobnicate-9000 cat " + TOGGLE),
    ("unknown_launcher_then_git_add", "frobnicate-9000 git add " + TOGGLE),
    # An interpreter with NO kinship to the toggle stays allowed even after
    # an unknown launcher — the hop denies on the OPERAND, not on the hop.
    ("unknown_launcher_then_other_script",
     "frobnicate-9000 python3 .claude/scripts/ceo-boot.py"),
    ("xcrun_then_pytest_module", "xcrun python3 -m pytest " + TOGGLE),
]


@pytest.mark.parametrize(
    "slug,command",
    INVOCATION_VECTORS,
    ids=[v[0] for v in INVOCATION_VECTORS],
)
def test_invocation_is_blocked(slug, command):
    """The model rail must not be able to RUN the posture toggle."""
    d = decide_command(command)
    assert not d.allow, (
        "NF-08 [%s]: model-rail invocation of the posture toggle was ALLOWED: %r"
        % (slug, command)
    )
    assert d.reason, "block must carry a reason"


@pytest.mark.parametrize(
    "slug,command",
    [v for v in INVOCATION_VECTORS if not v[0].startswith(
        ("review_form_3", "sh_c", "eval_", "shell_heredoc",
         "alias_toggle_as_destination"))],
    ids=[v[0] for v in INVOCATION_VECTORS if not v[0].startswith(
        ("review_form_3", "sh_c", "eval_", "shell_heredoc",
         "alias_toggle_as_destination"))],
)
def test_invocation_block_names_the_human_rail(slug, command):
    """The deny message must tell the operator HOW to proceed.

    A fail-closed gate without a recovery route is a lockout. Here the
    route is the ratified one: run it yourself. Bodies routed through the
    Wave E.3 blob-scan (`-c` / eval / heredoc) carry the older canonical
    message and are excluded — see the division-of-labour note in the
    matcher docstring.
    """
    reason = decide_command(command).reason or ""
    assert "!" in reason, "deny message must point at the `!` prefix: %r" % reason
    assert "night-mode" in reason


@pytest.mark.parametrize(
    "slug,command", WRITE_VECTORS, ids=[v[0] for v in WRITE_VECTORS]
)
def test_write_forms_still_blocked(slug, command):
    """Regression: the new matcher must not displace the Wave E.3 writes."""
    d = decide_command(command)
    assert not d.allow, "regression [%s]: write form now ALLOWED: %r" % (slug, command)


@pytest.mark.parametrize(
    "slug,command", ALLOW_VECTORS, ids=[v[0] for v in ALLOW_VECTORS]
)
def test_benign_commands_still_allowed(slug, command):
    """Negative controls — false positives here are operator DoS."""
    d = decide_command(command)
    assert d.allow, (
        "false positive [%s]: benign command BLOCKED (%s): %r"
        % (slug, d.reason, command)
    )


def test_unparseable_command_mentioning_the_toggle_fails_closed():
    """An unbalanced quote around the toggle must not sail through.

    Wave E.3's whole-command parse gate already fails CLOSED, so this
    asserts the OUTCOME (a block), not which matcher produced it — the
    property is order-independent.
    """
    d = decide_command("python3 " + SQ + TOGGLE + " on")
    assert not d.allow


def test_matcher_is_order_independent_of_e3():
    """`_e4` alone must block invocation, without help from `_e3`.

    Guards against a future refactor that reorders `decide_command` and
    silently re-opens NF-08.
    """
    from check_bash_safety import _e4_check_posture_toggle_invocation

    assert _e4_check_posture_toggle_invocation("python3 " + TOGGLE + " on")
    assert _e4_check_posture_toggle_invocation("./" + TOGGLE + " on") is not None
    assert _e4_check_posture_toggle_invocation("cat " + TOGGLE) is None
    assert _e4_check_posture_toggle_invocation("echo hello") is None


def test_guard_does_not_depend_on_knowing_the_launcher_name():
    """Codex S292 r5 — the STRUCTURAL property, stated as a property.

    The vector list above can only ever pin launchers somebody thought of;
    three review rounds proved that is not enough. This asserts the rule
    itself: for a launcher name drawn at random — one that exists in no
    table, no man page and no reviewer's memory — the interpreter chain
    behind it is still denied.
    """
    from check_bash_safety import _E4_PREFIX_RUNNERS
    from check_bash_safety import _e4_check_posture_toggle_invocation as _e4

    invented = "zqx-launcher-" + "9" * 7
    assert invented not in _E4_PREFIX_RUNNERS, "vector must be UNknown"
    for form in (
        invented + " python3 " + TOGGLE + " on",
        invented + " --some-flag VAL python3 " + TOGGLE + " on",
        invented + " bash " + TOGGLE + " on",
        "nohup " + invented + " python3 " + TOGGLE + " on",
    ):
        assert _e4(form) is not None, "unknown launcher bypassed: %r" % form

    # ...and the same unknown launcher in front of a READER stays allowed:
    # the hop re-opens the INTERPRETER rule only. Without this half the rule
    # would deny every read of the file and be reverted within a day.
    for benign in (
        invented + " cat " + TOGGLE,
        invented + " grep -n MODES " + TOGGLE,
        invented + " git add " + TOGGLE,
    ):
        assert _e4(benign) is None, "reader denied through hop: %r" % benign


def test_interpreter_word_used_as_data_is_a_known_false_positive():
    """The accepted cost of the r5 structural rule — pinned as a DECISION.

    `grep -n python3 <toggle>` and `xcrun python3 <toggle>` are the SAME
    shape to a string matcher: an unknown command word, an interpreter
    token, the toggle as its operand. The shell executes the first word in
    both; only the command's own semantics decide whether the second word is
    launched or read, and a hook cannot know those.

    So this DENIES, and the test exists so the next reader meets a recorded
    trade-off rather than a mystery:

      • it only fires on a command that ALREADY names the toggle, so the
        blast radius is one file, not the operator's shell;
      • the deny message names the `!` recovery route, and the rewrite is
        one pipe (`cat <toggle> | grep python3`);
      • the other error direction is a silent bypass of a boundary three
        signed comments claim is closed (CLAUDE.md §4 — fail-CLOSED on the
        input of a security matcher).

    NO "reader" allow-list softens this: `git` reads in `git add` and
    LAUNCHES in `git bisect run`, so the split is a property of
    command+flags, not of the name — an allow-list keyed on the name would
    hand back the exact bypass this round closes (pinned by the
    `git_bisect_run` vector above).
    """
    from check_bash_safety import _e4_check_posture_toggle_invocation as _e4

    accepted_false_positives = [
        "grep -n python3 " + TOGGLE,
        "grep -rn sh " + TOGGLE,
        "echo python3 " + TOGGLE,
    ]
    for cmd in accepted_false_positives:
        assert _e4(cmd) is not None, (
            "the r5 trade-off changed silently — if this now ALLOWS, the "
            "structural hop was weakened: %r" % cmd
        )
        assert "!" in (_e4(cmd) or ""), "an over-block MUST carry the route out"

    # The bound on that cost: an interpreter word next to a file that is NOT
    # the toggle is untouched, so ordinary greps keep working.
    for benign in (
        "grep -n python3 .claude/scripts/ceo-boot.py",
        "grep -rn python3 .claude/",
        "echo python3 --version",
    ):
        assert _e4(benign) is None, "cost leaked past the toggle: %r" % benign


def test_skeleton_does_not_invent_a_word_boundary():
    """Codex S292 r5-B — a decoded quoting form must stay ONE word.

    Bash makes `echo ok$'\\n'python3 <toggle> on` a single argument to
    `echo`; no command starts at `python3`. Decoding the escape literally
    put a real newline into the skeleton, `shlex` split there, and the
    interpreter hop then read a token the shell never produced. The old walk
    ignored everything after `echo`, so the artefact was invisible until the
    hop surfaced it.
    """
    from check_bash_safety import _e4_globify_expansions, _e4_skeleton_safe

    assert "\n" not in _e4_skeleton_safe("a\nb")
    assert _e4_skeleton_safe("a\nb") == "a?b", "length must be preserved"
    assert _e4_skeleton_safe("-") == "-", "non-whitespace decode is untouched"
    assert _e4_skeleton_safe("") == ""

    skeleton = _e4_globify_expansions(
        "echo ok$" + SQ + "\\n" + SQ + "python3 " + TOGGLE + " on")
    assert "\n" not in skeleton, (
        "the skeleton still carries a shell-invented word boundary: %r" % skeleton
    )
    # The r3 property this must not regress: a NON-whitespace ANSI-C escape
    # is still decoded, so `night$'\\x2d'mode.py` still names the toggle.
    assert "night-mode.py" in _e4_globify_expansions(
        "python3 .claude/scripts/night$" + SQ + "\\x2d" + SQ + "mode.py on")


def test_single_dash_long_flags_classify_exactly():
    """Codex S292 r5 — macOS spells long options with ONE dash.

    `-sdk` must not be read as the cluster `-s -d -k`: an unknown
    classification keeps the command-word position open one token too long
    and false-positives on the reader behind it.
    """
    from check_bash_safety import (
        _E4_PREFIX_RUNNER_FLAGS,
        _e4_classify_prefix_flag,
    )

    vals, bools = _E4_PREFIX_RUNNER_FLAGS["xcrun"]
    assert _e4_classify_prefix_flag("-sdk", vals, bools) == "value"
    assert _e4_classify_prefix_flag("--sdk", vals, bools) == "value"
    assert _e4_classify_prefix_flag("-sdk=macosx", vals, bools) == "attached"
    assert _e4_classify_prefix_flag("-f", vals, bools) == "bool"

    avals, abools = _E4_PREFIX_RUNNER_FLAGS["arch"]
    assert _e4_classify_prefix_flag("-x86_64", avals, abools) == "bool"
    assert _e4_classify_prefix_flag("-32", avals, abools) == "bool"
    assert _e4_classify_prefix_flag("-arch", avals, abools) == "value"

    # Regression: the pre-existing single-character rows keep their meaning.
    svals, sbools = _E4_PREFIX_RUNNER_FLAGS["sudo"]
    assert _e4_classify_prefix_flag("-u", svals, sbools) == "value"
    assert _e4_classify_prefix_flag("-E", svals, sbools) == "bool"
    assert _e4_classify_prefix_flag("-En", svals, sbools) == "bool"
    assert _e4_classify_prefix_flag("--frobnicate", svals, sbools) == "unknown"


def test_every_prefix_runner_has_a_flag_table_entry():
    """Codex S292 P1-B: the flag table must cover the runner set.

    A runner missing from `_E4_PREFIX_RUNNER_FLAGS` degrades to "every flag
    is unknown" — fail-closed, but noisier than it needs to be, and the gap
    is invisible at runtime. Derive the assertion from the runner frozenset
    rather than restating the names (S291 lesson: a closed set written from
    memory errs in both directions).
    """
    from check_bash_safety import (
        _E4_PREFIX_RUNNER_FLAGS,
        _E4_PREFIX_RUNNERS,
    )

    missing = sorted(_E4_PREFIX_RUNNERS - set(_E4_PREFIX_RUNNER_FLAGS))
    assert not missing, "prefix runners with no flag table: %s" % missing

    extra = sorted(set(_E4_PREFIX_RUNNER_FLAGS) - _E4_PREFIX_RUNNERS)
    assert not extra, "flag table rows for non-runners: %s" % extra

    for runner, (value_flags, bool_flags) in _E4_PREFIX_RUNNER_FLAGS.items():
        both = value_flags & bool_flags
        assert not both, (
            "%s: flag classified BOTH value-bearing and boolean: %s"
            % (runner, sorted(both))
        )


def test_matcher_tokenizes_rather_than_substring_matching():
    """Codex S292 P1-A: no raw-substring fast path may return early.

    The forms below name the toggle only AFTER shell normalisation, so a
    matcher that pre-filters on `basename in command` answers ALLOW without
    ever tokenizing. Asserted against `_e4` directly, so a future reordering
    of `decide_command` cannot make this pass on `_e3`'s back.
    """
    from check_bash_safety import _e4_check_posture_toggle_invocation as _e4

    normalised_only = [
        "python3 .claude/scripts/night" + DQ + "-" + DQ + "mode.py on",
        "python3 .claude/scripts/night" + SQ + SQ + "-mode.py on",
        "python3 .claude/scripts/night\\-mode.py on",
        "python3 .claude/scripts/NIGHT-MODE.PY on",
        "python3 .claude/scripts/night-mod?.py on",
    ]
    for cmd in normalised_only:
        assert _e4(cmd) is not None, "raw-substring bypass survived: %r" % cmd
        # ...and the raw string really does NOT carry the literal basename,
        # i.e. the vector tests what it claims to test (a positive control
        # for the test itself — S291: a probe that cannot fail proves nothing).
        assert TOGGLE.rsplit("/", 1)[-1] not in cmd, (
            "vector %r contains the literal basename — it does not exercise "
            "the normalisation path" % cmd
        )


def test_ambiguous_unknown_flag_buys_exactly_one_candidate():
    """The fail-closed continuation must not walk into the command's args.

    `sudo --frobnicate VAL ./<toggle>` denies (VAL may be the flag's value,
    so the toggle may be the command word), while `sudo --frobnicate VAL cat
    <toggle>` allows (`cat` settles as the command word and the toggle is
    its READ operand). One unknown flag, one extra candidate position.
    """
    from check_bash_safety import _e4_check_posture_toggle_invocation as _e4

    assert _e4("sudo --frobnicate VAL ./" + TOGGLE + " on") is not None
    assert _e4("sudo --frobnicate VAL cat " + TOGGLE) is None
    assert _e4("sudo --frobnicate VAL python3 " + TOGGLE + " on") is not None


def test_alias_creation_is_denied_by_e4_alone():
    """Codex S292 r2 P1: the LINK half must not lean on `_e3`.

    `ln -s <toggle> X` is a READ of the toggle as far as the write matcher is
    concerned, so `_e3` allows it (verified below). If a future refactor
    reorders `decide_command`, this keeps the alias rail honest.
    """
    from check_bash_safety import (
        _e3_check_canonical_path_write,
        _e4_check_posture_toggle_invocation as _e4,
    )

    link = "ln -s " + TOGGLE + " /tmp/nm"
    assert _e4(link) is not None, "alias creation ALLOWED by _e4: %r" % link
    # Positive control for the test itself: `_e3` really does let it through,
    # so the assertion above is not passing on `_e3`'s back (S291 — a probe
    # that cannot fail proves nothing).
    assert _e3_check_canonical_path_write(link) is None, (
        "_e3 now blocks alias creation — this test no longer proves _e4 does"
    )


def test_copy_is_deliberately_not_an_alias():
    """The `cp`-stays-allowed decision is a DECISION, pinned here.

    A copy is a snapshot, not a second entry point: `night-mode.py`'s
    self-path guard refuses to run any file that is not at the canonical
    path of the repository it resolves into, so the copy is inert. Blocking
    `cp` would break backing the file up before editing it, and
    `install.sh` copying the toggle into an adopter repo's own canonical
    location. If someone later adds `cp` to `_E4_LINK_RUNNERS`, they must
    delete this test and say why.
    """
    from check_bash_safety import _E4_LINK_RUNNERS
    from check_bash_safety import _e4_check_posture_toggle_invocation as _e4

    assert "ln" in _E4_LINK_RUNNERS
    assert "cp" not in _E4_LINK_RUNNERS, (
        "cp was added to the link runners — see this test's docstring"
    )
    assert _e4("cp " + TOGGLE + " /tmp/night-mode.py.bak") is None
    assert _e4("cp " + TOGGLE + " /other/repo/" + TOGGLE) is None


def test_newline_normalisation_is_quote_aware():
    """Codex S292 r3 P1-A, asserted on the normaliser itself.

    The property is not "newlines are replaced" — that would be a blind
    `str.replace` that breaks every multi-line `echo`. It is "an UNQUOTED
    newline becomes a separator, a QUOTED one stays literal, and
    `\\<newline>` disappears the way Bash makes it disappear".
    """
    from check_bash_safety import _e4_normalise_command as _norm

    # unquoted newline -> separator
    assert " ; " in _norm("echo ok\npython3 x.py")
    # quoted newline -> untouched (both quote flavours)
    assert _norm("echo " + SQ + "a\nb" + SQ) == "echo " + SQ + "a\nb" + SQ
    assert _norm("echo " + DQ + "a\nb" + DQ) == "echo " + DQ + "a\nb" + DQ
    # line continuation -> removed entirely, both LF and CRLF
    assert _norm("python3 \\\nx.py") == "python3 x.py"
    assert _norm("python3 \\\r\nx.py") == "python3 x.py"
    # an ESCAPED BACKSLASH is not an escape of the newline that follows it:
    # `\\` + NL is a real line boundary, and eating it would lose a command.
    assert " ; " in _norm("echo 'a\\\\'\nls")
    # a command with no newline at all is returned unchanged (the fast path
    # must be an identity, not an approximation).
    for sample in ("python3 " + TOGGLE + " on", "cat " + TOGGLE, "echo hi && ls"):
        assert _norm(sample) == sample


def test_expansion_skeleton_keeps_the_literal_floor():
    """Codex S292 r3 P1-B: the fail-closed rule must not become a DoS.

    An expansion that could resolve to the toggle is denied; an expansion
    that names EVERYTHING (`$SCRIPT` -> `*`) names nothing in particular and
    must stay allowed, or every variable-driven interpreter call in this repo
    starts failing. The floor is the one the glob rule already uses.
    """
    from check_bash_safety import (
        _e4_check_posture_toggle_invocation as _e4,
        _e4_globify_expansions,
    )

    # skeletonisation itself
    assert _e4_globify_expansions("a${X}b") == "a*b"
    assert _e4_globify_expansions("a$(echo x)b") == "a*b"
    assert _e4_globify_expansions("a" + chr(96) + "echo x" + chr(96) + "b") == "a*b"
    assert _e4_globify_expansions("$A$B") == "*"          # runs collapse
    assert _e4_globify_expansions("no expansions") == "no expansions"

    # ANSI-C / locale quoting is DECODED, not wildcarded: its content is
    # static text sitting in the command, so `*` would discard information
    # and drop below the glob literal floor.
    assert _e4_globify_expansions("night$" + SQ + "\\x2d" + SQ + "mode.py") == "night-mode.py"
    assert _e4_globify_expansions("night$" + SQ + "\\055" + SQ + "mode.py") == "night-mode.py"
    assert _e4_globify_expansions("night$" + DQ + "-" + DQ + "mode.py") == "night-mode.py"


def test_ansi_c_decoding_does_not_over_match():
    """The decode must name the file bash names — no more, no less.

    `night$'\\x2d\\'x'mode.py` decodes to `night-'xmode.py`, a DIFFERENT
    file (verified by running bash: the path it produces does not exist).
    `_e4` must therefore ALLOW it; denying would be a false positive on an
    ordinary — if strange — filename.

    Asserted against `_e4` directly ON PURPOSE: `decide_command` DOES block
    this command, via `_e3`'s whole-command parse gate (the unbalanced quote
    makes it unparseable, and Wave E.3 fails closed on that). That is a
    different, pre-existing rail with nothing to do with night-mode — the
    positive control below shows it fires identically on a command that
    never mentions the toggle.
    """
    from check_bash_safety import _e3_check_canonical_path_write as _e3
    from check_bash_safety import _e4_check_posture_toggle_invocation as _e4

    weird = "python3 .claude/scripts/night$" + SQ + "\\x2d\\" + SQ + "x" + SQ + "mode.py on"
    assert _e4(weird) is None, "_e4 over-matched a decode that is NOT the toggle"
    # Positive control: the parse gate that DOES block it is `_e3`'s, and it
    # blocks an unrelated command of the same shape just as readily.
    unrelated = "python3 tools/build$" + SQ + "\\x2d\\" + SQ + "x" + SQ + "fast.py"
    assert _e3(weird) is not None
    assert _e3(unrelated) is not None
    assert _e4(unrelated) is None

    # denied: the skeleton can still resolve to the toggle
    assert _e4("python3 .claude/scripts/night${X}-mode.py on") is not None
    # allowed: the skeleton resolves to anything at all
    assert _e4("python3 $SCRIPT --check") is None
    assert _e4("python3 $SCRIPT_DIR/other.py") is None
    # allowed: expansion-built, but in a READ position
    assert _e4("cat .claude/scripts/night${X}-mode.py") is None


def test_expansion_skeleton_does_not_shadow_the_literal_pass():
    """The literal pass must run FIRST and own its own message.

    `python3 $(echo <toggle>) on` is caught by the SUBSTITUTION rule, whose
    skeleton (`python3 *`) is deliberately allow-shaped. If the passes were
    reordered — or if only the skeleton pass survived a refactor — this
    vector would silently re-open.
    """
    from check_bash_safety import _e4_check_posture_toggle_invocation as _e4
    from check_bash_safety import _e4_globify_expansions

    cmd = "python3 $(echo " + TOGGLE + ") on"
    assert _e4(cmd) is not None
    # Positive control for the claim above: the SKELETON alone does not deny
    # it, so the deny really is the literal pass's (S291 — a probe that
    # cannot fail proves nothing).
    assert _e4(_e4_globify_expansions(cmd)) is None
    assert "SKELETON" not in (_e4(cmd) or "")


def test_brace_expansion_matches_what_bash_produces():
    """Codex S292 r4 P1: the expander must agree with bash, word for word.

    Every expectation here was taken from GNU bash 3.2.57 output, not from
    the spec: `echo .claude/scripts/night-mode.p{y..y}` prints ONE word, and
    that is the fact the guard depends on.
    """
    from check_bash_safety import _e4_brace_words, _e4_group_alternatives

    def words(tok):
        return sorted(_e4_brace_words(tok))

    assert words("a{b,c}d") == ["abd", "acd"]
    assert words("night-mode{,}.py") == ["night-mode.py", "night-mode.py"]
    assert words("night-mode.p{y..y}") == ["night-mode.py"]      # ONE word
    assert words("x{1..3}") == ["x1", "x2", "x3"]
    assert words("x{c..a}") == ["xa", "xb", "xc"]                # descending
    assert words("{a,{b,c}}") == ["a", "b", "c"]                 # nested
    assert words("no-braces-here") == ["no-braces-here"]

    # A group bash leaves LITERAL must come back unchanged, or the matcher
    # would invent a file the shell never names.
    assert words("night{weird}mode.py") == ["night{weird}mode.py"]
    assert _e4_group_alternatives("weird") is None

    # `${…}` is parameter expansion. Treating its braces as a group would
    # both mis-expand it and steal the closer from a real group around it.
    assert words("${SCRIPT}") == ["${SCRIPT}"]
    assert words("${A}{b,c}") == ["${A}b", "${A}c"]

    # The STEP of a sequence expression is ignored, yielding a SUPERSET of
    # what bash produces. Deliberate: a matcher that considered fewer words
    # than the shell is the one direction this must not fail in.
    assert set(words("x{1..9..3}")) >= {"x1", "x4", "x7"}


def test_brace_budget_fails_closed_and_has_a_positive_control():
    """The budget must refuse a bomb — and must NOT refuse ordinary fan-out.

    A guard whose budget never triggers proves nothing, and one that triggers
    on real commands is operator DoS. Both directions are asserted here.
    """
    from check_bash_safety import (
        _E4_BRACE_MAX_TOKEN,
        _E4_BRACE_MAX_WORDS,
        _e4_brace_names_toggle,
        _e4_check_posture_toggle_invocation as _e4,
        _e4_is_toggle_path,
    )

    # POSITIVE CONTROL for the budget itself: it does fire, and it fires as
    # `undecidable` rather than as a claimed match.
    bomb = "{%s}.py" % ",".join("d%d" % i for i in range(_E4_BRACE_MAX_WORDS + 10))
    matched, undecidable = _e4_brace_names_toggle(bomb)
    assert (matched, undecidable) == (False, True)
    assert _e4_is_toggle_path(bomb) is True                 # fail-CLOSED
    assert len("x" * (_E4_BRACE_MAX_TOKEN + 1)) > _E4_BRACE_MAX_TOKEN
    assert _e4_brace_names_toggle("{a,b}" + "x" * _E4_BRACE_MAX_TOKEN) == (False, True)

    # ... and the deny message says which of the two it was. Claiming "one of
    # those words IS the guarded path" for a token nobody enumerated would be
    # a false statement in an operator-facing message.
    bomb_cmd = "python3 .claude/scripts/" + bomb + " on"
    reason = _e4(bomb_cmd) or ""
    assert "cannot be decided" in reason, reason
    exact = _e4("python3 .claude/scripts/night-mode.p{y..y} on") or ""
    assert "IS the guarded path" in exact, exact

    # NEGATIVE CONTROL: a large-but-sane range expands exactly and is allowed.
    assert _e4_brace_names_toggle("{srv001..srv300}") == (False, False)
    assert _e4("bash deploy.sh {srv001..srv300}") is None


def test_brace_rule_only_widens_execution_positions():
    """Reads stay reads — the structural reason, asserted directly.

    The brace rule lives inside `_e4_is_toggle_path`, and every caller of that
    helper passes an EXECUTION-position operand. So a token that expands to
    the toggle is denied in a script-operand position and allowed in an
    argument position, with nothing but the position differing.
    """
    from check_bash_safety import _e4_check_posture_toggle_invocation as _e4
    from check_bash_safety import _e4_is_toggle_path

    token = ".claude/scripts/{night-mode,other}.py"
    assert _e4_is_toggle_path(token) is True            # the token itself
    assert _e4("python3 " + token + " on") is not None  # execution position
    assert _e4("cat " + token) is None                  # read position
    assert _e4("grep -n MODES " + token) is None
    # `python3 tool.py <token>` is argv of tool.py, not something python runs.
    assert _e4("python3 tool.py " + token) is None


def test_guard_target_is_a_canonical_guard_entry():
    """Coherence: the invocation target is also write-guarded.

    If someone removes `.claude/scripts/night-mode.py` from
    `_CANONICAL_GUARDS`, the write rail opens while this matcher keeps
    reporting healthy — a split-brain the round-3 review would catch only
    by re-probing. Fail here instead.
    """
    sys.path.insert(0, str(_HOOKS_DIR))
    from check_canonical_edit import _CANONICAL_GUARDS

    from check_bash_safety import _E4_POSTURE_TOGGLE_SCRIPTS

    for target in _E4_POSTURE_TOGGLE_SCRIPTS:
        assert target in _CANONICAL_GUARDS, (
            "%s is invocation-guarded but no longer write-guarded" % target
        )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
