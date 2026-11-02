"""Rule 2 constants and policy rationale for the contamination CLI."""
from __future__ import annotations

import errno
import os
import re
import stat
import time

# RULE 2 — `personal-path`: absolute home paths under docs/ and .claude/plans/
# ---------------------------------------------------------------------------
# The TERM rule above exempts those two trees almost entirely: `.claude/plans/*`
# is a WHOLESALE glob (fnmatch's `*` crosses `/`) and most of `docs/` sits on
# the exact allowlist. Both exemptions were written for PROSE that legitimately
# names adopter context; neither was ever a decision about absolute HOME paths.
# This repository is PUBLIC, and the plan tree is where frozen rail transcripts
# and ceremony logs land — which is exactly where a `/Users/<name>/` leaks.
# PLAN-186 §Riscos recorded the follow-up (Codex P1, S339); this rule is it.
#
# WHAT IT FLAGS: an absolute home directory whose owner segment is a REAL name
# — `/Users/<name>/...`, `/home/<name>/...`, and the harness slug form
# `-Users-<name>-...` that a project state directory carries. The documented
# placeholder style (`/Users/<user>/`, `/Users/devuser/`, `/home/runner/`) is
# not a hit: `<` is not a path character, and the generic owner segments are
# listed below.
#
# NOTHING IS EXEMPT BY NAME OR BY SUFFIX. Every in-scope tracked path is
# read and matched the SAME WAY -- no basename, no extension and no
# directory decides that a file is not looked at. Three versions of this
# pack shipped a name-shaped skip and the pair-rail found each of them:
# `*.asc` exempt by suffix (v2, land round 1), `*-approved.md` exempt by
# basename (v2, round cure-2), and `OWNER-*.sh` exempt by basename BEFORE
# any content was read (v3, land round 1 -- the finding that dropped the
# pack). Each time the bypass was one rename: a tracked symlink
# `docs/OWNER-leak.sh -> /Users/<owner>/repo` walked through the gate that
# `docs/plain-leak.md` with the SAME target failed. The class is closed by
# REMOVAL, not by enumerating the safe names -- which is the only closure
# this repository has ever made stick (CLAUDE.md, S336 lesson).
#
# WAIVERS therefore act on a hit that has ALREADY been found, and come
# from exactly ONE place:
#   * the tracked allowlist file, ONE `<path> | sha256:<64 hex> | <reason>`
#     row per file. A row is a human decision with the decision written
#     down, and BOTH halves are checked: the reason must contain a
#     character that is actually shown and none that is a control or a
#     format character, so a reason of zero-width spaces -- which
#     satisfied the grammar and waived a real leak (round 19) -- is
#     MALFORMED. There is no glob, no directory prefix and no generated
#     baseline, because every shape that waives a file nobody named is the
#     shape this rule exists to remove. THE ROW IS PINNED TO CONTENT: it
#     waives the file only while the bytes the scan read hash to the
#     recorded digest, so a row cannot waive a file FOREVER (pair-rail,
#     land round 1, P2) -- one added byte and the waiver lapses, the gate
#     goes red, and a human re-reads the file and re-records the digest.
#     TRACKEDNESS IS VERIFIED, not assumed: an allowlist git cannot
#     confirm is read as EMPTY, so a `touch`ed copy waives nothing
#     (`_personal_path_allowlist_is_tracked`).
#
# THERE IS NO SECOND WAIVER, AND NO RULE WAIVER AT ALL. A signed
# sentinel (`approved.md` / `*-approved.md`) used to be forgiven by a
# RULE that asked four questions of content -- a sibling `.asc`, an
# armoured signature body over a size floor, an `Approved-By`
# fingerprint a tracked row granted, and not-a-symlink. Every one of
# those answers is TRANSPLANTABLE by anyone who can write a file: the
# sidecar is not bound to the document, and the Owner's fingerprint is
# published. So `docs/leak-approved.md` with a copied `.asc` was waived
# while the same bytes under another name were a finding -- exemption
# by NAME in a content-shaped costume, which is the one class this rule
# exists to remove. It waived ZERO hits on this tree (CENSUS below), so
# deleting it moved no row and closed the surface outright.
#
# A signature this gate can actually VERIFY would be a second waiver
# earned by content; that needs `gpg` and a keyring, and it is
# `.claude/plans/PLAN-186-FOLLOWUP-sentinel-gpg-verification.md`. Until
# it lands, a frozen signed artifact carrying a home path is waived the
# same way everything else is: by a row pinned to its digest -- and a
# signature freezes that digest, so the row cannot go stale behind
# anyone's back.
#
# The rule NEVER prints a matched LINE — its findings land in a PUBLIC CI log,
# and a gate that quotes the leak it found is a second copy of it. It prints
# `file:line`, which is what a human needs to go and look.
#
# THAT RULE APPLIES TO THE GATE'S OWN OUTPUT, at one choke point. Everything
# this rule prints that it did not compose itself — a waiver REASON, an
# allowlist path outside the repo, an ignored CLI token, the REASON an
# OSError carries — goes through `_personal_path_safe`, which runs the
# rule's own predicate over the string and replaces it wholesale when it
# names a home directory. Two of those fatal prints were interpolating
# `_oserror_reason(exc)` RAW until the text lane of round 20 injected an
# error whose diagnostic carried a home path and watched it print at rc 2;
# an exhaustive-sounding sentence beside four safe call sites is how the
# fifth stays unnoticed. There is ONE deliberate exception and it is not a
# print: the row offered by `--emit-personal-path-rows`, which the parser
# has to read back, is built from `hit.rel` under two explicit refusals --
# see `_personal_path_safe`. Four separate
# print sites were found leaking by the pair-rail (round cure-1, P2 x3); they
# were four instances of one shape, so the cure is one predicate at the
# boundary, not four redactions. A contaminated waiver reason is ALSO refused
# at parse time, so it never reaches a printer at all.
#
# A tracked SYMLINK is scanned as what git stores: the TARGET STRING. Not
# doing so was a false negative with a one-line trigger (rail round cure-1,
# P1) — `is_file()` follows the link, so a dangling link read as "absent" and
# a resolvable one had someone else's file scanned in its place, while the
# `/Users/<name>/…` in the committed link payload was never looked at.
#
# FAIL-CLOSED ON INPUT (CLAUDE.md §4): an allowlist that exists and cannot be
# read or DECODED (a single non-UTF-8 byte used to raise through the CLI as a
# traceback carrying the absolute checkout path — rail round cure-1, P2), and
# an in-scope file that exists and cannot be read, are both fatal
# (rc 2) — an unverified scan is not a clean one. That fatal names the file the
# way every other line of this rule does — repo-relative, NEVER absolute:
# `str(OSError)` embeds `filename`, and on an operator machine that filename is
# the very `/Users/<name>/...` this rule exists to keep out of a public log
# (`_oserror_reason` below is what strips it; measured, cured,
# controlled). A file that is TRACKED but
# ABSENT from the worktree is skipped: absence is not unreadable input. Bytes
# that are not valid UTF-8 are REPLACED, never skipped, so "the guard could not
# parse it" cannot read as "the guard found nothing".
#
# DECLARED BLIND SPOTS (a rule that names what it cannot see):
#   * a path split across two lines, or assembled from fragments;
#   * the Windows form, and the `-home-<name>-` slug form (the latter would
#     fire on ordinary hyphenated prose such as `-home-page-`);
#   * a HYPHENATED owner in the SLUG form only: `-Users-dev-jane-repo` reads
#     as owner `dev`, a placeholder, and is missed (pair-rail round cure-2,
#     P2 — DECLARED, not cured). Reading further would mean treating
#     `-Users-runner-work-repo` as owner `runner-work`, which is not on the
#     placeholder list, so the fail-closed reading fires on the documented
#     placeholder style the rule exists to protect. The direct form
#     `/Users/dev-jane/` IS caught (that regex accepts `-`), and a document
#     carrying the slug almost always carries the direct form too;
#   * a relative `Users/<name>/...` with no leading slash;
#   * a personal path glued straight onto a preceding word character
#     (`x/Users/<name>`) — the price of not firing on every `.../home/<page>`
#     URL route, a shape docs legitimately carry;
#   * TWO undecodable bytes in one line: the second reading removes every
#     U+FFFD at once, so `/Us<FF>ers/<FF>name` is covered, but a byte that
#     decodes to a VALID character (rather than to U+FFFD) is not modelled at
#     all — this rule is a leak detector, not an adversary-proof filter;
#   * THE INDEX IS ENUMERATED AND THE WORKTREE IS READ. `git ls-files`
#     names the entries; the bytes come from the filesystem. Stage a
#     leaking blob and then overwrite or delete it in the worktree and
#     the scan sees the clean copy, while `git commit` lands the staged
#     one -- and a row pins the WORKTREE bytes, not necessarily the bytes
#     being landed (pair-rail round 1, P1, both lanes). DECLARED, not
#     cured: closing it means reading blobs through `git cat-file`
#     instead of the filesystem, which changes what every digest in the
#     shipped allowlist means. It is also the pre-existing behaviour of
#     RULE 1 and of `FileWalker`, and in CI -- where this gate runs -- the
#     index and the worktree are the same tree by construction;
#   * the owner class is a DELIMITER class, so an owner segment that
#     CONTAINS one of the delimiters (`<`, `>`, a quote, a comma, a
#     closing bracket) is still read short. That set is exactly what
#     keeps `/Users/<user>/` clean without a special case, and the trade
#     is deliberate: the alternative fires on the documented placeholder
#     style this rule exists to encourage;
#   * `/./Users/<name>/...` is missed -- the lookbehind rejects a leading
#     `.`, which is what keeps the rule off `../home/x` and
#     `example.com/home/index`. Same family as the relative form above;
#   * a row waives the WHOLE file AT ONE DIGEST: two leaks added in the
#     same edit are waived together by the row that records that edit's
#     sha256. What a row can no longer do is waive the NEXT edit -- the
#     digest is the thing a reviewer re-approves;
#   * a FROZEN artifact is waived by a row like anything else. There is
#     no rule waiver to earn, so the operator cost of a signed sentinel
#     that really does carry a home path is one row -- and because a
#     signature freezes the bytes, that row's digest cannot lapse
#     without the signature lapsing first;
#   * a symlink's TARGET is scanned as text, so a link to a file whose
#     CONTENT carries a personal path is judged by the link, not by that
#     file — the file itself is scanned on its own if it is tracked and in
#     scope, and out of scope it was never this rule's subject;
#   * TRACKED is not COMMITTED. The allowlist's trackedness is
#     verified, so a file git never heard of waives nothing — but an
#     UNCOMMITTED edit to a tracked allowlist still grants. That edit
#     is a `git diff`, which is the reviewable artifact the claim was
#     always about, and refusing it would make "add the row, run the
#     gate, commit it in the same change" impossible in that order.
#
# CENSUS — the table most "MEASURED" notes below are derived from. Two are
# not, and say so where they stand: the case-variant fold and the NUL
# refusal each name their own instrument, because each counts a different
# population than this table does. A note that cites this table when it
# measured something else would be the drift this block exists to stop.
#
# It is the SOURCE, not the only occurrence: a note repeats a figure
# from it inline (the 242 waived files) because the
# sentence is unreadable without it. Each says CENSUS beside the number
# so a reader knows where it came from, and a claim of exclusivity that
# the file itself contradicts is worse than none (pair-rail round 3, P3).
#
# Every "MEASURED" note below cites this table instead of carrying a figure
# of its own. Three of them had already drifted by the time a cross-vendor
# review read the module (S344): two docstrings were a generation behind the
# disk, while sibling comments in this same file carried the current ones. A
# number written in six places is six chances to be wrong; written once,
# with the command beside it, it is one thing to re-run.
#
# Measured 2026-09-04 (S344) at 056e11c, on the tree with this rule applied
# and staged. From the repository root:
#
#   git ls-files -z | tr '\0' '\n' | grep -c .                      -> 5222
#   git ls-files 'docs/*' '.claude/plans/*' | wc -l                 -> 2171
#   git ls-files 'docs/*' '.claude/plans/*' \
#     | grep -cE '(^|/)(approved|.*-approved)\.md$'                 ->   75
#   ... the same list, counting those with `test -f "$f.asc"`       ->   75
#   git ls-files 'docs/*' '.claude/plans/*' | grep -c '\.asc$'      ->   82
#
# The rest is this module's own predicates driven over `git ls-files`, plus
# one `python3 .claude/scripts/check_contamination.py` for the verdict line:
#
#   * in-scope `.asc`: 0 are symlinks, 0 carry a hit line, and every one
#     decodes to the same 147-byte signature body;
#   * in-scope sentinels: 75, and NONE of them carries a hit. That is the
#     number that made the DELETION of the rule waiver free: 34 of them
#     passed the four checks the deleted rule asked, and not one of those
#     34 had anything to be forgiven. A waiver that forgives nothing is
#     an attack surface with no user;
#   * in-scope files carrying a hit: 242 — each one waived by a row whose
#     digest matches, with 0 unwaived, 0 digest mismatches, 0 stale and
#     0 malformed rows;
#   * what the REMOVED name exemptions were hiding, measured on this tree
#     before they were removed: of 54 in-scope `OWNER-*.sh` scripts, 0
#     carry a hit (they name the checkout through `$HOME` and `$CEO_REPO`,
#     never literally); of 75 in-scope sentinels, 0 carry a hit; 0 in-scope
#     paths are symlinks; 0 in-scope regular files carry a binary suffix.
#     EVERY exemption this rule ever had waived exactly nothing — so the
#     uniform scan and the deleted `_SKIP_SUFFIXES` branch move ZERO rows,
#     and the waived count is the same 242 before and after;
#   * in-scope paths hitting on their own NAME: 0. Tracked paths that are
#     undecodable in scope: 0;
#   * hit lines over every tracked file: 4238 under the widened `\w` pair
#     and 4237 under the ASCII one. The ONE line they disagree on is the
#     non-ASCII example spelled out in the `_PERSONAL_PATH_HOME_RE` note
#     below — a line under `.claude/scripts/`, which this rule never scans,
#     so the widening moves no ROW.
#
# These figures AGE with the tree; they are dated and pinned to a base so a
# reader can tell staleness from drift. Re-run the commands before quoting
# them, and change them HERE — not in the prose that cites them.

