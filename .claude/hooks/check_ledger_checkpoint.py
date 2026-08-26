#!/usr/bin/env python3
"""PLAN-179 W2 US6 — work-boundary ledger checkpoint (ADVISORY, never blocks).

The doctrine this hook exists to serve (ADR-195, PLAN-179 §W2): durable
state must be written at a WORK BOUNDARY, not at session death. S309 proved
the death-time write does not arrive — the ADR-153 fires-proof fired on a
real autocompact and delivered nothing. A commit that lands plan work is the
one boundary this repo already has, is already auditable, and already
survives a killed session.

This hook does NOT write the ledger. It makes an OMITTED checkpoint VISIBLE
— a breadcrumb the operator can see, an advisory the model can act on, and a
closed-enum audit event a later window report can count. Writing the ledger
stays a decision of the model/Owner (same doctrine as ``SessionEnd.py``: the
hook surfaces the omission, it never authors the content).

## Why PreToolUse(Bash) and not PostToolUse / SessionEnd / Stop

Read against `.claude/data/hook-schema-2.1.220.json`:

1. **The AC is "the ledger was updated in the SAME commit."** Only a
   PRE-commit event leaves a moment where that is still achievable: the
   model can `git add <plan>/LEDGER.md` and re-issue the commit. At
   PostToolUse the commit already exists, so the only cure is `git commit
   --amend` — rewriting a commit to satisfy an advisory is a worse trade
   than the advisory itself.
2. **The enforce flip must not re-site the hook.** PLAN-179 W2 says enforce
   is a FUTURE ceremony with a would-block/TP-FP table (the
   ``CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED`` shape, ADR-191). ``PreToolUse`` is
   the only event in the enum whose output arm carries
   ``permissionDecision: deny``. Registering anywhere else would mean the
   measure-first window measures one code path and the flip ships another —
   the class this repo keeps re-learning (a green instrument whose question
   aged).
3. **The advisory channel exists here.** The PreToolUse arm carries
   ``additionalContext``, so the advisory reaches the model without touching
   permissions. This hook NEVER sets ``permissionDecision`` — not even
   ``ask``. There is no code path in this module that returns a deny.
4. Rejected alternatives, named: ``PostToolUse(Bash)`` — advisory arrives
   after the fact (see 1); ``SessionEnd``/``Stop`` — death-time write, the
   exact failure mode PLAN-179 exists to replace; ``PostToolUseFailure`` —
   would only see failed commits.

Registration JSON is reported by the implementing agent, NOT edited here —
``.claude/settings.json`` is canonical and lands in the W2 ceremony.

## Trigger derives from PATHS — never from ``resolve_plan_id`` (emenda r1-C6)

``scratchpad_lib.resolve_plan_id`` needs a ``plan_transition`` event *from
the same session*, and a real session emits ~0 of those (2 events in 12.515
log lines, S309). That function is the ROOT CAUSE PLAN-179 exists to fix;
routing the trigger through it would re-inherit the bug in the wave meant to
cure it. So the scope is derived, mechanically, from the paths in the commit:

  (a) any path under ``.claude/plans/PLAN-NNN/`` — the plan's own directory;
  (b) any path listed in a plan AC of the form ``[P?][USn][path]``.

There is NO fallback to session state, env, or the audit log. The ban is
enforced by a test that parses this module's AST: no name, attribute,
import or string constant may be ``resolve_plan_id``, and nothing from
``scratchpad_lib`` may be imported. The prose above is allowed to NAME the
banned function — a ban whose reason is undocumented gets re-litigated by
the next reader.

Declared false negative (deliberate, not an oversight): a commit that
touches ONLY the plan FILE ``.claude/plans/PLAN-NNN-<slug>.md`` (e.g.
ticking a checkbox) is OUT of scope, because the plan text names (a) and (b)
and nothing else. Widening to the plan file is a scope change with its own
FP cost; if the window shows it matters, it is a named amendment, not a
silent edit here.

## Skips are VISIBLE (never silent)

A commit the hook decides not to advise on emits
``ledger_checkpoint_skipped`` with a CLOSED-ENUM ``reason``
(``_SKIP_REASONS``): out-of-scope paths, kill switch, hotfix, exploratory,
operator opt-out, unparseable command, exhausted time budget, no repo.
Omission is a measurement, not silence. The ONLY fully-silent paths are
(i) a Bash call that is not a ``git commit`` at all — every Bash tool call
reaches this hook and emitting there would drown the log — and (ii) the
master kill ``CEO_SOTA_DISABLE=1``, which is the operator's declared
"instrument off" route.

## The censored universe (the number that decides the window)

The Owner commits with a leading ``!`` in the REPL, which bypasses the tool
layer entirely: those commits never reach this hook. A window report that
ignores them would report a checkpoint rate over a universe it does not
have. So every event carries ``commits_since_last_observation``: the count
of commits that landed between this observation and the previous one,
measured as ``git rev-list --count <last_observed_head>..HEAD`` against a
state file under the (gitignored) ``.claude/state/``.

The report's identity — stated here so the counter is not re-derived by
guesswork later, INCLUDING its bias. The observation happens BEFORE the
commit, so HEAD at observation *k* excludes the commit being made; the delta
seen at observation *k+1* therefore counts our own commit *k* (if it
succeeded) plus every commit that bypassed the hook:

    Σ_since   = Σ commits_since_last_observation over the window
    observed  = number of events emitted in the window (ATTEMPTED commits —
                a commit that fails after the advisory is still counted,
                the declared over-count of this estimator)
    unobserved ≥ Σ_since − observed          (a LOWER bound, because
                                              observed ≥ successful)
    censored_rate ≥ 1 − observed / Σ_since   (same direction)

The report must publish the bound, not a point estimate dressed as one.
``state_kind`` names the counter's confidence: ``fresh`` = no prior anchor,
so the 0 is structural and MUST NOT be read as "zero unobserved commits";
``resumed`` = a real delta; ``unavailable`` = git or the state file failed.

## Death criterion (emendas r1-A1/A3/B6)

``LEDGER_OMISSION_DEATH_THRESHOLD_PCT``. If, at the end of the advisory
window (``ADVISORY_WINDOW_MIN_DAYS`` / ``ADVISORY_WINDOW_MIN_SESSIONS``,
whichever is later), the omitted-checkpoint rate over the OBSERVED universe
exceeds that threshold, the ledger is REMOVED — hook, contract and
``LEDGER.md`` files — not kept as debt and not flipped to enforce. A ledger
nobody writes is pure floor cost in a plan whose W3 exists to cut the floor.

## Ledger content rules this hook checks (it never edits the file)

- **Identifiers only.** The ledger carries paths, SHAs, PLAN-/ADR-/AC-ids —
  never transcript bodies or excerpts. The repo is PUBLIC. This hook never
  copies ledger CONTENT anywhere: not into the audit wire (counts and closed
  enums only) and not into the advisory text (paths it already derived).
- **Size ceiling** ``LEDGER_MAX_TOKENS`` (~``LEDGER_MAX_BYTES``). Over the
  ceiling the advisory says: archive the oldest sections to
  ``<plan-dir>/LEDGER-ARCHIVE.md`` and keep the current unit + open
  blockers. Otherwise W2 adds to the context floor exactly what W3 removes.
- **Every AC-state claim names its VERIFIER** — grammar in
  ``_VERIFIER_RE``: ``verifier: `<command>` exit=<n>``. A WRONG ledger entry
  is worse than a missing one: the next session writes its checkpoint from a
  corrupted premise and the corruption compounds silently.

## Failure semantics

ADVISORY + fail-OPEN on everything. This is not a security matcher: nothing
it reads is an attack surface it is guarding, so an infra bug (missing file,
git failure, import error, blown budget) produces a stderr breadcrumb and a
schema-compliant ``{}``. It never blocks the session; there is no deny path.

## Honest degradation when the W2 ceremony has not landed

``ledger_checkpoint_recorded`` / ``ledger_checkpoint_skipped`` are NOT in
``_lib/audit_emit.py``'s ``_KNOWN_ACTIONS`` until the W2 canonical ceremony
registers them (plus SPEC/v1 rows and a deny-by-default scrub branch).
``emit_generic`` drops an unknown action with a breadcrumb only. This module
therefore checks registration ITSELF and, when the action is absent, is
LOUD: stderr + a line in the advisory + a ``systemMessage`` naming exactly
what is missing. Silent telemetry loss in the window that decides the
ledger's life would corrupt the very decision the window exists to make.

Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:  # audit_emit is optional at import time — fail-open (PLAN-091 S116).
    from _lib import audit_emit as _audit_emit  # type: ignore
    _AUDIT_EMIT_AVAILABLE = True
except Exception:  # pragma: no cover - infra fail-open
    _audit_emit = None  # type: ignore
    _AUDIT_EMIT_AVAILABLE = False

# --------------------------------------------------------------------------
# Named constants (every number that carries a DECISION is named here)
# --------------------------------------------------------------------------

#: Kill switch for this rail alone. ``0`` => the hook still reports the skip
#: (``reason=kill_switch``), so "the rail is off" is itself measured.
KILL_SWITCH_ENV = "CEO_LEDGER_CHECKPOINT"
#: Master kill (E3-rail precedent, CLAUDE.md §4). ``1`` => fully silent.
MASTER_KILL_ENV = "CEO_SOTA_DISABLE"
#: FUTURE enforce flip (ADR-191 shape). Setting it today does NOT block —
#: ``ENFORCE_FLIP_IMPLEMENTED`` is False and no deny path exists in this
#: module. It only marks the events so a dry-run of the flip is countable.
ENFORCE_ENV = "CEO_LEDGER_CHECKPOINT_REQUIRED"

#: The enforce flip is a FUTURE ceremony (PLAN-179 W2, ADR-191 precedent):
#: it requires a would-block/TP-FP table from the advisory window. Flipping
#: this constant is NOT the ceremony — the ceremony also has to add the deny
#: branch, which deliberately does not exist yet.
ENFORCE_FLIP_IMPLEMENTED = False

#: Advisory window before the flip-or-kill decision may be taken at all.
ADVISORY_WINDOW_MIN_DAYS = 30
ADVISORY_WINDOW_MIN_SESSIONS = 20

#: DEATH CRITERION (emendas r1-A1/A3/B6). Omitted-checkpoint rate over the
#: OBSERVED universe, in percent. Above it the ledger is REMOVED, not kept
#: as debt and not flipped to enforce.
#:
#: The value is 33 because ADR-195 §3.2 M1 says 33 and gives the reason ("um
#: ledger escrito em menos de dois terços das fronteiras é um ledger em que a
#: próxima sessão não pode confiar"). This constant read 30 while the ADR read
#: 33 (pair-rail round 1, P2): a measured rate in (30, 33] produced OPPOSITE
#: keep/remove verdicts depending on which authority the report happened to
#: quote. The agreement is now pinned by a test that PARSES the ADR, so the
#: two cannot drift apart again silently.
LEDGER_OMISSION_DEATH_THRESHOLD_PCT = 33

#: Ledger size ceiling. A ledger is a context-floor cost; W3 exists to cut
#: the floor, so W2 is not allowed to grow one without a bound.
LEDGER_MAX_TOKENS = 2000
#: Bytes-per-token used to turn the token ceiling into a checkable number.
#: Coarse on purpose — the ceiling is a hygiene bound, not an accounting one.
LEDGER_BYTES_PER_TOKEN = 4
LEDGER_MAX_BYTES = LEDGER_MAX_TOKENS * LEDGER_BYTES_PER_TOKEN

LEDGER_BASENAME = "LEDGER.md"
LEDGER_ARCHIVE_BASENAME = "LEDGER-ARCHIVE.md"

#: Wall budget for the whole hook (git subprocesses + AC scan).
TIME_BUDGET_S = 2.0
#: Per-subprocess cap, well under the wall budget.
_GIT_TIMEOUT_S = 1.0

#: Bounds for the AC scan of plan files (ReDoS/IO defense, both directions).
_AC_SCAN_MAX_FILES = 200
_AC_SCAN_MAX_BYTES = 256 * 1024
#: Command length above which parsing is refused as ``unparseable``.
_COMMAND_MAX_CHARS = 8192
#: Cap on committed paths considered (a mega-commit is not a work boundary
#: this rail can reason about; the count is still reported, clamped).
_MAX_PATHS = 2000
#: Cap on ledger bytes read for the verifier scan.
_LEDGER_SCAN_MAX_BYTES = 512 * 1024

#: Relative location of the observation state (``.claude/state/`` is
#: gitignored as a whole — .gitignore:77 — so this never enters a commit).
_STATE_SUBPATH = (".claude", "state", "ledger-checkpoint.json")

# --------------------------------------------------------------------------
# Closed enums (the audit wire carries ONLY these + clamped ints)
# --------------------------------------------------------------------------

ACTION_RECORDED = "ledger_checkpoint_recorded"
ACTION_SKIPPED = "ledger_checkpoint_skipped"

_OUTCOMES = (
    "ledger_updated",           # the plan's LEDGER.md is in this commit
    "ledger_missing",           # in scope, ledger exists on disk, NOT committed
    "ledger_absent_from_plan",  # in scope, the plan has no LEDGER.md at all
    "error",
    "other",
)
_SKIP_REASONS = (
    "out_of_scope_paths",  # a commit that touches no plan-scoped path
    "kill_switch",         # CEO_LEDGER_CHECKPOINT=0
    "hotfix",              # operator-declared hotfix/revert
    "exploratory",         # operator-declared wip/spike
    "operator_opt_out",    # explicit [skip-ledger] tag
    "unparseable",         # command shape the parser refuses to guess at
    "budget_exhausted",    # wall budget blown mid-derivation (infra, visible)
    "no_repo",             # no git repo / no HEAD
    "other",
)
_SCOPE_SOURCES = ("plan_dir", "plan_ac", "both", "other")
_STATE_KINDS = ("fresh", "resumed", "unavailable")

# --------------------------------------------------------------------------
# Regexes — all bounded, no nested quantifiers
# --------------------------------------------------------------------------

#: ``.claude/plans/PLAN-179/anything`` => scope rule (a).
_PLAN_DIR_RE = re.compile(r"^\.claude/plans/(PLAN-[0-9]{3})/")
#: A plan file, used to find AC lines for scope rule (b).
_PLAN_FILE_GLOB = "PLAN-[0-9][0-9][0-9]-*.md"
_PLAN_FILE_ID_RE = re.compile(r"^(PLAN-[0-9]{3})-")
#: AC grammar ``[P?][USn][path]`` as this repo writes it (US ids may carry a
#: trailing letter: US5c, US15c). Bounded on every axis.
_AC_PATH_RE = re.compile(
    r"\[P[0-3]\]\[US[0-9]{1,6}[a-z]{0,2}\]\[([^\[\]\n]{1,200})\]"
)
#: A ledger bullet CLAIMS an AC state when it names an AC/US id.
_AC_ID_RE = re.compile(r"\b(?:AC-[0-9]{1,3}|US[0-9]{1,6}[a-z]{0,2})\b")
#: ...and must then name its verifier: command in backticks + exit code.
_VERIFIER_RE = re.compile(
    r"verifier:\s*`[^`\n]{1,200}`\s*exit=[0-9]{1,3}", re.IGNORECASE
)
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")

#: Operator-declared skip markers. Conservative BY DESIGN, with declared
#: misses: the bracket tags match anywhere in the message; the bare words
#: match only inside the conventional-commit type region (first
#: ``_MSG_TYPE_REGION`` chars), so a "hotfix" mentioned in prose does not
#: silently disarm the rail. Synonyms and other languages are MISSED
#: ("correção urgente", "temp", "scratch") — an operator who wants the skip
#: uses the explicit tag.
_MSG_TYPE_REGION = 32
_HOTFIX_TAGS = ("[hotfix]",)
_HOTFIX_WORDS = ("hotfix", "revert")
_EXPLORATORY_TAGS = ("[wip]", "[spike]")
_EXPLORATORY_WORDS = ("wip", "spike", "exploratory")
_OPT_OUT_TAGS = ("[skip-ledger]", "[no-ledger]")


# --------------------------------------------------------------------------
# Breadcrumbs
# --------------------------------------------------------------------------

def _breadcrumb(msg: str) -> None:
    """Non-fatal stderr breadcrumb (fail-open doctrine)."""
    try:
        sys.stderr.write("# check_ledger_checkpoint: %s\n" % str(msg)[:400])
    except Exception:  # pragma: no cover
        pass


def _loud(msg: str) -> None:
    """LOUD stderr breadcrumb — an instrument defect, not routine noise."""
    try:
        sys.stderr.write("!! check_ledger_checkpoint: %s\n" % str(msg)[:600])
    except Exception:  # pragma: no cover
        pass


def _flag_on(name: str, default: str = "") -> bool:
    return (os.environ.get(name) or default).strip() == "1"


def _clamp_count(value: Any, hi: int = 99) -> int:
    """Clamp to 0..hi as an INT. Never a float: a float in an HMAC-covered
    field discards the whole event ([[feedback-float-in-hmac-field-drops-
    whole-event]])."""
    try:
        if isinstance(value, bool):
            return 0
        n = int(value)
    except (TypeError, ValueError):
        return 0
    if n < 0:
        return 0
    return n if n <= hi else hi


# --------------------------------------------------------------------------
# Command parsing — is this Bash call a `git commit`, and of what shape?
# --------------------------------------------------------------------------

class CommitInvocation(object):
    """Parsed shape of a ``git commit`` inside a Bash command string."""

    __slots__ = (
        "is_commit", "unparseable", "foreign_repo",
        "all_flag", "amend", "message", "pathspecs",
    )

    def __init__(self) -> None:
        self.is_commit = False
        self.unparseable = False
        self.foreign_repo = False
        self.all_flag = False
        self.amend = False
        self.message = ""
        self.pathspecs = []  # type: List[str]


_SEPARATORS = frozenset({"&&", "||", ";", "|", "&", "(", ")", "{", "}", "\n"})
# `if`/`while`/`until` ABREM uma posicao de comando tanto quanto `then`/`do`.
# Sem elas, `if git commit -m x; then ...; fi` nao era reconhecido e o
# commit sumia do universo observado (pair-rail rodada 6, P2).
_CMD_POSITION_WORDS = frozenset({
    "then", "do", "else", "elif", "!", "time",
    "if", "while", "until",
})
#: `NAME=value` prefix — shell keeps the command position after it.
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*=")
#: Thin wrappers that keep the command position. Deliberately SHORT: each
#: entry is a wrapper whose next non-option token is the real command. Things
#: like `sudo` or `xargs` are NOT here — widening this set trades a false
#: negative for a false positive, and the rail is advisory either way.
_CMD_WRAPPERS = frozenset({"env", "command", "nohup", "stdbuf"})
#: git GLOBAL options that take a value (consumed before the subcommand).
_GIT_GLOBAL_VALUE_OPTS = frozenset({
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
})

#: ``git commit`` options whose value is a SEPARATE next token. Skipping only
#: the option name leaves the value to be read as a pathspec, and a bogus
#: pathspec turns a perfectly normal commit into ``unparseable`` — a SKIP
#: event in the very window this rail exists to measure (pair-rail round 1,
#: P2: `git commit --author Alice -m x` recorded "Alice" as a path).
#:
#: REQUIRED-value options only. Options whose value is optional (``-S`` /
#: ``--gpg-sign``, ``-u`` / ``--untracked-files``) accept it in ``=`` form
#: alone, so consuming a second token for them would eat a real pathspec —
#: the opposite error. The ``--opt=value`` form needs no entry here: it is
#: one token and the generic ``--`` branch already skips it.
_COMMIT_VALUE_OPTS_LONG = frozenset({
    "--author", "--date", "--message", "--file", "--template",
    "--cleanup", "--reuse-message", "--reedit-message",
    "--fixup", "--squash", "--trailer",
})

#: NAO e opcao de valor comum: ela SELECIONA os paths do commit. Tratada como
#: pathspec, porque consumi-la em silencio deixava `inv.pathspecs` vazio,
#: `_committed_paths()` inspecionava o conjunto staged INTEIRO, e um
#: LEDGER.md staged mas EXCLUIDO pelo arquivo de pathspec gerava um registro
#: `ledger_updated` FALSO para um commit que nao o conteria.
#: (pair-rail do main, rodada 3, P2.)
_PATHSPEC_FROM_FILE = "--pathspec-from-file"
#: Same, in short form. ``-m`` is handled earlier (it fills ``message``);
#: the rest only need their value consumed so it is not read as a path.
_COMMIT_VALUE_OPTS_SHORT = frozenset({"-F", "-c", "-C", "-t"})


def parse_git_commit(command: str) -> CommitInvocation:
    """Parse ``command`` and report whether it runs ``git commit``.

    Conservative in BOTH directions and honest about it:

    - a quoted string that merely CONTAINS "git commit" is one token, so it
      is not a command position and does not trigger (verified: ``echo "git
      commit"`` tokenizes to ``['echo', 'git commit']``);
    - ``git -C <dir> commit`` sets ``foreign_repo`` — the commit may not be
      this repo, so the caller refuses to guess (``unparseable``);
    - an unbalanced quote, an over-long command, or any tokenizer error is
      ``unparseable`` — but ONLY when the raw text contains both ``git`` and
      ``commit``. Otherwise every long or quote-heavy Bash call would emit a
      skip event and drown the very log the window has to count;
    - a heredoc body, a shell function, or a command built by string
      interpolation is MISSED (declared false negative).
    """
    inv = CommitInvocation()
    text = command or ""
    if not text.strip():
        return inv
    # Cheap prefilter: only a command that mentions BOTH words can be a
    # `git commit`, and only such a command may report `unparseable`.
    commit_shaped = ("git" in text) and ("commit" in text)
    if not commit_shaped:
        return inv
    if len(text) > _COMMAND_MAX_CHARS:
        inv.unparseable = True
        return inv
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except Exception:
        inv.unparseable = True
        return inv

    at_command_position = True
    idx = 0
    total = len(tokens)
    while idx < total:
        tok = tokens[idx]
        if tok in _SEPARATORS:
            at_command_position = True
            idx += 1
            continue
        if tok in _CMD_POSITION_WORDS:
            at_command_position = True
            idx += 1
            continue
        # A command position survives environment assignments and thin
        # wrappers (pair-rail round 2, P2). `GIT_EDITOR=true git commit -m x`
        # and `env FOO=1 git commit -m x` are ordinary shell; treating the
        # assignment as "some other command" cleared the flag and the `git`
        # right after it was never recognised — the commit got NEITHER an
        # advisory NOR a skip event, i.e. it vanished from the observed
        # universe entirely. Silence is the one outcome this rail is not
        # allowed to produce for a real commit.
        if at_command_position and _ENV_ASSIGN_RE.match(tok):
            idx += 1
            continue
        if at_command_position and tok in _CMD_WRAPPERS:
            # Consumir SO o nome do wrapper nao basta (pair-rail do main,
            # rodada 2, P2): em `env -i FOO=1 git commit`, `command -- git
            # commit` e `stdbuf -oL git commit`, a OPCAO do wrapper era lida
            # como "outro comando" e limpava a posicao antes do `git`. Os
            # commits voltavam a sumir do universo observado — a mesma
            # invariante que a cura anterior tinha acabado de restaurar.
            idx += 1
            while idx < total:
                nxt = tokens[idx]
                if nxt in _SEPARATORS:
                    break
                # `env -u NAME` leva o valor num token SEPARADO; consumir os
                # dois. As demais opcoes desta lista curta ou sao booleanas
                # (`-i`, `--`) ou carregam o valor coladas (`-oL`).
                if tok == "env" and nxt == "-u":
                    idx += 2
                    continue
                # `stdbuf -o L git commit` e forma valida: `-i/-o/-e` aceitam o
                # valor SEPARADO. So a forma colada (`-oL`) era tratada, e na
                # separada o `L` virava "o comando", matando a posicao antes do
                # `git` (pair-rail rodada 6, P2).
                if tok == "stdbuf" and nxt in ("-i", "-o", "-e"):
                    idx += 2
                    continue
                if nxt.startswith("-") or _ENV_ASSIGN_RE.match(nxt):
                    idx += 1
                    continue
                break
            continue
        if not at_command_position or tok != "git":
            at_command_position = False
            idx += 1
            continue
        # `git` at a command position: consume global options, find the verb.
        j = idx + 1
        foreign = False
        verb = None  # type: Optional[str]
        while j < total:
            nxt = tokens[j]
            if nxt in _SEPARATORS:
                break
            if nxt in _GIT_GLOBAL_VALUE_OPTS:
                if nxt in ("-C", "--git-dir", "--work-tree"):
                    foreign = True
                j += 2
                continue
            if nxt.startswith("--git-dir=") or nxt.startswith("--work-tree="):
                foreign = True
                j += 1
                continue
            if nxt.startswith("-"):
                j += 1
                continue
            verb = nxt
            break
        if verb == "commit":
            inv.is_commit = True
            inv.foreign_repo = foreign
            _parse_commit_args(tokens[j + 1:], inv)
            return inv
        at_command_position = False
        idx += 1
    return inv


def _parse_commit_args(args: List[str], inv: CommitInvocation) -> None:
    """Fill ``all_flag`` / ``amend`` / ``message`` / ``pathspecs``."""
    i = 0
    n = len(args)
    after_ddash = False
    while i < n:
        tok = args[i]
        if tok in _SEPARATORS:
            break
        if after_ddash:
            inv.pathspecs.append(tok)
            i += 1
            continue
        if tok == "--":
            after_ddash = True
            i += 1
            continue
        if tok in ("-a", "--all"):
            inv.all_flag = True
            i += 1
            continue
        if tok == "--amend":
            inv.amend = True
            i += 1
            continue
        if tok in ("-m", "--message"):
            if i + 1 < n:
                inv.message = args[i + 1]
                i += 2
                continue
            i += 1
            continue
        if tok.startswith("--message="):
            inv.message = tok[len("--message="):]
            i += 1
            continue
        if tok == _PATHSPEC_FROM_FILE or tok.startswith(_PATHSPEC_FROM_FILE + "="):
            # O commit passa a ser dirigido por paths que este hook NAO
            # resolve (o arquivo pode conter globs, exclusoes, diretorios).
            # Marcar como pathspec faz `_committed_paths()` devolver None e o
            # caller reportar `unparseable` — a MESMA resposta que o modulo ja
            # da para pathspec explicito, nao uma semantica nova.
            inv.pathspecs.append(_PATHSPEC_FROM_FILE)
            i += 2 if (tok == _PATHSPEC_FROM_FILE and i + 1 < n) else 1
            continue
        if tok in _COMMIT_VALUE_OPTS_LONG:
            # Consume the VALUE too, or it lands in `pathspecs` and makes an
            # ordinary commit look unparseable.
            i += 2 if i + 1 < n else 1
            continue
        if tok.startswith("--"):
            i += 1
            continue
        if tok in _COMMIT_VALUE_OPTS_SHORT:
            i += 2 if i + 1 < n else 1
            continue
        if tok.startswith("-") and len(tok) > 1:
            # Flags curtas combinadas (-am / -amv) E a forma COLADA
            # `-m"texto"` / `-am"texto"`, que o shlex entrega como UM token.
            # Tratar o sufixo inteiro como letras de flag perdia a mensagem
            # (marcadores [skip-ledger]/[hotfix] eram ignorados) e ainda podia
            # ligar `all_flag` por causa de um "a" DENTRO do texto
            # (pair-rail rodada 6, P2).
            letters = tok[1:]
            mi = letters.find("m")
            if mi >= 0:
                if "a" in letters[:mi]:
                    inv.all_flag = True
                attached = letters[mi + 1:]
                if attached:
                    inv.message = attached
                    i += 1
                    continue
                if i + 1 < n:
                    inv.message = args[i + 1]
                    i += 2
                    continue
                i += 1
                continue
            if "a" in letters:
                inv.all_flag = True
            i += 1
            continue
        inv.pathspecs.append(tok)
        i += 1


def classify_message(message: str) -> Optional[str]:
    """Operator-declared skip class for a commit message, or None.

    Returns one of ``operator_opt_out`` / ``hotfix`` / ``exploratory``. The
    message text NEVER leaves this function: only the enum does.
    """
    msg = (message or "").strip().lower()
    if not msg:
        return None
    for tag in _OPT_OUT_TAGS:
        if tag in msg:
            return "operator_opt_out"
    for tag in _HOTFIX_TAGS:
        if tag in msg:
            return "hotfix"
    for tag in _EXPLORATORY_TAGS:
        if tag in msg:
            return "exploratory"
    head = msg[:_MSG_TYPE_REGION]
    # Palavra NUA casa por FRONTEIRA, nunca por substring: `wip` dentro de
    # `swipe` fazia `feat: swipe gesture` virar uma isencao `exploratory`
    # FALSA, e isencao falsa corrompe exatamente a metrica da janela que este
    # rail existe para medir (pair-rail rodada 6, P2). Os TAGS acima seguem
    # por substring de proposito: sao delimitados (`[skip-ledger]`).
    for word in _HOTFIX_WORDS:
        if re.search(r"\b%s\b" % re.escape(word), head):
            return "hotfix"
    for word in _EXPLORATORY_WORDS:
        if re.search(r"\b%s\b" % re.escape(word), head):
            return "exploratory"
    return None


# --------------------------------------------------------------------------
# git plumbing (every call bounded; every failure fail-open)
# --------------------------------------------------------------------------

def _git(repo_root: Path, args: List[str], deadline: float) -> Optional[str]:
    """Run ``git <args>`` in ``repo_root``. None on ANY failure/timeout."""
    if time.monotonic() >= deadline:
        return None
    try:
        proc = subprocess.run(
            ["git"] + list(args),
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=min(_GIT_TIMEOUT_S, max(0.05, deadline - time.monotonic())),
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        return proc.stdout.decode("utf-8", "replace")
    except Exception:  # pragma: no cover
        return None


def _committed_paths(
    repo_root: Path, inv: CommitInvocation, deadline: float
) -> Optional[List[str]]:
    """Repo-relative paths this commit would carry, or None if unknowable.

    - default: the staged set (``git diff --cached --name-only``);
    - ``-a/--all``: staged ∪ tracked-modified (``git diff --name-only HEAD``);
    - explicit pathspecs: NOT resolved (globs, directories, exclusions) —
      returns None so the caller reports ``unparseable`` rather than
      inventing a set.
    """
    if inv.pathspecs:
        return None
    out = _git(repo_root, ["diff", "--cached", "--name-only", "-z"], deadline)
    if out is None:
        return None
    paths = [p for p in out.split("\0") if p]
    if inv.all_flag:
        extra = _git(repo_root, ["diff", "--name-only", "-z", "HEAD"], deadline)
        if extra is None:
            return None
        for p in extra.split("\0"):
            if p and p not in paths:
                paths.append(p)
    return paths[:_MAX_PATHS]


# --------------------------------------------------------------------------
# Observation state — the censored-universe counter
# --------------------------------------------------------------------------

def _state_path(repo_root: Path) -> Path:
    return repo_root.joinpath(*_STATE_SUBPATH)


def observe_commits_since(
    repo_root: Path, deadline: float
) -> Tuple[int, str]:
    """Return ``(commits_since_last_observation, state_kind)`` and re-anchor.

    ``fresh`` means "no prior anchor", so the 0 is structural — a report
    MUST NOT read it as "no unobserved commits". ``unavailable`` means git
    or the state file failed; the count is 0 and equally uninformative.
    """
    head = _git(repo_root, ["rev-parse", "HEAD"], deadline)
    head_sha = (head or "").strip()
    if not _SHA40_RE.match(head_sha):
        return 0, "unavailable"

    previous = None  # type: Optional[str]
    path = _state_path(repo_root)
    try:
        if path.is_file():
            blob = json.loads(path.read_text(encoding="utf-8") or "{}")
            if isinstance(blob, dict):
                cand = str(blob.get("last_observed_head") or "")
                if _SHA40_RE.match(cand):
                    previous = cand
    except Exception as exc:
        _breadcrumb("observation state unreadable: %s" % str(exc)[:80])

    count = 0
    kind = "fresh"
    if previous is not None:
        if previous == head_sha:
            count, kind = 0, "resumed"
        else:
            out = _git(
                repo_root,
                ["rev-list", "--count", "%s..%s" % (previous, head_sha)],
                deadline,
            )
            if out is None:
                kind = "unavailable"
            else:
                count, kind = _clamp_count((out or "").strip()), "resumed"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"last_observed_head": head_sha, "schema": "ledger-checkpoint/v1"},
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    except Exception as exc:
        _breadcrumb("observation state unwritable: %s" % str(exc)[:80])
    return count, kind


# --------------------------------------------------------------------------
# Scope derivation — PATHS ONLY (emenda r1-C6)
# --------------------------------------------------------------------------

def _ac_path_index(repo_root: Path, deadline: float) -> Dict[str, str]:
    """Map ``AC path -> PLAN-NNN`` by scanning plan files for the AC grammar.

    Bounded by ``_AC_SCAN_MAX_FILES`` / ``_AC_SCAN_MAX_BYTES`` / the wall
    deadline. On the first plan whose id repeats a path, the LOWEST plan id
    wins so the mapping is deterministic across runs.
    """
    index = {}  # type: Dict[str, str]
    plans_dir = repo_root / ".claude" / "plans"
    try:
        files = sorted(plans_dir.glob(_PLAN_FILE_GLOB))[:_AC_SCAN_MAX_FILES]
    except Exception:
        return index
    for plan_file in files:
        if time.monotonic() >= deadline:
            _breadcrumb("AC scan stopped at the wall budget")
            break
        match = _PLAN_FILE_ID_RE.match(plan_file.name)
        if match is None:
            continue
        plan_id = match.group(1)
        try:
            with plan_file.open("r", encoding="utf-8", errors="replace") as fh:
                text = fh.read(_AC_SCAN_MAX_BYTES)
        except OSError:
            continue
        for ac_path in _AC_PATH_RE.findall(text):
            candidate = ac_path.strip().strip("`").strip()
            # A leading "./" is a PREFIX, not a character class: `lstrip("./")`
            # would eat the leading dot of `.claude/...` and silently make
            # every AC path in this repo unmatchable.
            while candidate.startswith("./"):
                candidate = candidate[2:]
            if not candidate or candidate.startswith("<"):
                continue
            current = index.get(candidate)
            if current is None or plan_id < current:
                index[candidate] = plan_id
    return index


def derive_scope(
    paths: List[str], repo_root: Path, deadline: float
) -> Tuple[Optional[str], str, List[str]]:
    """``(plan_id, scope_source, in_scope_paths)`` from the commit's PATHS.

    NOTHING here consults session state, env, or the audit log. When several
    plans match, the one with the most in-scope paths wins; ties break on the
    lowest plan id, so the choice is reproducible.
    """
    by_plan = {}  # type: Dict[str, List[str]]
    sources = {}  # type: Dict[str, set]
    for path in paths:
        m = _PLAN_DIR_RE.match(path)
        if m is not None:
            plan_id = m.group(1)
            by_plan.setdefault(plan_id, []).append(path)
            sources.setdefault(plan_id, set()).add("plan_dir")

    unmatched = [p for p in paths if not _PLAN_DIR_RE.match(p)]
    if unmatched:
        index = _ac_path_index(repo_root, deadline)
        if index:
            for path in unmatched:
                plan_id = index.get(path)
                if plan_id is None:
                    for ac_path, candidate in index.items():
                        if ac_path.endswith("/") and path.startswith(ac_path):
                            plan_id = candidate
                            break
                        if path.startswith(ac_path + "/"):
                            plan_id = candidate
                            break
                if plan_id is not None:
                    by_plan.setdefault(plan_id, []).append(path)
                    sources.setdefault(plan_id, set()).add("plan_ac")

    if not by_plan:
        return None, "other", []
    best = sorted(by_plan.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0]
    plan_id = best[0]
    kinds = sources.get(plan_id, set())
    if kinds == {"plan_dir"}:
        source = "plan_dir"
    elif kinds == {"plan_ac"}:
        source = "plan_ac"
    elif kinds:
        source = "both"
    else:  # pragma: no cover - unreachable, kept total
        source = "other"
    return plan_id, source, best[1]


# --------------------------------------------------------------------------
# Ledger inspection (never edits, never quotes)
# --------------------------------------------------------------------------

def ledger_rel_path(plan_id: str) -> str:
    return ".claude/plans/%s/%s" % (plan_id, LEDGER_BASENAME)


def count_unverified_ac_claims(text: str) -> int:
    """Bullets that CLAIM an AC/US state without naming a verifier.

    A bullet is a line starting with ``-``/``*`` plus its indented
    continuation lines, so the verifier may sit on the next line. Returns a
    COUNT — never the text (repo is public; the wire carries no content).
    """
    bullets = []  # type: List[List[str]]
    for raw in (text or "").splitlines():
        stripped = raw.lstrip()
        if stripped[:2] in ("- ", "* ") or stripped[:2] in ("-\t", "*\t"):
            bullets.append([raw])
        elif bullets and raw[:1] in (" ", "\t"):
            bullets[-1].append(raw)
    unverified = 0
    for bullet in bullets:
        body = "\n".join(bullet)
        if _AC_ID_RE.search(body) and not _VERIFIER_RE.search(body):
            unverified += 1
    return unverified


def inspect_ledger(repo_root: Path, plan_id: str) -> Dict[str, Any]:
    """On-disk facts about a plan's ledger. Counts only, never content."""
    facts = {
        "exists": False,
        "size_bytes": 0,
        "over_ceiling": 0,
        "unverified_ac_claims": 0,
    }  # type: Dict[str, Any]
    path = repo_root / ledger_rel_path(plan_id)
    try:
        if not path.is_file():
            return facts
        facts["exists"] = True
        size = path.stat().st_size
        facts["size_bytes"] = int(size)
        facts["over_ceiling"] = 1 if size > LEDGER_MAX_BYTES else 0
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(_LEDGER_SCAN_MAX_BYTES)
        facts["unverified_ac_claims"] = count_unverified_ac_claims(text)
    except OSError as exc:
        _breadcrumb("ledger unreadable: %s" % str(exc)[:80])
    return facts


# --------------------------------------------------------------------------
# Audit emission — LOUD when the action is not registered yet
# --------------------------------------------------------------------------

#: Identity of the session being observed. Set ONCE per invocation from the
#: hook event, read by :func:`_emit`.
#:
#: Why it is not optional (pair-rail round 1, P1): this rail's whole purpose
#: is a measure-first window declared in SESSIONS (">= 20 sessions"), and a
#: row with no ``session_id`` cannot be counted into a session, nor
#: partitioned by project. Emitting the window's own telemetry without the
#: field the window is counted over would repeat the session-coupling
#: failure that PLAN-179 exists to cure (ADR-153: `resolve_plan_id` needed a
#: `plan_transition` FROM THE SAME SESSION and there were 2 in 12.515 lines).
#: Both allowlists already admit ``session_id`` and ``project``
#: (`audit_emit._LEDGER_CHECKPOINT_*_ALLOWLIST`) — only the caller was missing.
#:
#: ``project`` is DELIBERATELY not emitted, and the reason is local to this
#: module: no path ever reaches this rail's wire (the invariant its own
#: `test_no_ledger_content_reaches_the_audit_wire` enforces by asserting no
#: emitted value contains "/"), and the correct project identity is the
#: `runtime_paths` slug — re-deriving a slug locally is exactly the M4 class
#: PLAN-182 closed, so it is NOT open-coded here. Nothing is lost: since
#: PLAN-182 W1 the audit directory and HMAC key are already PER PROJECT, so
#: rows are partitioned by project by LOCATION, not by a field. Wiring the
#: single resolver into this hook is its own change, with its own contract
#: tests — not a line slipped into a ceremony.
_IDENTITY = {"session_id": ""}

#: Bounded shape for the id that reaches the HMAC-chained event: identifier
#: characters only, hard-capped. An unbounded string from hook input has no
#: business in a signed record.
_SESSION_ID_MAX = 64
_SESSION_ID_OK = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
)


