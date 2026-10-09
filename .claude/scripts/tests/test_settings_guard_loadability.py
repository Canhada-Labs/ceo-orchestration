"""Guard-hook loadability of every shipped settings surface (rule derived from the Claude Code 2.1.280 binary, re-derived from 2.1.295).

WHY THIS FILE EXISTS
--------------------
Claude Code refuses a WHOLE settings file when a PreToolUse or
PermissionRequest ("guard") hook in it cannot be loaded. The loader reports
such a finding with ``severity: "fatal"``, and the per-file parse then returns
``settings: null``: nothing in that file applies, not the other hooks and not
``permissions.deny``. The reason string shipped in the binary is: "a
PreToolUse/PermissionRequest hook that cannot be loaded may be what guards the
permissions declared beside it, so nothing it sits in is applied until the
entry is fixed or removed". For this framework, one malformed guard entry in
``.claude/settings.json`` would turn off every hook and every deny rule in
that file at once. Hooks of every other event are handled entry by entry: the
bad entry is dropped with a warning and the file still loads (rule 5 below is
the exception).

Before this file, no tracked Python, shell or workflow file mentioned this
rule (``git grep``, 2026-09-22). This file replicates the rule and asserts
that no shipped surface trips it.

PROVENANCE (re-derived 2026-10-09, macOS, Claude Code 2.1.295)
---------------------------------------------------------------
The rule was first derived on 2026-09-22 by reading the JavaScript embedded
in the 2.1.277, 2.1.278 and 2.1.280 native binaries. Six code segments were
byte-identical after identifier normalisation in those builds: (1) the entry
check, recursive guard scan, exempt-key set and matcher walk; (2) the
settings-file validator; (3) the per-file parse; (4) the event list; (5) the
hook entry schemas; (6) the matcher schema.

The replica is now pinned to ``~/.local/share/claude/versions/2.1.295``
(sha256 ``DERIVED_FROM_BINARY_SHA256``), re-measured on 2026-10-09 (section
"CC 2.1.295" of ``.claude/plans/PLAN-194/LEDGER.md``). Against 2.1.292, the
oldest build still on disk, the entry check, the matcher walk, the
settings-file validator and the per-file parse are identical after renaming.
The 33 events keep their order and the 9 exempt keys are the same. Segment
(5) changed: the ``command`` and ``http`` entry schemas gained ``onFailure``,
an optional enum ``"continue"``/``"block"`` with no ``.catch``. A byte search
for the field's describe text and for ``onFailure`` right after each
schema's ``timeout`` finds it in 2.1.295 only, once per schema, and in none
of 2.1.292, 2.1.293 or 2.1.294. No other build on disk carries this exact
rule, so ``SAME_RULE_NORMALISED_IN`` is empty. 2.1.280 and 2.1.288 are no
longer on disk: the chain back to 2.1.280 rests on recorded constants, not
on a diff. The plugin ``hooks.json`` variant was read in 2.1.280 only.

Minified names change in every build, so search by message text, not by
name. To re-derive the rule, search the binary for ``unloadableGuards`` and
for these strings (names: 2.1.295 first, then 2.1.280):

* ``holds PreToolUse/PermissionRequest hooks where a matcher was expected``
  (the per-event matcher walk, ``on``; ``Lt``);
* ``PreToolUse/PermissionRequest hooks are declared outside "hooks"`` (the
  settings-file validator ``u_``, which calls ``G8`` with the exempt-key set
  ``si``; ``Af``, ``k6`` and ``Js``);
* ``Hook entry must be an object`` (the entry check, ``Rp``; ``rd``, which
  validates against the discriminated union of the hook schemas);
* ``.describe("Shell command hook type")`` (the hook entry schemas);
* ``What a failure of this hook does`` (the shared ``onFailure`` schema
  ``ni``, used as ``onFailure:ni()`` by the command and http schemas only);
* ``return{settings:c.data,errors:d}`` (the per-file parse, ``OE``; ``POe``,
  which returns ``settings:null`` when any finding has
  ``severity==="fatal"``). The 2.1.280 text of this docstring gave the anchor
  as ``errors:i``; that form is absent from 2.1.287, 2.1.288 and 2.1.292 to
  2.1.295.

RUNTIME CROSS-CHECK. ``claude doctor`` makes no model call and prints the
loader's verdict for each settings file. It was run in a scratch project with
``HOME`` and ``CLAUDE_CONFIG_DIR`` pointed at scratch directories.

* 2026-09-23 UTC, Claude Code 2.1.280: the fatal reason quoted above for a
  PreToolUse entry of unknown ``type``, "entry ignored" for the same entry
  under PostToolUse, and no settings finding for a clean control.
* 2026-10-09 UTC, Claude Code 2.1.295 (with ``DISABLE_AUTOUPDATER=1`` and
  ``CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1``), six ``onFailure``
  documents. The fatal reason for ``"retry"`` and for ``null``
  on a PreToolUse command entry, and for ``"Block"`` on a PermissionRequest
  http entry. "entry ignored" for ``"retry"`` under PostToolUse. No settings
  finding for ``"block"`` on a PreToolUse command entry, nor for ``"retry"``
  on a PreToolUse prompt entry.

Every other shape below rests on the text read. When re-deriving, plant a
shape in such a scratch project and compare the ``claude doctor`` output with
the replica's verdict.

The replica is pinned to one Claude Code version. ``ReplicaPinTracksTheLedger``
holds ``DERIVED_FROM_CLAUDE_CODE`` equal to ``claude_code.last_seen.version`` in
``.claude/scripts/substrate-watch.json``. A ledger bump therefore turns this
file red until someone re-derives the rule from the new binary (the search
strings above) and moves the three pin constants on purpose.

THE RULE, BY SHAPE
------------------
A settings file is dropped whole when any of these holds:

1. **Declared outside ``hooks``.** A key ``PreToolUse`` or ``PermissionRequest``
   with a value that is not null and not an empty array, or an object shaped
   like a matcher, sits outside the top-level ``hooks`` object and outside the
   exempt keys (``env``, ``mcpServers`` and the rest of
   ``SETTINGS_UNSCANNED_KEYS``, skipped at every level). The scan runs from the top level down through a
   budget of 3 more containers below each top-level value (lists count), so a
   guard key is caught up to 5 path steps deep and a matcher-shaped object up
   to 4. Keys named after a hook event stop the matcher-shape test below them,
   and entries inside a ``hooks`` list that carry a string ``type`` are not
   descended into.
2. **``hooks`` itself is malformed around guards.** ``hooks`` is an array that
   holds an object or a nested guard, or ``hooks`` is a single matcher.
3. **Unknown event holding guards.** A key under ``hooks`` that is not one of
   the 33 events, whose value holds a guard (as in 1).
4. **Event value not an array.** ``PreToolUse``/``PermissionRequest`` under
   ``hooks`` holds anything but an array or null, or any event holds a
   non-array value that itself holds a guard.
5. **Any event's matcher holds a nested guard.** This includes non-guard
   events such as PostToolUse.
6. **A guard matcher or entry fails its schema.** The matcher is not an
   object, its ``hooks`` is not an array, or ``matcher`` is not a string. Or an
   entry is not an object, has no string ``type``, has a ``type`` outside
   command/prompt/agent/http/mcp_tool, or fails that type's schema, for example
   a missing ``command``, a ``timeout`` that is not a positive number, or a
   wrong-typed optional field. Since 2.1.295 that includes an ``onFailure``
   on a command or http entry that is not ``"continue"`` or ``"block"``;
   ``null`` fails too, because the field is optional, not nullable. Unknown
   extra keys such as ``_comment`` are stripped, not rejected, because the
   schemas are plain (non-strict) objects. ``onFailure`` on a prompt, agent
   or mcp_tool entry is such an extra key.

The replica is FAITHFUL where it can be and CONSERVATIVE where it cannot: it
may flag something the binary would load (an http ``url`` it cannot prove
valid, an empty or blank ``command``), never the reverse. A false red costs a
look. A false green costs the whole rail. A field the replica does not list
in ``_TYPE_FIELDS`` is stripped like an extra key, so every field the binary
validates must be listed: until the 2.1.295 re-derivation, ``onFailure`` was
such a false green.

OUT OF SCOPE (declared)
-----------------------
* The settings loader also drops the whole file when the full settings schema
  rejects it. That schema is not replicated here.
* The full settings schema rejects a malformed ``hooks`` value outright (no
  ``.catch``), which is why rules 2-4 drop the file even where the validator
  attaches no ``fatal`` severity.
* Stack fragments are checked on their own. The jq reducer in
  ``scripts/install.sh`` only concatenates their PreToolUse/PostToolUse
  matcher arrays and copies ``sandbox``/``autoAllowBashIfSandboxed`` into
  base, so a clean base and a clean fragment compose clean under this rule.
  Other composition paths (``upgrade.sh``) are not modelled here.
* The plugin ``hooks.json`` is not tracked. It is composed in memory through
  ``scripts/build-plugin.py``'s pure ``compose_plugin_hooks`` and checked
  against the plugin loader's variant of the rule. That loader's full schema
  is not replicated.

stdlib-only; Python >= 3.9.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

DERIVED_FROM_CLAUDE_CODE = "2.1.295"
DERIVED_FROM_BINARY_SHA256 = "0116ee2e0a513900b633d9951367f18747686478e2b462805b8c31609f047f70"
# Empty: 2.1.292-2.1.294 lack ``onFailure`` (module docstring, PROVENANCE).
SAME_RULE_NORMALISED_IN: Tuple[str, ...] = ()

# The 33-event registry, in binary order.
HOOK_EVENTS: Tuple[str, ...] = (
    "PreToolUse", "PostToolUse", "PostToolUseFailure", "PostToolBatch", "Notification",
    "UserPromptSubmit", "UserPromptExpansion", "SessionStart", "SessionEnd", "Stop",
    "StopFailure", "SubagentStart", "SubagentStop", "PreCompact", "PostCompact",
    "PreModelSwitch", "PostModelSwitch", "PermissionRequest", "PermissionDenied", "Setup",
    "TeammateIdle", "TaskCreated", "TaskCompleted", "Elicitation", "ElicitationResult",
    "ConfigChange", "WorktreeCreate", "WorktreeRemove", "InstructionsLoaded", "CwdChanged",
    "FileChanged", "DirectoryAdded", "MessageDisplay",
)
GUARD_EVENTS: FrozenSet[str] = frozenset({"PreToolUse", "PermissionRequest"})
# Keys the settings-file validator does not scan, at the top level and below.
SETTINGS_UNSCANNED_KEYS: FrozenSet[str] = frozenset({
    "mcpServers", "managedMcpServers", "lspServers", "pluginConfigs", "enabledPlugins",
    "extraKnownMarketplaces", "env", "skillOverrides", "modelSettings",
})
# The plugin hooks.json loader scans every key.
PLUGIN_HOOKS_JSON_UNSCANNED_KEYS: FrozenSet[str] = frozenset()
HOOK_TYPES: Tuple[str, ...] = ("command", "prompt", "agent", "http", "mcp_tool")
SCAN_BUDGET = 3

# Every tracked settings surface a Claude Code session loads as a whole file
# (directly, or after the installer copies/merges it). A path that disappears
# is a RED: this list must stay honest.
SETTINGS_SURFACES: Tuple[str, ...] = (
    ".claude/settings.json",
    "templates/settings/settings.base.json",
    "templates/settings/settings.user.json",
    "templates/settings/settings.stack.node.json",
    "templates/settings/settings.stack.otel.json",
    "templates/settings/settings.stack.sandbox.json",
)
# Surfaces that must carry guard entries (non-vacuity: the walk reaches them).
SURFACES_WITH_GUARDS: Tuple[str, ...] = (
    ".claude/settings.json",
    "templates/settings/settings.base.json",
    "templates/settings/settings.user.json",
)
DOGFOOD_SURFACE = ".claude/settings.json"
BUILD_PLUGIN = REPO_ROOT / "scripts" / "build-plugin.py"
USER_TEMPLATE = REPO_ROOT / "templates" / "settings" / "settings.user.json"
SUBSTRATE_LEDGER = REPO_ROOT / ".claude" / "scripts" / "substrate-watch.json"


# --------------------------------------------------------------------------
# Replica of the binary's guard scan (names in brackets are 2.1.280's).
# --------------------------------------------------------------------------

def _has_guard_key(node: Any) -> bool:
    """[Xs] An object with a guard key whose value is not null / not []."""
    if not isinstance(node, dict):
        return False
    return any(
        k in GUARD_EVENTS and v is not None and not (isinstance(v, list) and not v)
        for k, v in node.items()
    )


def _matcher_shaped(node: Any) -> bool:
    """[qJ] An object that looks like a matcher."""
    if not isinstance(node, dict):
        return False
    if "matcher" not in node and any(k in HOOK_EVENTS for k in node):
        return False
    hooks = node.get("hooks")
    if isinstance(hooks, list):
        return len(hooks) > 0
    return isinstance(hooks, dict) and ("matcher" in node or isinstance(hooks.get("type"), str))


def _holds_guard(node: Any, budget: int = SCAN_BUDGET, matchers_count: bool = True,
                 unscanned: FrozenSet[str] = frozenset(), in_hooks_list: bool = False) -> bool:
    """[Spe] Recursive guard scan with a container budget."""
    if _has_guard_key(node):
        return True
    if matchers_count and _matcher_shaped(node):
        return True
    if budget == 0 or not isinstance(node, (dict, list)):
        return False
    if isinstance(node, list):
        return any(_holds_guard(c, budget - 1, matchers_count, unscanned, in_hooks_list)
                   for c in node)
    if in_hooks_list and isinstance(node.get("type"), str):
        return False
    return any(
        _holds_guard(v, budget - 1, matchers_count and k not in HOOK_EVENTS, unscanned,
                     k == "hooks" and isinstance(v, list))
        for k, v in node.items() if k not in unscanned
    )


def _declared_outside_hooks(doc: Any, unscanned: FrozenSet[str]) -> bool:
    """[k6] Guards declared at the top level or under a key other than hooks."""
    if not isinstance(doc, dict):
        return False
    return _has_guard_key(doc) or any(
        k != "hooks" and k not in unscanned
        and _holds_guard(v, SCAN_BUDGET, k not in HOOK_EVENTS, unscanned)
        for k, v in doc.items()
    )


def _holds_guard_anywhere(node: Any) -> bool:
    """[bpe] Unbounded variant used on a malformed top-level hooks array."""
    if _matcher_shaped(node):
        return True
    if isinstance(node, list):
        return any(_holds_guard_anywhere(c) for c in node)
    return _has_guard_key(node)


def _is_str(v: Any) -> bool:
    return isinstance(v, str)


def _is_str_min1(v: Any) -> bool:
    return isinstance(v, str) and len(v) >= 1


def _is_bool(v: Any) -> bool:
    return isinstance(v, bool)


def _is_positive_number(v: Any) -> bool:
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v) and v > 0)


def _is_str_list(v: Any) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _is_str_record(v: Any) -> bool:
    return isinstance(v, dict) and all(isinstance(x, str) for x in v.values())


def _is_record(v: Any) -> bool:
    return isinstance(v, dict)


def _is_shell(v: Any) -> bool:
    return v in ("bash", "powershell")


def _is_on_failure(v: Any) -> bool:
    return v in ("continue", "block")


_URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://\S+$")


def _is_url_conservative(v: Any) -> bool:
    return isinstance(v, str) and bool(_URL_RE.match(v))


_Check = Callable[[Any], bool]
_COMMON_OPTIONAL: Dict[str, _Check] = {
    "if": _is_str, "timeout": _is_positive_number, "statusMessage": _is_str, "once": _is_bool,
}
# type -> (required fields, optional fields). ``cloud`` is omitted: the binary
# wraps it in .catch(), so no value of it can fail. ``onFailure`` (``ni`` in
# 2.1.295, command and http only) has no .catch: a value outside its enum fails.
_TYPE_FIELDS: Dict[str, Tuple[Dict[str, _Check], Dict[str, _Check]]] = {
    "command": ({"command": _is_str}, {
        "args": _is_str_list, "shell": _is_shell, "async": _is_bool, "asyncRewake": _is_bool,
        "rewakeMessage": _is_str_min1, "rewakeSummary": _is_str_min1,
        "onFailure": _is_on_failure}),
    "prompt": ({"prompt": _is_str}, {"model": _is_str, "continueOnBlock": _is_bool}),
    "agent": ({"prompt": _is_str}, {"model": _is_str}),
    "http": ({"url": _is_url_conservative}, {
        "headers": _is_str_record, "allowedEnvVars": _is_str_list,
        "onFailure": _is_on_failure}),
    "mcp_tool": ({"server": _is_str, "tool": _is_str}, {"input": _is_record}),
}


def entry_problem(entry: Any, conservative: bool = True) -> Optional[str]:
    """[rd] Why this guard entry cannot be loaded, or None."""
    if not isinstance(entry, dict):
        return "Hook entry must be an object"
    t = entry.get("type")
    if "type" not in entry:
        return 'Hook entry has no "type"'
    if not isinstance(t, str):
        return 'Hook entry "type" must be a string'
    if t not in HOOK_TYPES:
        return 'Unknown hook type "%s"' % t
    required, optional = _TYPE_FIELDS[t]
    probs: List[str] = []
    for key, ok in required.items():
        if key not in entry or not ok(entry[key]):
            probs.append("%s: required, wrong type or invalid" % key)
    for key, ok in list(_COMMON_OPTIONAL.items()) + list(optional.items()):
        if key in entry and not ok(entry[key]):
            probs.append("%s: wrong type or invalid" % key)
    if conservative and t == "command" and isinstance(entry.get("command"), str) \
            and not entry["command"].strip():
        probs.append("command: empty (conservative; the binary accepts it)")
    return ("Invalid %s hook (%s)" % (t, "; ".join(probs))) if probs else None


def _matcher_list(matchers: Any, event: str, conservative: bool) -> Tuple[List[str], List[str]]:
    """[Lt] (fatal, dropped-with-warning) findings for one event's matcher array."""
    fatal: List[str] = []
    dropped: List[str] = []
    if not isinstance(matchers, list):
        return fatal, dropped
    guard = event in GUARD_EVENTS
    sink = fatal if guard else dropped
    for g, m in enumerate(matchers):
        where = "%s.%d" % (event, g)
        if _holds_guard(m, SCAN_BUDGET, matchers_count=False):
            fatal.append(where + ": holds PreToolUse/PermissionRequest hooks where a matcher was expected")
            continue
        if not isinstance(m, dict):
            sink.append(where + ": Hook matcher must be an object")
            continue
        entries = m.get("hooks")
        if not isinstance(entries, list):
            sink.append(where + ': Hook matcher "hooks" must be an array of hook entries')
            continue
        for j, e in enumerate(entries):
            p = entry_problem(e, conservative=conservative and guard)
            if p:
                sink.append("%s.hooks.%d: %s" % (where, j, p))
        if "matcher" in m and not isinstance(m["matcher"], str):
            sink.append(where + ": Invalid hook matcher (matcher must be a string)")
    return fatal, dropped