#: Only these two trees. The rule deliberately does NOT widen the walk — the
#: term rule already sees everything else.
_PERSONAL_PATH_SCOPE = (".claude/plans/", "docs/")

#: `/Users/<seg>` and `/home/<seg>`. The lookbehind keeps the rule off URL
#: routes and nested directories (`example.com/home/index`, `/srv/home/x`):
#: a home path is written from a path root, so it is preceded by `/`, a quote,
#: a space or a line start — never by a word character.
#:
#: BOTH separators are `/+`, not `/` (pair-rail land round 1, P2):
#: `/Users//<owner>/repo` is the same directory to every filesystem and
#: every shell, and it read CLEAN (reproduced: `False` against `True` on
#: the single-slash form). A matcher that a doubled separator walks past is
#: a matcher with a one-keystroke bypass. MEASURED over every tracked file
#: before it was chosen: the widened pair and the v3 pair answer
#: IDENTICALLY on all 4238 hit lines — zero disagreements, in scope or out
#: — so this closes a hole and moves no row.
#:
#: The owner class is `\w` (UNICODE), not `[A-Za-z0-9]` (pair-rail round 1,
#: P2). An ASCII-only class was wrong in BOTH directions: `/Users/<é>…` did
#: not match at all, and — worse — a name whose ASCII PREFIX is a placeholder
#: was TRUNCATED to it (`/Users/devé/` read as owner `dev`, which the
#: placeholder set forgives), so a real owner was reported clean. Matching
#: the whole segment is what makes the placeholder comparison meaningful.
#: MEASURED before choosing it — the CENSUS above carries both
#: counts. The two pairs answer identically over every tracked file
#: but ONE line: the non-ASCII example this note spells out, which
#: is the very class the widening exists to catch. That line lives
#: under `.claude/scripts/`, out of this rule's scope, so the
#: correction moves no ROW on this tree.
#: The owner class is a DELIMITER class, not a character whitelist
#: (pair-rail round 1, P1). `[\w.\-]+` stopped at the first character it
#: did not know, and a segment read HALFWAY is worse than one not read at
#: all: `/Users/dev+zzfake/repo` was truncated to owner `dev`, which is on
#: the placeholder list, so a real owner was reported CLEAN. Round 1 of the
#: previous version fixed the ASCII half of exactly this and the class was
#: still a whitelist, so the shape came back for `+`, `$`, `~` and every
#: other legal filename character. Enumerating the legal ones is the thing
#: that keeps failing; the class now takes everything up to a character
#: that ENDS a path segment in prose.
#:
#: `<` and `>` are in the delimiter set, and that is what keeps the
#: documented placeholder style clean without a special case: in
#: `/Users/<user>/x` the very first character after the literal is a
#: delimiter, so there is no match at all — not a match the placeholder
#: list has to forgive.
#:
#: MEASURED over every tracked file, BOTH matchers together, before it
#: was chosen: 20 lines change answer (4238 -> 4258), ALL of them out of
#: this rule's scope, and every one is the widening being RIGHT — a shell
#: `${USER_NAME}` expansion, regex sources spelling `/Users/[A-Za-z]...`,
#: and byte fixtures in this rule's own tests. ZERO in-scope
#: disagreements, so zero rows move. The cost is declared: a regex or a
#: shell variable written inside `docs/` now needs a row, which is the
#: recoverable failure this rule is built around.
#:
#: BOTH matchers are built from ONE delimiter set, below. Round 2 of the
#: rail found the reason that matters: the first cure widened the DIRECT
#: matcher and left the SLUG one a whitelist, so `-Users-dev+<real>-repo`
#: still read as owner `dev` — the same defect, one regex over. Two
#: matchers of the same thing that can be edited apart WILL be edited
#: apart; the shared constant is what makes that impossible rather than
#: unlikely.
_PERSONAL_PATH_SEG_DELIMS = r"""/\s"'`,;:)\]}<>|"""
#: The lookbehind excludes a WORD character, a dot and a tilde -- the
#: forms that make the slash part of something else (`x/Users/`,
#: `./Users/`, `~/Users/`). It used to exclude `-` as well, which made
#: a unified-diff DELETION line invisible: `-/Users/<real>/work` in a
#: frozen diff read clean while the `+` line beside it was a hit
#: (pair-rail round 4, P1). A hyphen does not attach a path to a
#: preceding word the way a letter does, and MEASURED over every
#: tracked file the removal moves ZERO lines.
#:
#: The ROOT TOKEN is CASE-FOLDED; nothing else is. On the default
#: case-insensitive macOS volume this rule was written for,
#: `/users/<owner>/x` names the same directory as `/Users/<owner>/x`,
#: and the exact-case matcher answered False for it -- a decision made
#: by SPELLING rather than by content, which is the failure this whole
#: rule exists to remove (pair-rail round 16, P2). `/USERS/`, `/Home/`
#: and `/HOME/` were the same hole.
#:
#: Written as explicit per-character classes rather than a pattern-wide
#: `re.IGNORECASE`. The honest reason is LOCALITY, not behaviour: a flag
#: would not change what is captured (the owner segment keeps its own
#: case either way) and the delimiter class holds no letters. The two
#: spellings are NOT equivalent, and saying they were was the second
#: overstatement in this note: `re.IGNORECASE` folds U+017F LATIN SMALL
#: LETTER LONG S onto `s` and the explicit `[Ss]` class does not
#: (measured: ignorecase True, explicit False -- text lane, round 23).
#: The explicit classes are therefore the NARROWER spelling as well as
#: the local one, and a letter entering either class would widen the
#: fold silently. The classes put the fold where a
#: reader can see its extent. (Stated wrongly here once, as a
#: behavioural claim, and caught by the round-17 text lane.)
#:
#: MEASURED before shipping. The comparison only means something on the
#: tree WITHOUT the cure: run over a tree that already folds, the
#: instrument compares the fold against itself and answers zero for
#: free. `measure-case-variant-root.py` therefore reads its matcher from
#: the tree it is pointed at, and the number quoted here is its run
#: against the PRE-cure derivation -- see the CENSUS block above and
#: EVIDENCE section J, which also carry the two different in-scope
#: counts (the census counts with git pathspec globs, the instrument
#: with this rule's own scope predicate) so neither reads as a
#: correction of the other. The finding: the fold moves ZERO lines.
#:
#: `/users/me`, `/Users/me/x` and `/users/alice/x` stay clean because
#: `me` and `alice` are PLACEHOLDERS. That is why the estimate of five
#: false positives does not reproduce -- FOUR of those lines are the HTTP
#: route `/users/me` (three in one document, one in a frozen transcript)
#: and the fifth is a `HOME/CLAUDE_PROJECT_DIR` example, which is not a
#: home path at all. The estimate was made against an implementation
#: that had lost the placeholder filter.
#:
#: The narrower form proposed first -- fold only when the owner segment
#: matches the repo private-term pattern -- was measured and REJECTED,
#: with the reason stated exactly. `build_pattern()` never matches
#: nothing: it always carries `_PLACEHOLDER_TERMS`. In an adopter, with
#: no `scripts/contamination-terms.txt`, it reduces TO those three
#: alternatives -- so the narrowed fold would fire only for an owner
#: segment spelled like one of the three `_PLACEHOLDER_TERMS` at the top
#: of this file, and never for a real handle. (Those three are NOT
#: written out here: this module must not match the pattern it builds,
#: and quoting them made it do exactly that -- caught by
#: `test_delivered_module_is_not_itself_contaminated`, which is the
#: PLAN-183 W2 A7 guard doing its job on this very edit.)
#: A cure that fires only where its author declared a
#: terms file is a fail-open by configuration: the class this file
#: closes, not one it adds.
#: The leading run is ONE literal `/` guarded by a fixed-width
#: lookbehind, not `/+`. `/+` after a lookbehind can restart at every
#: slash of a run, and each restart rescans the rest of it: `"/" * 16000`
#: followed by a home path took 1.833 s on the machine that measured it,
#: and 8 000 took 0.48 s -- quadratic, on a line a committed file can
#: carry (mechanism lane, round 21, A1; reproduced). The slash is
#: CONSUMED and there is ONE lookbehind, `(?<![\w.~]/)`, which carries
#: the same start condition the old pattern did: it refuses the position
#: only when the character before that slash makes it part of something
#: else AND there is no second slash -- which is exactly what
#: `(?<![\w.~])/+` said. (An earlier draft of this note described two
#: lookbehinds and quoted a `(?<=/)` that the final pattern does not
#: have, because the slash was made a literal so the mask could keep
#: replacing it -- text lane, round 23.) Verified as a DIFFERENTIAL over
#: every in-scope tracked file plus the boundary forms `/Users/x`,
#: `//Users/x`, `a/Users/x`, `a//Users/x`, `./Users/x`, `~/Users/x`:
#: zero disagreements. The match now begins at the LAST slash of the
#: run rather than the first, which is why the `/` is CONSUMED and not
#: asserted -- `_personal_path_mask_rel` replaces the match, and a mask
#: that dropped the slash would rewrite the path it masks.
_PERSONAL_PATH_HOME_RE = re.compile(
    r"/(?<![\w.~]/)(?:[Uu][Ss][Ee][Rr][Ss]|[Hh][Oo][Mm][Ee])/+([^"
    + _PERSONAL_PATH_SEG_DELIMS + "]+)"
)

