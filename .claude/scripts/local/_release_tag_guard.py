#!/usr/bin/env python3
# ============================================================================
# _release_tag_guard.py — the two fail-closed asserts `tag()` runs before it
# asks the Owner's key to sign anything.
#
# WHY THIS EXISTS (v1.3.0-rc.1 re-pass, F2 + the F1/F2 composite risk):
#
#   (a) ANCESTRY. Nothing verified that the commit being tagged is on main.
#       `bump` could create a local commit AFTER the preflight proved CI green
#       for a different SHA, and `tag()` would sign that never-tested tree.
#       Two DISTINCT failures, never merged into one message: "could not talk
#       to origin" (network/offline — has a named escape hatch) and "HEAD is
#       not an ancestor of origin/main" (a real governance stop). The fetch and
#       the merge-base are SEPARATE statements: a failed fetch followed by a
#       merge-base against a stale ref is a FALSE APPROVAL.
#
#   (b) RESTRICTED DELTA. The invariant is "nothing landed after what the
#       re-pass reviewed, other than the verdict itself". The anchor is the
#       REVIEWED PARENT recorded in the signed verdict — one rule for RC and
#       GA. Anchoring on "the last RC" is wrong in both directions: for the GA
#       it coincides by accident, and for an rc.2 it would reject the very
#       W0/W1 fixes the re-pass just reviewed.
#
#       The allowlist is TAG-SPECIFIC and CLOSED:
#         * never the wildcard `pair-rail-verdict-*.md` — that would let a
#           historical verdict or the template be touched and still pass;
#         * never `repass-<N>/**` — any file dropped into that directory after
#           the review would pass the guard, and the pair-rail step-15 replay
#           does not cover plan artifacts;
#         * so the set closes by NAME (exact paths, set equality against the
#           re-pass MANIFEST) *and* by CONTENT (the verdict pins the sha256 of
#           MANIFEST.sha256, and the manifest itself is verified with
#           `shasum -a 256 -c`);
#         * and a plan path OUTSIDE the manifest directory — where no sha256
#           pins content — is admitted ONLY as `verdict-fields-<TAG>.md` with
#           the literal target tag, at its ONE canonical path (directly in
#           the plan directory containing the manifest dir): the plan file
#           itself, immutable repass history, another tag's verdict-fields,
#           and same-basename look-alikes in any other directory all close by
#           name alone and would carry a post-review edit onto the tag;
#         * the reviewed parent itself must be an ANCESTOR of HEAD —
#           `cat-file -e` proves existence, not lineage, and a fabricated
#           `commit-tree` anchor makes the whole delta trivially clean.
#
# THE LOCAL ASSERT IS NOT ENOUGH. A tag signed by hand skips this driver
# entirely, and the pair-rail step 15 recomputes inputs_hash only over the
# manifest — which deliberately EXCLUDES the bump surfaces. The same assert
# therefore goes server-side into `.github/workflows/release.yml` in PLAN-166
# W1 (release.yml is canonical; it is changed under the GPG ceremony, not
# here). Keep the two implementations in sync: this file is the reference.
#
# Exit codes are distinct so the failure MODE is testable, not just the
# failure:
#   2 usage   3 fetch failed   4 not-ancestor   5 remote ref unusable
#   6 delta outside allowlist  7 manifest sha pin mismatch
#   8 manifest content mismatch (shasum -c)  9 manifest/allowlist set mismatch
#  10 verdict unusable (missing file/field, wildcard, wrong tag, bad parent)
#  11 the assert would be VACUOUS (the verdict is not inside the delta it
#     anchors — e.g. parent_sha == HEAD, which makes the verdict review itself)
#  12 parent_sha is not an ancestor of HEAD (a fabricated/orphan anchor:
#     `cat-file -e` proves existence, not lineage — a `commit-tree` object
#     carrying HEAD's own tree makes diff(parent..HEAD) contain only the
#     verdict while unreviewed work sits on main)
#  13 the verdict DECISION does not authorize a release (NO-GO, absent,
#     empty, or an unknown token), OR the block spells a top-level key in a
#     form this reader and the step-15 validator resolve differently.
#     PLAN-177 W0.1 / P1-4: this guard read the tag, the anchor, the
#     allowlist and the manifest of a verdict but never its DECISION, so a
#     cross-model NO-GO still cut a tag. PLAN-177 t2 / P1-a: it then read
#     the DECISION with a grammar the other rail did not share, so
#     `verdict : NO-GO` + `verdict: GO` cut a tag on a NO-GO.
# ============================================================================
"""Ancestry + restricted-delta asserts for the release tag phase."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

E_USAGE = 2
E_FETCH = 3
E_NOT_ANCESTOR = 4
E_REMOTE_REF = 5
E_DELTA = 6
E_MANIFEST_PIN = 7
E_MANIFEST_CONTENT = 8
E_MANIFEST_SET = 9
E_VERDICT = 10
E_VACUOUS = 11
E_PARENT_NOT_ANCESTOR = 12
E_DECISION = 13

# PLAN-177 W0.1 (P1-4). Spelled out here rather than imported from
# .github/scripts/validate-pair-rail-verdict.py: the two rails are separate
# processes on separate machines and neither may become a dependency of the
# other. The set itself comes from
# .claude/governance/pair-rail-verdict-template.md. EXACT equality, no case
# folding and no prefix/substring rule -- NO-GO contains GO.
ACCEPTED_DECISIONS = ("GO", "GO-WITH-CONDITIONS")

HEX40 = re.compile(r"\A[0-9a-f]{40}\Z")

# t9 P1 (byte-for-byte twin of the step-15 validator): ONE strict
# extractor for the signed yaml block.
#   * the artifact must contain EXACTLY ONE occurrence of the literal
#     three-backtick yaml opener anywhere — a second occurrence (even
#     quoted inside a four-backtick block) makes the authoritative block
#     ambiguous, so the artifact is rejected fail-closed;
#   * the opener must sit at line start, column 0, closed by a
#     line-start fence — an unanchored search let a quoted GO envelope
#     inside a four-backtick block shadow the real NO-GO one;
#   * the body must be free of every line separator except LF and every
#     control char except TAB: str.splitlines() also splits on
#     U+000B/000C/001C-001E/0085/2028/2029, so a value glued to
#     <U+000B>#NO-GO parsed as the exact token GO on both rails.
# Returns the block body, or None when the artifact is rejected.
_FORBIDDEN_CTRL_RE = re.compile(
    "[\u0000-\u0008\u000b-\u001f\u007f\u0085\u2028\u2029]"
)


def _extract_single_yaml_block(text):
    if text.count("```yaml") != 1:
        return None
    # t12 P1: the FIRST fence of the document must BE the canonical
    # yaml opener — a complete envelope quoted inside a four-backtick
    # block as the document's ONLY ```yaml occurrence passed the
    # count==1 gate and became authoritative while the real decision
    # sat in prose. Any fence-looking line BEFORE the opener rejects.
    _first_fence = re.search(r"(?m)^`{3,}", text)
    if _first_fence is not None and not text[
        _first_fence.start():
    ].startswith("```yaml"):
        return None
    # t10 P1: the CLOSER must be canonical too — a bare ^``` matched
    # ANY line starting with three backticks, so ```not-a-closer
    # closed the body early and hid a later NO-GO.
    m = re.search(
        r"(?m)^```yaml[ \t]*\n(.*?)^```[ \t]*(?:\n|\Z)",
        text,
        re.DOTALL,
    )
    if not m:
        return None
    body = m.group(1)
    if _FORBIDDEN_CTRL_RE.search(body):
        return None
    return body

HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
GLOB_CHARS = "*?["
VERDICT_PREFIX = ".claude/governance/pair-rail-verdict-"
# The allowlist is EXHAUSTIVE, not merely closed: the verdict for this tag plus
# plan-side evidence (the `verdict-fields-<TAG>` pair and the re-pass artifact
# directory both live under `.claude/plans/`). Anything else — a version site, a
# workflow, any code path — would re-open the very hole the delta assert exists
# to close: a post-review bump commit riding in on the tag.
EVIDENCE_PREFIX = ".claude/plans/"


def _fail(code: int, msg: str) -> int:
    # Flush the ok-lines first: an operator reading a release failure must see
    # WHICH checks passed before the one that stopped it, in order.
    sys.stdout.flush()
    print("FAIL: %s" % msg, file=sys.stderr)
    sys.stderr.flush()
    return code


def _git(repo: str, *args: str) -> Tuple[int, str, str]:
    proc = subprocess.run(
        ["git"] + list(args),
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# (a) ancestry
# ---------------------------------------------------------------------------
def ancestry(repo: str, remote: str, branch: str, offline_ack: bool) -> int:
    ref = "%s/%s" % (remote, branch)
    if offline_ack:
        print(
            "  --   ancestry: --offline-ack given, NOT fetching; the "
            "merge-base below is judged against a possibly STALE %s" % ref
        )
    else:
        rc, _out, err = _git(repo, "fetch", "--quiet", remote, branch)
        # NEVER `;` between the fetch and the merge-base: a failed fetch plus a
        # stale ref reads as approval.
        if rc != 0:
            return _fail(
                E_FETCH,
                "could not talk to origin: `git fetch %s %s` exited %d.\n"
                "      This is NOT a verdict on the commit — the check did not "
                "run.\n"
                "      Fix the network/remote and re-run, or, if you are "
                "deliberately\n"
                "      offline and accept judging against the last-known ref, "
                "re-run\n"
                "      with --offline-ack (it is recorded in the output).\n"
                "      git said: %s" % (remote, branch, rc, err.strip()),
            )
        print("  ok   fetched %s" % ref)

    rc, out, err = _git(repo, "rev-parse", "--verify", "--quiet", ref)
    if rc != 0 or not out.strip():
        return _fail(
            E_REMOTE_REF,
            "no usable ref %s in this repo — cannot judge ancestry "
            "(git said: %s)" % (ref, err.strip()),
        )
    remote_sha = out.strip()

    rc, _out, err = _git(repo, "merge-base", "--is-ancestor", "HEAD", ref)
    if rc == 0:
        print("  ok   HEAD is an ancestor of %s (%s)" % (ref, remote_sha[:12]))
        return 0
    if rc == 1:
        return _fail(
            E_NOT_ANCESTOR,
            "HEAD is not an ancestor of %s — push main and re-run the "
            "preflight.\n"
            "      A tag on an unpushed commit points at a tree CI never "
            "saw; the\n"
            "      preflight's green verdict was about a different SHA."
            % ref,
        )
    return _fail(
        E_REMOTE_REF,
        "`git merge-base --is-ancestor HEAD %s` exited %d (neither yes nor "
        "no) — refusing to guess (git said: %s)" % (ref, rc, err.strip()),
    )


# ---------------------------------------------------------------------------
# (b) restricted delta
# ---------------------------------------------------------------------------
def _parse_verdict(text: str) -> Dict[str, object]:
    """Minimal, stdlib-only reader for the verdict's fenced YAML block.

    Deliberately NOT a YAML parser: it accepts `key: value` and a single level
    of `  - item` list entries, and ignores everything else. Anything it cannot
    read is absent, and every consumer below treats absent as fail-closed.

    Parity with the step-15 reader (`.github/scripts/
    validate-pair-rail-verdict.py`, parse_verdict_file), stated at its REAL
    scope: block selection (the regex below is the validator's own — the
    first ```yaml fence, not the first fence of any language) and inline
    comment stripping MATCH; list parsing (`- item`) exists ONLY here —
    parse_verdict_file reads key:value and sub-dicts and would drop
    `delta_allowlist` silently. The W1 server-side port must therefore extend
    ONE shared reader (this file is the declared reference), never grow a
    third parser of the same signed file.
    """
    fields: Dict[str, object] = {}
    _body = _extract_single_yaml_block(text)
    if _body is None:
        # No/ambiguous/forbidden-bytes block -> no fields -> every
        # consumer below fails closed.
        return fields
    cur_list: Optional[str] = None
    for raw in _body.split("\n"):
        line = _strip_yaml_comment(raw)
        if not line.strip():
            continue
        if line.startswith(("  - ", "- ")) and cur_list:
            item = line.split("-", 1)[1].strip()
            if item:
                fields[cur_list].append(item)  # type: ignore[union-attr]
            continue
        # [ \t]* not \s* (t5 P1): Python \s is Unicode-aware and would
        # swallow a NBSP that must stay attached to the VALUE.
        m = re.match(r"\A([A-Za-z0-9_]+):(?:[ \t]+(.*))?\Z", line)
        if not m:
            continue
        key, val = m.group(1), (m.group(2) or "").strip(" \t")
        if val == "":
            fields[key] = []
            cur_list = key
        else:
            fields[key] = val
            cur_list = None
    return fields


# PLAN-177 t2 (re-pass rc.4 P1-a). The CANONICAL top-level declaration.
# The two readers of this signed file disagreed about what a key IS: the
# step-15 validator strips the key (`line.partition(":")[0].strip()`), so it
# reads `verdict : NO-GO` as a declaration of `verdict`; the regexes in THIS
# file demand the colon immediately after the name, so they skipped the line.
# The valid-YAML pair
#
#     verdict : NO-GO
#     verdict: GO
#
# was therefore two declarations there (refused) and ONE here, parsed as GO —
# and this is the rail that enforces in every mode, so the tag was authorised.
#
# ONE semantics for both rails: NON-CANONICAL top-level syntax is REJECTED,
# fail-closed. Trimming the key in both readers would also close the
# divergence, but it widens the grammar of a SIGNED artifact to spellings no
# author writes and no template emits; refusing the shape is the smaller
# surface and is the only behaviour that cannot silently prefer a value.
# A top-level line is canonical iff it is `name:` with no whitespace before
# the colon; list items are legal ONLY indented under an active bare
# key (t8 P2: a root `- item` is rejected — the old comment said
# otherwise and misled operators).
def _strip_yaml_comment(raw):
    """YAML comment rule (re-pass rc.4 t3 P1): `#` starts a comment ONLY at
    line start or when PRECEDED by whitespace — `verdict: GO#NO-GO` is the
    single unknown VALUE `GO#NO-GO`, never `GO` plus a comment. Byte-for-
    byte twin of `_strip_comment` in validate-pair-rail-verdict.py.
    """
    # ASCII-only trims (re-pass rc.4 t5 P1): Unicode-aware strip()/rstrip()
    # silently converted `GO<U+00A0>` into the authorizing token `GO`.
    if raw.lstrip(" \t").startswith("#"):
        return ""
    i = 0
    while True:
        j = raw.find("#", i)
        if j == -1:
            return raw.rstrip(" \t")
        if j > 0 and raw[j - 1] in (" ", "\t"):
            return raw[:j].rstrip(" \t")
        i = j + 1


_CANONICAL_TOP_LEVEL_KEY_RE = re.compile(r"\A[A-Za-z0-9_]+:(?:[ \t]|\Z)")  # t5 P1: separator required — `verdict:GO` is NOT a YAML mapping


def _noncanonical_top_level_lines(text: str) -> List[str]:
    """Top-level lines of the yaml block that are not canonical declarations.

    Byte-for-byte twin of `noncanonical_top_level_lines` in
    `.github/scripts/validate-pair-rail-verdict.py` (separate processes on
    separate machines; neither may import the other — keep them identical).
    Empty list == the block speaks the grammar both readers assume.
    """
    body = _extract_single_yaml_block(text)
    if body is None:
        return ["<yaml block rejected: ambiguous fence, bad opener, or "
                "forbidden control/separator bytes>"]
    bad: List[str] = []
    # Parent state closes the line whitelist (re-pass rc.4 t7 P1): an
    # indented line is legitimate ONLY under an ACTIVE bare `key:` parent.
    # Both None (before any key) and "scalar" reject — an orphan-indented
    # FIRST line (`  verdict: NO-GO` then `verdict: GO`) previously slipped
    # through the prev_scalar_decl=False initial state and resolved as GO,
    # and a root-level `- item` is malformed for this signed format (its
    # only lists are INDENTED under a bare key) yet was accepted outright.
    # After a SCALAR `key: value`, an indented non-comment line is a YAML
    # CONTINUATION that changes the scalar's value (`verdict: GO` +
    # `  NO-GO` == "GO NO-GO") — reject fail-closed (re-pass rc.4 t2 P1).
    # t8 P1: ASCII-only trims in the SHAPE classifier too — a Unicode-aware
    # strip() treats a lone U+00A0 as a blank line and a U+00A0 VALUE as a
    # bare parent (`padding: <NBSP>` + orphan-indented `verdict:` line),
    # reopening the orphan-indentation class through the whitespace side.
    parent = None  # None | "scalar" | "bare"
    for raw in body.split("\n"):
        line = _strip_yaml_comment(raw)
        if not line.strip(" \t"):
            continue
        if line[0] in (" ", "\t"):
            if parent != "bare":
                bad.append(line)
            continue
        if _CANONICAL_TOP_LEVEL_KEY_RE.match(line):
            _key, _, _val = line.partition(":")
            parent = "scalar" if _val.strip(" \t") else "bare"
            continue
        bad.append(line)
        parent = None
    return bad


def _count_top_level_key(text: str, key: str) -> int:
    """How many times `key:` is declared at the top level of the block.

    PLAN-177 W0.1 / CF-2. _parse_verdict above is LAST-WINS, and so is the
    step-15 reader: a second `verdict:` silently overrides the first, so
    NO-GO followed by GO parses as GO. delta() requires exactly one. Same
    block selection and same comment rule as the reader, or the count
    would be about a different text than the parse.

    Only meaningful once `_noncanonical_top_level_lines` is empty: this
    counter does NOT strip the key and the step-15 twin does, so on a
    non-canonical block the two counts differ. delta() checks the shape
    first.
    """
    _body = _extract_single_yaml_block(text)
    if _body is None:
        return 0
    seen = 0
    for raw in _body.split("\n"):
        line = _strip_yaml_comment(raw)
        if not line.strip() or line[0] in (" ", "\t"):
            continue
        m = re.match(r"\A([A-Za-z0-9_]+):", line)
        if m and m.group(1) == key:
            seen += 1
    return seen


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_manifest(path: str) -> List[Tuple[str, str]]:
    """`shasum -a 256` format: '<sha>  <name>' — returns [(sha, name)]."""
    entries: List[Tuple[str, str]] = []
    # t10 P2: newline="" keeps CR bytes visible to the grammar.
    with open(path, encoding="utf-8", newline="") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            m = re.match(r"\A([0-9a-f]{64}) [ *](.+)\Z", line)
            if not m:
                raise ValueError("unparsable manifest line: %r" % line)
            entries.append((m.group(1), m.group(2)))
    return entries


def _verify_manifest_content(manifest: str) -> Tuple[bool, str]:
    """Run `shasum -a 256 -c`; fall back to hashlib when shasum is absent."""
    directory = os.path.dirname(manifest) or "."
    name = os.path.basename(manifest)
    try:
        proc = subprocess.run(
            ["shasum", "-a", "256", "-c", name],
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        return proc.returncode == 0, proc.stdout.strip()
    except (OSError, FileNotFoundError):
        bad: List[str] = []
        for want, rel in _read_manifest(manifest):
            full = os.path.join(directory, rel)
            if not os.path.isfile(full) or _sha256(full) != want:
                bad.append(rel)
        if bad:
            return False, "hashlib fallback: mismatch/missing: %s" % ", ".join(bad)
        return True, "hashlib fallback: all entries match"


def delta(repo: str, tag: str, verdict_rel: Optional[str]) -> int:
    verdict_rel = verdict_rel or (VERDICT_PREFIX + tag + ".md")
    verdict_abs = os.path.join(repo, verdict_rel)
    if not os.path.isfile(verdict_abs):
        return _fail(
            E_VERDICT,
            "no signed verdict at %s — the re-pass verdict for THIS tag must "
            "be committed before the tag is cut (release.yml validates it per "
            "tag on the tagged tree)." % verdict_rel,
        )
    # t10 P2: newline="" keeps CR bytes visible to the grammar.
    with open(verdict_abs, encoding="utf-8", newline="") as fh:
        verdict_text = fh.read()
    # PLAN-177 t2 (P1-a): SHAPE BEFORE ANY FIELD. Both rails read this file;
    # they only agree on a canonical block. A non-canonical top-level line is
    # refused here rather than handed to two different grammars — E_DECISION
    # because the class this closes is the decision override (`verdict :
    # NO-GO` + `verdict: GO`), and because a refusal that names the decision
    # rail is the one an operator can act on.
    noncanonical = _noncanonical_top_level_lines(verdict_text)
    if noncanonical:
        return _fail(
            E_DECISION,
            "verdict %s: non-canonical top-level key syntax %r -- a "
            "top-level line must be\n"
            "      `name:` with no whitespace before the colon (or a `- ` "
            "list item only when INDENTED under a bare key, never at the "
            "root). The two release rails read this\n"
            "      file with different grammars, so `verdict : NO-GO` "
            "followed by `verdict: GO` counts as two\n"
            "      declarations server-side and one here; the shape is "
            "refused instead of guessed."
            % (verdict_rel, noncanonical),
        )
    fields = _parse_verdict(verdict_text)

    release_tag = fields.get("release_tag")
    if release_tag != tag:
        return _fail(
            E_VERDICT,
            "verdict %s declares release_tag=%r, target tag is %r — refusing "
            "to judge this tag against another tag's verdict."
            % (verdict_rel, release_tag, tag),
        )
    # PLAN-177 W0.1 (P1-4) -- the DECISION gate.
    #
    # CF-3 ASYMMETRY (stated in BOTH rails, where it can be acted on): the
    # server-side twin (.github/scripts/validate-pair-rail-verdict.py, step
    # 15) carries `continue-on-error` when CEO_PAIR_RAIL_VERDICT_OPTIONAL=1
    # (release.yml:689) -- there the decision check is defence in depth.
    # THIS is the rail that enforces in every mode: release.sh calls it with
    # `|| die`, and the release.yml step that calls it carries no escape
    # hatch. Neither may be dropped for the other.
    #
    # Fail-CLOSED on SHAPE as well as value (CF-1): _parse_verdict returns a
    # LIST for an empty `verdict:` line, so the type check precedes the
    # compare -- a malformed decision is a named refusal, never a crash.
    declared_decisions = _count_top_level_key(verdict_text, "verdict")
    if declared_decisions > 1:
        return _fail(
            E_DECISION,
            "verdict %s declares the decision %d times -- this reader "
            "is last-wins, so a duplicated\n"
            "      `verdict:` silently overrides the first; exactly one "
            "is required."
            % (verdict_rel, declared_decisions),
        )
    decision = fields.get("verdict")
    if decision is None:
        shown = "<absent>"
    elif not isinstance(decision, str):
        shown = "<non-string:%s>" % type(decision).__name__
    else:
        # ASCII-only trim (t5 P1) — twin of the server validator.
        shown = decision.strip(" \t")
    if shown not in ACCEPTED_DECISIONS:
        return _fail(
            E_DECISION,
            "verdict %s: decision '%s' not in {%s} -- a tag may only be "
            "cut on an authorizing decision.\n"
            "      Everything the checks below assert (anchor, closed "
            "allowlist, manifest content) is about WHICH TREE the\n"
            "      re-pass saw; this one is about what the re-pass SAID "
            "about it. A NO-GO over a perfect delta is still a NO-GO."
            % (verdict_rel, shown, ", ".join(ACCEPTED_DECISIONS)),
        )
    parent = fields.get("parent_sha")
    if not isinstance(parent, str) or not HEX40.match(parent):
        return _fail(
            E_VERDICT,
            "verdict %s has no usable 40-hex `parent_sha:` — that field IS "
            "the review anchor." % verdict_rel,
        )
    rc, _out, _err = _git(repo, "cat-file", "-e", parent + "^{commit}")
    if rc != 0:
        return _fail(
            E_VERDICT,
            "parent_sha %s from %s is not a commit in this repo."
            % (parent, verdict_rel),
        )
    # Existence is not lineage. A fabricated anchor (`git commit-tree` over
    # HEAD's own tree, parented anywhere, on no branch) passes `cat-file -e`
    # and makes diff(parent..HEAD) contain ONLY the verdict + evidence while
    # unreviewed work sits on main — every check below then passes and the
    # guard prints approval over a tree the re-pass never saw. The anchor has
    # to be a commit HEAD actually descends from. (The staged W1 server-side
    # port asserts the same against origin/main — keep the two in sync.)
    rc, _out, err = _git(repo, "merge-base", "--is-ancestor", parent, "HEAD")
    if rc == 1:
        return _fail(
            E_PARENT_NOT_ANCESTOR,
            "parent_sha %s from %s is not an ancestor of HEAD — the review "
            "anchor is not in\n"
            "      the history this tag would sign. `cat-file -e` proves the "
            "object exists, not\n"
            "      that main descends from it; a fabricated commit carrying "
            "HEAD's own tree\n"
            "      makes the delta below trivially clean while unreviewed "
            "work rides the tag."
            % (parent[:12], verdict_rel),
        )
    if rc != 0:
        return _fail(
            E_PARENT_NOT_ANCESTOR,
            "`git merge-base --is-ancestor %s HEAD` exited %d (neither yes "
            "nor no) — refusing to guess (git said: %s)"
            % (parent[:12], rc, err.strip()),
        )
    print("  ok   parent_sha %s is an ancestor of HEAD" % parent[:12])

    allow = fields.get("delta_allowlist")
    if not isinstance(allow, list) or not allow:
        return _fail(
            E_VERDICT,
            "verdict %s carries no `delta_allowlist:` entries — the closed "
            "set is what makes the delta assert meaningful." % verdict_rel,
        )
    for entry in allow:
        if any(ch in entry for ch in GLOB_CHARS):
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r contains a glob metacharacter. The "
                "set is CLOSED and literal: a pattern like "
                "`pair-rail-verdict-*.md` would let a historical verdict or "
                "the template be edited and still pass." % entry,
            )
        if entry.startswith("/") or ".." in entry.split("/"):
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r must be a repo-relative path with "
                "no `..` segment." % entry,
            )
        if entry.startswith(VERDICT_PREFIX) and entry != verdict_rel:
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r is another tag's verdict (or the "
                "template). Only %s may move for this tag."
                % (entry, verdict_rel),
            )
        if entry != verdict_rel and not entry.startswith(EVIDENCE_PREFIX):
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r is neither this tag's verdict nor "
                "plan-side evidence under %s\n"
                "      The allowlist is EXHAUSTIVE: the verdict, its "
                "verdict-fields, and the\n"
                "      re-pass artifacts — nothing else. Allowlisting a "
                "version site, a\n"
                "      workflow or any code path turns this assert into "
                "permission to land\n"
                "      unreviewed work on the tag, which is the hole it "
                "exists to close."
                % (entry, EVIDENCE_PREFIX),
            )
    allow_set: Set[str] = set(allow)
    if verdict_rel not in allow_set:
        return _fail(
            E_VERDICT,
            "the verdict itself (%s) is not in its own delta_allowlist — it "
            "has to be committed, so it has to be allowed." % verdict_rel,
        )

    manifest_rel = fields.get("delta_manifest")
    manifest_sha = fields.get("delta_manifest_sha256")
    if not isinstance(manifest_rel, str) or not manifest_rel:
        return _fail(
            E_VERDICT,
            "verdict %s carries no `delta_manifest:` — without it the "
            "re-pass artifacts close by NAME only, and any file dropped into "
            "the directory after the review would pass." % verdict_rel,
        )
    if not isinstance(manifest_sha, str) or not HEX64.match(manifest_sha):
        return _fail(
            E_VERDICT,
            "verdict %s has no usable 64-hex `delta_manifest_sha256:`."
            % verdict_rel,
        )
    if manifest_rel not in allow_set:
        return _fail(
            E_VERDICT,
            "delta_manifest %s is not in delta_allowlist." % manifest_rel,
        )

    # --- content pin: the manifest itself, then everything it lists ---
    manifest_abs = os.path.join(repo, manifest_rel)
    if not os.path.isfile(manifest_abs):
        return _fail(E_MANIFEST_PIN, "delta_manifest %s missing" % manifest_rel)
    actual = _sha256(manifest_abs)
    if actual != manifest_sha:
        return _fail(
            E_MANIFEST_PIN,
            "delta_manifest sha256 mismatch for %s\n"
            "      verdict pins %s\n"
            "      on disk      %s" % (manifest_rel, manifest_sha, actual),
        )
    print("  ok   %s matches the sha256 pinned in the verdict" % manifest_rel)

    try:
        entries = _read_manifest(manifest_abs)
    except (OSError, ValueError) as exc:
        return _fail(E_MANIFEST_CONTENT, "cannot read %s: %s" % (manifest_rel, exc))
    good, detail = _verify_manifest_content(manifest_abs)
    if not good:
        return _fail(
            E_MANIFEST_CONTENT,
            "re-pass artifacts do not match %s (shasum -c failed):\n      %s"
            % (manifest_rel, detail),
        )
    print("  ok   shasum -a 256 -c %s (%d entries)" % (manifest_rel, len(entries)))

    # --- plan-side entries OUTSIDE the manifest directory ---
    # Everything inside the manifest directory is content-pinned (sha256 of
    # the manifest in the signed verdict + shasum -c + name equality below).
    # An EVIDENCE_PREFIX entry outside it closes by NAME ONLY — the plan file
    # itself, immutable repass history, or ANOTHER tag's verdict-fields could
    # be allowlisted and a post-review edit would ride the tag. The one such
    # file the plan promises is the verdict-fields for THIS tag, at its ONE
    # canonical path: directly inside the plan directory that CONTAINS the
    # manifest dir. A basename-only rule would admit any number of
    # look-alikes anywhere under EVIDENCE_PREFIX (plans/archive/, a sibling
    # repass dir, ...), each an unpinned name-only pass-through. Mirror this
    # rule in the W1 server-side port.
    man_dir = os.path.dirname(manifest_rel)
    plan_dir = os.path.dirname(man_dir)
    vf_name = "verdict-fields-%s.md" % tag
    vf_expected = "%s/%s" % (plan_dir, vf_name) if plan_dir else vf_name
    for entry in sorted(allow_set):
        if entry == verdict_rel or entry == manifest_rel:
            continue
        if entry.startswith(man_dir + "/"):
            continue
        if entry != vf_expected:
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r is outside the manifest directory "
                "(%s/) and is not this\n"
                "      tag's verdict-fields at its canonical path (%s).\n"
                "      Outside the manifest nothing pins content — a "
                "post-review edit there\n"
                "      would ride the tag by NAME alone, and a basename "
                "match in any other\n"
                "      directory is a look-alike, not the plan's file. Move "
                "the file into the\n"
                "      re-pass manifest, or it must be exactly %s."
                % (entry, man_dir, vf_expected, vf_expected),
            )

    # --- set equality by NAME, both directions, inside the manifest dir ---
    listed = set(
        os.path.normpath(os.path.join(man_dir, name)).replace(os.sep, "/")
        for _sha, name in entries
    )
    listed.add(manifest_rel)
    allowed_in_dir = set(
        e for e in allow_set if man_dir and (e == manifest_rel or e.startswith(man_dir + "/"))
    )
    if allowed_in_dir != listed:
        extra = sorted(allowed_in_dir - listed)
        missing = sorted(listed - allowed_in_dir)
        return _fail(
            E_MANIFEST_SET,
            "re-pass artifact set is not closed under %s\n"
            "      allowlisted but not in the manifest: %s\n"
            "      in the manifest but not allowlisted: %s"
            % (manifest_rel, extra or "-", missing or "-"),
        )
    print("  ok   re-pass artifact set closes (name equality with the manifest)")

    # --- the delta itself ---
    # --no-renames on purpose: with rename detection a file moved OUT of the
    # allowlisted evidence directory is reported only under its destination
    # name, and the disappearance of the reviewed original goes unmentioned.
    # Literal paths on both sides or the set comparison is not a set comparison.
    rc, out, err = _git(repo, "diff", "--no-renames", "%s..HEAD" % parent, "--name-only")
    if rc != 0:
        return _fail(
            E_DELTA,
            "`git diff --no-renames %s..HEAD --name-only` failed: %s"
            % (parent, err.strip()),
        )
    changed = [line for line in out.splitlines() if line.strip()]
    outside = sorted(p for p in changed if p not in allow_set)
    if outside:
        return _fail(
            E_DELTA,
            "files changed after the reviewed parent %s that the verdict does "
            "NOT allow:\n%s\n"
            "      The invariant is: NOTHING landed after what the re-pass "
            "reviewed,\n"
            "      other than the verdict and its pinned evidence. Either "
            "re-run the\n"
            "      re-pass against this tree, or drop these commits."
            % (parent[:12], "\n".join("        - %s" % p for p in outside)),
        )

    # VACUITY. Everything above is satisfied trivially by an anchor that sits
    # AT (or after) the verdict: the delta is then empty or verdict-free and
    # "all files are inside the allowlist" proves nothing at all. The verdict
    # has to have LANDED after the tree it certifies.
    if verdict_rel not in changed:
        return _fail(
            E_VACUOUS,
            "the verdict %s is not part of the delta %s..HEAD — this assert "
            "would pass\n"
            "      VACUOUSLY. parent_sha has to be the commit the re-pass "
            "reviewed, with\n"
            "      the verdict landing after it; parent_sha == HEAD (or any "
            "anchor whose\n"
            "      tree already carried the verdict) is the v1.16.0 "
            "self-reference bug that\n"
            "      the parent_sha field was introduced to kill."
            % (verdict_rel, parent[:12]),
        )

    # State the inputs, not just the verdict: an operator reading a release log
    # has to be able to tell what this assert actually examined.
    print(
        "  ok   delta %s..HEAD is %d file(s), all inside the verdict's closed "
        "allowlist of %d (verdict present in the delta)"
        % (parent[:12], len(changed), len(allow_set))
    )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="_release_tag_guard.py")
    sub = parser.add_subparsers(dest="cmd")

    p_anc = sub.add_parser("ancestry", help="HEAD must be on origin/<branch>")
    p_anc.add_argument("--repo", default=".")
    p_anc.add_argument("--remote", default="origin")
    p_anc.add_argument("--branch", default="main")
    p_anc.add_argument(
        "--offline-ack",
        action="store_true",
        help="named escape hatch: skip the fetch and judge against the "
        "last-known remote ref (loudly announced)",
    )

    p_delta = sub.add_parser("delta", help="restricted delta vs the verdict")
    p_delta.add_argument("--repo", default=".")
    p_delta.add_argument("--tag", required=True)
    p_delta.add_argument("--verdict", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "ancestry":
        return ancestry(args.repo, args.remote, args.branch, args.offline_ack)
    if args.cmd == "delta":
        return delta(args.repo, args.tag, args.verdict)
    parser.print_usage(sys.stderr)
    return E_USAGE


if __name__ == "__main__":
    sys.exit(main())