def _hooks_map(hooks: Dict[str, Any], conservative: bool) -> Tuple[List[str], List[str]]:
    """[vf / YJ] Walk the ``hooks`` object: unknown events, non-arrays, matchers."""
    fatal: List[str] = []
    dropped: List[str] = []
    for event, value in hooks.items():
        if event not in HOOK_EVENTS:
            if _holds_guard(value, SCAN_BUDGET, matchers_count=not isinstance(value, list)):
                fatal.append("%s: not a hook event, but it holds PreToolUse/PermissionRequest hooks" % event)
            else:
                dropped.append("%s: unknown hook event" % event)
            continue
        if not isinstance(value, list):
            if (event in GUARD_EVENTS and value is not None) \
                    or _holds_guard(value, SCAN_BUDGET, matchers_count=False):
                fatal.append("%s: must be an array of matchers" % event)
            else:
                dropped.append("%s: must be an array of matchers" % event)
            continue
        f, d = _matcher_list(value, event, conservative)
        fatal.extend(f)
        dropped.extend(d)
    return (["hooks." + x for x in fatal], ["hooks." + x for x in dropped])


def settings_findings(doc: Any, conservative: bool = True) -> Tuple[List[str], List[str]]:
    """(fatal, dropped): fatal => Claude Code ignores the WHOLE settings file."""
    if not isinstance(doc, dict):
        return ["settings file is not a JSON object"], []
    fatal: List[str] = []
    if _declared_outside_hooks(doc, SETTINGS_UNSCANNED_KEYS):
        fatal.append('PreToolUse/PermissionRequest hooks are declared outside "hooks"')
    if "hooks" not in doc:
        return fatal, []
    hooks = doc["hooks"]
    if not isinstance(hooks, dict):
        if isinstance(hooks, list) and (any(isinstance(x, dict) for x in hooks)
                                         or _holds_guard_anywhere(hooks)):
            return fatal + ['"hooks" must be an object; received an array holding matchers'], []
        return fatal, ['"hooks" is not an object and was ignored']
    if _matcher_shaped(hooks):
        return fatal + ['"hooks" must be an object; received a single matcher'], []
    f, d = _hooks_map(hooks, conservative)
    return fatal + f, d


