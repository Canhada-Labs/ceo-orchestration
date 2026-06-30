#!/usr/bin/env python3
"""check-adr-chain.py — validates ADR status-chain integrity.

PLAN-019 F-CHAOS-8. Parses every `.claude/adr/ADR-*.md`, extracts the
`Status:` field plus any `Superseded-By:` / `Supersedes:` references,
and exits non-zero if the chain is broken.

## Checks

1. Every ADR has a `Status:` field matching one of:
     - PROPOSED
     - ACCEPTED / ACCEPTED-*  (e.g. "ACCEPTED-as-RESERVED")
     - SUPERSEDED
     - REJECTED
     - DEPRECATED

2. Every SUPERSEDED ADR declares a concrete successor via either:
     - A `Superseded-By:` line pointing at another ADR-NNN identifier, OR
     - An inline "(SUPERSEDED — removed in ...)" note that identifies the
       commit/plan that retired it (acceptable for retired scaffolding).

3. If an ADR has a `Supersedes:` line, the pointed-to ADR must exist and
   must have `Status: SUPERSEDED`.

4. ADR-NNN filename must be zero-padded 3 digits.

5. Every `ADR-NNN-AMEND-K-*.md` file must declare an `amends:` target that
   exists in the corpus.  Additionally the amendment predecessor
   (`ADR-NNN-AMEND-(K-1)` for K>1, or the base `ADR-NNN` for K=1) must
   also be present, unless the gap is explicitly listed in the README's
   "Known amendment chain gaps" section.

Exit codes:
    0  chain valid (or only advisory warnings for permitted patterns)
    1  broken chain — one or more errors

Usage:
    python3 .claude/scripts/check-adr-chain.py [--adr-dir PATH]

stdlib only; Python 3.9 compatible.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ADR_DIR = REPO_ROOT / ".claude" / "adr"

ADR_FILE_RE = re.compile(
    # Standard: ADR-NNN-kebab-slug.md (NNN = exactly 3 digits)
    # AMEND variant: ADR-NNN-AMEND-N-kebab-slug.md  (AMEND-N is uppercase, N = 1+)
    # 049a variant: ADR-049a-kebab-slug.md  (legacy 'a' suffix for worktree split)
    # Slug chars: lowercase kebab (normal), uppercase (AMEND/CLASS), underscore (SHA_EXISTS)
    r"^ADR-(\d{3}[a-z]?)-[A-Za-z0-9_]+(?:[-.][A-Za-z0-9_]+)*\.md$"
)
ADR_ID_RE = re.compile(r"ADR-(\d{3})")

# Status field.  Accepts three formats in priority order:
#
#   1. Inline colon:  `**Status:** VALUE` / `## Status: VALUE` / `status: VALUE`
#      (covers YAML frontmatter, bold-inline, and colon-heading forms)
#   2. Heading-then-value:  `## Status\n\nVALUE` or `## Status\nVALUE`
#      (the block used by ADR-082 through ADR-097 and some later ADRs)
#
# Both patterns capture a named group `status` with the leading status word.
_STATUS_INLINE_RE = re.compile(
    r"(?im)^[#\s]*\**\s*status\s*\**\s*:\s*\**\s*(?P<status>[A-Z][A-Z0-9\- ]*)"
)
_STATUS_HEADING_RE = re.compile(
    r"(?im)^##\s+Status\s*\n+(?P<status>[A-Z][A-Z0-9\-]+)"
)


def _extract_status(text: str) -> str:
    """Return the leading status token from `text`, preferring the inline
    colon form (YAML/bold) but falling back to the heading-then-value form."""
    m = _STATUS_INLINE_RE.search(text)
    if m:
        return m.group("status").strip().upper()
    m = _STATUS_HEADING_RE.search(text)
    if m:
        return m.group("status").strip().upper()
    return ""


# Keep a single reference so callers of parse_adr can still access the
# primary regex (used to locate the status *position* for inline-SUPERSEDED
# scanning).  We use the inline form as the primary for that purpose.
STATUS_RE = _STATUS_INLINE_RE

SUPERSEDED_BY_RE = re.compile(
    r"(?im)^[#\s]*\**\s*superseded[- ]by\s*\**\s*:\s*(?P<ref>.+)$"
)
# SUPERSEDES_RE: matches a `supersedes:` key/line and captures the reference
# value on the SAME line only (no cross-line capture).  This prevents a YAML
# block-sequence like:
#   supersedes:
#     - rename_source: ADR-111 (context: renamed via ADR-117 doctrine)
# from incorrectly extracting ADR-117 as a superseded target.
# The regex uses [^\n]+ (any char except newline) so it never crosses lines,
# even though \s would match \n by default.
SUPERSEDES_RE = re.compile(
    r"(?im)^[ \t#]*\**[ \t]*supersedes(?:[ \t]*\([^)\n]*\))?[ \t]*\**[ \t]*:[ \t]*(?P<ref>[^\n]+)"
)

# YAML frontmatter extractor — used to read `supersedes:` block sequences
# from ADRs that use YAML-list syntax instead of an inline colon value.
# Pattern: isolate the YAML block between leading `---` fence pairs.
_FM_FENCE_RE = re.compile(r"^---[ \t]*\n(?P<fm>.*?)\n---[ \t]*\n", re.DOTALL)
# Match a `supersedes:` YAML key whose value is a block sequence (no same-line value).
_FM_SUPERSEDES_BLOCK_RE = re.compile(
    r"(?im)^supersedes\s*:\s*\n(?P<items>(?:[ \t]*-[ \t].+\n?)+)"
)
# Match a single list item under `supersedes:`, capturing any ADR-NNN token.
_FM_LIST_ITEM_RE = re.compile(r"^\s*-\s+(?P<content>.+)", re.MULTILINE)

# ---------------------------------------------------------------------------
# amends: field parsing
# ---------------------------------------------------------------------------
# Matches various forms of the `amends:` declaration in AMEND files:
#   YAML scalar:     amends: ADR-042
#   Bold markdown:   **Amends:** ADR-019        (colon is INSIDE the closing **)
#   YAML inline list: amends: [ADR-118]
# The bold-markdown form `**Amends:**` has the structure:
#   ** + Amends: + ** so the regex allows up to 2 asterisks around the key
#   AND optionally after the colon.
_AMENDS_INLINE_RE = re.compile(
    r"(?im)^\*{0,2}(?:amends)\*{0,2}:?\*{0,2}\s*\[?(?P<ref>[A-Za-z0-9][^\]\n]*)\]?"
)

# YAML block-sequence under `amends:` with structured `target:` dict items:
#   amends:
#     - target: ADR-040 §4 ...
_AMENDS_BLOCK_ITEM_RE = re.compile(
    r"(?im)^\s+-\s+target\s*:\s*(?P<ref>[^\n]+)"
)

# Full ADR-NNN or ADR-NNN-AMEND-K identifier (stops at whitespace / punct).
# Used to pull the primary reference token from an `amends:` value.
_AMENDS_REF_RE = re.compile(r"ADR-\d{3}[a-z]?(?:-AMEND-\d+)?")


def _extract_amends_targets(text: str) -> List[str]:
    """Return the list of `amends:` target IDs declared in an AMEND file.

    Handles four formats:

    * YAML scalar:        ``amends: ADR-042``
    * YAML inline list:   ``amends: [ADR-118]``
    * Bold markdown:      ``**Amends:** ADR-019``
    * YAML block sequence with ``target:`` dicts::

          amends:
            - target: ADR-040 §4 (Credential lifecycle)

    Returns a list of canonical target IDs (e.g. ``["ADR-042"]``,
    ``["ADR-019-AMEND-1"]``).  Each ID is the longest
    ``ADR-NNN[-AMEND-K]`` token found at the START of the value
    (before any whitespace / punctuation).  Parenthetical annotations
    such as ``§4 (context)`` are stripped.
    """
    refs: List[str] = []
    seen: set = set()

    def _add(raw: str) -> None:
        """Extract first ADR-NNN[-AMEND-K] from *raw* and record it."""
        m = _AMENDS_REF_RE.search(raw.strip())
        if m:
            ref = m.group(0)
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)

    # Inline / scalar / bold-markdown forms
    for m in _AMENDS_INLINE_RE.finditer(text):
        raw = m.group("ref").strip()
        # Skip if the value is empty or starts a block sequence (next char
        # would be a newline, but the regex already stops at \n, so an empty
        # match means the line is just `amends:` with no value).
        if not raw:
            continue
        _add(raw)

    # Block-sequence `target:` form
    for m in _AMENDS_BLOCK_ITEM_RE.finditer(text):
        raw = m.group("ref").strip()
        _add(raw)

    return refs


# ---------------------------------------------------------------------------
# README "Known amendment chain gaps" parser
# ---------------------------------------------------------------------------

_README_GAP_SECTION_RE = re.compile(
    r"(?is)##\s+Known amendment chain gaps.*?(?=^##|\Z)", re.MULTILINE
)
# e.g. "ADR-040: base → AMEND-2 (no AMEND-1)"
_GAP_ENTRY_RE = re.compile(r"(ADR-\d{3}[a-z]?)\s*:", re.IGNORECASE)


def _load_known_chain_gaps(adr_dir: Path) -> set:
    """Parse the README in *adr_dir* and return the set of base ADR IDs
    whose amendment chains have documented gaps (e.g. ``{"ADR-040"}``).

    Only ADR IDs mentioned in the "Known amendment chain gaps" section are
    returned.  Returns an empty set if the README is missing or the section
    is absent.
    """
    readme = adr_dir / "README.md"
    if not readme.is_file():
        return set()
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return set()
    m = _README_GAP_SECTION_RE.search(text)
    if not m:
        return set()
    section_text = m.group(0)
    return {m2.group(1).upper() for m2 in _GAP_ENTRY_RE.finditer(section_text)}


def _extract_yaml_supersedes(text: str) -> List[str]:
    """Return ADR-NNN identifiers declared in a YAML frontmatter
    ``supersedes:`` block sequence (multi-line YAML list form).

    E.g.::

        supersedes:
          - rename_source: ADR-111-pii-core-promotion (ID 111; ...)
          - ADR-099

    Only applies to the frontmatter block (between the opening ``---``
    fences). Body occurrences are handled by ``SUPERSEDES_RE``.

    Only the FIRST ADR-NNN token in each list item value is extracted
    (the primary superseded reference). Parenthetical context like
    ``(renamed via ADR-117 doctrine)`` is excluded to avoid treating
    policy-reference ADRs as supersession targets.
    """
    fm_match = _FM_FENCE_RE.match(text)
    if not fm_match:
        return []
    fm = fm_match.group("fm")
    block_match = _FM_SUPERSEDES_BLOCK_RE.search(fm)
    if not block_match:
        return []
    refs: List[str] = []
    for item_match in _FM_LIST_ITEM_RE.finditer(block_match.group("items")):
        content = item_match.group("content")
        # Strip any parenthetical context (e.g. "(ID 111; renamed via ADR-117 doctrine)")
        # so we only consider the primary reference, not policy/context mentions.
        pre_paren = content.split("(")[0]
        idm = ADR_ID_RE.search(pre_paren)
        if idm:
            ref = "ADR-" + idm.group(1)
            if ref not in refs:
                refs.append(ref)
    return refs


VALID_STATUS_PREFIXES = (
    "PROPOSED",
    "ACCEPTED",
    "SUPERSEDED",
    "REJECTED",
    "DEPRECATED",
    "RETRACTED",  # terminal state for ADRs withdrawn before reaching ACCEPTED
)


def parse_adr(path: Path) -> Dict[str, object]:
    """Parse an ADR file. Returns a dict with normalized fields."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "path": path,
            "error": f"unreadable: {exc}",
        }

    status = _extract_status(text)
    # Compact whitespace: "SUPERSEDED  (2026-04-13)" → "SUPERSEDED"
    # Keep only the leading word for the canonical status.
    status_token = status.split()[0] if status else ""
    # Also store the inline-regex match for later inline-SUPERSEDED scanning.
    m_status = STATUS_RE.search(text)

    superseded_by_refs: List[str] = []
    _sb_seen: set = set()
    for m in SUPERSEDED_BY_RE.finditer(text):
        line = m.group("ref").strip()
        # Extract any ADR-NNN tokens on the line (there may be multiple)
        for idm in ADR_ID_RE.finditer(line):
            ref = "ADR-" + idm.group(1)
            if ref not in _sb_seen:
                _sb_seen.add(ref)
                superseded_by_refs.append(ref)

    # Also accept inline "SUPERSEDED by ADR-NNN" on the status line itself
    # (ADR-017 form: "## Status: SUPERSEDED by ADR-020 (2026-04-14)").
    # Scope scan to END-OF-LINE so we do not sweep up ADR-NNN refs from
    # the historical prose that follows.
    if m_status:
        start = m_status.start()
        # `^` under re.MULTILINE can anchor to the `\n` BEFORE a line, so
        # start may point at the preceding newline. Skip it.
        while start < len(text) and text[start] == "\n":
            start += 1
        eol = text.find("\n", start)
        status_line_only = text[start:eol] if eol != -1 else text[start:]
        if re.search(r"(?i)SUPERSEDED\s+by\s+ADR-\d{3}", status_line_only):
            for idm in re.finditer(r"ADR-(\d{3})", status_line_only):
                ref = "ADR-" + idm.group(1)
                if ref not in superseded_by_refs:
                    superseded_by_refs.append(ref)

    supersedes_refs: List[str] = []
    for m in SUPERSEDES_RE.finditer(text):
        line = m.group("ref").strip()
        for idm in ADR_ID_RE.finditer(line):
            ref = "ADR-" + idm.group(1)
            if ref not in supersedes_refs:
                supersedes_refs.append(ref)
    # Also parse YAML frontmatter block-sequence `supersedes:` lists.
    # (e.g. ADR-120 uses `supersedes:\n  - rename_source: ADR-111 ...`)
    # We only extract the PRIMARY (first) ADR-NNN token from each list item
    # to avoid pulling in parenthetical context references like
    # "renamed via ADR-117 doctrine" as false supersession targets.
    for ref in _extract_yaml_supersedes(text):
        if ref not in supersedes_refs:
            supersedes_refs.append(ref)

    # Inline supersession note ("SUPERSEDED — removed in PLAN-006 Phase 6b")
    # Accept as a concrete retirement signal even without a
    # `Superseded-By:` field.
    inline_note_ok = bool(
        re.search(r"SUPERSEDED\s*[—\-:]\s*.+", text[:2048], re.IGNORECASE)
    )

    # amends: targets — only meaningful for AMEND files, but we parse
    # unconditionally so the field is always present in the returned dict.
    amends_targets = _extract_amends_targets(text)

    return {
        "path": path,
        "status_raw": status,  # full extracted text (may include parenthetical)
        "status": status_token,
        "superseded_by": superseded_by_refs,
        "supersedes": supersedes_refs,
        "inline_retirement_note": inline_note_ok,
        "amends_targets": amends_targets,
        "error": None,
    }


