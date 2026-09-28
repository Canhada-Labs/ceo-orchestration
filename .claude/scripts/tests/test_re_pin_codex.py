"""Tests for ``.claude/scripts/re-pin-codex.py`` (the Codex re-pin pack generator).

No network: ``npm`` is a PATH shim (a Python script driven by a JSON config)
that answers ``npm view`` from canned documents and ``npm pack`` by copying a
synthetic tarball built in the test. Every invocation is logged (argv, npm
cache and logs env, cwd) so the tests can assert that a refusal happens
BEFORE any registry call, that ``--offline-from`` never runs ``npm pack``,
that every call names the public registry explicitly, and that npm's own
cache and logs live in a temporary directory removed on exit.

Every test class name carries ``Repin``: the PLAN-193 W5 Check selects with
``-k "repin or ..."`` and the module name (``test_re_pin_codex``) does not
contain that keyword — ``RepinSelectorTest`` guards the convention.

Covered:
- happy path: the range is widened upper-only when the version falls outside
  it and left alone when it falls inside; the manifest, pin, ceremony script
  and sentinel draft carry the measured digests, the registry, the tarball
  URL and the declared payload-path residual; the platform defaults to the
  manifest's pinned triple;
- verification: tarball sha512 != registry integrity, payload missing, payload
  a symlink, payload duplicated — also under names npm's extractor lands on
  the payload path (another top-level directory, since pacote strips the
  first segment; './', repeated '/', letter case) —, an absolute or '..'
  member, a link onto / at / pointing at the payload path, alias naming
  another version -> rc 3, and nothing is written; a tar header outside the
  one shape both tar readers decode identically (plain POSIX ustar of a
  regular file, directory or link) -> rc 3, with the reviewer's pax-global
  PoC as the first case and in-shape positive controls;
- the integrity check and the member hash read ONE in-memory copy: a file
  swapped on disk right after the sha512 cannot change the pinned sha256;
- input refusals (rc 2): version shape, not-an-upgrade, existing output, an
  unwritable output parent (no traceback), --offline-from that is a symlink,
  FIFO, directory or missing, heredoc mold grammar (stale version literal in
  the body, missing/duplicated value line, quoted heredoc, foreign SRC_PIN,
  code in the header, CRLF, no ADR-182 §5 step-4 verification after the
  apply), an incomplete constants block refused BY NAME, manifest with a
  second triple or an unknown key, malformed pin;
- the constants-block grammar end to end: every rendered constant (SRC_* =
  sha256 of the emitted .new files, BASE_* = sha256 of the live canonicals),
  the pass-through keys verbatim, the body verbatim outside the owned
  regions, the rehearsal and README emitted, bash -n + ceremony-lint (zero
  findings) + the PLAN-193 rehearsal's own literal scan over the emitted
  script, the next generation built from the emitted script, --ga-tag and
  --pin-note rules, a missing publication date (rc 3), and a table of
  grammar refusals (unknown/duplicate/missing key, D, value shape, unclosed
  block, key reassigned or exported in the body, PACK_FILES, frozen-copy and
  step-4 anchors, stale literals, mold placement, rehearsal defects);
- the hardened shapes of the PLAN-193 mold (``DRY`` set by a ``case`` on the
  argv, ``|| die "..."`` on single-command step anchors) emit and seed the
  next generation, in both grammars; a ``DRY`` in any other shape, a
  ``|| true`` suffix and a ``die`` message that runs a command are refused;
- mold selection: packs ranked by the version each pins; an older mold is
  refused when a newer pack exists, also when the newer pack's mold is not
  generator-compatible; an unrankable pack is a named refusal; the plan is
  named (--plan), its file must exist; tag and version collisions refused;
- infrastructure (rc 4): npm absent; any filesystem error no step names;
- the emitted script is ``bash -n`` clean and ceremony-lint clean (no
  BLOCKING), and its TODO(owner) guard refuses a real run and only warns in a
  dry run (executed in bash, not grepped);
- positive control on the REAL packs and the LIVE governance files: the tool
  builds from the newest real mold and refuses every older one; a newest
  real mold it refuses turns the control RED (named), never green; a
  generated script is itself a valid mold for the next generation.
"""
from __future__ import annotations

import base64
import contextlib
import difflib
import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".claude" / "scripts" / "re-pin-codex.py"
LINT = REPO / ".claude" / "scripts" / "check-ceremony-script.py"

_HOOKS_DIR = REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


MOD = _load("re_pin_codex", SCRIPT)

PLATFORM = "darwin-arm64"
TRIPLE = "aarch64-apple-darwin"
ALIAS = "@openai/codex-darwin-arm64"
MANIFEST_PATH = f"{ALIAS}/vendor/{TRIPLE}/bin/codex"
MEMBER = f"package/vendor/{TRIPLE}/bin/codex"
OLD_SHA = "b" * 64
PLAN = "PLAN-900"
MOLD_REL = f".claude/plans/{PLAN}/codex-pin-02/OWNER-PIN-SIGN.sh"
REGISTRY_ARGS = ["--registry=https://registry.npmjs.org/",
                 "--@openai:registry=https://registry.npmjs.org/"]
PIN_TEXT = (
    "# Codex CLI version pin (synthetic)\n"
    "#\n"
    "# older paragraph about 0.2.0\n"
    ">=0.1.0,<0.3.0\n"
)

SYN_MOLD = """#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: molde sintético do teste.
# OWNER-PIN-SIGN.sh — cerimônia sintética 0.1.0 -> 0.2.0.
set -euo pipefail

DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
D=.claude/plans/PLAN-900/codex-pin-02
SENT_LIVE="$D/pin-02-approved.md"
SENT="$SENT_LIVE"
DST_PIN=.claude/governance/codex-cli-pin.txt
DST_MAN=.claude/governance/codex-cli-pin-manifest.json
SRC_PIN="$D/codex-cli-pin.txt.new"
SRC_MAN="$D/codex-cli-pin-manifest.json.new"
NEW_RANGE='>=0.1.0,<0.3.0'
NEW_VERSION='"package_version": "0.2.0"'
NEW_SHA='""" + OLD_SHA + """'
BAK=$(mktemp -d "${TMPDIR:-/tmp}/pinbak.XXXXXX")

die() { printf 'FAIL: %s\\n' "$*" >&2; exit 1; }
say() { printf '== %s\\n' "$*"; }
trap 'rc=$?; [ $rc -ne 0 ] && printf "restaurado\\n" >&2' EXIT

say "P0 pré-condições"
HEAD_SHA=$(git rev-parse HEAD)
say "3/7 aplicar"
cp "$SRC_PIN" "$DST_PIN"
cp "$SRC_MAN" "$DST_MAN"
say "4/7 verificar"
python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)" >"$BAK/verify.out" 2>&1 || die "reprovou"
grep -q '"status": "verified"' "$BAK/verify.out" || die "sem status verified"
bash .claude/scripts/local/pair-rail-gate.sh --phase 6
say "7/7 commit"
git commit -q -F - <<MSG
ceremony(PLAN-900): re-pin codex-cli 0.1.0 -> 0.2.0

texto antigo do molde

Sentinel: $SENT (Anchor-SHA $HEAD_SHA)
MSG
trap - EXIT
printf 'feito\\n'
"""

#: A constants-block mold that LACKS most keys: refused by name (it stands
#: for any newest mold this generator cannot build from).
CONSTANTS_MOLD = """#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: molde sintético (gramática de constantes).
set -euo pipefail
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
# ---------------------------------------------------------------- constantes
PLAN=PLAN-900
PACK_TAG=09
NEW_VER=0.9.0
D=.claude/plans/$PLAN/codex-pin-$PACK_TAG
# ------------------------------------------------------------ fim constantes
die() { printf 'FAIL: %s\\n' "$*" >&2; exit 1; }
"""

CONST_TAG = "029"
CONST_MOLD_REL = f".claude/plans/{PLAN}/codex-pin-{CONST_TAG}/OWNER-PIN-SIGN.sh"
#: A COMPLETE constants-block mold (the PLAN-193 W2 generation's grammar,
#: reduced to what the parser keys on). Its tag (029 for 0.2.9) follows no
#: rule of this tool, as a hand-built pack may not.
CONST_MOLD = """#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: molde sintético (gramática de constantes).
# OWNER-PIN-SIGN.sh — cerimônia sintética 0.2.0 -> 0.2.9 (PLAN-900).
set -euo pipefail
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
# ---------------------------------------------------------------- constantes
PLAN=PLAN-900
PACK_TAG=029
OLD_VER=0.2.0
NEW_VER=0.2.9
LOWER=0.1.0
OLD_UPPER=0.3.0
NEW_UPPER=0.3.0
NEW_PUBLISHED=2026-09-01
TRIPLE=aarch64-apple-darwin
OLD_SHA=""" + OLD_SHA + """
NEW_SHA=""" + "c" * 64 + """
NEW_INTEGRITY='sha512-""" + "C" * 86 + """=='
# sha256 dos canônicos vivos quando o pack foi montado (guard de deriva)
BASE_PIN_SHA256=""" + "d" * 64 + """
BASE_MAN_SHA256=""" + "e" * 64 + """
SRC_PIN_SHA256=""" + "f" * 64 + """
SRC_MAN_SHA256=""" + "1" * 64 + """
GA_TAG=v9.8.7
COAUTHOR='Autor Sintético <noreply@example.invalid>'
REMOTE_SLUG='Canhada-Labs/ceo-orchestration'
T2_NODE='.claude/hooks/tests/test_x.py::T::test_y'
SIGNERS=.claude/sentinel-signers.txt
SIGNER_REGISTRY=.claude/security/sentinel-signers-registry.yaml
GPG_VERIFY_LIB=.claude/hooks/_lib/gpg_verify.py
SIGNER_REGISTRY_LIB=.claude/hooks/_lib/sentinel_signers.py
D=.claude/plans/$PLAN/codex-pin-$PACK_TAG
# ------------------------------------------------------------ fim constantes
NEW_RANGE=">=$LOWER,<$NEW_UPPER"
SENT_LIVE="$D/pin-$PACK_TAG-approved.md"
SENT="$SENT_LIVE"
DST_PIN=.claude/governance/codex-cli-pin.txt
DST_MAN=.claude/governance/codex-cli-pin-manifest.json
SRC_PIN="$D/codex-cli-pin.txt.new"
SRC_MAN="$D/codex-cli-pin-manifest.json.new"
PACK_FILES="$SENT_LIVE $SRC_PIN $SRC_MAN $D/OWNER-PIN-SIGN.sh $D/rehearse-pin-$PACK_TAG.sh $D/README.md"
BAK=$(mktemp -d "${TMPDIR:-/tmp}/pinbak.XXXXXX")
FZ="$BAK/frozen"; mkdir "$FZ"
die() { printf 'FAIL: %s\\n' "$*" >&2; exit 1; }
say() { printf '== %s\\n' "$*"; }
sha256f() { shasum -a 256 "$1" | awk '{print $1}'; }
trap 'rc=$?; [ $rc -ne 0 ] && printf "restaurado\\n" >&2' EXIT
verify_pin() {  # $1 = arquivo de saída
  local vrc=0
  python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)" \\
    >"$1" 2>"$1.err" || vrc=$?
  printf '%s' "$vrc"
}
check_verify_json() { grep -q "\\"status\\": \\"$2\\"" "$1"; }
say "P0 pré-condições"
cp "$SRC_PIN" "$FZ/pin"; cp "$SRC_MAN" "$FZ/man"
[ "$(sha256f "$FZ/pin")" = "$SRC_PIN_SHA256" ] || die "pin não é o declarado"
[ "$(sha256f "$FZ/man")" = "$SRC_MAN_SHA256" ] || die "manifesto não é o declarado"
say "1/7 Anchor-SHA"
HEAD_SHA=$(git rev-parse HEAD)
say "3/7 aplicar"
for d in "$DST_PIN" "$DST_MAN"; do [ -L "$d" ] && die "destino é symlink: $d"; done
cp "$FZ/pin" "$DST_PIN"
cp "$FZ/man" "$DST_MAN"
say "4/7 verificar"
vrc=$(verify_pin "$BAK/verify.out")
[ "$vrc" = "0" ] || { cat "$BAK/verify.out" >&2; die "reprovou"; }
VERIFIED_PAYLOAD=$(check_verify_json "$BAK/verify.out" verified ok "$NEW_SHA" "$NEW_SHA") \\
  || { cat "$BAK/verify.out" >&2; die "campos inesperados"; }
say "7/7 commit"
TREE=$(git write-tree)
MSG="$BAK/msg"
printf 'ceremony(%s): re-pin codex-cli %s -> %s\\n' "$PLAN" "$OLD_VER" "$NEW_VER" >"$MSG"
NEWC=$(git commit-tree "$TREE" -p "$HEAD_SHA" -F "$MSG")
git update-ref HEAD "$NEWC" "$HEAD_SHA"
trap - EXIT
printf 'feito\\n'
"""

