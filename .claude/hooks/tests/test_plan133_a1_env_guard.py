#!/usr/bin/env python3
"""PLAN-133 A1 — env-hijack denylist: detection + no-value-echo property tests.

Env / HOME isolation via ``TestEnvContext`` (never the real $HOME / audit log).
Asserts:
  - the 31-key denylist detects each set-shape (prefix / export / env(1));
  - a bare reference ($LD_PRELOAD) is NOT a set;
  - the emitted env_var_hijack_blocked event carries ONLY the closed-enum
    hijack_class — never the variable NAME, never the assigned VALUE;
  - the audit_emit closed set mirrors env_guard's (no drift);
  - an out-of-set hijack_class is coerced to "parse_failure".
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import env_guard  # noqa: E402
from _lib import audit_emit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class EnvGuardDetectionTests(TestEnvContext):
    def test_denylist_is_31_unique_keys(self):
        self.assertEqual(len(env_guard.DISALLOWED_ENV_KEYS), 31)

    def test_assignment_prefix_blocks(self):
        m = env_guard.scan_command("LD_PRELOAD=/tmp/evil.so make all")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "LD_PRELOAD")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_LINKER_PRELOAD)

    def test_export_blocks(self):
        m = env_guard.scan_command("export DYLD_INSERT_LIBRARIES=/tmp/x.dylib")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "DYLD_INSERT_LIBRARIES")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_LINKER_PRELOAD)

    def test_env_wrapper_blocks(self):
        m = env_guard.scan_command("env NODE_OPTIONS=--require=/tmp/x node app.js")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "NODE_OPTIONS")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_RUNTIME_HOOK)

    def test_env_wrapper_unset_flag_does_not_hide_later_set(self):
        # `env -u FOO LD_PRELOAD=...` — the '-u' flag consumes the FOLLOWING
        # token (FOO, a name to unset); detection must NOT stop there and must
        # still catch the LD_PRELOAD= set that follows.
        m = env_guard.scan_command("env -u FOO LD_PRELOAD=/tmp/evil.so make")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "LD_PRELOAD")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_LINKER_PRELOAD)

    def test_env_wrapper_unset_equals_form_does_not_hide_later_set(self):
        # `--unset=NAME` is self-contained; the following LD_PRELOAD= still hits.
        m = env_guard.scan_command("env --unset=FOO LD_PRELOAD=/tmp/evil.so make")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "LD_PRELOAD")

    def test_env_wrapper_unset_attached_form_does_not_hide_later_set(self):
        # `env -uFOO LD_PRELOAD=...` — the attached short form glues the name to
        # the flag (one token); it must be consumed as a self-contained unset and
        # detection must still catch the LD_PRELOAD= set that follows.
        m = env_guard.scan_command("env -uFOO LD_PRELOAD=/tmp/evil.so make")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "LD_PRELOAD")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_LINKER_PRELOAD)

    def test_env_wrapper_cluster_separated_unset_does_not_hide_later_set(self):
        # `env -iu FOO LD_PRELOAD=...` — `-iu` is a getopt CLUSTER (i=ignore-env,
        # u=unset). The 'u' consumes the FOLLOWING token (FOO); scanning must
        # continue and still catch the LD_PRELOAD= set that follows.
        m = env_guard.scan_command("env -iu FOO LD_PRELOAD=/tmp/x make")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "LD_PRELOAD")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_LINKER_PRELOAD)

    def test_env_wrapper_cluster_attached_unset_does_not_hide_later_set(self):
        # `env -iuFOO LD_PRELOAD=...` — `-iuFOO` is a CLUSTER where 'u' takes the
        # REST of the token (FOO) as its arg in-token. Scanning must continue and
        # still catch the LD_PRELOAD= set that follows.
        m = env_guard.scan_command("env -iuFOO LD_PRELOAD=/tmp/x make")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "LD_PRELOAD")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_LINKER_PRELOAD)

    def test_env_wrapper_clean_assignment_after_options_stays_clean(self):
        # A non-denylisted env set (with options) must NOT false-positive.
        self.assertIsNone(env_guard.scan_command("env -i FOO=bar make all"))
        self.assertIsNone(env_guard.scan_command("env -iu FOO BAR=baz make"))
        self.assertIsNone(env_guard.scan_command("env -iuFOO BAR=baz make"))

    def test_env_wrapper_alt_path_flag_does_not_hide_later_set(self):
        # `env -P /usr/bin BASH_ENV=...` — `-P` (alt search path) TAKES an arg
        # (/usr/bin); it must NOT be mistaken for the command. Scanning must
        # continue and still catch the BASH_ENV= set that follows. (Verified vs
        # macOS env(1): `env -P /usr/bin BASH_ENV=/tmp/x printenv BASH_ENV`.)
        m = env_guard.scan_command("env -P /usr/bin BASH_ENV=/tmp/x printenv")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "BASH_ENV")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_RUNTIME_HOOK)

    def test_env_wrapper_bare_dash_does_not_hide_later_set(self):
        # `env - BASH_ENV=...` — a lone `-` means ignore-environment (like -i),
        # NOT the command; it must be skipped so the BASH_ENV= set is still
        # caught. (Verified vs macOS env(1): `env - BASH_ENV=/tmp/x printenv`
        # sets BASH_ENV and drops the inherited environment.)
        m = env_guard.scan_command("env - BASH_ENV=/tmp/x printenv")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "BASH_ENV")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_RUNTIME_HOOK)

    def test_path_class(self):
        m = env_guard.scan_command("PYTHONPATH=/tmp/evil python run.py")
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_LINKER_PATH)

    def test_bare_reference_is_not_a_set(self):
        self.assertIsNone(env_guard.scan_command("echo $LD_PRELOAD"))
        self.assertIsNone(env_guard.scan_command("printenv LD_LIBRARY_PATH"))

    def test_non_denylisted_assignment_passes(self):
        self.assertIsNone(env_guard.scan_command("FOO=1 make all"))
        self.assertIsNone(env_guard.scan_command("export EDITOR=vim"))

    def test_chaining_finds_match_in_later_subcommand(self):
        m = env_guard.scan_command("echo hi && BASH_ENV=/tmp/x bash -c 'id'")
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "BASH_ENV")

    def test_unbalanced_quote_smuggling_fails_closed(self):
        # A broken quote can't hide a denylisted SET.
        m = env_guard.scan_command("LD_PRELOAD=/tmp/'evil.so make")
        self.assertIsNotNone(m)
        self.assertEqual(m.hijack_class, env_guard.HIJACK_CLASS_PARSE_FAILURE)

    def test_reason_never_contains_value(self):
        m = env_guard.scan_command("LD_PRELOAD=/tmp/SUPER-SECRET-PAYLOAD.so make")
        self.assertIsNotNone(m)
        self.assertNotIn("SUPER-SECRET-PAYLOAD", m.reason)
        self.assertNotIn("/tmp/", m.reason)


class EnvVarHijackNoValueEchoTests(TestEnvContext):
    """The emitted audit event must NEVER contain the var name or the value."""

    def _emit_and_read(self, hijack_class: str) -> dict:
        # TestEnvContext points HOME/audit at a temp dir; read the last event.
        audit_emit.emit_env_var_hijack_blocked(
            hijack_class=hijack_class, session_id="s", project="p"
        )
        log = self._read_audit_events()  # helper below
        return log[-1]

    def _read_audit_events(self):
        # TestEnvContext defaults SYNC_MODE_DEFAULT=True (sets CEO_AUDIT_SYNC_MODE=1
        # in setUp), so the event is on disk immediately — no async drain needed.
        # self.audit_dir is the isolated audit dir TestEnvContext points env at.
        path = self.audit_dir / "audit-log.jsonl"
        out = []
        if path.exists():
            for line in path.read_text().splitlines():
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def test_emitted_event_has_only_closed_enum_class(self):
        e = self._emit_and_read("linker_preload")
        self.assertEqual(e["action"], "env_var_hijack_blocked")
        self.assertEqual(e["hijack_class"], "linker_preload")
        # No leak of any plausible var name or value.
        blob = json.dumps(e)
        for forbidden in (
            "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "NODE_OPTIONS",
            "evil.so", "/tmp/", "SUPER-SECRET",
        ):
            self.assertNotIn(forbidden, blob)
        # No forbidden field names.
        self.assertNotIn("key", e)
        self.assertNotIn("value", e)
        self.assertNotIn("command", e)
        self.assertNotIn("reason", e)

    def test_out_of_set_class_coerced_to_parse_failure(self):
        # A smuggled raw value in hijack_class is reset (defense-in-depth).
        e = self._emit_and_read("LD_PRELOAD=/tmp/evil.so")
        self.assertEqual(e["hijack_class"], "parse_failure")
        self.assertNotIn("evil.so", json.dumps(e))

    def test_emit_generic_path_also_coerces(self):
        audit_emit.emit_generic(
            action="env_var_hijack_blocked",
            hijack_class="/tmp/secret-payload.so",
            command="LD_PRELOAD=/tmp/secret-payload.so make",  # forbidden field
        )
        e = self._read_audit_events()[-1]
        self.assertEqual(e["hijack_class"], "parse_failure")
        blob = json.dumps(e)
        self.assertNotIn("secret-payload", blob)
        self.assertNotIn("command", e)


class EnvGuardAuditDriftTests(TestEnvContext):
    def test_closed_set_mirrors_audit_emit(self):
        self.assertEqual(
            env_guard.ENV_VAR_HIJACK_CLASSES,
            audit_emit._ENV_VAR_HIJACK_CLASSES,
            "env_guard and audit_emit closed hijack_class sets drifted",
        )


if __name__ == "__main__":
    unittest.main()
