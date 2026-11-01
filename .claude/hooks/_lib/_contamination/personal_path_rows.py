"""Row rendering for contamination personal-path reports."""
from __future__ import annotations

def _emit_personal_path_rows(scan: PersonalPathScan,
                             allowlist: Dict[str, "PersonalPathRow"]) -> int:
    """`--emit-personal-path-rows`: a row per file that is not waived TODAY.

    A convenience for the human who must then write each reason — the emitted
    reason is `REPLACE-WITH-REASON`, which the parser REFUSES, so a paste that
    skips the decision fails the gate instead of passing it.

    It emits for a file whose row exists but whose DIGEST no longer matches,
    because that is the ordinary workflow now: the file was edited, the
    waiver lapsed, and what the operator needs is the new digest. The reason
    still comes out unreasoned — a re-approval is a decision too.

    A hit with no digest is a NAME hit, and no row can waive a name. Those
    are COUNTED on stderr instead of printed as rows, because stdout here
    exists to be pasted into the allowlist and a row that the parser
    refuses by construction is not something to paste.
    """
    nameless = 0
    unexpressible = 0
    for hit in scan.hits:
        # The NAME first, in the SAME order the verdict uses it — nothing
        # waives a path. This ordering was a cure when a rule waiver was
        # consulted ahead of it and swallowed a mixed hit (pair-rail
        # round 1, P2, both lanes); the waiver is gone, and the ordering
        # stays because a mixed hit HAS a digest, so "no digest" was
        # never the full test for a name hit.
        if (hit.sha256 is None
                or _PERSONAL_PATH_NAME_LINE in hit.lines):
            nameless += 1
            continue
        row = allowlist.get(hit.rel)
        if row is not None and row.sha256 == hit.sha256:
            continue
        # The row is built from the path the PARSER will read, not from
        # the path the REPORT would print. `_personal_path_safe` is the
        # display choke point and, to stay injective, it doubles a
        # backslash: `docs/a\b.md` is a legal git path and came out of
        # it as `docs/a\\b.md`, which fails the probe below and was
        # counted "unexpressible" -- with a note blaming whitespace --
        # while a HAND-WRITTEN row for that same path parses and waives
        # (mechanism lane, round 18; reproduced). Display escaping is
        # not row grammar.
        #
        # The two properties that boundary owned here are kept as
        # explicit refusals, because both are real: a path that NAMES a
        # home directory must not be printed at all (round cure-2, P2),
        # and a path carrying a control character cannot be offered as
        # a row -- escaped it is a DIFFERENT path to the parser, and
        # raw it would put a terminal command in the output. Such a
        # file has to be RENAMED, not waived, which is what the note
        # below says.
        if (_personal_path_hit_either(hit.rel)
                or not _personal_path_renders_as_itself(hit.rel)):
            unexpressible += 1
            continue
        candidate = ("%s | sha256:%s | %s"
                     % (hit.rel, hit.sha256, _PERSONAL_PATH_UNREASONED))
        # The emitter is judged by the PARSER, not by its own formatting.
        # `docs/frozen log.md` is a valid git path and an INVALID row:
        # `_PERSONAL_PATH_ROW_RE` refuses whitespace and `|` in the path
        # field, so the advertised paste produced a MALFORMED row and the
        # frozen artifact ended with no usable waiver at all, from a mode
        # that had exited 0 (mechanism lane, round 11; reproduced).
        # Producer and consumer share one grammar: the row is offered only
        # if the parser that will read it accepts it AND resolves it back
        # to the same path.
        probe = _PERSONAL_PATH_ROW_RE.match(candidate)
        if probe is None or probe.group(1) != hit.rel:
            unexpressible += 1
            continue
        print(candidate)
    if nameless:
        print(
            "NOTE: %d file(s) hit on their own PATH and have no row form: "
            "rename them" % nameless, file=sys.stderr)
    if unexpressible:
        print(
            "NOTE: %d file(s) have a path this rule cannot offer as a row "
            "(whitespace, `|`, a control character, or a home directory "
            "written into the path itself) and have no row form: rename "
            "them — a row emitted for such a path is one the parser "
            "refuses, or one no reviewer could read"
            % unexpressible, file=sys.stderr)
    return 0


def _personal_path_mask_owner(match, replacement: str) -> str:
    """``replacement`` for this owner segment -- unless it is a PLACEHOLDER.

    The mask asks the SAME question the matcher asks: is this lowercased
    owner segment on `_PERSONAL_PATH_PLACEHOLDERS`? `alice`, `bob`,
    `devuser`, `runner` are the segments the rule exists NOT to flag, and
    replacing them told a reviewer nothing while making two different
    tracked files -- and a real owner -- render as one line (mechanism
    lane, round 24; reproduced before it was believed).

    The RAW lowercased segment decides, and only it. NFKC folding can turn
    a full-width owner into an ASCII placeholder, never a placeholder into
    a person, so consulting the folded reading here is the bypass and not
    the safeguard -- the same asymmetry `_personal_path_hit_either` states
    from the other side.

    `match.group(0)` is returned verbatim rather than re-spelled: the point
    is that the reader can tell WHICH file, and `/Users//alice` and
    `-Users--alice` are not the same path as their normal forms. A
    function replacement is used, so what is returned is taken literally --
    no backslash re-interpretation on a path that carries one.
    """
    if match.group(1).lower() in _PERSONAL_PATH_PLACEHOLDERS:
        return match.group(0)
    return replacement