#: CONST_MOLD in the shapes the pin lane's hardening gave the PLAN-193 mold
#: after its first draft (C-R1-01 re-probe, S357): DRY set by a ``case`` on
#: the argv (anything but no argument or exactly ``--dry-run`` exits), and
#: ``|| die "..."`` appended to single-command step anchors.
_DRY_LINE = 'DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1\n'
_DRY_CASE = ('case "$#:${1:-}" in\n'
             "  0:) DRY=0 ;;\n"
             "  1:--dry-run) DRY=1 ;;\n"
             "  *) printf 'uso: bash %s [--dry-run]\\n' \"$0\" >&2; exit 1 ;;\n"
             "esac\n")
_MAN_APPLY = 'cp "$FZ/man" "$DST_MAN"\n'
_COMMIT_TREE = 'NEWC=$(git commit-tree "$TREE" -p "$HEAD_SHA" -F "$MSG")\n'
CONST_MOLD_HARDENED = (CONST_MOLD.replace(_DRY_LINE, _DRY_CASE)
                       .replace(_MAN_APPLY, _MAN_APPLY[:-1]
                                + ' || die "não consegui aplicar $DST_MAN"\n')
                       .replace(_COMMIT_TREE, _COMMIT_TREE[:-1]
                                + ' || die "commit-tree falhou — nada foi commitado"\n'))

CONST_REHEARSAL = """#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: ensaio sintético.
# rehearse-pin-029.sh — ensaio sintético do PLAN-900 (0.2.9).
set -euo pipefail
PACK_DIR=$(cd "$(dirname "$0")" && pwd -P)
SIGN_SRC="$PACK_DIR/OWNER-PIN-SIGN.sh"
const() { sed -n "s/^$1=//p" "$SIGN_SRC" | head -n 1 | sed "s/^'//; s/'\\$//"; }
NEW_VER=$(const NEW_VER); PACK_TAG=$(const PACK_TAG)
tgz="openai-codex-$NEW_VER-darwin-arm64.tgz"
printf 'ensaio do sentinel %s %s\\n' "$PACK_TAG" "$tgz"
"""

#: The literal scan the PLAN-193 rehearsal runs over its pack's ceremony
#: script (every line outside the constants block).
REHEARSAL_LITERAL_SCAN = (
    "awk '/^# -+ constantes$/{inb=1; next} /^# -+ fim constantes$/{inb=0; next} "
    "!inb{print FILENAME\":\"FNR\": \"$0}' \"$1\" | grep -E "
    "'0\\.1[0-9][0-9]\\.[0-9]|[0-9a-f]{64}|sha512-|v[0-9]+\\.[0-9]+\\.[0-9]+|Opus|Fable'")

FAKE_NPM = r'''#!/usr/bin/env python3
import json, os, shutil, sys
cfg = json.load(open(os.environ["RE_PIN_FAKE_NPM_CONFIG"], encoding="utf-8"))
with open(cfg["log"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(),
                         "cache": os.environ.get("npm_config_cache"),
                         "logs_dir": os.environ.get("npm_config_logs_dir"),
                         "logs_max": os.environ.get("npm_config_logs_max")}) + "\n")
args = sys.argv[1:]
cache = os.environ.get("npm_config_cache")
if cache:
    os.makedirs(cache, exist_ok=True)
    open(os.path.join(cache, "touched"), "w").close()
if args[:1] == ["view"]:
    doc = cfg["view"].get(args[1])
    if doc is None:
        print(json.dumps({"error": {"code": "E404", "summary": "No match"}}))
        sys.exit(1)
    print(json.dumps(doc))
    sys.exit(0)
if args[:1] == ["pack"]:
    if cfg.get("pack_forbidden"):
        sys.stderr.write("pack forbidden in this test\n")
        sys.exit(97)
    dest = args[args.index("--pack-destination") + 1]
    src = cfg["pack"][args[1]]
    shutil.copyfile(src, os.path.join(dest, os.path.basename(src)))
    print(json.dumps([{"filename": os.path.basename(src)}]))
    sys.exit(0)
sys.exit(64)
'''


def _prose(text: str) -> str:
    """The comment prose of a pin file, unwrapped (wrap points are not asserted)."""
    return " ".join(ln[2:] for ln in text.splitlines() if ln.startswith("# "))


def _sri(path: Path) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(path.read_bytes()).digest()).decode()