#: The harness slug form (`/` replaced by `-`), e.g. a project state directory
#: named `-Users-<name>-<repo>`. `-` separates segments here, so it cannot be
#: part of one: the capture is lazy up to the next `-`. `-+` for the same
#: reason the two above are `/+`: the slug of `/Users//<owner>` is
#: `-Users--<owner>`, and it read clean. Same differential, same answer:
#: zero disagreements over every tracked file.
#:
#: The owner class is the SHARED delimiter set plus `-`, which is this
#: form's own separator. Built from the same constant as the direct
#: matcher (pair-rail round 2, P1): widening one and not the other left
#: `-Users-dev+<real>-repo` reading as the placeholder `dev`.
#:
#: The TERMINATOR is that same class, and it took a second round to be
#: (mechanism lane, round 20). It used to be `(?:-|$)` -- a hyphen or the
#: end of the line -- so any ordinary punctuation after the owner hid the
#: whole slug: `~/.claude/projects/-Users-<owner>/memory/`,
#: `docs/-Users-<owner>/note.md` and a quoted `"-Users-<owner>"` all read
#: CLEAN while `-Users-<owner>-repo` was a hit. The class the capture
#: cannot CONTAIN and the class it may END at are the same class, which
#: is the only spelling of this that has no third case.
#:
#: MEASURED over 2 189 in-scope tracked files and 1 744 389 lines before
#: it shipped (`measure-slug-terminator.py`): the widening alone moved SIX
#: lines, all six the elided `-Users-<ellipsis>` in prose about the slug
#: families. That elision is what the placeholder list is FOR, so the
#: Unicode ellipsis joined it beside the ASCII spelling, and the pair
#: together move ZERO lines.
#: The root token folds here for the same reason and in the same way as
#: in the direct matcher above: a slug is derived from a path, so a
#: case-variant path yields a case-variant slug, and one matcher folding
#: while its twin did not is how `-Users-dev+<real>-repo` got through
#: once already (round 2, P1). Both fold, from the same reasoning.
_PERSONAL_PATH_SLUG_RE = re.compile(
    r"-[Uu][Ss][Ee][Rr][Ss]-+([^" + _PERSONAL_PATH_SEG_DELIMS
    + r"-]+?)(?=[-" + _PERSONAL_PATH_SEG_DELIMS + r"]|$)"
)

