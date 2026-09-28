#!/usr/bin/env python3
"""re-pin-codex.py — generate the Codex CLI re-pin pack (ADR-182 §5).

It EMITS a pack; it never applies one.

Given a target ``@openai/codex`` version, the tool:

1. resolves the main package and its platform artifact through ``npm view``
   against the public registry named explicitly (``--registry`` and
   ``--@openai:registry`` = ``https://registry.npmjs.org/``, whatever an
   ``.npmrc`` says; the sentinel records it and ``dist.tarball``). The platform
   artifact is the optional-dependency alias
   ``npm:@openai/codex@<ver>-<platform>`` (ADR-182 §5 step 2), and the alias
   must name exactly the requested version;
2. downloads the platform tarball with ``npm pack`` into a private temporary
   directory, or takes a local tarball with ``--offline-from`` (``npm view``
   still runs: the registry integrity is the thing the tarball is checked
   against). npm's own cache and logs point into that temporary directory,
   which is removed on return. The tarball is read ONCE, into memory, from one
   descriptor opened without following a symlink and checked to be a regular
   file; steps 3 and 4 both run on those bytes, so a file swapped or rewritten
   on disk afterwards cannot split what is checked from what is pinned;
3. checks the tarball's sha512 against the registry ``dist.integrity``. On a
   mismatch it stops before anything is written;
4. streams the single payload member at the manifest's recorded relative path
   out of the tarball (never written to disk) and sha256s it. Members are
   keyed where npm's extractor puts them (npm 11: pacote extracts with
   node-tar ``strip: 1``): the first raw path segment is dropped whatever it
   is (``package``, ``other``, or the ``.`` of ``./package/…``), then ``./``,
   repeated ``/`` and letter case are normalised. An absolute or ``..``
   member name anywhere, a second member that lands on the payload path, a
   payload that is not a regular file, and a link that lands on the payload
   path or one of its parent directories, or points at the payload path, are
   all refused. The two readers (Python's ``tarfile`` and npm's node-tar)
   must see the SAME member list, so the list is accepted only in the one
   header shape whose decoding the tool models for both: the tarball is
   decompressed once (bounded, single gzip member, nothing after the gzip
   stream); every 512-byte header is plain POSIX ustar (magic
   ``ustar\\0`` + ``00``), with a checksum both readers parse to the same
   value and that matches the unsigned sum, an octal size field, printable
   ASCII names (name, prefix, link name), and a type among regular file,
   directory, hard link and symlink (only a regular file has a size or a
   body; only a link has a link name; only a directory name ends in
   ``/``); the member list ends at the first all-zero block and every byte
   after it is zero; and Python's
   ``tarfile`` must list exactly the members that header walk lists. Any
   other header (an extension header of any kind, another type, another
   magic, a malformed field) is refused by name. The registry artifact
   (0.156.1, measured) uses regular files only;
5. writes a NEW pack directory (an existing path is refused) holding:

   - ``codex-cli-pin-manifest.json.new``: schema 1 with ``package_version``,
     the PLATFORM ``npm_integrity`` and the per-triple ``sha256``;
   - ``codex-cli-pin.txt.new``: the live pin's lines before the range,
     unchanged, plus a dated paragraph and the range. The range is widened
     upper-only, and only when the version
     falls outside it. The human rationale comes from ``--pin-note FILE``;
     without it the paragraph carries a ``TODO(owner)``;
   - ``<mold basename>``: the ceremony script. The mold's body is copied
     verbatim except the regions the generator owns (per grammar, below). A
     guard is added after the mold's EXIT trap that refuses a real run while
     a ``TODO(owner)`` remains in the sentinel or in the pin;
   - ``pin-<tag>-approved.md``: the sentinel draft. The measured digests, the
     new range and the sha256 of the live canonicals and of the two ``.new``
     files are filled in; the human sections are ``TODO(owner)``;
   - constants-block grammar only, when the mold's ``PACK_FILES`` lists them:
     ``rehearse-pin-<tag>.sh`` (the mold's rehearsal, body verbatim, header
     regenerated) and ``README.md`` (provenance, measured values, file list).

It never touches ``.claude/governance/``, never installs a CLI, never signs and
never commits. Applying the pack is the Owner's ceremony (the emitted script).

Two mold grammars are modelled, chosen by shape and parsed fail-closed; any
other shape is refused BY NAME (that pack is then cloned by hand):

- heredoc grammar (the ``PLAN-189/codex-pin-0155`` generation): five value
  lines ``D``/``SENT_LIVE``/``NEW_RANGE``/``NEW_VERSION``/``NEW_SHA``, each
  exactly once in the expected shape, and a ``git commit ... <<DELIM``
  message. The generator owns those lines, the commit heredoc and the header.
  The mold must run the ADR-182 §5 step-4 verification AFTER it applies the
  manifest and before it commits: ``check_pair_rail.py --verify-codex-pin``
  against the installed binary, then a check for ``"status": "verified"``;
- constants-block grammar (modelled on the hand-built PLAN-193 pack,
  ``codex-pin-0156``, which this tree may not carry yet): ONE block from
  ``# --- constantes`` to ``# --- fim constantes`` of ``KEY=VALUE`` lines
  holding exactly the keys of ``_CONST_RENDERED`` (values the
  generator renders: plan, tag, versions, range bounds, publication date,
  triple, digests, ``BASE_*_SHA256`` = sha256 of the live canonicals,
  ``SRC_*_SHA256`` = sha256 of the rendered ``.new`` files, ``GA_TAG`` from
  ``--ga-tag``, ``D`` fixed to ``.claude/plans/$PLAN/codex-pin-$PACK_TAG``)
  and of ``_CONST_PASSTHROUGH`` (copied verbatim), none assigned again outside
  the block. ``PACK_FILES`` may list only files this tool emits. The body must
  check the frozen ``.new`` copies against ``SRC_PIN_SHA256`` and
  ``SRC_MAN_SHA256``, apply the manifest, run ``verify_pin`` (whose body calls
  ``--verify-codex-pin``), die unless it exits 0 and require ``verified`` with
  the pinned sha256, in that order, before the plumbing commit. The mold must
  sit at ``.claude/plans/<PLAN>/codex-pin-<PACK_TAG>/``. Its rehearsal must
  read the constants from its pack's ``OWNER-PIN-SIGN.sh`` and name no npm
  platform other than the one of the mold's ``TRIPLE``. The generator owns
  the block's values, the header and the guard; the generated header carries
  no version, digest or tag literal, because the rehearsal refuses one
  outside the block.

In both grammars the files the mold reads (``SRC_PIN``/``SRC_MAN``) and writes
(``DST_PIN``/``DST_MAN``) must be the ones this tool emits and targets, and no
version, digest or pack-path literal may survive outside the regions the
generator owns: a mold that carries version-specific text in its body is
refused rather than copied stale. ``DRY`` (the switch the guard reads) is set
by ONE ``DRY=...`` line at column 0, or by ONE ``case ... in`` / ``esac``
block at column 0 with one ``<pattern>) DRY=0 ;;`` arm and one
``<pattern>) DRY=1 ;;`` arm whose pattern names ``--dry-run``; no other line
assigns it. A single-command step anchor (the manifest apply, the
``verify_pin`` run, the plumbing commit) may end in one
``|| die "<message>"`` whose message runs no command; ``|| true`` or any
other suffix is not the anchor.

The mold is never older than the newest pack. Packs are ranked by the
``package_version`` of the ``codex-cli-pin-manifest.json.new`` beside each
``.claude/plans/PLAN-*/codex-pin*/OWNER-PIN-SIGN.sh`` (grammar-independent).
``--mold`` must pin the newest version, and every other mold at that version
must parse too; otherwise the run is refused and names the newest mold.
Building from an older mold would silently drop whatever the newer pack
hardened. ``newest_mold()`` is the one predicate; ``check-substrate-drift.py``
calls it for its recommendation.

The pack's plan is named, never inherited from the mold: ``--plan PLAN-NNN``
(or ``--pack-dir``) is required, and ``.claude/plans/PLAN-NNN-*.md`` must
exist (an orphan ``PLAN-NNN/`` subdirectory fails the plan schema,
``PLAN-SCHEMA.md``); a missing ``PLAN-NNN/`` is created with the pack (and
removed again if the write fails). A constants-block pack must go to
``.claude/plans/PLAN-NNN/codex-pin-<tag>`` (its script derives that dir). The
tag is THIS TOOL's rule, not a repo convention: ``X.Y.0`` -> ``XY``,
``X.Y.Z`` -> ``XY-Z`` (``0156``, ``0156-1``). A hand-built pack may differ:
the PLAN-193 pack pins 0.156.1 under the tag ``0156``. A tag already
used under ``.claude/plans`` (a ``codex-pin-<tag>`` directory or a
``pin-<tag>-approved.md``) is refused, which also catches two versions that
share a tag (``1.23.0`` and ``12.3.0``); so is an existing pack that already
pins the target version. A ``--dry-run`` writes nothing and skips these two
checks, so it can re-measure an existing pack.

Maintainer-only. ``scripts/install.sh`` copies every ``.claude/scripts/*.py``
into an adopter repository, so this file reaches adopters; there it refuses
(exit 2) because neither ``install.sh`` nor ``upgrade.sh`` delivers
``.claude/governance/`` or the pack molds.

Declared residual: the payload path is copied from the pinned manifest, and
the tool checks only that the new tarball holds one regular member there.
Whether the new version's launcher (``bin/codex.js`` of the main package)
still runs that path is NOT checked; ``--verify-codex-pin`` hashes the same
manifest path, so the blind spot is shared. The generated sentinel says so.

Usage (``X.Y.Z`` = the target release; ``<newest mold>`` = the
``OWNER-PIN-SIGN.sh`` of the newest pack, which ``check-substrate-drift.py``
names)::

    python3 .claude/scripts/re-pin-codex.py X.Y.Z --plan PLAN-NNN --mold <newest mold>
    python3 .claude/scripts/re-pin-codex.py X.Y.Z --plan PLAN-NNN --mold <newest mold> \\
        --ga-tag vA.B.C          # constants-block mold: the tag the re-pin follows
    python3 .claude/scripts/re-pin-codex.py X.Y.Z --plan PLAN-NNN --mold <...> --dry-run
    python3 .claude/scripts/re-pin-codex.py X.Y.Z --plan PLAN-NNN --mold <...> \\
        --offline-from ./openai-codex-X.Y.Z-<platform>.tgz --pin-note ./why.txt

Exit codes: 0 emitted (or dry-run computed); 2 input refused (version,
manifest, pin, mold, ``--offline-from``, output path — including one that
cannot be written); 3 verification failed (registry or tarball data
inconsistent); 4 infrastructure (npm absent or failing, timeout, any other
filesystem error). No other exit code is used: a filesystem error that no
step names is reported as 4, never as a traceback.

Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import errno
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "@openai/codex"
GENERATOR = ".claude/scripts/re-pin-codex.py"
MANIFEST_REL = ".claude/governance/codex-cli-pin-manifest.json"
PIN_REL = ".claude/governance/codex-cli-pin.txt"
MANIFEST_OUT = "codex-cli-pin-manifest.json.new"
PIN_OUT = "codex-cli-pin.txt.new"
TODO_MARK = "TODO(owner)"

EXIT_INPUT = 2
EXIT_VERIFY = 3
EXIT_INFRA = 4

#: The registry every npm call names explicitly (never ~/.npmrc's choice):
#: the sentinel records it, so the signed reproduction runs against the
#: registry that was measured.
NPM_REGISTRY = "https://registry.npmjs.org/"
#: Both flags: a ``@openai:registry`` line in an .npmrc outranks ``registry``
#: for this scoped package, so the scope is pinned too.
NPM_REGISTRY_ARGS = ("--registry=" + NPM_REGISTRY, "--@openai:registry=" + NPM_REGISTRY)
#: Pack molds, relative to ``.claude/plans`` (the same glob the drift
#: detector used to walk).
MOLD_GLOB = "PLAN-*/codex-pin*/OWNER-PIN-SIGN.sh"
NPM_VIEW_TIMEOUT = 120
NPM_PACK_TIMEOUT = 1800
# Cap on the tarball read into memory. The 0.156.0 darwin-arm64 platform
# tarball measured 131,567,699 bytes (2026-09-22).
TARBALL_MAX_BYTES = 1 << 30
# Decompressed-size cap (a gzip bomb stops here). Measured: the real 0.156.1
# darwin-arm64 platform tarball is 131,652,985 bytes gzipped and 326,415,360
# bytes of tar (2026-09-23).
UNPACKED_MAX_BYTES = 1 << 30

# npm platform suffix -> launcher targetTriple. Mirror of
# check_pair_rail._codex_target_triple (the host -> triple map).
PLATFORM_TRIPLE: Dict[str, str] = {
    "darwin-arm64": "aarch64-apple-darwin",
    "darwin-x64": "x86_64-apple-darwin",
    "linux-x64": "x86_64-unknown-linux-musl",
    "linux-arm64": "aarch64-unknown-linux-musl",
    "win32-x64": "x86_64-pc-windows-msvc",
    "win32-arm64": "aarch64-pc-windows-msvc",
}

_MANIFEST_KEYS = frozenset({"schema", "package_version", "npm_integrity", "payloads"})
_SEMVER_RE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
_RANGE_RE = re.compile(r">=([0-9]+\.[0-9]+\.[0-9]+),<([0-9]+\.[0-9]+\.[0-9]+)")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_SRI512_RE = re.compile(r"sha512-[A-Za-z0-9+/]{86}==")
_PACK_DIR_RE = re.compile(r"\.claude/plans/(PLAN-[0-9]{3})/[a-z0-9][a-z0-9._-]*")
_PLAN_RE = re.compile(r"PLAN-[0-9]{3}")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
# Registry data is untrusted: only a plain https tarball URL reaches the sentinel.
_TARBALL_URL_RE = re.compile(r"https://[A-Za-z0-9.-]+/[A-Za-z0-9._~@%+/-]+\.tgz")

# Mold grammar (the value lines the generator owns, each exactly once).
_OWNED_SHAPES: Dict[str, "re.Pattern[str]"] = {
    "D": re.compile(r"\.claude/plans/[A-Za-z0-9._/-]+"),
    "SENT_LIVE": re.compile(r'"\$D/pin-[a-z0-9-]+-approved\.md"'),
    "NEW_RANGE": re.compile(r"'>=[0-9]+\.[0-9]+\.[0-9]+,<[0-9]+\.[0-9]+\.[0-9]+'"),
    "NEW_VERSION": re.compile(r"""'"package_version": "[0-9]+\.[0-9]+\.[0-9]+"'"""),
    "NEW_SHA": re.compile(r"'[0-9a-f]{64}'"),
}
# Lines the mold must carry verbatim: what it reads is what this tool emits,
# what it writes is what this tool targets.
_REQUIRED_LINES = (
    'SRC_PIN="$D/' + PIN_OUT + '"',
    'SRC_MAN="$D/' + MANIFEST_OUT + '"',
    "DST_PIN=" + PIN_REL,
    "DST_MAN=" + MANIFEST_REL,
)
# Names the injected guard and the generated commit message rely on (``DRY``
# is checked by ``_dry_definition``: it has two accepted shapes).
_REQUIRED_DEFS = (
    re.compile(r"^SENT="), re.compile(r"^die\(\) *\{"), re.compile(r"^HEAD_SHA="),
)
# ``DRY``, the switch the injected guard reads, in one of two shapes: ONE
# ``DRY=...`` line at column 0, or ONE ``case ... in`` / ``esac`` block at
# column 0 (no other column-0 code line inside it) whose arms
# ``<pattern>) DRY=0 ;;`` and ``<pattern>) DRY=1 ;;`` each appear once, the
# ``DRY=1`` arm's pattern naming ``--dry-run`` and the ``DRY=0`` arm's not.
# No other code line may assign ``DRY``. The shape is textual: what the
# other arms do (the PLAN-193 mold's ``*)`` arm exits) is not checked; an
# unset ``DRY`` makes the guard's ``"$DRY"`` abort under ``set -u``.
_DRY_LINE_RE = re.compile(r"DRY=.*")
_CASE_OPEN_RE = re.compile(r"case .+ in")
_CASE_CLOSE_RE = re.compile(r"esac")
_DRY_ARM_RE = re.compile(r" +([^ ()][^()]*)\) DRY=([01]) ;;")
# A single-command step anchor may carry ONE trailing failure handler that
# dies: ``<command> || die "<message>"``. The message may expand ``$NAME`` or
# ``${NAME}`` but runs no command (no backquote, no ``$(``). Any other suffix
# (``|| true``, a second command) is not the anchor and is refused.
_OR_DIE = r'(?: \|\| die "(?:[^"`$\\]|\$[A-Za-z_{])*")?'
# ADR-182 §5 step 4, in this order (code lines, stripped): apply the new
# manifest, verify the INSTALLED binary against it, require "verified".
_APPLY_MAN_RE = re.compile(r'cp "\$SRC_MAN" "\$DST_MAN"' + _OR_DIE)
_VERIFY_PIN_RE = re.compile(
    r'python3 \.claude/hooks/check_pair_rail\.py --verify-codex-pin '
    r'"\$\(command -v codex\)"(?: .*)?')
_VERIFIED_RE = re.compile(r"""grep -q '"status": "verified"' .+\|\|.*\bdie\b.*""")
GRAMMAR_HEREDOC = "heredoc grammar"
GRAMMAR_CONSTANTS = "constants-block grammar"
_SET_E_RE = re.compile(r"set -euo pipefail\s*")
_HEREDOC_RE = re.compile(r"git commit\b.*<<\s*([A-Za-z_][A-Za-z0-9_]*)\s*")
_TRAP_RE = re.compile(r"trap '.*' EXIT\s*")
_SAY_RE = re.compile(r'^say "([^"$`\\]*)"')
_ANY_VERSION_RE = re.compile(r"(?<![0-9.])[0-9]+\.[0-9]+\.[0-9]+(?![0-9])")
_HEX64_RE = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
_SRI_LITERAL_RE = re.compile(r"sha512-[A-Za-z0-9+/]{20,}")
_GA_TAG_RE = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")

# ---- The constants-block grammar (the PLAN-193 W2 generation) --------------
# Every version, digest and path the ceremony uses is a KEY=VALUE line of ONE
# delimited block; the body reads them as variables. The generator renders
# the values of _CONST_RENDERED, copies _CONST_PASSTHROUGH verbatim, and
# refuses any other key, a missing key, a key assigned twice or assigned
# again outside the block.
_CONSTANTS_BLOCK_RE = re.compile(r"# -{3,} *constantes *")
_CONSTANTS_END_RE = re.compile(r"# -{3,} *fim constantes *")
_CONST_LINE_RE = re.compile(r"([A-Z][A-Z0-9_]*)=(.*)")
_SEMVER_SHAPE = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
_SHA_SHAPE = re.compile(r"[0-9a-f]{64}")
_CONST_D_TEMPLATE = ".claude/plans/$PLAN/codex-pin-$PACK_TAG"
_CONST_RENDERED: Dict[str, "re.Pattern[str]"] = {
    "PLAN": _PLAN_RE,
    "PACK_TAG": re.compile(r"[a-z0-9][a-z0-9-]*"),
    "OLD_VER": re.compile(_SEMVER_SHAPE),
    "NEW_VER": re.compile(_SEMVER_SHAPE),
    "LOWER": re.compile(_SEMVER_SHAPE),
    "OLD_UPPER": re.compile(_SEMVER_SHAPE),
    "NEW_UPPER": re.compile(_SEMVER_SHAPE),
    "NEW_PUBLISHED": _DATE_RE,
    "TRIPLE": re.compile(r"[a-z0-9_]+(?:-[a-z0-9_]+)+"),
    "OLD_SHA": _SHA_SHAPE,
    "NEW_SHA": _SHA_SHAPE,
    "NEW_INTEGRITY": re.compile(r"'sha512-[A-Za-z0-9+/]{86}=='"),
    "BASE_PIN_SHA256": _SHA_SHAPE,
    "BASE_MAN_SHA256": _SHA_SHAPE,
    "SRC_PIN_SHA256": _SHA_SHAPE,
    "SRC_MAN_SHA256": _SHA_SHAPE,
    "GA_TAG": re.compile("v" + _SEMVER_SHAPE),
    "D": re.compile(re.escape(_CONST_D_TEMPLATE)),
}
_CONST_REPO_PATH = re.compile(r"\.claude/[A-Za-z0-9._/-]+")
_CONST_PASSTHROUGH: Dict[str, "re.Pattern[str]"] = {
    "COAUTHOR": re.compile(r"'[^'$`\\]*'"),
    "REMOTE_SLUG": re.compile(r"'[A-Za-z0-9._-]+/[A-Za-z0-9._-]+'"),
    "T2_NODE": re.compile(r"'[A-Za-z0-9._/:\[\]-]+'"),
    "SIGNERS": _CONST_REPO_PATH,
    "SIGNER_REGISTRY": _CONST_REPO_PATH,
    "GPG_VERIFY_LIB": _CONST_REPO_PATH,
    "SIGNER_REGISTRY_LIB": _CONST_REPO_PATH,
}
# Derived lines the body must carry verbatim (after the block).
_CONST_REQUIRED_LINES = (
    'SENT_LIVE="$D/pin-$PACK_TAG-approved.md"',
    'NEW_RANGE=">=$LOWER,<$NEW_UPPER"',
)
_PACK_FILES_RE = re.compile(r'PACK_FILES="([^"`\\]*)"')
# PACK_FILES token -> the role of the file the generator emits for it.
_PACK_FILE_ROLES: Dict[str, str] = {
    "$SENT_LIVE": "sentinel", "$SRC_PIN": "pin", "$SRC_MAN": "manifest",
    "$D/OWNER-PIN-SIGN.sh": "script", "$D/rehearse-pin-$PACK_TAG.sh": "rehearsal",
    "$D/README.md": "readme",
}
_PACK_FILES_REQUIRED = ("sentinel", "pin", "manifest", "script")
# The frozen-copy checks and ADR-182 §5 step 4 in this grammar: code lines
# (stripped), in this order, after the EXIT trap and before the plumbing
# commit. The two sha256 checks are what make a hand edit of a .new fail.
_CONST_STEP4: Tuple[Tuple["re.Pattern[str]", str], ...] = (
    (re.compile(r'\[ "\$\(sha256f "\$FZ/pin"\)" = "\$SRC_PIN_SHA256" \] \|\| die .+'),
     "check the frozen pin copy against $SRC_PIN_SHA256"),
    (re.compile(r'\[ "\$\(sha256f "\$FZ/man"\)" = "\$SRC_MAN_SHA256" \] \|\| die .+'),
     "check the frozen manifest copy against $SRC_MAN_SHA256"),
    (re.compile(r'cp "\$FZ/man" "\$DST_MAN"' + _OR_DIE),
     "apply the frozen manifest (cp \"$FZ/man\" \"$DST_MAN\")"),
    (re.compile(r'vrc=\$\(verify_pin "[^"]+"\)' + _OR_DIE), "run verify_pin after the apply"),
    (re.compile(r'\[ "\$vrc" = "0" \] \|\| \{.*\bdie\b.*\}'),
     "die unless verify_pin exits 0"),
    (re.compile(r'VERIFIED_PAYLOAD=\$\(check_verify_json "[^"]+" verified ok '
                r'"\$NEW_SHA" "\$NEW_SHA"\) \\'),
     "require status verified with the pinned sha256 (check_verify_json ... verified ok)"),
)
_CONST_DIES_RE = re.compile(r"\|\| \{.*\bdie\b.*\}")
_CONST_COMMIT_RE = re.compile(r'NEWC=\$\(git commit-tree "\$TREE" -p "\$HEAD_SHA" -F "\$MSG"\)'
                              + _OR_DIE)
_CONST_VERIFY_CALL_RE = re.compile(
    r'python3 \.claude/hooks/check_pair_rail\.py --verify-codex-pin '
    r'"\$\(command -v codex\)"(?: \\)?')
# The rehearsal reads its constants from the ceremony script of its own pack.
_REHEARSAL_SIGN_LINE = 'SIGN_SRC="$PACK_DIR/OWNER-PIN-SIGN.sh"'


class RePinError(Exception):
    """A refusal with its exit code (2 input, 3 verification, 4 infra)."""

    def __init__(self, rc: int, msg: str) -> None:
        super().__init__(msg)
        self.rc = rc


# ---------------------------------------------------------------------------
# Version, manifest and pin parsing (pure; fail-closed on input)
# ---------------------------------------------------------------------------


def parse_version(text: Any) -> Tuple[int, int, int]:
    """Parse a plain ``X.Y.Z`` release; pre-releases and ranges are refused."""
    m = _SEMVER_RE.fullmatch(text) if isinstance(text, str) else None
    if m is None:
        raise RePinError(
            EXIT_INPUT,
            f"version {text!r} is not a plain X.Y.Z release "
            "(pre-releases, tags and ranges are refused)",
        )
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def pack_tag(version: Tuple[int, int, int]) -> str:
    """This tool's rule: ``0.156.0`` -> ``0156``; ``0.156.2`` -> ``0156-2`` (slug ``[a-z0-9-]``)."""
    tag = f"{version[0]}{version[1]}"
    return tag if version[2] == 0 else f"{tag}-{version[2]}"


