from __future__ import annotations

from typing import NamedTuple

class PersonalPathHit(NamedTuple):
    """One in-scope file, its 1-based hit lines, and the digest of
    the bytes that produced them.

    `sha256` is over the RAW BYTES this scan matched — a file's content,
    or a symlink's target string — taken from the SAME read, never a
    second one. A row waives a file by naming that digest, so hashing
    any other bytes than the ones that were matched would let a row
    waive content nobody scanned (and would race an edit between the
    two reads). It is None when there were no BODY hits to pin — a
    name-only hit, or no readable content — and a hit with no digest
    is unwaivable by construction, which is the fail-closed default.
    """

    rel: str
    lines: Tuple[int, ...]
    sha256: Optional[str] = None
    #: The same bytes with CRLF folded to LF. NOTHING is ever waived on
    #: this digest -- it exists only so a mismatch caused by a checkout
    #: EOL filter can be NAMED instead of looking like an edit nobody
    #: made (pair-rail round 3, P2). Diagnosis, not a second key.
    sha256_lf: Optional[str] = None


class PersonalPathScan(NamedTuple):
    """What the walk found: the hits, and nothing else.

    There is no rule-waived map any more. It carried the ONE waiver
    the scan decided for itself -- the signed-sentinel rule, deleted
    with the refuter's F1 -- and a field that is always empty is a
    channel waiting to be re-opened. Every waiver now comes from the
    tracked allowlist and is applied by `personal_path_verdict`, which
    stays pure so tests can drive every split without a filesystem.

    Each in-scope entry is read exactly once, AS A SUBJECT. That is
    now literally true: the sidecar read a sentinel used to cause is
    gone with the rule that needed it (pair-rail round 2, P3, which
    the deletion answers rather than qualifies).
    """

    hits: List[PersonalPathHit]


class PersonalPathRow(NamedTuple):
    """One allowlist row: the digest it pins, and the reason a human wrote.

    `rowno` is the 1-based line the row was read from. A row is refused by
    NUMBER -- that is the only address an operator can act on -- and the
    reason check below runs after the load, in the caller that knows the
    repository, so the row has to carry where it came from.
    """

    sha256: str
    reason: str
    rowno: int = 0


class PersonalPathVerdict(NamedTuple):
    """Split of the scan against the allowlist. `waived` keeps the reasons.

    `mismatched` is its own category and not a kind of `unwaived`: a row
    exists and NAMES this file, but the bytes moved since a human read
    them. The operator action is different (re-read the file, re-record
    the digest, not write a new decision), so the report says so.
    """

    unwaived: List[PersonalPathHit]
    waived: List[Tuple[str, str]]      # (rel, reason)
    stale: List[str]
    malformed: List[int]
    mismatched: List[str]


