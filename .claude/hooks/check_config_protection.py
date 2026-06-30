#!/usr/bin/env python3
"""Governance Hook: adopter linter/formatter config protection (PLAN-124 WS-2).

Registered in `.claude/settings.json` under `hooks.PreToolUse` with matcher
`Edit|Write|MultiEdit`. Runs via the `_python-hook.sh` shim. Ported (re-implemented
in stdlib Python, MIT-attributed to `affaan-m/ECC`
`scripts/hooks/config-protection.js`) from the ECC value-harvest study.

## The insight (why this exists)

An agent told to "make the lint gate pass" has two paths: fix the offending
CODE, or *relax the config* that defines the gate. The cheap, wrong path is to
weaken the config (loosen an eslint rule, drop a ruff select, raise a prettier
printWidth) so the gate stops complaining. This is the SAME principle as our
canonical guard ("don't relax the gate to pass it"), generalized to an ADOPTER
project's quality-gate configs. This hook keeps an agent from silently lowering
a project's quality bar.

## DESIGN CHOICE (Owner pre-resolved for this build — revisitable)

We use **block-any-edit of an EXISTING config** (ECC parity, simpler) rather
than weakening-only / semantic-diff detection. Rationale:

* Parsing every linter config dialect (JSON / YAML / TOML / JS / INI) and
  deciding "did this edit WEAKEN the gate?" is dialect-specific, fragile, and a
  large attack surface for false-negatives. A semantic-weakening detector that
  is wrong in the agent's favor is worse than a blunt block.
* First-time CREATION is always allowed (an agent legitimately scaffolds a new
  config). The friction only lands when an agent tries to MODIFY a config that
  the project already committed to — exactly the "relax the gate" moment.

Trade-off (documented so this can be revisited): legitimate config maintenance
(e.g. adding a new rule, bumping a plugin) is also blocked and must be done with
the escape hatch (per-repo disable file or env). If that friction proves too
high in practice, swap this for weakening-only detection — the allowlist and
fail-mode contract below stay the same.

## Allowlist (UNAMBIGUOUS adopter linter/formatter configs ONLY)

Matched by **basename** (lstat-based exists-check on the resolved target). We
deliberately match ONLY files whose sole purpose is to configure a linter or
formatter, so a block is never a surprise:

    JS/TS linters/formatters : .eslintrc, .eslintrc.{js,cjs,mjs,json,yml,yaml},
                               eslint.config.{js,cjs,mjs,ts},
                               .prettierrc, .prettierrc.{js,cjs,mjs,json,yml,yaml,toml},
                               prettier.config.{js,cjs,mjs,ts},
                               biome.json, biome.jsonc, tslint.json,
                               .stylelintrc, .stylelintrc.{js,cjs,json,yml,yaml}
    Python linters           : .ruff.toml, ruff.toml, .flake8
    Markdown / shell linters : .markdownlint.{json,jsonc,yml,yaml,yaml},
                               .markdownlintrc, .shellcheckrc

### Deliberately EXCLUDED (ambiguous / shared / governance — NOT this hook's job)

* `pyproject.toml` / `setup.cfg` / `package.json` / `tox.ini` — shared, multi-
  purpose files (deps, build, packaging). Blocking every edit to them would be a
  constant false-positive; a `[tool.ruff]` section can live there but matching by
  basename keeps this hook unambiguous (plan §WS-2: "match by basename
  allowlist; ... EXCLUDE ambiguous shared files").
* `.claude/settings.json`, `pytest.ini`, and every governance config — those are
  the CANONICAL guard's job (`check_canonical_edit.py` / `_CANONICAL_GUARDS`),
  NOT a duplicate weaker adopter-linter hook (debate K6 / MF-L). A second weaker
  guard on governance configs = bypass-by-confusion + risks blocking our own
  config maintenance. This hook is for ADOPTER linters only.

## Fail-mode contract (MF-F / debate C5)

* **ENOENT (target does not exist) => ALLOW** — first-time creation is fine.
* **Truncation / parse-ambiguity of the tool input => fail-CLOSED block**
  (this is a safety surface), but BOUNDED: only when the tool name is a write
  tool AND we cannot extract a usable file path do we treat the input as
  ambiguous-and-block; a clean parse with a non-allowlisted path is a plain
  ALLOW. An infra/parse error of the HOOK ITSELF still fails OPEN (a hook bug
  must never brick the session — §5 doctrine).
* **Dangling symlink (target is a symlink whose link-target is missing) =>
  BLOCK** — treat as existing (the config slot is occupied; `os.lstat`
  succeeds on a dangling symlink, so it is correctly seen as "exists").
* Raw tool input is **NEVER** echoed into stderr/audit beyond the bare
  basename + the resolved path.

## Escape hatches (both tested on AND off)

* Per-repo disable file: `<CLAUDE_PROJECT_DIR>/.claude/.config-protection-disable`
  (presence => allow). Lets an adopter opt the whole repo out.
* Env kill-switch: `CEO_CONFIG_PROTECTION=0` => allow.
* Advisory mode (USER ceremony): `CEO_CONFIG_PROTECTION_ADVISORY=1` => never
  block; instead ALLOW + attach a `systemMessage` steer. The `--ceremony user`
  install wires this (non-blocking) variant; the maintainer ceremony leaves it
  unset (BLOCKING).

## Output contract

Writes a single-line JSON decision to stdout via the Adapter Layer:

    {}                                              (allow)
    {"systemMessage":"..."}                         (advisory allow — user ceremony)
    {"decision":"block","reason":"BLOCKED: ..."}    (block — maintainer ceremony)

Exit code is 0 in all cases — Claude Code reads the decision from stdout.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# Make the _lib package importable — hooks live in .claude/hooks/ and
# _lib is a sibling package.
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import contract as _contract  # noqa: E402
from _lib.adapters import claude as _claude_adapter  # noqa: E402


# ---------------------------------------------------------------------------
# Activation / escape-hatch contract
# ---------------------------------------------------------------------------

KILL_SWITCH_ENV = "CEO_CONFIG_PROTECTION"          # "0" => disabled (allow)
ADVISORY_ENV = "CEO_CONFIG_PROTECTION_ADVISORY"    # "1" => never block (user ceremony)
DISABLE_FILE = ".claude/.config-protection-disable"  # per-repo opt-out (relative to project dir)

# Write tools this hook governs. Read/Glob/Grep are non-mutating and the
# matcher in settings.json is narrowed to the write set; we re-assert here.
_WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit"})


# ---------------------------------------------------------------------------
# Allowlist — UNAMBIGUOUS adopter linter/formatter config basenames ONLY.
# ---------------------------------------------------------------------------

# Exact basenames (no extension wildcard needed).
_EXACT_BASENAMES = frozenset({
    # JS/TS linters + formatters
    "biome.json",
    "biome.jsonc",
    "tslint.json",
    # Python linters
    ".ruff.toml",
    "ruff.toml",
    ".flake8",
    # Shell
    ".shellcheckrc",
    # rc-style (no extension)
    ".eslintrc",
    ".prettierrc",
    ".stylelintrc",
    ".markdownlintrc",
})

# (stem, extension-set) families. A basename matches if it equals
# ``<stem>`` exactly OR ``<stem>.<ext>`` with ext in the allowed set. This
# captures the dotfile-with-optional-extension idiom (.eslintrc.json,
# eslint.config.mjs, .prettierrc.yaml, …) without matching unrelated files.
_CONFIG_EXTS = frozenset({"js", "cjs", "mjs", "ts", "json", "jsonc", "yml", "yaml", "toml"})

_STEM_FAMILIES = (
    ".eslintrc",
    "eslint.config",
    ".prettierrc",
    "prettier.config",
    ".stylelintrc",
    ".markdownlint",
)


def is_protected_basename(basename: str) -> bool:
    """True iff `basename` is an UNAMBIGUOUS adopter linter/formatter config.

    Pure function. Matches the exact-basename set OR a ``<stem>``/``<stem>.<ext>``
    family member (ext restricted to known config extensions). Anything else
    (incl. ambiguous shared files like pyproject.toml / setup.cfg /
    package.json, and every governance config) is NOT protected here.
    """
    if not basename:
        return False
    if basename in _EXACT_BASENAMES:
        return True
    for stem in _STEM_FAMILIES:
        if basename == stem:
            return True
        if basename.startswith(stem + "."):
            ext = basename[len(stem) + 1:]
            if ext in _CONFIG_EXTS:
                return True
    return False


# ---------------------------------------------------------------------------
# Existence check (lstat — a dangling symlink counts as "exists" => block)
# ---------------------------------------------------------------------------


def target_exists(path: Path) -> bool:
    """True iff `path` already exists on disk (lstat — does NOT follow symlinks).

    ``os.lstat`` succeeds on a dangling symlink (the link node exists even if its
    target is missing), so a dangling symlink is correctly treated as
    "exists" => BLOCK (the config slot is occupied). ENOENT (truly absent) =>
    does-not-exist => the caller ALLOWS the create. Any other OSError (e.g.
    a permission error walking the path) is treated as "exists" — fail-CLOSED on
    the safety surface (we cannot prove the file is absent).
    """
    try:
        os.lstat(str(path))
        return True
    except FileNotFoundError:
        return False
    except OSError:
        # Cannot prove absence (permission / loop / name-too-long) → treat as
        # existing so we do not silently allow a weakening edit.
        return True


def _is_disabled_for_repo(project_dir: Optional[Path]) -> bool:
    """True iff the per-repo disable file exists under the project dir."""
    if project_dir is None:
        return False
    try:
        return (project_dir / DISABLE_FILE).exists()
    except OSError:
        return False


def _project_dir(env: dict) -> Optional[Path]:
    raw = (env.get("CLAUDE_PROJECT_DIR") or "").strip()
    if not raw:
        return None
    try:
        return Path(raw)
    except (ValueError, OSError):
        return None


def _resolve_target(file_path: str, project_dir: Optional[Path]) -> Optional[Path]:
    """Resolve `file_path` to an absolute Path (against the project dir if
    relative). Returns None when the path is empty/unparseable.

    NOTE: we do NOT call ``.resolve()`` (which would follow symlinks and could
    collapse a dangling-symlink target) — we only need the basename + the
    on-disk lstat, both of which work on the un-followed path. Relative paths are
    joined to the project dir so a bare ``.eslintrc`` resolves correctly.
    """
    s = (file_path or "").strip()
    if not s:
        return None
    try:
        p = Path(s)
    except (ValueError, OSError):
        return None
    if not p.is_absolute() and project_dir is not None:
        p = project_dir / p
    return p


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

_STEER = (
    "fix the code, not the config. An agent should not relax a project's "
    "linter/formatter gate to make it pass — change the offending code instead. "
    "If this edit is a legitimate config change, use the escape hatch: set "
    "CEO_CONFIG_PROTECTION=0 (session) or create "
    "<repo>/.claude/.config-protection-disable (per-repo)."
)


def _advisory(env: dict) -> bool:
    return (env.get(ADVISORY_ENV) or "").strip() == "1"


def _kill_switched(env: dict) -> bool:
    return (env.get(KILL_SWITCH_ENV) or "").strip() == "0"


def decide(
    event: "_contract.NormalizedEvent",
    *,
    env: Optional[dict] = None,
) -> _contract.Decision:
    """Return the allow/block Decision for a write event under WS-2.

    Pure-ish: `env` defaults to the process env (injectable for tests).
    Block-any-edit of an EXISTING allowlisted adopter linter/formatter config;
    ENOENT (create) and non-allowlisted paths ALLOW. Advisory mode never blocks
    (allow + systemMessage steer). Fail-CLOSED on a write tool with no usable
    file path (truncation/parse-ambiguity safety surface).
    """
    src = env if env is not None else os.environ

    # Kill-switch / per-repo disable → allow (escape hatch).
    project_dir = _project_dir(src)
    if _kill_switched(src) or _is_disabled_for_repo(project_dir):
        return _contract.allow()

    tool = event.tool_name or ""
    # A tool outside the write set should never reach here (matcher is narrowed),
    # but if it does, this hook has nothing to say → allow.
    if tool not in _WRITE_TOOLS:
        return _contract.allow()

    file_path = event.file_path or str((event.tool_input or {}).get("file_path") or "")
    target = _resolve_target(file_path, project_dir)

    if target is None:
        # A write tool with no usable file path = truncation / parse-ambiguity of
        # the tool input → fail-CLOSED (BOUNDED to write tools only). In advisory
        # mode this surfaces as a steer rather than a hard block.
        reason = (
            "BLOCKED: a write tool with no resolvable file_path (truncated or "
            "ambiguous tool input) — cannot prove this is not a linter/formatter "
            "config edit (fail-CLOSED safety surface, PLAN-124 WS-2)."
        )
        if _advisory(src):
            return _contract.allow(system_message="[config-protection] " + reason)
        return _contract.block(reason)

    basename = target.name
    if not is_protected_basename(basename):
        # Not an adopter linter/formatter config → not our concern → allow.
        return _contract.allow()

    if not target_exists(target):
        # First-time creation of a config is always fine.
        return _contract.allow()

    # An EXISTING adopter linter/formatter config is being modified → block
    # (block-any-edit design choice). Name ONLY the basename + resolved path —
    # never the raw tool input (no diff / content echo).
    reason = (
        f"BLOCKED: {tool} would modify the existing linter/formatter config "
        f"'{basename}' ({target}) — {_STEER}"
    )
    if _advisory(src):
        return _contract.allow(system_message="[config-protection] " + reason)
    return _contract.block(reason)


def main() -> int:
    """Hook entry point: read stdin via Adapter Layer, decide, write stdout.

    Fail-OPEN on any infra/parse error of the HOOK ITSELF (a hook bug must NEVER
    block the user session); the in-:func:`decide` truncation case is the only
    fail-CLOSED path and it is bounded to write tools with no usable path.
    """
    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
        if event.parse_error:
            # An adapter-level stdin parse error is an INFRA problem with the
            # hook's own input plumbing → fail-OPEN (allow), distinct from the
            # in-decide "write tool with no file path" ambiguity which is
            # fail-CLOSED. A hook bug must never brick the session (§5 doctrine).
            print(
                f"[check_config_protection] WARN: stdin parse error: "
                f"{event.parse_error}",
                file=sys.stderr,
            )
            _claude_adapter.emit_decision(_contract.allow())
            return 0
        decision = decide(event)
        _claude_adapter.emit_decision(decision)
        return 0
    except Exception as e:  # pragma: no cover — fail-open on hook bug
        print(
            f"[check_config_protection] FATAL: {e.__class__.__name__}: {e}",
            file=sys.stderr,
        )
        _claude_adapter.emit_decision(_contract.allow())
        return 0


if __name__ == "__main__":
    sys.exit(main())