def validate_chain(adr_dir: Path) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings) for the ADR corpus under `adr_dir`."""
    errors: List[str] = []
    warnings: List[str] = []

    if not adr_dir.is_dir():
        return [f"ADR dir not found: {adr_dir}"], []

    # Load documented chain gaps from README before building corpus.
    known_chain_gaps = _load_known_chain_gaps(adr_dir)

    adrs: Dict[str, Dict[str, object]] = {}
    for f in sorted(adr_dir.iterdir()):
        if f.name == "README.md":
            continue
        if not f.name.startswith("ADR-"):
            continue
        m = ADR_FILE_RE.match(f.name)
        if not m:
            errors.append(
                f"{f}: filename must match ADR-NNN-<kebab-slug>.md "
                f"(NNN zero-padded 3-digit, AMEND variant, or 049a)"
            )
            continue
        # For base ADRs: adr_id = "ADR-NNN" (e.g. "ADR-019")
        # For AMEND files: use the stem without .md so they don't collide
        # with the base ADR id (e.g. "ADR-019-AMEND-1-...").
        slug_body = f.stem  # e.g. "ADR-019-AMEND-1-confidence-gate-..."
        if "-AMEND-" in slug_body.upper():
            adr_id = slug_body  # full stem as unique key
        else:
            adr_id = "ADR-" + m.group(1)  # e.g. "ADR-019" or "ADR-049a"
        if adr_id in adrs:
            errors.append(
                f"{f}: duplicate ADR id {adr_id} "
                f"(also at {adrs[adr_id]['path']})"
            )
            continue
        parsed = parse_adr(f)
        if parsed.get("error"):
            errors.append(f"{f}: {parsed['error']}")
            continue
        adrs[adr_id] = parsed

    # Check 1: Status field exists + is valid
    for adr_id, d in adrs.items():
        status = str(d.get("status") or "")
        if not status:
            errors.append(f"{d['path']}: missing `Status:` field")
            continue
        # status_token is already the leading word. Accept compound forms
        # that start with a known prefix (e.g. "ACCEPTED-as-RESERVED",
        # "DEPRECATED-pending-replacement").
        if not any(status.startswith(pfx) for pfx in VALID_STATUS_PREFIXES):
            errors.append(
                f"{d['path']}: `Status: {d['status_raw']}` — must start "
                f"with one of {list(VALID_STATUS_PREFIXES)}"
            )

    # Check 2: SUPERSEDED ADRs declare a concrete successor
    for adr_id, d in adrs.items():
        if not str(d.get("status") or "").startswith("SUPERSEDED"):
            continue
        has_superseded_by = bool(d.get("superseded_by"))
        has_inline_retirement = bool(d.get("inline_retirement_note"))
        if not (has_superseded_by or has_inline_retirement):
            errors.append(
                f"{d['path']}: SUPERSEDED but missing both `Superseded-By:` "
                f"reference AND inline retirement note — broken chain"
            )

    # Check 3: Superseded-By / Supersedes mutual consistency
    for adr_id, d in adrs.items():
        for target in list(d.get("superseded_by") or []):  # type: ignore[arg-type]
            if target not in adrs:
                # Pointing at a non-existent ADR is a warning (may be a
                # commit-only retirement where the successor is not an
                # ADR).
                warnings.append(
                    f"{d['path']}: `Superseded-By:` references unknown "
                    f"{target} (warning — may point at commit/plan, not ADR)"
                )
                continue
            target_d = adrs[target]
            target_supersedes = list(target_d.get("supersedes") or [])  # type: ignore[arg-type]
            if adr_id not in target_supersedes:
                warnings.append(
                    f"{d['path']}: declares Superseded-By={target} but "
                    f"{target} does not declare Supersedes={adr_id} "
                    f"(missing bidirectional link)"
                )

        for target in list(d.get("supersedes") or []):  # type: ignore[arg-type]
            if target not in adrs:
                errors.append(
                    f"{d['path']}: `Supersedes:` points at unknown {target}"
                )
                continue
            target_d = adrs[target]
            if not str(target_d.get("status") or "").startswith("SUPERSEDED"):
                errors.append(
                    f"{d['path']}: declares Supersedes={target}, but "
                    f"{target_d['path']} has "
                    f"`Status: {target_d.get('status_raw') or '(missing)'}` "
                    f"— should be SUPERSEDED"
                )

    # Check 5: amends: lineage validation for AMEND files
    #
    # For each ADR-NNN-AMEND-K file:
    #   a) It must declare an `amends:` target, and that target must resolve
    #      to an existing entry in the corpus.  A missing or broken target
    #      is an ERROR (non-zero exit).
    #   b) The amendment predecessor must exist:
    #        - K == 1 → predecessor is the base ADR-NNN
    #        - K  > 1 → predecessor is ADR-NNN-AMEND-(K-1)
    #      A missing predecessor is an ERROR unless the gap is documented in
    #      the README "Known amendment chain gaps" section for this base ADR.
    #
    # Corpus key form for AMEND files: full stem, e.g.
    #   "ADR-019-AMEND-1-confidence-gate-block-mode-lifecycle"
    # Corpus key form for base ADRs: "ADR-NNN" (e.g. "ADR-019").
    #
    # Target lookup: an `amends:` value like "ADR-019" maps to corpus key
    # "ADR-019"; a value like "ADR-019-AMEND-1" maps to the corpus key
    # whose PREFIX is "ADR-019-AMEND-1" (since the full key includes the
    # slug after the AMEND-K part).

    # Build a prefix-lookup index for AMEND corpus keys so we can resolve
    # short IDs like "ADR-019-AMEND-1" → full key.
    _amend_key_by_prefix: Dict[str, str] = {}
    for key in adrs:
        if "-AMEND-" in key.upper():
            # Extract the "ADR-NNN-AMEND-K" prefix (strip trailing slug).
            parts = key.split("-")
            amend_idx = next(
                (i for i, p in enumerate(parts) if p.upper() == "AMEND"), None
            )
            if amend_idx is not None and amend_idx + 1 < len(parts):
                prefix = "-".join(parts[: amend_idx + 2])  # "ADR-NNN-AMEND-K"
                _amend_key_by_prefix[prefix.upper()] = key

    def _resolve_amends_target(ref: str) -> Optional[str]:
        """Return the corpus key for *ref*, or None if not found.

        Handles both base refs ("ADR-042") and AMEND refs
        ("ADR-019-AMEND-1") — the latter are matched by prefix since the
        full corpus key includes the slug.
        """
        # Exact match (base ADRs like "ADR-042")
        if ref in adrs:
            return ref
        # Prefix match for AMEND refs (the ref may omit the slug)
        return _amend_key_by_prefix.get(ref.upper())

    # Regex to extract ADR-NNN-AMEND-K structure from the corpus key.
    _AMEND_STEM_RE = re.compile(
        r"^(?P<base>ADR-\d{3}[a-z]?)-AMEND-(?P<k>\d+)", re.IGNORECASE
    )

    for adr_id, d in adrs.items():
        if "-AMEND-" not in adr_id.upper():
            continue  # not an AMEND file

        stem_m = _AMEND_STEM_RE.match(adr_id)
        if not stem_m:
            continue  # malformed — already caught by filename check

        base_id = stem_m.group("base").upper()  # e.g. "ADR-040"
        k = int(stem_m.group("k"))             # amendment number

        amends_targets: List[str] = list(d.get("amends_targets") or [])  # type: ignore[arg-type]

        # 5a) Must declare at least one amends: target
        if not amends_targets:
            errors.append(
                f"{d['path']}: AMEND file declares no `amends:` target "
                f"— broken lineage (add 'amends: ADR-NNN' or "
                f"'**Amends:** ADR-NNN')"
            )
            continue  # no point checking predecessor without a declared target

        # 5b) Each declared target must resolve to an existing corpus entry
        all_targets_resolved = True
        for ref in amends_targets:
            resolved = _resolve_amends_target(ref)
            if resolved is None:
                errors.append(
                    f"{d['path']}: `amends: {ref}` points at a nonexistent ADR "
                    f"— target not found in corpus"
                )
                all_targets_resolved = False

        if not all_targets_resolved:
            continue  # skip predecessor check if target is broken

        # 5c) Predecessor must exist (chain gap check)
        if k == 1:
            # Predecessor is the base ADR-NNN
            base_key = base_id  # corpus keys for base ADRs are "ADR-NNN"
            predecessor_exists = base_key in adrs
        else:
            # Predecessor is ADR-NNN-AMEND-(K-1)
            predecessor_prefix = f"{base_id}-AMEND-{k - 1}"
            predecessor_key = _amend_key_by_prefix.get(predecessor_prefix.upper())
            predecessor_exists = predecessor_key is not None

        if not predecessor_exists:
            # Check if this gap is documented in the README
            if base_id in known_chain_gaps:
                # Documented gap — skip silently (allowed exception)
                pass
            else:
                if k == 1:
                    missing_desc = f"base {base_id}"
                else:
                    missing_desc = f"{base_id}-AMEND-{k - 1}"
                errors.append(
                    f"{d['path']}: amendment chain gap — predecessor "
                    f"{missing_desc} not found in corpus "
                    f"(document this gap in the README 'Known amendment chain gaps' "
                    f"section if it is intentional)"
                )

    return errors, warnings


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — validate ADR supersede / amend chain integrity."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--adr-dir",
        type=Path,
        default=DEFAULT_ADR_DIR,
        help=f"ADR directory (default: {DEFAULT_ADR_DIR})",
    )
    args = p.parse_args(argv)

    errors, warnings = validate_chain(args.adr_dir)

    for w in warnings:
        sys.stderr.write(f"WARN: {w}\n")
    for e in errors:
        sys.stderr.write(f"ERROR: {e}\n")

    if errors:
        sys.stderr.write(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)\n")
        return 1
    sys.stderr.write(f"PASS: ADR chain clean ({len(warnings)} warning(s))\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