#: Home-directory owner segments that are NEUTRAL PLACEHOLDERS, not people.
#: Docs and tests are supposed to use these, so flagging them would punish the
#: correct behaviour and push authors toward worse examples. Every entry is a
#: generic word or a CI/system account; adding a real handle here would make
#: this list the contamination it guards against (the PLAN-183 W2 A7 shape).
#: `git ls-files -s` renders a symlink with this mode. It is the ONLY
#: authority this rule accepts on whether an entry is a link, because the
#: filesystem is not one: under `core.symlinks=false` git materialises a
#: mode-120000 entry as a REGULAR FILE whose content is the target string,
#: so `Path.is_symlink()` answers False for a link: the link's TARGET
#: STRING would be scanned as ordinary content on one checkout and as a
#: link on another (pair-rail round 1, P1). Asking git
#: also removes the check/use race: the classification and the read no
#: longer come from two separate filesystem answers.
_PERSONAL_PATH_LINK_MODE = "120000"

#: The index modes this rule knows how to turn into bytes: a regular
#: file, an executable file, and a symlink (whose blob is its target
#: string). ANY OTHER mode -- today the 160000 gitlink, tomorrow
#: whatever git adds -- is refused by name rather than skipped: a
#: gitlink in scope opened as a directory, yielded no blob, and still
#: counted as a file the walk had seen, so the scan reported clean
#: without reading it (pair-rail round 3, P1). A mode this rule cannot
#: read is an unverified entry, not a clean one.
_PERSONAL_PATH_BLOB_MODES = frozenset({"100644", "100755", "120000"})

