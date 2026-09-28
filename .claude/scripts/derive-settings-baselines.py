#!/usr/bin/env python3
"""derive-settings-baselines.py — derive the upgrade.sh T5.4 baselines from GA tags.

The settings-migration table in ``scripts/upgrade.sh`` (``_T54_BASELINES_JSON``)
carries, per LEAF key, the OLD baseline, the NEW one and the ``superseded``
values: every value a release SHIPPED that is neither. Those were hand-kept
literals; a missed ``superseded`` entry is silent (the install/upgrade parity
e2e compares settings keys, not bytes), and the adopters on that value are
then read as ADOPTER-CUSTOMIZED and never receive the new baseline.

This script derives the leaf part of the table from what was actually shipped:
``git show <tag>:templates/settings/settings.base.json`` for every GA tag
(``vX.Y.Z``; prereleases only with ``--include-prereleases``), plus the NEW
value from the working-tree template (``--new-from <ref>`` to override).

Per leaf key, over the GA tags in version order:
  old        = the value shipped by the earliest GA tag carrying the template
  new        = the value in the new source (the release being built)
  superseded = every other distinct shipped value, in first-shipped order
               (the key is emitted only when non-empty, as in the literal)

Absence is POLICY, not bytes — declared in ``_LEAVES``: an absent array leaf
contributes no value; an absent ``model`` stands for ``null`` (old installs
carry no top-level ``model``); an absent ``permissions.defaultMode`` stands
for ``"default"`` (the mode the pre-v1.2.0 templates ran under, which the
migration's OLD branch matches when spelled explicitly).

Modes:
  (default)          print the derived leaf block (the literal's own layout)
                     on stdout; provenance on stderr
  --check UPGRADE_SH compare with the literal embedded in UPGRADE_SH (parsed
                     statically, never executed); every difference is named

``registrations`` (feature-gated hook entries) are NOT template-shipped values
and are not derived; ``--check`` reports them as such and ignores them. A
literal KEY this script does not model fails CLOSED (exit 2): a leaf whose
old / superseded / new the deriver cannot compute must never read as a match.

Per leaf, only ``DERIVED_FIELDS`` (``old``, ``superseded``, ``new``) are what
tag history can prove, and they are the only fields ``--check`` compares —
fail-closed: a wrong or missing ``old``/``new``, a ``superseded`` value no tag
shipped or one it lacks is a named difference (exit 1), and a ``superseded``
that is not a non-empty array exits 2. EVERY other field of a leaf is a
POLICY attribute (a decision the migration reads, such as
``requires_member_of``, ``notice``, ``opt_in``, ``cost_note``,
``on_migrate_of``, ``on_migrate_note``, or one no release has invented yet):
``--check`` passes it through untouched and names it on stdout, never as an
error, and the rendered block never carries one. There is no allow-list of
policy names to keep in step with upgrade.sh — a new attribute cannot break
the check (the 2nd occurrence of that break is what removed the list).

Scope of the guarantee: ``--check`` verifies the TABLE. Whether the migration
code in upgrade.sh CONSULTS a derived ``superseded`` list for a key is a
property of that code, not of this table. The one link the script holds is
declared by hand: a scalar key that gains one exits 2 unless it is listed in
``SCALAR_SUPERSEDED_CONSUMERS`` (the list asserts the code, it does not read it;
see that tuple for the tree it describes).

Wiring: no ``.github/workflows/validate.yml`` step runs ``--check``: a CI
checkout is shallow and tagless, where the derivation cannot answer. The
release preflight DOES run it: ``release.sh preflight`` runs
``pytest .claude/scripts/tests/``, whose ``SupersededLiveRepoTest`` runs
``--check scripts/upgrade.sh`` against the live tags of the maintainer
checkout (the same tests skip, visibly, where no GA tag exists). Any patch
that touches ``templates/settings/settings.base.json`` or
``scripts/upgrade.sh`` still runs ``--check scripts/upgrade.sh`` in its land
battery, so a red surfaces at the land and not first at the release cut.

Exit codes: 0 derived / match; 1 --check mismatch; 2 input or infrastructure
failure (no git, no GA tags — e.g. a shallow clone —, a template that is not
JSON at a tag, an unparseable, ambiguous or concatenated literal, a variable
written anywhere else in the file, an unmodelled key, a scalar ``superseded``
with no declared consumer, a ``superseded`` that is not a non-empty array).

Tag order is SemVer precedence (prerelease identifiers numerically where
numeric: ``rc.2`` < ``rc.10``), never lexical.

Tag universe = the history of the NEW source (``HEAD`` for the worktree,
else the ``--new-from`` ref): a tag that is an ancestor of it is counted; a
tag outside that history and newer (SemVer) than every tag inside it is
excluded and named on stderr — it shipped after the release being built
(``--new-from v1.2.0`` reproduces the v1.2.0 literal; a maintenance build
behind a newer tag gets no ``superseded`` value from the future). A GA tag
outside that history that PRECEDES its newest tag (a release cut off a side
branch, which adopters may be on) is a shape this deriver does not model:
exit 2, named. A prerelease tag of that shape is kept (more values, never
fewer).

An ``OPTIONAL_LEAVES`` key is omitted from the derived table when no tag and
no NEW template carry it; a literal that still migrates such a key is a named
``--check`` difference (exit 1), never a match.

Maintainer-only. ``scripts/install.sh`` copies every ``.claude/scripts/*.py``
into an adopter repository, so this file reaches adopters; it answers only
in the framework checkout, where the GA tags carry the template (in an
adopter's own repository no tag carries it: exit 2).

Read-only. Stdlib only. Python >= 3.9.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404 — fixed git argv, no shell
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_REPO = Path(__file__).resolve().parents[2]
TEMPLATE_REL = "templates/settings/settings.base.json"
LITERAL_VAR = "_T54_BASELINES_JSON"
NOT_DERIVED_KEYS = ("registrations",)
#: The per-leaf fields tag history PROVES, and the only ones --check
#: compares. Every other field of a leaf is a POLICY attribute: passed
#: through, named on stdout, never an error, never rendered.
DERIVED_FIELDS = ("old", "superseded", "new")
#: SCALAR leaves whose upgrade.sh migration CONSULTS ``superseded``. It
#: describes the migration of ADR-149 Amendment 3 (PLAN-193 wave-opus55):
#: ONE generic branch walks every TOP-LEVEL table entry whose "new" is a
#: string, and it reads "superseded" for each (its runtime oracle, from
#: that wave on, is test_every_scalar_superseded_value_migrates in
#: test_upgrade_settings_migration.py). A DOTTED scalar
#: (permissions.defaultMode) has no superseded branch and is not listed.
#: On a tree before that wave (5c6ab5f6 and earlier) the migration reads
#: "superseded" only in its array loop, so this declaration is ahead of
#: that code — vacuous there only because no scalar gains a superseded list
#: on it (measured: --check on 5c6ab5f6 is a MATCH with no scalar list);
#: land this file after the wave. A scalar that gains a superseded list
#: while absent here is a named error (exit 2): the table would promise a
#: move the code never makes. Whoever adds a scalar consumer lists it here.
SCALAR_SUPERSEDED_CONSUMERS: Tuple[str, ...] = ("model", "effortLevel")
#: Leaves omitted from the table when NO tag shipped them and the NEW
#: template does not carry them either (all absent = no migration).
OPTIONAL_LEAVES: Tuple[str, ...] = ("effortLevel",)

_ABSENT = object()  # absence contributes no baseline value

#: (leaf key, kind, value that ABSENCE stands for). Order = the rendered
#: block's order, which is the literal's: the top-level leaves first, then the
#: dotted ones. An OPTIONAL_LEAVES leaf that no tag and no NEW template ships
#: is omitted, so its place changes nothing where it is absent.
_LEAVES: Tuple[Tuple[str, str, Any], ...] = (
    ("availableModels", "array", _ABSENT),
    ("fallbackModel", "array", _ABSENT),
    ("model", "scalar", None),
    ("effortLevel", "scalar", None),
    ("permissions.defaultMode", "scalar", "default"),
)

_GA_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_PRE_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-([0-9A-Za-z.\-]+)$")


class DeriveError(Exception):
    """Input/infrastructure failure — exit 2."""


def _git(repo: Path, *args: str) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(  # nosec B603 B607 — fixed git argv
            ["git", "-C", str(repo)] + list(args), capture_output=True, text=True,
            timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeriveError("git unavailable: {}".format(exc))
    return proc.returncode, proc.stdout, proc.stderr


def _pre_key(pre: str) -> Tuple[Tuple[int, int, str], ...]:
    """SemVer §11 prerelease precedence: numeric ids numerically, below alphanumerics."""
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split("."))


def _tag_key(tag: str) -> Optional[Tuple[int, int, int, int, Tuple[Tuple[int, int, str], ...]]]:
    m = _GA_TAG_RE.match(tag)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 1, ())
    m = _PRE_TAG_RE.match(tag)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, _pre_key(m.group(4)))
    return None


def list_tags(repo: Path, include_prereleases: bool) -> List[str]:
    rc, out, err = _git(repo, "tag", "-l")
    if rc != 0:
        raise DeriveError("git tag -l failed in {}: {}".format(repo, err.strip()[:200]))
    tags = [t.strip() for t in out.splitlines() if t.strip()]
    keep = [t for t in tags if _GA_TAG_RE.match(t) or (include_prereleases and _PRE_TAG_RE.match(t))]
    return sorted(keep, key=lambda t: _tag_key(t) or (0, 0, 0, 0, ()))


def _new_commit(repo: Path, new_from: str) -> str:
    ref = "HEAD" if new_from == "worktree" else new_from
    rc, out, err = _git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    if rc != 0 or not out.strip():
        raise DeriveError("{} does not name a commit in {} ({})".format(
            ref, repo, err.strip()[:200] or "rev-parse failed"))
    return out.strip()


def _is_ancestor(repo: Path, tag: str, commit: str) -> bool:
    rc, _out, err = _git(repo, "merge-base", "--is-ancestor", "refs/tags/" + tag, commit)
    if rc in (0, 1):
        return rc == 0
    raise DeriveError("git merge-base --is-ancestor {} failed: {}".format(tag, err.strip()[:200]))


def select_tags(repo: Path, new_from: str, notes: List[str]) -> List[str]:
    """Every GA and prerelease tag in the history of the NEW source, in
    version order (see the module docstring for the shapes outside it)."""
    commit = _new_commit(repo, new_from)
    tags = list_tags(repo, True)
    inside = {t for t in tags if _is_ancestor(repo, t, commit)}
    keys = [_tag_key(t) for t in inside]
    top = max(k for k in keys if k is not None) if keys else None
    kept: List[str] = []
    for tag in tags:
        if tag in inside:
            kept.append(tag)
            continue
        key = _tag_key(tag)
        if top is not None and key is not None and key < top:
            if _GA_TAG_RE.match(tag):
                raise DeriveError("GA tag {} is not in the history of the NEW source ({}) yet "
                                  "precedes its newest tag — a release cut off a side branch, "
                                  "which adopters may be on; this deriver does not model that "
                                  "shape".format(tag, "HEAD" if new_from == "worktree" else new_from))
            kept.append(tag)
            continue
        notes.append("{}: outside the history of the NEW source and newer than every tag in it "
                     "— excluded".format(tag))
    return kept


def read_template_at(repo: Path, ref: str) -> Optional[Dict[str, Any]]:
    """The template JSON at ``ref``; None when the path does not exist there."""
    rc, out, err = _git(repo, "ls-tree", "--name-only", ref, "--", TEMPLATE_REL)
    if rc != 0:
        raise DeriveError("git ls-tree {} failed: {}".format(ref, err.strip()[:200]))
    if not out.strip():
        return None
    rc, out, err = _git(repo, "show", "{}:{}".format(ref, TEMPLATE_REL))
    if rc != 0:
        raise DeriveError("git show {}:{} failed: {}".format(ref, TEMPLATE_REL, err.strip()[:200]))
    return _parse_template(out, "{}:{}".format(ref, TEMPLATE_REL))


def _parse_template(text: str, where: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise DeriveError("{} is not JSON: {}".format(where, exc))
    if not isinstance(data, dict):
        raise DeriveError("{} is not a JSON object".format(where))
    return data


def leaf_value(data: Dict[str, Any], key: str, absent_as: Any, where: str) -> Any:
    node: Any = data
    parts = key.split(".")
    for i, part in enumerate(parts):
        if not isinstance(node, dict):
            raise DeriveError("{}: {} is not an object".format(where, ".".join(parts[:i])))
        if part not in node:
            return absent_as
        node = node[part]
    return node


def _check_kind(value: Any, kind: str, key: str, where: str) -> None:
    if value is _ABSENT:
        return
    if kind == "array" and not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
        raise DeriveError("{}: {} is not an array of strings".format(where, key))
    if kind == "scalar" and not (value is None or isinstance(value, str)):
        raise DeriveError("{}: {} is not a string".format(where, key))


def _compact(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def load_shipped(repo: Path, include_prereleases: bool, notes: List[str],
                 universe: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
    """(tag, template) for every selected tag that carries the template, in version order."""
    shipped: List[Tuple[str, Dict[str, Any]]] = []
    for tag in [t for t in universe if _GA_TAG_RE.match(t) or include_prereleases]:
        data = read_template_at(repo, tag)
        if data is None:
            notes.append("{}: no {} (skipped)".format(tag, TEMPLATE_REL))
            continue
        shipped.append((tag, data))
    if not any(_GA_TAG_RE.match(t) for t, _ in shipped):
        raise DeriveError("no GA tag (vX.Y.Z) carrying {} is visible in {} — a shallow or "
                          "tagless clone? run: git fetch --tags --unshallow".format(TEMPLATE_REL, repo))
    return shipped


def load_new(repo: Path, new_from: str) -> Tuple[Dict[str, Any], str]:
    """The NEW template: the working tree (default) or the template at a ref."""
    if new_from == "worktree":
        path = repo / TEMPLATE_REL
        try:
            return _parse_template(path.read_text(encoding="utf-8"), str(path)), "worktree"
        except OSError as exc:
            raise DeriveError("cannot read {}: {}".format(path, exc))
    data = read_template_at(repo, new_from)
    if data is None:
        raise DeriveError("{} has no {}".format(new_from, TEMPLATE_REL))
    return data, new_from


def shipped_history(shipped: List[Tuple[str, Dict[str, Any]]], key: str, kind: str,
                    absent_as: Any) -> List[Tuple[Any, List[str]]]:
    """Distinct shipped values of ``key`` in first-shipped order, with their tags."""
    history: List[Tuple[Any, List[str]]] = []
    for tag, data in shipped:
        val = leaf_value(data, key, absent_as, tag)
        _check_kind(val, kind, key, tag)
        if val is _ABSENT:
            continue
        for seen_val, tags in history:
            if seen_val == val:
                tags.append(tag)
                break
        else:
            history.append((val, [tag]))
    return history


def derive_key(key: str, kind: str, history: List[Tuple[Any, List[str]]], new_val: Any,
               new_where: str, notes: List[str]) -> Dict[str, Any]:
    """old = first shipped; new = the new source; superseded = every other shipped value."""
    if new_val is _ABSENT:
        raise DeriveError("{}: {} is absent — the migration table cannot express a "
                          "removal".format(new_where, key))
    if not history:
        raise DeriveError("{} was never shipped by any tag — no OLD baseline".format(key))
    old_val = history[0][0]
    spec: Dict[str, Any] = {"old": old_val}
    sup = [v for v, _ in history[1:] if v != new_val]
    if sup:
        spec["superseded"] = sup
        if kind == "scalar" and key not in SCALAR_SUPERSEDED_CONSUMERS:
            raise DeriveError("scalar key {} gains a 'superseded' list {} but is not in "
                              "SCALAR_SUPERSEDED_CONSUMERS — that tuple declares which scalar "
                              "leaves upgrade.sh's migration consults 'superseded' for; if "
                              "upgrade.sh has such a consumer for this key, list the key there "
                              "(in the same patch), otherwise add the consumer first".format(
                                  key, json.dumps(sup)))
    spec["new"] = new_val
    for val, tags in history:
        role = "old" if val == old_val else ("new" if val == new_val else "superseded")
        notes.append("{} [{}] {} <- {}".format(key, role, _compact(val), ", ".join(tags)))
    notes.append("{} [new] {} <- {}".format(key, _compact(new_val), new_where))
    return spec


def derive(repo: Path, new_from: str, include_prereleases: bool) -> Tuple[Dict[str, Any], List[str]]:
    """Return (derived leaf table, provenance/notes lines)."""
    notes: List[str] = []
    universe = select_tags(repo, new_from, notes)
    shipped = load_shipped(repo, include_prereleases, notes, universe)
    new_data, new_where = load_new(repo, new_from)
    table: Dict[str, Any] = {}
    for key, kind, absent_as in _LEAVES:
        new_val = leaf_value(new_data, key, absent_as, new_where)
        _check_kind(new_val, kind, key, new_where)
        history = shipped_history(shipped, key, kind, absent_as)
        if (key in OPTIONAL_LEAVES and new_val == absent_as
                and all(v == absent_as for v, _ in history)):
            notes.append("{} never shipped and absent from NEW — omitted".format(key))
            continue
        table[key] = derive_key(key, kind, history, new_val, new_where, notes)
    return table, notes


def render_block(table: Dict[str, Any]) -> str:
    """The literal's own layout: one field per line, compact JSON values.

    Leaves only: the block carries the DERIVED_FIELDS and never a policy
    attribute a literal may hold, so on a tree whose literal carries one the
    rendered block is paste-ready for everything BUT those fields.
    """
    out = ["{"]
    keys = list(table.keys())
    for i, key in enumerate(keys):
        out.append("  {}: {{".format(json.dumps(key)))
        fields = list(table[key].items())
        for j, (field, value) in enumerate(fields):
            out.append("    {}: {}{}".format(json.dumps(field), json.dumps(value, separators=(",", ":")),
                                            "," if j < len(fields) - 1 else ""))
        out.append("  }}{}".format("," if i < len(keys) - 1 else ""))
    out.append("}")
    return "\n".join(out)


_FIELD_LINE_RE = re.compile(r'^    ("(?:[^"\\]|\\.)*")\s*:')


def leaf_lines_for_compare(lines: List[str]) -> List[str]:
    """Leaf-block lines as the paste-ready comparison reads them.

    A field whose name is not in ``DERIVED_FIELDS`` is a policy attribute
    and is dropped WHOLE: its field line (indented four spaces) and every
    continuation line of a value spread over several lines (anything deeper,
    up to the next field line or the next line indented two spaces or
    less). The rendered block never carries one, so on a tree whose literal
    holds a policy attribute the block is paste-ready for everything BUT
    those lines — whatever the attribute is called. A trailing comma is
    ignored on every line (dropping a field moves it). Derived values,
    their field order and leaf order still compare byte for byte.
    """
    out: List[str] = []
    dropping = False
    for line in lines:
        m = _FIELD_LINE_RE.match(line)
        if m is not None:
            try:
                name = json.loads(m.group(1))
            except ValueError:
                name = None
            dropping = name not in DERIVED_FIELDS
        elif re.match(r"^ {0,2}\S", line):
            dropping = False
        if dropping:
            continue
        out.append(line.rstrip().rstrip(","))
    return out


def policy_attributes(literal: Dict[str, Any]) -> List[str]:
    """``<leaf>.<field>`` for every non-derived field of every leaf, in the
    literal's order. Passed through by --check: named, never compared."""
    out: List[str] = []
    for key, spec in literal.items():
        if key in NOT_DERIVED_KEYS or not isinstance(spec, dict):
            continue
        out.extend("{}.{}".format(key, f) for f in spec if f not in DERIVED_FIELDS)
    return out