def plugin_hooks_json_findings(doc: Any, conservative: bool = True) -> Tuple[List[str], List[str]]:
    """(fatal, dropped) for a plugin hooks.json: fatal => the plugin load breaks."""
    fatal: List[str] = []
    if _declared_outside_hooks(doc, PLUGIN_HOOKS_JSON_UNSCANNED_KEYS) or _matcher_shaped(doc):
        fatal.append("hooks.json declares PreToolUse/PermissionRequest at its top level")
    if not (isinstance(doc, dict) and "hooks" in doc):
        return fatal, []
    hooks = doc["hooks"]
    if hooks is not None and not isinstance(hooks, dict):
        return fatal + ["hooks: must be an object mapping event names to matcher arrays"], []
    if not isinstance(hooks, dict):
        return fatal, []
    if _matcher_shaped(hooks):
        return fatal + ["hooks: received a single matcher"], []
    f, d = _hooks_map(hooks, conservative)
    return fatal + f, d


def guard_entry_count(doc: Any) -> int:
    hooks = doc.get("hooks") if isinstance(doc, dict) else None
    if not isinstance(hooks, dict):
        return 0
    matchers = [m for ev in GUARD_EVENTS if isinstance(hooks.get(ev), list)
                for m in hooks[ev] if isinstance(m, dict)]
    return sum(len(m["hooks"]) for m in matchers if isinstance(m.get("hooks"), list))