#: How many ancestors the allowlist symlink walk will examine before it
#: gives up -- and giving up is a REFUSAL, never a fall-through.
_PERSONAL_PATH_ANCESTOR_CAP = 64

#: `O_NOFOLLOW` where the platform has it. A regular-file read opens with
#: it, so 'this is not a link' is decided by the SAME syscall that hands
#: back the inode — not by an `is_symlink()` a moment earlier that
#: something could invalidate before the read (pair-rail round 1, P1).
_PERSONAL_PATH_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)

#: `open(O_RDONLY)` on a FIFO BLOCKS until a writer connects, so the
#: `fstat` that classifies the inode is never reached and the scan hangs
#: until an outer CI timeout instead of returning a verdict (pair-rail
#: round 3, P2; measured, still blocked at 25 s). `O_NONBLOCK` makes the
#: open return immediately for a non-regular inode, which is then
#: rejected by the fstat that already existed. It is a no-op for the
#: regular files this rule actually reads.
_PERSONAL_PATH_O_NONBLOCK = getattr(os, "O_NONBLOCK", 0)

#: Compared lowercased.
_PERSONAL_PATH_PLACEHOLDERS = frozenset({
    "...",        # an elided segment, `/Users/.../project`
    "\u2026",     # the SAME elision as one character, `-Users-\u2026-repo`
    "a", "b", "x", "y", "u",
    "adopter", "alice", "bob", "carol",
    "ci", "runner", "ubuntu", "root",       # CI / container accounts
    "dev", "devuser", "example", "home", "me", "someone", "tmp",
    "test", "testuser", "user", "username", "you", "youruser",
})