def _write_mentions(text: str) -> List[int]:
    """Offsets of every mention of the variable that is NOT a plain read.

    Classified by SHAPE, fail-closed: a mention on a ``#`` comment line is
    ignored; ``$NAME`` and ``${NAME…}`` are reads, except ``${NAME=…}`` and
    ``${NAME:=…}``, which assign; every other mention — ``NAME=``, an indented
    or ``local``/``declare``/``export``/``readonly`` assignment, ``NAME+=``,
    ``read NAME``, ``printf -v NAME``, ``unset NAME`` — counts as a write.
    """
    out: List[int] = []
    for m in re.finditer(r"(?<![A-Za-z0-9_]){}(?![A-Za-z0-9_])".format(re.escape(LITERAL_VAR)), text):
        pos = m.start()
        line_start = text.rfind("\n", 0, pos) + 1
        if text[line_start:pos].lstrip().startswith("#"):
            continue
        after = text[m.end():m.end() + 2]
        if text[max(0, pos - 1):pos] == "$":
            continue
        if text[max(0, pos - 2):pos] == "${" and not (after.startswith("=") or after == ":="):
            continue
        out.append(pos)
    return out


def extract_literal(upgrade_sh: Path) -> Dict[str, Any]:
    """Parse the ONE ``_T54_BASELINES_JSON='…'`` assignment statically."""
    try:
        text = upgrade_sh.read_text(encoding="utf-8")
    except OSError as exc:
        raise DeriveError("cannot read {}: {}".format(upgrade_sh, exc))
    starts = [m.start() for m in re.finditer(r"(?m)^{}=".format(re.escape(LITERAL_VAR)), text)]
    if len(starts) != 1:
        raise DeriveError("{}: expected exactly 1 assignment of {}, found {}".format(
            upgrade_sh, LITERAL_VAR, len(starts)))
    others = [pos for pos in _write_mentions(text) if pos != starts[0]]
    if others:
        raise DeriveError("{}: {} is also written at line(s) {} — the value bash ends up "
                          "with is not the parsed literal".format(
                              upgrade_sh, LITERAL_VAR,
                              ", ".join(str(text.count("\n", 0, p) + 1) for p in others)))
    m = re.compile(r"{}='([^']*)'".format(re.escape(LITERAL_VAR))).match(text, starts[0])
    if m is None:
        raise DeriveError("{}: {} is not a single-quoted literal".format(upgrade_sh, LITERAL_VAR))
    # The word must END at the closing quote: bash concatenates adjacent
    # quoted/unquoted text ('…''x', '…'"$X"), which would make the value
    # bash sees differ from the one parsed here.
    tail = text[m.end():m.end() + 1]
    if tail not in ("", "\n", " ", "\t", ";"):
        raise DeriveError("{}: {} literal is followed by {!r} — a concatenated word, not "
                          "one single-quoted literal".format(upgrade_sh, LITERAL_VAR, tail))
    try:
        data = json.loads(m.group(1))
    except ValueError as exc:
        raise DeriveError("{}: {} is not JSON: {}".format(upgrade_sh, LITERAL_VAR, exc))
    if not isinstance(data, dict):
        raise DeriveError("{}: {} is not a JSON object".format(upgrade_sh, LITERAL_VAR))
    return data