def _clean_session_id(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    kept = "".join(ch for ch in raw if ch in _SESSION_ID_OK)
    return kept[:_SESSION_ID_MAX]


def _set_identity(event: Dict[str, Any]) -> None:
    """Capture session identity from the hook event, once per invocation."""
    _IDENTITY["session_id"] = _clean_session_id(event.get("session_id"))


def _resolve_repo_root(start: Path, deadline: float) -> Path:
    """Git TOP-LEVEL for ``start``, or ``start`` itself if git cannot say.

    Why this exists (pair-rail round 2, P1): the hook event's ``cwd`` follows
    the session, and a ``CwdChanged`` into a subdirectory made every
    filesystem lookup in this module point at the SUBDIRECTORY. Git does not
    play along — ``diff --cached --name-only`` answers ROOT-relative — so the
    paths and the tree disagreed:

      * ``_ac_path_index`` scanned ``<subdir>/.claude/plans`` (usually absent)
        ⇒ AC-scoped commits silently classified out of scope;
      * ``inspect_ledger`` looked for ``<subdir>/.claude/plans/PLAN-NNN/
        LEDGER.md`` ⇒ an existing ledger reported absent;
      * ``_state_path`` WROTE observation state into ``<subdir>/.claude/state``
        ⇒ the commit counter fragmented into nested, un-gitignored dirs.

    Resolving the top level once, before any path is derived, closes all
    three. Fail-OPEN by design (this is not a security matcher): if git is
    unavailable the caller keeps the previous behaviour and the existing
    ``no_repo`` route reports it honestly.
    """
    out = _git(start, ["rev-parse", "--show-toplevel"], deadline)
    if out:
        first = out.strip().splitlines()[0].strip() if out.strip() else ""
        if first:
            try:
                top = Path(os.path.realpath(first))
            except (OSError, ValueError):
                return start
            if top.is_dir():
                return top
    return start


def _emit(action: str, **fields: Any) -> str:
    """Emit a closed-enum event. Returns the emit OUTCOME for the caller.

    ``"emitted"`` | ``"unregistered"`` | ``"unavailable"`` | ``"error"``.
    The unregistered case is the pre-ceremony reality (``audit_emit.py`` is
    canonical and this action lands with the W2 ceremony) and it is LOUD:
    a window that silently loses its telemetry would decide the ledger's
    life on a number it does not have.

    Session identity is injected here rather than at every call site, so a
    future emitter cannot forget it.
    """
    fields.setdefault("session_id", _IDENTITY["session_id"])
    if not _AUDIT_EMIT_AVAILABLE or _audit_emit is None:
        _loud("audit_emit unavailable — %s NOT recorded" % action)
        return "unavailable"
    known = getattr(_audit_emit, "_KNOWN_ACTIONS", None)
    if known is not None and action not in known:
        _loud(
            "audit action %r is NOT registered in .claude/hooks/_lib/"
            "audit_emit.py (_KNOWN_ACTIONS + a deny-by-default scrub branch) "
            "nor in SPEC/v1/audit-log.schema.md — the W2 ceremony has not "
            "landed, so this checkpoint advisory is NOT on the audit wire "
            "and the advisory-window counters are INCOMPLETE." % action
        )
        return "unregistered"
    try:
        _audit_emit.emit_generic(action, **fields)
        return "emitted"
    except Exception as exc:  # pragma: no cover - fail-open
        _loud("emit %s failed: %s" % (action, str(exc)[:120]))
        return "error"


def _would_block_flag(outcome: str) -> int:
    """1 when the FUTURE enforce flip would have denied this commit."""
    return 1 if outcome == "ledger_missing" else 0


def emit_skipped(
    reason: str, plan_id: Optional[str], commits_since: int, state_kind: str
) -> str:
    return _emit(
        ACTION_SKIPPED,
        reason=reason if reason in _SKIP_REASONS else "other",
        plan_id=plan_id if plan_id else "unknown",
        commits_since_last_observation=_clamp_count(commits_since),
        state_kind=state_kind if state_kind in _STATE_KINDS else "unavailable",
        would_block=0,
    )


def emit_recorded(
    outcome: str,
    plan_id: str,
    scope_source: str,
    in_scope_path_count: int,
    facts: Dict[str, Any],
    commits_since: int,
    state_kind: str,
) -> str:
    return _emit(
        ACTION_RECORDED,
        outcome=outcome if outcome in _OUTCOMES else "other",
        plan_id=plan_id or "unknown",
        scope_source=scope_source if scope_source in _SCOPE_SOURCES else "other",
        in_scope_path_count=_clamp_count(in_scope_path_count),
        ledger_size_bucket_kib=_clamp_count(
            int(facts.get("size_bytes") or 0) // 1024
        ),
        over_ceiling=1 if facts.get("over_ceiling") else 0,
        unverified_ac_claim_count=_clamp_count(
            facts.get("unverified_ac_claims")
        ),
        commits_since_last_observation=_clamp_count(commits_since),
        state_kind=state_kind if state_kind in _STATE_KINDS else "unavailable",
        would_block=_would_block_flag(outcome),
    )


# --------------------------------------------------------------------------
# Advisory text (identifiers only — no ledger content, ever)
# --------------------------------------------------------------------------

def build_advisory(
    outcome: str, plan_id: str, facts: Dict[str, Any], emit_state: str
) -> str:
    lines = []  # type: List[str]
    rel = ledger_rel_path(plan_id)
    if outcome == "ledger_missing":
        lines.append(
            "[PLAN-179 W2 ADVISORY — not a block] This commit lands work "
            "scoped to %s but does not update %s. Durable state belongs at "
            "the WORK BOUNDARY, not at session death: add the checkpoint "
            "(current unit, ACs with verified state, last commit, decisions, "
            "open blockers) and include the file in THIS commit."
            % (plan_id, rel)
        )
    elif outcome == "ledger_absent_from_plan":
        lines.append(
            "[PLAN-179 W2 ADVISORY — not a block] This commit lands work "
            "scoped to %s, which has no %s yet. Create one if this plan "
            "spans sessions; skip it if the plan is a single-session unit."
            % (plan_id, rel)
        )
    if facts.get("over_ceiling"):
        lines.append(
            "%s is over the %d-token ceiling (~%d bytes). Archive the oldest "
            "sections to .claude/plans/%s/%s and keep the current unit + open "
            "blockers, or the ledger becomes the context floor W3 exists to "
            "cut." % (rel, LEDGER_MAX_TOKENS, LEDGER_MAX_BYTES, plan_id,
                      LEDGER_ARCHIVE_BASENAME)
        )
    unverified = _clamp_count(facts.get("unverified_ac_claims"))
    if unverified:
        lines.append(
            "%d ledger entr%s name an AC/US id without a verifier. Every "
            "AC-state claim must carry `verifier: `<command>` exit=<n>` — a "
            "WRONG entry is worse than a missing one, because the next "
            "session writes its checkpoint from a corrupted premise."
            % (unverified, "y" if unverified == 1 else "ies")
        )
    if lines:
        lines.append(
            "Content rule: verbatim identifiers ONLY (paths, SHAs, "
            "PLAN-/ADR-/AC-ids) — never transcript bodies (public repo). "
            "This rail is ADVISORY; kill it with %s=0." % KILL_SWITCH_ENV
        )
    if emit_state == "unregistered":
        lines.append(
            "INSTRUMENT DEFECT: the ledger-checkpoint audit actions are not "
            "registered in .claude/hooks/_lib/audit_emit.py or SPEC/v1 — the "
            "PLAN-179 W2 ceremony has not landed, so this advisory is NOT "
            "being counted in the measure-first window."
        )
    elif emit_state in ("unavailable", "error"):
        lines.append(
            "INSTRUMENT DEFECT: the audit emit failed (%s) — this advisory "
            "is not counted in the window." % emit_state
        )
    return "\n".join(lines)


def _output(additional_context: str, system_message: str = "") -> Dict[str, Any]:
    """PreToolUse output. NEVER carries ``permissionDecision`` — there is no
    deny path in this module (advisory-first; the enforce flip is a future
    ceremony that must add the branch deliberately)."""
    if not additional_context and not system_message:
        return {}
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": additional_context,
        }
    }  # type: Dict[str, Any]
    if system_message:
        out["systemMessage"] = system_message
    return out