#: The tracked allowlist, NEXT TO this file, under `.claude/scripts/`.
#:
#: IT DOES NOT YET TRAVEL WITH A FRESH INSTALL, and saying that it did was
#: a claim about code that is not there (pair-rail round 2, P2):
#: `scripts/install.sh` copies `*.sh`, `*.py` and `*.yaml` out of this
#: directory and nothing copies a `.txt`. An adopter therefore gets the
#: rule and no allowlist, which the rule reads as EMPTY — fail-closed, so
#: their own findings are reported rather than silently waived, but it is
#: not the delivery this line used to promise. `install.sh` is CANONICAL,
#: so the fix is a signed ceremony (`scripts-fu`), not this free pack.
#: It must be TRACKED to waive anything: the gate confirms that with
#: git before it parses a row, and an untracked copy reads as empty.
_PERSONAL_PATH_ALLOWLIST_REL = (
    ".claude/scripts/contamination-personal-path-allowlist.txt"
)

#: An explicitly EMPTY value for a path option. `argparse` distinguishes
#: omission (`default=None`) from `--root ""`, and the module then read
#: both by truthiness: the empty string silently selected the DEFAULT, so
#: the gate scanned the checkout this file lives in and returned green
#: while the operator believed it had scanned somewhere else (pair-rail
#: round 4, P1). An empty path is not a path; it is a usage error.
_PERSONAL_PATH_EMPTY_OPTION = (
    "%s was given an EMPTY value; an empty path is not a path, and "
    "treating it as \"not given\" would silently scan the default "
    "instead"
)