def load_manifest(path: Path) -> Dict[str, Any]:
    """Read the live ADR-182 manifest; refuse any shape the tool does not know."""
    return read_manifest(path)[0]


def read_manifest(path: Path) -> Tuple[Dict[str, Any], bytes]:
    """(parsed manifest, the raw bytes it was parsed from: ONE read)."""
    if not path.exists():
        raise RePinError(EXIT_INPUT, f"no {MANIFEST_REL}: the Codex re-pin is maintainer-only "
                                     "(install.sh and upgrade.sh deliver no .claude/governance/ "
                                     "to an adopter), run it in the framework checkout")
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except OSError as exc:
        raise RePinError(EXIT_INPUT, f"manifest unreadable: {MANIFEST_REL} "
                                     f"({type(exc).__name__})") from None
    except ValueError:
        raise RePinError(EXIT_INPUT, f"manifest is not JSON: {MANIFEST_REL}") from None
    return _check_manifest(data), raw


def _check_manifest(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise RePinError(EXIT_INPUT, "manifest is not a schema-1 object")
    if set(data) != _MANIFEST_KEYS:
        raise RePinError(EXIT_INPUT, "manifest keys differ from the schema-1 set "
                                     f"{sorted(_MANIFEST_KEYS)}: {sorted(data)}")
    parse_version(data.get("package_version"))
    payloads = data.get("payloads")
    if not isinstance(payloads, dict) or not payloads:
        raise RePinError(EXIT_INPUT, "manifest 'payloads' is empty or not an object")
    for triple, entry in payloads.items():
        ok = (isinstance(entry, dict) and set(entry) == {"path", "sha256"}
              and isinstance(entry.get("path"), str) and entry["path"]
              and isinstance(entry.get("sha256"), str)
              and _SHA256_RE.fullmatch(entry["sha256"]) is not None)
        if not ok:
            raise RePinError(EXIT_INPUT, f"manifest entry for {triple!r} is malformed")
    return data


def parse_pin(text: str) -> Tuple[List[str], str, str]:
    """Split the pin file into (comment prefix, lower, upper).

    The range must be the only non-comment line, and the last one.
    """
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise RePinError(EXIT_INPUT, f"{PIN_REL} is empty")
    for n, line in enumerate(lines[:-1], 1):
        if line.strip() and not line.lstrip().startswith("#"):
            raise RePinError(EXIT_INPUT, f"{PIN_REL} line {n} is neither a comment "
                                         "nor blank; the range must be the only "
                                         "non-comment line, and the last")
    m = _RANGE_RE.fullmatch(lines[-1])
    if m is None:
        raise RePinError(EXIT_INPUT, f"{PIN_REL} last line {lines[-1]!r} is not "
                                     "'>=X.Y.Z,<X.Y.Z'")
    return lines[:-1], m.group(1), m.group(2)


def plan_range(lower: str, upper: str,
               target: Tuple[int, int, int]) -> Tuple[str, bool]:
    """Return (new range, widened?). Widen-upper-only; the lower bound is fixed."""
    if target < parse_version(lower):
        raise RePinError(EXIT_INPUT, f"target is below the lower bound >={lower}; "
                                     "widen-upper-only cannot express it")
    if target < parse_version(upper):
        return f">={lower},<{upper}", False
    return f">={lower},<{target[0]}.{target[1] + 1}.0", True


def payload_member(manifest_rel_path: str, alias_key: str) -> str:
    """Map the manifest's node_modules-relative path to the tarball member.

    ``@openai/codex-darwin-arm64/vendor/<triple>/bin/codex`` installs from the
    platform tarball's ``package/vendor/<triple>/bin/codex``.
    """
    prefix = alias_key + "/"
    if not manifest_rel_path.startswith(prefix):
        raise RePinError(EXIT_INPUT, f"manifest path {manifest_rel_path!r} is not "
                                     f"under the platform package {alias_key!r}")
    inner = manifest_rel_path[len(prefix):]
    if not inner or any(p in ("", ".", "..") for p in inner.split("/")):
        raise RePinError(EXIT_INPUT, f"manifest path {manifest_rel_path!r} has an "
                                     "empty or relative segment")
    return "package/" + inner


# ---------------------------------------------------------------------------
# Registry and tarball (the only side-effecting reads)
# ---------------------------------------------------------------------------


def _npm_env(scratch: Path) -> Dict[str, str]:
    """npm's own state (cache, logs, update notifier) confined to ``scratch``.

    ``scratch`` lives inside the run's temporary directory, removed on return:
    a run (``--dry-run`` included) leaves no tarball in the user's npm cache.
    """
    env = dict(os.environ)
    env.update({"npm_config_cache": str(scratch / "npm-cache"),
                "npm_config_logs_dir": str(scratch / "npm-logs"),
                "npm_config_logs_max": "0",
                "npm_config_update_notifier": "false",
                "npm_config_fund": "false", "npm_config_audit": "false"})
    return env


def run_npm(npm: str, args: List[str], cwd: Path,
            timeout: int) -> "subprocess.CompletedProcess[str]":
    """Run npm with a fixed argv (never a shell) against ``NPM_REGISTRY``;
    timeouts are infrastructure. ``cwd`` is the run's temporary directory."""
    try:
        return subprocess.run(
            [npm] + args + list(NPM_REGISTRY_ARGS), cwd=str(cwd),
            env=_npm_env(cwd), capture_output=True,
            text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        raise RePinError(EXIT_INFRA, f"npm {args[0]} timed out after {timeout}s") from None
    except OSError as exc:
        raise RePinError(EXIT_INFRA, f"npm could not run ({type(exc).__name__})") from None


def npm_view(npm: str, spec: str, cwd: Path) -> Dict[str, Any]:
    """``npm view <spec> --json`` resolved to exactly one version document."""
    proc = run_npm(npm, ["view", spec, "--json"], cwd, NPM_VIEW_TIMEOUT)
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        code = ""
        try:
            code = str(_obj(_obj(json.loads(out)).get("error")).get("code", ""))
        except (ValueError, AttributeError):
            pass
        if code == "E404":
            raise RePinError(EXIT_INPUT, f"{spec} is not published in the registry")
        first = ((proc.stderr or "").strip().splitlines() or [""])[0][:200]
        raise RePinError(EXIT_INFRA, f"npm view {spec} failed rc={proc.returncode}: {first}")
    if not out:
        raise RePinError(EXIT_INPUT, f"npm view {spec} returned nothing (not published?)")
    try:
        doc = json.loads(out)
    except ValueError:
        raise RePinError(EXIT_INFRA, f"npm view {spec} returned non-JSON output") from None
    if not isinstance(doc, dict):
        raise RePinError(EXIT_VERIFY, f"npm view {spec} did not resolve to exactly one version")
    return doc


def _obj(value: Any) -> Dict[str, Any]:
    """A registry field as a dict; any other shape reads as empty."""
    return value if isinstance(value, dict) else {}


def resolve_registry(npm: str, version: str, platform: str,
                     cwd: Path) -> Dict[str, str]:
    """Resolve the main document and the platform artifact's integrity."""
    main = npm_view(npm, f"{PACKAGE}@{version}", cwd)
    if main.get("version") != version:
        raise RePinError(EXIT_VERIFY, f"registry answered version {main.get('version')!r} "
                                      f"for {PACKAGE}@{version}")
    alias_key = f"{PACKAGE}-{platform}"
    expected_alias = f"npm:{PACKAGE}@{version}-{platform}"
    alias = _obj(main.get("optionalDependencies")).get(alias_key)
    if alias != expected_alias:
        raise RePinError(EXIT_VERIFY, f"optionalDependencies[{alias_key!r}] = {alias!r}; "
                                      f"expected {expected_alias!r}")
    platform_spec = expected_alias[len("npm:"):]
    plat = npm_view(npm, platform_spec, cwd)
    if plat.get("name") != PACKAGE or plat.get("version") != f"{version}-{platform}":
        raise RePinError(EXIT_VERIFY, f"registry answered {plat.get('name')!r}@"
                                      f"{plat.get('version')!r} for {platform_spec}")
    integrity = _obj(plat.get("dist")).get("integrity")
    if not isinstance(integrity, str) or _SRI512_RE.fullmatch(integrity) is None:
        raise RePinError(EXIT_VERIFY, f"{platform_spec} dist.integrity is not a single "
                                      f"sha512 SRI: {integrity!r}")
    main_integrity = _obj(main.get("dist")).get("integrity")
    published = _obj(main.get("time")).get(version)
    latest = _obj(main.get("dist-tags")).get("latest")
    tarball_url = _obj(plat.get("dist")).get("tarball")
    return {
        "alias_key": alias_key,
        "platform_spec": platform_spec,
        "integrity": integrity,
        "main_integrity": main_integrity if isinstance(main_integrity, str) else "",
        "published": published if isinstance(published, str) else "",
        "registry_latest": latest if isinstance(latest, str) else "",
        "tarball_url": (tarball_url if isinstance(tarball_url, str)
                        and _TARBALL_URL_RE.fullmatch(tarball_url) else ""),
    }


def fetch_tarball(npm: str, spec: str, work: Path, dest: Path) -> Path:
    """``npm pack <spec>`` into ``dest`` (scripts ignored); exactly one tarball.

    npm runs in ``work`` (its cache and logs live there, see ``_npm_env``).
    """
    proc = run_npm(npm, ["pack", spec, "--pack-destination", str(dest), "--json",
                         "--ignore-scripts"], work, NPM_PACK_TIMEOUT)
    if proc.returncode != 0:
        first = ((proc.stderr or "").strip().splitlines() or [""])[0][:200]
        raise RePinError(EXIT_INFRA, f"npm pack {spec} failed rc={proc.returncode}: {first}")
    tarballs = sorted(p for p in dest.iterdir() if p.name.endswith(".tgz"))
    if len(tarballs) != 1:
        raise RePinError(EXIT_INFRA, f"npm pack left {len(tarballs)} tarballs, expected 1")
    return tarballs[0]


def read_tarball(path: Path, rc: int, what: str) -> bytes:
    """The tarball's bytes, read ONCE from ONE descriptor.

    Opened with ``O_NOFOLLOW`` (a symlink is refused) and ``O_NONBLOCK`` (a
    FIFO cannot hang the open); ``fstat`` on that same descriptor must say
    regular file. The integrity check and the member hash both run on the
    returned bytes, never on the path again. ``rc`` is the exit code of a
    refusal: input for ``--offline-from``, infrastructure for npm's own
    download.
    """
    flags = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
             | getattr(os, "O_BINARY", 0))
    try:
        fd = os.open(str(path), flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise RePinError(rc, f"{what} is a symlink; refused") from None
        raise RePinError(rc, f"{what} unreadable ({type(exc).__name__})") from None
    try:
        with os.fdopen(fd, "rb", buffering=0) as fh:
            st = os.fstat(fh.fileno())
            if not stat.S_ISREG(st.st_mode):
                raise RePinError(rc, f"{what} is not a regular file")
            if st.st_size > TARBALL_MAX_BYTES:
                raise RePinError(EXIT_VERIFY, f"{what} is larger than {TARBALL_MAX_BYTES} bytes")
            data = fh.readall()
    except OSError as exc:
        raise RePinError(rc, f"{what} unreadable ({type(exc).__name__})") from None
    if len(data) > TARBALL_MAX_BYTES:
        raise RePinError(EXIT_VERIFY, f"{what} grew past {TARBALL_MAX_BYTES} bytes while read")
    return data


def sri_sha512(data: bytes) -> str:
    """``sha512-<base64>`` of the tarball bytes."""
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")


def _refused_name(name: str) -> bool:
    """An absolute name or one with a ``..`` segment: refused outright (npm's
    extractor refuses a ``..`` path too; this tool is stricter on absolute)."""
    return name.startswith("/") or ".." in name.split("/")


def _member_key(raw: str) -> Optional[str]:
    """Where npm's extractor installs a member, case-folded; None = nowhere.

    Modelled on npm 11's pacote (``strip: 1``) and node-tar: the FIRST RAW
    ``/``-segment is dropped whatever it is (``package``, ``other``, even
    ``.`` in ``./package/x``, which therefore lands under ``package/``), the
    rest loses a leading ``/`` and is resolved (``./``, repeated ``/``). So
    ``other/x`` and ``package/x`` land on the same file. A name with nothing
    below its first segment is not extracted (None). Case-folded on every
    host: the pinned payload installs onto a case-insensitive filesystem by
    default (APFS), where two names that differ only in case land on ONE
    path; refusing that everywhere keeps the verdict independent of the host
    that generates the pack.
    """
    parts = raw.split("/")
    if len(parts) < 2:
        return None
    rest = "/".join(parts[1:]).lstrip("/")
    if not rest:
        return None
    norm = posixpath.normpath(rest)
    return None if norm in (".", "") else norm.casefold()


def _check_member(info: tarfile.TarInfo, target: str, parents: Set[str]) -> bool:
    """True when ``info`` lands on the payload path; raises on a refused shape."""
    if _refused_name(info.name):
        raise RePinError(EXIT_VERIFY, f"tarball member {info.name!r} is absolute or has a "
                                      "'..' segment; refused")
    key = _member_key(info.name)
    if key is None:
        return False
    if key == target:
        return True
    if not (info.islnk() or info.issym()):
        return False
    if key in parents:
        raise RePinError(EXIT_VERIFY, f"tarball link {info.name!r} sits on a parent "
                                      "directory of the payload path; refused")
    if info.islnk():
        # A hard link's target is another member name (its first segment is
        # stripped too, as the extractor does).
        if _refused_name(info.linkname) or _member_key(info.linkname) == target:
            raise RePinError(EXIT_VERIFY, f"tarball hard link {info.name!r} points at the "
                                          "payload path or out of the archive; refused")
    elif not info.linkname.startswith("/"):
        # A symlink's target is relative to the link's own installed directory.
        dest = posixpath.normpath(posixpath.join(posixpath.dirname(key), info.linkname))
        if dest.casefold() == target:
            raise RePinError(EXIT_VERIFY, f"tarball symlink {info.name!r} points at the "
                                          "payload path; refused")
    return False


def _gunzip_single(data: bytes) -> io.BytesIO:
    """The tarball's tar bytes: ONE gzip member, decompressed once, bounded
    by ``UNPACKED_MAX_BYTES``. A second gzip member or any byte after the
    gzip stream is refused (rc 3): the registry artifact has neither
    (measured on 0.156.1), and each is a place where two readers can
    disagree about what the archive holds."""
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = io.BytesIO()
    buf = data
    try:
        while not d.eof:
            chunk = d.decompress(buf, 1 << 24)
            buf = d.unconsumed_tail
            if not chunk and not buf:
                break
            out.write(chunk)
            if out.tell() > UNPACKED_MAX_BYTES:
                raise RePinError(EXIT_VERIFY, f"tarball unpacks past {UNPACKED_MAX_BYTES} "
                                              "bytes; refused")
    except zlib.error:
        raise RePinError(EXIT_VERIFY, "tarball unreadable (gzip stream corrupt)") from None
    if not d.eof:
        raise RePinError(EXIT_VERIFY, "tarball unreadable (gzip stream truncated)")
    if d.unused_data:
        raise RePinError(EXIT_VERIFY, "tarball carries bytes after its gzip stream (a "
                                      "second gzip member or trailing data); refused")
    out.seek(0)
    return out


#: The one tar header shape the tool accepts (C-R3M-01, closed by
#: construction rather than by listing divergences). For this shape the
#: node-tar bundled with npm 11.16 (7.5.15 ``header.js``/``parse.js``, read
#: 2026-09-23) and Python's ``tarfile`` decode every field that decides
#: WHERE bytes land identically: path (ustar prefix + name), type, size,
#: link name and checksum.
_TAR_BLOCK = 512
_TAR_MAGIC = b"ustar\x0000"
_TAR_TYPES = {b"0": "regular file", b"1": "hard link", b"2": "symlink", b"5": "directory"}
_TAR_LINK_TYPES = (b"1", b"2")
#: Octal digits, then only spaces or NULs. node-tar parses the checksum out
#: of 12 bytes (the field, the type byte and the start of the link name), so
#: a field whose digits run to its last byte parses differently there.
_TAR_OCTAL_RE = re.compile(rb"[0-7]+[ \x00]+")


def _tar_refuse(off: int, why: str) -> RePinError:
    return RePinError(EXIT_VERIFY, f"tar header at offset {off}: {why}; only plain POSIX ustar "
                                   "headers of a regular file, directory or link are accepted, "
                                   "the one shape both tar readers list identically — refused")


def _tar_octal(block: bytes, start: int, width: int, what: str, off: int) -> int:
    field = block[start:start + width]
    if not _TAR_OCTAL_RE.fullmatch(field):
        raise _tar_refuse(off, f"{what} field {field!r} is not octal digits followed by a "
                               "terminator")
    return int(field.rstrip(b" \x00"), 8)


def _tar_text(block: bytes, start: int, width: int, what: str, off: int) -> str:
    """The field up to its first NUL (both readers stop there), refused
    unless printable ASCII: one decoding, and no Unicode name that a
    normalising filesystem folds onto another."""
    text = block[start:start + width].split(b"\0", 1)[0]
    if any(b < 0x20 or b > 0x7E for b in text):
        raise _tar_refuse(off, f"{what} is not printable ASCII")
    return text.decode("ascii")


def _tar_header(block: bytes, off: int) -> Tuple[str, bytes, int, str]:
    """(path, type, size, link name) of ONE header, in the accepted shape."""
    if block[257:265] != _TAR_MAGIC:
        raise _tar_refuse(off, f"magic {block[257:265]!r} is not POSIX ustar")
    kind = block[156:157]
    if kind not in _TAR_TYPES:
        raise _tar_refuse(off, f"type {kind!r} (an extension header, or a member type the "
                               "tool does not model)")
    stored = _tar_octal(block, 148, 8, "checksum", off)
    if stored != 8 * 0x20 + sum(block[:148]) + sum(block[156:]):
        raise _tar_refuse(off, "checksum does not match the unsigned header sum")
    size = _tar_octal(block, 124, 12, "size", off)
    name = _tar_text(block, 0, 100, "name", off)
    # node-tar reads a 155-byte prefix when byte 475 is set, else 130 bytes;
    # tarfile reads up to the first NUL of 155, which then falls at <= 475.
    prefix = _tar_text(block, 345, 155 if block[475] else 130, "prefix", off)
    link = _tar_text(block, 157, 100, "link name", off)
    what = _TAR_TYPES[kind]
    if not name:
        raise _tar_refuse(off, "empty name")
    if kind != b"0" and size:
        raise _tar_refuse(off, f"a {what} with a size (only a regular file has a body)")
    if (kind in _TAR_LINK_TYPES) != bool(link):
        raise _tar_refuse(off, f"a {what} with{'out' if kind in _TAR_LINK_TYPES else ''} "
                               "a link name")
    path = f"{prefix}/{name}" if prefix else name
    if kind != b"5" and path.endswith("/"):
        raise _tar_refuse(off, f"a {what} whose name ends in '/'")
    return path, kind, size, link


def _walk_tar(raw: io.BytesIO) -> List[Tuple[int, str, bytes, int, str]]:
    """Every member header, walked block by block in the accepted shape. The
    list ends at the first all-zero block and every byte after it must be
    zero: ``tarfile`` stops listing there, while npm's extractor (node-tar,
    non-strict) skips a null or invalid block and installs what follows
    (C-R2M-04)."""
    end = raw.seek(0, io.SEEK_END)
    entries: List[Tuple[int, str, bytes, int, str]] = []
    off = 0
    while off < end:
        raw.seek(off)
        block = raw.read(_TAR_BLOCK)
        if len(block) < _TAR_BLOCK or block.count(0) == _TAR_BLOCK:
            raw.seek(off)
            nonzero = 0
            for chunk in iter(lambda: raw.read(1 << 20), b""):
                nonzero += len(chunk) - chunk.count(0)
            if nonzero:
                raise RePinError(EXIT_VERIFY, f"tarball carries {nonzero} non-zero byte(s) "
                                              f"after its member list (offset {off}): a member "
                                              "npm's extractor would install past a null or "
                                              "invalid block; refused")
            break
        path, kind, size, link = _tar_header(block, off)
        entries.append((off, path, kind, size, link))
        off += _TAR_BLOCK + -(-size // _TAR_BLOCK) * _TAR_BLOCK
        if off > end:
            raise RePinError(EXIT_VERIFY, f"tar member {path!r} runs past the end of the "
                                          "archive; refused")
    raw.seek(0)
    return entries


def _require_reader_parity(entries: List[Tuple[int, str, bytes, int, str]],
                           members: List[tarfile.TarInfo]) -> None:
    """Python's ``tarfile`` must list exactly the members the header walk
    lists (offset, path, type, size, link name); ``tarfile`` drops a
    directory's trailing ``/``."""
    walked = [(off, path.rstrip("/") if kind == b"5" else path, kind, size, link)
              for off, path, kind, size, link in entries]
    listed = [(m.offset, m.name, m.type, m.size, m.linkname) for m in members]
    if walked != listed:
        raise RePinError(EXIT_VERIFY, f"Python's tarfile lists {len(listed)} member(s) and the "
                                      f"header walk {len(walked)}, or the two differ in a "
                                      "path, type, size or link name: the tar readers would "
                                      "not see the same member list; refused")


def hash_member(data: bytes, member: str) -> Tuple[str, int]:
    """sha256 + size of ONE regular member, streamed; never written to disk."""
    target = _member_key(member)
    if target is None:
        raise RePinError(EXIT_INPUT, f"payload member {member!r} has no path below its "
                                     "top-level directory")
    parents: Set[str] = set()
    parent = posixpath.dirname(target)
    while parent:
        parents.add(parent)
        parent = posixpath.dirname(parent)
    raw = _gunzip_single(data)
    entries = _walk_tar(raw)
    try:
        with tarfile.open(fileobj=raw, mode="r:") as tf:
            members = tf.getmembers()
            _require_reader_parity(entries, members)
            matches = [m for m in members if _check_member(m, target, parents)]
            if len(matches) != 1:
                raise RePinError(EXIT_VERIFY, f"tarball holds {len(matches)} members that "
                                              f"land on {member!r} (first path segment "
                                              "dropped as npm extracts, './', repeated '/' "
                                              "and letter case normalised), expected exactly 1")
            info = matches[0]
            fh = tf.extractfile(info) if info.isreg() else None
            if fh is None:
                raise RePinError(EXIT_VERIFY, f"{member!r} is not a regular file in the "
                                              "tarball (link, directory or device)")
            h = hashlib.sha256()
            size = 0
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
                size += len(chunk)
            return h.hexdigest(), size
    except (tarfile.TarError, OSError, EOFError, zlib.error) as exc:
        raise RePinError(EXIT_VERIFY, f"tarball unreadable ({type(exc).__name__})") from None


# ---------------------------------------------------------------------------
# Mold parsing (fail-closed) and rendering
# ---------------------------------------------------------------------------


# The guard injected right after the mold's trap line. A mold that is itself
# a generated script carries it already: the parser recognises it (exact
# lines) as an owned region, so it is regenerated, never duplicated.
_GUARD = [
    f"# [{GENERATOR}] a justificativa humana do pack fica em {TODO_MARK}:",
    "# o run real recusa assinar enquanto restar um; o ensaio só avisa.",
    f"if grep -n '{TODO_MARK}' \"$SENT\" \"$SRC_PIN\" 2>/dev/null; then",
    f"  [ \"$DRY\" = \"1\" ] || die \"{TODO_MARK} pendente nos materiais (linhas acima)"
    " — escreva a justificativa antes de assinar\"",
    f"  printf '   AVISO: {TODO_MARK} pendente — o run real vai recusar\\n'",
    "fi",
]


def _find_one(body: List[str], pattern: "re.Pattern[str]", what: str,
              label: str = "mold") -> int:
    hits = [i for i, line in enumerate(body) if pattern.fullmatch(line)]
    if len(hits) != 1:
        raise RePinError(EXIT_INPUT, f"{label}: {what} appears {len(hits)} times, expected 1")
    return hits[0]


def _split_script(text: str, what: str) -> Tuple[List[str], int]:
    """(lines, index of 'set -euo pipefail'); only comments may precede it
    (the generator owns that header and regenerates it)."""
    lines = text.split("\n")
    if not lines[0].startswith("#!") or "bash" not in lines[0]:
        raise RePinError(EXIT_INPUT, f"{what}: first line is not a bash shebang")
    set_e = [i for i, line in enumerate(lines) if _SET_E_RE.fullmatch(line)]
    if not set_e:
        raise RePinError(EXIT_INPUT, f"{what}: no 'set -euo pipefail' line")
    start = set_e[0]
    for n in range(1, start):
        if lines[n].strip() and not lines[n].startswith("#"):
            raise RePinError(EXIT_INPUT, f"{what} line {n + 1}: code before 'set -euo "
                                         "pipefail' (the generator owns only comments there)")
    return lines, start


def parse_mold(text: str) -> Dict[str, Any]:
    """Split and validate the mold; returns the parts the renderer needs.

    The grammar is chosen by shape: a ``# --- constantes`` line selects the
    constants-block grammar, otherwise the heredoc grammar applies. Either
    way every rule is fail-closed.
    """
    lines, start = _split_script(text, "mold")
    if any(_CONSTANTS_BLOCK_RE.fullmatch(line) for line in lines):
        return _parse_constants_mold(lines, start)
    return _parse_heredoc_mold(lines, start)


def _parse_heredoc_mold(lines: List[str], start: int) -> Dict[str, Any]:
    body = lines[start:]
    owned: Dict[str, int] = {}
    for name, shape in _OWNED_SHAPES.items():
        idx = _find_one(body, re.compile(re.escape(name) + r"=.*"), f"{name}=")
        if shape.fullmatch(body[idx][len(name) + 1:]) is None:
            raise RePinError(EXIT_INPUT, f"mold line {start + idx + 1}: {name}= value "
                                         "has an unexpected shape")
        owned[name] = idx
    for required in _REQUIRED_LINES:
        if required not in body:
            raise RePinError(EXIT_INPUT, f"mold does not carry the line {required!r}")
    for pattern in _REQUIRED_DEFS:
        if not any(pattern.match(line) for line in body):
            raise RePinError(EXIT_INPUT, f"mold does not define {pattern.pattern!r}")
    _dry_definition(body, "mold")
    commit = _find_one(body, _HEREDOC_RE, "the 'git commit ... <<DELIM' line")
    delim = _HEREDOC_RE.fullmatch(body[commit]).group(1)
    ends = [j for j in range(commit + 1, len(body)) if body[j] == delim]
    if not ends:
        raise RePinError(EXIT_INPUT, f"mold: commit heredoc {delim!r} is never closed")
    trap = _find_one(body, _TRAP_RE, "the \"trap '...' EXIT\" line")
    guard_len = _previous_guard(body, trap)
    if not (max(owned.values()) < trap and trap + guard_len < commit):
        raise RePinError(EXIT_INPUT, "mold: expected value lines < trap < commit")
    _check_step4(body, commit)
    parts = {"grammar": GRAMMAR_HEREDOC, "shebang": lines[0], "start": start,
             "body": body, "owned": owned, "commit": commit, "commit_end": ends[0],
             "trap": trap, "guard_len": guard_len,
             "mold_version": body[owned["NEW_VERSION"]].split('"')[3]}
    _scan_stale(parts)
    return parts


def _const_refuse(msg: str) -> RePinError:
    return RePinError(EXIT_INPUT, f"mold ({GRAMMAR_CONSTANTS}): {msg}")


def _parse_constants_block(body: List[str], start: int
                           ) -> Tuple[int, int, Dict[str, Tuple[int, str]]]:
    """(block open index, block close index, KEY -> (index, value))."""
    opens = [i for i, line in enumerate(body) if _CONSTANTS_BLOCK_RE.fullmatch(line)]
    closes = [i for i, line in enumerate(body) if _CONSTANTS_END_RE.fullmatch(line)]
    if len(opens) != 1 or len(closes) != 1 or closes[0] < opens[0]:
        raise _const_refuse(f"the block must open once ('# --- constantes', found "
                            f"{len(opens)}) and close once after it ('# --- fim "
                            f"constantes', found {len(closes)})")
    known = dict(_CONST_RENDERED)
    known.update(_CONST_PASSTHROUGH)
    consts: Dict[str, Tuple[int, str]] = {}
    for i in range(opens[0] + 1, closes[0]):
        line = body[i]
        if not line.strip() or line.startswith("#"):
            continue
        m = _CONST_LINE_RE.fullmatch(line)
        if m is None:
            raise _const_refuse(f"line {start + i + 1} of the block is not KEY=VALUE")
        key, value = m.group(1), m.group(2)
        if key not in known:
            raise _const_refuse(f"unknown key {key} (line {start + i + 1}): this generator "
                                "models only " + ", ".join(sorted(known)))
        if key in consts:
            raise _const_refuse(f"{key} is assigned twice in the block")
        if known[key].fullmatch(value) is None:
            raise _const_refuse(f"line {start + i + 1}: {key}= value has an unexpected shape")
        consts[key] = (i, value)
    missing = sorted(set(known) - set(consts))
    if missing:
        raise _const_refuse("the block lacks " + ", ".join(missing))
    return opens[0], closes[0], consts


def _assigns(line: str, key: str) -> bool:
    """A code line that (re)assigns ``key``: ``KEY=``, ``KEY+=``, ``${KEY:=…}``,
    ``export/local/declare/readonly KEY=``, ``read``/``unset``/``printf -v KEY``."""
    if re.search(r"(?<![A-Za-z0-9_$])" + key + r"(?:\+|:)?=", line):
        return True
    return re.search(r"\b(?:read|unset|printf -v)\b[^#]*(?<![A-Za-z0-9_$])" + key
                     + r"(?![A-Za-z0-9_])", line) is not None


def _dry_definition(body: List[str], what: str) -> int:
    """Index of the line that completes the ``DRY`` definition, in one of the
    two shapes of ``_DRY_LINE_RE`` / ``_DRY_ARM_RE`` (see there); any other
    shape is refused by name (``what`` prefixes the message)."""
    def refuse(msg: str) -> RePinError:
        return RePinError(EXIT_INPUT, f"{what}: {msg}")

    code = [(i, line) for i, line in enumerate(body) if not line.lstrip().startswith("#")]
    assigning = [i for i, line in code if _assigns(line, "DRY")]
    if not assigning:
        raise refuse("no line defines DRY (the dry-run switch the guard reads)")
    top = [i for i in assigning if _DRY_LINE_RE.fullmatch(body[i])]
    if top:
        if top != assigning or len(top) != 1:
            raise refuse(f"DRY must be defined by ONE 'DRY=' line at column 0 and assigned "
                         f"nowhere else (lines {', '.join(str(i + 1) for i in assigning)} "
                         "of the body)")
        return top[0]
    arms = [i for i in assigning if _DRY_ARM_RE.fullmatch(body[i])]
    if arms != assigning or len(arms) != 2:
        raise refuse("DRY is assigned outside the two accepted shapes (one column-0 "
                     "'DRY=' line, or one case block with ONE '<pattern>) DRY=0 ;;' and "
                     "ONE '<pattern>) DRY=1 ;;' arm)")
    by_value = {_DRY_ARM_RE.fullmatch(body[i]).group(2): i for i in arms}
    if set(by_value) != {"0", "1"}:
        raise refuse("the case block must set DRY=0 in one arm and DRY=1 in the other")
    pat_dry = _DRY_ARM_RE.fullmatch(body[by_value["1"]]).group(1)
    pat_real = _DRY_ARM_RE.fullmatch(body[by_value["0"]]).group(1)
    if "--dry-run" not in pat_dry or "--dry-run" in pat_real:
        raise refuse("the DRY=1 arm's pattern must name --dry-run and the DRY=0 arm's "
                     "must not")
    opens = [i for i, line in code if _CASE_OPEN_RE.fullmatch(line) and i < min(arms)]
    if not opens:
        raise refuse("the DRY arms are not inside a 'case ... in' block at column 0")
    closes = [i for i, line in code if _CASE_CLOSE_RE.fullmatch(line) and i > opens[-1]]
    if not closes or max(arms) > closes[0] or any(
            line and not line[0].isspace() for i, line in code
            if opens[-1] < i < closes[0]):
        raise refuse("the DRY arms are not inside ONE 'case ... in' / 'esac' block at "
                     "column 0")
    return closes[0]


def _fn_body(body: List[str], name: str) -> List[str]:
    """Lines of the shell function ``name() {`` up to its closing ``}`` line."""
    heads = [i for i, line in enumerate(body) if re.match(re.escape(name) + r"\(\) *\{", line)]
    if len(heads) != 1:
        raise _const_refuse(f"function {name}() is defined {len(heads)} times, expected 1")
    for j in range(heads[0] + 1, len(body)):
        if body[j] == "}":
            return body[heads[0] + 1:j]
    raise _const_refuse(f"function {name}() never closes")


def _parse_constants_mold(lines: List[str], start: int) -> Dict[str, Any]:
    """The constants-block grammar: see the module docstring."""
    body = lines[start:]
    b_open, b_close, consts = _parse_constants_block(body, start)
    for required in _REQUIRED_LINES + _CONST_REQUIRED_LINES:
        if required not in body[b_close + 1:]:
            raise _const_refuse(f"the body does not carry the line {required!r}")
    for pattern in _REQUIRED_DEFS:
        if not any(pattern.match(line) for line in body):
            raise _const_refuse(f"no line defines {pattern.pattern!r}")
    code = [(i, line) for i, line in enumerate(body)
            if not (b_open <= i <= b_close) and not line.lstrip().startswith("#")]
    for key in consts:
        again = [i for i, line in code if _assigns(line, key)]
        if again:
            raise _const_refuse(f"{key} is assigned again outside the block (line "
                                f"{start + again[0] + 1}): the rendered value would not "
                                "be the one the script uses")
    pack_files = [i for i, line in enumerate(body) if _PACK_FILES_RE.fullmatch(line)]
    if len(pack_files) != 1:
        raise _const_refuse(f"PACK_FILES=\"...\" appears {len(pack_files)} times, expected 1")
    tokens = _PACK_FILES_RE.fullmatch(body[pack_files[0]]).group(1).split()
    unknown = [t for t in tokens if t not in _PACK_FILE_ROLES]
    if unknown or len(set(tokens)) != len(tokens):
        raise _const_refuse(f"PACK_FILES lists {unknown or 'a duplicate'}: the generator "
                            "emits only " + ", ".join(_PACK_FILE_ROLES))
    roles = {_PACK_FILE_ROLES[t] for t in tokens}
    absent = [r for r in _PACK_FILES_REQUIRED if r not in roles]
    if absent:
        raise _const_refuse(f"PACK_FILES does not list the {', '.join(absent)}")
    label = f"mold ({GRAMMAR_CONSTANTS})"
    trap = _find_one(body, _TRAP_RE, "the \"trap '...' EXIT\" line", label)
    guard_len = _previous_guard(body, trap)
    guard_uses = [_dry_definition(body, label)]
    guard_uses += [_find_one(body, re.compile(p), what, label) for p, what in (
        (r'SENT="\$SENT_LIVE"', 'SENT="$SENT_LIVE"'),
        (r'SRC_PIN="\$D/' + re.escape(PIN_OUT) + '"', "SRC_PIN="),
        (r"die\(\) *\{.*", "die() {"))]
    if not (b_close < trap and max(guard_uses) < trap):
        raise _const_refuse("expected constants block < DRY/SENT/SRC_PIN/die() < the EXIT trap")
    commit = _find_one(body, _CONST_COMMIT_RE,
                       "the plumbing commit (NEWC=$(git commit-tree ...) [|| die \"...\"])",
                       label)
    _check_const_step4(body, trap + 1 + guard_len, commit)
    if not any(_CONST_VERIFY_CALL_RE.fullmatch(line.strip())
               for line in _fn_body(body, "verify_pin")
               if not line.lstrip().startswith("#")):
        raise _const_refuse("verify_pin() does not run check_pair_rail.py "
                            "--verify-codex-pin \"$(command -v codex)\" (ADR-182 §5 step 4)")
    parts = {"grammar": GRAMMAR_CONSTANTS, "shebang": lines[0], "start": start,
             "body": body, "block": (b_open, b_close), "consts": consts,
             "roles": roles, "trap": trap, "guard_len": guard_len,
             "mold_version": consts["NEW_VER"][1]}
    _scan_stale_constants(parts)
    return parts


def _check_const_step4(body: List[str], begin: int, commit: int) -> None:
    """ADR-182 §5 step 4 in the constants-block grammar (see _CONST_STEP4)."""
    pos = begin
    for pattern, what in _CONST_STEP4:
        hit = next((i for i in range(pos, commit)
                    if not body[i].lstrip().startswith("#")
                    and pattern.fullmatch(body[i].strip())), None)
        if hit is None:
            raise _const_refuse(f"does not {what} after the previous step and before the "
                                "commit (ADR-182 §5 step 4)")
        pos = hit + 1
    if pos >= commit or _CONST_DIES_RE.fullmatch(body[pos].strip()) is None:
        raise _const_refuse("the check_verify_json line is not followed by '|| { ... die ... }'")


def _const_tokens(consts: Dict[str, Tuple[int, str]]) -> List[str]:
    """Literals of the mold's own values that must not survive outside the block."""
    val = {k: v for k, (_i, v) in consts.items()}
    tag = val["PACK_TAG"]
    tokens = [val["PLAN"], f"codex-pin-{tag}", f"pin-{tag}-", f"rehearse-pin-{tag}",
              val["GA_TAG"], val["NEW_INTEGRITY"].strip("'")]
    tokens += [v for k, v in val.items() if _SHA_SHAPE.fullmatch(v)]
    return tokens


def _stale_hits(lines: List[Tuple[int, str]], tokens: List[str], offset: int) -> List[str]:
    bad: List[str] = []
    for i, line in lines:
        hit = (_ANY_VERSION_RE.search(line) or _HEX64_RE.search(line)
               or _SRI_LITERAL_RE.search(line))
        stale = next((t for t in tokens if t in line), None)
        if hit or stale:
            bad.append(f"line {offset + i + 1}: {(hit.group(0) if hit else stale)!r}")
    return bad


def _scan_stale_constants(parts: Dict[str, Any]) -> None:
    """Outside the KEY=VALUE lines of the block and the guard, no version,
    digest, tag or path literal of any pack may survive (the block's own
    comment lines are copied, so they are scanned too)."""
    body = parts["body"]
    value_lines = {i for i, _v in parts["consts"].values()}
    guard = set(range(parts["trap"] + 1, parts["trap"] + 1 + parts["guard_len"]))
    scan = [(i, line) for i, line in enumerate(body)
            if i not in value_lines and i not in guard]
    bad = _stale_hits(scan, _const_tokens(parts["consts"]), parts["start"])
    if bad:
        raise _const_refuse("version-specific text outside the block's values (it would "
                            "be copied stale): " + "; ".join(bad[:5]))


def parse_rehearsal(text: str, consts: Dict[str, Tuple[int, str]]) -> Dict[str, Any]:
    """The pack's rehearsal script: header regenerated, body copied verbatim.

    The body must read its constants from its own pack's ceremony script
    (``SIGN_SRC``) and carry no literal of the pack; every npm platform
    suffix it names must be the platform of the mold's ``TRIPLE``.
    """
    lines, start = _split_script(text, "rehearsal")
    body = lines[start:]
    if _REHEARSAL_SIGN_LINE not in body:
        raise _const_refuse(f"the rehearsal does not carry the line {_REHEARSAL_SIGN_LINE!r}")
    bad = _stale_hits(list(enumerate(body)), _const_tokens(consts), start)
    if bad:
        raise _const_refuse("the rehearsal carries version-specific text (it would be "
                            "copied stale): " + "; ".join(bad[:5]))
    triple = consts["TRIPLE"][1]
    platforms = {p for p in PLATFORM_TRIPLE if any(p in line for line in body)}
    by_triple = {t: p for p, t in PLATFORM_TRIPLE.items()}
    if platforms - {by_triple.get(triple)}:
        raise _const_refuse(f"the rehearsal names npm platform(s) {sorted(platforms)} but "
                            f"the mold pins {triple}")
    return {"shebang": lines[0], "body": body,
            "platform": by_triple.get(triple) if platforms else None}


def load_mold_siblings(parts: Dict[str, Any], mold: Path) -> None:
    """Constants-block grammar: the mold's place and its rehearsal sibling.

    The block derives the pack dir (``D``) from ``PLAN`` and ``PACK_TAG``, so
    the mold must live at ``.claude/plans/<PLAN>/codex-pin-<PACK_TAG>/``;
    the rehearsal (when ``PACK_FILES`` lists one) is its
    ``rehearse-pin-<PACK_TAG>.sh`` and must parse (``parse_rehearsal``).
    """
    if parts["grammar"] != GRAMMAR_CONSTANTS:
        return
    plan, tag = parts["consts"]["PLAN"][1], parts["consts"]["PACK_TAG"][1]
    if (mold.parent.name, mold.parent.parent.name) != (f"codex-pin-{tag}", plan):
        raise _const_refuse(f"the mold sits in {mold.parent.parent.name}/{mold.parent.name}, "
                            f"not in {plan}/codex-pin-{tag} as its PLAN and PACK_TAG say")
    parts["rehearsal"] = None
    if "rehearsal" in parts["roles"]:
        sibling = mold.parent / f"rehearse-pin-{tag}.sh"
        if sibling.is_symlink() or not sibling.is_file():
            raise _const_refuse(f"PACK_FILES lists the rehearsal but {sibling.name} is not a "
                                "regular file beside the mold")
        raw = sibling.read_bytes()
        parts["rehearsal"] = parse_rehearsal(_mold_text(raw, sibling.name), parts["consts"])
        parts["rehearsal"].update({"name": sibling.name,
                                   "sha": hashlib.sha256(raw).hexdigest()})
    readme = mold.parent / "README.md"
    parts["mold_readme"] = readme.is_file() and not readme.is_symlink()


def _check_step4(body: List[str], commit: int) -> None:
    """The mold must verify the installed binary AFTER applying the manifest.

    ADR-182 §5 step 4 is what catches a wrong pin against the binary that
    will actually run; a mold without it would sign whatever was measured.
    Code lines only, in this order before the commit: the manifest apply,
    then a ``--verify-codex-pin`` run, then a ``"status": "verified"`` check
    that dies (a verification BEFORE the apply does not count).
    """
    def after(start: int, pattern: "re.Pattern[str]", what: str) -> int:
        for i in range(start, commit):
            line = body[i]
            if not line.lstrip().startswith("#") and pattern.fullmatch(line.strip()):
                return i
        raise RePinError(EXIT_INPUT, f"mold does not {what} (ADR-182 §5 step 4: apply "
                                     "the manifest, then --verify-codex-pin, then require "
                                     "'\"status\": \"verified\"', all before the commit)")
    apply = after(0, _APPLY_MAN_RE, "apply the new manifest (cp \"$SRC_MAN\" \"$DST_MAN\")")
    verify = after(apply + 1, _VERIFY_PIN_RE, "run check_pair_rail.py --verify-codex-pin "
                                              "\"$(command -v codex)\" after the apply")
    after(verify + 1, _VERIFIED_RE, "require '\"status\": \"verified\"' (grep ... || die) "
                                    "after that verification")


def _previous_guard(body: List[str], trap: int) -> int:
    """Length of a previous generation's guard right after the trap, else 0.

    The guard's first line anywhere else, or a guard whose lines differ, is
    refused: a hand-modified generator region is not silently re-owned.
    """
    marks = [i for i, line in enumerate(body) if line == _GUARD[0]]
    if not marks:
        return 0
    if marks != [trap + 1] or body[trap + 1:trap + 1 + len(_GUARD)] != _GUARD:
        raise RePinError(EXIT_INPUT, "mold carries a moved or modified generator "
                                     "guard; regenerate from an unmodified pack")
    return len(_GUARD)


def _old_tokens(parts: Dict[str, Any]) -> List[str]:
    body, owned = parts["body"], parts["owned"]
    d_value = body[owned["D"]][2:]
    tag = re.search(r"/pin-([a-z0-9-]+)-approved", body[owned["SENT_LIVE"]]).group(1)
    sha = body[owned["NEW_SHA"]].split("=", 1)[1].strip("'")
    return [d_value, "pin-" + tag + "-", sha]


def _scan_stale(parts: Dict[str, Any]) -> None:
    """Refuse a mold whose body keeps version-specific text outside owned lines."""
    body = parts["body"]
    skip = set(parts["owned"].values())
    skip.update(range(parts["trap"] + 1, parts["trap"] + 1 + parts["guard_len"]))
    skip.update(range(parts["commit"] + 1, parts["commit_end"]))
    tokens = _old_tokens(parts)
    bad: List[str] = []
    for i, line in enumerate(body):
        if i in skip:
            continue
        hit = _ANY_VERSION_RE.search(line)
        stale = next((t for t in tokens if t in line), None)
        if hit or stale:
            bad.append(f"line {parts['start'] + i + 1}: {(hit.group(0) if hit else stale)!r}")
    if bad:
        raise RePinError(EXIT_INPUT, "mold carries version-specific text outside the "
                                     "regions the generator owns (it would be copied "
                                     "stale): " + "; ".join(bad[:5]))


def _code_lines(body: List[str]) -> List[str]:
    return [line for line in body if not line.lstrip().startswith("#")]


def _wrap(text: str, width: int = 78) -> List[str]:
    return textwrap.wrap(text, width=width, break_on_hyphens=False,
                         break_long_words=False)


def _wrap_comment(text: str, width: int = 76) -> List[str]:
    return ["# " + w for w in _wrap(text, width - 2)]


def _render_header(parts: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    body = parts["body"]
    steps = [m.group(1) for m in (_SAY_RE.match(line) for line in body) if m]
    script = f"{ctx['pack_dir']}/{ctx['script_name']}"
    head = [
        f"# AUTO-GENERATED por {GENERATOR} em {ctx['date']} a partir do molde",
        f"# {ctx['mold_rel']} (sha256 {ctx['mold_sha']}).",
    ]
    head += _wrap_comment(
        "Não edite valores à mão: regenere o pack. O corpo é o do molde, byte a "
        "byte, fora das linhas de valor (" + ", ".join(_OWNED_SHAPES) + "), do "
        f"guard {TODO_MARK} e da mensagem de commit.")
    head += ["#", f"# {ctx['script_name']} — cerimônia do re-pin codex-cli "
                  f"{ctx['from_version']} -> {ctx['version']}."]
    if steps:
        head += _wrap_comment("Passos (lidos do molde): " + " · ".join(steps) + ".")
    head += ["#", f"#   bash {script}            # real"]
    if '[ "${1:-}" = "--dry-run" ]' in " ".join(_code_lines(body)):
        head.append(f"#   bash {script} --dry-run  # ensaio")
    head += ["#", "# Se o GPG reclamar de pinentry:", "#   export GPG_TTY=$(tty)"]
    return head




def _render_commit_message(parts: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    code = " ".join(_code_lines(parts["body"]))
    source = ("fornecido localmente (--offline-from)" if ctx["offline"]
              else "baixado com npm pack")
    msg = [f"ceremony({ctx['plan_id']}): re-pin codex-cli {ctx['from_version']} -> "
           f"{ctx['version']}", ""]
    msg += _wrap(
        f"Digests medidos por {GENERATOR} em {ctx['date']}: tarball de plataforma "
        f"{ctx['platform_spec']} {source}; sha512 do tarball == dist.integrity do "
        f"registry; sha256 do payload {ctx['member']} dentro dele. Motivo, "
        "protocolo, consequência e comandos de reprodução: no sentinel "
        "assinado.") + [""]
    if ctx["widened"]:
        rng = (f"Widen-upper-only (<{ctx['old_upper']} -> <{ctx['new_upper']}); "
               f"limite inferior inalterado em >={ctx['lower']}.")
    else:
        rng = f"Range inalterado ({ctx['new_range']}): {ctx['version']} já está dentro dele."
    msg += _wrap(rng) + [""]
    # parse_mold already required the step-4 verification (_check_step4).
    checks = ["--verify-codex-pin = verified"]
    if "--phase 6" in code:
        checks.append("pair-rail-gate.sh --phase 6 OK")
    msg += _wrap("Verificado na cerimônia, depois de aplicar: "
                 + "; ".join(checks) + ".") + [""]
    msg.append("Sentinel: $SENT (assinado, Anchor-SHA $HEAD_SHA)")
    residue = re.sub(r"\$(SENT|HEAD_SHA)\b", "", "\n".join(msg))
    if any(c in residue for c in "$`\\"):
        raise RePinError(EXIT_INPUT, "generated commit message would expand in the "
                                     "unquoted heredoc")
    return msg


def render_mold(parts: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    """The filled ceremony script: owned regions regenerated, body verbatim."""
    if parts["grammar"] == GRAMMAR_CONSTANTS:
        return _render_constants_mold(parts, ctx)
    body = list(parts["body"])
    owned = parts["owned"]
    values = {
        "D": ctx["pack_dir"],
        "SENT_LIVE": f'"$D/{ctx["sentinel_name"]}"',
        "NEW_RANGE": f"'{ctx['new_range']}'",
        "NEW_VERSION": f"'\"package_version\": \"{ctx['version']}\"'",
        "NEW_SHA": f"'{ctx['sha256']}'",
    }
    for name, idx in owned.items():
        body[idx] = f"{name}={values[name]}"
    message = _render_commit_message(parts, ctx)
    after_guard = parts["trap"] + 1 + parts["guard_len"]
    out = (body[:parts["trap"] + 1] + _GUARD
           + body[after_guard:parts["commit"] + 1] + message
           + body[parts["commit_end"]:])
    return "\n".join([parts["shebang"]] + _render_header(parts, ctx) + out)


def constants_values(ctx: Dict[str, Any]) -> Dict[str, str]:
    """The rendered value of every _CONST_RENDERED key, each re-checked
    against the shape the parser demands of a mold (the output is a mold)."""
    values = {
        "PLAN": ctx["plan_id"], "PACK_TAG": ctx["tag"], "OLD_VER": ctx["from_version"],
        "NEW_VER": ctx["version"], "LOWER": ctx["lower"], "OLD_UPPER": ctx["old_upper"],
        "NEW_UPPER": ctx["new_upper"], "NEW_PUBLISHED": ctx["published_date"],
        "TRIPLE": ctx["triple"], "OLD_SHA": ctx["old_sha"], "NEW_SHA": ctx["sha256"],
        "NEW_INTEGRITY": f"'{ctx['integrity']}'",
        "BASE_PIN_SHA256": ctx["base_pin_sha256"], "BASE_MAN_SHA256": ctx["base_man_sha256"],
        "SRC_PIN_SHA256": ctx["src_pin_sha256"], "SRC_MAN_SHA256": ctx["src_man_sha256"],
        "GA_TAG": ctx["ga_tag"], "D": _CONST_D_TEMPLATE,
    }
    for key, value in values.items():
        if _CONST_RENDERED[key].fullmatch(value or "") is None:
            raise RePinError(EXIT_VERIFY, f"rendered {key}={value!r} has an unexpected shape")
    return values


def _generated_notice(ctx: Dict[str, Any], source_rel: str, source_sha: str,
                      owned: str) -> List[str]:
    """Provenance lines for the constants-block generation. No version,
    digest or tag literal: the pack's rehearsal refuses one outside the block
    (the source sha256 is cut to 16 hex digits for that reason)."""
    head = [f"# AUTO-GENERATED por {GENERATOR} em {ctx['date']} a partir de",
            f"# {source_rel} (sha256 {source_sha[:16]}...)."]
    return head + _wrap_comment(f"Não edite à mão: regenere o pack. O corpo é o da "
                                f"fonte, byte a byte, exceto {owned}.")


def _render_constants_mold(parts: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    body = list(parts["body"])
    values = constants_values(ctx)
    for key, (idx, _old) in parts["consts"].items():
        if key in values:
            body[idx] = f"{key}={values[key]}"
    trap = parts["trap"]
    out = body[:trap + 1] + _GUARD + body[trap + 1 + parts["guard_len"]:]
    script = f"{ctx['pack_dir']}/{ctx['script_name']}"
    head = _generated_notice(ctx, ctx["mold_rel"], ctx["mold_sha"],
                             f"este cabeçalho, os valores do bloco de constantes e o "
                             f"guard {TODO_MARK}")
    head += ["#"] + _wrap_comment(
        f"{ctx['script_name']} — cerimônia do re-pin do codex-cli ({ctx['plan_id']}). "
        "As versões, os digests e os caminhos estão todos no bloco de constantes abaixo.")
    steps = [m.group(1) for m in (_SAY_RE.match(line) for line in parts["body"]) if m]
    if steps:
        head += _wrap_comment("Passos (lidos do molde): " + " · ".join(steps) + ".")
    head += ["#", f"#   bash {script}            # real",
             f"#   bash {script} --dry-run  # ensaio"]
    if parts.get("rehearsal") is not None:
        head.append(f"#   bash {ctx['pack_dir']}/rehearse-pin-{ctx['tag']}.sh  # ensaio ponta a "
                    "ponta (cópia descartável)")
        head += ["#"] + _wrap_comment(_rehearsal_order_note(ctx))
    head.append("#")
    if parts.get("mold_readme"):
        head += _wrap_comment("O que cada guard confere e por quê: o README do pack do molde "
                              f"({posixpath.dirname(ctx['mold_rel'])}/README.md).")
    head += ["# Se o GPG reclamar de pinentry:", "#   export GPG_TTY=$(tty)"]
    return "\n".join([parts["shebang"]] + head + out)


def render_rehearsal(parts: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    """The rehearsal: a regenerated header over the mold rehearsal's body."""
    reh = parts["rehearsal"]
    src = f"{posixpath.dirname(ctx['mold_rel'])}/{reh['name']}"
    head = _generated_notice(ctx, src, reh["sha"], "este cabeçalho")
    head += ["#"] + _wrap_comment(
        f"rehearse-pin-{ctx['tag']}.sh — ensaio ponta a ponta da cerimônia do re-pin, "
        "numa cópia descartável; as constantes vêm do OWNER-PIN-SIGN.sh deste diretório. "
        f"O que o ensaio faz, passo a passo: o cabeçalho de {src}.")
    head += ["#", f"#   bash {ctx['pack_dir']}/rehearse-pin-{ctx['tag']}.sh"]
    return "\n".join([reh["shebang"]] + head + reh["body"])


def _rehearsal_order_note(ctx: Dict[str, Any]) -> str:
    """C-R2M-05: the rehearsal clones ``main`` and runs this script for REAL
    in its negative controls and in p2; the injected guard dies in every
    real run while a ``TODO(owner)`` remains, so each of those cases would
    abort on the guard instead of the pattern it expects."""
    return (f"O ensaio (`rehearse-pin-{ctx['tag']}.sh`) clona o `main` e roda o script de "
            f"verdade nos controles negativos e no p2: com {TODO_MARK} pendente cada caso "
            f"aborta no guard {TODO_MARK}, não no padrão que espera. Antes do ensaio: gere "
            "com `--pin-note`, escreva as seções humanas do sentinel e commite o pack.")


def _inherited_prose_flags(parts: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    """Named contradictions between this run and the mold's inherited prose
    that the generator CAN see, in the mold's ``printf`` lines: under
    ``--offline-from``, a line naming ``npm pack`` states a measurement this
    run did not make; when the version already sits inside the range
    (nothing widened), a line saying ``Widen-upper-only`` states a widening
    this run did not make (C-R3M-02)."""
    printfs = [ln for ln in parts["body"] if ln.lstrip().startswith("printf ")]
    flags = []
    if ctx["offline"] and any("npm pack" in ln for ln in printfs):
        flags.append("a mensagem de commit herdada do molde diz que os digests saíram de "
                     "`npm pack`; esta geração usou `--offline-from` (tarball fornecido "
                     "localmente, conferido contra o `dist.integrity`) — corrija a frase "
                     "antes de assinar")
    if not ctx["widened"] and any("Widen-upper-only" in ln for ln in printfs):
        flags.append("a mensagem de commit herdada do molde diz `Widen-upper-only`; nesta "
                     f"geração o range fica inalterado (`{ctx['new_range']}`: "
                     f"{ctx['version']} já está dentro dele) — corrija a frase antes de "
                     "assinar")
    return flags


def _inherited_prose_notes(parts: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    """C-R2M-06, declared by SHAPE: in the constants-block grammar every line
    of the mold body outside the constants block, the guard and the header
    is copied verbatim, including the commit message's ``printf`` prose. The
    generator's only check on that text is the stale-literal scan (version,
    hex and SRI tokens); a sentence that is true only of the mold's own
    re-pin passes it unchanged."""
    if parts["grammar"] != GRAMMAR_CONSTANTS:
        return []
    lines = _wrap(
        "Texto herdado sem conferência: fora do bloco de constantes, do guard "
        f"{TODO_MARK} e do cabeçalho, o corpo do script é o do molde, byte a byte — "
        "inclusive a prosa da mensagem de commit (as linhas `printf`). O gerador só "
        "confere nela os literais de versão, hex e SRI; uma frase verdadeira apenas "
        "para o re-pin do molde passa inalterada. Leia a mensagem de commit do "
        "script contra ESTE re-pin antes de assinar.")
    for flag in ctx.get("inherited_flags") or []:
        lines += [""] + _wrap("Contradição detectada nesta geração: " + flag + ".")
    return lines


def render_readme(parts: Dict[str, Any], ctx: Dict[str, Any], files: List[str]) -> str:
    """The pack's README: provenance, the measured values and the files."""
    rng = (f"`<{ctx['old_upper']}` → `<{ctx['new_upper']}` (inferior inalterado em "
           f"`>={ctx['lower']}`)" if ctx["widened"] else f"inalterado (`{ctx['new_range']}`)")
    lines = [
        f"# {ctx['pack_name']} — re-pin do Codex CLI {ctx['from_version']} → "
        f"{ctx['version']} ({ctx['plan_id']})",
        "",
        f"Gerado por `{GENERATOR}` em {ctx['date']} a partir do molde `{ctx['mold_rel']}`",
        f"(sha256 `{ctx['mold_sha']}`). Não edite à mão: regenere o pack.",
        "",
        "| valor | medido |",
        "|---|---|",
        f"| versão | `{ctx['version']}` (publicada em {ctx['published_date']}) |",
        f"| range | {rng} |",
        f"| `npm_integrity` (plataforma `{ctx['platform_spec']}`) | `{ctx['integrity']}` |",
        f"| `sha256` do payload `{ctx['triple']}` | `{ctx['sha256']}` |",
        f"| `sha256` dos canônicos vivos (pin, manifesto) | `{ctx['base_pin_sha256']}`, "
        f"`{ctx['base_man_sha256']}` |",
        f"| `sha256` dos `.new` (pin, manifesto) | `{ctx['src_pin_sha256']}`, "
        f"`{ctx['src_man_sha256']}` |",
        f"| tag que o re-pin segue | `{ctx['ga_tag']}` |",
        "",
        "Arquivos: " + ", ".join(f"`{f}`" for f in files) + ".",
        "",
        f"O `{ctx['script_name']}` recusa a execução real enquanto houver `{TODO_MARK}` "
        "no sentinel ou no",
        f"`{PIN_OUT}`. Os dois `.new` são conferidos por sha256 (`SRC_PIN_SHA256`,",
        "`SRC_MAN_SHA256`): editar um deles à mão faz o script recusar. Para escrever a",
        "justificativa no pin, regenere o pack (num diretório novo, ou depois de",
        "removê-lo) com `--pin-note <arquivo>`.",
    ]
    if parts.get("rehearsal") is not None:
        lines += [""] + _wrap(_rehearsal_order_note(ctx))
    notes = _inherited_prose_notes(parts, ctx)
    if notes:
        lines += [""] + notes
    if parts.get("mold_readme"):
        lines += ["", "O que cada passo e cada guard da cerimônia conferem, e por quê: o README "
                  f"do pack do molde, `{posixpath.dirname(ctx['mold_rel'])}/README.md` (o "
                  "corpo do script é o do molde)."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Rendering of the pin paragraph, the manifest and the sentinel draft
# ---------------------------------------------------------------------------


def render_manifest(old: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    entry_path = old["payloads"][ctx["triple"]]["path"]
    new = {
        "schema": 1,
        "package_version": ctx["version"],
        "npm_integrity": ctx["integrity"],
        "payloads": {ctx["triple"]: {"path": entry_path, "sha256": ctx["sha256"]}},
    }
    return json.dumps(new, indent=2, ensure_ascii=False) + "\n"


def render_pin(prefix: List[str], ctx: Dict[str, Any]) -> str:
    """The live pin's lines before the range, unchanged, then a blank line
    (unless they already end in one), the dated paragraph and the range."""
    lines = list(prefix)
    if lines and lines[-1].strip():
        lines.append("")
    if ctx["widened"]:
        rng = (f"Upper bound widened <{ctx['old_upper']} -> <{ctx['new_upper']}; "
               f"LOWER BOUND UNCHANGED at >={ctx['lower']} (widen-upper-only).")
    else:
        rng = (f"Range UNCHANGED ({ctx['new_range']}): {ctx['version']} already "
               "sits inside it.")
    para = (f"re-pin update ({ctx['date']}, pack {ctx['pack_name']}; generated by "
            f"{GENERATOR}): package_version {ctx['from_version']} -> "
            f"{ctx['version']}. {rng} The payload manifest is re-pinned in this "
            f"same pack: payload sha256 {ctx['sha256'][:8]}... for "
            f"{ctx['version']}/{ctx['triple']}, npm_integrity from the PLATFORM "
            f"artifact {ctx['platform_spec']} (ADR-182 §5 step 2).")
    lines += _wrap_comment(para)
    note = ctx.get("pin_note")
    if note:
        for paragraph in note:
            lines += _wrap_comment(paragraph)
    else:
        lines += _wrap_comment(
            f"{TODO_MARK}: why this re-pin now; whether it runs outside any open "
            "release window; whether ADR-111 §pin-update-protocol asks for a "
            "Phase 4-bis re-run; and the declared consequence (rail measurements "
            "taken before and after this commit are NOT comparable).")
    lines.append(ctx["new_range"])
    return "\n".join(lines) + "\n"


def read_pin_note(path: str) -> List[str]:
    """``--pin-note``: the Owner's rationale, as paragraphs (split on blank
    lines, each re-wrapped as ``# `` comment lines by ``render_pin``)."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise RePinError(EXIT_INPUT, f"--pin-note unreadable ({type(exc).__name__})") from None
    text = _mold_text(raw, "--pin-note")
    if TODO_MARK in text:
        raise RePinError(EXIT_INPUT, f"--pin-note still carries {TODO_MARK}")
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n[ \t]*\n", text)]
    paragraphs = [p for p in paragraphs if p]
    if not paragraphs:
        raise RePinError(EXIT_INPUT, "--pin-note is empty")
    if any(not c.isprintable() for p in paragraphs for c in p):
        raise RePinError(EXIT_INPUT, "--pin-note carries a control character")
    return paragraphs


def _sentinel_data_line(ctx: Dict[str, Any]) -> str:
    """The sentinel's ``Data:`` header line.

    A constants-block mold's step 1 rewrites BOTH ``Anchor-SHA:`` and
    ``Data:`` with the signing day, and its rehearsal (copied verbatim into
    the pack) requires exactly those two lines to change in the ceremony
    commit (4 delta lines). A ``Data:`` already equal to the signing day
    would change nothing and a same-day rehearsal would go red, so there
    the line is a PLACEHOLDER, never the generation date. A heredoc-grammar
    mold's step 1 rewrites only ``Anchor-SHA:``; there the line keeps the
    generation date, as the hand-built sentinel of that grammar did.
    """
    if ctx["grammar"] == GRAMMAR_CONSTANTS:
        return "Data: (preenchida pelo passo 1 do script de cerimônia)"
    return f"Data: {ctx['date']}"


def render_sentinel(ctx: Dict[str, Any]) -> str:
    # justified: one literal template; splitting it would scatter the
    # sentinel's section order across helpers.
    source =("fornecido por --offline-from (não baixado nesta execução)"
              if ctx["offline"] else "baixado com npm pack num diretório temporário")
    published = ctx["published"] or "ausente no documento do registry"
    rng = (f"`<{ctx['old_upper']}` → `<{ctx['new_upper']}` (limite inferior "
           f"INALTERADO em `>={ctx['lower']}`)" if ctx["widened"]
           else f"range INALTERADO (`{ctx['new_range']}`)")
    tgz, member = ctx["tarball_name"], ctx["member"]
    reg = " ".join(NPM_REGISTRY_ARGS)
    url = ctx["tarball_url"] or "ausente ou fora do formato https://…/*.tgz"
    return "\n".join([
        f"# {ctx['sentinel_stem']} — sentinel do re-pin do codex CLI "
        f"{ctx['from_version']} → {ctx['version']}",
        "",
        f"Plan: {ctx['plan_id']}",
        f"Wave: re-pin codex-cli {ctx['from_version']} → {ctx['version']}",
        "Anchor-SHA: (preenchido pelo passo 1 do script de cerimônia)",
        _sentinel_data_line(ctx),
        "",
        "## Ratificação",
        "",
        f"{TODO_MARK}: o mandato do Owner (verbatim, com data) e por que este",
        "re-pin entra agora.",
        "",
        "## Scope",
        "",
        f"- `{PIN_REL}` — {rng}, com o parágrafo datado do cabeçalho.",
        f"- `{MANIFEST_REL}` — `package_version` {ctx['version']}, `npm_integrity` "
        f"do artefato de PLATAFORMA e `sha256` do payload `{ctx['triple']}`.",
        "",
        "Nada além desses dois arquivos canônicos, deste sentinel e da sua",
        "assinatura entra no commit da cerimônia.",
        "",
        "## Bytes que esta assinatura cobre",
        "",
        f"    range novo                         {ctx['new_range']}",
        f"    {PIN_REL} vivo (sha256)   {ctx['base_pin_sha256']}",
        f"    {MANIFEST_REL} vivo (sha256)",
        f"                                       {ctx['base_man_sha256']}",
        f"    {PIN_OUT} (sha256)          {ctx['src_pin_sha256']}",
        f"    {MANIFEST_OUT} (sha256)",
        f"                                       {ctx['src_man_sha256']}",
        f"    payload {ctx['triple']} (sha256)  {ctx['sha256']}",
        f"    npm_integrity (plataforma)         {ctx['integrity']}",
        "",
        "Os dois `vivo` são os canônicos de quando o pack foi gerado; os dois `.new`",
        "são os bytes que a cerimônia aplica.",
        "",
        f"## Evidência dos digests (medida por `{GENERATOR}` em {ctx['date']})",
        "",
        f"Registry: `{NPM_REGISTRY}`, passado explicitamente a toda chamada do npm",
        "(`--registry` e `--@openai:registry`: nenhum `.npmrc` escolhe outro).",
        "",
        f"    npm view {PACKAGE}@{ctx['version']} --json {reg}",
        f"      -> time[\"{ctx['version']}\"] = {published}",
        f"      -> optionalDependencies[\"{ctx['alias_key']}\"] = npm:{ctx['platform_spec']}",
        f"    npm view {ctx['platform_spec']} --json {reg}",
        f"      -> dist.integrity = {ctx['integrity']}",
        f"      -> dist.tarball = {url}",
        f"    tarball {tgz} ({ctx['tarball_size']} bytes), {source}",
        f"      -> sha512 = {ctx['integrity']}  (confere com o dist.integrity)",
        f"    membro {member} ({ctx['payload_size']} bytes)",
        f"      -> sha256 = {ctx['sha256']}",
        "",
        "Reprodução manual:",
        "",
        f"    npm pack {ctx['platform_spec']} {reg}",
        f"    openssl dgst -sha512 -binary {tgz} | base64",
        f"    tar xzf {tgz} {member}",
        f"    shasum -a 256 {member}",
        "",
        f"Para registro, o `dist.integrity` do pacote PRINCIPAL {PACKAGE}@"
        f"{ctx['version']} é `{ctx['main_integrity'] or 'ausente'}` — não é o",
        "que se grava (ADR-182 §5 passo 2).",
        "",
        "Conferência opcional antes da cerimônia, com a versão já instalada:",
        "`python3 .claude/hooks/check_pair_rail.py --verify-codex-pin \"$(command -v codex)\"`",
        f"deve trazer `\"sha256\": \"{ctx['sha256']}\"` (o `status` ainda é `mismatch`",
        "contra o pin vigente).",
        "",
        "## Protocolo, consequência e residual",
        "",
        f"{TODO_MARK}: janela de release aberta ou não; ADR-111",
        "§pin-update-protocol (Phase 4-bis); a consequência declarada (medições do",
        "rail antes e depois deste commit não são comparáveis); o residual (só o",
        f"payload `{ctx['triple']}` é pinado).",
        "",
        f"Residual declarado pelo gerador: o caminho do payload (`{ctx['entry_path']}`)",
        "é COPIADO do manifesto vivo; o gerador só confere que o tarball novo tem",
        "um membro regular ali. Que o launcher da versão nova (`bin/codex.js` do",
        "pacote principal) ainda execute esse caminho NÃO é conferido — ponto",
        "cego compartilhado com `--verify-codex-pin`, que faz hash do mesmo",
        "caminho do manifesto.",
        "",
    ] + ([*ctx["inherited_notes"], ""] if ctx.get("inherited_notes") else []))


# ---------------------------------------------------------------------------
# Emission and orchestration
# ---------------------------------------------------------------------------


def emit_pack(out: Path, files: Dict[str, str], make_parent: bool = False) -> None:
    """Write the pack into a sibling temp dir, then rename it into place.

    A path that exists at either check is refused. Between the last check and
    the rename, ``rename(2)`` refuses a non-empty directory or a non-directory
    at ``out``; only an EMPTY directory created in that window would be
    replaced (nothing is lost). A filesystem error (an unwritable parent, for
    instance) is an input refusal of ``out``, never a traceback.
    ``make_parent`` creates a missing parent (ONE level: the plan's
    ``PLAN-NNN/`` subdirectory) and removes it again if the write fails.
    """
    if os.path.lexists(out):
        raise RePinError(EXIT_INPUT, f"output path already exists: {out}")
    parent = out.parent
    made_parent = False
    if make_parent and not os.path.lexists(parent):
        try:
            os.mkdir(parent, 0o755)
            made_parent = True
        except OSError as exc:
            raise RePinError(EXIT_INPUT, f"cannot create {parent} "
                                         f"({type(exc).__name__})") from None
    if not parent.is_dir():
        raise RePinError(EXIT_INPUT, f"output parent is not a directory: {parent}")
    try:
        _write_pack(out, parent, files)
    except BaseException:
        if made_parent:
            try:
                os.rmdir(parent)
            except OSError:
                pass
        raise


def _write_pack(out: Path, parent: Path, files: Dict[str, str]) -> None:
    try:
        tmp = Path(tempfile.mkdtemp(prefix=".re-pin-codex-", dir=str(parent)))
    except OSError as exc:
        raise RePinError(EXIT_INPUT, f"cannot write under {parent} "
                                     f"({type(exc).__name__})") from None
    try:
        for name, content in files.items():
            with open(tmp / name, "x", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            os.chmod(tmp / name, 0o644)
        os.chmod(tmp, 0o755)
        if os.path.lexists(out):
            raise RePinError(EXIT_INPUT, f"output path appeared meanwhile: {out}")
        os.rename(tmp, out)
    except OSError as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RePinError(EXIT_INPUT, f"cannot write the pack at {out} "
                                     f"({type(exc).__name__})") from None
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def _mold_text(raw: bytes, what: str) -> str:
    """The mold's text; CR bytes and non-UTF-8 are input refusals."""
    if b"\r" in raw:
        raise RePinError(EXIT_INPUT, f"{what} carries CR bytes (CRLF); refused")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise RePinError(EXIT_INPUT, f"{what} is not UTF-8") from None


def _resolve_mold(mold_arg: str, repo: Path) -> Tuple[Path, str, str, str]:
    mold = Path(mold_arg)
    if not mold.is_absolute():
        mold = Path.cwd() / mold
    try:
        rel = mold.resolve().relative_to(repo)
    except ValueError:
        raise RePinError(EXIT_INPUT, "--mold must live inside the repository "
                                     "(its path is recorded in the pack)") from None
    try:
        raw = mold.read_bytes()
    except OSError as exc:
        raise RePinError(EXIT_INPUT, f"--mold unreadable ({type(exc).__name__})") from None
    text = _mold_text(raw, "--mold")
    return mold, rel.as_posix(), text, hashlib.sha256(raw).hexdigest()


def mold_target(mold: Path) -> Tuple[Optional[Tuple[int, int, int]], str]:
    """The version a pack pins: ``package_version`` of the manifest ``.new``
    beside its ceremony script. Grammar-independent: every pack generation
    carries that file. ``(None, why)`` when it cannot be read."""
    try:
        data = json.loads((mold.parent / MANIFEST_OUT).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return None, f"no readable {MANIFEST_OUT} beside it ({type(exc).__name__})"
    ver = data.get("package_version") if isinstance(data, dict) else None
    try:
        return parse_version(ver), ""
    except RePinError:
        return None, f"its {MANIFEST_OUT} package_version is not X.Y.Z"


def mold_inventory(repo: Path) -> List[Dict[str, Any]]:
    """Every pack mold under ``.claude/plans``: the version its pack pins and
    whether THIS generator parses it (``reason`` names the refusal)."""
    rows: List[Dict[str, Any]] = []
    for path in sorted((repo / ".claude" / "plans").glob(MOLD_GLOB)):
        target, target_note = mold_target(path)
        grammar = ""
        try:
            parts = parse_mold(_mold_text(path.read_bytes(), "mold"))
            grammar = parts["grammar"]
            load_mold_siblings(parts, path)
            compatible, reason = True, ""
        except RePinError as exc:
            compatible, reason = False, str(exc)
        except OSError as exc:
            compatible, reason = False, f"mold unreadable ({type(exc).__name__})"
        rows.append({"rel": path.relative_to(repo).as_posix(), "target": target,
                     "target_note": target_note, "compatible": compatible,
                     "reason": reason, "grammar": grammar})
    return rows


def _fmt_version(v: Tuple[int, int, int]) -> str:
    return ".".join(str(n) for n in v)


def newest_molds(repo: Path) -> List[Dict[str, Any]]:
    """The molds of the pack(s) that pin the NEWEST version ([] = no pack).

    Raises (input) when some pack's version cannot be read: the newest pack
    cannot be established, and guessing could pick an older mold.
    """
    rows = mold_inventory(repo)
    unranked = [r for r in rows if r["target"] is None]
    if unranked:
        raise RePinError(EXIT_INPUT, f"pack mold {unranked[0]['rel']} has "
                                     f"{unranked[0]['target_note']}: the newest pack "
                                     "cannot be established")
    if not rows:
        return []
    top = max(r["target"] for r in rows)
    return [r for r in rows if r["target"] == top]


def newest_mold(repo: Path) -> Optional[Dict[str, Any]]:
    """THE mold a re-pin is built from, or None when no pack mold exists.

    When a mold of the newest pack is not generator-compatible, that row is
    returned (``compatible`` False, ``reason`` set): the answer is then
    "clone it by hand", never an older mold that would drop what the newer
    pack hardened. The drift detector's recommendation reads this function.
    """
    top = newest_molds(repo)
    if not top:
        return None
    blocked = [r for r in top if not r["compatible"]]
    return blocked[0] if blocked else top[-1]


def _refuse_older_mold(repo: Path, mold_rel: str, mold_version: str) -> None:
    """``--mold`` must be a mold of the newest pack, and every mold of that
    pack must be generator-compatible (no silent downgrade)."""
    top = newest_molds(repo)
    rels = [r["rel"] for r in top]
    newest = _fmt_version(top[0]["target"]) if top else ""
    if mold_rel not in rels:
        mine = next((r for r in mold_inventory(repo) if r["rel"] == mold_rel), None)
        if mine is None:
            raise RePinError(EXIT_INPUT, f"--mold {mold_rel} is not a pack mold "
                                         f"(.claude/plans/{MOLD_GLOB})")
        raise RePinError(EXIT_INPUT, f"--mold {mold_rel} pins "
                                     f"{_fmt_version(mine['target'])}, but the newest pack "
                                     f"pins {newest} ({', '.join(rels)}): building from an "
                                     "older mold would drop what the newer pack hardened")
    blocked = [r for r in top if not r["compatible"]]
    if blocked:
        raise RePinError(EXIT_INPUT, f"the newest pack mold {blocked[0]['rel']} (pins "
                                     f"{newest}) is not generator-compatible: "
                                     f"{blocked[0]['reason']}")
    if mold_version != newest:
        raise RePinError(EXIT_INPUT, f"--mold declares NEW_VERSION {mold_version} but its "
                                     f"pack's {MANIFEST_OUT} pins {newest}")


def _pack_location(args: argparse.Namespace, repo: Path, target: Tuple[int, int, int],
                   tag: str, grammar: str = GRAMMAR_HEREDOC) -> Tuple[str, str, Path]:
    """Pack dir from ``--pack-dir`` or ``--plan`` (never from the mold's plan);
    the plan file must exist; tag and version collisions are refused (a
    ``--dry-run`` writes nothing, so it may re-measure an existing pack).
    In the constants-block grammar the script derives its own dir from
    ``PLAN`` and ``PACK_TAG``, so the dir must be ``codex-pin-<tag>``."""
    if args.pack_dir:
        pack_dir = args.pack_dir
    elif args.plan:
        if _PLAN_RE.fullmatch(args.plan) is None:
            raise RePinError(EXIT_INPUT, f"--plan {args.plan!r} is not PLAN- plus three "
                                         "digits (name the plan that carries this re-pin)")
        pack_dir = f".claude/plans/{args.plan}/codex-pin-{tag}"
    else:
        raise RePinError(EXIT_INPUT, "name the plan that carries this re-pin: --plan "
                                     "PLAN-NNN (or --pack-dir); it is never inherited "
                                     "from the mold")
    m = _PACK_DIR_RE.fullmatch(pack_dir)
    if m is None:
        raise RePinError(EXIT_INPUT, f"pack dir {pack_dir!r} is not "
                                     "'.claude/plans/PLAN-NNN/<slug>'")
    if grammar == GRAMMAR_CONSTANTS and posixpath.basename(pack_dir) != f"codex-pin-{tag}":
        raise RePinError(EXIT_INPUT, f"pack dir {pack_dir!r}: a {GRAMMAR_CONSTANTS} pack "
                                     f"derives its dir from PLAN and PACK_TAG, so it must be "
                                     f"'.claude/plans/PLAN-NNN/codex-pin-{tag}'")
    plans = repo / ".claude" / "plans"
    if not list(plans.glob(f"{m.group(1)}-*.md")):
        raise RePinError(EXIT_INPUT, f"no plan file .claude/plans/{m.group(1)}-*.md: a "
                                     f"{m.group(1)}/ subdirectory without its plan fails "
                                     "the plan schema (PLAN-SCHEMA.md)")
    out = Path(args.out) if args.out else repo / pack_dir
    if args.dry_run:
        return pack_dir, m.group(1), out
    if os.path.lexists(out):
        raise RePinError(EXIT_INPUT, f"output path already exists: {out}")
    used = sorted(p.relative_to(repo).as_posix() for p in
                  list(plans.glob(f"PLAN-*/codex-pin-{tag}"))
                  + list(plans.glob(f"PLAN-*/*/pin-{tag}-approved.md")))
    if used:
        raise RePinError(EXIT_INPUT, f"pack tag {tag!r} is already used under "
                                     f".claude/plans: {', '.join(used)}")
    same = [r["rel"] for r in mold_inventory(repo) if r["target"] == target]
    if same:
        raise RePinError(EXIT_INPUT, f"a pack for {_fmt_version(target)} already exists: "
                                     f"{', '.join(same)}")
    return pack_dir, m.group(1), out


def _measure(args: argparse.Namespace, manifest: Dict[str, Any],
             triple: str, platform: str) -> Dict[str, Any]:
    """Registry resolution + tarball verification; returns the measured facts."""
    npm = shutil.which("npm")
    if npm is None:
        raise RePinError(EXIT_INFRA, "npm is not on PATH")
    try:
        with tempfile.TemporaryDirectory(prefix="re-pin-codex-") as tmp:
            work = Path(tmp)
            reg = resolve_registry(npm, args.version, platform, work)
            member = payload_member(manifest["payloads"][triple]["path"], reg["alias_key"])
            if args.offline_from:
                tarball = Path(args.offline_from)
                data = read_tarball(tarball, EXIT_INPUT, "--offline-from")
            else:
                dest = work / "pack"
                dest.mkdir()
                tarball = fetch_tarball(npm, reg["platform_spec"], work, dest)
                data = read_tarball(tarball, EXIT_INFRA, "the npm pack tarball")
    except OSError as exc:
        raise RePinError(EXIT_INFRA, f"temporary work dir ({type(exc).__name__})") from None
    # From here on only ``data`` is read: the bytes checked against the
    # registry are the bytes the payload is hashed from.
    actual = sri_sha512(data)
    if actual != reg["integrity"]:
        raise RePinError(EXIT_VERIFY, f"tarball sha512 {actual} != registry "
                                      f"dist.integrity {reg['integrity']}")
    sha, size = hash_member(data, member)
    reg.update({"member": member, "sha256": sha, "payload_size": size,
                "tarball_name": tarball.name, "tarball_size": len(data)})
    return reg


def _platform_for(manifest: Dict[str, Any], requested: Optional[str]) -> Tuple[str, str]:
    """(platform, triple): ``--platform`` or, by default, the platform of the
    manifest's single pinned triple (never the generating host's)."""
    if requested is None:
        (pinned,) = manifest["payloads"]
        by_triple = {t: p for p, t in PLATFORM_TRIPLE.items()}
        if pinned not in by_triple:
            raise RePinError(EXIT_INPUT, f"manifest pins triple {pinned!r}, which maps to "
                                         "no known npm platform; pass --platform")
        return by_triple[pinned], pinned
    triple = PLATFORM_TRIPLE.get(requested)
    if triple is None:
        raise RePinError(EXIT_INPUT, f"unknown --platform {requested!r}")
    if set(manifest["payloads"]) != {triple}:
        raise RePinError(EXIT_INPUT, f"manifest pins {sorted(manifest['payloads'])}; this "
                                     f"tool re-pins exactly one triple per run ({triple}) "
                                     "and refuses to emit stale digests for others")
    return requested, triple


def run(args: argparse.Namespace) -> Dict[str, Any]:
    # justified: linear orchestration of already-factored steps; splitting it
    # further would only thread the same context dict through more calls.
    target = parse_version(args.version)
    date = args.date or datetime.date.today().isoformat()
    if _DATE_RE.fullmatch(date) is None:
        raise RePinError(EXIT_INPUT, f"--date {date!r} is not YYYY-MM-DD")
    if args.platform is not None and args.platform not in PLATFORM_TRIPLE:
        raise RePinError(EXIT_INPUT, f"unknown --platform {args.platform!r}")
    repo = Path(args.repo_root).resolve()
    manifest, manifest_raw = read_manifest(repo / MANIFEST_REL)
    if len(manifest["payloads"]) != 1:
        raise RePinError(EXIT_INPUT, f"manifest pins {sorted(manifest['payloads'])}; this "
                                     "tool re-pins exactly one triple per run and refuses "
                                     "to emit stale digests for others")
    platform, triple = _platform_for(manifest, args.platform)
    from_version = manifest["package_version"]
    if target <= parse_version(from_version):
        raise RePinError(EXIT_INPUT, f"{args.version} is not newer than the pinned "
                                     f"{from_version}")
    try:
        pin_raw = (repo / PIN_REL).read_bytes()
        pin_text = pin_raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RePinError(EXIT_INPUT, f"{PIN_REL} unreadable ({type(exc).__name__})") from None
    prefix, lower, upper = parse_pin(pin_text)
    new_range, widened = plan_range(lower, upper, target)
    mold, mold_rel, mold_text, mold_sha = _resolve_mold(args.mold, repo)
    parts = parse_mold(mold_text)
    load_mold_siblings(parts, mold)
    _check_grammar_args(parts, args, platform, triple)
    _refuse_older_mold(repo, mold_rel, parts["mold_version"])
    pin_note = read_pin_note(args.pin_note) if args.pin_note else None
    tag = pack_tag(target)
    pack_dir, plan_id, out = _pack_location(args, repo, target, tag, parts["grammar"])
    ctx = _measure(args, manifest, triple, platform)
    sentinel_stem = f"pin-{tag}-approved"
    ctx.update({
        "version": args.version, "from_version": from_version, "triple": triple,
        "platform": platform, "entry_path": manifest["payloads"][triple]["path"],
        "old_sha": manifest["payloads"][triple]["sha256"],
        "date": date, "offline": bool(args.offline_from), "lower": lower,
        "old_upper": upper, "new_upper": new_range.rsplit("<", 1)[1],
        "new_range": new_range, "widened": widened, "pack_dir": pack_dir,
        "pack_name": Path(pack_dir).name, "plan_id": plan_id, "tag": tag,
        "sentinel_stem": sentinel_stem, "sentinel_name": sentinel_stem + ".md",
        "script_name": mold.name, "mold_rel": mold_rel,
        "mold_sha": mold_sha, "ga_tag": args.ga_tag, "pin_note": pin_note,
        "base_pin_sha256": hashlib.sha256(pin_raw).hexdigest(),
        "base_man_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "published_date": _published_date(ctx["published"], parts["grammar"]),
        "grammar": parts["grammar"],
    })
    files = render_pack(parts, manifest, prefix, ctx)
    if not args.dry_run:
        emit_pack(out, files, make_parent=not args.out)
    keys = ("version", "from_version", "triple", "platform", "platform_spec", "integrity",
            "main_integrity", "published", "registry_latest", "tarball_url", "member",
            "sha256", "payload_size", "tarball_name", "tarball_size", "new_range",
            "widened", "pack_dir", "plan_id", "mold_rel", "ga_tag", "base_pin_sha256",
            "base_man_sha256", "src_pin_sha256", "src_man_sha256")
    summary: Dict[str, Any] = {"status": "dry-run" if args.dry_run else "emitted",
                               "grammar": parts["grammar"]}
    summary.update({k: ctx[k] for k in keys})
    summary.update({"registry": NPM_REGISTRY, "range": f">={lower},<{upper}",
                    "inherited_prose_flags": ctx["inherited_flags"],
                    "out": str(out), "files": sorted(files),
                    # the two files the emitted guard greps (sentinel, pin)
                    "todo_owner": sorted(n for n in (ctx["sentinel_name"], PIN_OUT)
                                         if TODO_MARK in files[n])})
    return summary


def _published_date(published: str, grammar: str) -> str:
    """``YYYY-MM-DD`` of the registry's ``time[<version>]``. The constants-block
    mold states it in its commit message, so there a missing date refuses."""
    day = published[:10] if isinstance(published, str) else ""
    if _DATE_RE.fullmatch(day):
        return day
    if grammar == GRAMMAR_CONSTANTS:
        raise RePinError(EXIT_VERIFY, "the registry document carries no publication time for "
                                      "this version (the constants-block mold states it)")
    return ""


def _check_grammar_args(parts: Dict[str, Any], args: argparse.Namespace,
                        platform: str, triple: str) -> None:
    """Grammar-specific inputs, refused before any registry call."""
    if parts["grammar"] != GRAMMAR_CONSTANTS:
        if args.ga_tag is not None:
            raise RePinError(EXIT_INPUT, f"--ga-tag applies only to a {GRAMMAR_CONSTANTS} "
                                         "mold (GA_TAG constant); this mold has none")
        return
    if args.ga_tag is None or _GA_TAG_RE.fullmatch(args.ga_tag) is None:
        raise RePinError(EXIT_INPUT, f"a {GRAMMAR_CONSTANTS} mold needs --ga-tag vX.Y.Z: the "
                                     "release tag the re-pin ceremony must follow (its GA_TAG "
                                     "constant; the ceremony refuses to run before that tag)")
    reh = parts.get("rehearsal")
    if reh is not None and reh["platform"] not in (None, platform):
        raise RePinError(EXIT_INPUT, f"the mold's rehearsal is tied to npm platform "
                                     f"{reh['platform']}, but this re-pin pins {triple}")


def render_pack(parts: Dict[str, Any], manifest: Dict[str, Any], prefix: List[str],
                ctx: Dict[str, Any]) -> Dict[str, str]:
    """Every file of the pack, name -> text. The two ``.new`` files are
    rendered first: their sha256 is part of what the sentinel and a
    constants-block script declare."""
    files = {MANIFEST_OUT: render_manifest(manifest, ctx), PIN_OUT: render_pin(prefix, ctx)}
    ctx["src_man_sha256"] = hashlib.sha256(files[MANIFEST_OUT].encode("utf-8")).hexdigest()
    ctx["src_pin_sha256"] = hashlib.sha256(files[PIN_OUT].encode("utf-8")).hexdigest()
    files[ctx["script_name"]] = render_mold(parts, ctx)
    ctx["inherited_flags"] = _inherited_prose_flags(parts, ctx)
    ctx["inherited_notes"] = _inherited_prose_notes(parts, ctx)
    files[ctx["sentinel_name"]] = render_sentinel(ctx)
    if parts["grammar"] == GRAMMAR_CONSTANTS:
        if parts.get("rehearsal") is not None:
            files[f"rehearse-pin-{ctx['tag']}.sh"] = render_rehearsal(parts, ctx)
        if "readme" in parts["roles"]:
            files["README.md"] = render_readme(parts, ctx, sorted(files) + ["README.md"])
    return files


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="re-pin-codex.py",
        description="Generate (never apply) the Codex CLI re-pin pack (ADR-182 §5) from "
                    "the ceremony script of the newest pack. Two mold grammars are "
                    "modelled (heredoc; constants-block); a mold in any other shape is "
                    "refused by name, and so is an older mold. Maintainer-only: it needs "
                    ".claude/governance/, which adopters do not receive.")
    ap.add_argument("version", help="target @openai/codex release, X.Y.Z")
    ap.add_argument("--mold", required=True,
                    help="ceremony script of the NEWEST pack (inside the repo). An older "
                         "mold, or one whose grammar this tool does not model, is refused "
                         "by name")
    ap.add_argument("--ga-tag", default=None,
                    help="constants-block molds only (required there): the release tag "
                         "vX.Y.Z the re-pin ceremony must follow (its GA_TAG constant)")
    ap.add_argument("--pin-note", default=None,
                    help="UTF-8 text file with the human rationale for the pin paragraph; "
                         "without it the pin carries a TODO(owner) the emitted script "
                         "refuses to sign over")
    ap.add_argument("--plan", default=None,
                    help="PLAN-NNN that carries this re-pin; the pack goes to "
                         ".claude/plans/PLAN-NNN/codex-pin-<tag> (required unless "
                         "--pack-dir is given)")
    ap.add_argument("--platform", default=None,
                    help="npm platform suffix whose payload is pinned (default: the "
                         "platform of the manifest's single pinned triple)")
    ap.add_argument("--pack-dir", default=None,
                    help="repo-relative pack dir '.claude/plans/PLAN-NNN/<slug>' "
                         "(instead of --plan)")
    ap.add_argument("--out", default=None,
                    help="filesystem dir to write (default: <repo>/<pack-dir>)")
    ap.add_argument("--repo-root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    ap.add_argument("--date", default=None, help="date stamped into the pack (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve, download and verify; write no pack (npm's cache and "
                         "logs live in a temporary directory removed on exit)")
    ap.add_argument("--offline-from", default=None,
                    help="use this local platform tarball instead of npm pack")
    return ap.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        summary = run(args)
    except RePinError as exc:
        print(f"re-pin-codex: ERROR: {exc}", file=sys.stderr)
        return exc.rc
    except OSError as exc:
        # Backstop of the exit contract: a filesystem error no step names.
        print(f"re-pin-codex: ERROR: filesystem ({type(exc).__name__})", file=sys.stderr)
        return EXIT_INFRA
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
