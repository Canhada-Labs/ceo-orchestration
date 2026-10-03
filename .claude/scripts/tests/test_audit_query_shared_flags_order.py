"""FD-23 — the shared flags of audit-query.py work in BOTH positions.

`_build_shared_parser()` documents that ``audit-query.py --json summary``
and ``audit-query.py summary --json`` are equivalent. Before the cure the
sub-command re-registered every shared flag WITH its default, and argparse
copies the whole sub-command namespace back over the top-level one — so a
flag written BEFORE the sub-command was silently overwritten by the
sub-command default. Measured: ``audit-query.py --log X summary`` read the
default (live) log and reported its counts as if they were X's.

Two layers:

1. ``TestSharedFlagsParseBothOrders`` — the CLASS guard. Every sub-command
   registered by ``build_parser()`` × every flag of ``_build_shared_parser()``
   (both enumerated from the parser itself, so a new sub-command or a new
   shared flag is covered without editing this file): before == after ==
   expected value, absent == top-level default, and — the documented
   precedence rule — a value flag given on both sides resolves to the
   sub-command-level value.
2. ``TestSharedFlagsExecuteBothOrders`` — end to end through ``main()``
   against synthetic logs in the per-test tmp tree (never the live log,
   never the real $HOME — ``TestEnvContext`` points the defaults at a
   sandbox DECOY). For each shared flag × a sample of sub-commands covering
   every ``_add_*_subparsers`` group: the two orders print byte-identical
   output, and that output differs from the flag-absent run (the case is
   not vacuous — the flag's effect, e.g. reading the REQUESTED file instead
   of the default, is observable).

The clock is frozen inside ``main()`` so window-bounded sub-commands
(``case-summary`` prints ``window_end`` to the second) are deterministic.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_AQ_PATH = _REPO_ROOT / ".claude" / "scripts" / "audit-query.py"
_spec = importlib.util.spec_from_file_location("audit_query_fd23", str(_AQ_PATH))
aq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aq)


_FROZEN_NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)


class _FrozenDatetime(datetime):
    """``datetime`` whose ``now()`` is pinned to ``_FROZEN_NOW``."""

    @classmethod
    def now(cls, tz: Optional[Any] = None) -> datetime:  # type: ignore[override]
        if tz is None:
            return _FROZEN_NOW.replace(tzinfo=None)
        return _FROZEN_NOW.astimezone(tz)


def _shared_flag_actions() -> List[argparse.Action]:
    """Every optional flag of the shared parent parser (no help action)."""
    return [a for a in aq._build_shared_parser()._actions if a.option_strings]


def _subcommand_parsers(parser: argparse.ArgumentParser) -> Dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    raise AssertionError("build_parser() registered no sub-commands")


def _placeholder(action: argparse.Action) -> str:
    if action.choices:
        return str(sorted(action.choices)[0])
    if action.type is int or action.type is float:
        return "1"
    return "x"


def _required_tail(sub: argparse.ArgumentParser) -> List[str]:
    """Minimal argv a sub-command needs to parse (positionals + required)."""
    tail: List[str] = []
    for action in sub._actions:
        if not action.option_strings:
            if action.nargs not in ("?", "*"):
                tail.append(_placeholder(action))
        elif action.required:
            tail += [action.option_strings[0], _placeholder(action)]
    return tail


def _flag_argv(action: argparse.Action, value: str) -> List[str]:
    opt = action.option_strings[0]
    return [opt] if action.nargs == 0 else [opt, value]


def _expected(action: argparse.Action, value: str) -> Any:
    return action.const if action.nargs == 0 else value


class TestSharedFlagsParseBothOrders(TestEnvContext):
    """Class guard: all sub-commands × all shared flags, at parse level."""

    def _parse(self, argv: List[str]) -> argparse.Namespace:
        err = io.StringIO()
        with redirect_stderr(err):
            try:
                return aq.build_parser().parse_args(argv)
            except SystemExit as exc:  # pragma: no cover — failure path
                self.fail(f"argv {argv!r} did not parse (exit {exc.code}): "
                          f"{err.getvalue().strip()}")
        raise AssertionError("unreachable")  # pragma: no cover

    def test_shared_flags_are_enumerated(self) -> None:
        dests = sorted(a.dest for a in _shared_flag_actions())
        # Pin the current population so a silent drop of a flag is loud;
        # ADDING a flag only needs this list (and an execution case below).
        self.assertEqual(
            dests, ["as_csv", "as_json", "errors_path", "include_rotated", "log"]
        )

    def test_every_subcommand_honours_every_shared_flag_in_both_orders(self) -> None:
        parser = aq.build_parser()
        subs = _subcommand_parsers(parser)
        self.assertGreater(len(subs), 20, "sub-command enumeration looks broken")
        for name, sub in sorted(subs.items()):
            tail = _required_tail(sub)
            for action in _shared_flag_actions():
                value = f"/fd23/sentinel/{action.dest}"
                want = _expected(action, value)
                flag = _flag_argv(action, value)
                with self.subTest(cmd=name, flag=action.option_strings[0]):
                    before = self._parse(flag + [name] + tail)
                    after = self._parse([name] + tail + flag)
                    absent = self._parse([name] + tail)
                    self.assertEqual(getattr(after, action.dest), want)
                    self.assertEqual(
                        getattr(before, action.dest), want,
                        f"{action.option_strings[0]} given BEFORE {name!r} "
                        f"was discarded by the sub-command default",
                    )
                    self.assertEqual(
                        getattr(absent, action.dest), parser.get_default(action.dest)
                    )

    def test_flag_on_both_sides_resolves_to_the_subcommand_level_value(self) -> None:
        parser = aq.build_parser()
        for name, sub in sorted(_subcommand_parsers(parser).items()):
            tail = _required_tail(sub)
            for action in _shared_flag_actions():
                if action.nargs == 0:
                    continue  # store_true: both sides mean True
                opt = action.option_strings[0]
                with self.subTest(cmd=name, flag=opt):
                    ns = self._parse([opt, "/fd23/top", name] + tail + [opt, "/fd23/sub"])
                    self.assertEqual(getattr(ns, action.dest), "/fd23/sub")


def _events(tag: str, spawns: int, extras: int) -> List[Dict[str, Any]]:
    """A synthetic log whose every sampled sub-command sees ``tag``'s data."""
    ts = (_FROZEN_NOW - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: List[Dict[str, Any]] = []
    for i in range(spawns):
        rows.append({
            "ts": ts, "action": "agent_spawn", "skill": f"{tag}-skill",
            "subagent_type": f"{tag}-agent", "model": f"{tag}-model",
            "tokens_in": 100 + i, "tokens_out": 10 + i,
            "dispatch_archetype_hint": f"{tag}-domain",
            "desc_preview": f"{tag} spawn {i}",
        })
    for _ in range(extras):
        rows.append({"ts": ts, "action": "veto_triggered", "hook": f"{tag}-hook",
                     "reason_code": f"{tag}-reason", "reason_preview": tag})
        rows.append({"ts": ts, "action": "confidence_gate", "agent_name": f"{tag}-agent",
                     "claim_count": 2, "pass_count": 1, "fail_count": 1,
                     "verifier_kind_counts": {"path_exists": 2}})
        rows.append({"ts": ts, "action": "pair_rail_case", "case": "A"})
        rows.append({"ts": ts, "action": aq._CRITICAL_SECURITY_ACTIONS[0]})
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


# One sub-command per `_add_*_subparsers` group (v1, v2, sprint8_9, plan015,
# plan080, plan081, plan113) plus a second v1/v2 member. `label` is left to
# the parse-level guard — it APPENDS to a label store.
_LOG_READERS: Tuple[str, ...] = (
    "summary", "by-skill", "tokens", "vetoes", "claims", "spawn-stats",
    "by-domain", "case-summary", "critical",
)


class TestSharedFlagsExecuteBothOrders(TestEnvContext):
    """End to end through ``main()``: before == after != absent."""

    def setUp(self) -> None:
        super().setUp()
        # Defaults (TestEnvContext's CEO_AUDIT_LOG_PATH / CEO_AUDIT_LOG_ERR)
        # hold the DECOY; a rotated sibling sits next to it.
        self.default_log = Path(aq.default_log_path())
        self.assertTrue(str(self.default_log).startswith(str(self._tmp_root)))
        self.decoy_rows = _events("decoy", spawns=3, extras=1)
        _write_jsonl(self.default_log, self.decoy_rows)
        _write_jsonl(self.default_log.parent / "audit-log-2026-09.jsonl",
                     _events("rotated", spawns=5, extras=3))
        self.default_errors = Path(aq.default_errors_path())
        self.assertTrue(str(self.default_errors).startswith(str(self._tmp_root)))
        self.default_errors.write_text("decoy error line\n", encoding="utf-8")
        # The REQUESTED files live in their own dir (no rotated siblings).
        req_dir = self._tmp_root / "requested"
        self.req_rows = _events("req", spawns=9, extras=2)
        self.req_log = _write_jsonl(req_dir / "audit-log.jsonl", self.req_rows)
        self.req_errors = req_dir / "req.errors"
        self.req_errors.write_text("req error 1\nreq error 2\n", encoding="utf-8")

    def _run(self, argv: List[str]) -> Tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(aq, "datetime", _FrozenDatetime), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                rc = aq.main(list(argv))
            except SystemExit as exc:
                rc = exc.code if isinstance(exc.code, int) else 1
        return rc, out.getvalue()

    def _cases(self) -> Dict[str, List[Tuple[str, List[str], List[str], List[str]]]]:
        """dest → [(cmd, flag argv, argv before the flag, argv after it)]."""
        log = ["--log", str(self.req_log)]
        rot = ["--include-rotated"]
        cases: Dict[str, List[Tuple[str, List[str], List[str], List[str]]]] = {
            "log": [(c, log, [c], ["--json"]) for c in _LOG_READERS],
            "include_rotated": [(c, rot, [c], ["--json"]) for c in _LOG_READERS],
            "as_json": [(c, ["--json"], [c], []) for c in _LOG_READERS + ("errors",)],
            # CSV only changes list-of-dict results; `vetoes` is one.
            "as_csv": [("vetoes", ["--csv"], ["vetoes"], [])],
            # `errors` is the only consumer of --errors-path.
            "errors_path": [("errors", ["--errors-path", str(self.req_errors)],
                             ["errors"], ["--json"])],
        }
        return cases

    def test_every_shared_flag_has_an_execution_case(self) -> None:
        self.assertEqual(
            sorted(self._cases()), sorted(a.dest for a in _shared_flag_actions())
        )

    def test_both_orders_print_the_same_and_the_flag_takes_effect(self) -> None:
        for dest, rows in sorted(self._cases().items()):
            for cmd, flag, head, rest in rows:
                after_argv = head + rest + flag
                before_argv = flag + head + rest
                absent_argv = head + rest
                with self.subTest(flag=flag[0], cmd=cmd):
                    rc_a, out_a = self._run(after_argv)
                    rc_b, out_b = self._run(before_argv)
                    rc_c, out_c = self._run(absent_argv)
                    self.assertEqual((rc_a, rc_b, rc_c), (0, 0, 0))
                    self.assertEqual(
                        out_b, out_a,
                        f"{before_argv!r} printed something different from "
                        f"{after_argv!r}",
                    )
                    self.assertNotEqual(
                        out_a, out_c,
                        f"vacuous case: {flag[0]} had no observable effect on {cmd!r}",
                    )

    def test_log_before_subcommand_reads_the_requested_file(self) -> None:
        rc, out = self._run(["--log", str(self.req_log), "summary", "--json"])
        self.assertEqual(rc, 0)
        # `summary` counts every row of the file it read.
        self.assertEqual(json.loads(out)["total_spawns"], len(self.req_rows),
                         "summary did not read the --log file")
        self.assertIn("req-skill", out)
        self.assertNotIn("decoy-skill", out)
        rc, out = self._run(["summary", "--json"])
        self.assertEqual(json.loads(out)["total_spawns"], len(self.decoy_rows))

    def test_errors_path_before_subcommand_reads_the_requested_file(self) -> None:
        rc, out = self._run(["--errors-path", str(self.req_errors), "errors", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["errors_path"], str(self.req_errors))
        self.assertEqual(data["count"], 2)


if __name__ == "__main__":
    unittest.main()
