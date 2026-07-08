#!/usr/bin/env python3
"""Harness-config gate: runtime-resolution model + behavioral positive controls.

PLAN-153 Wave E item 1 (ADR-173, allocated by PLAN-153 — static side +
replay harness). Extends `.claude/scripts/check-active-hooks-executable.py`
(which owns the exists+exec-bit hygiene sweep and is DELEGATED to, not
duplicated — see ``run_exec_bit_gate``) with the checks that a repo-root
static scan structurally cannot see:

1. **Runtime resolution (check ``runtime_resolution``)** — models how the
   Claude Code harness ACTUALLY resolves a hook ``command`` at fire time:

   - The harness guarantees ``$CLAUDE_PROJECT_DIR`` is set; it does NOT
     guarantee the shell's cwd is the repo root. A command that reaches
     into ``.claude/...`` without anchoring on ``$CLAUDE_PROJECT_DIR`` (or
     an absolute path) is cwd-dependent: it may work in dev and be a DEAD
     RAIL in production. This is the S254 lesson — the v1.0.0 pair-rail
     PreToolUse gate was dead because ``settings.json`` carried a relative
     shim path that resolved to nothing at runtime, and the shim then
     fail-opened with ``{}``.
   - The ``_python-hook.sh`` shim resolves its script ARGUMENT relative to
     the shim's OWN directory, not cwd (`_python-hook.sh:274` computes
     ``HOOKS_DIR`` from ``dirname "${BASH_SOURCE[0]}"``; `:281` builds
     ``HOOK_SCRIPT="$HOOKS_DIR/$1"``). So a bare ``check_x.py`` argument is
     fine — but ONLY if the shim path itself resolves.
   - A registered script that does not exist at its runtime-resolved path
     is a silent fail-open: the shim prints ``{}`` and exits 0
     (`_python-hook.sh:284-288`). Static repo-root existence checks miss
     this whole class; this gate goes RED on it.

2. **Inline-secret scan (check ``inline_secret``)** — every string value in
   the settings JSON is scanned with the versioned catalog in
   ``_lib/secret_patterns.py`` (fallback: minimal built-in regexes when the
   lib is unavailable). Matched content is NEVER echoed — only the family
   id and JSON path.

3. **Missing-deny detection (check ``deny_baseline``)** — ``DENY_BASELINE``
   (module-level constant, integrator-owned) must be a subset of
   ``permissions.deny``. Live baseline mirrors ``.claude/settings.json``
   lines 644-653 at authoring time.

4. **Intentional no-op annotation (check ``noop_hook``)** — a hook whose
   command is a constant emitter (``echo``/``printf``/``true``/``:``) is a
   rail that inspects nothing. That is RED unless explicitly opted in via:
   (a) the ``[harness-noop-ok]`` marker inside the matcher entry's
   ``_comment``; (b) a line in ``.claude/hooks/harness-noop-allowlist.txt``
   (substring match against the command); or (c)
   ``DEFAULT_NOOP_ALLOWLIST_SUBSTRINGS`` below. A generalized
   ``[harness-resolution-ok]`` marker likewise waives runtime-resolution
   findings for a single entry that manages its own cwd (rare; explicit).

5. **Behavioral positive controls (``--replay``)** — the Wave E doctrine:
   what certifies a security rail alive is a REPLAYED planted violation the
   rail MUST block, asserted red. ``run_replay`` feeds each hook listed in
   ``REQUIRED_REPLAY_CONTROLS`` a known-bad fixture on stdin (inert JSON
   data under ``.claude/hooks/tests/fixtures/harness-config/replay/``),
   inside a scrubbed hermetic env (temp HOME/GNUPGHOME/audit dir; no
   CEO_* session overrides can leak in), and asserts the stdout decision is
   block-shaped. A fixture that is missing, unparseable, tampered
   (``expect`` != ``block``), or that stops firing REDDENS the run.

Failure doctrine (house rules):
- This is a CI/preflight GATE, not a registered session hook: it fails
  LOUD (exit != 0), never silently green.
- Fail-CLOSED on input the matcher cannot parse: an unparseable hook
  command or settings file is a finding, not a skip (precedent:
  ``check_bash_safety.py`` ``_e3`` whole-command parse gate).
- ``CEO_SOTA_DISABLE=1`` skips the OPTIONAL replay machinery (prints a
  notice; static checks still run).

Exit codes: 0 all green; 1 one or more RED findings; 2 settings file
malformed/unreadable (mirrors check-active-hooks-executable.py).

Stdlib-only, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple

_THIS_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# _lib import (works when landed at .claude/hooks/; degrades when not)
# ---------------------------------------------------------------------------
try:  # plain import — pytest conftest puts the hooks dir on sys.path
    from _lib import secret_patterns as _secret_patterns  # type: ignore
except Exception:  # pragma: no cover - staged/degraded environments
    try:
        if str(_THIS_DIR) not in sys.path:
            sys.path.insert(0, str(_THIS_DIR))
        from _lib import secret_patterns as _secret_patterns  # type: ignore
    except Exception:
        _secret_patterns = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Integrator-owned constants
# ---------------------------------------------------------------------------

#: Deny entries that MUST be present in ``permissions.deny`` of every
#: settings file that declares a ``permissions`` object. INTEGRATOR-OWNED:
#: extend here (single source of truth) — the settings check reads this.
#: Seeded from the live ``.claude/settings.json`` permissions.deny
#: (lines 644-653 at PLAN-153 Wave E authoring time).
DENY_BASELINE: Tuple[str, ...] = (
    "Bash(git push --force*)",
    "Edit(PROTOCOL.md)",
    "Write(PROTOCOL.md)",
    "Edit(.claude/settings.json)",
    "Write(.claude/settings.json)",
    "Edit(SPEC/**)",
    "Write(SPEC/**)",
)

#: Marker an integrator places inside a matcher entry's ``_comment`` to
#: declare a constant-emitter hook INTENTIONAL (e.g. an advisory echo).
NOOP_MARKER = "[harness-noop-ok]"

#: Marker that waives runtime-resolution findings for ONE entry that
#: provably manages its own cwd (e.g. ``cd "$CLAUDE_PROJECT_DIR" && ...``).
RESOLUTION_WAIVER_MARKER = "[harness-resolution-ok]"

#: Optional allowlist file — one substring per line, ``#`` comments allowed.
#: A no-op hook whose command CONTAINS a listed substring passes.
NOOP_ALLOWLIST_REL = ".claude/hooks/harness-noop-allowlist.txt"

#: Module-level seed so the LIVE repo lands green: the POST-AGENT advisory
#: echo registered at .claude/settings.json:319-320 is a known-intentional
#: no-op. Integrator: prefer migrating this to the ``[harness-noop-ok]``
#: marker in that entry's ``_comment`` (settings.json is guarded; this seed
#: exists so landing this gate does not require a settings edit).
DEFAULT_NOOP_ALLOWLIST_SUBSTRINGS: Tuple[str, ...] = (
    "POST-AGENT: Check git diff",
)

#: Behavioral positive controls: (hook file under .claude/hooks/, fixture
#: file under the replay fixtures dir). Every entry is REQUIRED — a missing
#: fixture reddens the run, so a control cannot silently stop firing.
REQUIRED_REPLAY_CONTROLS: Tuple[Tuple[str, str], ...] = (
    ("check_canonical_edit.py", "canonical_edit_unauthorized.json"),
    ("check_bash_safety.py", "bash_safety_destructive.json"),
    ("check_agent_spawn.py", "agent_spawn_named_no_skill_content.json"),
)

#: Default replay fixtures location (repo-relative).
REPLAY_FIXTURES_REL = ".claude/hooks/tests/fixtures/harness-config/replay"

#: Placeholder replaced by the absolute repo root in fixture payloads.
#: Built from fragments so the doubled-brace PROJECT_DIR marker never appears
#: as a contiguous token at rest in this shipped hook. The install-time
#: placeholder scanner (test_install_sh_placeholders) greps every installed
#: .claude/ file for doubled-brace UPPER_SNAKE markers; this value is a RUNTIME
#: fixture marker (not an install-time --flag placeholder), so it must not
#: false-positive that scan. The concatenation rebuilds the exact value.
FIXTURE_PROJECT_PLACEHOLDER = "{{" + "PROJECT_DIR" + "}}"

# Settings files scanned by default (mirrors check-active-hooks-executable).
DEFAULT_SETTINGS_REL = (
    ".claude/settings.json",
    "templates/settings/settings.base.json",
)

_ANCHOR_RE = re.compile(r"\$\{?CLAUDE_PROJECT_DIR\}?")
_NOOP_PROGRAMS = frozenset({"echo", "printf", "true", ":"})

# Degraded-mode secret regexes (used ONLY when _lib.secret_patterns is
# unavailable). Deliberately conservative.
_FALLBACK_SECRET_RES: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_personal_token", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|passwd|password)\b"
            r"\s*[:=]\s*[\"'][A-Za-z0-9_\-/+=]{20,}[\"']"
        ),
    ),
)


class Finding(NamedTuple):
    """One gate finding. severity: RED (fails the gate) or WARN (printed)."""

    check_id: str
    severity: str  # "RED" | "WARN"
    location: str
    message: str


def _red(check_id: str, location: str, message: str) -> Finding:
    return Finding(check_id, "RED", location, message)


def _warn(check_id: str, location: str, message: str) -> Finding:
    return Finding(check_id, "WARN", location, message)


# ---------------------------------------------------------------------------
# Settings walking
# ---------------------------------------------------------------------------

def load_settings(path: Path) -> Dict[str, Any]:
    """Parse a settings JSON file. Raises ValueError on any failure
    (fail-CLOSED: a gate input we cannot parse is an error, not a skip)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"cannot parse {path}: top-level JSON is not an object")
    return data