def _add_bytes(tf: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o755
    tf.addfile(info, io.BytesIO(data))


def _add_link(tf: tarfile.TarFile, name: str, linkname: str, hard: bool = False) -> None:
    info = tarfile.TarInfo(name)
    info.type = tarfile.LNKTYPE if hard else tarfile.SYMTYPE
    info.linkname = linkname
    tf.addfile(info)


# A member spec: ("file", name, bytes) | ("sym", name, linkname) | ("hard", name, linkname)
MemberSpec = Tuple[str, str, Any]


def _ustar(name: str, data: bytes) -> bytes:
    """One raw USTAR member (header + data + padding), for hand-built
    archives whose block layout tarfile's writer would not produce."""
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o755
    return (info.tobuf(format=tarfile.USTAR_FORMAT) + data
            + b"\0" * ((512 - len(data) % 512) % 512))


def _raw_member(name: str, data: bytes = b"", kind: bytes = b"0", link: str = "",
                magic: bytes = b"ustar\x0000", prefix: bytes = b"",
                size: Optional[int] = None, ck_fmt: bytes = b"%06o\x00 ") -> bytes:
    """One header block written field by field (plus data and padding), for
    header shapes tarfile's writer would not produce. ``ck_fmt`` formats the
    checksum (tarfile writes ``%06o\\0 ``, node-tar ``%06o \\0``)."""
    block = bytearray(512)
    raw_name = name.encode("utf-8")
    block[0:len(raw_name)] = raw_name
    block[100:108] = b"0000755\x00"
    block[108:116] = b"0000000\x00"
    block[116:124] = b"0000000\x00"
    block[124:136] = b"%011o\x00" % (len(data) if size is None else size)
    block[136:148] = b"%011o\x00" % 1700000000
    block[148:156] = b" " * 8
    block[156:157] = kind
    raw_link = link.encode("utf-8")
    block[157:157 + len(raw_link)] = raw_link
    block[257:265] = magic
    block[345:345 + len(prefix)] = prefix
    block[148:156] = ck_fmt % sum(block)
    return bytes(block) + data + b"\0" * ((512 - len(data) % 512) % 512)


def _pax(kind: bytes, records: Dict[str, str]) -> bytes:
    """A pax extension header (``x`` local, ``g`` global) carrying ``records``."""
    body = b""
    for key, value in records.items():
        rec = f" {key}={value}\n".encode("utf-8")
        n = len(rec) + 1
        while len(str(n)) + len(rec) != n:
            n = len(str(n)) + len(rec)
        body += str(n).encode("ascii") + rec
    return _raw_member("././@PaxHeader", body, kind=kind)


_PKG_JSON = json.dumps({"name": "@openai/codex", "version": f"0.3.0-{PLATFORM}"}).encode()
_TAR_END = b"\0" * 1024


def _header_shape_cases() -> Dict[str, bytes]:
    """Tar streams (uncompressed) outside the one header shape the tool
    models. All but the last were pinned before C-R3M-01 (rc 0). On the
    first six the two tar readers disagree about what lands on the payload
    path (Python's tarfile vs npm's node-tar 7.x, extracting as pacote
    does); the rest are refused because they sit outside the shape."""
    pkg = _raw_member("package/package.json", _PKG_JSON)
    measured = _ustar(MEMBER, b"measured")
    hidden = _ustar(MEMBER, b"installed")
    long_name = "package/" + "d" * 100 + "/codex"
    return {
        # tarfile renames the plain payload member to the GLOBAL pax path and
        # keeps the local-pax one; node-tar ignores a global path
        "a pax global path (the C-R3M-01 shape)": (
            _pax(b"g", {"path": "package/decoy"}) + pkg
            + _pax(b"x", {"path": MEMBER}) + _ustar("package/x-benign", b"measured")
            + hidden + _TAR_END),
        # node-tar skips the header (linkpath forbidden) and reads its body as headers
        "a regular file carrying a link name": (
            pkg + measured + _raw_member("package/README", hidden, link="x") + _TAR_END),
        # node-tar parses the checksum from 12 bytes: the digits fuse with the type
        "a checksum field with no terminator": (
            pkg + measured + _raw_member("package/README", hidden, ck_fmt=b"%08o")
            + _TAR_END),
        # tarfile does not skip a link's body; node-tar does
        "a symlink with a body": (
            pkg + _raw_member("package/README", measured, kind=b"2", link="docs") + _TAR_END),
        # tarfile joins the prefix whatever the magic; node-tar only under ustar
        "a GNU-magic header with a prefix": (
            pkg + _raw_member("codex", b"measured", magic=b"ustar  \x00",
                              prefix=f"package/vendor/{TRIPLE}/bin".encode()) + _TAR_END),
        # node-tar turns a '0' named '.../' into a directory
        "a regular file whose name ends in '/'": (
            pkg + _raw_member(MEMBER + "/", b"measured") + _TAR_END),
        "a local pax header": (
            pkg + _pax(b"x", {"comment": "c"}) + measured + _TAR_END),
        "a GNU long-name header": (
            pkg + measured + _raw_member("././@LongLink", long_name.encode() + b"\0", kind=b"L")
            + _raw_member(long_name[:100], b"x") + _TAR_END),
        "a contiguous-file member": (
            pkg + _raw_member(MEMBER, b"measured", kind=b"7") + _TAR_END),
        "a name that is not ASCII": (
            pkg + measured + _raw_member("package/résumé", b"x") + _TAR_END),
        "a directory with a size": (
            pkg + _raw_member("package/vendor/", kind=b"5", size=512) + measured + _TAR_END),
        "a member that runs past the end": pkg + _raw_member(MEMBER, b"measured", size=4096),
    }


def _header_shape_controls() -> Dict[str, bytes]:
    """Streams inside the modelled shape: they pin ``b"measured"``."""
    pkg = _raw_member("package/package.json", _PKG_JSON)
    return {
        "node-tar's checksum form and a directory": (
            pkg + _raw_member("package/vendor/", kind=b"5", ck_fmt=b"%06o \x00")
            + _raw_member(MEMBER, b"measured", ck_fmt=b"%06o \x00") + _TAR_END),
        "the payload path split into ustar prefix and name": (
            pkg + _raw_member("codex", b"measured", prefix=f"package/vendor/{TRIPLE}/bin".encode())
            + _TAR_END),
        "an unrelated symlink and hard link": (
            pkg + _ustar(MEMBER, b"measured")
            + _raw_member("package/README", kind=b"2", link="docs/README.md")
            + _raw_member("package/LICENSE", kind=b"1", link="package/package.json")
            + _TAR_END),
    }


def _build_tarball(path: Path, version: str, payload: bytes, kind: str = "file",
                   members: Optional[List[MemberSpec]] = None) -> None:
    with tarfile.open(str(path), "w:gz") as tf:
        _add_bytes(tf, "package/package.json",
                   json.dumps({"name": "@openai/codex",
                               "version": f"{version}-{PLATFORM}"}).encode())
        if members is not None:
            for spec, name, value in members:
                if spec == "file":
                    _add_bytes(tf, name, value)
                else:
                    _add_link(tf, name, value, hard=(spec == "hard"))
            return
        if kind in ("file", "dup"):
            _add_bytes(tf, MEMBER, payload)
        if kind == "dup":
            _add_bytes(tf, MEMBER, payload + b"-second")
        if kind == "symlink":
            _add_link(tf, MEMBER, "../../../../etc/passwd")


def _mold_for(version: str, tag: str) -> str:
    """SYN_MOLD re-targeted to another pack (tag) pinning ``version``."""
    return (SYN_MOLD.replace("codex-pin-02", f"codex-pin-{tag}")
            .replace("pin-02-approved", f"pin-{tag}-approved")
            .replace('"package_version": "0.2.0"', f'"package_version": "{version}"'))


class _RePinBase(TestEnvContext):
    """Fixture repo + fake npm on PATH; the tool runs in-process."""

    def setUp(self) -> None:
        super().setUp()
        self.root = self._tmp_root / "rp"
        self.repo = self.root / "repo"
        gov = self.repo / ".claude" / "governance"
        gov.mkdir(parents=True)
        (gov / "codex-cli-pin-manifest.json").write_text(json.dumps({
            "schema": 1, "package_version": "0.2.0",
            "npm_integrity": "sha512-" + "A" * 86 + "==",
            "payloads": {TRIPLE: {"path": MANIFEST_PATH, "sha256": OLD_SHA}},
        }, indent=2) + "\n", encoding="utf-8")
        (gov / "codex-cli-pin.txt").write_text(PIN_TEXT, encoding="utf-8")
        self.write_plan(PLAN)
        self.write_mold(SYN_MOLD)
        self.shim = self.root / "shim"
        self.shim.mkdir()
        npm = self.shim / "npm"
        npm.write_text(FAKE_NPM, encoding="utf-8")
        npm.chmod(0o755)
        self.log = self.root / "npm.log"
        self.cfg = self.root / "npm.json"
        self.tarballs = self.root / "tarballs"
        self.tarballs.mkdir()

    # -- fixtures ---------------------------------------------------------

    def write_plan(self, plan: str) -> None:
        path = self.repo / ".claude" / "plans" / f"{plan}-synthetic.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {plan} synthetic\n", encoding="utf-8")

    def write_mold(self, text: str, rel: str = MOLD_REL,
                   pins: Optional[str] = "0.2.0") -> Path:
        """The mold plus, unless ``pins`` is None, its pack's manifest .new."""
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        if pins is not None:
            (path.parent / "codex-cli-pin-manifest.json.new").write_text(json.dumps({
                "schema": 1, "package_version": pins,
                "npm_integrity": "sha512-" + "B" * 86 + "==",
                "payloads": {TRIPLE: {"path": MANIFEST_PATH, "sha256": OLD_SHA}},
            }, indent=2) + "\n", encoding="utf-8")
        return path

    def write_const_pack(self, mold: str = CONST_MOLD, rehearsal: Optional[str] = CONST_REHEARSAL,
                         rel: str = CONST_MOLD_REL, pins: str = "0.2.9",
                         readme: bool = True) -> Path:
        """A constants-block pack: the mold, its manifest .new, and (unless
        None) the rehearsal sibling and a README."""
        path = self.write_mold(mold, rel=rel, pins=pins)
        tag = path.parent.name.split("codex-pin-", 1)[1]
        if rehearsal is not None:
            (path.parent / f"rehearse-pin-{tag}.sh").write_text(rehearsal, encoding="utf-8")
        if readme:
            (path.parent / "README.md").write_text("# notas de desenho\n", encoding="utf-8")
        return path

    def configure(self, version: str, payload: bytes = b"codex payload bytes",
                  kind: str = "file", integrity: Optional[str] = None,
                  alias_version: Optional[str] = None, publish: bool = True,
                  pack_forbidden: bool = False,
                  members: Optional[List[MemberSpec]] = None,
                  published: Optional[str] = "2026-09-22T19:55:37.255Z") -> Path:
        tgz = self.tarballs / f"openai-codex-{version}-{PLATFORM}.tgz"
        _build_tarball(tgz, version, payload, kind, members)
        spec_plat = f"@openai/codex@{version}-{PLATFORM}"
        alias_v = alias_version or version
        view: Dict[str, Any] = {}
        if publish:
            view[f"@openai/codex@{version}"] = {
                "name": "@openai/codex", "version": version,
                "optionalDependencies": {
                    ALIAS: f"npm:@openai/codex@{alias_v}-{PLATFORM}",
                    "@openai/codex-linux-x64": f"npm:@openai/codex@{version}-linux-x64",
                },
                "dist": {"integrity": "sha512-" + "M" * 86 + "=="},
                "time": {version: published} if published else {},
                "dist-tags": {"latest": version},
            }
            view[spec_plat] = {"name": "@openai/codex", "version": f"{version}-{PLATFORM}",
                               "dist": {"integrity": integrity or _sri(tgz),
                                        "tarball": "https://registry.npmjs.org/@openai/"
                                                   f"codex/-/codex-{version}-{PLATFORM}.tgz"}}
        self.cfg.write_text(json.dumps({
            "log": str(self.log), "view": view, "pack": {spec_plat: str(tgz)},
            "pack_forbidden": pack_forbidden,
        }), encoding="utf-8")
        return tgz

    # -- running ----------------------------------------------------------

    def env(self, with_npm: bool = True) -> Dict[str, str]:
        path = str(self.shim) + os.pathsep + os.environ.get("PATH", "") if with_npm \
            else str(self.root / "no-npm-here")
        return {"PATH": path, "RE_PIN_FAKE_NPM_CONFIG": str(self.cfg)}

    def run_tool(self, *argv: str, with_npm: bool = True,
                 mold: Optional[str] = None, plan: Optional[str] = PLAN) -> Tuple[int, str, str]:
        args = [argv[0], "--mold", str(self.repo / (mold or MOLD_REL)),
                "--repo-root", str(self.repo), "--date", "2026-09-22"]
        if plan is not None:
            args += ["--plan", plan]
        args += list(argv[1:])
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, self.env(with_npm)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = MOD.main(args)
        return rc, out.getvalue(), err.getvalue()

    def npm_log(self) -> List[Dict[str, Any]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def npm_calls(self) -> List[List[str]]:
        return [entry["argv"] for entry in self.npm_log()]

    def pack_dir(self, tag: str, plan: str = PLAN) -> Path:
        return self.repo / ".claude" / "plans" / plan / f"codex-pin-{tag}"

    def assert_nothing_written(self, tag: str) -> None:
        parent = self.pack_dir(tag).parent
        self.assertFalse(os.path.lexists(self.pack_dir(tag)))
        self.assertEqual([p.name for p in parent.iterdir() if p.name.startswith(".re-pin")], [])


class RepinHappyPathTest(_RePinBase):

    def test_emits_pack_and_widens_range_upper_only(self) -> None:
        payload = b"\x7fELF fake codex 0.3.0"
        tgz = self.configure("0.3.0", payload=payload)
        rc, out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 0, err)
        summary = json.loads(out)
        sha = hashlib.sha256(payload).hexdigest()
        self.assertEqual(summary["status"], "emitted")
        self.assertEqual(summary["sha256"], sha)
        self.assertTrue(summary["widened"])
        self.assertEqual(summary["plan_id"], PLAN)
        pack = self.pack_dir("03")
        names = sorted(p.name for p in pack.iterdir())
        self.assertEqual(names, ["OWNER-PIN-SIGN.sh", "codex-cli-pin-manifest.json.new",
                                 "codex-cli-pin.txt.new", "pin-03-approved.md"])
        for p in pack.iterdir():
            self.assertEqual(p.stat().st_mode & 0o777, 0o644, p.name)
        manifest = json.loads((pack / "codex-cli-pin-manifest.json.new").read_text())
        self.assertEqual(manifest, {
            "schema": 1, "package_version": "0.3.0", "npm_integrity": _sri(tgz),
            "payloads": {TRIPLE: {"path": MANIFEST_PATH, "sha256": sha}}})
        pin = (pack / "codex-cli-pin.txt.new").read_text()
        self.assertTrue(pin.startswith(PIN_TEXT.rsplit(">=", 1)[0]))
        self.assertEqual(pin.splitlines()[-1], ">=0.1.0,<0.4.0")
        self.assertIn("TODO(owner)", pin)
        self.assertIn("widened <0.3.0 -> <0.4.0", _prose(pin))
        self.assertEqual(summary["todo_owner"], ["codex-cli-pin.txt.new", "pin-03-approved.md"])
        calls = self.npm_calls()
        self.assertEqual([c[0] for c in calls], ["view", "view", "pack"])
        self.assertIn("--ignore-scripts", calls[2])

    def test_every_npm_call_names_the_public_registry(self) -> None:
        # An .npmrc (``registry`` or the ``@openai:registry`` scope line) must
        # not choose where the measured bytes come from.
        self.configure("0.3.0")
        rc, out, err = self.run_tool("0.3.0", "--dry-run")
        self.assertEqual(rc, 0, err)
        calls = self.npm_calls()
        self.assertEqual(len(calls), 3)
        for argv in calls:
            self.assertEqual(argv[-2:], REGISTRY_ARGS, argv)
        self.assertEqual(json.loads(out)["registry"], "https://registry.npmjs.org/")

    def test_npm_cache_and_logs_live_in_the_removed_temp_dir(self) -> None:
        self.configure("0.3.0", payload=b"cache")
        rc, _out, err = self.run_tool("0.3.0", "--dry-run")
        self.assertEqual(rc, 0, err)
        entries = self.npm_log()
        self.assertEqual(len(entries), 3)
        for entry in entries:
            cwd = os.path.realpath(entry["cwd"])
            self.assertTrue(os.path.realpath(entry["cache"]).startswith(cwd + os.sep), entry)
            self.assertTrue(os.path.realpath(entry["logs_dir"]).startswith(cwd + os.sep), entry)
            self.assertEqual(entry["logs_max"], "0")
            self.assertFalse(os.path.exists(entry["cwd"]), "npm's temp dir must be removed")

    def test_platform_defaults_to_the_manifest_triple(self) -> None:
        self.configure("0.3.0")
        rc, out, err = self.run_tool("0.3.0", "--dry-run")
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)["platform"], PLATFORM)
        self.assertIn(f"@openai/codex@0.3.0-{PLATFORM}", self.npm_calls()[1])

    def test_ceremony_script_values_header_and_commit(self) -> None:
        self.configure("0.3.0", payload=b"p")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 0, err)
        script = (self.pack_dir("03") / "OWNER-PIN-SIGN.sh").read_text()
        lines = script.splitlines()
        sha = hashlib.sha256(b"p").hexdigest()
        for expected in ("D=.claude/plans/PLAN-900/codex-pin-03",
                         'SENT_LIVE="$D/pin-03-approved.md"',
                         "NEW_RANGE='>=0.1.0,<0.4.0'",
                         "NEW_VERSION='\"package_version\": \"0.3.0\"'",
                         f"NEW_SHA='{sha}'",
                         "ceremony(PLAN-900): re-pin codex-cli 0.2.0 -> 0.3.0",
                         "Sentinel: $SENT (assinado, Anchor-SHA $HEAD_SHA)"):
            self.assertIn(expected, lines)
        self.assertTrue(lines[0].startswith("#!"))
        self.assertIn("AUTO-GENERATED", lines[1])
        flat = " ".join(lines)
        self.assertIn("Verificado na cerimônia, depois de aplicar: --verify-codex-pin = "
                      "verified; pair-rail-gate.sh --phase 6 OK.", flat)
        self.assertNotIn("texto antigo do molde", script)
        self.assertNotIn("handwritten-exception", script)
        self.assertNotIn(OLD_SHA, script)
        self.assertIn(hashlib.sha256(SYN_MOLD.encode()).hexdigest(), script)

    def test_range_left_alone_when_version_is_inside(self) -> None:
        self.configure("0.2.5")
        rc, out, err = self.run_tool("0.2.5")
        self.assertEqual(rc, 0, err)
        self.assertFalse(json.loads(out)["widened"])
        pack = self.pack_dir("02-5")
        pin = (pack / "codex-cli-pin.txt.new").read_text()
        self.assertEqual(pin.splitlines()[-1], ">=0.1.0,<0.3.0")
        self.assertIn("Range UNCHANGED", _prose(pin))
        self.assertIn("NEW_RANGE='>=0.1.0,<0.3.0'",
                      (pack / "OWNER-PIN-SIGN.sh").read_text().splitlines())

    def test_sentinel_draft_carries_the_measured_digests(self) -> None:
        tgz = self.configure("0.3.0", payload=b"payload")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 0, err)
        text = (self.pack_dir("03") / "pin-03-approved.md").read_text()
        self.assertEqual(sum(1 for ln in text.splitlines() if ln.startswith("Anchor-SHA:")), 1)
        self.assertIn(hashlib.sha256(b"payload").hexdigest(), text)
        self.assertIn(_sri(tgz), text)
        self.assertIn(tgz.name, text)
        self.assertIn("Plan: PLAN-900", text)
        # heredoc grammar: its step 1 fills only Anchor-SHA, so Data keeps
        # the generation date (the constants grammar renders a placeholder)
        self.assertIn("\nData: 2026-09-22\n", text)
        # the heredoc grammar regenerates its commit message: nothing inherited
        self.assertNotIn("Texto herdado", text)
        self.assertIn("Registry: `https://registry.npmjs.org/`", text)
        self.assertIn("-> dist.tarball = https://registry.npmjs.org/@openai/codex/-/"
                      f"codex-0.3.0-{PLATFORM}.tgz", text)
        self.assertIn(f"npm pack @openai/codex@0.3.0-{PLATFORM} " + " ".join(REGISTRY_ARGS), text)
        self.assertIn(f"Residual declarado pelo gerador: o caminho do payload (`{MANIFEST_PATH}`)",
                      text)
        self.assertNotIn(str(self._tmp_root), text)

    def test_dry_run_writes_nothing(self) -> None:
        self.configure("0.3.0", payload=b"dry")
        rc, out, err = self.run_tool("0.3.0", "--dry-run")
        self.assertEqual(rc, 0, err)
        summary = json.loads(out)
        self.assertEqual(summary["status"], "dry-run")
        self.assertEqual(summary["sha256"], hashlib.sha256(b"dry").hexdigest())
        self.assert_nothing_written("03")

    def test_offline_from_never_runs_npm_pack(self) -> None:
        tgz = self.configure("0.3.0", payload=b"offline", pack_forbidden=True)
        rc, out, err = self.run_tool("0.3.0", "--offline-from", str(tgz))
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)["sha256"], hashlib.sha256(b"offline").hexdigest())
        self.assertEqual([c[0] for c in self.npm_calls()], ["view", "view"])
        self.assertIn("--offline-from", (self.pack_dir("03") / "OWNER-PIN-SIGN.sh").read_text())

    def test_subprocess_entry_point(self) -> None:
        self.configure("0.3.0")
        env = dict(os.environ)
        env.update(self.env())
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "0.3.0", "--mold", str(self.repo / MOLD_REL),
             "--plan", PLAN, "--repo-root", str(self.repo), "--date", "2026-09-22",
             "--dry-run"],
            capture_output=True, text=True, env=env, timeout=120, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["status"], "dry-run")