def _reject_constant(name: str) -> Any:
    raise ValueError("non-standard JSON constant %s (JSON.parse rejects it)" % name)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)


def _load_build_plugin() -> Any:
    spec = importlib.util.spec_from_file_location("build_plugin_for_guard_test", BUILD_PLUGIN)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# --------------------------------------------------------------------------
# Real surfaces.
# --------------------------------------------------------------------------

class ShippedSurfacesLoadWhole(TestEnvContext):
    """No shipped surface trips the whole-file drop."""

    def test_every_surface_exists(self) -> None:
        missing = [p for p in SETTINGS_SURFACES if not (REPO_ROOT / p).is_file()]
        self.assertEqual(missing, [], "settings surface list is stale: %r" % (missing,))

    def test_surface_list_covers_every_template_profile(self) -> None:
        # The explicit list stays the source of truth, but a new settings
        # profile must not ship unchecked: every templates/settings/*.json
        # has to be named in SETTINGS_SURFACES.
        profiles = sorted(p.relative_to(REPO_ROOT).as_posix()
                          for p in (REPO_ROOT / "templates" / "settings").glob("*.json"))
        self.assertTrue(profiles, "templates/settings/*.json matched nothing; the check is vacuous")
        unlisted = [p for p in profiles if p not in SETTINGS_SURFACES]
        self.assertEqual(unlisted, [], "settings profiles missing from SETTINGS_SURFACES: %r"
                         % (unlisted,))

    def test_surface_list_names_the_dogfood_settings(self) -> None:
        # The glob above covers the templates only. The dogfood settings file
        # is the one this repo's own sessions load, so it is pinned by name, and
        # every surface that must carry guards has to be one the checks walk.
        self.assertIn(DOGFOOD_SURFACE, SETTINGS_SURFACES)
        self.assertIn(DOGFOOD_SURFACE, SURFACES_WITH_GUARDS)
        not_walked = sorted(set(SURFACES_WITH_GUARDS) - set(SETTINGS_SURFACES))
        self.assertEqual(not_walked, [], "guard surfaces the checks never walk: %r"
                         % (not_walked,))

    def test_walk_reaches_guard_entries(self) -> None:
        for rel in SURFACES_WITH_GUARDS:
            n = guard_entry_count(load_json(REPO_ROOT / rel))
            self.assertGreater(n, 0, "%s: no guard entry reached; the check would be vacuous" % rel)

    def test_no_fatal_finding_in_settings_surfaces(self) -> None:
        findings = {}
        for rel in SETTINGS_SURFACES:
            fatal, _ = settings_findings(load_json(REPO_ROOT / rel))
            if fatal:
                findings[rel] = fatal
        self.assertEqual(
            findings, {},
            "By the rule derived from the Claude Code %s binary (a text replica, not a "
            "runtime observation), Claude Code would IGNORE these whole settings files: %r"
            % (DERIVED_FROM_CLAUDE_CODE, findings))

    def test_no_hook_entry_dropped_with_warning(self) -> None:
        findings = {}
        for rel in SETTINGS_SURFACES:
            _, dropped = settings_findings(load_json(REPO_ROOT / rel))
            if dropped:
                findings[rel] = dropped
        self.assertEqual(findings, {}, "hook registrations Claude Code would drop: %r" % (findings,))

    def test_composed_plugin_hooks_json_loads(self) -> None:
        build_plugin = _load_build_plugin()
        doc = {"hooks": build_plugin.compose_plugin_hooks(USER_TEMPLATE)}
        self.assertGreater(guard_entry_count(doc), 0, "composed plugin hooks carry no guard entry")
        fatal, dropped = plugin_hooks_json_findings(doc)
        self.assertEqual((fatal, dropped), ([], []), "plugin hooks.json would not load cleanly")