def iter_hook_entries(
    data: Dict[str, Any],
) -> Iterable[Tuple[str, int, Dict[str, Any], Dict[str, Any]]]:
    """Yield ``(event_name, entry_index, matcher_entry, hook_dict)`` for
    every ``{"type": "command", ...}``-shaped hook in ``data["hooks"]``."""
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        return
    for event_name, matcher_blocks in hooks.items():
        if not isinstance(matcher_blocks, list):
            continue
        for idx, entry in enumerate(matcher_blocks):
            if not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks", []) or []:
                if isinstance(hook, dict):
                    yield event_name, idx, entry, hook


# ---------------------------------------------------------------------------
# Check (a): runtime resolution model
# ---------------------------------------------------------------------------

def _expand_project_dir(token: str, repo_root: Path) -> str:
    return _ANCHOR_RE.sub(str(repo_root), token)


def _is_anchored(raw_token: str) -> bool:
    """True iff the token resolves independently of the harness cwd:
    it carries the $CLAUDE_PROJECT_DIR anchor or is absolute."""
    return bool(_ANCHOR_RE.search(raw_token)) or raw_token.startswith("/")


def analyze_hook_command(
    command: str, repo_root: Path, *, location: str
) -> Tuple[List[Finding], bool]:
    """Simulate harness-time resolution of one hook ``command``.

    Returns ``(findings, is_noop_candidate)``. Model (see module docstring):
    ``$CLAUDE_PROJECT_DIR`` is expanded (the harness guarantees the env
    var); cwd is NOT trusted. The ``_python-hook.sh`` argument resolves
    against the shim's own dirname (`_python-hook.sh:274,281`); a missing
    resolved script is a silent ``{}`` fail-open (`:284-288`) and therefore
    RED here.
    """
    findings: List[Finding] = []
    command = (command or "").strip()
    if not command:
        findings.append(_red("runtime_resolution", location, "empty hook command"))
        return findings, False

    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        # Fail-CLOSED on unparseable input (check_bash_safety _e3 precedent).
        findings.append(
            _red(
                "runtime_resolution",
                location,
                f"command not shell-parseable ({exc}); refusing to certify",
            )
        )
        return findings, False
    if not tokens:
        findings.append(_red("runtime_resolution", location, "empty hook command"))
        return findings, False

    consumed: set = set()

    # --- shim invocations -------------------------------------------------
    for i, tok in enumerate(tokens):
        if Path(tok).name != "_python-hook.sh":
            continue
        consumed.add(i)
        if not _is_anchored(tok):
            findings.append(
                _red(
                    "runtime_resolution",
                    location,
                    "shim path is cwd-relative "
                    f"({tok!r}): resolves only when the harness cwd happens "
                    "to be the repo root — the S254 dead-rail class. Anchor "
                    'it: "$CLAUDE_PROJECT_DIR/'
                    + (tok[2:] if tok.startswith("./") else tok)
                    + '"',
                )
            )
            # cannot certify the script arg either; still consume it below.
        shim_path = Path(_expand_project_dir(tok, repo_root))
        anchored_shim_exists = _is_anchored(tok) and shim_path.is_file()
        if _is_anchored(tok) and not anchored_shim_exists:
            findings.append(
                _red(
                    "runtime_resolution",
                    location,
                    f"shim not found at runtime-resolved path {shim_path}",
                )
            )
        # First subsequent non-flag token = hook script name.
        script_arg: Optional[str] = None
        for j in range(i + 1, len(tokens)):
            if tokens[j].startswith("-"):
                continue
            script_arg = tokens[j]
            consumed.add(j)
            break
        if script_arg is None:
            findings.append(
                _red(
                    "runtime_resolution",
                    location,
                    "shim invoked without a hook script argument — shim "
                    "emits '{}' and exits 0 (fail-open dead rail, "
                    "_python-hook.sh:275-279)",
                )
            )
        elif anchored_shim_exists:
            # dirname rule: HOOK_SCRIPT = HOOKS_DIR/<arg>
            resolved = (shim_path.parent / script_arg).resolve()
            if not resolved.is_file():
                findings.append(
                    _red(
                        "runtime_resolution",
                        location,
                        f"registered hook script {script_arg!r} does not "
                        f"exist at shim-resolved path {resolved} — at "
                        "runtime the shim emits '{}' and exits 0 "
                        "(_python-hook.sh:284-288): a SILENT fail-open "
                        "dead rail",
                    )
                )

    # --- direct references (python3 x.py, bash x.sh, any .claude/ path) ---
    for i, tok in enumerate(tokens):
        if i in consumed:
            continue
        looks_pathy = tok.endswith(".py") or tok.endswith(".sh") or ".claude/" in tok
        if not looks_pathy:
            continue
        if not _is_anchored(tok):
            findings.append(
                _red(
                    "runtime_resolution",
                    location,
                    f"cwd-relative reference {tok!r}: not anchored on "
                    "$CLAUDE_PROJECT_DIR and not absolute — resolution "
                    "depends on the harness cwd at fire time (S254 class)",
                )
            )
            continue
        expanded = Path(_expand_project_dir(tok, repo_root))
        if not expanded.is_file():
            findings.append(
                _red(
                    "runtime_resolution",
                    location,
                    f"referenced file missing at runtime-resolved path {expanded}",
                )
            )

    # --- no-op candidate ---------------------------------------------------
    prog = Path(tokens[0]).name
    referenced_any_file = any(
        t.endswith(".py") or t.endswith(".sh") or ".claude/" in t for t in tokens
    )
    is_noop = prog in _NOOP_PROGRAMS and not referenced_any_file

    return findings, is_noop