def _as_set(values: Any) -> List[str]:
    return sorted(json.dumps(v, separators=(",", ":")) for v in (values or []))


def compare(derived: Dict[str, Any], literal: Dict[str, Any]) -> List[str]:
    """Named differences between the derived table and the literal, over the
    DERIVED_FIELDS only; every other field of a leaf passes through (see
    ``policy_attributes``)."""
    unmodelled = [k for k in literal if k not in derived and k not in NOT_DERIVED_KEYS
                  and k not in OPTIONAL_LEAVES]
    if unmodelled:
        raise DeriveError("literal carries key(s) this deriver does not model: {} — extend "
                          "_LEAVES (or NOT_DERIVED_KEYS) before trusting --check".format(
                              ", ".join(sorted(unmodelled))))
    diffs: List[str] = []
    for key in OPTIONAL_LEAVES:
        if key in literal and key not in derived:
            # C-R1-03: an optional leaf the derivation omitted (no GA tag and
            # no NEW template ships it) must not read as a match when the
            # literal still migrates it.
            diffs.append("{}: the literal migrates it ({}) but no GA tag and no NEW template "
                         "ship it — the derived table omits it".format(
                             key, json.dumps(literal[key], separators=(",", ":"))))
    for key, spec in derived.items():
        lit = literal.get(key)
        if not isinstance(lit, dict):
            diffs.append("{}: absent from the literal (derived {})".format(key, json.dumps(spec)))
            continue
        if "superseded" in lit and not (isinstance(lit["superseded"], list) and lit["superseded"]):
            # null / {} / "" / 0 / [] would read as "no superseded" and match a
            # derived table without one — a shape the migration never emits.
            raise DeriveError("literal {}.superseded is not a non-empty JSON array: {}".format(
                key, json.dumps(lit["superseded"])))
        for field in ("old", "new"):
            if field not in lit or lit[field] != spec[field]:
                diffs.append("{}.{}: literal {} != derived {}".format(
                    key, field, json.dumps(lit.get(field, "<missing>")), json.dumps(spec[field])))
        want, have = _as_set(spec.get("superseded")), _as_set(lit.get("superseded"))
        for val in want:
            if val not in have:
                diffs.append("{}.superseded: literal LACKS shipped value {} — adopters on it would "
                             "be read as ADOPTER-CUSTOMIZED".format(key, val))
        for val in have:
            if val not in want:
                diffs.append("{}.superseded: literal declares {} which no derived tag shipped".format(key, val))
    return diffs


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Derive the upgrade.sh T5.4 settings baselines "
                                "from the GA tags' templates/settings/settings.base.json.")
    p.add_argument("--repo", default=str(DEFAULT_REPO))
    p.add_argument("--new-from", default="worktree",
                   help="'worktree' (default) or a git ref holding the NEW template")
    p.add_argument("--include-prereleases", action="store_true",
                   help="also treat vX.Y.Z-<pre> tags as shipped (adopters on an rc)")
    p.add_argument("--check", metavar="UPGRADE_SH",
                   help="compare with the _T54_BASELINES_JSON literal in this file")
    p.add_argument("--quiet", action="store_true", help="no provenance on stderr")
    args = p.parse_args(argv)
    repo = Path(args.repo).resolve()
    try:
        table, notes = derive(repo, args.new_from, args.include_prereleases)
        pre_only: List[str] = []
        if not args.include_prereleases:
            pre_only = _prerelease_only_notes(repo, table, select_tags(repo, args.new_from, []))
            notes.extend(pre_only)
        if not args.quiet:
            for line in notes:
                sys.stderr.write("[derive-settings-baselines] {}\n".format(line))
        if not args.check:
            sys.stdout.write(render_block(table) + "\n")
            return 0
        literal = extract_literal(Path(args.check))
        diffs = compare(table, literal)
        policy = policy_attributes(literal)
        # C-R2-03: under --check a prerelease-only value is a named MISMATCH on
        # stdout, never a stderr WARNING that --quiet would hide.
        diffs.extend("prerelease-only: {}".format(n) for n in pre_only)
    except DeriveError as exc:
        sys.stderr.write("[derive-settings-baselines] ERROR: {}\n".format(exc))
        return 2
    policy_line = "POLICY (passed through, not compared): {}\n".format(
        ", ".join(policy) if policy else "none")
    if diffs:
        sys.stdout.write("CHECK: MISMATCH ({} difference(s)) — derived block:\n".format(len(diffs)))
        for d in diffs:
            sys.stdout.write("  - {}\n".format(d))
        sys.stdout.write(policy_line)
        sys.stdout.write(render_block(table) + "\n")
        return 1
    sys.stdout.write("CHECK: MATCH ({} leaf keys; not derived: {})\n".format(
        len(table), ", ".join(NOT_DERIVED_KEYS)))
    sys.stdout.write(policy_line)
    return 0


def _prerelease_only_notes(repo: Path, table: Dict[str, Any],
                           universe: List[str]) -> List[str]:
    """Warn when a prerelease in the NEW source's tag universe shipped a
    value no GA tag and no NEW carries."""
    notes: List[str] = []
    for tag in [t for t in universe if not _GA_TAG_RE.match(t)]:
        data = read_template_at(repo, tag)
        if data is None:
            continue
        for key, kind, absent_as in _LEAVES:
            val = leaf_value(data, key, absent_as, tag)
            if val is _ABSENT:
                continue
            if key not in table:  # an OPTIONAL_LEAVES leaf omitted as all-absent
                if val != absent_as:
                    notes.append("WARNING: prerelease {} shipped {} = {} that no GA tag and "
                                 "no NEW carries".format(tag, key, json.dumps(val)))
                continue
            spec = table[key]
            known = [spec["old"], spec["new"]] + list(spec.get("superseded", []))
            if val not in known:
                notes.append("WARNING: prerelease {} shipped {} = {} that no GA tag carries — "
                             "adopters on it read as CUSTOMIZED unless --include-prereleases".format(
                                 tag, key, json.dumps(val, separators=(",", ":"))))
    return notes


if __name__ == "__main__":
    sys.exit(main())
