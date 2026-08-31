#!/usr/bin/env python3
"""Generate ``templates/settings/settings.user.json`` from the base template.

PLAN-169 wave-s330-F (OQ-E5). The user-ceremony template used to be a MANUAL
copy of ``settings.base.json`` with hooks deleted by hand, frozen at 9777a8d.
Its own ``_comment`` claimed it was "derived ... by REMOVING exactly the 10
governance/sentinel/kernel hooks" and that "every RETAINED entry's BEHAVIORAL
fields (matcher/command/timeout) are byte-identical to settings.base.json".
Both claims were FALSE when measured in S330 (see ``_derivation`` in the
generated file and PLAN-169/s330-ceremony-F/DESIGN-F.md):

  * the base template had grown 16 further hooks the manual copy never
    received, so the real subtraction was 26 basenames, not 10;
  * ``check_anti_ceo_overhead.py`` carried a HAND-NARROWED matcher;
  * ``check_output_secrets.py`` silently lost its ``PostToolUseFailure``
    registration;
  * three retained groups carried hand-edited ``_comment`` prose and one a
    hand-edited ``statusMessage``.

Prose cannot be checked by CI, so the prose is replaced by a machine-checked
DERIVATION: the subtraction becomes DATA (the ``_derivation`` object embedded
in the generated file) and this script is the single MECHANISM that applies
it. Same shape as ``.claude/scripts/generate-skill-inventory.sh``: regenerate
after changing the spec, or CI (``--check``) turns red.

The exclusions themselves are not this script's opinion. Every one was ruled
per hook in ``.claude/plans/PLAN-169/s330-ceremony-F/hook-classification-S330.md``
— which also found that the OLD criterion ("blocks edits or requires
GPG/sentinel infra") held for only 5 of the 10 hooks it was written to
justify, and moved two of them (``check_scratchpad_access.py``,
``check_skill_reference_read.py``) INTO the advisory profile. The rule that
does hold is stated once, as ``_derivation.criterion``.

## Why the spec is EMBEDDED rather than a sibling file

The natural home would be ``templates/settings/settings.user.derivation.json``.
Measured in S330: ``.claude/scripts/check-install-profiles.py`` enforces a
BIJECTION between ``scripts/profiles/profiles.json`` hook-stack entries and
``templates/settings/settings*.json`` on disk, so that filename makes the gate
red with ``DRIFT: settings template on disk has no hook_stacks entry`` (rc 1,
reproduced with a positive control). A ``_``-prefixed key inside the template
is the convention these files already use for non-settings metadata
(``_comment``, ``_model_comment``, ``_squad_allowlist_comment``), it reaches
exactly the surfaces the prose it replaces already reached, and it needs no
new delivery route.

## Contract

Sources, one each, no second copy anywhere:

  hooks             base.hooks minus the declared exclusions
  env               base.env minus env_exclude, plus env_overrides
  _model_comment    spec ``literals`` (profile POLICY prose, not mechanism)
  _comment          fixed text in this script (describes the MECHANISM)
  _derivation       the spec itself, round-tripped verbatim
  everything else   COPIED from base verbatim, in base's own key order,
                    unless ``top_level_exclude`` NAMES it with a reason

So ``model``, ``squad_allowlist`` and ``_squad_allowlist_comment`` have one
source (base) and cannot drift by construction, while ``permissions``,
``availableModels`` and the rest of the maintainer surface stay out because
the spec says so, in writing, per key.

Retained hook entries are byte-identical to the base template — including
group ``_comment`` annotations — except where ``matcher_overrides`` or
``annotation_overrides`` declare a difference. Every override must resolve to
a registration that exists in base and is NOT excluded; a dead override is a
spec-integrity failure, never a silent no-op.

## Usage

    python3 .claude/scripts/gen-settings-user-template.py --check
    python3 .claude/scripts/gen-settings-user-template.py --write
    python3 .claude/scripts/gen-settings-user-template.py --json
    python3 .claude/scripts/gen-settings-user-template.py --check --repo-root <path>
    python3 .claude/scripts/gen-settings-user-template.py --check --spec <path>

``--spec`` reads the derivation from a standalone JSON file instead of the
on-disk template. It exists for bootstrap (the first generation, when the
template does not yet carry the key) and for tests; normal operation reads
the spec from the artifact it describes.

Exit codes:
    0 — generated output matches the on-disk template (``--check``), or the
        write/json succeeded.
    1 — DRIFT (``--check`` and the file differs), or the spec failed its
        integrity checks.
    2 — infrastructure: repo root, base template or user template missing,
        unreadable, or not parseable JSON.

Stdlib-only, Python >= 3.9.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

BASE_REL = "templates/settings/settings.base.json"
USER_REL = "templates/settings/settings.user.json"
#: The one regeneration mechanism the artifact may advertise. `source` is
#: validated by VALUE below; `generator` was validated by PRESENCE only,
#: so an empty or wrong path survived `--write`/`--check` round-trips
#: while pointing readers at nothing (pair-rail round 9).
GEN_REL = ".claude/scripts/gen-settings-user-template.py"
SPEC_KEY = "_derivation"

RC_OK = 0
RC_DRIFT = 1
RC_INFRA = 2

#: Closed vocabulary for a DECIDED exclusion, from the S330 classification
#: (``.claude/plans/PLAN-169/s330-ceremony-F/hook-classification-S330.md`` §1).
#: Each verdict there was MEASURED per hook — does it emit ``block``? does it
#: have an advisory switch? what infrastructure does it resolve? — and the
#: audit found that for 5 of the 10 hooks the previously declared criterion
#: was FALSE. These four names are the criterion that actually holds.
EXCLUSION_CLASSES = (
    # Blocks a tool call with no advisory route out.
    "bloqueia-edicao",
    # Blocks, and its allow path resolves Owner-signed sentinel / GPG
    # material that `--ceremony user` never installs.
    "exige-gpg-sentinel",
    # Depends on infrastructure the user ceremony does not install (Codex CLI
    # pin manifest, PROTOCOL.md, .claude/proposals/).
    "exige-infra-ausente-no-user",
    # Observes or reinforces a maintainer rite whose enforcing half this
    # profile does not register — a forensic trail for a gate that is not
    # there.
    "maintainer-only-por-desenho",
)

#: The only class a PENDING entry may carry. A pending entry is excluded from
#: the generated roster exactly like a decided one — the difference is that
#: nobody has ruled on it yet, so it carries an open-question pointer instead
#: of a reason/evidence pair.
PENDING_CLASS = "pending-classification"

#: Top-level keys the generator SOURCES itself instead of copying base's value
#: verbatim. Everything else in base is copied as-is unless ``top_level_exclude``
#: names it.
#:
#: The direction matters. An earlier draft used a literal ``top_level_keep``
#: list; the S330 classification (§3, note on top_level_keep) rejected it as
#: "the same class of literal list OQ-E5 exists to kill" — with a keep list,
#: base gaining a key means the user profile silently does NOT get it, which
#: is the very defect this wave closes, one layer up. But a bare exclude list
#: has the opposite failure: base gains ``permissions`` or ``availableModels``
#: and the advisory profile silently INHERITS it (and
#: ``test-install-deny-baseline.sh`` leg D plus
#: ``test_template_dogfood_parity.py`` would redden).
#:
#: So neither direction is left silent: base keys are carried by default, and
#: ``validate_spec`` requires every base key to be either carried or NAMED in
#: ``top_level_exclude`` with a reason. A new base key stops the generator
#: until someone decides, which is the only honest answer.
TOP_LEVEL_COMPUTED = {
    "_comment": "generated",
    "_derivation": "spec",
    "_model_comment": "literal",
    "hooks": "computed",
    "env": "computed",
}

#: Keys the user template carries that base does NOT have, and where they go.
#: Position is mechanism (deterministic output), not policy.
USER_ONLY_PLACEMENT = (
    ("_derivation", "after", "_comment"),
    ("_model_comment", "before", "model"),
)

#: The generated ``_comment``. Fixed text, and deliberately WITHOUT any count:
#: a number in prose is exactly the claim that rotted here, and no gate in
#: this repo watches a numeral inside a JSON string.
GENERATED_COMMENT = (
    "CEO Orchestration - USER ceremony settings. GENERATED FILE, do not "
    "hand-edit: every hook registration, env key and top-level value below is "
    "DERIVED from templates/settings/settings.base.json by "
    ".claude/scripts/gen-settings-user-template.py, applying the subtraction "
    "declared in the `_derivation` key of this same file. To change what the "
    "user profile carries, edit `_derivation` and re-run the generator with "
    "--write; CI re-runs it with --check and reddens on any drift. The rule "
    "the exclusions follow is stated once, in `_derivation.criterion`, and "
    "every excluded hook carries its own class, reason and evidence. Retained "
    "entries are byte-identical to the base template, including their "
    "`_comment` annotations, except where `_derivation.matcher_overrides` or "
    "`_derivation.annotation_overrides` declares a difference and says why. "
    "All hook FILES are still copied to disk by install.sh, so "
    "validate-governance.sh REQUIRED_FILES stay satisfied; an omitted hook is "
    "simply never registered, and is therefore dormant for the no-GPG user "
    "profile."
)

_PY_BASENAME_RE = re.compile(r"([A-Za-z0-9_.\-]+\.py)")


class SpecError(Exception):
    """The derivation spec is internally inconsistent or does not fit base."""


class InfraError(Exception):
    """A file the generator needs is missing, unreadable, or not JSON."""


# --------------------------------------------------------------------------
# repo / io helpers
# --------------------------------------------------------------------------

def repo_root(explicit: Optional[str]) -> Path:
    if explicit:
        root = Path(explicit).resolve()
        if not root.is_dir():
            raise InfraError("--repo-root is not a directory: %s" % root)
        return root
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InfraError(
            "cannot resolve the repository root via git (%s); pass --repo-root"
            % exc
        )
    if not out:
        raise InfraError("git rev-parse --show-toplevel returned nothing; pass --repo-root")
    return Path(out).resolve()


def load_json(path: Path, label: str) -> Any:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InfraError("%s unreadable at %s: %s" % (label, path, exc))
    except UnicodeDecodeError as exc:
        # Not an OSError, and it fires BEFORE json ever sees the bytes — so
        # without this the CLI printed a traceback and exited with a generic
        # status, breaking its own documented contract (unreadable or
        # unparseable input => RC_INFRA, pair-rail round 6).
        raise InfraError(
            "%s is not valid UTF-8 at %s: %s" % (label, path, exc))
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise InfraError("%s is not parseable JSON at %s: %s" % (label, path, exc))


def render(obj: Any) -> str:
    """The one serialisation. Any other formatting is drift by definition."""
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------
# hook identity
# --------------------------------------------------------------------------

def hook_basename(command: Any) -> str:
    """The identity a hook registration is addressed by in the spec.

    For the overwhelming majority that is the ``*.py`` basename the command
    runs. But the base template also registers at least one INLINE command
    with no script at all (measured S330: a ``PostToolUse`` ``echo`` emitting
    a fixed allow payload), and such a registration still has to be
    addressable — otherwise the generator either refuses to run at all or,
    worse, cannot express an exclusion for it. Inline commands therefore get
    a stable content-derived identity, ``inline:<12 hex of sha256>``, which a
    human can copy into the spec and which CHANGES if the command text
    changes — turning any exclusion of it into a loud dead-exclusion error
    rather than a silent mismatch.

    Fail-CLOSED only where identity is impossible: a missing or non-string
    ``command``.
    """
    if not isinstance(command, str) or not command.strip():
        raise SpecError("hook entry has no string `command` — cannot identify it")
    found = _PY_BASENAME_RE.findall(command)
    if not found:
        digest = hashlib.sha256(command.encode("utf-8")).hexdigest()[:12]
        return "inline:%s" % digest
    return found[-1].rsplit("/", 1)[-1]


def base_registrations(base: Any) -> List[Tuple[str, str]]:
    """Every ``(event, basename)`` the base template registers, in file order."""
    hooks = base.get("hooks") if isinstance(base, dict) else None
    if not isinstance(hooks, dict):
        raise SpecError("base template has no object `hooks`")
    out: List[Tuple[str, str]] = []
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise SpecError("base template event %r is not an array" % event)
        for group in groups:
            if not isinstance(group, dict):
                raise SpecError("base template event %r holds a non-object block" % event)
            entries = group.get("hooks")
            if not isinstance(entries, list) or not entries:
                raise SpecError(
                    "base template event %r holds a block with no `hooks` array" % event
                )
            for entry in entries:
                if not isinstance(entry, dict):
                    raise SpecError("base template event %r holds a non-object hook" % event)
                out.append((event, hook_basename(entry.get("command"))))
    return out


# --------------------------------------------------------------------------
# spec
# --------------------------------------------------------------------------

def _as_list(spec: Dict[str, Any], key: str) -> List[Any]:
    val = spec.get(key, [])
    if val is None:
        return []
    if not isinstance(val, list):
        raise SpecError("`%s` must be an array (found %s)" % (key, type(val).__name__))
    return val


def _as_dict(spec: Dict[str, Any], key: str) -> Dict[str, Any]:
    val = spec.get(key, {})
    if val is None:
        return {}
    if not isinstance(val, dict):
        raise SpecError("`%s` must be an object (found %s)" % (key, type(val).__name__))
    return val


def _override_key(raw: Any, field: str) -> Tuple[Optional[str], str]:
    """Parse an override key: ``"Event/basename.py"`` or ``"basename.py"``."""
    if not isinstance(raw, str) or not raw.strip():
        raise SpecError("`%s` has a non-string key" % field)
    if "/" in raw:
        event, _, name = raw.partition("/")
        if not event or not name:
            raise SpecError("`%s` key %r is not `Event/basename.py`" % (field, raw))
        return event, name
    return None, raw


#: Closed vocabulary of an exclusion entry, PER BUCKET (pair-rail rounds 4-5).
#: One shared set let a DECIDED exclusion carry `oq`/`note` and a PENDING one
#: carry `reason`/`evidence` — contradictory audit records that round-tripped
#: with a green `--check`. A decided exclusion justifies itself (`reason` +
#: `evidence` that resolves); a pending one names the open question instead,
#: and its rationale lives once in `pending_note`.
_EXCLUSION_FIELDS_DECIDED = frozenset({
    "name", "event", "class", "reason", "evidence", "_comment",
})
_EXCLUSION_FIELDS_PENDING = frozenset({
    "name", "event", "class", "oq", "_comment",
})


#: Closed top-level vocabulary of the derivation spec (pair-rail round 3). A key
#: outside this set is a typo or an invention; either way the derivation would
#: ignore it while `--check` stayed green.
SPEC_KEYS = frozenset({
    # metadata, carried for the reader and never consumed by the derivation
    "_comment", "classification", "provisional",
    # required
    "source", "generator", "criterion", "top_level_exclude",
    # the subtraction itself
    "exclude_hooks", "exclude_hooks_pending", "pending_note",
    "env_exclude", "env_overrides",
    "matcher_overrides", "annotation_overrides",
    "literals", "blocking_inclusions",
})

#: What an *annotation* may touch: presentation, never behaviour. `command`,
#: `type`, `timeout` and `prompt` decide what runs and for how long, and a
#: second source for any of them is the defect this generator removes.
ANNOTATION_FIELDS = frozenset({"statusMessage", "_comment"})

def validate_spec(spec: Any, base: Any) -> None:
    """Reject a spec that cannot mean what it says. Raises SpecError."""
    if not isinstance(spec, dict):
        raise SpecError("the derivation spec is not a JSON object")

    for required in ("source", "generator", "criterion", "top_level_exclude"):
        if required not in spec:
            raise SpecError("spec is missing required key `%s`" % required)
    # Closed vocabulary. Without it a typo (`env_override`, `exclude_hook`) was
    # accepted, round-tripped into `_derivation`, and then IGNORED by the
    # derivation, which used the correctly-spelled default — `--check` green
    # while the declared change did nothing. That is the silent-no-op class
    # this validator exists to prevent, reappearing in its own input surface
    # (pair-rail round 3).
    # RETIRED keys get their own sentence first: a generic "unknown key" would
    # be correct and useless to whoever is still on the old spelling.
    if "top_level_keep" in spec:
        raise SpecError(
            "`top_level_keep` was replaced by `top_level_exclude` (S330 "
            "classification §3): a keep list makes a NEW base key silently "
            "absent from the advisory profile, which is the defect this wave "
            "closes"
        )
    unknown_top = sorted(set(spec) - SPEC_KEYS)
    if unknown_top:
        raise SpecError(
            "spec has unknown key(s) %s. The vocabulary is closed: %s. A "
            "misspelled key is accepted by nothing and silently does nothing, "
            "which is worse than an error." % (unknown_top, sorted(SPEC_KEYS))
        )
    if spec.get("source") != Path(BASE_REL).name:
        raise SpecError(
            "spec `source` must be %r (found %r) — this generator derives from "
            "the base template and nothing else" % (Path(BASE_REL).name, spec.get("source"))
        )
    # Same ruler as `source`, one line down: the artifact ADVERTISES its
    # regeneration mechanism, and generate() round-trips the spec, so a
    # wrong or empty path here stays green forever (pair-rail round 9).
    if spec.get("generator") != GEN_REL:
        raise SpecError(
            "spec `generator` must be %r (found %r) — the artifact's own "
            "pointer at how to regenerate it is a declaration like any "
            "other, and an unvalidated one survives every round-trip"
            % (GEN_REL, spec.get("generator"))
        )

    regs = base_registrations(base)
    reg_set: Set[Tuple[str, str]] = set(regs)
    names_in_base: Set[str] = set(name for _, name in regs)

    # --- exclusions -------------------------------------------------------
    seen: Set[Tuple[Optional[str], str]] = set()
    for bucket, pending in (("exclude_hooks", False), ("exclude_hooks_pending", True)):
        for item in _as_list(spec, bucket):
            if not isinstance(item, dict):
                raise SpecError("`%s` holds a non-object entry" % bucket)
            # Closed vocabulary per ENTRY. `events` (a typo of `event`)
            # validated, `get("event")` returned None, and the entry became a
            # BARE exclusion — silently removing EVERY registration of a
            # security hook, with `--check` green on the regenerated artifact.
            # A typo that WIDENS a subtraction is the worst shape this family
            # takes (pair-rail round 4).
            _allowed = (_EXCLUSION_FIELDS_PENDING if pending
                        else _EXCLUSION_FIELDS_DECIDED)
            _unknown_entry = sorted(set(item) - _allowed)
            if _unknown_entry:
                raise SpecError(
                    "`%s` entry has field(s) %s that do not belong to it — "
                    "allowed here: %s. A misspelled `event` silently turns a "
                    "scoped exclusion into a total one, and a field from the "
                    "OTHER bucket is an audit record that contradicts itself."
                    % (bucket, _unknown_entry, sorted(_allowed))
                )
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                raise SpecError("`%s` entry has no `name`" % bucket)
            event = item.get("event")
            if event is not None and (not isinstance(event, str) or not event.strip()):
                raise SpecError("`%s` entry %r has a non-string `event`" % (bucket, name))

            key = (event, name)
            if key in seen:
                raise SpecError(
                    "duplicate exclusion for %s%s — an exclusion listed twice "
                    "hides which of the two the reviewer approved"
                    % (name, " under %s" % event if event else "")
                )
            seen.add(key)

            # DEAD exclusion: names a registration the base template does not
            # have. This is the rot the wave exists to close, so it is red.
            if event is None:
                if name not in names_in_base:
                    raise SpecError(
                        "`%s` excludes %s, which the base template does not "
                        "register anywhere — a dead exclusion" % (bucket, name)
                    )
            elif (event, name) not in reg_set:
                raise SpecError(
                    "`%s` excludes %s under event %s, which the base template "
                    "does not register — a dead exclusion" % (bucket, name, event)
                )

            klass = item.get("class")
            if pending:
                if klass != PENDING_CLASS:
                    raise SpecError(
                        "`exclude_hooks_pending` entry %s must carry class %r "
                        "(found %r)" % (name, PENDING_CLASS, klass)
                    )
                oq = item.get("oq")
                if not isinstance(oq, str) or not oq.strip():
                    raise SpecError(
                        "pending exclusion %s must name the open question "
                        "(`oq`) that will decide it" % name
                    )
                if "note" in item:
                    raise SpecError(
                        "pending exclusion %s carries its own `note`; the "
                        "rationale is the same for every pending entry and "
                        "lives once, in `pending_note`" % name
                    )
            else:
                if klass not in EXCLUSION_CLASSES:
                    raise SpecError(
                        "exclusion %s has class %r, which is not in the closed "
                        "vocabulary %s" % (name, klass, list(EXCLUSION_CLASSES))
                    )
                for field in ("reason", "evidence"):
                    val = item.get(field)
                    if not isinstance(val, str) or not val.strip():
                        raise SpecError(
                            "exclusion %s has an empty `%s` — an undocumented "
                            "subtraction is the defect this spec replaces"
                            % (name, field)
                        )

    if _as_list(spec, "exclude_hooks_pending"):
        note = spec.get("pending_note")
        if not isinstance(note, str) or not note.strip():
            raise SpecError(
                "`exclude_hooks_pending` is non-empty but `pending_note` does "
                "not say why those registrations are held out"
            )

    # A bare exclusion removes EVERY registration of the basename, so an
    # event-qualified entry for the same hook is dead data — and it passed,
    # because the two tuple keys differ. Checked across BOTH buckets
    # (pair-rail round 3).
    _bare: Set[str] = set()
    _scoped: Set[Tuple[str, str]] = set()
    for _bucket in ("exclude_hooks", "exclude_hooks_pending"):
        for _item in _as_list(spec, _bucket):
            if not isinstance(_item, dict):
                continue
            _nm = _item.get("name")
            if not isinstance(_nm, str):
                continue
            _ev = _item.get("event")
            if isinstance(_ev, str) and _ev:
                _scoped.add((_ev, _nm))
            else:
                _bare.add(_nm)
    _shadowed = sorted({n for _e, n in _scoped} & _bare)
    if _shadowed:
        raise SpecError(
            "these hooks are excluded BOTH bare and event-qualified: %s. The "
            "bare entry already removes every registration, so the qualified "
            "one is dead data. Keep exactly one." % _shadowed
        )

    excluded_pairs, excluded_names = exclusion_sets(spec)

    def _retained_in_block(event: str, name: str) -> int:
        """How many entries survive in the BASE BLOCK that carries this hook.

        `matcher` and a group `_comment` belong to the BLOCK, not to one
        registration inside it, so they can only be applied when the block
        narrows to a single entry. The ambiguity check above counts
        registrations matching the NAME across events; this counts entries
        inside the one block, which is a different question and the one the
        derivation actually asks.
        """
        for group in base["hooks"].get(event, []):
            entries = [hook_basename(e.get("command")) for e in group.get("hooks", [])]
            if name not in entries:
                continue
            return sum(
                1 for n in entries
                if n not in excluded_names and (event, n) not in excluded_pairs
            )
        return 0

    def _base_site(event: str, name: str) -> Tuple[Any, Any]:
        """The (block, entry) in the BASE for one retained (event, name).

        Serves the no-op guards below: an override whose declared value is
        byte-equal to what the base already carries changes no output byte,
        so its reason/evidence would survive as stale justification for an
        exception that no longer exists (pair-rail round 9).
        """
        for _blk in base.get("hooks", {}).get(event, []):
            if not isinstance(_blk, dict):
                continue
            for _ent in _blk.get("hooks", []):
                if isinstance(_ent, dict) and hook_basename(_ent.get("command")) == name:
                    return _blk, _ent
        return None, None

    # --- overrides --------------------------------------------------------
    for field in ("matcher_overrides", "annotation_overrides"):
        table = _as_dict(spec, field)
        # `lookup` in `derive_hooks` prefers the event-qualified key over the
        # bare one, so declaring BOTH means the bare entry is applied never and
        # refused never. Each passes the checks below on its own — the defect
        # only exists in their RELATION, so it is checked here, once, before
        # the per-key loop (pair-rail round 2).
        for raw_key in table:
            if "/" not in raw_key:
                continue
            bare = raw_key.split("/", 1)[1]
            if bare in table:
                raise SpecError(
                    "`%s` declares BOTH %r and %r. The qualified key wins and "
                    "the bare one is silently ignored — a declaration that "
                    "does nothing. Keep exactly one." % (field, bare, raw_key)
                )
        for raw_key, value in table.items():
            event, name = _override_key(raw_key, field)
            targets = [r for r in regs if r[1] == name and (event is None or r[0] == event)]
            if not targets:
                raise SpecError(
                    "`%s` targets %s, which the base template does not "
                    "register — a dead override" % (field, raw_key)
                )
            live = [t for t in targets if t not in excluded_pairs and t[1] not in excluded_names]
            if not live:
                raise SpecError(
                    "`%s` targets %s, which is EXCLUDED — an override on a "
                    "registration that never reaches the output" % (field, raw_key)
                )
            if len(live) > 1:
                raise SpecError(
                    "`%s` key %s is ambiguous: it matches %d retained "
                    "registrations (%s). Qualify it as `Event/%s`."
                    % (field, raw_key, len(live), ", ".join(e for e, _ in live), name)
                )
            if field == "matcher_overrides":
                # Shape from the S330 classification §3: an override carries
                # its own justification, the same discipline `exclude_hooks`
                # has. A bare string would let a matcher be narrowed with no
                # recorded reason — which is exactly how the current one got
                # there.
                if not isinstance(value, dict):
                    raise SpecError(
                        "`matcher_overrides[%s]` must be an object with "
                        "`matcher`, `reason` and `evidence`" % raw_key
                    )
                unknown = set(value) - {"matcher", "reason", "evidence"}
                if unknown:
                    raise SpecError(
                        "`matcher_overrides[%s]` has unknown field(s) %s"
                        % (raw_key, sorted(unknown))
                    )
                for sub in ("matcher", "reason", "evidence"):
                    if not isinstance(value.get(sub), str) or not value[sub].strip():
                        raise SpecError(
                            "`matcher_overrides[%s]` has an empty `%s`"
                            % (raw_key, sub)
                        )
                # A matcher belongs to the BLOCK. If the block keeps more
                # than one entry, `derive_hooks` cannot attribute the matcher
                # to this registration and drops the override — a declaration
                # that does nothing, which is the class this spec removes.
                # Fail-CLOSED and by name (pair-rail round 1, P2-1).
                _kept = _retained_in_block(live[0][0], live[0][1])
                if _kept != 1:
                    raise SpecError(
                        "`matcher_overrides[%s]` targets a block that keeps %d "
                        "entries. A matcher belongs to the block, not to one "
                        "hook inside it, so this override would be SILENTLY "
                        "DROPPED. Either exclude the other entries of that "
                        "block, or narrow the matcher in the base template."
                        % (raw_key, _kept)
                    )
                # Presence passed, scope passed — now the VALUE. If the
                # base block already carries this exact matcher (because
                # the base moved underneath the spec), the override is a
                # NO-OP whose reason/evidence read as a live exception.
                _blk, _ent = _base_site(live[0][0], live[0][1])
                if _blk is not None and value["matcher"] == _blk.get("matcher", ""):
                    raise SpecError(
                        "`matcher_overrides[%s]` is a NO-OP: the base block "
                        "already carries matcher %r, so the output is "
                        "identical with or without it and its "
                        "reason/evidence survive as stale justification. "
                        "Delete the override, or update it to the value it "
                        "should enforce (pair-rail round 9)."
                        % (raw_key, value["matcher"])
                    )
            else:
                if not isinstance(value, dict):
                    raise SpecError("`annotation_overrides[%s]` must be an object" % raw_key)
                unknown = set(value) - {"_comment", "hook", "reason"}
                if unknown:
                    raise SpecError(
                        "`annotation_overrides[%s]` has unknown field(s) %s — "
                        "allowed: _comment, hook, reason"
                        % (raw_key, sorted(unknown))
                    )
                hook_fields = value.get("hook", {})
                if not isinstance(hook_fields, dict):
                    raise SpecError(
                        "`annotation_overrides[%s].hook` must be an object" % raw_key
                    )
                # `command` decides WHAT RUNS. An override of it would be a
                # second source for the hook roster, which is the whole class
                # this generator removes.
                # Closed vocabulary, not a denylist of one. Rejecting only
                # `command` let `type`, `timeout` and `prompt` through —
                # `timeout` IS behaviour, and a second source for it is exactly
                # the class this generator removes; `type` can make the
                # inherited command unreachable (pair-rail round 3).
                behavioural = sorted(set(hook_fields) - ANNOTATION_FIELDS)
                if behavioural:
                    raise SpecError(
                        "`annotation_overrides[%s].hook` may not override %s — "
                        "those decide BEHAVIOUR and belong to the base "
                        "template. Annotation fields are: %s"
                        % (raw_key, behavioural, sorted(ANNOTATION_FIELDS))
                    )
                # The NAME being allowed says nothing about the VALUE.
                # `{"statusMessage": {"x": 1}}` validated and was emitted
                # straight into the hook entry, so a fresh install and every
                # plugin build received schema-invalid configuration with
                # `--check` green (pair-rail round 5).
                for field, val in hook_fields.items():
                    if not isinstance(val, str):
                        raise SpecError(
                            "`annotation_overrides[%s].hook.%s` must be a "
                            "string, got %s — the value is emitted into the "
                            "hook entry verbatim"
                            % (raw_key, field, type(val).__name__)
                        )
                if "_comment" in value and not isinstance(value["_comment"], str):
                    raise SpecError(
                        "`annotation_overrides[%s]._comment` must be a string"
                        % raw_key
                    )
                # Same discipline as `exclude_hooks` and `matcher_overrides`:
                # an exception carries its justification. DESIGN-F §3 states
                # `reason` as mandatory here; the validator did not enforce it,
                # so an undocumented annotation could be blessed by `--check`
                # (pair-rail round 1, P2-2).
                reason = value.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    raise SpecError(
                        "`annotation_overrides[%s]` has no `reason` — an "
                        "undocumented exception is the defect this spec "
                        "replaces" % raw_key
                    )
                # And it must actually override something. A reason-only entry
                # changes no byte, so it is a dead exception that survives
                # every gate while claiming an exception exists.
                if "_comment" not in value and not hook_fields:
                    raise SpecError(
                        "`annotation_overrides[%s]` changes nothing: it has "
                        "neither `_comment` nor a non-empty `hook`. A dead "
                        "override reads as a documented exception and is not "
                        "one." % raw_key
                    )
                # A group `_comment` has the same block-scope problem as a
                # matcher (P2-1): `derive_hooks` only writes it when the block
                # narrows to one entry.
                if "_comment" in value:
                    _kept = _retained_in_block(live[0][0], live[0][1])
                    if _kept != 1:
                        raise SpecError(
                            "`annotation_overrides[%s]._comment` targets a "
                            "block that keeps %d entries. A block comment "
                            "cannot be attributed to one hook inside it, so "
                            "this override would be SILENTLY DROPPED. Move the "
                            "note to `reason`, or exclude the other entries."
                            % (raw_key, _kept)
                        )
                # Same VALUE ruler as the matcher branch above: a field
                # whose declared value equals what the base already has is
                # a dead exception wearing a live reason (pair-rail r9).
                _blk, _ent = _base_site(live[0][0], live[0][1])
                for _field in sorted(hook_fields):
                    if _ent is not None and _ent.get(_field) == hook_fields[_field]:
                        raise SpecError(
                            "`annotation_overrides[%s].hook.%s` is a NO-OP: "
                            "the base entry already carries this exact "
                            "value. Delete the field or update it "
                            "(pair-rail round 9)." % (raw_key, _field)
                        )
                if ("_comment" in value and _blk is not None
                        and _blk.get("_comment") == value["_comment"]):
                    raise SpecError(
                        "`annotation_overrides[%s]._comment` is a NO-OP: "
                        "the base block already carries this exact comment. "
                        "Delete it or update it (pair-rail round 9)."
                        % raw_key
                    )

    # --- env --------------------------------------------------------------
    base_env = base.get("env", {})
    if not isinstance(base_env, dict):
        raise SpecError("base template `env` is not an object")
    env_exclude = _as_list(spec, "env_exclude")
    for key in env_exclude:
        if not isinstance(key, str):
            raise SpecError("`env_exclude` holds a non-string entry")
        if key not in base_env:
            raise SpecError(
                "`env_exclude` names %s, which the base template does not set "
                "— a dead exclusion" % key
            )
    env_overrides = _as_dict(spec, "env_overrides")
    for key, value in env_overrides.items():
        if not isinstance(value, str):
            raise SpecError(
                "`env_overrides[%s]` must be a string — settings env values "
                "are strings" % key
            )
        if key in env_exclude:
            raise SpecError(
                "%s is in BOTH `env_exclude` and `env_overrides` — the spec "
                "does not say what should happen" % key
            )

    # --- literals / top level --------------------------------------------
    literals = _as_dict(spec, "literals")
    excluded_top = _as_list(spec, "top_level_exclude")
    seen_top = set()
    for item in excluded_top:
        if not isinstance(item, dict):
            raise SpecError("`top_level_exclude` holds a non-object entry")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise SpecError("`top_level_exclude` entry has no `name`")
        if name in seen_top:
            raise SpecError("`top_level_exclude` names %r twice" % name)
        seen_top.add(name)
        if name not in base:
            raise SpecError(
                "`top_level_exclude` names %r, which the base template does "
                "not carry — a dead exclusion" % name
            )
        if name in TOP_LEVEL_COMPUTED:
            raise SpecError(
                "`top_level_exclude` names %r, which the generator sources "
                "itself; excluding it would produce a template without it" % name
            )
        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise SpecError(
                "`top_level_exclude` entry %r has an empty `reason` — an "
                "undeclared omission is the defect this spec replaces" % name
            )

    # The generated fields ride on anchors from the base document. If an anchor
    # is excluded (or a future base drops it), the placement loop takes the
    # generated field with it — and losing `_derivation` is UNRECOVERABLE in
    # the normal path: the next `--check` exits 2 because the artifact no
    # longer carries its own spec. Fail-CLOSED here, where the input is still
    # a decision rather than a byte on disk (pair-rail round 2).
    _top_excluded = set(item["name"] for item in _as_list(spec, "top_level_exclude")
                        if isinstance(item, dict) and "name" in item)
    for _generated, _where, _anchor in USER_ONLY_PLACEMENT:
        # An anchor ABSENT from the base is not an error: `generate`
        # emits the generated field anyway (appended, in table order). Only an
        # anchor the SPEC removes is refused — that is an operator decision
        # about the shipped artifact, and quietly relocating the field would
        # hide it from the person making the decision.
        if _anchor in _top_excluded:
            raise SpecError(
                "`top_level_exclude` removes `%s`, but `%s` is placed %s it — "
                "excluding the anchor drops the generated field too. "
                "%s" % (_anchor, _generated, _where,
                        "Losing `_derivation` leaves an artifact that cannot "
                        "read its own spec (rc 2 on the next --check)."
                        if _generated == "_derivation"
                        else "Keep the anchor, or move the field.")
            )

    # Both directions are loud, by different mechanisms, and neither is
    # silent:
    #   dropped  -> `top_level_exclude` must NAME it, with a reason (above);
    #   inherited-> a new base key is COPIED, so the generated bytes change,
    #               so `--check` reddens and the key shows up in the diff a
    #               human must review before `--write` (and the write itself
    #               goes through the canonical-edit ceremony).
    # What is impossible is a base key quietly appearing in, or vanishing
    # from, the advisory profile without a person seeing it.

    for key, source in TOP_LEVEL_COMPUTED.items():
        if source == "literal" and key not in literals:
            raise SpecError(
                "`literals` must provide %r (the generator has no other "
                "source for it)" % key
            )
    for key in literals:
        if TOP_LEVEL_COMPUTED.get(key) != "literal":
            raise SpecError(
                "`literals` provides %r, which the generator does not source "
                "from `literals` — dead data" % key
            )

    # --- blocking inclusions ----------------------------------------------
    # A hook that is KEPT and can still block one call is not a contradiction
    # of the criterion — but it is a claim, and a claim needs a route. Each is
    # named here with the alternative the adopter actually has, and the
    # validator refuses an entry that is excluded, dead, or undocumented
    # (pair-rail round 2, P2-c).
    blocking = _as_list(spec, "blocking_inclusions")
    seen_blocking = set()
    for item in blocking:
        if not isinstance(item, dict):
            raise SpecError("`blocking_inclusions` entries must be objects")
        unknown = set(item) - {"hook", "route", "evidence"}
        if unknown:
            raise SpecError(
                "`blocking_inclusions` entry has unknown field(s) %s — "
                "allowed: hook, route, evidence" % sorted(unknown)
            )
        name = item.get("hook")
        if not isinstance(name, str) or not name.strip():
            raise SpecError("`blocking_inclusions` entry has no `hook`")
        if name in seen_blocking:
            raise SpecError(
                "`blocking_inclusions` names %s twice" % name)
        seen_blocking.add(name)
        for field in ("route", "evidence"):
            val = item.get(field)
            if not isinstance(val, str) or not val.strip():
                raise SpecError(
                    "`blocking_inclusions[%s]` has an empty `%s` — an "
                    "undocumented block is the thing the criterion forbids"
                    % (name, field)
                )
        if name not in {n for _e, n in regs}:
            raise SpecError(
                "`blocking_inclusions` names %s, which the base template does "
                "not register — a dead declaration" % name
            )
        # "Excluded" has to mean EVERY registration is gone. A hook registered
        # under two events with only one excluded still reaches the adopter and
        # can still block, so its route must be documentable — refusing the
        # entry because ONE scoped exclusion carries the basename is the same
        # over-broad reading round 4 found in the install oracle (round 6).
        _survivors = [
            (e, n) for e, n in regs if n == name
            and n not in excluded_names and (e, n) not in excluded_pairs
        ]
        if not _survivors:
            raise SpecError(
                "`blocking_inclusions` names %s, whose registrations are ALL "
                "excluded. The list describes hooks the profile KEEPS; a hook "
                "that never reaches the adopter needs no route." % name
            )

    criterion = spec.get("criterion")
    if not isinstance(criterion, str) or not criterion.strip():
        raise SpecError(
            "spec must carry a `criterion` — the one-line rule the exclusions "
            "follow. The frozen copy's criterion was measured FALSE for 5 of "
            "its 10 hooks precisely because nothing checked it was stated."
        )


def exclusion_sets(spec: Dict[str, Any]) -> Tuple[Set[Tuple[str, str]], Set[str]]:
    """``(event, name)`` pairs and bare names the spec removes.

    An entry WITH ``event`` removes only that registration; an entry WITHOUT
    one removes every registration of the basename. The distinction exists
    because ``check_output_secrets.py`` is registered under two events, and
    the manual copy dropped exactly one of them.
    """
    pairs: Set[Tuple[str, str]] = set()
    names: Set[str] = set()
    for bucket in ("exclude_hooks", "exclude_hooks_pending"):
        for item in _as_list(spec, bucket):
            name = item.get("name")
            event = item.get("event")
            if event:
                pairs.add((event, name))
            else:
                names.add(name)
    return pairs, names


# --------------------------------------------------------------------------
# derivation
# --------------------------------------------------------------------------

def derive_hooks(base: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
    pairs, names = exclusion_sets(spec)
    matcher_ov = _as_dict(spec, "matcher_overrides")
    annot_ov = _as_dict(spec, "annotation_overrides")

    def lookup(table: Dict[str, Any], event: str, name: str) -> Any:
        if "%s/%s" % (event, name) in table:
            return table["%s/%s" % (event, name)]
        return table.get(name)

    out: Dict[str, Any] = {}
    for event, groups in base["hooks"].items():
        kept_groups: List[Dict[str, Any]] = []
        for group in groups:
            kept_entries = []
            for entry in group["hooks"]:
                name = hook_basename(entry.get("command"))
                if name in names or (event, name) in pairs:
                    continue
                kept_entries.append((name, entry))
            if not kept_entries:
                # Every entry of this block was subtracted; the block itself
                # is meaningless without them.
                continue
            new_group = dict(group)  # preserves base key order
            new_entries = []
            for name, entry in kept_entries:
                new_entry = dict(entry)
                annot = lookup(annot_ov, event, name)
                if isinstance(annot, dict):
                    for field, value in annot.get("hook", {}).items():
                        new_entry[field] = value
                new_entries.append(new_entry)
            new_group["hooks"] = new_entries

            if len(kept_entries) == 1:
                only = kept_entries[0][0]
                matcher = lookup(matcher_ov, event, only)
                if isinstance(matcher, dict):
                    new_group["matcher"] = matcher["matcher"]
                annot = lookup(annot_ov, event, only)
                if isinstance(annot, dict) and "_comment" in annot:
                    new_group["_comment"] = annot["_comment"]
            kept_groups.append(new_group)
        if kept_groups:
            # An event left with no blocks is REMOVED, not emitted empty: an
            # empty array is a claim that the event is wired with nothing.
            out[event] = kept_groups
    return out


def derive_env(base: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, str]:
    excluded = set(_as_list(spec, "env_exclude"))
    overrides = _as_dict(spec, "env_overrides")
    out: Dict[str, str] = {}
    for key, value in base.get("env", {}).items():
        if key in excluded:
            continue
        out[key] = overrides.get(key, value)
    for key, value in overrides.items():
        if key not in out:
            out[key] = value
    return out


def generate(base: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
    """Build the user template. Assumes ``validate_spec`` already passed.

    Emission order is BASE's order, with the excluded keys removed and the
    user-only keys inserted at the positions ``USER_ONLY_PLACEMENT`` fixes.
    Deriving the order from base rather than from a literal list means one
    less hand-maintained sequence to rot.
    """
    literals = _as_dict(spec, "literals")
    excluded = set(
        item["name"] for item in _as_list(spec, "top_level_exclude")
    )

    def value_for(key: str) -> Any:
        source = TOP_LEVEL_COMPUTED.get(key)
        if source == "spec":
            return spec
        if source == "generated":
            return GENERATED_COMMENT
        if source == "literal":
            return literals[key]
        if source == "computed":
            return derive_env(base, spec) if key == "env" else derive_hooks(base, spec)
        return base[key]

    before: Dict[str, List[str]] = {}
    after: Dict[str, List[str]] = {}
    for key, where, anchor in USER_ONLY_PLACEMENT:
        (before if where == "before" else after).setdefault(anchor, []).append(key)

    out: Dict[str, Any] = {}
    for key in base:
        if key in excluded:
            continue
        for extra in before.get(key, []):
            out[extra] = value_for(extra)
        out[key] = value_for(key)
        for extra in after.get(key, []):
            out[extra] = value_for(extra)
    # A generated field whose anchor is not in the base would otherwise vanish
    # with it. Position is negotiable; presence is not — without `_derivation`
    # the artifact cannot read its own spec, and the next `--check` exits 2
    # (pair-rail round 2, P2-b). Appended in the table's declared order so the
    # output stays deterministic.
    for generated, _where, _anchor in USER_ONLY_PLACEMENT:
        if generated not in out:
            out[generated] = value_for(generated)
    # Same vanishing act, one table up: every COMPUTED key must reach the
    # output even when the base omits its passthrough twin. A base without
    # `env` is a shape `validate_spec` accepts, and losing `env` here silently
    # drops every declared `env_override` — with the shipped spec that would
    # ship `check_config_protection.py` BLOCKING instead of advisory; a
    # missing base `_comment` likewise swallows the generated one (pair-rail
    # round 10). `hooks` cannot be absent (validate_spec requires it) but is
    # covered anyway: the rule is the TABLE, not a hand-picked subset of it.
    for computed_key in TOP_LEVEL_COMPUTED:
        if computed_key not in out and computed_key not in excluded:
            out[computed_key] = value_for(computed_key)
    return out


def _require_reviewed_spec(root: Path, resolved: Path) -> None:
    """`--write --spec` demands a spec git has SEEN. Raises SpecError.

    Round 3 asked whether the file was inside the repository. Round 4 showed
    that is not provenance: an UNTRACKED `spec.json` written anywhere under the
    tree passed, and then drove a write to a canonical-guarded template through
    Bash — where `check_canonical_edit` does not look, because it matches
    Edit/Write/MultiEdit and not Bash.

    Tracked-and-unmodified is the question that means something: such a file
    went through the same review as any other. Untracked, or tracked with an
    uncommitted change, is exactly the shape of a spec someone just wrote.

    Fail-CLOSED on an unusable git: if provenance cannot be answered, the
    answer is no. This is a POLICY gate — an environment where provenance is
    unverifiable is not one where this particular write is safe.
    """
    try:
        rel = resolved.relative_to(root.resolve())
    except ValueError:
        raise SpecError(
            "refusing `--write` with a spec from outside the repository: %s\n"
            "  `--spec` is for bootstrap; combined with `--write` it would let "
            "an unreviewed document rewrite a canonical-guarded template "
            "through a Bash call.\n"
            "  Run `--check` to see what it would produce." % resolved
        )
    def _git(args, want_bytes=False):
        """Run git, or REFUSE. A git that cannot answer is not a green light."""
        try:
            proc = subprocess.run(
                ["git", "-C", str(root)] + args,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise SpecError(
                "refusing `--write --spec %s`: could not ask git about its "
                "provenance (%s). Unverifiable provenance is not provenance."
                % (rel, exc)
            )
        return proc

    tracked = _git(["ls-files", "--error-unmatch", "--", str(rel)]).returncode == 0
    if not tracked:
        raise SpecError(
            "refusing `--write` with an UNTRACKED spec: %s\n"
            "  Being inside the repository is not provenance — an untracked "
            "file has been reviewed by nobody, and this write lands on a "
            "canonical-guarded template through a Bash call that the "
            "canonical-edit hook does not see.\n"
            "  Commit the spec first, or run `--check`." % rel
        )

    # BYTES, not porcelain. `git status` lies by design when the file carries
    # `assume-unchanged` or `skip-worktree`: the index flag tells git to stop
    # looking, so a tracked-and-EDITED spec reports clean. And the previous
    # version discarded git's RETURN CODE, so a failed invocation with empty
    # stdout read as "no changes" — a broken git meant a green light
    # (pair-rail round 5).
    #
    # Comparing the working-tree bytes to the committed blob cannot be spoofed
    # by an index flag: either the file IS what was reviewed, or it is not.
    show = _git(["show", "HEAD:%s" % rel.as_posix()])
    if show.returncode != 0:
        raise SpecError(
            "refusing `--write --spec %s`: git cannot produce the committed "
            "copy to compare against (%s). A spec whose reviewed version "
            "cannot be read has no provenance to check."
            % (rel, (show.stderr or b"").decode("utf-8", "replace").strip()[:120])
        )
    try:
        on_disk = resolved.read_bytes()
    except OSError as exc:
        raise SpecError("refusing `--write --spec %s`: %s" % (rel, exc))
    if on_disk != show.stdout:
        raise SpecError(
            "refusing `--write` with a MODIFIED spec: %s\n"
            "  The working-tree bytes differ from the committed ones. The "
            "committed copy was reviewed; the working-tree copy is the one "
            "that would drive the write.\n"
            "  (This compares BYTES, so `assume-unchanged` and `skip-worktree` "
            "cannot hide the difference.)\n"
            "  Commit the change first, or run `--check`." % rel
        )


def read_spec(root: Path, spec_path: Optional[str],
              for_write: bool = False) -> Dict[str, Any]:
    if spec_path:
        # `--spec` exists for BOOTSTRAP: deriving the artifact the first time,
        # when it cannot yet carry its own spec. Combining it with `--write`
        # lets an UNREVIEWED, out-of-tree document rewrite a canonical path
        # through a Bash call — and `check_canonical_edit` is registered for
        # Edit/Write/MultiEdit, not Bash, so nothing sees it (pair-rail round
        # 3, P1).
        #
        # The wider class is NOT this generator's to close: `generate-adr-index
        # --write` rewrites the canonical `.claude/adr/README.md` the same way,
        # and so does `build-plugin.py --write-manifests`. Curing one of three
        # would be theatre. What IS this wave's to close is the route it
        # introduced, so the spec must live inside the repository — where it is
        # tracked, reviewed, and covered by the canonical-edit ceremony like
        # any other file.
        resolved = Path(spec_path).resolve()
        if for_write:
            _require_reviewed_spec(root, resolved)
        data = load_json(Path(spec_path), "derivation spec")
        if isinstance(data, dict) and SPEC_KEY in data:
            data = data[SPEC_KEY]
        return data
    user = load_json(root / USER_REL, "user template")
    if not isinstance(user, dict) or SPEC_KEY not in user:
        raise InfraError(
            "%s carries no `%s` key. The spec lives inside the artifact it "
            "describes; restore the file from git, or bootstrap with --spec."
            % (USER_REL, SPEC_KEY)
        )
    return user[SPEC_KEY]


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate templates/settings/settings.user.json from settings.base.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="compare the on-disk template with the generated one (rc 1 on drift)")
    mode.add_argument("--write", action="store_true",
                      help="write the generated template to disk")
    mode.add_argument("--json", action="store_true",
                      help="print the generated template on stdout")
    parser.add_argument("--repo-root", default=None,
                        help="repository root (default: git rev-parse --show-toplevel)")
    parser.add_argument("--spec", default=None,
                        help="read the derivation from this file instead of the template")
    args = parser.parse_args(argv)

    if not (args.check or args.write or args.json):
        args.check = True

    try:
        root = repo_root(args.repo_root)
        base = load_json(root / BASE_REL, "base template")
        spec = read_spec(root, args.spec, for_write=bool(args.write))
    except InfraError as exc:
        sys.stderr.write("gen-settings-user-template: INFRA: %s\n" % exc)
        return RC_INFRA
    except SpecError as exc:
        # The `--write` confinement refusal is a POLICY answer, not a broken
        # environment: rc 1 (the caller asked for something the contract
        # forbids), never rc 2 (pair-rail round 3, P1).
        sys.stderr.write("gen-settings-user-template: SPEC: %s\n" % exc)
        return RC_DRIFT

    try:
        validate_spec(spec, base)
        generated = render(generate(base, spec))
    except SpecError as exc:
        sys.stderr.write(
            "gen-settings-user-template: SPEC: %s\n"
            "  the derivation spec lives in the `%s` key of %s\n"
            % (exc, SPEC_KEY, USER_REL)
        )
        return RC_DRIFT

    if args.json:
        sys.stdout.write(generated)
        return RC_OK

    target = root / USER_REL
    if args.write:
        try:
            target.write_text(generated, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write("gen-settings-user-template: INFRA: cannot write %s: %s\n"
                             % (target, exc))
            return RC_INFRA
        sys.stdout.write("gen-settings-user-template: wrote %s\n" % USER_REL)
        return RC_OK

    try:
        on_disk = target.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write("gen-settings-user-template: INFRA: cannot read %s: %s\n"
                         % (target, exc))
        return RC_INFRA
    except UnicodeDecodeError as exc:
        # Under `--check --spec`, `read_spec()` never parses the TARGET, so this
        # is its first access: invalid UTF-8 escaped as an uncaught traceback
        # (pair-rail round 7).
        sys.stderr.write("gen-settings-user-template: INFRA: %s is not valid "
                         "UTF-8: %s\n" % (target, exc))
        return RC_INFRA
    # An unparseable target is INFRA, not drift. Reporting "it differs from the
    # derivation" about a file that is not JSON at all names the wrong problem
    # and sends the reader to `--write` instead of to the corruption.
    try:
        json.loads(on_disk)
    except ValueError as exc:
        sys.stderr.write("gen-settings-user-template: INFRA: %s is not "
                         "parseable JSON: %s\n" % (target, exc))
        return RC_INFRA
    if on_disk == generated:
        sys.stdout.write("gen-settings-user-template: OK (%s matches the derivation)\n" % USER_REL)
        return RC_OK

    sys.stderr.write(
        "gen-settings-user-template: DRIFT — %s does not match the derivation "
        "declared in its own `%s` key.\n"
        "Remediation: python3 .claude/scripts/gen-settings-user-template.py --write\n\n"
        % (USER_REL, SPEC_KEY)
    )
    diff = difflib.unified_diff(
        on_disk.splitlines(keepends=True),
        generated.splitlines(keepends=True),
        fromfile="%s (on disk)" % USER_REL,
        tofile="%s (generated)" % USER_REL,
    )
    sys.stderr.writelines(diff)
    return RC_DRIFT


if __name__ == "__main__":
    sys.exit(main())
