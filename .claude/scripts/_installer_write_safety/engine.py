#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-installer-write-safety.py — PLAN-185 W0, 5th pass (FAIL-CLOSED DISCOVERY).

Census of two classes of unsafe write in ``scripts/**/*.sh``:

  symlink-follow  a path is decided by a DEREFERENCING file test (-e/-f/-d/...,
                  anything but -L/-h) and is also WRITTEN.  Both a dangling and
                  a resolved symlink at that path make the write land OUTSIDE
                  the tree the installer was given.  (CWE-59 / CWE-61)

  sed-interp      an operator-controlled value is interpolated into a sed/awk
                  substitution without escaping that substitution's delimiter
                  (and & / backslash on the replacement side).  The value
                  aborts the command; because ``>`` created the destination
                  first, the abort leaves a 0-byte file that the EXISTS-skip
                  branch then treats as installed forever.

WHY THIS FILE WAS REWRITTEN TWICE (verdict, then DISCOVERY)
-----------------------------------------------------------
Passes 1..3 worked by *implicit denylist*: they enumerated the syntactic forms
they could recognise and credited ``guardado``/``nao-aplicavel`` to everything
that did not match.  Every form nobody thought of was born fail-OPEN, so every
review round found more of them — 8, then 7, then 9, then 10, then 16.

The 4th pass inverted the VERDICT rule: safety became a THEOREM provable only
by a named form in ALLOWLIST below.  The 5th round of review then returned 16
findings of the SAME class, because inverting the verdict is only half the
job.  DISCOVERY was still a denylist: a site existed only where a recognised
file test or a bare ``sed`` name appeared, so ``test -a "$dst"``,
``/usr/bin/sed``, ``$1``, ``>& "$dst"`` and ``sort -o "$dst"`` produced no site
AT ALL.  An invisible site is worse than a wrongly-cleared one: nothing in the
output says it exists.

This pass makes discovery fail-closed as well.  A command is PROVEN read-only
only if its name is in PROVEN_READONLY and it opens no file for output;
everything else whose operands or redirections carry an expansion is a
CANDIDATE WRITE (class ``write-candidate``) that must be proven safe like any
other site.  A test expression the model cannot walk to the end, an
``eval``/``source``/``exec``, and an unparseable file are sites too.  The
census therefore reports what it does NOT understand, which is the only way a
"no finding" line can mean anything.

Three structural consequences, all deliberate:

0. **Volume went up ~5x, and that is the correct direction.**  The baseline is
   a RATCHET over what the instrument can see, not a list of reviewed defects;
   PLAN-185 W1/W2 is what turns real sites into ``guardado``.  A small baseline
   here would only mean discovery was narrow again.

1. **Reachability analysis is gone.**  The old matcher spent ~600 lines asking
   "is the write reachable when the link dangles?", and answered
   ``nao-aplicavel`` whenever it could not tell.  That question was wrong on
   its own terms: the threat model covers the RESOLVED link too (``-e`` true,
   ``cp`` writes through it, clobbering a file outside the target), so the
   branch a dangling link happens to take never decided safety.  An argument
   about control flow can only make a site MORE dangerous, never safe, so no
   such argument can produce a non-blocking verdict here.  Safety comes from a
   dominating ``-L`` guard or from there being no write at all — nothing else.

2. **Parsing is fail-closed.**  Analysis runs on a real (small) shell lexer and
   a block-scope stack, not on regexes over raw text.  Unbalanced quotes, an
   unterminated heredoc, a block stack that does not close, an unreadable file
   — any of these makes the WHOLE FILE unparseable: it emits a synthetic
   blocking ``parse`` site and every site inside it is ``indeterminado``.

SITE CLASSES
------------
  symlink-follow  a dereferencing file test decides a path that is written.
  sed-interp      a value is interpolated into a stream-editor script.
  write-candidate a command that is not PROVEN read-only touches an expansion.
  parse           the file could not be read or modelled at all.

VERDICTS
--------
  nao-aplicavel   PROVEN: nothing writes the tested path (form a3 / n0).
  guardado        PROVEN: a non-dereferencing guard dominates every write
                  (forms a1, a2), or the interpolation is provably escaped or
                  validated (forms b1, b2, b3).
  desguardado     PROVEN dangerous: a write exists with no dominating guard,
                  or a raw interpolation with no escaping anywhere.
  indeterminado   NOT PROVEN either way.  Blocks.

Both ``desguardado`` and ``indeterminado`` are BLOCKING and must appear in the
tracked baseline.  Being in the baseline means a human LOOKED — never that the
form is tolerated.

EXIT CODES
----------
  0  every blocking site is recorded in the baseline and every baseline entry
     still matches a site.
  1  drift: a blocking site is missing from the baseline, or a baseline entry
     matches nothing (rot), or --strict is on and any site is indeterminate.
  2  the census found ZERO sites.  This FAILS by design: zero means the search
     is broken, not that the corpus is clean.

Python >= 3.9, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
_INSTRUMENT_PACKAGE = Path(__file__).resolve().parent


def instrument_sha256() -> str:
    """Digest the entry point and every shipped implementation component.

    A census number published without it is not reproducible: the same corpus
    judged by two versions of this script is two different measurements, and
    this instrument has changed under a reader at least once.
    """
    try:
        package = _INSTRUMENT_PACKAGE
        entry_point = package.parent / "check-installer-write-safety.py"
        members = [entry_point] + sorted(package.glob("*.py"))
        digest = hashlib.sha256()
        for member in members:
            payload = member.read_bytes()
            name = ("entry/" + member.name if member == entry_point
                    else "package/" + member.name)
            digest.update(name.encode("utf-8"))
            digest.update(b"\x00")
            digest.update(str(len(payload)).encode("ascii"))
            digest.update(b"\x00")
            digest.update(payload)
            digest.update(b"\x00")
        return digest.hexdigest()
    except OSError:
        return "unavailable"