class RepinVerificationTest(_RePinBase):

    def test_tarball_integrity_mismatch_is_rc3_and_writes_nothing(self) -> None:
        self.configure("0.3.0", integrity="sha512-" + "Z" * 86 + "==")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 3, err)
        self.assertIn("dist.integrity", err)
        self.assert_nothing_written("03")

    def test_offline_tarball_that_is_not_the_registry_artifact(self) -> None:
        self.configure("0.3.0", payload=b"registry")
        other = self.tarballs / "other.tgz"
        _build_tarball(other, "0.3.0", b"tampered")
        rc, _out, err = self.run_tool("0.3.0", "--offline-from", str(other))
        self.assertEqual(rc, 3, err)
        self.assert_nothing_written("03")

    def test_payload_member_shapes_refused(self) -> None:
        for kind in ("missing", "symlink", "dup"):
            with self.subTest(kind=kind):
                self.configure("0.3.0", kind=kind)
                rc, _out, err = self.run_tool("0.3.0")
                self.assertEqual(rc, 3, err)
                self.assert_nothing_written("03")

    def test_alias_naming_another_version_is_rc3(self) -> None:
        self.configure("0.3.0", alias_version="0.2.9")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 3, err)
        self.assertIn("optionalDependencies", err)

    def test_members_that_extraction_resolves_onto_the_payload_are_refused(self) -> None:
        # npm's extractor (pacote, strip: 1) lands these on the payload path,
        # and the LATER entry is what gets installed; the tool must not pin
        # the first.
        first = ("file", MEMBER, b"first")
        inner = MEMBER.split("/", 1)[1]
        cases = {
            "another top-level directory": [first, ("file", "other/" + inner, b"2nd")],
            "another top-level directory, first": [("file", "other/" + inner, b"2nd"), first],
            "'./' segment": [first, ("file", MEMBER.replace("/bin/codex", "/bin/./codex"), b"2nd")],
            "repeated '/'": [first, ("file", MEMBER.replace("package/", "package//"), b"2nd")],
            "letter case": [first, ("file", MEMBER.replace("/codex", "/CODEX"), b"2nd")],
            "'..' member anywhere": [first, ("file", "package/../evil", b"x")],
            "absolute member": [first, ("file", "/tmp/evil", b"x")],
            "hard link onto the payload": [("hard", MEMBER, "package/other"),
                                           ("file", "package/other", b"x")],
            "hard link pointing at the payload": [first, ("hard", "package/bin/codex", MEMBER)],
            "hard link via another top-level dir": [
                first, ("hard", "package/bin/codex", "other/" + inner)],
            "symlink pointing at the payload": [
                first, ("sym", "package/bin/codex", "../vendor/aarch64-apple-darwin/bin/codex")],
            "symlink on a parent directory": [
                ("sym", f"package/vendor/{TRIPLE}/bin", "/tmp"), first],
            "symlink on a parent, other top-level dir": [
                ("sym", f"other/vendor/{TRIPLE}/bin", "/tmp"), first],
            # node-tar strips the RAW first segment: './package/x' lands at
            # 'package/x', so this tarball has NO member at the payload path.
            "only a './package/...' member (installed elsewhere)": [
                ("file", "./" + MEMBER, b"dot")],
        }
        for label, members in cases.items():
            with self.subTest(case=label):
                self.configure("0.3.0", members=members)
                rc, _out, err = self.run_tool("0.3.0")
                self.assertEqual(rc, 3, f"{label}: {err}")
                self.assertNotIn("Traceback", err)
                self.assert_nothing_written("03")

    def _configure_raw(self, blob: bytes) -> None:
        """configure(), then replace the tarball with ``blob`` (and its
        integrity, so the sha512 check passes and the tar reader decides)."""
        tgz = self.configure("0.3.0")
        tgz.write_bytes(blob)
        cfg = json.loads(self.cfg.read_text(encoding="utf-8"))
        cfg["view"][f"@openai/codex@0.3.0-{PLATFORM}"]["dist"]["integrity"] = _sri(tgz)
        self.cfg.write_text(json.dumps(cfg), encoding="utf-8")

    def test_members_past_a_null_or_invalid_block_are_refused(self) -> None:
        """C-R2M-04: Python's tarfile stops listing at the first null block,
        or at an invalid header past offset 0; npm's extractor (node-tar,
        non-strict) skips such a block and installs what follows. Measured
        on crafted tarballs: without the zero-tail check the tool pinned A
        while node-tar extracted B. A second gzip member or bytes after the
        gzip stream are refused too (two readers could disagree there)."""
        pkg = _ustar("package/package.json",
                     json.dumps({"name": "@openai/codex",
                                 "version": f"0.3.0-{PLATFORM}"}).encode())
        a, b = _ustar(MEMBER, b"measured"), _ustar(MEMBER, b"installed")
        end = b"\0" * 1024
        cases = {
            "second payload past one null block": gzip.compress(pkg + a + b"\0" * 512 + b + end),
            "second payload past an invalid header": gzip.compress(pkg + a + b"A" * 512 + b + end),
            "only payload past one null block": gzip.compress(pkg + b"\0" * 512 + b + end),
            "bytes after the gzip stream": gzip.compress(pkg + a + end) + b"junk",
            "a second gzip member": gzip.compress(pkg + a + end) + gzip.compress(b + end),
        }
        for label, blob in cases.items():
            with self.subTest(case=label):
                self._configure_raw(blob)
                rc, _out, err = self.run_tool("0.3.0")
                self.assertEqual(rc, 3, f"{label}: {err}")
                self.assertNotIn("Traceback", err)
                self.assert_nothing_written("03")
        # positive control: the same hand-built layout with an all-zero tail
        # (end-of-archive blocks plus record padding) pins the measured bytes
        self._configure_raw(gzip.compress(pkg + a + end + b"\0" * 8192))
        rc, out, err = self.run_tool("0.3.0", "--dry-run")
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)["sha256"], hashlib.sha256(b"measured").hexdigest())

    def test_headers_outside_the_modelled_shape_are_refused(self) -> None:
        """C-R3M-01, closed by construction: only plain POSIX ustar headers of
        a regular file, directory or link are accepted, and tarfile must
        list what the header walk lists. The first case is the reviewer's
        PoC: tarfile hashed the local-pax member while node-tar installed
        the other one."""
        for label, stream in _header_shape_cases().items():
            with self.subTest(case=label):
                self._configure_raw(gzip.compress(stream))
                rc, _out, err = self.run_tool("0.3.0")
                self.assertEqual(rc, 3, f"{label}: {err}")
                self.assertNotIn("Traceback", err)
                self.assert_nothing_written("03")
        for label, stream in _header_shape_controls().items():
            with self.subTest(control=label):
                self._configure_raw(gzip.compress(stream + b"\0" * 8192))
                rc, out, err = self.run_tool("0.3.0", "--dry-run")
                self.assertEqual(rc, 0, f"{label}: {err}")
                self.assertEqual(json.loads(out)["sha256"],
                                 hashlib.sha256(b"measured").hexdigest())

    def test_decompressed_size_is_bounded(self) -> None:
        with mock.patch.object(MOD, "UNPACKED_MAX_BYTES", 4096):
            with self.assertRaises(MOD.RePinError) as ctx:
                MOD.hash_member(gzip.compress(b"\0" * 65536), MEMBER)
        self.assertEqual(ctx.exception.rc, 3)
        self.assertIn("unpacks past", str(ctx.exception))

    def test_benign_member_shapes_still_pin(self) -> None:
        cases = {
            "'./package/...' beside the payload (installed under package/)": [
                ("file", MEMBER, b"dot"), ("file", "./" + MEMBER, b"x")],
            "unrelated symlink": [("file", MEMBER, b"dot"),
                                  ("sym", "package/README", "docs/README.md")],
            "top-level file (the extractor skips it)": [("file", MEMBER, b"dot"),
                                                        ("file", "codex", b"x")],
            "other top-level dir, other path": [("file", MEMBER, b"dot"),
                                                ("file", "other/README", b"x")],
        }
        for label, members in cases.items():
            with self.subTest(case=label):
                self.configure("0.3.0", members=members)
                rc, out, err = self.run_tool("0.3.0", "--dry-run")
                self.assertEqual(rc, 0, f"{label}: {err}")
                self.assertEqual(json.loads(out)["sha256"], hashlib.sha256(b"dot").hexdigest())

    def test_offline_tarball_swapped_after_the_read_cannot_change_the_pin(self) -> None:
        # The integrity check and the member hash run on ONE in-memory read:
        # swapping the file on disk right after the sha512 (a concurrent
        # writer) must not make the tool pin the swapped payload.
        tgz = self.configure("0.3.0", payload=b"genuine", pack_forbidden=True)
        tampered = self.tarballs / "tampered.tgz"
        _build_tarball(tampered, "0.3.0", b"swapped")
        original = MOD.sri_sha512

        def swap_after_hashing(data: bytes) -> str:
            result = original(data)
            os.replace(str(tampered), str(tgz))
            return result

        with mock.patch.object(MOD, "sri_sha512", side_effect=swap_after_hashing):
            rc, out, err = self.run_tool("0.3.0", "--dry-run", "--offline-from", str(tgz))
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)["sha256"], hashlib.sha256(b"genuine").hexdigest())
        self.assertFalse(tampered.exists(), "the swap did not happen")

    def test_offline_from_must_be_a_regular_file(self) -> None:
        tgz = self.configure("0.3.0", pack_forbidden=True)
        link = self.tarballs / "link.tgz"
        link.symlink_to(tgz)
        fifo = self.tarballs / "fifo.tgz"
        os.mkfifo(str(fifo))
        for label, path in (("symlink", link), ("fifo", fifo), ("directory", self.tarballs),
                            ("missing", self.tarballs / "absent.tgz")):
            with self.subTest(case=label):
                rc, _out, err = self.run_tool("0.3.0", "--offline-from", str(path))
                self.assertEqual(rc, 2, f"{label}: {err}")
                self.assert_nothing_written("03")


