"""PLAN-163 T3.1 (thread B2) — session-roots write-guard tests.

The DirectoryAdded consumer half: `check_canonical_edit.py` gains a
`_session_roots_guard` extension that DENIES writes whose realpath
resolves inside a session-registered workspace root
(`.claude/state/session-roots.json`, written by the B1 observer
`check_directory_added.py`) unless the root is allowlisted via
`CEO_SESSION_ROOTS_ALLOW` (os.pathsep-separated, realpath-compared).

## Module resolution (staged-aware, landing-safe)

The module under test is resolved feature-first:

1. the SIBLING hook (`parents[1]/check_canonical_edit.py`) when it carries
   `_session_roots_guard` — this is the post-landing live tree, and also
   the pre-landing staged tree when this test runs in place inside
   `.claude/plans/PLAN-163/staged/main-pack/`;
2. else the PLAN-163 staged copy under the repo root;
3. else every test SKIPS (pack absent — nothing to verify).

## Red-first proof

Running the whole PreToolUse flow of the LIVE hook in a way that stays
green after the pack lands is impossible for the red direction (the very
point of the pack is to flip that behavior), so per the B2 fallback
contract the red path is proven two ways:

- `TestRedPathLiveHook` runs the LIVE hook as a subprocess with a
  registered root + a write under it and asserts it ALLOWS — it
  auto-skips once the live hook carries `_session_roots_guard` (pack
  landed), exactly like the PLAN-064 marker-test auto-detection pattern.
- The staged-module deny case (`test_deny_write_under_registered_root`)
  plus its allowlist mirror (`test_allowlist_releases_root`) pin the
  red→green flip in-process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from importlib import util as _importlib_util
from pathlib import Path
from typing import Optional


def _find_repo_root() -> Optional[Path]:
    """Walk up from this file until a tree carrying the live hooks _lib.

    Works from BOTH locations this file lives in during the PLAN-163
    lifecycle: the staged pack (pre-landing) and `.claude/hooks/tests/`
    (post-landing).
    """
    for anc in Path(__file__).resolve().parents:
        if (anc / ".claude" / "hooks" / "_lib" / "testing.py").is_file():
            return anc
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    if env_dir:
        cand = Path(env_dir)
        if (cand / ".claude" / "hooks" / "_lib" / "testing.py").is_file():
            return cand
    return None


_REPO_ROOT = _find_repo_root()
_LIVE_HOOKS_DIR = (_REPO_ROOT / ".claude" / "hooks") if _REPO_ROOT else None
if _LIVE_HOOKS_DIR is not None and str(_LIVE_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_SIBLING_HOOK = Path(__file__).resolve().parents[1] / "check_canonical_edit.py"
_STAGED_HOOK = (
    _REPO_ROOT
    / ".claude" / "plans" / "PLAN-163" / "staged" / "main-pack"
    / ".claude" / "hooks" / "check_canonical_edit.py"
) if _REPO_ROOT is not None else None
_LIVE_HOOK = (
    (_LIVE_HOOKS_DIR / "check_canonical_edit.py")
    if _LIVE_HOOKS_DIR is not None
    else None
)


def _load_module(path: Path, name: str):
    """Import a hook file under a private module name.

    The hook inserts its own directory at ``sys.path[0]`` on import; the
    snapshot/restore below removes anything the import added so later
    tests in the same process never see a staged hooks dir on sys.path.
    ``_lib`` resolution stays deterministic either way: the live hooks
    ``_lib`` is a regular package (has ``__init__.py``) and is already
    cached in ``sys.modules`` by the TestEnvContext import above.
    """
    pre_path = list(sys.path)
    try:
        spec = _importlib_util.spec_from_file_location(name, str(path))
        if spec is None or spec.loader is None:
            return None
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None
    finally:
        for entry in [p for p in sys.path if p not in pre_path]:
            sys.path.remove(entry)


def _resolve_module():
    for path, name in (
        (_SIBLING_HOOK, "_srwg_hook_sibling"),
        (_STAGED_HOOK, "_srwg_hook_staged"),
    ):
        if path is None or not path.is_file():
            continue
        mod = _load_module(path, name)
        if mod is not None and hasattr(mod, "_session_roots_guard"):
            return mod, path
    return None, None


_MOD, _MOD_PATH = _resolve_module()
_SKIP_REASON = (
    "session-roots write-guard absent from both the sibling hook and the "
    "PLAN-163 staged main-pack copy — pack not present, nothing to verify"
)


def _live_hook_lacks_guard() -> bool:
    try:
        return bool(
            _LIVE_HOOK is not None
            and _LIVE_HOOK.is_file()
            and "_session_roots_guard"
            not in _LIVE_HOOK.read_text(encoding="utf-8")
        )
    except OSError:
        return False


_SID = "sess-plan163-b2"


class _SessionRootsBase(TestEnvContext):
    """Shared fixture: an external root dir + registry writer helpers."""

    def setUp(self) -> None:
        super().setUp()
        # External to self.project_dir by construction (sibling subtree of
        # the isolated tmp root).
        self.root = self.home_dir / "added-root"
        self.root.mkdir(parents=True, exist_ok=True)
        self.sid = _SID

    def _entry(self, directory: str, **overrides) -> dict:
        entry = {
            "directory": directory,
            "source": "slash_command",
            "ts": "2026-07-28T00:00:00Z",
        }
        entry.update(overrides)
        return entry

    def _write_registry(self, sessions: dict) -> Path:
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schema": 1, "sessions": sessions}),
            encoding="utf-8",
        )
        return path

    def _guard(self, paths, sid=None, env=None):
        return _MOD._session_roots_guard(
            list(paths),
            Path(self.project_dir),
            self.sid if sid is None else sid,
            env={} if env is None else env,
        )


@unittest.skipIf(_MOD is None, _SKIP_REASON)
class TestSessionRootsGuardFunction(_SessionRootsBase):
    """Pure-function contract of `_session_roots_guard`."""

    def test_deny_write_under_registered_root(self) -> None:
        """Registry-with-root + empty allowlist → deny (the B2 red case)."""
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        reason = self._guard([str(self.root / "notes.txt")])
        self.assertIsNotNone(reason)
        self.assertIn("session_root_write_denied", reason)
        self.assertIn("CEO_SESSION_ROOTS_ALLOW", reason)

    def test_allowlist_releases_root(self) -> None:
        """Mirror of the red case: allowlisted root → allow."""
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        reason = self._guard(
            [str(self.root / "notes.txt")],
            env={"CEO_SESSION_ROOTS_ALLOW": str(self.root)},
        )
        self.assertIsNone(reason)

    def test_allowlist_is_pathsep_separated(self) -> None:
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        other = self.home_dir / "some-other-dir"
        other.mkdir(parents=True, exist_ok=True)
        allow = os.pathsep.join([str(other), str(self.root)])
        reason = self._guard(
            [str(self.root / "notes.txt")],
            env={"CEO_SESSION_ROOTS_ALLOW": allow},
        )
        self.assertIsNone(reason)

    def test_allowlist_compares_realpaths(self) -> None:
        """Allowlisting a SYMLINK to the root still releases the root."""
        link = self.home_dir / "root-alias"
        os.symlink(str(self.root), str(link))
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        reason = self._guard(
            [str(self.root / "notes.txt")],
            env={"CEO_SESSION_ROOTS_ALLOW": str(link)},
        )
        self.assertIsNone(reason)

    def test_unparseable_entry_denies_external_writes(self) -> None:
        """`unparseable: true` → boundary unknowable → fail-CLOSED."""
        self._write_registry(
            {
                self.sid: {
                    "roots": [
                        self._entry("<unparseable>", unparseable=True)
                    ]
                }
            }
        )
        target = self.home_dir / "anywhere-external" / "f.txt"
        reason = self._guard([str(target)])
        self.assertIsNotNone(reason)
        self.assertIn("session_root_unparseable", reason)

    def test_malformed_entry_without_directory_denies(self) -> None:
        """A recorded root with no usable directory is the same class as
        unparseable — fail-CLOSED in the consumer."""
        self._write_registry(
            {self.sid: {"roots": [{"source": "slash_command"}]}}
        )
        reason = self._guard([str(self.home_dir / "x.txt")])
        self.assertIsNotNone(reason)
        self.assertIn("session_root_unparseable", reason)

    def test_registry_absent_allows(self) -> None:
        """No registry = observer never ran → INFRA-side allow."""
        reason = self._guard([str(self.root / "notes.txt")])
        self.assertIsNone(reason)

    def test_registry_corrupt_denies_external_write(self) -> None:
        """FXγ (C3): a PRESENT-but-unparseable registry is an INPUT-parse
        failure of a security matcher, not an ABSENT-file INFRA condition →
        fail-CLOSED for writes that cannot be proven repo-internal."""
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json at all", encoding="utf-8")
        reason = self._guard([str(self.root / "notes.txt")])
        self.assertIsNotNone(reason)
        self.assertIn("session_roots_registry_unreadable", reason)

    def test_registry_non_utf8_denies_external_write(self) -> None:
        """C3 (codex/grok R5): a PRESENT registry whose bytes are not
        decodable as utf-8 raises UnicodeDecodeError (IS-A ValueError, NOT
        OSError) — present-but-unparseable security-matcher input, so it
        must fail CLOSED for external writes exactly like corrupt JSON. The
        earlier read_text(encoding='utf-8') let UnicodeDecodeError escape to
        the caller's infra catch-all and wrongly ALLOW a binary registry
        overwrite; reading raw bytes + decoding inside the fail-closed parse
        block keeps it closed."""
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xff\xfe\x00\x01 not utf8 \xc0\xc0")
        reason = self._guard([str(self.root / "notes.txt")])
        self.assertIsNotNone(reason)
        self.assertIn("session_roots_registry_unreadable", reason)

    def test_registry_corrupt_allows_repo_internal_write(self) -> None:
        """FXγ cross-state: the corrupt-registry deny is scoped to EXTERNAL
        writes — a repo-internal write stays governed by the canonical
        stack, so the corrupt registry must NOT deny it here."""
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json at all", encoding="utf-8")
        reason = self._guard([str(Path(self.project_dir) / "inside.py")])
        self.assertIsNone(reason)

    def test_registry_corrupt_multi_candidate_any_external_denies(self) -> None:
        """FXγ: one repo-internal candidate must not smuggle a sibling
        external write through under a corrupt registry."""
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json at all", encoding="utf-8")
        reason = self._guard(
            [
                str(Path(self.project_dir) / "inside.py"),
                str(self.root / "notes.txt"),
            ]
        )
        self.assertIsNotNone(reason)
        self.assertIn("session_roots_registry_unreadable", reason)

    def test_registry_corrupt_uncanonicalizable_candidate_denies(self) -> None:
        """FXγ: under a corrupt registry a NUL-bearing path cannot be proven
        repo-internal → fail-CLOSED (not waved through as INFRA)."""
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json at all", encoding="utf-8")
        reason = self._guard(["/somewhere/bad\x00path/file.txt"])
        self.assertIsNotNone(reason)
        self.assertIn("session_roots_registry_unreadable", reason)

    def test_registry_unknown_schema_denies_external_write(self) -> None:
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema": 99,
                    "sessions": {
                        self.sid: {"roots": [self._entry(str(self.root))]}
                    },
                }
            ),
            encoding="utf-8",
        )
        reason = self._guard([str(self.root / "notes.txt")])
        self.assertIsNotNone(reason)
        self.assertIn("session_roots_registry_unreadable", reason)

    def test_registry_unknown_schema_allows_repo_internal_write(self) -> None:
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema": 99,
                    "sessions": {
                        self.sid: {"roots": [self._entry(str(self.root))]}
                    },
                }
            ),
            encoding="utf-8",
        )
        reason = self._guard([str(Path(self.project_dir) / "inside.py")])
        self.assertIsNone(reason)

    def test_symlink_traversal_into_root_denied(self) -> None:
        """realpath resolves the symlink → the write is inside the root."""
        link = self.home_dir / "innocent-looking"
        os.symlink(str(self.root), str(link))
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        reason = self._guard([str(link / "escape.txt")])
        self.assertIsNotNone(reason)
        self.assertIn("session_root_write_denied", reason)

    def test_other_session_roots_do_not_affect(self) -> None:
        self._write_registry(
            {"another-session": {"roots": [self._entry(str(self.root))]}}
        )
        reason = self._guard([str(self.root / "notes.txt")])
        self.assertIsNone(reason)

    def test_repo_internal_write_exempt(self) -> None:
        """Even when a registered root CONTAINS the repo, writes that
        resolve inside the repo stay governed by the canonical stack, not
        this guard — while sibling external writes under that same root
        are denied."""
        parent_root = Path(self.project_dir).parent
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(parent_root))]}}
        )
        self.assertIsNone(
            self._guard([str(Path(self.project_dir) / "inside.py")])
        )
        reason = self._guard([str(parent_root / "outside.txt")])
        self.assertIsNotNone(reason)
        self.assertIn("session_root_write_denied", reason)

    def test_uncanonicalizable_path_denies_when_active(self) -> None:
        """A NUL-byte path cannot be realpath'd → security-matcher input →
        fail-CLOSED while roots are registered for this session."""
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        reason = self._guard(["/somewhere/bad\x00path/file.txt"])
        self.assertIsNotNone(reason)
        self.assertIn("session_root_path_uncanonicalizable", reason)

    def test_multi_candidate_any_offender_denies(self) -> None:
        """One benign candidate must not smuggle a second one through."""
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        benign = self.home_dir / "unrelated" / "ok.txt"
        reason = self._guard([str(benign), str(self.root / "sneaky.txt")])
        self.assertIsNotNone(reason)
        self.assertIn("session_root_write_denied", reason)

    def test_allow_env_var_name_pinned(self) -> None:
        """Pin the consumed env-var name (S218 env-inventory drift class)."""
        self.assertEqual(
            _MOD._SESSION_ROOTS_ALLOW_ENV, "CEO_SESSION_ROOTS_ALLOW"
        )

    # ---- PLAN-163 fix-pass (FX3): H5 / M1 / M2 hardening ----

    def _read_audit_events(self):
        """Parse the isolated audit-log.jsonl into a list of event dicts.

        TestEnvContext pins CEO_AUDIT_LOG_PATH under self.audit_dir, so any
        in-process emit from the guard lands here (SYNC_MODE_DEFAULT).
        """
        log = self.audit_dir / "audit-log.jsonl"
        if not log.is_file():
            return []
        events = []
        for line in log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        return events

    def _reason_codes(self):
        return [e.get("reason_code") for e in self._read_audit_events()]

    def test_registry_corrupt_denies_external_and_emits_tamper_event(self) -> None:
        """H5 + FXγ: a corrupt registry now fail-CLOSES an external write
        (deny) AND still emits the `session_roots_registry_unreadable`
        tamper event, so a registry-rewrite attack is both blocked (for the
        external write it opened) and HMAC-observable."""
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json at all", encoding="utf-8")
        reason = self._guard([str(self.root / "notes.txt")])
        # FXγ: external write under a corrupt registry is now DENIED
        self.assertIsNotNone(reason)
        self.assertIn("session_roots_registry_unreadable", reason)
        # ...and the tamper is still recorded in the audit chain
        self.assertIn(
            "session_roots_registry_unreadable", self._reason_codes()
        )

    def test_registry_corrupt_repo_internal_emits_tamper_no_deny(self) -> None:
        """FXγ cross-state: even for a repo-internal write (which is ALLOWED
        by this guard), the corruption is still recorded as a tamper event —
        the observability is unconditional, only the deny is external-scoped."""
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json at all", encoding="utf-8")
        reason = self._guard([str(Path(self.project_dir) / "inside.py")])
        self.assertIsNone(reason)
        self.assertIn(
            "session_roots_registry_unreadable", self._reason_codes()
        )

    def test_registry_unknown_schema_denies_external_emits_tamper(self) -> None:
        """Same fail-closed + tamper-observability for an unknown-schema
        registry with an external write."""
        path = self.project_dir / ".claude" / "state" / "session-roots.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema": 99,
                    "sessions": {
                        self.sid: {"roots": [self._entry(str(self.root))]}
                    },
                }
            ),
            encoding="utf-8",
        )
        reason = self._guard([str(self.root / "notes.txt")])
        self.assertIsNotNone(reason)
        self.assertIn("session_roots_registry_unreadable", reason)
        self.assertIn(
            "session_roots_registry_unreadable", self._reason_codes()
        )

    def test_registry_empty_overwrite_allows_no_tamper_event(self) -> None:
        """A legitimately EMPTY registry ({"schema":1,"sessions":{}}) is a
        valid parse → allow with NO tamper event. (The empty-overwrite
        BYPASS is a documented residual, not a corruption; the corruption
        signal is reserved for unparseable/unknown-schema.)"""
        self._write_registry({})
        reason = self._guard([str(self.root / "notes.txt")])
        self.assertIsNone(reason)
        self.assertNotIn(
            "session_roots_registry_unreadable", self._reason_codes()
        )

    def test_missing_session_id_with_registry_denies_external(self) -> None:
        """M1: empty/absent session_id while the registry holds roots →
        fail-CLOSED on external writes (clearing CLAUDE_SESSION_ID must not
        neutralize the guard)."""
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        target = self.home_dir / "anywhere-external" / "f.txt"
        reason = self._guard([str(target)], sid="")
        self.assertIsNotNone(reason)
        self.assertIn("session_id_missing", reason)

    def test_missing_session_id_repo_internal_write_allowed(self) -> None:
        """M1 is scoped to EXTERNAL writes: with no session_id, a
        repo-internal write stays governed by the canonical stack, not
        denied here."""
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        reason = self._guard(
            [str(Path(self.project_dir) / "inside.py")], sid=""
        )
        self.assertIsNone(reason)

    def test_missing_session_id_empty_registry_allows(self) -> None:
        """No session_id AND an empty registry → nothing to guard → allow
        (the M1 deny only fires when registered sessions actually exist)."""
        self._write_registry({})
        reason = self._guard([str(self.root / "notes.txt")], sid="")
        self.assertIsNone(reason)

    def test_relative_directory_entry_denies(self) -> None:
        """M2: a registered root whose `directory` is RELATIVE would resolve
        against the process CWD → boundary mis-scoped → fail-CLOSED, same
        class as unparseable."""
        self._write_registry(
            {self.sid: {"roots": [self._entry("relative/added/root")]}}
        )
        target = self.home_dir / "anywhere-external" / "f.txt"
        reason = self._guard([str(target)])
        self.assertIsNotNone(reason)
        self.assertIn("session_root_unparseable", reason)

    def test_absolute_directory_entry_still_enforced(self) -> None:
        """M2 mirror: an ABSOLUTE directory still enforces normally (deny a
        write inside it, allow an unrelated one) — the isabs gate does not
        break the happy path."""
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        self.assertIsNotNone(self._guard([str(self.root / "x.txt")]))
        self.assertIsNone(
            self._guard([str(self.home_dir / "elsewhere" / "y.txt")])
        )


@unittest.skipIf(_MOD is None, _SKIP_REASON)
class TestSessionRootsGuardIntegration(_SessionRootsBase):
    """End-to-end: the extended hook run as a subprocess (main() wiring)."""

    def _run_hook(self, hook_path: Path, target: str, extra_env=None):
        payload = {
            "session_id": self.sid,
            "hook_event_name": "PreToolUse",
            "cwd": str(self.project_dir),
            "tool_name": "Write",
            "tool_input": {"file_path": target, "content": "x"},
        }
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        env["CLAUDE_SESSION_ID"] = self.sid
        env.pop("CEO_SESSION_ROOTS_ALLOW", None)
        env.pop("CEO_HOOK_ADAPTER", None)
        live_dir = str(_LIVE_HOOKS_DIR) if _LIVE_HOOKS_DIR else ""
        prior_pp = env.get("PYTHONPATH") or ""
        env["PYTHONPATH"] = (
            live_dir + (os.pathsep + prior_pp if prior_pp else "")
        )
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(hook_path)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    @staticmethod
    def _decision(stdout: str) -> dict:
        lines = [ln for ln in stdout.strip().splitlines() if ln.strip()]
        if not lines:
            return {}
        return json.loads(lines[-1])

    def test_hook_blocks_write_under_registered_root(self) -> None:
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        proc = self._run_hook(_MOD_PATH, str(self.root / "loot.txt"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = self._decision(proc.stdout)
        self.assertEqual(out.get("decision"), "block", proc.stdout)
        self.assertIn("session_root_write_denied", out.get("reason") or "")

    def test_hook_allows_when_root_allowlisted(self) -> None:
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        proc = self._run_hook(
            _MOD_PATH,
            str(self.root / "loot.txt"),
            extra_env={"CEO_SESSION_ROOTS_ALLOW": str(self.root)},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = self._decision(proc.stdout)
        self.assertNotEqual(out.get("decision"), "block", proc.stdout)

    def test_hook_allows_when_registry_absent(self) -> None:
        proc = self._run_hook(_MOD_PATH, str(self.root / "loot.txt"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = self._decision(proc.stdout)
        self.assertNotEqual(out.get("decision"), "block", proc.stdout)


class TestRedPathLiveHook(_SessionRootsBase):
    """Pre-landing red proof: the LIVE (unextended) hook lets a write
    under a registered, non-allowlisted root PASS. Auto-skips once the
    pack lands (live hook carries `_session_roots_guard`) — the same
    auto-detection pattern as the PLAN-064 marker tests."""

    @unittest.skipUnless(
        _live_hook_lacks_guard(),
        "live hook already carries _session_roots_guard (pack landed) — "
        "the red gap this test documents no longer exists",
    )
    def test_live_hook_allows_write_under_registered_root(self) -> None:
        self._write_registry(
            {self.sid: {"roots": [self._entry(str(self.root))]}}
        )
        payload = {
            "session_id": self.sid,
            "hook_event_name": "PreToolUse",
            "cwd": str(self.project_dir),
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.root / "loot.txt"),
                "content": "x",
            },
        }
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        env["CLAUDE_SESSION_ID"] = self.sid
        env.pop("CEO_SESSION_ROOTS_ALLOW", None)
        env.pop("CEO_HOOK_ADAPTER", None)
        proc = subprocess.run(
            [sys.executable, str(_LIVE_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [
            ln for ln in proc.stdout.strip().splitlines() if ln.strip()
        ]
        out = json.loads(lines[-1]) if lines else {}
        # THE GAP: no extension → the write under the registered root is
        # allowed straight through.
        self.assertNotEqual(out.get("decision"), "block", proc.stdout)


if __name__ == "__main__":
    unittest.main()