class ReplicaPinTracksTheLedger(TestEnvContext):
    """The replica is re-derived whenever the ledger moves to a new Claude Code."""

    def test_derived_version_matches_the_ledger(self) -> None:
        ledger = load_json(SUBSTRATE_LEDGER)
        rows = [c for c in ledger.get("components", [])
                if isinstance(c, dict) and c.get("key") == "claude_code"]
        self.assertEqual(len(rows), 1, "%s: expected exactly one claude_code component"
                         % SUBSTRATE_LEDGER)
        last_seen = (rows[0].get("last_seen") or {}).get("version")
        self.assertEqual(
            last_seen, DERIVED_FROM_CLAUDE_CODE,
            "substrate-watch.json reconciles Claude Code %r, but this replica was derived "
            "from %r. Re-derive the rule from the %r binary (search strings in the module "
            "docstring), then move DERIVED_FROM_CLAUDE_CODE, DERIVED_FROM_BINARY_SHA256 and "
            "SAME_RULE_NORMALISED_IN together." % (last_seen, DERIVED_FROM_CLAUDE_CODE, last_seen))
        self.assertNotIn(DERIVED_FROM_CLAUDE_CODE, SAME_RULE_NORMALISED_IN)
        self.assertRegex(DERIVED_FROM_BINARY_SHA256, r"^[0-9a-f]{64}$")