def _personal_path_blob(
    path: Path, rel: str, index_is_link: bool = False,
) -> Optional[PersonalPathBlob]:
    """The BYTES git stores for a tracked entry, or None when there are none.

    ONE classification, inside ONE try. Spreading it over an `is_symlink()`
    outside the try, a suffix test before it and a read inside it produced two
    pair-rail findings in a row (round cure-2, P1+P2): the suffix test skipped
    a symlink by its NAME — `docs/photo.png -> /Users/<name>/photo.png` walked
    straight through the gate — and `is_symlink()` itself raises
    `PermissionError` when an ancestor directory is unsearchable, which
    escaped `PersonalPathUnreadable` as an rc-1 traceback carrying the
    absolute path. Two symptoms, one shape: a decision taken outside the
    boundary that is supposed to contain it.

    * a SYMLINK is its target STRING — that is the blob git stores, and where
      a `/Users/<name>/…` sits. Following the link would scan someone else's
      file instead, and a dangling one would read as absent;
    * a tracked path with no file is None: absence is not unreadable INPUT;
    * NOTHING IS SKIPPED BY NAME. v3 skipped a regular file whose SUFFIX
      was in `_SKIP_SUFFIXES`, which is the term rule's list, written for
      a different question. It was the last name-shaped skip left in this
      rule after the `.asc` and `*-approved.md` ones were removed, and
      leaving it would have kept the class alive in a third form: an image
      carries the author's home path in its metadata all the time, which
      is precisely the leak this rule exists to find. MEASURED before it
      was removed (CENSUS above): ZERO in-scope regular files carry one of
      those suffixes, so the removal moves no row and costs no read that
      the rule was not already paying;
    * BYTES, not text. Decoding is the CALLER's, in one place, so the
      digest a waiver is pinned to is taken from the same object that was
      matched. `errors="replace"` there, never `strict`: an undecodable
      blob must not be SKIPPED (the fail-open the LEDGER exception above
      had to cure by hand), and the replacement is deterministic.

    Every OSError on any of those steps becomes `PersonalPathUnreadable` with
    `rel` and the REASON — never `exc`, whose str() carries the absolute
    filename — and `from None`, because an uncaught one would print the
    chained OSError repr and leak the same path through the traceback.
    """
    try:
        if index_is_link:
            # git said mode 120000. On a normal checkout that is a link
            # and the blob is the target string; under
            # `core.symlinks=false` it is a regular file whose CONTENT is
            # that same string. Both readings give the bytes git stores.
            #
            # ONE reader for both, and the SAME reader the non-link branch
            # uses. Asking `is_symlink()` and then `is_file()` was three
            # questions about three moments, and the answer to each is
            # whatever `pathlib` decides to swallow: on the supported floor
            # `is_symlink()` RAISES under an unsearchable ancestor (measured,
            # 3.9.6) while `os.path.lexists` answers False for anything it
            # cannot stat -- so the v4.2 shape was one pathlib change away
            # from reading a present-but-unreadable entry as ABSENT
            # (mechanism lane, round 11). `_personal_path_read_nofollow`
            # classifies by ERRNO in a single open: absence is `ENOENT` /
            # `ENOTDIR`, a link is `ELOOP` and comes back as its target
            # string, a directory or a device is fatal, and any other
            # OSError propagates to the sanitised fatal below.
            blob = _personal_path_read_nofollow(path)
            if blob is None:
                # ABSENT. A tracked path with no file is not unreadable
                # INPUT -- the one documented `None` of this function.
                return None
            # git's INDEX decides link-ness, never the filesystem: under
            # `core.symlinks=false` the entry is a regular file and the
            # reader says so, but the bytes are still a link payload and
            # must be denied every waiver a link is denied.
            return PersonalPathBlob(raw=blob.raw, is_symlink=True)
        return _personal_path_read_nofollow(path)
    except PersonalPathUnreadable as exc:
        # The reader below raises this for a DIRECTORY or a FIFO left where
        # a tracked file should be, and it is not an OSError -- so it went
        # past the clause below and the fatal named the reason without the
        # SUBJECT. In a large tree that is a message an operator cannot act
        # on (mechanism lane, round 14). The path is MASKED, like every
        # other path this rule prints.
        raise PersonalPathUnreadable(
            "%s: %s" % (_personal_path_mask_rel(rel), exc)) from None
    except OSError as exc:
        raise PersonalPathUnreadable(
            "%s: %s" % (rel, _oserror_reason(exc))) from None