#: A reason an emitted row still carries. Refused by the parser so a row
#: pasted from `--emit-personal-path-rows` cannot be committed unreasoned.
_PERSONAL_PATH_UNREASONED = "REPLACE-WITH-REASON"

#: Cap on what the CLI prints per section — the shipped allowlist waives
#: hundreds of frozen artifacts, and a wall of them hides the one that matters.
_PERSONAL_PATH_PRINT_CAP = 20

#: EVERY alternative of BOTH regexes above requires one of these literals
#: UP TO THE CASE OF THE ROOT TOKEN, so a line holding none of them -- in
#: any case spelling -- cannot match either. That is why the fast path is
#: `_PERSONAL_PATH_LITERAL_RE` below and no longer `str.__contains__`:
#: since v4.9 the matchers fold the root, and an exact-case containment
#: test would reject `/users/<owner>/x` before either matcher ran -- the
#: fast path would have become a filter of its own, which is exactly what
#: this note promised it never would (round 17, text lane: the paragraph
#: here described code that had already been replaced). It remains a
#: SEMANTIC EQUIVALENCE, not a performance claim — the framework makes no
#: speed claim (CLAUDE.md §1), and pair-rail round 1 (P2) removed the
#: measured one that stood here. A differential test drives the predicate
#: and a regex-only reference over the same corpus and demands the same
#: answer.
_PERSONAL_PATH_LITERALS = ("/Users/", "/home/", "-Users-")

