"""macOS AppleDouble members ``._<name>`` in ceo-backup archives (PLAN-198).

ceo-backup.sh must not write them; ceo-restore.sh skips (never writes) one
only when it is a regular file whose companion is an accepted member, and
refuses every other ``._`` member, in the preview and in the apply alike.

The Python extraction that replaced ``tar -x`` must also hold what it
promises: a truncated or corrupt archive is refused, every sparse member is
refused before anything is written, two members with one name are refused,
and the key files are refused in any letter case.  Archives are built with
Python tarfile, so all but the real backup round trip and the letter-case
probe run on Linux too.
"""
from __future__ import annotations

import gzip
import io
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / ".claude" / "scripts"
RESTORE = SCRIPTS / "ceo-restore.sh"
BACKUP = SCRIPTS / "ceo-backup.sh"
VALIDATOR = SCRIPTS / "_restore_archive.py"
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(SCRIPTS))
from _lib.testing import TestEnvContext  # noqa: E402
from _subprocess_helpers import run_in_process_group  # noqa: E402
import _restore_archive  # noqa: E402

_METADATA = b"\x00\x05\x16\x07\x00\x02\x00\x00Mac OS X        "

# (name, tar type, content, linkname)
Entry = Tuple[str, bytes, bytes, str]


def _file(name: str, content: bytes = _METADATA) -> Entry:
    return (name, tarfile.REGTYPE, content, "")


def _dir(name: str) -> Entry:
    return (name, tarfile.DIRTYPE, b"", "")


def _info(entry: Entry) -> tarfile.TarInfo:
    name, kind, content, linkname = entry
    info = tarfile.TarInfo(name)
    info.type = kind
    info.linkname = linkname
    info.size = len(content) if kind == tarfile.REGTYPE else 0
    info.mode = 0o755 if kind == tarfile.DIRTYPE else 0o644
    return info


def _archive(path: Path, entries: Sequence[Entry]) -> None:
    with tarfile.open(str(path), "w:gz") as archive:
        for entry in entries:
            info = _info(entry)
            payload = io.BytesIO(entry[2]) if entry[1] == tarfile.REGTYPE else None
            archive.addfile(info, payload)