# ---------------------------------------------------------------------------
# Check (d): intentional no-op allowlist
# ---------------------------------------------------------------------------

def load_noop_allowlist(repo_root: Path, override: Optional[Path] = None) -> List[str]:
    """Load allowlist substrings: file lines (if present) + module seed."""
    entries: List[str] = list(DEFAULT_NOOP_ALLOWLIST_SUBSTRINGS)
    path = override if override is not None else repo_root / NOOP_ALLOWLIST_REL
    try:
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.split("#", 1)[0].strip()
                if line:
                    entries.append(line)
    except OSError:
        # Infra failure reading an OPTIONAL allowlist: proceed with the seed
        # (a read error must not un-allowlist and false-RED the gate run,
        # nor silently allow anything new).
        pass
    return entries


def is_noop_allowlisted(
    command: str, entry: Dict[str, Any], allowlist: List[str]
) -> bool:
    comment = entry.get("_comment", "")
    if isinstance(comment, str) and NOOP_MARKER in comment:
        return True
    return any(sub and sub in command for sub in allowlist)


def _entry_has_resolution_waiver(entry: Dict[str, Any]) -> bool:
    comment = entry.get("_comment", "")
    return isinstance(comment, str) and RESOLUTION_WAIVER_MARKER in comment


# ---------------------------------------------------------------------------
# Check (b): inline-secret scan
# ---------------------------------------------------------------------------