#: The fast path asks the SAME question as the matchers, so it folds the
#: root token the same way -- and it is DERIVED from the tuple above
#: rather than written out a second time. A second spelling of the same
#: authority that silently omits the fold is the false-green shape this
#: file removes wherever it finds it: before this, the fast path rejected
#: `/users/<owner>/x` by exact case and the folded matchers below were
#: never reached (pair-rail round 16, P2).
_PERSONAL_PATH_LITERAL_RE = re.compile("|".join(
    "".join(
        "[%s%s]" % (char.upper(), char.lower()) if char.isalpha()
        else re.escape(char)
        for char in literal
    )
    for literal in _PERSONAL_PATH_LITERALS
))

#: Seconds a SINGLE in-scope file may spend in the line matcher before
#: the scan refuses it. The matcher is linear per line since the cure
#: above, so this is not the fix for that defect and does not claim to
#: be: it is the boundary for the general case, an arbitrary tracked file
#: fed to a regex engine. Fail-CLOSED, like every other unreadable INPUT
#: here (CLAUDE.md section 4): the file is REFUSED, rc 2, never reported
#: clean. Generous on purpose -- the largest in-scope file in this
#: repository scans in well under a second -- because a deadline that
#: fires on a slow runner turns a gate into a coin toss.
_PERSONAL_PATH_FILE_BUDGET_S = 30.0

#: What `bytes.decode(errors="replace")` leaves where a byte was not valid
#: UTF-8. Its presence makes the line's FIRST reading untrustworthy — see
#: `line_is_personal_path_hit`.
#:
#: DECLARED FALSE POSITIVE (pair-rail round 4, P2): U+FFFD is itself a
#: valid character, so a name or a line that CONTAINS one deliberately is
#: read here as a decoding failure. By the time this rule sees a name,
#: `FileWalker` has already decoded it with `errors="replace"`, so the
#: two cases are no longer distinguishable at this layer. The direction
#: is the safe one -- the gate REFUSES rather than waives, and the
#: remedy it prints (rename the file) is correct for both -- and the fix
#: means carrying raw bytes through the walker, which is a change to the
#: older rule's contract.
_PERSONAL_PATH_REPLACEMENT = "�"

#: Every mark a decoder can leave where it could not read a byte: U+FFFD
#: from `errors="replace"`, and the lone surrogates U+DC80-U+DCFF from
#: `errors="surrogateescape"` — which is what the OS hands back for a
#: symlink target and what the symlink branch used to feed this matcher
#: RAW (pair-rail land round 1, P1: the surrogate is not U+FFFD, so the
#: second reading never fired and `/Users/dev<0xFF>zzfake/` read as the
#: placeholder `dev`). One regex, so a new marker is added in one place.
_PERSONAL_PATH_UNDECODABLE_RE = re.compile("[\ufffd\udc80-\udcff]")