def _tar_bytes(entries: Sequence[Entry]) -> bytes:
    """The uncompressed tar stream, so a test can cut or damage it."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for entry in entries:
            info = _info(entry)
            payload = io.BytesIO(entry[2]) if entry[1] == tarfile.REGTYPE else None
            archive.addfile(info, payload)
    return buffer.getvalue()


def _macos_layout() -> List[Entry]:
    """The member sequence macOS tar writes for a ceo-backup stage."""
    return [
        _file("._."),
        _dir("."),
        _file("./._audit"),
        _dir("./audit"),
        _file("./audit/._audit-log.jsonl"),
        _file("./audit/audit-log.jsonl", b'{"event":"ok"}\n'),
        _file("./._memory"),
        _dir("./memory"),
        _file("./memory/._MEMORY.md"),
        _file("./memory/MEMORY.md", b"# memory\n"),
        _file("./._MANIFEST.txt"),
        _file("./MANIFEST.txt", b"./audit/audit-log.jsonl\n./memory/MEMORY.md\n"),
    ]


def _plain_layout() -> List[Entry]:
    """The same backup without metadata members (what GNU tar writes)."""
    return [entry for entry in _macos_layout()
            if not entry[0].rsplit("/", 1)[-1].startswith("._")]


def _env() -> dict:
    env = dict(os.environ)
    env.pop("CEO_AUDIT_LOG_DIR", None)
    env.pop("COPYFILE_DISABLE", None)
    return env


def _run(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess:
    return run_in_process_group(
        list(args), cwd=cwd, env=_env(), text=True,
        capture_output=True, check=False, timeout=30,
    )


def _restore(bundle: Path, destination: Path, cwd: Path,
             apply: bool) -> subprocess.CompletedProcess:
    args = ["bash", str(RESTORE), str(bundle), "--dest", str(destination)]
    if apply:
        args += ["--apply", "--force"]
    return _run(args, cwd)


def _appledouble_paths(root: Path) -> List[str]:
    return [os.path.join(top, name) for top, dirs, files in os.walk(str(root))
            for name in dirs + files if name.startswith("._")]


def _tree(root: Path) -> List[str]:
    return sorted(os.path.relpath(os.path.join(top, name), str(root))
                  for top, _dirs, files in os.walk(str(root)) for name in files)


class AppleDoubleRestoreTest(TestEnvContext):
    """Positive control: companion ``._`` members are skipped, never written."""

    def test_preview_and_apply_skip_companion_metadata(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            destination = root / "destination"
            _archive(bundle, _macos_layout())
            preview = _restore(bundle, destination, root, apply=False)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse(destination.exists(), "preview must not write")
            apply = _restore(bundle, destination, root, apply=True)
            self.assertEqual(apply.returncode, 0, apply.stderr)
            self.assertEqual((destination / "audit-log.jsonl").read_bytes(),
                             b'{"event":"ok"}\n')
            self.assertEqual((destination / "memory" / "MEMORY.md").read_bytes(),
                             b"# memory\n")
            self.assertEqual(_appledouble_paths(destination), [])

    def test_optional_plans_and_metrics_skip_companion_metadata(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".claude").mkdir()
            bundle = root / "state.tar.gz"
            _archive(bundle, _macos_layout() + [
                _file("./._agent-metrics.md"),
                _file("./agent-metrics.md", b"metrics\n"),
                _file("./._plans"),
                _dir("./plans"),
                _file("./plans/._one.md"),
                _file("./plans/one.md", b"plan\n"),
            ])
            result = _run(["bash", str(RESTORE), str(bundle), "--apply", "--force",
                           "--restore-plans", "--restore-agent-metrics",
                           "--dest", str(root / "destination")], root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / ".claude" / "plans" / "one.md").read_bytes(), b"plan\n")
            self.assertEqual((root / ".claude" / "agent-metrics.md").read_bytes(), b"metrics\n")
            self.assertEqual(_appledouble_paths(root / ".claude"), [])
            self.assertEqual(_appledouble_paths(root / "destination"), [])

    def test_stage_extraction_writes_only_accepted_members(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            stage = root / "stage"
            stage.mkdir()
            _archive(bundle, _macos_layout())
            result = _run([sys.executable, str(VALIDATOR), str(bundle), str(stage)], root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(_tree(stage), ["MANIFEST.txt", "audit/audit-log.jsonl",
                                            "memory/MEMORY.md"])

    def test_validate_returns_data_members_only(self) -> None:
        members = [_info(entry) for entry in _macos_layout()]
        accepted = _restore_archive.validate(members)
        self.assertEqual([m.name for m in accepted],
                         [".", "./audit", "./audit/audit-log.jsonl", "./memory",
                          "./memory/MEMORY.md", "./MANIFEST.txt"])


class AppleDoubleRefusalTest(TestEnvContext):
    """Negative controls: every other ``._`` member stays refused."""

    def _assert_refused_both_modes(self, entries: Sequence[Entry], needle: str) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            destination = root / "destination"
            _archive(bundle, entries)
            for apply in (False, True):
                result = _restore(bundle, destination, root, apply=apply)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(needle, result.stderr)
                self.assertFalse(destination.exists())

    def test_orphan_metadata_member_is_refused(self) -> None:
        self._assert_refused_both_modes(_macos_layout() + [_file("./._x")],
                                        "refused path: ./._x")

    def test_orphan_metadata_member_inside_layout_is_refused(self) -> None:
        self._assert_refused_both_modes(_macos_layout() + [_file("./memory/._x.md")],
                                        "refused path: ./memory/._x.md")

    def test_metadata_symlink_is_refused(self) -> None:
        entries = _macos_layout()
        entries[8] = ("./memory/._MEMORY.md", tarfile.SYMTYPE, b"", "MEMORY.md")
        self._assert_refused_both_modes(entries, "refused member type: ./memory/._MEMORY.md")

    def test_metadata_member_under_parent_reference_is_refused(self) -> None:
        self._assert_refused_both_modes(_macos_layout() + [_file("./memory/../._memory")],
                                        "refused path: ./memory/../._memory")

    def test_metadata_directory_is_refused(self) -> None:
        entries = _macos_layout()
        entries[6] = _dir("./._memory")
        self._assert_refused_both_modes(entries, "refused member type: ./._memory")

    def test_bare_prefix_at_the_root_is_refused(self) -> None:
        # The root directory is in the archive, so "._" with an empty
        # companion would otherwise pass as the root's own metadata.
        self._assert_refused_both_modes(_macos_layout() + [_file("./._")],
                                        "refused AppleDouble name: ./._")

    def _refused(self, entries: Sequence[Entry]) -> Optional[str]:
        try:
            _restore_archive.validate([_info(entry) for entry in entries])
        except ValueError as exc:
            return str(exc)
        return None

    def test_other_metadata_shapes_are_refused(self) -> None:
        base = _macos_layout()

        def metadata_as(kind: bytes, linkname: str = "") -> List[Entry]:
            # Replaces the layout's own ./memory/._MEMORY.md (index 8).
            return base[:8] + [("./memory/._MEMORY.md", kind, b"", linkname)] + base[9:]

        cases = {
            "hard link": (metadata_as(tarfile.LNKTYPE, "./memory/MEMORY.md"),
                          "refused member type: ./memory/._MEMORY.md"),
            "fifo": (metadata_as(tarfile.FIFOTYPE),
                     "refused member type: ./memory/._MEMORY.md"),
            "character device": (metadata_as(tarfile.CHRTYPE),
                                 "refused member type: ./memory/._MEMORY.md"),
            "absolute": (base + [_file("/._x")], "refused path: /._x"),
            "parent prefix": (base + [_file("../._memory")], "refused path: ../._memory"),
            "bare prefix": (base + [_file("./memory/._")],
                            "refused AppleDouble name: ./memory/._"),
            "bare prefix at the root": (base + [_file("./._")],
                                        "refused AppleDouble name: ./._"),
            "bare prefix at the root, no ./": (base + [_file("._")],
                                               "refused AppleDouble name: ._"),
            "parent companion": (base + [_file("./memory/._..")],
                                 "refused AppleDouble name: ./memory/._.."),
            # Regression guard for the audit-key rule: the key itself is
            # refused before its metadata member is looked at.
            "audit-key with its metadata": (base + [_file("./audit/._audit-key"),
                                                    _file("./audit/audit-key", b"k")],
                                            "refused path: ./audit/audit-key"),
            "companion is metadata": (base + [_file("./memory/._._MEMORY.md")],
                                      "refused path: ./memory/._._MEMORY.md"),
            "root companion missing": ([_file("._."), _dir("./audit"),
                                        _file("./audit/audit-log.jsonl", b"{}\n")],
                                       "refused path: ._."),
        }
        for label, (entries, expected) in cases.items():
            with self.subTest(label):
                self.assertEqual(self._refused(entries), expected)


_TRUNCATED = "refused truncated or corrupt archive"


def _two_members() -> bytes:
    # ./memory/one: header 0-511, data 512-1023; ./memory/two: header
    # 1024-1535, data 1536-2559 (1000 bytes padded); end blocks from 2560.
    return _tar_bytes([_file("./memory/one", b"1" * 100),
                       _file("./memory/two", b"2" * 1000)])


def _write_gz(path: Path, raw: bytes) -> None:
    path.write_bytes(gzip.compress(raw, mtime=0))


def _extract_to_stage(bundle: Path, stage: Path, cwd: Path) -> subprocess.CompletedProcess:
    return _run([sys.executable, str(VALIDATOR), str(bundle), str(stage)], cwd)


class TruncatedArchiveTest(TestEnvContext):
    """Members after a cut must not vanish silently: the archive is refused."""

    def _assert_refused(self, write, detail: str) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            stage = root / "stage"
            stage.mkdir()
            write(bundle)
            result = _extract_to_stage(bundle, stage, root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("{0}: {1}".format(_TRUNCATED, detail), result.stderr)
            self.assertEqual(_tree(stage), [])

    def test_header_cut_after_the_first_member_is_refused(self) -> None:
        full = _two_members()
        self._assert_refused(lambda p: _write_gz(p, full[:1024 + 200]),
                             "no end-of-archive block at byte 1024")

    def test_archive_ending_without_end_block_is_refused(self) -> None:
        full = _two_members()
        self._assert_refused(lambda p: _write_gz(p, full[:2560]),
                             "no end-of-archive block at byte 2560")

    def test_invalid_header_after_the_last_member_is_refused(self) -> None:
        full = _two_members()
        self._assert_refused(
            lambda p: _write_gz(p, full[:2560] + b"X" * 512 + b"\0" * 1024),
            "no end-of-archive block at byte 2560")

    def test_compressed_stream_cut_after_the_end_block_is_refused(self) -> None:
        packed = gzip.compress(_two_members(), mtime=0)
        self._assert_refused(lambda p: p.write_bytes(packed[:-10]), "")

    def test_bad_stream_checksum_is_refused(self) -> None:
        packed = gzip.compress(_two_members(), mtime=0)
        damaged = packed[:-8] + bytes(b ^ 0xFF for b in packed[-8:-4]) + packed[-4:]
        self._assert_refused(lambda p: p.write_bytes(damaged), "")

    def test_member_cut_inside_its_data_is_refused(self) -> None:
        # Regression guard: tarfile already raised here; the refusal is named.
        full = _two_members()
        self._assert_refused(lambda p: _write_gz(p, full[:1536 + 300]),
                             "unexpected end of data")

    def test_restore_refuses_a_truncated_archive_under_quiet(self) -> None:
        full = _two_members()
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            destination = root / "destination"
            _write_gz(bundle, full[:1024 + 200])
            for extra in ([], ["--apply", "--force"]):
                result = _run(["bash", str(RESTORE), str(bundle), "--quiet",
                               "--dest", str(destination)] + extra, root)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(_TRUNCATED, result.stderr)
                self.assertFalse(destination.exists())


_SPARSE_SIZE = 8192
_SPARSE_SEGMENTS = ((0, b"head"), (_SPARSE_SIZE - 4, b"tail"))
_SPARSE_NAME = "./memory/sparse.bin"


def _padded(data: bytes) -> bytes:
    return data + b"\0" * (-len(data) % tarfile.BLOCKSIZE)


def _member_bytes(entry: Entry) -> bytes:
    content = entry[2] if entry[1] == tarfile.REGTYPE else b""
    return _info(entry).tobuf(format=tarfile.PAX_FORMAT) + _padded(content)


def _sparse_numbers(segments: Sequence[Tuple[int, bytes]]) -> List[str]:
    return [str(n) for offset, data in segments for n in (offset, len(data))]


def _sparse_pax(name: str, version: str) -> bytes:
    """One sparse member in a GNU PAX sparse format: "0.0", "0.1" or "1.0"."""
    segments = _SPARSE_SEGMENTS
    if version == "1.0":
        numbers = [str(len(segments))] + _sparse_numbers(segments)
        payload = _padded(("\n".join(numbers) + "\n").encode("ascii"))
        headers = {"GNU.sparse.major": "1", "GNU.sparse.minor": "0",
                   "GNU.sparse.name": name, "GNU.sparse.realsize": str(_SPARSE_SIZE)}
    elif version == "0.1":
        payload = b""
        headers = {"GNU.sparse.size": str(_SPARSE_SIZE),
                   "GNU.sparse.numblocks": str(len(segments)),
                   "GNU.sparse.map": ",".join(_sparse_numbers(segments))}
    else:
        # 0.0 repeats one offset/numbytes record pair per segment; a single
        # segment keeps the header a plain mapping.
        segments = segments[:1]
        payload = b""
        headers = {"GNU.sparse.size": str(_SPARSE_SIZE), "GNU.sparse.numblocks": "1",
                   "GNU.sparse.offset": str(segments[0][0]),
                   "GNU.sparse.numbytes": str(len(segments[0][1]))}
    payload += b"".join(data for _offset, data in segments)
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = 0o644
    info.pax_headers = headers
    return info.tobuf(format=tarfile.PAX_FORMAT) + _padded(payload)


def _sparse_old_gnu(name: str) -> bytes:
    """One old GNU sparse member (type 'S'); its two unused map slots stay zero."""
    payload = b"".join(data for _offset, data in _SPARSE_SEGMENTS)
    info = tarfile.TarInfo(name)
    info.type = tarfile.GNUTYPE_SPARSE
    info.size = len(payload)
    info.mode = 0o644
    header = bytearray(info.tobuf(format=tarfile.GNU_FORMAT))
    position = 386
    for offset, data in _SPARSE_SEGMENTS:
        header[position:position + 24] = (tarfile.itn(offset, 12, tarfile.GNU_FORMAT)
                                          + tarfile.itn(len(data), 12, tarfile.GNU_FORMAT))
        position += 24
    header[483:495] = tarfile.itn(_SPARSE_SIZE, 12, tarfile.GNU_FORMAT)
    header[148:156] = b" " * 8
    header[148:155] = ("%06o\0" % sum(header)).encode("ascii")
    return bytes(header) + _padded(payload)


def _write_members(path: Path, members: Sequence[bytes]) -> None:
    _write_gz(path, b"".join(members) + b"\0" * (2 * tarfile.BLOCKSIZE))


class SparseMemberRefusalTest(TestEnvContext):
    """Every sparse member is refused before anything is written."""

    def _assert_refused_everywhere(self, members: Sequence[bytes], name: str) -> None:
        expected = "refused sparse member: {0}".format(name)
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            _write_members(bundle, members)
            with tarfile.open(str(bundle), "r:gz") as archive:
                listed = archive.getmembers()
            self.assertEqual([m.name for m in listed if m.issparse()], [name])
            with self.assertRaises(ValueError) as caught:
                _restore_archive.validate(listed)
            self.assertEqual(str(caught.exception), expected)
            stage = root / "stage"
            stage.mkdir()
            result = _extract_to_stage(bundle, stage, root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(expected, result.stderr)
            self.assertEqual(os.listdir(str(stage)), [])
            destination = root / "destination"
            for apply in (False, True):
                result = _restore(bundle, destination, root, apply=apply)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(expected, result.stderr)
                self.assertFalse(destination.exists())
                # The first validator call refuses: the SHA-256 check and the
                # stage that follow it never run.
                self.assertNotRegex(result.stderr, r"(?m)^(sha256: |warning: no \.sha256)")

    def _after_layout(self, member: bytes) -> List[bytes]:
        return [_member_bytes(entry) for entry in _plain_layout()] + [member]

    def test_gnu_sparse_1_0_member_is_refused(self) -> None:
        self._assert_refused_everywhere(
            self._after_layout(_sparse_pax(_SPARSE_NAME, "1.0")), _SPARSE_NAME)

    def test_old_gnu_sparse_member_is_refused(self) -> None:
        self._assert_refused_everywhere(
            self._after_layout(_sparse_old_gnu(_SPARSE_NAME)), _SPARSE_NAME)

    def test_pax_sparse_0_0_member_is_refused(self) -> None:
        self._assert_refused_everywhere(
            self._after_layout(_sparse_pax(_SPARSE_NAME, "0.0")), _SPARSE_NAME)

    def test_pax_sparse_0_1_member_is_refused(self) -> None:
        self._assert_refused_everywhere(
            self._after_layout(_sparse_pax(_SPARSE_NAME, "0.1")), _SPARSE_NAME)

    def test_sparse_metadata_member_is_refused(self) -> None:
        # Replaces the layout's own ./memory/._MEMORY.md (index 8), whose
        # companion follows it, so only the sparse rule can refuse it.
        name = "./memory/._MEMORY.md"
        layout = [_member_bytes(entry) for entry in _macos_layout()]
        self._assert_refused_everywhere(
            layout[:8] + [_sparse_pax(name, "1.0")] + layout[9:], name)


def _case_insensitive(directory: Path) -> bool:
    probe = directory / "case-probe"
    probe.write_bytes(b"")
    folded = (directory / "CASE-PROBE").exists()
    probe.unlink()
    return folded


class DuplicateMemberTest(TestEnvContext):
    """Two members that land on one path are refused, never merged."""

    def _refused(self, entries: Sequence[Entry]) -> Optional[str]:
        try:
            _restore_archive.validate([_info(entry) for entry in entries])
        except ValueError as exc:
            return str(exc)
        return None

    def test_duplicate_names_are_refused(self) -> None:
        base = _plain_layout()
        cases = {
            "file twice": (base + [_file("./memory/MEMORY.md", b"later\n")],
                           "refused duplicate path: ./memory/MEMORY.md"),
            "same name, other spelling": (base + [_file("memory/MEMORY.md", b"later\n")],
                                          "refused duplicate path: memory/MEMORY.md"),
            "file then directory": (base + [_dir("./memory/MEMORY.md")],
                                    "refused duplicate path: ./memory/MEMORY.md"),
            "directory then file": (base + [_file("./memory", b"x")],
                                    "refused duplicate path: ./memory"),
            "metadata twice": (_macos_layout() + [_file("./memory/._MEMORY.md")],
                               "refused duplicate path: ./memory/._MEMORY.md"),
        }
        for label, (entries, expected) in cases.items():
            with self.subTest(label):
                self.assertEqual(self._refused(entries), expected)

    def test_later_duplicate_with_another_mode_is_refused_in_both_modes(self) -> None:
        later = _info(_file("./memory/MEMORY.md", b"later\n"))
        later.mode = 0o600
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            destination = root / "destination"
            with tarfile.open(str(bundle), "w:gz") as archive:
                for entry in _plain_layout():
                    payload = io.BytesIO(entry[2]) if entry[1] == tarfile.REGTYPE else None
                    archive.addfile(_info(entry), payload)
                archive.addfile(later, io.BytesIO(b"later\n"))
            for apply in (False, True):
                result = _restore(bundle, destination, root, apply=apply)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("refused duplicate path: ./memory/MEMORY.md", result.stderr)
                self.assertFalse(destination.exists())

    def test_name_already_in_the_stage_is_refused(self) -> None:
        # The stage is always fresh, so a name that already exists there can
        # only be an earlier member's name in another letter case (on the
        # default macOS disk, APFS).
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            stage = root / "stage"
            (stage / "memory").mkdir(parents=True)
            (stage / "memory" / "MEMORY.md").write_bytes(b"earlier\n")
            _archive(bundle, _plain_layout())
            with tarfile.open(str(bundle), "r:gz") as archive:
                members = _restore_archive.validate(archive.getmembers())
                with self.assertRaises(ValueError) as caught:
                    _restore_archive.extract(archive, members, str(stage))
            self.assertEqual(str(caught.exception),
                             "refused duplicate path: ./memory/MEMORY.md")
            self.assertEqual((stage / "memory" / "MEMORY.md").read_bytes(), b"earlier\n")

    def test_names_differing_only_in_case_are_refused_where_case_is_ignored(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            if not _case_insensitive(root):
                self.skipTest("case-sensitive file system")
            bundle = root / "state.tar.gz"
            stage = root / "stage"
            stage.mkdir()
            _archive(bundle, _plain_layout() + [_file("./memory/memory.md", b"later\n")])
            result = _extract_to_stage(bundle, stage, root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("refused duplicate path: ./memory/memory.md", result.stderr)


class KeyFileCaseTest(TestEnvContext):
    """audit-key and .salt are refused in any letter case."""

    def test_key_file_names_are_refused_in_any_case(self) -> None:
        for name in ("./audit/AUDIT-KEY", "./audit/Audit-Key", "./audit/.SALT",
                     "./audit/audit-Key", "./audit/.ſalt"):
            with self.subTest(name):
                with self.assertRaises(ValueError) as caught:
                    _restore_archive.validate(
                        [_info(entry) for entry in _plain_layout() + [_file(name, b"x")]])
                self.assertEqual(str(caught.exception), "refused path: {0}".format(name))

    def test_apply_leaves_an_existing_audit_key_untouched(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            destination = root / "destination"
            destination.mkdir()
            key = destination / "audit-key"
            key.write_bytes(b"live key\n")
            key.chmod(0o600)
            _archive(bundle, _plain_layout() + [_file("./audit/AUDIT-KEY", b"other\n")])
            for apply in (False, True):
                result = _restore(bundle, destination, root, apply=apply)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("refused path: ./audit/AUDIT-KEY", result.stderr)
            self.assertEqual(key.read_bytes(), b"live key\n")
            self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)
            self.assertEqual(sorted(os.listdir(str(destination))), ["audit-key"])


@unittest.skipUnless(sys.platform == "darwin", "macOS tar and xattr(1) only")
class MacBackupRoundTripTest(TestEnvContext):
    """A real ceo-backup.sh -> ceo-restore.sh --apply on files with an xattr."""

    def test_backup_writes_no_metadata_members_and_restores(self) -> None:
        xattr = shutil.which("xattr")
        if xattr is None:
            self.skipTest("xattr(1) not found")
        with TemporaryDirectory() as raw:
            root = Path(raw)
            audit = root / "audit"
            (audit / "memory").mkdir(parents=True)
            (audit / "audit-log.jsonl").write_text("{}\n", encoding="utf-8")
            (audit / "memory" / "MEMORY.md").write_text("# m\n", encoding="utf-8")
            for target in (audit / "audit-log.jsonl", audit / "memory" / "MEMORY.md",
                           audit / "memory"):
                marked = _run([xattr, "-w", "org.example.ceo-test", "1", str(target)], root)
                self.assertEqual(marked.returncode, 0, marked.stderr)
            backup_root = root / "backups"
            backup = _run(["bash", str(BACKUP), "--audit-dir", str(audit),
                           "--backup-root", str(backup_root), "--project-slug", "sample"],
                          root)
            self.assertEqual(backup.returncode, 0, backup.stderr)
            tarball = next((backup_root / "sample").glob("*.tar.gz"))
            with tarfile.open(str(tarball), "r:gz") as archive:
                names = archive.getnames()
            self.assertIn("./memory/MEMORY.md", names)
            self.assertEqual([n for n in names if n.rsplit("/", 1)[-1].startswith("._")], [])
            destination = root / "restored"
            restore = _restore(tarball, destination, root, apply=True)
            self.assertEqual(restore.returncode, 0, restore.stderr)
            self.assertEqual((destination / "audit-log.jsonl").read_text(encoding="utf-8"), "{}\n")
            self.assertEqual((destination / "memory" / "MEMORY.md").read_text(encoding="utf-8"),
                             "# m\n")
            self.assertEqual(_appledouble_paths(destination), [])


if __name__ == "__main__":
    unittest.main()