def _iter_strings(node: Any, path: str) -> Iterable[Tuple[str, str]]:
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            for item in _iter_strings(v, f"{path}.{k}"):
                yield item
    elif isinstance(node, list):
        for i, v in enumerate(node):
            for item in _iter_strings(v, f"{path}[{i}]"):
                yield item


def _settings_secret_patterns() -> Optional[list]:
    """Catalog subset for CONFIG scanning: token + credential families.

    The pii category (br_rg, br_cpf, ...) is deliberately excluded here:
    the inline-secret threat in a settings file is a credential, and the
    checksum-less PII patterns false-positive on doc-comment digit runs
    (observed: ``(GPG: 00000000)`` in the live settings matched br_rg).
    """
    if _secret_patterns is None:
        return None
    try:
        return [
            p
            for p in _secret_patterns.ALL_PATTERNS
            if getattr(p, "category", "") in ("token", "credential")
        ]
    except Exception:
        return None


def scan_settings_for_secrets(data: Dict[str, Any], source: str) -> List[Finding]:
    """Scan every string value for inline secrets. Never echoes matches."""
    findings: List[Finding] = []
    catalog = _settings_secret_patterns()
    for path, value in _iter_strings(data, source):
        if _secret_patterns is not None and catalog:
            try:
                hits = _secret_patterns.scan(value, patterns=catalog)
            except Exception:
                # Codex pair-rail P2 (S261 landing): a scan failure means this
                # value was NEVER scanned. Per the repo's fail-CLOSED rule for
                # security matchers (input a matcher cannot parse == block, not
                # wave through — CLAUDE.md §4 / PLAN-152 C4), an unscanned
                # settings value is RED, not an advisory WARN. A stalled scanner
                # reddens the gate rather than letting a possibly-secret-bearing
                # value slip past unscanned.
                findings.append(
                    _red(
                        "inline_secret",
                        path,
                        "secret scan errored on this value — unscanned "
                        "content is fail-CLOSED (fix the scanner or the value)",
                    )
                )
                continue
            for h in hits:
                findings.append(
                    _red(
                        "inline_secret",
                        path,
                        f"inline secret (family={h.family_id}) in settings "
                        "value — move it to the environment / a secret store",
                    )
                )
        else:
            for family, rx in _FALLBACK_SECRET_RES:
                if rx.search(value):
                    findings.append(
                        _red(
                            "inline_secret",
                            path,
                            f"inline secret (family={family}, degraded "
                            "built-in scan) in settings value",
                        )
                    )
    return findings