# --------------------------------------------------------------------------
# Positive controls: the checker must flag each fatal shape (anti-vacuity).
# --------------------------------------------------------------------------

def _entry(**over: Any) -> Dict[str, Any]:
    e: Dict[str, Any] = {"type": "command", "command": "true", "timeout": 5}
    e.update(over)
    return e


def _doc(entry: Any = None, event: str = "PreToolUse", **matcher_over: Any) -> Dict[str, Any]:
    m: Dict[str, Any] = {"_comment": "x", "matcher": "Bash",
                         "hooks": [_entry() if entry is None else entry]}
    m.update(matcher_over)
    return {"_comment": "x", "hooks": {event: [m]}, "permissions": {"deny": ["Bash(rm *)"]}}


_GUARD = [{"matcher": "Bash", "hooks": [_entry()]}]


class PlantedFatalShapesAreFlagged(TestEnvContext):
    """Each planted fatal shape must be flagged, each non-fatal one must not."""

    def _fatal(self, doc: Any) -> List[str]:
        return settings_findings(doc)[0]

    def assertFatal(self, doc: Any, needle: str = "") -> None:  # noqa: N802
        fatal = self._fatal(doc)
        self.assertTrue(fatal, "planted fatal NOT flagged: %r" % (doc,))
        if needle:
            self.assertTrue(any(needle in f for f in fatal), "%r not in %r" % (needle, fatal))

    def test_clean_document_is_green(self) -> None:
        self.assertEqual(settings_findings(_doc()), ([], []))

    def test_entry_shapes(self) -> None:
        cases = {
            "not an object": "echo hi",
            "no type": {"command": "true"},
            "type not a string": _entry(type=1),
            "unknown type": _entry(type="function"),
            "missing command": {"type": "command", "timeout": 5},
            "command not a string": _entry(command=["true"]),
            "timeout zero": _entry(timeout=0),
            "timeout negative": _entry(timeout=-1),
            "timeout bool": _entry(timeout=True),
            "timeout string": _entry(timeout="5"),
            "timeout null": _entry(timeout=None),
            # JSON.parse reads 1e999 as Infinity; the number schema rejects it.
            "timeout infinite": _entry(timeout=float("inf")),
            "statusMessage not a string": _entry(statusMessage=3),
            "if not a string": _entry(**{"if": ["Bash(git *)"]}),
            "once not a bool": _entry(once="yes"),
            "shell unknown": _entry(shell="zsh"),
            "args not strings": _entry(args=["a", 1]),
            "async not a bool": _entry(**{"async": 1}),
            "asyncRewake not a bool": _entry(asyncRewake="yes"),
            "rewakeMessage empty": _entry(rewakeMessage=""),
            "rewakeSummary empty": _entry(rewakeSummary=""),
            "onFailure unknown value": _entry(onFailure="retry"),
            "onFailure wrong case": _entry(onFailure="Block"),
            "onFailure null": _entry(onFailure=None),
            "onFailure not a string": _entry(onFailure=True),
            "prompt missing prompt": {"type": "prompt"},
            "prompt model not a string": {"type": "prompt", "prompt": "p", "model": 1},
            "prompt continueOnBlock not a bool": {"type": "prompt", "prompt": "p",
                                                  "continueOnBlock": "yes"},
            "agent missing prompt": {"type": "agent", "model": "x"},
            "agent model not a string": {"type": "agent", "prompt": "p", "model": ["x"]},
            "mcp_tool missing tool": {"type": "mcp_tool", "server": "s"},
            "mcp_tool missing server": {"type": "mcp_tool", "tool": "t"},
            "mcp_tool server not a string": {"type": "mcp_tool", "server": 1, "tool": "t"},
            "mcp_tool input not a record": {"type": "mcp_tool", "server": "s", "tool": "t",
                                            "input": []},
            "http missing url": {"type": "http"},
            "http url not a url": {"type": "http", "url": "not a url"},
            "http headers not strings": {"type": "http", "url": "https://x.test/h",
                                         "headers": {"A": 1}},
            "http allowedEnvVars not a list": {"type": "http", "url": "https://x.test/h",
                                               "allowedEnvVars": "TOKEN"},
            "http onFailure unknown value": {"type": "http", "url": "https://x.test/h",
                                             "onFailure": "retry"},
        }
        for name, entry in cases.items():
            for event in sorted(GUARD_EVENTS):
                with self.subTest(case=name, event=event):
                    self.assertFatal(_doc(entry, event=event), "hooks.%s.0.hooks.0" % event)

    def test_on_failure_field(self) -> None:
        # 2.1.295 gives the command and http entries ``onFailure`` (``ni``): enum
        # continue|block, optional, no .catch. ``claude doctor`` on 2.1.295
        # gave these verdicts (docstring, RUNTIME CROSS-CHECK); the agent and
        # mcp_tool legs rest on the byte search (``onFailure:ni()`` twice).
        http = {"type": "http", "url": "https://x.test/h"}
        for value in ("continue", "block"):
            for entry in (_entry(onFailure=value), dict(http, onFailure=value)):
                with self.subTest(value=value, type=entry["type"]):
                    self.assertEqual(settings_findings(_doc(entry)), ([], []))
        self.assertFatal(_doc(_entry(onFailure="retry")), "onFailure")
        self.assertFatal(_doc(_entry(onFailure=None)), "onFailure")
        self.assertFatal(_doc(dict(http, onFailure="Block"), event="PermissionRequest"),
                         "onFailure")
        # Under a non-guard event the entry is dropped and the file still loads.
        fatal, dropped = settings_findings(_doc(_entry(onFailure="retry"), event="PostToolUse"))
        self.assertEqual(fatal, [])
        self.assertTrue(any("onFailure" in d for d in dropped), dropped)
        # On the other entry types the field is an extra key and is stripped.
        for entry in ({"type": "prompt", "prompt": "p", "onFailure": "retry"},
                      {"type": "agent", "prompt": "p", "onFailure": "retry"},
                      {"type": "mcp_tool", "server": "s", "tool": "t", "onFailure": "retry"}):
            with self.subTest(type=entry["type"]):
                self.assertEqual(settings_findings(_doc(entry)), ([], []))

    def test_conservative_blank_command(self) -> None:
        self.assertFatal(_doc(_entry(command="  ")), "conservative")
        self.assertEqual(settings_findings(_doc(_entry(command="  ")), conservative=False)[0], [])

    def test_matcher_shapes(self) -> None:
        self.assertFatal({"hooks": {"PreToolUse": ["Bash"]}}, "matcher must be an object")
        self.assertFatal(_doc(hooks={"type": "command", "command": "x"}), "must be an array")
        self.assertFatal(_doc(matcher=7), "matcher must be a string")
        self.assertFatal(_doc(matcher=None), "matcher must be a string")

    def test_guard_event_value_not_an_array(self) -> None:
        self.assertFatal({"hooks": {"PreToolUse": {"matcher": "Bash", "hooks": [_entry()]}}},
                         "hooks.PreToolUse: must be an array")
        self.assertFatal({"hooks": {"PermissionRequest": "x"}}, "must be an array")

    def test_non_guard_event_value_not_an_array_holding_a_guard(self) -> None:
        # Rule 4, second leg: any event whose non-array value holds a guard.
        self.assertFatal({"hooks": {"PostToolUse": {"x": {"PreToolUse": _GUARD}}}},
                         "hooks.PostToolUse: must be an array")
        # Without a guard inside, the same shape only drops the event.
        fatal, dropped = settings_findings({"hooks": {"PostToolUse": {"x": 1}}})
        self.assertEqual(fatal, [])
        self.assertTrue(dropped)

    def test_matcher_shape_with_an_empty_hooks_object(self) -> None:
        # [qJ] ``!!{}`` is true in JavaScript: a ``matcher`` key beside an empty
        # ``hooks`` object is matcher-shaped, even though ``{}`` is falsy in Python.
        self.assertFatal({"_x": {"matcher": "Bash", "hooks": {}}}, "outside")
        self.assertFatal({"hooks": {"matcher": "Bash", "hooks": {}}}, "single matcher")
        # Without ``matcher`` (and without a string ``type``) the same object is not.
        self.assertEqual(self._fatal({"_x": {"hooks": {}}}), [])

    def test_declared_outside_hooks(self) -> None:
        self.assertFatal({"PreToolUse": _GUARD}, "outside")
        self.assertFatal({"_notes": {"PreToolUse": _GUARD}}, "outside")
        self.assertFatal({"permissions": {"PermissionRequest": _GUARD}}, "outside")
        self.assertFatal({"_x": {"matcher": "Bash", "hooks": [_entry()]}}, "outside")
        self.assertFatal({"_x": [{"hooks": [_entry()]}]}, "outside")
        # Reach: a guard key 5 path steps deep is caught, 6 is past the budget.
        self.assertFatal({"a": {"b": {"c": {"d": {"PreToolUse": _GUARD}}}}}, "outside")
        self.assertEqual(self._fatal({"a": {"b": {"c": {"d": {"e": {"PreToolUse": _GUARD}}}}}}), [])
        # [Spe] The typed-entry skip applies only to entries inside a ``hooks``
        # list. An object with a string ``type`` anywhere else is still scanned.
        self.assertFatal({"_x": {"type": "note", "y": {"PreToolUse": _GUARD}}}, "outside")
        # Inside a ``hooks`` list (under an event key, so the matcher-shape test
        # is off) the same typed object is not descended into.
        self.assertEqual(self._fatal(
            {"PostToolUse": {"hooks": [{"type": "command", "y": {"PreToolUse": _GUARD}}]}}), [])

    def test_hooks_object_malformed(self) -> None:
        self.assertFatal({"hooks": [{"matcher": "Bash", "hooks": [_entry()]}]}, "array")
        self.assertFatal({"hooks": [[{"PreToolUse": _GUARD}]]}, "array")
        self.assertFatal({"hooks": {"matcher": "Bash", "hooks": [_entry()]}}, "single matcher")
        # An array holding ANY plain object drops the file, guard or not.
        self.assertFatal({"hooks": [{"foo": 1}]}, "array")
        # An array of scalars is only ignored.
        fatal, dropped = settings_findings({"hooks": ["x", 1]})
        self.assertEqual(fatal, [])
        self.assertTrue(dropped)

    def test_unknown_event_holding_guards(self) -> None:
        self.assertFatal({"hooks": {"PreToolUsee": {"matcher": "Bash", "hooks": [_entry()]}}},
                         "not a hook event")
        self.assertFatal({"hooks": {"Custom": [{"PreToolUse": _GUARD}]}}, "not a hook event")

    def test_non_guard_matcher_holding_nested_guard(self) -> None:
        doc = _doc(event="PostToolUse", _notes={"PreToolUse": _GUARD})
        self.assertFatal(doc, "hooks.PostToolUse.0: holds PreToolUse/PermissionRequest")

    def test_non_fatal_shapes_stay_non_fatal(self) -> None:
        # Exempt top-level keys are not scanned.
        self.assertEqual(self._fatal({"env": {"PreToolUse": "x"}, "mcpServers": {"s": _GUARD}}), [])
        # A defect under a non-guard event drops that entry only (warning).
        fatal, dropped = settings_findings(_doc(_entry(type="function"), event="PostToolUse"))
        self.assertEqual(fatal, [])
        self.assertTrue(dropped)
        # A null or empty guard event, and an unknown event with no guards.
        self.assertEqual(self._fatal({"hooks": {"PreToolUse": None, "PermissionRequest": []}}), [])
        fatal, dropped = settings_findings({"hooks": {"Custom": [{"matcher": "x"}]}})
        self.assertEqual(fatal, [])
        self.assertTrue(any("Custom: unknown hook event" in d for d in dropped), dropped)
        # [YJ] A misspelled guard event whose guards sit at matcher depth is not
        # fatal: the event is dropped with a warning and the file still loads.
        # That is how a guard is lost silently, so the warning leg must record it
        # (test_no_hook_entry_dropped_with_warning depends on it).
        fatal, dropped = settings_findings({"hooks": {"PretoolUse": _GUARD}})
        self.assertEqual(fatal, [])
        self.assertTrue(any("PretoolUse: unknown hook event" in d for d in dropped), dropped)
        # Unknown extra keys are stripped by the (non-strict) schemas.
        self.assertEqual(self._fatal(_doc(_entry(_comment="y", cloud="nowhere"))), [])

    def test_plugin_profile(self) -> None:
        self.assertEqual(plugin_hooks_json_findings({"hooks": {"PreToolUse": _GUARD}}), ([], []))
        self.assertTrue(plugin_hooks_json_findings({"hooks": "x"})[0])
        self.assertTrue(plugin_hooks_json_findings({"env": {"PreToolUse": _GUARD}})[0])
        self.assertTrue(plugin_hooks_json_findings(
            {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [_entry(type="x")]}]}})[0])
        # The whole hooks.json shaped like one matcher: only the top-level
        # matcher-shape test catches it (its ``hooks`` is an object, so the
        # "hooks must be an object" check does not fire).
        top_matcher = {"matcher": "Bash", "hooks": {"type": "command", "command": "x"}}
        fatal, _ = plugin_hooks_json_findings(top_matcher)
        self.assertTrue(any("top level" in f for f in fatal), fatal)

    def test_red_control_on_real_surface_content(self) -> None:
        """Plant one fatal into a copy of each real surface: the check names its path."""
        for rel in SETTINGS_SURFACES:
            with self.subTest(surface=rel):
                doc = copy.deepcopy(load_json(REPO_ROOT / rel))
                if guard_entry_count(doc):
                    ev = next(e for e in ("PreToolUse", "PermissionRequest")
                              if doc["hooks"].get(e))
                    doc["hooks"][ev][0]["hooks"][0]["type"] = "function"
                    needle = "hooks.%s.0.hooks.0" % ev
                else:
                    doc["PreToolUse"] = _GUARD
                    needle = "outside"
                self.assertFatal(doc, needle)

    def test_file_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "settings.json"
            p.write_text(json.dumps(_doc(matcher=7)), encoding="utf-8")
            self.assertFatal(load_json(p), "hooks.PreToolUse.0")
            p.write_text('{"hooks": {"PreToolUse": [{"hooks": [{"type": "command", '
                         '"command": "x", "timeout": NaN}]}]}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_json(p)
            # 1e999 is valid JSON. Python and JSON.parse both read it as infinity,
            # and the timeout schema must reject it.
            p.write_text('{"hooks": {"PreToolUse": [{"hooks": [{"type": "command", '
                         '"command": "x", "timeout": 1e999}]}]}}', encoding="utf-8")
            self.assertFatal(load_json(p), "hooks.PreToolUse.0.hooks.0")


if __name__ == "__main__":
    unittest.main()