class RepinInputRefusalTest(_RePinBase):

    def test_version_shapes_refused_before_any_npm_call(self) -> None:
        self.configure("0.3.0")
        for bad in ("0.3", "0.3.0-alpha.1", "latest", "v0.3.0", "0.3.0\n", "00.3.0"):
            with self.subTest(version=bad):
                rc, _out, err = self.run_tool(bad)
                self.assertEqual(rc, 2, err)
        self.assertEqual(self.npm_calls(), [])

    def test_not_an_upgrade_refused(self) -> None:
        for version in ("0.2.0", "0.1.9"):
            with self.subTest(version=version):
                self.configure(version)
                rc, _out, err = self.run_tool(version)
                self.assertEqual(rc, 2, err)
        self.assertEqual(self.npm_calls(), [])

    def test_existing_output_refused_before_download(self) -> None:
        self.configure("0.3.0")
        pack = self.pack_dir("03")
        pack.mkdir(parents=True)
        (pack / "keep.txt").write_text("mine")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 2, err)
        self.assertEqual((pack / "keep.txt").read_text(), "mine")
        self.assertEqual(self.npm_calls(), [])

    def test_unpublished_version_is_an_input_error(self) -> None:
        self.configure("0.3.0", publish=False)
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 2, err)
        self.assertIn("not published", err)

    def test_npm_absent_is_infrastructure(self) -> None:
        self.configure("0.3.0")
        rc, _out, err = self.run_tool("0.3.0", with_npm=False)
        self.assertEqual(rc, 4, err)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root ignores directory permissions")
    def test_unwritable_out_parent_is_an_input_refusal_not_a_traceback(self) -> None:
        self.configure("0.3.0")
        ro = self.root / "ro"
        ro.mkdir()
        ro.chmod(0o555)
        try:
            rc, _out, err = self.run_tool("0.3.0", "--out", str(ro / "pack"))
        finally:
            ro.chmod(0o755)
        self.assertEqual(rc, 2, err)
        self.assertIn("cannot write under", err)
        self.assertEqual(sorted(os.listdir(ro)), [])

    def test_unnamed_filesystem_error_maps_to_infrastructure(self) -> None:
        # Backstop of the exit contract: an OSError no step converts.
        with mock.patch.object(MOD, "run", side_effect=PermissionError(13, "denied")):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = MOD.main(["0.3.0", "--mold", str(self.repo / MOLD_REL)])
        self.assertEqual(rc, 4, err.getvalue())
        self.assertIn("filesystem (PermissionError)", err.getvalue())

    def test_mold_grammar_refusals(self) -> None:
        self.configure("0.3.0")
        verify = next(ln for ln in SYN_MOLD.splitlines() if "--verify-codex-pin" in ln)
        verified = next(ln for ln in SYN_MOLD.splitlines() if '"status": "verified"' in ln)
        cases = {
            "stale version literal in the body": SYN_MOLD.replace(
                'say "7/7 commit"', 'say "7/7 commit"\necho "fixo em 0.2.0"'),
            "stale pack path in the body": SYN_MOLD.replace(
                'say "7/7 commit"', 'say "7/7 commit"\nls .claude/plans/PLAN-900/codex-pin-02'),
            "missing NEW_SHA line": SYN_MOLD.replace("NEW_SHA='" + OLD_SHA + "'\n", ""),
            "duplicated D line": SYN_MOLD.replace(
                "SENT=\"$SENT_LIVE\"", "SENT=\"$SENT_LIVE\"\nD=.claude/plans/PLAN-900/x"),
            "quoted heredoc": SYN_MOLD.replace("<<MSG", "<<'MSG'"),
            "foreign SRC_PIN": SYN_MOLD.replace('SRC_PIN="$D/codex-cli-pin.txt.new"',
                                                'SRC_PIN="$D/pin.txt"'),
            "code before set -e": SYN_MOLD.replace("# OWNER-PIN-SIGN.sh", "echo hi"),
            "CRLF": SYN_MOLD.replace("\n", "\r\n"),
            "no trap": SYN_MOLD.replace("trap 'rc=$?;", "true 'rc=$?;"),
            "no --verify-codex-pin (ADR-182 §5 step 4)": SYN_MOLD.replace(verify + "\n", ""),
            "no 'verified' check": SYN_MOLD.replace(verified + "\n", ""),
            "'verified' check that never dies": SYN_MOLD.replace(
                verified, "grep -q '\"status\": \"verified\"' \"$BAK/verify.out\" || true"),
            "verification only BEFORE the apply": SYN_MOLD.replace(
                verify + "\n", "").replace(verified + "\n", "").replace(
                'say "3/7 aplicar"', verify + "\n" + verified + '\nsay "3/7 aplicar"'),
            "verification commented out": SYN_MOLD.replace(verify, "# " + verify),
            "no DRY definition": SYN_MOLD.replace(_DRY_LINE, ""),
            "DRY assigned twice": SYN_MOLD.replace(_DRY_LINE, _DRY_LINE + "DRY=0\n"),
            "manifest apply swallowing its failure": SYN_MOLD.replace(
                'cp "$SRC_MAN" "$DST_MAN"', 'cp "$SRC_MAN" "$DST_MAN" || true'),
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                self.write_mold(text)
                rc, _out, err = self.run_tool("0.3.0")
                self.assertEqual(rc, 2, f"{label}: {err}")
        self.assertEqual(self.npm_calls(), [])

    def test_incomplete_constants_block_is_refused_by_name(self) -> None:
        self.configure("0.3.0")
        self.write_mold(CONSTANTS_MOLD)
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 2, err)
        self.assertIn(MOD.GRAMMAR_CONSTANTS, err)
        self.assertIn("the block lacks", err)
        self.assertIn("NEW_SHA", err)
        self.assertEqual(self.npm_calls(), [])

    def test_mold_outside_the_repo_refused(self) -> None:
        self.configure("0.3.0")
        outside = self.root / "OWNER-PIN-SIGN.sh"
        outside.write_text(SYN_MOLD, encoding="utf-8")
        rc, _out, err = self.run_tool("0.3.0", mold=str(outside))
        self.assertEqual(rc, 2, err)
        self.assertIn("inside the repository", err)

    def test_manifest_and_pin_shapes_refused(self) -> None:
        self.configure("0.3.0")
        gov = self.repo / ".claude" / "governance"
        good_manifest = (gov / "codex-cli-pin-manifest.json").read_text()
        data = json.loads(good_manifest)
        second = dict(data, payloads=dict(data["payloads"], **{
            "x86_64-apple-darwin": {"path": "@openai/codex-darwin-x64/vendor/"
                                    "x86_64-apple-darwin/bin/codex", "sha256": "c" * 64}}))
        unknown_triple = dict(data, payloads={"riscv64-unknown-none": {
            "path": MANIFEST_PATH, "sha256": OLD_SHA}})
        cases = {
            "second triple": (json.dumps(second), PIN_TEXT),
            "unknown key": (json.dumps(dict(data, extra=1)), PIN_TEXT),
            "triple with no npm platform": (json.dumps(unknown_triple), PIN_TEXT),
            "code line in the pin": (good_manifest, "# a\nsomething=1\n>=0.1.0,<0.3.0\n"),
            "range not last": (good_manifest, ">=0.1.0,<0.3.0\n# trailing comment\n"),
            "below the lower bound": (good_manifest, "# a\n>=0.5.0,<0.6.0\n"),
        }
        for label, (manifest, pin) in cases.items():
            with self.subTest(case=label):
                (gov / "codex-cli-pin-manifest.json").write_text(manifest)
                (gov / "codex-cli-pin.txt").write_text(pin)
                rc, _out, err = self.run_tool("0.3.0")
                self.assertEqual(rc, 2, f"{label}: {err}")

    def test_platform_that_is_not_the_pinned_triple_refused(self) -> None:
        self.configure("0.3.0")
        rc, _out, err = self.run_tool("0.3.0", "--platform", "linux-x64")
        self.assertEqual(rc, 2, err)
        self.assertIn("exactly one triple", err)
        self.assertEqual(self.npm_calls(), [])


class RepinMoldSelectionTest(_RePinBase):
    """The mold is the newest pack's; the plan is named, never inherited."""

    def test_older_mold_refused_when_a_newer_pack_exists(self) -> None:
        self.configure("0.3.0")
        newer = f".claude/plans/{PLAN}/codex-pin-02-5/OWNER-PIN-SIGN.sh"
        self.write_mold(_mold_for("0.2.5", "02-5"), rel=newer, pins="0.2.5")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 2, err)
        self.assertIn("newest pack pins 0.2.5", err)
        self.assertIn(newer, err)
        self.assertEqual(self.npm_calls(), [])
        rc, out, err = self.run_tool("0.3.0", "--dry-run", mold=newer)
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)["mold_rel"], newer)

    def test_ranking_is_by_pinned_version_not_by_plan_number(self) -> None:
        self.configure("0.3.0")
        self.write_plan("PLAN-950")
        later_plan_older_pin = ".claude/plans/PLAN-950/codex-pin-01/OWNER-PIN-SIGN.sh"
        self.write_mold(_mold_for("0.1.5", "01").replace("PLAN-900/", "PLAN-950/"),
                        rel=later_plan_older_pin, pins="0.1.5")
        rc, _out, err = self.run_tool("0.3.0", "--dry-run")
        self.assertEqual(rc, 0, err)
        rc, _out, err = self.run_tool("0.3.0", "--dry-run", mold=later_plan_older_pin)
        self.assertEqual(rc, 2, err)
        self.assertIn("newest pack pins 0.2.0", err)

    def test_no_downgrade_when_the_newest_mold_is_not_generator_compatible(self) -> None:
        # The class of C-R1-01: the newest pack uses a grammar this generator
        # does not model; falling back to the older (parseable) mold would
        # drop what the newer pack hardened.
        self.configure("0.3.0")
        newest = f".claude/plans/{PLAN}/codex-pin-09/OWNER-PIN-SIGN.sh"
        self.write_mold(CONSTANTS_MOLD, rel=newest, pins="0.2.9")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 2, err)
        self.assertIn("newest pack pins 0.2.9", err)
        rc, _out, err = self.run_tool("0.3.0", mold=newest)
        self.assertEqual(rc, 2, err)
        self.assertIn(MOD.GRAMMAR_CONSTANTS, err)
        row = MOD.newest_mold(self.repo)
        self.assertEqual((row["rel"], row["compatible"]), (newest, False))
        self.assertIn(MOD.GRAMMAR_CONSTANTS, row["reason"])
        self.assertEqual(self.npm_calls(), [])

    def test_a_second_mold_of_the_newest_pack_that_does_not_parse_blocks(self) -> None:
        self.configure("0.3.0")
        twin = ".claude/plans/PLAN-900/codex-pin-02-hand/OWNER-PIN-SIGN.sh"
        self.write_mold(CONSTANTS_MOLD, rel=twin, pins="0.2.0")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 2, err)
        self.assertIn("not generator-compatible", err)
        self.assertIn(twin, err)

    def test_unrankable_pack_is_a_named_refusal(self) -> None:
        self.configure("0.3.0")
        stray = ".claude/plans/PLAN-900/codex-pin-xx/OWNER-PIN-SIGN.sh"
        self.write_mold(_mold_for("0.2.9", "xx"), rel=stray, pins=None)
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 2, err)
        self.assertIn("cannot be established", err)
        self.assertIn(stray, err)
        with self.assertRaises(MOD.RePinError):
            MOD.newest_mold(self.repo)

    def test_mold_version_must_match_its_pack_manifest(self) -> None:
        self.configure("0.3.0")
        self.write_mold(SYN_MOLD, pins="0.2.1")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 2, err)
        self.assertIn("NEW_VERSION 0.2.0", err)

    def test_plan_is_required_and_its_file_must_exist(self) -> None:
        self.configure("0.3.0")
        rc, _out, err = self.run_tool("0.3.0", plan=None)
        self.assertEqual(rc, 2, err)
        self.assertIn("--plan", err)
        rc, _out, err = self.run_tool("0.3.0", plan="PLAN-777")
        self.assertEqual(rc, 2, err)
        self.assertIn("no plan file .claude/plans/PLAN-777-*.md", err)
        rc, _out, err = self.run_tool("0.3.0", plan="PLAN-7")
        self.assertEqual(rc, 2, err)
        self.assertEqual(self.npm_calls(), [])

    def test_pack_lands_in_the_named_plan_not_the_molds(self) -> None:
        self.configure("0.3.0")
        self.write_plan("PLAN-901")
        rc, out, err = self.run_tool("0.3.0", plan="PLAN-901")
        self.assertEqual(rc, 0, err)
        summary = json.loads(out)
        self.assertEqual(summary["pack_dir"], ".claude/plans/PLAN-901/codex-pin-03")
        text = (self.pack_dir("03", plan="PLAN-901") / "pin-03-approved.md").read_text()
        self.assertIn("Plan: PLAN-901", text)
        self.assert_nothing_written("03")

    def test_tag_used_anywhere_under_plans_is_refused(self) -> None:
        self.configure("0.3.0")
        self.write_plan("PLAN-901")
        clash = self.pack_dir("03", plan="PLAN-950")
        clash.mkdir(parents=True)
        rc, _out, err = self.run_tool("0.3.0", plan="PLAN-901")
        self.assertEqual(rc, 2, err)
        self.assertIn("pack tag '03' is already used", err)
        self.assertEqual(self.npm_calls(), [])

    def test_an_existing_pack_for_the_target_version_is_refused(self) -> None:
        self.configure("0.3.0")
        existing = f".claude/plans/{PLAN}/codex-pin-x3/OWNER-PIN-SIGN.sh"
        self.write_mold(_mold_for("0.3.0", "x3"), rel=existing, pins="0.3.0")
        rc, _out, err = self.run_tool("0.3.0", mold=existing)
        self.assertEqual(rc, 2, err)
        self.assertIn("a pack for 0.3.0 already exists", err)
        rc, _out, err = self.run_tool("0.3.0", "--dry-run", mold=existing)
        self.assertEqual(rc, 0, "a dry run may re-measure an existing pack: " + err)

    def test_pack_tag_is_this_tools_rule(self) -> None:
        self.assertEqual(MOD.pack_tag((0, 156, 0)), "0156")
        self.assertEqual(MOD.pack_tag((0, 156, 1)), "0156-1")
        # The rule can collide across versions; the used-tag refusal
        # (test_tag_used_anywhere_under_plans_is_refused) is what catches it.
        self.assertEqual(MOD.pack_tag((1, 23, 0)), MOD.pack_tag((12, 3, 0)))