# ---------------------------------------------------------------------------
# Check (c): deny baseline
# ---------------------------------------------------------------------------

def check_deny_baseline(data: Dict[str, Any], source: str) -> List[Finding]:
    """Assert DENY_BASELINE ⊆ permissions.deny for files declaring
    ``permissions``. A file without ``permissions`` yields no findings here
    (main() enforces presence for the default dogfood settings)."""
    findings: List[Finding] = []
    perms = data.get("permissions")
    if perms is None:
        return findings
    if not isinstance(perms, dict):
        findings.append(
            _red("deny_baseline", f"{source}.permissions", "permissions is not an object")
        )
        return findings
    deny = perms.get("deny", [])
    if not isinstance(deny, list):
        findings.append(
            _red("deny_baseline", f"{source}.permissions.deny", "deny is not a list")
        )
        return findings
    present = {d for d in deny if isinstance(d, str)}
    for required in DENY_BASELINE:
        if required not in present:
            findings.append(
                _red(
                    "deny_baseline",
                    f"{source}.permissions.deny",
                    f"missing required deny entry {required!r} (DENY_BASELINE)",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Delegation: exists+exec-bit gate (no duplicate gate)
# ---------------------------------------------------------------------------

def run_exec_bit_gate(repo_root: Path) -> List[Finding]:
    """Delegate to .claude/scripts/check-active-hooks-executable.py.

    That script remains the single owner of the exists+exec-bit sweep
    (Session 75 Codex Finding 9). We import it by file path (its name is
    not import-safe) and call its main() with stdout captured.
    """
    script = repo_root / ".claude" / "scripts" / "check-active-hooks-executable.py"
    if not script.is_file():
        return [
            _warn(
                "exec_bit",
                str(script),
                "check-active-hooks-executable.py not found — exec-bit "
                "sub-check skipped (degraded)",
            )
        ]
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ceo_check_active_hooks_executable", str(script)
        )
        if spec is None or spec.loader is None:
            raise ImportError("spec_from_file_location returned None")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                rc = int(mod.main())
            except SystemExit as exc:  # its parser exits 2 on parse failure
                rc = int(exc.code or 0)
    except Exception as exc:
        return [
            _warn(
                "exec_bit",
                str(script),
                f"could not run exec-bit gate ({type(exc).__name__}: {exc}) — degraded",
            )
        ]
    if rc != 0:
        detail = " | ".join(
            line.strip() for line in buf.getvalue().splitlines() if line.strip()
        )
        return [_red("exec_bit", str(script), f"exec-bit gate rc={rc}: {detail}")]
    return []


# ---------------------------------------------------------------------------
# Static driver
# ---------------------------------------------------------------------------

def run_static(
    repo_root: Path,
    settings_paths: List[Path],
    *,
    noop_allowlist_path: Optional[Path] = None,
    include_exec_bit: bool = True,
) -> List[Finding]:
    findings: List[Finding] = []
    allowlist = load_noop_allowlist(repo_root, noop_allowlist_path)

    for settings_path in settings_paths:
        if not settings_path.is_file():
            findings.append(
                _warn("settings", str(settings_path), "settings file not present — skipped")
            )
            continue
        data = load_settings(settings_path)  # ValueError propagates → exit 2
        src = settings_path.name

        for event_name, idx, entry, hook in iter_hook_entries(data):
            command = hook.get("command", "") or ""
            location = f"{src}:hooks.{event_name}[{idx}]"
            cmd_findings, is_noop = analyze_hook_command(
                command, repo_root, location=location
            )
            if cmd_findings and _entry_has_resolution_waiver(entry):
                findings.extend(
                    _warn(f.check_id, f.location, f"[waived {RESOLUTION_WAIVER_MARKER}] {f.message}")
                    for f in cmd_findings
                )
            else:
                findings.extend(cmd_findings)
            if is_noop and not is_noop_allowlisted(command, entry, allowlist):
                findings.append(
                    _red(
                        "noop_hook",
                        location,
                        "hook command is a constant emitter (no-op rail) and "
                        f"is not annotated: add {NOOP_MARKER} to the entry's "
                        f"_comment or a line to {NOOP_ALLOWLIST_REL}",
                    )
                )

        # statusLine command (harness-resolved too), if present.
        status_line = data.get("statusLine")
        if isinstance(status_line, dict) and status_line.get("command"):
            sl_findings, _ = analyze_hook_command(
                str(status_line["command"]), repo_root, location=f"{src}:statusLine"
            )
            findings.extend(sl_findings)

        findings.extend(scan_settings_for_secrets(data, src))
        findings.extend(check_deny_baseline(data, src))

    if include_exec_bit:
        findings.extend(run_exec_bit_gate(repo_root))
    return findings


# ---------------------------------------------------------------------------
# Behavioral positive-control replay
# ---------------------------------------------------------------------------

def _substitute_placeholders(node: Any, repo_root: Path) -> Any:
    if isinstance(node, str):
        return node.replace(FIXTURE_PROJECT_PLACEHOLDER, str(repo_root))
    if isinstance(node, dict):
        return {k: _substitute_placeholders(v, repo_root) for k, v in node.items()}
    if isinstance(node, list):
        return [_substitute_placeholders(v, repo_root) for v in node]
    return node


def _is_block_shaped(decision: Any) -> bool:
    if not isinstance(decision, dict):
        return False
    if decision.get("decision") in ("block", "deny"):
        return True
    hso = decision.get("hookSpecificOutput")
    if isinstance(hso, dict) and hso.get("permissionDecision") == "deny":
        return True
    return False


def _replay_env(repo_root: Path, scratch: Path) -> Dict[str, str]:
    """Hermetic env for a replayed hook: real repo provides the hook's
    dependencies (team files, guard lists, sentinel dirs); HOME, GNUPGHOME
    and the audit sink are TEMP so the replay never touches the real
    profile or the live audit chain; CEO_*/CLAUDE_* session overrides
    (CEO_SENTINEL_UNLOCK, CEO_KERNEL_OVERRIDE, ...) are deliberately NOT
    inherited — a planted violation must block under DEFAULT posture.

    GNUPGHOME is pinned to a short temp dir: without it gpg auto-creates
    agent sockets under $HOME and can stall for the full 15s-per-sentinel
    verify timeout (observed while building this gate).
    """
    home = scratch / "home"
    gnupg = scratch / "gnupg"
    audit = scratch / "audit"
    for d in (home, audit):
        d.mkdir(parents=True, exist_ok=True)
    gnupg.mkdir(parents=True, exist_ok=True)
    os.chmod(str(gnupg), 0o700)
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "GNUPGHOME": str(gnupg),
        "TMPDIR": str(scratch),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "CLAUDE_PROJECT_DIR": str(repo_root),
        "CEO_AUDIT_LOG_DIR": str(audit),
        "CEO_AUDIT_SYNC_MODE": "1",
    }