DEFAULT_SCAN_ROOT = "scripts"
DEFAULT_BASELINE_REL = ".claude/scripts/data/installer-write-safety-baseline.txt"
EXCLUDED_REL_PREFIXES = ("scripts/tests/",)

CLASS_SYMLINK = "symlink-follow"
CLASS_SED = "sed-interp"
CLASS_PARSE = "parse"
# Fail-closed DISCOVERY (5th pass).  A command that is not PROVEN read-only and
# touches an expansion is a candidate write, whether or not anything ever
# tested that path.  Without this class the census could only see writes that
# some `-e`/`-f` test had already pointed at, so the forms nobody tested were
# invisible rather than indeterminate.
CLASS_WRITE = "write-candidate"

VERDICT_GUARDED = "guardado"
VERDICT_UNGUARDED = "desguardado"
VERDICT_INDETERMINATE = "indeterminado"
VERDICT_NA = "nao-aplicavel"

BLOCKING_VERDICTS = (VERDICT_UNGUARDED, VERDICT_INDETERMINATE)

# --------------------------------------------------------------------------
# THE ALLOWLIST.  A site may leave the blocking set ONLY through one of these
# named forms.  Each id is asserted by a positive control in
# .claude/scripts/tests/test_check_installer_write_safety.py: the form with its
# guard present must come out non-blocking, and the same fixture with the guard
# removed or mutated must come out blocking, naming the path.
# --------------------------------------------------------------------------
ALLOWLIST = (
    ("a1-nofollow-test-dominates",
     "A -L/-h test on the same path, whose taken branch aborts at the branch's "
     "own level, on an earlier logical line whose scope path is a prefix of "
     "every write's scope path."),
    ("a2-nofollow-helper-dominates",
     "A call to a helper DEFINED IN THE SAME FILE whose body satisfies a1 for "
     "$1 and whose symlink branch returns a NON-ZERO literal, called as "
     "`helper <path> || <abort>` (or aborting the process outright).  The "
     "helper's body is inspected; its NAME is never evidence."),
    ("a3-no-write-to-operand",
     "Every occurrence of the tested path (and of its one-level aliases) in the "
     "analysis region is at a position proven not to write: a file test, an "
     "argument of a PROVEN_READONLY command, a read redirection, or the SOURCE "
     "operand of a known writer.  A single occurrence the model cannot place "
     "voids the proof."),
    ("a4-confinement-predicate-dominates",
     "A dominating call to a predicate DEFINED EXACTLY ONCE in the scanned "
     "corpus -- another file is fine -- whose BODY applies a "
     "non-dereferencing check to a path built from its own positional "
     "parameters and has an explicit refusal path, called in a modelled "
     "refusal polarity, AND whose arguments COVER the write destination: "
     "either the destination itself or the (root, relpath) pair it is "
     "concatenated from.  Cross-file resolution never credits a NAME -- an "
     "ambiguous or missing definition fails, and so does an argument list "
     "that does not bind the destination."),
    ("b1-delimiter-escape-dominates",
     "Every assignment to the interpolated variable in the region escapes the "
     "delimiter OF THIS SUBSTITUTION (plus & and backslash on the replacement "
     "side) with a replacement that actually inserts a backslash, and at least "
     "one of those assignments dominates the use."),
    ("b2-closed-charset-validated",
     "A dominating validation aborts unless the value matches a literal closed "
     "character class that excludes this substitution's delimiter, &, "
     "backslash and newline."),
    ("b3-literal-only",
     "The substitution contains no expansion at all, or every assignment to the "
     "interpolated variable in the region is a literal free of the delimiter, "
     "& and backslash."),
    ("b4-inline-escape-substitution",
     "The interpolation is a single command substitution that escapes THIS "
     "substitution's delimiter in place (plus & and backslash), with a "
     "replacement that actually inserts a backslash."),
    ("n0-no-interpolation",
     "The stream-editor invocation's script is fully literal and contains no "
     "substitution with an expansion in it."),
)
ALLOWLIST_IDS = frozenset(i for i, _ in ALLOWLIST)

# Reason codes attached to indeterminate verdicts.  Every one of them means
# "the model does not cover this shape", never "this looked fine".
R_PARSE = "i-parse-failed"
R_UNREADABLE = "i-file-unreadable"
R_OCCURRENCE = "i-unmodeled-occurrence"
R_GUARD_NOT_DOM = "i-guard-not-dominating"
R_SCRIPT_DYNAMIC = "i-script-not-literal"
R_SCRIPT_UNPARSED = "i-script-unparsed"
R_CMD_SUBST = "i-command-substitution"
R_ESCAPE_UNPROVEN = "i-escape-unproven"
R_AWK_EXPANSION = "i-awk-program-interpolated"
R_GUARD_STALE = "i-guard-value-rebound"
R_TEST_UNMODELED = "i-unmodeled-test-form"
R_CANDIDATE = "i-write-candidate-unproven"
R_OPAQUE = "i-opaque-command"
R_PRED_AMBIGUOUS = "i-predicate-definition-ambiguous"
R_PRED_ARG_UNBOUND = "i-predicate-arg-unbound"

# --------------------------------------------------------------------------
# Lexer
# --------------------------------------------------------------------------



__all__ = [name for name in globals() if not name.startswith("__")]