class RepinEmittedScriptTest(_RePinBase):

    def _generated(self) -> Path:
        self.configure("0.3.0")
        rc, _out, err = self.run_tool("0.3.0")
        self.assertEqual(rc, 0, err)
        return self.pack_dir("03") / "OWNER-PIN-SIGN.sh"

    def test_bash_syntax_and_ceremony_lint(self) -> None:
        script = self._generated()
        proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True,
                              timeout=60, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lint = _load("check_ceremony_script_for_re_pin", LINT)
        body = script.read_text()
        self.assertTrue(lint.SHEBANG_RE.match(body) and lint.CEREMONY_OPS_RE.search(body),
                        "the emitted script must stay discoverable by the ceremony lint")
        rel = script.relative_to(self.repo).as_posix()
        blocking = [f for f in lint.lint_file(str(script), rel, "100644")
                    if f["sev"] == "BLOCKING"]
        self.assertEqual(blocking, [])

    def _run_guard(self, script: Path, dry: str, todo: bool) -> subprocess.CompletedProcess:
        lines = script.read_text().splitlines()
        start = next(i for i, ln in enumerate(lines) if ln.startswith("# [") and "re-pin-codex" in ln)
        end = next(i for i in range(start, len(lines)) if lines[i] == "fi")
        sent = self.root / "sent.md"
        pin = self.root / "pin.new"
        sent.write_text("TODO(owner): falta\n" if todo else "pronto\n")
        pin.write_text("# ok\n")
        harness = "\n".join([
            "set -euo pipefail",
            "die() { printf 'DIE: %s\\n' \"$*\"; exit 1; }",
            f"DRY={dry}", f"SENT='{sent}'", f"SRC_PIN='{pin}'",
        ] + lines[start:end + 1] + ["echo PASSED"])
        return subprocess.run(["bash", "-c", harness], capture_output=True, text=True,
                              timeout=60, check=False)

    def test_todo_guard_executes_as_declared(self) -> None:
        script = self._generated()
        real = self._run_guard(script, "0", todo=True)
        self.assertEqual(real.returncode, 1, real.stdout + real.stderr)
        self.assertIn("DIE: TODO(owner) pendente", real.stdout)
        rehearsal = self._run_guard(script, "1", todo=True)
        self.assertEqual(rehearsal.returncode, 0, rehearsal.stderr)
        self.assertIn("AVISO", rehearsal.stdout)
        self.assertIn("PASSED", rehearsal.stdout)
        filled = self._run_guard(script, "0", todo=False)
        self.assertEqual(filled.returncode, 0, filled.stderr)
        self.assertEqual(filled.stdout.strip(), "PASSED")

    def test_generated_script_is_a_valid_mold_for_the_next_generation(self) -> None:
        script = self._generated()
        gov = self.repo / ".claude" / "governance"
        shutil.copyfile(self.pack_dir("03") / "codex-cli-pin-manifest.json.new",
                        gov / "codex-cli-pin-manifest.json")
        shutil.copyfile(self.pack_dir("03") / "codex-cli-pin.txt.new", gov / "codex-cli-pin.txt")
        self.configure("0.4.0", payload=b"next")
        rc, out, err = self.run_tool("0.4.0", mold=str(script))
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out)["new_range"], ">=0.1.0,<0.5.0")
        nxt = (self.pack_dir("04") / "OWNER-PIN-SIGN.sh").read_text()
        self.assertEqual(nxt.count("# [.claude/scripts/re-pin-codex.py]"), 1)