def load_personal_path_allowlist(
    path: Path,
) -> Tuple[Dict[str, "PersonalPathRow"], List[int]]:
    """Parse into ``({rel: row}, malformed row numbers)``.

    Malformed rows are RETURNED by 1-based row number — never by content, so
    the report cannot echo a hand-written path — and never dropped silently: a
    file the parser could not read whole is not a file that waives anything. A
    DUPLICATE path is malformed too, and its entry is REMOVED rather than
    resolved to one of the two: the ambiguity fails closed. So is a row whose
    reason is still the emitted placeholder, and an absolute or `..` path.

    An ABSENT file parses as empty — also fail-closed: every hit reads as
    unwaived. Propagates OSError when the file exists but cannot be read, and
    UnicodeDecodeError when it cannot be DECODED — both are INPUT failures the
    caller turns into rc 2. Neither is swallowed here: a file this function
    could not read WHOLE waives nothing, and must not read as waiving nothing
    quietly.
    """
    entries: Dict[str, PersonalPathRow] = {}
    malformed: List[int] = []
    # ONE read, through the SAME no-follow helper the subject files go
    # through. `is_file()` then `read_text()` was a check and a use of
    # two different inodes: trackedness validated the name, and this
    # re-opened it, so replacing the validated file with a symlink in
    # the gap delivered a crafted untracked row to the waiver
    # (pair-rail round 4, P1). A LINK is refused rather than followed,
    # and a present-but-special inode is fatal, not "absent" -- the
    # helper answers all three questions in one syscall.
    blob = _personal_path_read_nofollow(path)
    if blob is None:
        # ABSENT, exactly as `is_file()` answered before: an allowlist
        # that is not there waives nothing and is not an error. Every
        # OTHER failure -- unreadable, undecodable, a special inode --
        # PROPAGATES, because a file that exists and cannot be read
        # WHOLE must not read as waiving nothing quietly.
        return entries, malformed
    if blob.is_symlink:
        raise PersonalPathUnreadable(
            "the allowlist is a SYMLINK; a link is a claim about "
            "another file, not a reviewable waiver list")
    seen_twice = set()
    # `split("\n")`, NOT `splitlines()` -- the same cure, for the same
    # reason, as `_personal_path_hit_lines` three hundred lines up.
    # `splitlines()` breaks on a bare CR, `\v`, `\f`, `\x1c`-`\x1e`,
    # U+2028 and U+2029; git counts LINES by LF. A tracked file holding
    #     `# reviewed<CR>docs/leak.md | sha256:<64 hex> | reason`
    # is ONE insertion in the diff a human reviews, and `splitlines()`
    # read it as a comment PLUS a granted waiver -- reproduced, rc 0 with
    # the leak waived (mechanism lane, round 13). A waiver a reviewer
    # cannot see ends the only claim a waiver makes.
    # Counted the way git counts, the whole physical line is one row, it
    # starts with `#`, and there is no waiver to grant. A row carrying a
    # stray separator inside it then fails `_PERSONAL_PATH_ROW_RE` and is
    # MALFORMED by number, which is what ambiguous input gets here.
    decoded = blob.raw.decode("utf-8")
    # A control byte in a waiver list makes the row say one thing to
    # this parser and another to whoever reads it, so the FILE is
    # refused. Round 18 found it as a NUL: a row appended with a NUL
    # inside its reason waived a real hit at rc 0 while the 320-row diff
    # rendered as one binary line.
    #
    # What this comment used to add -- that ONE NUL inside git's first
    # 8000 bytes makes `git diff` print `Binary files ... differ` for the
    # WHOLE file -- is NOT a rule git has: an explicit `diff` attribute
    # forces a text diff despite the NUL (round 21, B3; reproduced,
    # numstat `-/-` becomes `2/0`). The claim is withdrawn here as it was
    # withdrawn two hundred lines above, and the refusal stays for the
    # harm that IS a property of the bytes: display.
    #
    # The refusal is over the FILE, not the row: the blindness is the
    # file's, and a list whose other rows a reviewer cannot read either
    # is not a list this rule may consult. It names the row NUMBER and
    # the CODEPOINT -- never the content, which is the same discipline
    # every other refusal in this parser keeps.
    # An INTERIOR carriage return, which the class above deliberately does
    # not carry. `\s*` in the row grammar CONSUMES it, so
    # `<path> | sha256:<hex> | <CR># reviewed` reached the reason predicate
    # as `# reviewed`, waived at rc 0, and git emitted the CR raw -- the
    # row renders overwritten in the terminal that reviews it (text lane,
    # round 20; reproduced). The predicate can only judge what the grammar
    # hands it, so the question is asked HERE, where the physical row still
    # exists. A row ENDING in CR is untouched: that is the CRLF checkout
    # this parser has always accepted, and it is the only reason `\r` is
    # outside the class above.
    for rowno, raw in enumerate(decoded.split("\n"), 1):
        if "\r" in raw.rstrip("\r"):
            raise PersonalPathUnreadable(
                "the allowlist carries a carriage return INSIDE row %d "
                "(not as its line ending); git emits it raw and the row "
                "renders overwritten, so NONE of the rows waives anything "
                "(remove it, then re-run)" % rowno)
    control = _PERSONAL_PATH_ALLOWLIST_CONTROL_RE.search(decoded)
    if control is not None:
        raise PersonalPathUnreadable(
            "the allowlist carries the control character U+%04X on row "
            "%d; a control character rewrites how the row DISPLAYS in "
            "the terminal that renders it, so the row can say one thing "
            "to this parser and another to its reader -- NONE of them "
            "waives anything (remove the character, then re-run)"
            % (ord(control.group(0)),
               decoded.count("\n", 0, control.start()) + 1))
    for rowno, raw in enumerate(decoded.split("\n"), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            # A COMMENT is not a waiver, and until round 10 that meant
            # nothing read it at all: this file lives OUTSIDE both
            # `_PERSONAL_PATH_SCOPE` prefixes, so the rule never scans
            # it, and the parser skipped `#` lines before any predicate.
            # `archived from /Users/<name>/...` written one line above
            # the row it explains was therefore the one place in this
            # repository where a home path was examined by NOTHING
            # (mechanism lane, round 10, A-P2-2).
            # Same refusal a ROW naming a home directory gets, for the
            # same reason -- the waiver file is subject to the rule it
            # waives -- and it is reported by ROW NUMBER, so the fix is
            # the line the operator is already looking at. MEASURED on
            # the shipped allowlist before choosing this: 76 comment
            # lines, 0 of them malformed under this predicate.
            if _personal_path_hit_either(line):
                malformed.append(rowno)
            continue
        match = _PERSONAL_PATH_ROW_RE.match(line)
        if match is None:
            # Includes every row that carries no `sha256:<64 hex>` field:
            # a v3-shaped row, a truncated digest, a digest with a
            # non-hex character -- and, since the signer directive was
            # deleted with the rule waiver it fed, a leftover
            # `signer-fingerprint: <40 hex>` line from a v4.0 allowlist.
            # A row the parser cannot read WHOLE waives nothing and says
            # so (rc 1): an adopter upgrading is told which lines to
            # delete rather than having them silently ignored.
            malformed.append(rowno)
            continue
        rel = match.group(1)
        sha = match.group(2).lower()
        reason = match.group(3)
        if (
            reason == _PERSONAL_PATH_UNREASONED
            # A reason a reviewer cannot SEE is not a written decision:
            # zero-width and bidirectional characters satisfied `\S`
            # (mechanism lane, round 19; reproduced, rc 0 with the leak
            # waived). MALFORMED by number, like every other row this
            # parser cannot read.
            or not _personal_path_reason_is_visible(reason)
            or rel.startswith("/")
            or ".." in rel.split("/")
            # A row that itself names a home directory would be printed back
            # on a GREEN run (the reason is echoed grouped). Refused at the
            # source, so no printer ever sees it: the waiver file is subject
            # to the rule it waives, which is what makes it reviewable.
            or _personal_path_hit_either(line)
        ):
            malformed.append(rowno)
            continue
        if rel in entries or rel in seen_twice:
            malformed.append(rowno)
            seen_twice.add(rel)
            entries.pop(rel, None)
            continue
        entries[rel] = PersonalPathRow(
            sha256=sha, reason=reason, rowno=rowno)
    return entries, malformed


class PersonalPathUnreadable(Exception):
    """An in-scope file that EXISTS and cannot be read — fatal, not skipped."""


class PersonalPathBlob(NamedTuple):
    """The bytes git stores for a tracked entry, and whether it is a link.

    The link fact travels WITH the bytes because it is decided inside the
    same `try` that read them. Asking the filesystem a second time is how
    two pair-rail findings in a row were built (round cure-2, P1+P2): a
    decision taken outside the boundary that is supposed to contain it.
    """

    raw: bytes
    is_symlink: bool


def personal_path_verdict(
    scan: PersonalPathScan, allowlist: Dict[str, "PersonalPathRow"],
    malformed: Optional[List[int]] = None,
) -> PersonalPathVerdict:
    return _personal_path_verdict_impl(scan, allowlist, malformed)