# --------------------------------------------------------------------------
# Gate
# --------------------------------------------------------------------------

def gate(event: Dict[str, Any], cwd: Optional[str] = None) -> Dict[str, Any]:
    """Advisory work-boundary check. ALWAYS allows (returns no decision)."""
    # Identity FIRST: every emission below inherits it via _emit, and the
    # master-kill path returns before emitting anything at all.
    _set_identity(event)
    if _flag_on(MASTER_KILL_ENV):
        return {}
    tool_name = str(event.get("tool_name") or "")
    if tool_name and tool_name != "Bash":
        return {}
    tool_input = event.get("tool_input")
    command = ""
    if isinstance(tool_input, dict):
        command = str(tool_input.get("command") or "")
    inv = parse_git_commit(command)
    if not inv.is_commit and not inv.unparseable:
        # Not a commit at all: silent by design (every Bash call lands here).
        return {}

    deadline = time.monotonic() + TIME_BUDGET_S
    _start = Path(
        os.path.realpath(cwd or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    )
    # The event's cwd may be a SUBDIRECTORY of the repo; git answers
    # root-relative, so every path below has to be derived from the TOP LEVEL.
    repo_root = _resolve_repo_root(_start, deadline)
    commits_since, state_kind = observe_commits_since(repo_root, deadline)

    if _flag_on(ENFORCE_ENV) and not ENFORCE_FLIP_IMPLEMENTED:
        _loud(
            "%s=1 but the enforce flip is NOT implemented (advisory window "
            "still open: >= %d days / >= %d sessions + a would-block/TP-FP "
            "table). Still ADVISORY."
            % (ENFORCE_ENV, ADVISORY_WINDOW_MIN_DAYS, ADVISORY_WINDOW_MIN_SESSIONS)
        )

    if (os.environ.get(KILL_SWITCH_ENV) or "1").strip() == "0":
        emit_skipped("kill_switch", None, commits_since, state_kind)
        return {}
    if inv.unparseable or inv.foreign_repo:
        emit_skipped("unparseable", None, commits_since, state_kind)
        return {}

    paths = _committed_paths(repo_root, inv, deadline)
    if paths is None:
        reason = "unparseable" if inv.pathspecs else "no_repo"
        emit_skipped(reason, None, commits_since, state_kind)
        return {}
    if not paths:
        emit_skipped("out_of_scope_paths", None, commits_since, state_kind)
        return {}

    plan_id, scope_source, in_scope = derive_scope(paths, repo_root, deadline)
    if plan_id is None:
        reason = (
            "budget_exhausted" if time.monotonic() >= deadline
            else "out_of_scope_paths"
        )
        emit_skipped(reason, None, commits_since, state_kind)
        return {}

    # Operator-declared exemptions are classified AFTER scope, on purpose:
    # a hotfix outside plan scope must count as out_of_scope_paths, or the
    # window's hotfix rate is inflated by commits the rail never wanted.
    declared = classify_message(inv.message)
    if declared is not None:
        emit_skipped(declared, plan_id, commits_since, state_kind)
        return {}

    rel = ledger_rel_path(plan_id)
    facts = inspect_ledger(repo_root, plan_id)
    if rel in paths:
        outcome = "ledger_updated"
    elif facts.get("exists"):
        outcome = "ledger_missing"
    else:
        outcome = "ledger_absent_from_plan"

    emit_state = emit_recorded(
        outcome, plan_id, scope_source, len(in_scope), facts,
        commits_since, state_kind,
    )
    advisory = build_advisory(outcome, plan_id, facts, emit_state)
    system_message = ""
    if emit_state in ("unregistered", "unavailable", "error"):
        system_message = (
            "check_ledger_checkpoint: audit emit %s — PLAN-179 W2 advisory "
            "window is not counting this commit." % emit_state
        )
    return _output(advisory, system_message)


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
        if not isinstance(hook_input, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as exc:
        _breadcrumb("fail-open (stdin): %s" % str(exc)[:120])
        print("{}")
        return
    try:
        print(json.dumps(gate(hook_input, hook_input.get("cwd"))))
    except Exception as exc:  # pragma: no cover - fail-open invariant
        _breadcrumb("fail-open: %s" % str(exc)[:120])
        print("{}")


if __name__ == "__main__":
    main()