class RepinConstantsGrammarTest(_RePinBase):
    """The constants-block grammar (the PLAN-193 W2 generation), end to end."""

    def _emit(self, *extra: str, version: str = "0.3.0") -> Tuple[Dict[str, Any], Path]:
        self.write_const_pack()
        self.configure(version)
        rc, out, err = self.run_tool(version, "--ga-tag", "v1.9.0", *extra, mold=CONST_MOLD_REL)
        self.assertEqual(rc, 0, err)
        summary = json.loads(out)
        return summary, self.repo / summary["pack_dir"]

    @staticmethod
    def _consts(script: str) -> Dict[str, str]:
        lines = script.splitlines()
        start = next(i for i, ln in enumerate(lines) if MOD._CONSTANTS_BLOCK_RE.fullmatch(ln))
        end = next(i for i, ln in enumerate(lines) if MOD._CONSTANTS_END_RE.fullmatch(ln))
        return dict(ln.split("=", 1) for ln in lines[start + 1:end]
                    if ln and not ln.startswith("#"))

    @staticmethod
    def _outside_owned(text: str) -> List[str]:
        """Lines from 'set -euo pipefail' on, minus the guard and the values
        of the rendered keys (the regions the generator owns)."""
        lines = text.split("\n")
        lines = lines[lines.index("set -euo pipefail"):]
        if MOD._GUARD[0] in lines:
            at = lines.index(MOD._GUARD[0])
            lines = lines[:at] + lines[at + len(MOD._GUARD):]
        out = []
        for ln in lines:
            m = MOD._CONST_LINE_RE.fullmatch(ln)
            if m is None or m.group(1) not in MOD._CONST_RENDERED:
                out.append(ln)
        return out

    def test_emits_the_pack_with_every_constant_rendered(self) -> None:
        summary, pack = self._emit()
        self.assertEqual(summary["grammar"], MOD.GRAMMAR_CONSTANTS)
        self.assertEqual(summary["pack_dir"], f".claude/plans/{PLAN}/codex-pin-03")
        self.assertEqual(sorted(p.name for p in pack.iterdir()), sorted(summary["files"]))
        self.assertEqual(sorted(summary["files"]), sorted([
            "OWNER-PIN-SIGN.sh", "README.md", "codex-cli-pin-manifest.json.new",
            "codex-cli-pin.txt.new", "pin-03-approved.md", "rehearse-pin-03.sh"]))
        script = (pack / "OWNER-PIN-SIGN.sh").read_text()
        c = self._consts(script)
        gov = self.repo / ".claude" / "governance"
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
        self.assertEqual({k: c[k] for k in ("PLAN", "PACK_TAG", "OLD_VER", "NEW_VER", "LOWER",
                                            "OLD_UPPER", "NEW_UPPER", "NEW_PUBLISHED", "GA_TAG",
                                            "OLD_SHA", "D")},
                         {"PLAN": PLAN, "PACK_TAG": "03", "OLD_VER": "0.2.0", "NEW_VER": "0.3.0",
                          "LOWER": "0.1.0", "OLD_UPPER": "0.3.0", "NEW_UPPER": "0.4.0",
                          "NEW_PUBLISHED": "2026-09-22", "GA_TAG": "v1.9.0", "OLD_SHA": OLD_SHA,
                          "D": ".claude/plans/$PLAN/codex-pin-$PACK_TAG"})
        self.assertEqual(c["NEW_SHA"], summary["sha256"])
        self.assertEqual(c["NEW_INTEGRITY"], f"'{summary['integrity']}'")
        self.assertEqual(c["BASE_PIN_SHA256"], sha(gov / "codex-cli-pin.txt"))
        self.assertEqual(c["BASE_MAN_SHA256"], sha(gov / "codex-cli-pin-manifest.json"))
        self.assertEqual(c["SRC_PIN_SHA256"], sha(pack / "codex-cli-pin.txt.new"))
        self.assertEqual(c["SRC_MAN_SHA256"], sha(pack / "codex-cli-pin-manifest.json.new"))
        for key in ("COAUTHOR", "REMOTE_SLUG", "T2_NODE", "SIGNERS", "SIGNER_REGISTRY",
                    "GPG_VERIFY_LIB", "SIGNER_REGISTRY_LIB"):
            self.assertIn(f"\n{key}={c[key]}\n", CONST_MOLD, key)
        sentinel = (pack / "pin-03-approved.md").read_text()
        for key in ("BASE_PIN_SHA256", "BASE_MAN_SHA256", "SRC_PIN_SHA256", "SRC_MAN_SHA256",
                    "NEW_SHA"):
            self.assertIn(c[key], sentinel, key)
        self.assertIn(c["NEW_INTEGRITY"].strip("'"), sentinel)
        self.assertIn(">=0.1.0,<0.4.0", sentinel)
        self.assertIn("Plan: PLAN-900", sentinel)
        readme = (pack / "README.md").read_text()
        self.assertIn("rehearse-pin-03.sh", readme)
        self.assertIn(f"codex-pin-{CONST_TAG}/README.md", readme)

    def test_body_is_the_molds_outside_the_owned_regions(self) -> None:
        _summary, pack = self._emit()
        script = (pack / "OWNER-PIN-SIGN.sh").read_text()
        self.assertEqual(self._outside_owned(script), self._outside_owned(CONST_MOLD))
        self.assertEqual(script.count(MOD._GUARD[0]), 1)
        self.assertTrue(script.split("\n")[1].startswith("# AUTO-GENERATED"))
        self.assertNotIn("cerimônia sintética", script, "the mold's header is regenerated")
        reh = (pack / "rehearse-pin-03.sh").read_text()
        self.assertTrue(reh.endswith("set -euo pipefail\n"
                                     + CONST_REHEARSAL.split("set -euo pipefail\n", 1)[1]))
        self.assertTrue(reh.split("\n")[1].startswith("# AUTO-GENERATED"))
        self.assertIn(f"codex-pin-{CONST_TAG}/rehearse-pin-{CONST_TAG}.sh", reh)
        self.assertNotIn("ensaio sintético do PLAN-900", reh, "the rehearsal header is regenerated")

    def test_generated_scripts_pass_bash_lint_and_the_rehearsal_literal_scan(self) -> None:
        _summary, pack = self._emit()
        lint = _load("check_ceremony_script_for_re_pin_const", LINT)
        for name in ("OWNER-PIN-SIGN.sh", "rehearse-pin-03.sh"):
            with self.subTest(script=name):
                path = pack / name
                proc = subprocess.run(["bash", "-n", str(path)], capture_output=True,
                                      text=True, timeout=60, check=False)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                rel = path.relative_to(self.repo).as_posix()
                self.assertEqual(lint.lint_file(str(path), rel, "100644"), [])
        scan = subprocess.run(["bash", "-c", REHEARSAL_LITERAL_SCAN, "scan",
                               str(pack / "OWNER-PIN-SIGN.sh")],
                              capture_output=True, text=True, timeout=60, check=False)
        self.assertEqual((scan.returncode, scan.stdout), (1, ""),
                         "a version/digest/tag literal outside the constants block")

    def test_generated_pack_is_a_valid_mold_for_the_next_generation(self) -> None:
        _summary, pack = self._emit()
        gov = self.repo / ".claude" / "governance"
        shutil.copyfile(pack / "codex-cli-pin-manifest.json.new", gov / "codex-cli-pin-manifest.json")
        shutil.copyfile(pack / "codex-cli-pin.txt.new", gov / "codex-cli-pin.txt")
        self.configure("0.4.0", payload=b"next")
        mold = (pack / "OWNER-PIN-SIGN.sh").relative_to(self.repo).as_posix()
        rc, out, err = self.run_tool("0.4.0", "--ga-tag", "v1.9.1", mold=mold)
        self.assertEqual(rc, 0, err)
        nxt = self.pack_dir("04")
        script = (nxt / "OWNER-PIN-SIGN.sh").read_text()
        self.assertEqual(script.count(MOD._GUARD[0]), 1)
        self.assertEqual(self._consts(script)["OLD_VER"], "0.3.0")
        self.assertEqual(json.loads(out)["new_range"], ">=0.1.0,<0.5.0")
        self.assertEqual((nxt / "rehearse-pin-04.sh").read_text().split("set -euo pipefail\n")[1],
                         CONST_REHEARSAL.split("set -euo pipefail\n", 1)[1])

    def test_hardened_shapes_emit_and_seed_the_next_generation(self) -> None:
        """C-R1-01 re-probe (S357): the pin lane hardened the PLAN-193 mold
        after the generator first modelled it (DRY from a ``case`` on argv,
        ``|| die`` on step anchors) and the generator refused it by name.
        Both shapes are modelled now, in both grammars."""
        self.assertNotEqual(CONST_MOLD_HARDENED.count(_DRY_CASE), 0)
        self.assertEqual(CONST_MOLD_HARDENED.count(" || die \"não consegui aplicar"), 1)
        self.assertEqual(CONST_MOLD_HARDENED.count(" || die \"commit-tree falhou"), 1)
        self.write_const_pack(mold=CONST_MOLD_HARDENED)
        self.configure("0.3.0")
        rc, out, err = self.run_tool("0.3.0", "--ga-tag", "v1.9.0", mold=CONST_MOLD_REL)
        self.assertEqual(rc, 0, err)
        pack = self.repo / json.loads(out)["pack_dir"]
        script = (pack / "OWNER-PIN-SIGN.sh").read_text()
        self.assertEqual(self._outside_owned(script), self._outside_owned(CONST_MOLD_HARDENED))
        guard_at = script.split("\n").index(MOD._GUARD[0])
        self.assertLess(script.split("\n").index("esac"), guard_at,
                        "DRY is set before the guard that reads it")
        proc = subprocess.run(["bash", "-n", str(pack / "OWNER-PIN-SIGN.sh")],
                              capture_output=True, text=True, timeout=60, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        gov = self.repo / ".claude" / "governance"
        shutil.copyfile(pack / "codex-cli-pin-manifest.json.new", gov / "codex-cli-pin-manifest.json")
        shutil.copyfile(pack / "codex-cli-pin.txt.new", gov / "codex-cli-pin.txt")
        self.configure("0.4.0", payload=b"next")
        mold = (pack / "OWNER-PIN-SIGN.sh").relative_to(self.repo).as_posix()
        rc, _out, err = self.run_tool("0.4.0", "--ga-tag", "v1.9.1", mold=mold)
        self.assertEqual(rc, 0, err)
        # the heredoc grammar reads DRY through the same predicate
        heredoc = SYN_MOLD.replace(_DRY_LINE, _DRY_CASE)
        self.assertNotEqual(heredoc, SYN_MOLD)
        parts = MOD.parse_mold(heredoc)
        self.assertEqual(parts["grammar"], MOD.GRAMMAR_HEREDOC)

    def test_sentinel_header_survives_the_molds_step_one_on_the_generation_day(self) -> None:
        """C-R2M-01: the constants mold's step 1 rewrites Anchor-SHA and Data
        with the signing day, and its rehearsal's p2 requires exactly those
        two lines to change (4 delta lines). Replayed here with TODAY equal to
        the run's --date: a sentinel rendered with Data = generation date
        would yield 2 delta lines and a same-day rehearsal would go red."""
        _summary, pack = self._emit()
        before = (pack / "pin-03-approved.md").read_text(encoding="utf-8")
        after = before
        # the step-1 python of the PLAN-193 constants mold, verbatim in shape
        for key, val in (("Anchor-SHA", "a" * 40), ("Data", "2026-09-22")):
            after, n = re.subn(r"^" + key + r":.*$", key + ": " + val, after, count=1,
                               flags=re.M)
            self.assertEqual(n, 1, key)
        delta = [ln for ln in difflib.unified_diff(before.splitlines(), after.splitlines(),
                                                   lineterm="", n=0)
                 if re.match(r"^[-+][^-+]", ln)]
        self.assertEqual(len(delta), 4, delta)
        self.assertEqual([ln for ln in delta if not re.match(r"^[-+](Anchor-SHA|Data): ", ln)],
                         [])

    def test_pack_declares_inherited_prose_and_the_rehearsal_order(self) -> None:
        """C-R2M-05/06: the README and the script header say the TODOs must be
        resolved and committed before the rehearsal; the README and the
        sentinel declare, by shape, that the mold's commit-message prose is
        copied without any check."""
        summary, pack = self._emit()
        flat = lambda s: " ".join(s.split())  # noqa: E731
        readme = flat((pack / "README.md").read_text())
        sentinel = flat((pack / "pin-03-approved.md").read_text())
        header = _prose((pack / "OWNER-PIN-SIGN.sh").read_text())
        for text in (readme, header):
            self.assertIn("Antes do ensaio: gere com `--pin-note`, escreva as seções humanas "
                          "do sentinel e commite o pack.", text)
        for text in (readme, sentinel):
            self.assertIn("Texto herdado sem conferência:", text)
            self.assertNotIn("Contradição detectada", text)
        self.assertEqual(summary["inherited_prose_flags"], [])

    def test_offline_run_flags_an_inherited_npm_pack_sentence(self) -> None:
        line = "printf 'ceremony(%s): re-pin codex-cli %s -> %s\\n' \"$PLAN\" \"$OLD_VER\" \"$NEW_VER\" >\"$MSG\"\n"
        self.assertIn(line, CONST_MOLD)
        mold = CONST_MOLD.replace(line, line + "printf 'Digests tirados com npm pack.\\n' >>\"$MSG\"\n")
        for offline in (False, True):
            with self.subTest(offline=offline):
                shutil.rmtree(self.pack_dir("03"), ignore_errors=True)
                self.write_const_pack(mold=mold)
                tgz = self.configure("0.3.0", pack_forbidden=offline)
                extra = ["--offline-from", str(tgz)] if offline else []
                rc, out, err = self.run_tool("0.3.0", "--ga-tag", "v1.9.0", *extra,
                                             mold=CONST_MOLD_REL)
                self.assertEqual(rc, 0, err)
                flags = json.loads(out)["inherited_prose_flags"]
                readme = " ".join((self.pack_dir("03") / "README.md").read_text().split())
                if offline:
                    self.assertEqual(len(flags), 1)
                    self.assertIn("Contradição detectada nesta geração", readme)
                else:
                    self.assertEqual(flags, [])
                    self.assertNotIn("Contradição detectada", readme)

    def test_in_range_run_flags_an_inherited_widen_sentence(self) -> None:
        """C-R3M-02: an in-range patch re-pin (nothing widened) copies a mold
        commit line saying ``Widen-upper-only``; the generator names it."""
        line = "printf 'ceremony(%s): re-pin codex-cli %s -> %s\\n' \"$PLAN\" \"$OLD_VER\" \"$NEW_VER\" >\"$MSG\"\n"
        self.assertIn(line, CONST_MOLD)
        mold = CONST_MOLD.replace(line, line + "  printf 'Widen-upper-only.\\n' >>\"$MSG\"\n")
        for version, tag, widened in (("0.2.5", "02-5", False), ("0.3.0", "03", True)):
            with self.subTest(version=version):
                shutil.rmtree(self.pack_dir(tag), ignore_errors=True)
                self.write_const_pack(mold=mold)
                self.configure(version)
                rc, out, err = self.run_tool(version, "--ga-tag", "v1.9.0", mold=CONST_MOLD_REL)
                self.assertEqual(rc, 0, err)
                summary = json.loads(out)
                self.assertIs(summary["widened"], widened)
                readme = " ".join((self.pack_dir(tag) / "README.md").read_text().split())
                sentinel = " ".join((self.pack_dir(tag) / f"pin-{tag}-approved.md")
                                    .read_text().split())
                if widened:
                    self.assertEqual(summary["inherited_prose_flags"], [])
                    self.assertNotIn("Contradição detectada", readme)
                else:
                    self.assertEqual(len(summary["inherited_prose_flags"]), 1)
                    self.assertIn("Widen-upper-only", summary["inherited_prose_flags"][0])
                    for text in (readme, sentinel):
                        self.assertIn("Contradição detectada nesta geração", text)

    def test_todo_guard_executes_in_the_constants_grammar(self) -> None:
        _summary, pack = self._emit()
        real = RepinEmittedScriptTest._run_guard(self, pack / "OWNER-PIN-SIGN.sh", "0", todo=True)
        self.assertEqual(real.returncode, 1, real.stdout + real.stderr)
        self.assertIn("DIE: TODO(owner) pendente", real.stdout)

    def test_pin_note_replaces_the_todo_and_is_hashed(self) -> None:
        note = self.root / "why.txt"
        note.write_text("Motivo medido do re-pin.\n\nSegundo parágrafo.\n", encoding="utf-8")
        summary, pack = self._emit("--pin-note", str(note))
        pin = (pack / "codex-cli-pin.txt.new").read_text()
        self.assertNotIn("TODO(owner)", pin)
        self.assertIn("# Motivo medido do re-pin.", pin)
        self.assertEqual(summary["todo_owner"], ["pin-03-approved.md"])
        self.assertEqual(self._consts((pack / "OWNER-PIN-SIGN.sh").read_text())["SRC_PIN_SHA256"],
                         hashlib.sha256(pin.encode()).hexdigest())
        self.assertEqual(MOD.parse_pin(pin)[1:], ("0.1.0", "0.4.0"))

    def test_input_refusals_before_any_registry_call(self) -> None:
        self.write_const_pack()
        self.configure("0.3.0")
        todo_note = self.root / "todo.txt"
        todo_note.write_text("TODO(owner): depois\n", encoding="utf-8")
        empty_note = self.root / "empty.txt"
        empty_note.write_text("\n\n", encoding="utf-8")
        cases = {
            "no --ga-tag": ([], "needs --ga-tag"),
            "malformed --ga-tag": (["--ga-tag", "1.9.0"], "needs --ga-tag"),
            "pack dir that is not codex-pin-<tag>": (
                ["--ga-tag", "v1.9.0", "--pack-dir", f".claude/plans/{PLAN}/re-pin"],
                "codex-pin-03"),
            "pin note with a TODO": (["--ga-tag", "v1.9.0", "--pin-note", str(todo_note)],
                                     "still carries"),
            "empty pin note": (["--ga-tag", "v1.9.0", "--pin-note", str(empty_note)], "empty"),
        }
        for label, (argv, needle) in cases.items():
            with self.subTest(case=label):
                plan = None if "--pack-dir" in argv else PLAN
                rc, _out, err = self.run_tool("0.3.0", *argv, mold=CONST_MOLD_REL, plan=plan)
                self.assertEqual(rc, 2, f"{label}: {err}")
                self.assertIn(needle, err)
        self.assertEqual(self.npm_calls(), [])

    def test_ga_tag_is_refused_for_a_heredoc_mold(self) -> None:
        self.configure("0.3.0")
        rc, _out, err = self.run_tool("0.3.0", "--ga-tag", "v1.9.0")
        self.assertEqual(rc, 2, err)
        self.assertIn("applies only", err)
        self.assertEqual(self.npm_calls(), [])

    def test_missing_publication_date_is_a_verification_failure(self) -> None:
        self.write_const_pack()
        self.configure("0.3.0", published=None)
        rc, _out, err = self.run_tool("0.3.0", "--ga-tag", "v1.9.0", mold=CONST_MOLD_REL)
        self.assertEqual(rc, 3, err)
        self.assertIn("publication time", err)
        self.assert_nothing_written("03")

    def test_grammar_refusals(self) -> None:
        self.configure("0.3.0")
        verify_call = next(ln for ln in CONST_MOLD.splitlines() if "--verify-codex-pin" in ln)
        pin_check = next(ln for ln in CONST_MOLD.splitlines() if '"$SRC_PIN_SHA256"' in ln)
        molds = {
            "unknown key": CONST_MOLD.replace("GA_TAG=v9.8.7\n", "GA_TAG=v9.8.7\nEXTRA=1\n"),
            "key assigned twice": CONST_MOLD.replace("LOWER=0.1.0\n", "LOWER=0.1.0\nLOWER=0.1.0\n"),
            "missing key": CONST_MOLD.replace("T2_NODE='.claude/hooks/tests/test_x.py::T::test_y'\n",
                                              ""),
            "D not the template": CONST_MOLD.replace("D=.claude/plans/$PLAN/codex-pin-$PACK_TAG",
                                                     "D=.claude/plans/PLAN-900/codex-pin-029"),
            "value shape": CONST_MOLD.replace("NEW_PUBLISHED=2026-09-01", "NEW_PUBLISHED=ontem"),
            "block never closes": CONST_MOLD.replace(
                "# ------------------------------------------------------------ fim constantes\n", ""),
            "key assigned again in the body": CONST_MOLD.replace(
                'say "1/7 Anchor-SHA"', 'say "1/7 Anchor-SHA"\nNEW_SHA=$(cat x)'),
            "key exported in the body": CONST_MOLD.replace(
                'say "1/7 Anchor-SHA"', 'say "1/7 Anchor-SHA"\n  export GA_TAG=v1.0.0'),
            "unknown PACK_FILES entry": CONST_MOLD.replace(" $D/README.md\"", " $D/extra.txt\""),
            "PACK_FILES without the manifest": CONST_MOLD.replace(" $SRC_MAN $D/", " $D/"),
            "no frozen pin sha256 check": CONST_MOLD.replace(pin_check + "\n", ""),
            "verify_pin without --verify-codex-pin": CONST_MOLD.replace(
                verify_call, '  python3 -c "print(0)" \\'),
            "no verify_pin run": CONST_MOLD.replace('vrc=$(verify_pin "$BAK/verify.out")',
                                                    "vrc=0"),
            "stale version in the body": CONST_MOLD.replace(
                'say "7/7 commit"', 'say "7/7 commit"\necho "fixo em 0.2.9"'),
            "stale digest in a block comment": CONST_MOLD.replace(
                "# sha256 dos canônicos vivos", "# sha256 " + "c" * 64),
            "stale pack path in the body": CONST_MOLD.replace(
                'say "7/7 commit"', 'say "7/7 commit"\nls .claude/plans/x/codex-pin-029'),
            # DRY shapes (_dry_definition) and the '|| die' anchor suffix (_OR_DIE)
            "no DRY definition": CONST_MOLD.replace(_DRY_LINE, ""),
            "DRY assigned again after the line": CONST_MOLD.replace(
                'say "P0 pré-condições"', 'say "P0 pré-condições"\nDRY=1'),
            "DRY=1 arm without --dry-run": CONST_MOLD_HARDENED.replace(
                "1:--dry-run) DRY=1", "1:-n) DRY=1"),
            "DRY=0 arm naming --dry-run": CONST_MOLD_HARDENED.replace(
                "  0:) DRY=0 ;;", "  0:|2:--dry-run) DRY=0 ;;"),
            "a third DRY arm": CONST_MOLD_HARDENED.replace(
                "  0:) DRY=0 ;;", "  0:) DRY=0 ;;\n  2:--dry-run) DRY=1 ;;"),
            "DRY set outside the case arms": CONST_MOLD_HARDENED.replace(
                'say "P0 pré-condições"', 'say "P0 pré-condições"\n[ -n "${X:-}" ] && DRY=1'),
            "DRY arms in a case that is not at column 0": CONST_MOLD_HARDENED.replace(
                'case "$#:${1:-}" in', 'if true; then\n  case "$#:${1:-}" in').replace(
                "esac\n", "  esac\nfi\n", 1),
            "manifest apply swallowing its failure": CONST_MOLD_HARDENED.replace(
                ' || die "não consegui aplicar $DST_MAN"', " || true"),
            "commit-tree swallowing its failure": CONST_MOLD_HARDENED.replace(
                ' || die "commit-tree falhou — nada foi commitado"', " || true"),
            "'|| die' message running a command": CONST_MOLD_HARDENED.replace(
                ' || die "não consegui aplicar $DST_MAN"', ' || die "falhou $(date)"'),
        }
        rehearsals = {
            "rehearsal missing": None,
            "rehearsal with a stale version": CONST_REHEARSAL + 'echo "0.2.9"\n',
            "rehearsal naming another platform": CONST_REHEARSAL.replace("darwin-arm64",
                                                                         "linux-x64"),
            "rehearsal not reading the sign script": CONST_REHEARSAL.replace(
                'SIGN_SRC="$PACK_DIR/OWNER-PIN-SIGN.sh"', 'SIGN_SRC="$1"'),
        }
        cases = [(k, v, CONST_REHEARSAL, CONST_MOLD_REL) for k, v in molds.items()]
        cases += [(k, CONST_MOLD, v, CONST_MOLD_REL) for k, v in rehearsals.items()]
        cases.append(("mold outside codex-pin-<PACK_TAG>", CONST_MOLD, CONST_REHEARSAL,
                      f".claude/plans/{PLAN}/codex-pin-hand/OWNER-PIN-SIGN.sh"))
        for label, mold, rehearsal, rel in cases:
            with self.subTest(case=label):
                pack = (self.repo / rel).parent
                if pack.exists():
                    shutil.rmtree(pack)
                self.write_const_pack(mold=mold, rehearsal=rehearsal, rel=rel)
                rc, _out, err = self.run_tool("0.3.0", "--ga-tag", "v1.9.0", mold=rel)
                self.assertEqual(rc, 2, f"{label}: {err}")
                self.assertIn(MOD.GRAMMAR_CONSTANTS, err, label)
                shutil.rmtree(pack)
        self.assertEqual(self.npm_calls(), [])


class RepinRealCorpusTest(_RePinBase):
    """Positive control: the REAL packs and the LIVE governance files.

    The invariant, whatever the real corpus holds: the tool BUILDS from the
    newest real pack's mold, and refuses every older one. A newest real mold
    the generator refuses is a RED failure, never a pass: that is the day the
    tool stops serving its purpose (C-R1-01/C-R1-02, S357). Every real pack
    directory (mold, manifest .new, rehearsal, README) is copied into the
    fixture repo, so the ranking and the sibling checks see what the real
    repo holds.
    """

    def _copy_real_packs(self) -> List[str]:
        rels = []
        for mold in sorted((REPO / ".claude" / "plans").glob(MOD.MOLD_GLOB)):
            rel = mold.relative_to(REPO).as_posix()
            dst = self.repo / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            for src in sorted(mold.parent.iterdir()):
                if src.is_file() and not src.is_symlink():
                    shutil.copyfile(src, dst.parent / src.name)
            rels.append(rel)
        for src in (".claude/governance/codex-cli-pin-manifest.json",
                    ".claude/governance/codex-cli-pin.txt"):
            shutil.copyfile(REPO / src, self.repo / src)
        return rels

    def test_live_manifest_renders_byte_identical(self) -> None:
        live = REPO / ".claude" / "governance" / "codex-cli-pin-manifest.json"
        data = MOD.load_manifest(live)
        (triple, entry), = data["payloads"].items()
        ctx = {"version": data["package_version"], "integrity": data["npm_integrity"],
               "triple": triple, "sha256": entry["sha256"]}
        self.assertEqual(MOD.render_manifest(data, ctx), live.read_text(encoding="utf-8"))

    def test_every_real_pack_is_rankable(self) -> None:
        rows = MOD.mold_inventory(REPO)
        self.assertEqual([r["rel"] for r in rows if r["target"] is None], [],
                         "a real pack without a readable manifest .new blocks the tool")

    def test_newest_real_mold_is_built_from(self) -> None:
        if not list((REPO / ".claude" / "plans").glob(MOD.MOLD_GLOB)):
            self.skipTest("no codex-pin mold in this checkout")
        self._copy_real_packs()
        top = MOD.newest_molds(self.repo)
        self.assertTrue(top)
        blocked = [r for r in top if not r["compatible"]]
        # RED, by name: the newest real pack is one the generator cannot build
        # from, so every re-pin from here on would be refused.
        self.assertEqual(blocked, [], "re-pin-codex.py refuses the NEWEST real pack mold "
                         "— extend the grammar before landing (C-R1-01): "
                         + "; ".join(f"{r['rel']}: {r['reason']}" for r in blocked))
        live = MOD.load_manifest(REPO / ".claude" / "governance" / "codex-cli-pin-manifest.json")
        newest_pin = max(MOD.parse_version(live["package_version"]), top[0]["target"])
        target = f"{newest_pin[0]}.{newest_pin[1] + 1}.0"
        self.configure(target, payload=b"real-mold control")
        older = [r for r in MOD.mold_inventory(self.repo)
                 if r["compatible"] and r["target"] < top[0]["target"]]
        for row in older:
            with self.subTest(older=row["rel"]):
                extra = ["--ga-tag", "v9.9.9"] if row["grammar"] == MOD.GRAMMAR_CONSTANTS else []
                rc, _out, err = self.run_tool(target, "--dry-run", *extra, mold=row["rel"])
                self.assertEqual(rc, 2, err)
                self.assertIn("newest pack pins", err)
        mold_rel = top[-1]["rel"]
        extra = ["--ga-tag", "v9.9.9"] if top[-1]["grammar"] == MOD.GRAMMAR_CONSTANTS else []
        rc, out, err = self.run_tool(target, *extra, mold=mold_rel)
        self.assertEqual(rc, 0, err)
        summary = json.loads(out)
        pack = self.repo / summary["pack_dir"]
        lint = _load("check_ceremony_script_for_re_pin_real", LINT)
        for name in [n for n in summary["files"] if n.endswith(".sh")]:
            with self.subTest(script=name):
                proc = subprocess.run(["bash", "-n", str(pack / name)], capture_output=True,
                                      text=True, timeout=60, check=False)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                blocking = [f for f in lint.lint_file(str(pack / name),
                                                      summary["pack_dir"] + "/" + name, "100644")
                            if f["sev"] == "BLOCKING"]
                self.assertEqual(blocking, [])
        pin = (pack / "codex-cli-pin.txt.new").read_text()
        live_pin = (REPO / ".claude" / "governance" / "codex-cli-pin.txt").read_text()
        self.assertTrue(pin.startswith(live_pin.rstrip("\n").rsplit("\n", 1)[0]))
        self.assertEqual(pin.splitlines()[-1], summary["new_range"])


class RepinPureFunctionTest(_RePinBase):

    def test_plan_range_and_tag(self) -> None:
        self.assertEqual(MOD.plan_range("0.128.0", "0.156.0", (0, 156, 0)),
                         (">=0.128.0,<0.157.0", True))
        self.assertEqual(MOD.plan_range("0.128.0", "0.156.0", (0, 155, 1)),
                         (">=0.128.0,<0.156.0", False))
        self.assertEqual(MOD.plan_range("0.128.0", "0.156.0", (0, 158, 3)),
                         (">=0.128.0,<0.159.0", True))
        self.assertEqual(MOD.pack_tag((0, 156, 0)), "0156")
        self.assertEqual(MOD.pack_tag((0, 156, 2)), "0156-2")

    def test_payload_member_mapping(self) -> None:
        self.assertEqual(MOD.payload_member(MANIFEST_PATH, ALIAS), MEMBER)
        for bad in ("@openai/codex-linux-x64/vendor/x/bin/codex",
                    f"{ALIAS}/vendor/../bin/codex", f"{ALIAS}/"):
            with self.subTest(path=bad):
                with self.assertRaises(MOD.RePinError) as ctx:
                    MOD.payload_member(bad, ALIAS)
                self.assertEqual(ctx.exception.rc, 2)

    def test_member_key_models_the_extractor(self) -> None:
        # npm 11 (pacote strip: 1 over node-tar): the RAW first segment goes.
        cases = {
            "package/vendor/X/bin/codex": "vendor/x/bin/codex",
            "other/vendor/x/bin/codex": "vendor/x/bin/codex",
            "package//vendor/x/bin/codex": "vendor/x/bin/codex",
            "package/vendor/x/bin/./codex": "vendor/x/bin/codex",
            "./package/vendor/x/bin/codex": "package/vendor/x/bin/codex",
        }
        for raw, key in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(MOD._member_key(raw), key)
        for raw in ("package", "codex", "package/", "package/."):
            with self.subTest(raw=raw):
                self.assertIsNone(MOD._member_key(raw))

    def test_platform_for_maps_the_pinned_triple(self) -> None:
        for triple, platform in (("aarch64-apple-darwin", "darwin-arm64"),
                                 ("x86_64-unknown-linux-musl", "linux-x64")):
            with self.subTest(triple=triple):
                manifest = {"payloads": {triple: {}}}
                self.assertEqual(MOD._platform_for(manifest, None), (platform, triple))
        with self.assertRaises(MOD.RePinError):
            MOD._platform_for({"payloads": {"riscv64-unknown-none": {}}}, None)


class RepinSelectorTest(TestEnvContext):
    """PLAN-193 W5 selects with ``-k "repin or ..."``: every test class here
    must carry the keyword, or the gate silently stops seeing it."""

    def test_every_test_class_carries_the_selector_keyword(self) -> None:
        classes = [obj for _name, obj in sorted(globals().items())
                   if isinstance(obj, type) and issubclass(obj, unittest.TestCase)
                   and obj.__module__ == __name__
                   and any(n.startswith("test") for n in vars(obj))]
        self.assertTrue(classes)
        self.assertEqual([c.__name__ for c in classes if "repin" not in c.__name__.lower()], [])


if __name__ == "__main__":
    unittest.main()