def run_replay(
    repo_root: Path,
    fixtures_dir: Optional[Path] = None,
    *,
    timeout: float = 30.0,
    controls: Tuple[Tuple[str, str], ...] = REQUIRED_REPLAY_CONTROLS,
) -> List[Finding]:
    """Replay every required positive control; RED on any control that
    does not observably BLOCK its planted violation."""
    if (os.environ.get("CEO_SOTA_DISABLE") or "").strip() == "1":
        return [
            _warn(
                "replay",
                "env",
                "CEO_SOTA_DISABLE=1 — behavioral replay skipped (static checks unaffected)",
            )
        ]
    findings: List[Finding] = []
    fdir = fixtures_dir if fixtures_dir is not None else repo_root / REPLAY_FIXTURES_REL
    scratch = Path(tempfile.mkdtemp(prefix="ceo-hc-replay-"))
    try:
        env = _replay_env(repo_root, scratch)
        for hook_name, fixture_name in controls:
            loc = f"replay:{hook_name}"
            fixture_path = fdir / fixture_name
            if not fixture_path.is_file():
                findings.append(
                    _red(
                        "replay",
                        loc,
                        f"positive-control fixture MISSING ({fixture_path}) — "
                        "a control that stops firing reddens the run",
                    )
                )
                continue
            try:
                doc = json.loads(fixture_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                findings.append(
                    _red("replay", loc, f"fixture unparseable ({exc}) — fail-closed")
                )
                continue
            if not isinstance(doc, dict) or doc.get("expect") != "block":
                findings.append(
                    _red(
                        "replay",
                        loc,
                        "fixture tampered or malformed: 'expect' must be 'block'",
                    )
                )
                continue
            payload = doc.get("payload")
            if not isinstance(payload, dict):
                findings.append(
                    _red("replay", loc, "fixture missing 'payload' object")
                )
                continue
            payload = _substitute_placeholders(payload, repo_root)

            hook_path = repo_root / ".claude" / "hooks" / hook_name
            if not hook_path.is_file():
                findings.append(
                    _red("replay", loc, f"hook under test not found: {hook_path}")
                )
                continue
            try:
                proc = subprocess.run(
                    [sys.executable, str(hook_path)],
                    input=json.dumps(payload),
                    capture_output=True,
                    text=True,
                    env=env,
                    cwd=str(repo_root),
                    timeout=timeout,
                )
            except (subprocess.TimeoutExpired, OSError) as exc:
                findings.append(
                    _red(
                        "replay",
                        loc,
                        f"control errored ({type(exc).__name__}) — rail NOT certified alive",
                    )
                )
                continue
            lines = [l for l in proc.stdout.strip().splitlines() if l.strip()]
            decision: Any = None
            if lines:
                try:
                    decision = json.loads(lines[-1])
                except json.JSONDecodeError:
                    decision = None
            if decision is None:
                findings.append(
                    _red(
                        "replay",
                        loc,
                        f"no parseable decision on stdout (rc={proc.returncode}) — "
                        "rail NOT certified alive",
                    )
                )
                continue
            if not _is_block_shaped(decision):
                findings.append(
                    _red(
                        "replay",
                        loc,
                        "planted violation was NOT blocked "
                        f"(decision={json.dumps(decision)[:160]}) — DEAD or "
                        "fail-open rail",
                    )
                )
    finally:
        shutil.rmtree(str(scratch), ignore_errors=True)
    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_repo_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    # landed location: .claude/hooks/check_harness_config.py → repo root 2 up
    candidate = _THIS_DIR.parent.parent
    if (candidate / ".claude").is_dir():
        return candidate
    return Path.cwd()


def _print_findings(findings: List[Finding]) -> None:
    for f in findings:
        print(f"[{f.severity}] {f.check_id} @ {f.location}\n    {f.message}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_harness_config.py",
        description="Harness-config gate: runtime-resolution model, "
        "inline-secret scan, deny baseline, no-op annotation, and "
        "behavioral positive-control replay (PLAN-153 Wave E / ADR-173).",
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--settings",
        action="append",
        type=Path,
        default=None,
        help="settings file(s) to scan (default: dogfood + template)",
    )
    parser.add_argument("--fixtures-dir", type=Path, default=None)
    parser.add_argument("--noop-allowlist", type=Path, default=None)
    parser.add_argument(
        "--static", action="store_true", help="run only the static checks"
    )
    parser.add_argument(
        "--replay", action="store_true", help="run only the behavioral replay"
    )
    parser.add_argument(
        "--no-exec-bit",
        action="store_true",
        help="skip delegation to check-active-hooks-executable.py",
    )
    args = parser.parse_args(argv)

    repo_root = (args.repo_root or _default_repo_root()).resolve()
    do_static = args.static or not args.replay
    do_replay = args.replay or not args.static

    if args.settings:
        settings_paths = [p if p.is_absolute() else repo_root / p for p in args.settings]
    else:
        settings_paths = [repo_root / rel for rel in DEFAULT_SETTINGS_REL]

    findings: List[Finding] = []
    try:
        if do_static:
            findings.extend(
                run_static(
                    repo_root,
                    settings_paths,
                    noop_allowlist_path=args.noop_allowlist,
                    include_exec_bit=not args.no_exec_bit,
                )
            )
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    if do_replay:
        findings.extend(run_replay(repo_root, args.fixtures_dir))

    _print_findings(findings)
    reds = [f for f in findings if f.severity == "RED"]
    if reds:
        print(f"\nFAIL: {len(reds)} RED finding(s) "
              f"({len(findings) - len(reds)} warning(s))")
        return 1
    print(
        f"OK: harness-config gate green "
        f"(static={'yes' if do_static else 'no'}, "
        f"replay={'yes' if do_replay else 'no'}, "
        f"{len(findings)} warning(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
