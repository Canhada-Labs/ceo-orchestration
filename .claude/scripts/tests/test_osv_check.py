"""Tests for `.claude/scripts/osv_check.py` (PLAN-133 E2).

The OSV.dev supply-chain gate decision contract (load-bearing):

  * MAL advisory present        → BLOCK   (fail-CLOSED)
  * no record / clean / vulns   → ALLOW   (fail-OPEN, distinct reasons)
  * network timeout / error     → ALLOW   (fail-OPEN + breadcrumb)
  * malformed / empty body      → ALLOW   (inconclusive — NEVER allow-on-MAL)
  * disabled / offline          → SKIP    (advisory-skip, never hang)
  * property: a present MAL advisory can NEVER be downgraded to "unknown".

All tests are hermetic — the network layer (`_post_json`) is monkeypatched;
NO live OSV call is ever made. Env is isolated via `mock.patch.dict` so no
real `$HOME` / process env is touched.
"""
from __future__ import annotations

import importlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Import TestEnvContext from _lib so these tests get per-test env isolation
# (env-hygiene mandate) instead of bare unittest.TestCase.
_HOOKS_DIR = str(Path(__file__).resolve().parents[3] / ".claude" / "hooks")
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)
from _lib.testing import TestEnvContext  # noqa: E402

osv_check = importlib.import_module("osv_check")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _patch_post(return_value):
    """Patch _post_json to return a fixed (body, status) tuple."""
    return mock.patch.object(osv_check, "_post_json", return_value=return_value)


def _mal_body():
    return ({"vulns": [{"id": "MAL-2024-1234", "aliases": ["GHSA-xxxx"]}]}, "ok")


def _clean_body():
    return ({"vulns": [{"id": "GHSA-aaaa-bbbb-cccc"}]}, "ok")


def _unknown_body():
    return ({"vulns": []}, "ok")


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

class ParseInstallTargetTests(TestEnvContext):
    def test_npx_with_version(self):
        t = osv_check.parse_install_target("npx left-pad@1.0.0")
        self.assertEqual(t, {"name": "left-pad", "version": "1.0.0", "ecosystem": "npm"})

    def test_npx_scoped(self):
        t = osv_check.parse_install_target("npx @scope/tool@2.3.4")
        self.assertEqual(t["name"], "@scope/tool")
        self.assertEqual(t["version"], "2.3.4")
        self.assertEqual(t["ecosystem"], "npm")

    def test_npx_scoped_no_version(self):
        t = osv_check.parse_install_target("npx @scope/tool")
        self.assertEqual(t["name"], "@scope/tool")
        self.assertIsNone(t["version"])

    def test_pip_install_pinned(self):
        t = osv_check.parse_install_target("pip install requests==2.31.0")
        self.assertEqual(t["name"], "requests")
        self.assertEqual(t["version"], "2.31.0")
        self.assertEqual(t["ecosystem"], "PyPI")

    def test_pip3_install(self):
        t = osv_check.parse_install_target("pip3 install flask>=2.0")
        self.assertEqual(t["name"], "flask")
        self.assertEqual(t["ecosystem"], "PyPI")

    def test_uv_pip_install(self):
        t = osv_check.parse_install_target("uv pip install httpx")
        self.assertEqual(t["name"], "httpx")
        self.assertEqual(t["ecosystem"], "PyPI")

    def test_uvx(self):
        t = osv_check.parse_install_target("uvx ruff")
        self.assertEqual(t["name"], "ruff")
        self.assertEqual(t["ecosystem"], "PyPI")

    def test_pypi_extras_stripped(self):
        t = osv_check.parse_install_target("pip install uvicorn[standard]==0.20")
        self.assertEqual(t["name"], "uvicorn")
        self.assertEqual(t["version"], "0.20")

    def test_skips_flags(self):
        t = osv_check.parse_install_target("pip install --upgrade requests")
        self.assertEqual(t["name"], "requests")

    def test_non_install_command_is_none(self):
        self.assertIsNone(osv_check.parse_install_target("ls -la /tmp"))

    def test_pip_download_is_not_install(self):
        self.assertIsNone(osv_check.parse_install_target("pip download foo"))

    def test_local_path_not_a_package(self):
        self.assertIsNone(osv_check.parse_install_target("pip install ./mylocaldir"))
        self.assertIsNone(osv_check.parse_install_target("pip install /abs/path"))

    def test_vcs_url_not_a_package(self):
        self.assertIsNone(osv_check.parse_install_target("pip install git+https://x/y.git"))

    def test_requirements_file_not_a_package(self):
        self.assertIsNone(osv_check.parse_install_target("pip install -r requirements.txt"))

    def test_empty_and_none(self):
        self.assertIsNone(osv_check.parse_install_target(""))
        self.assertIsNone(osv_check.parse_install_target(None))  # type: ignore[arg-type]

    def test_wrapped_with_sudo_prefix(self):
        t = osv_check.parse_install_target("sudo pip install evil-pkg")
        self.assertEqual(t["name"], "evil-pkg")


# --------------------------------------------------------------------------- #
# query_osv decision contract
# --------------------------------------------------------------------------- #

class QueryOsvVerdictTests(TestEnvContext):
    def test_mal_hit_blocks_fail_closed(self):
        with _patch_post(_mal_body()):
            r = osv_check.query_osv("evil", "npm", "1.0.0", 4.0)
        self.assertEqual(r["verdict"], osv_check.VERDICT_BLOCK)
        self.assertEqual(r["reason"], osv_check.REASON_MAL)
        self.assertIn("MAL-2024-1234", r["advisory_ids"])

    def test_unknown_allows_fail_open(self):
        with _patch_post(_unknown_body()):
            r = osv_check.query_osv("left-pad", "npm", None, 4.0)
        self.assertEqual(r["verdict"], osv_check.VERDICT_ALLOW)
        self.assertEqual(r["reason"], osv_check.REASON_UNKNOWN)
        self.assertEqual(r["advisory_ids"], [])

    def test_clean_vulns_allows(self):
        with _patch_post(_clean_body()):
            r = osv_check.query_osv("requests", "PyPI", None, 4.0)
        self.assertEqual(r["verdict"], osv_check.VERDICT_ALLOW)
        self.assertEqual(r["reason"], osv_check.REASON_CLEAN)

    def test_network_timeout_fails_open(self):
        with _patch_post((None, osv_check.REASON_NETWORK_TIMEOUT)):
            r = osv_check.query_osv("x", "npm", None, 4.0)
        self.assertEqual(r["verdict"], osv_check.VERDICT_ALLOW)
        self.assertEqual(r["reason"], osv_check.REASON_NETWORK_TIMEOUT)

    def test_network_error_fails_open(self):
        with _patch_post((None, osv_check.REASON_NETWORK_ERROR)):
            r = osv_check.query_osv("x", "npm", None, 4.0)
        self.assertEqual(r["verdict"], osv_check.VERDICT_ALLOW)
        self.assertEqual(r["reason"], osv_check.REASON_NETWORK_ERROR)

    def test_malformed_body_is_inconclusive_not_mal(self):
        with _patch_post((None, osv_check.REASON_MALFORMED)):
            r = osv_check.query_osv("x", "npm", None, 4.0)
        self.assertEqual(r["verdict"], osv_check.VERDICT_ALLOW)
        self.assertEqual(r["reason"], osv_check.REASON_MALFORMED)
        # Inconclusive must NEVER be reported as a MAL.
        self.assertNotEqual(r["reason"], osv_check.REASON_MAL)

    def test_non_dict_body_is_malformed(self):
        # body=None with "ok" status (shouldn't normally happen) → malformed branch.
        with _patch_post((None, "ok")):
            r = osv_check.query_osv("x", "npm", None, 4.0)
        self.assertEqual(r["reason"], osv_check.REASON_MALFORMED)


# --------------------------------------------------------------------------- #
# Property: MAL can NEVER be downgraded to unknown
# --------------------------------------------------------------------------- #

class MalNeverDowngradedTests(TestEnvContext):
    def test_mal_never_downgraded_across_alias_shapes(self):
        # MAL id surfaced only via aliases, with an empty top-level id family.
        bodies = [
            {"vulns": [{"id": "OSV-2024-9", "aliases": ["MAL-2024-1"]}]},
            {"vulns": [{"id": "MAL-2024-2"}]},
            {"vulns": [{"id": "GHSA-x"}, {"id": "MAL-2024-3"}]},
            {"vulns": [{"id": "OSV-MAL-2024-4"}]},
        ]
        for b in bodies:
            with _patch_post((b, "ok")):
                r = osv_check.query_osv("p", "npm", "1.0", 4.0)
            self.assertEqual(r["verdict"], osv_check.VERDICT_BLOCK, b)
            self.assertEqual(r["reason"], osv_check.REASON_MAL, b)
            self.assertNotEqual(r["reason"], osv_check.REASON_UNKNOWN, b)

    def test_verdict_helper_rejects_fake_mal(self):
        # The _verdict invariant forbids a REASON_MAL that is not BLOCK+ids.
        with self.assertRaises(AssertionError):
            osv_check._verdict(
                osv_check.VERDICT_ALLOW, osv_check.REASON_MAL, [], "p", "npm"
            )
        with self.assertRaises(AssertionError):
            osv_check._verdict(
                osv_check.VERDICT_BLOCK, osv_check.REASON_MAL, [], "p", "npm"
            )

    def test_extract_mal_ids_does_not_invent(self):
        # No MAL token anywhere → empty list (cannot fabricate a MAL).
        ids = osv_check._extract_mal_ids([{"id": "GHSA-only"}, {"aliases": ["CVE-1"]}])
        self.assertEqual(ids, [])


# --------------------------------------------------------------------------- #
# check_command: disabled / offline / gating
# --------------------------------------------------------------------------- #

class CheckCommandTests(TestEnvContext):
    def test_disabled_skips(self):
        with mock.patch.dict("os.environ", {"CEO_OSV_DISABLE": "1"}, clear=False):
            r = osv_check.check_command("npx evil@1.0.0")
        self.assertEqual(r["verdict"], osv_check.VERDICT_SKIP)
        self.assertEqual(r["reason"], osv_check.REASON_DISABLED)

    def test_sota_disable_also_skips(self):
        with mock.patch.dict("os.environ", {"CEO_SOTA_DISABLE": "1"}, clear=False):
            r = osv_check.check_command("npx evil@1.0.0")
        self.assertEqual(r["verdict"], osv_check.VERDICT_SKIP)

    def test_offline_skips_without_network(self):
        called = {"n": 0}

        def _boom(*a, **k):
            called["n"] += 1
            raise AssertionError("network must not be called when offline")

        with mock.patch.object(osv_check, "_post_json", _boom):
            with mock.patch.dict("os.environ", {"CEO_OSV_OFFLINE": "1"}, clear=False):
                r = osv_check.check_command("npx evil@1.0.0")
        self.assertEqual(r["verdict"], osv_check.VERDICT_SKIP)
        self.assertEqual(r["reason"], osv_check.REASON_OFFLINE)
        self.assertEqual(called["n"], 0)

    def test_non_install_command_skips_no_package(self):
        r = osv_check.check_command("echo hi")
        self.assertEqual(r["verdict"], osv_check.VERDICT_SKIP)
        self.assertEqual(r["reason"], osv_check.REASON_NO_PACKAGE)

    def test_mal_hit_through_check_command(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with _patch_post(_mal_body()):
                r = osv_check.check_command("npx evil@1.0.0")
        self.assertEqual(r["verdict"], osv_check.VERDICT_BLOCK)

    def test_query_exception_fails_open(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch.object(osv_check, "query_osv", side_effect=RuntimeError("boom")):
                r = osv_check.check_command("npx evil@1.0.0")
        self.assertEqual(r["verdict"], osv_check.VERDICT_ALLOW)
        self.assertEqual(r["reason"], osv_check.REASON_NETWORK_ERROR)


# --------------------------------------------------------------------------- #
# gate_exit_code — default-OFF behavioral gate
# --------------------------------------------------------------------------- #

class GateExitCodeTests(TestEnvContext):
    def _mal_result(self):
        return osv_check._verdict(
            osv_check.VERDICT_BLOCK, osv_check.REASON_MAL, ["MAL-1"], "p", "npm"
        )

    def test_advisory_mode_default_returns_zero_even_on_mal(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(osv_check.gate_exit_code(self._mal_result()), 0)

    def test_block_mode_returns_nonzero_on_mal(self):
        with mock.patch.dict("os.environ", {"CEO_OSV_GATE": "block"}, clear=True):
            self.assertEqual(osv_check.gate_exit_code(self._mal_result()), 3)

    def test_block_mode_zero_on_timeout(self):
        timeout = osv_check._verdict(
            osv_check.VERDICT_ALLOW, osv_check.REASON_NETWORK_TIMEOUT, [], "p", "npm"
        )
        with mock.patch.dict("os.environ", {"CEO_OSV_GATE": "block"}, clear=True):
            self.assertEqual(osv_check.gate_exit_code(timeout), 0)

    def test_block_mode_zero_on_unknown(self):
        unk = osv_check._verdict(
            osv_check.VERDICT_ALLOW, osv_check.REASON_UNKNOWN, [], "p", "npm"
        )
        with mock.patch.dict("os.environ", {"CEO_OSV_GATE": "block"}, clear=True):
            self.assertEqual(osv_check.gate_exit_code(unk), 0)


# --------------------------------------------------------------------------- #
# Timeout hard ceiling
# --------------------------------------------------------------------------- #

class TimeoutCeilingTests(TestEnvContext):
    def test_default_timeout(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(osv_check._timeout_s(), osv_check._TIMEOUT_DEFAULT_S)

    def test_env_override_clamped_to_hard_ceiling(self):
        with mock.patch.dict("os.environ", {"CEO_OSV_TIMEOUT_S": "999"}, clear=True):
            self.assertEqual(osv_check._timeout_s(), osv_check._TIMEOUT_HARD_CEILING_S)

    def test_garbage_timeout_falls_back(self):
        with mock.patch.dict("os.environ", {"CEO_OSV_TIMEOUT_S": "notanumber"}, clear=True):
            self.assertEqual(osv_check._timeout_s(), osv_check._TIMEOUT_DEFAULT_S)

    def test_zero_or_negative_falls_back(self):
        with mock.patch.dict("os.environ", {"CEO_OSV_TIMEOUT_S": "0"}, clear=True):
            self.assertEqual(osv_check._timeout_s(), osv_check._TIMEOUT_DEFAULT_S)
        with mock.patch.dict("os.environ", {"CEO_OSV_TIMEOUT_S": "-5"}, clear=True):
            self.assertEqual(osv_check._timeout_s(), osv_check._TIMEOUT_DEFAULT_S)


# --------------------------------------------------------------------------- #
# Breadcrumb is value-safe
# --------------------------------------------------------------------------- #

class BreadcrumbTests(TestEnvContext):
    def test_breadcrumb_is_valid_json_with_expected_fields(self):
        result = osv_check._verdict(
            osv_check.VERDICT_BLOCK, osv_check.REASON_MAL, ["MAL-1"], "evil", "npm"
        )
        buf = io.StringIO()
        osv_check.emit_breadcrumb(result, stream=buf)
        line = buf.getvalue().strip()
        rec = json.loads(line)
        self.assertEqual(rec["event"], "supply_chain_advisory_emitted")
        self.assertEqual(rec["verdict"], osv_check.VERDICT_BLOCK)
        self.assertEqual(rec["reason"], osv_check.REASON_MAL)
        self.assertEqual(rec["package"], "evil")
        self.assertEqual(rec["ecosystem"], "npm")
        self.assertIn("MAL-1", rec["advisory_ids"])

    def test_breadcrumb_never_echoes_command_or_secret(self):
        # Even if a name carried junk, the breadcrumb only ever carries the
        # parsed name/ecosystem/ids — never the raw command bytes or env.
        result = osv_check._verdict(
            osv_check.VERDICT_ALLOW, osv_check.REASON_UNKNOWN, [], "pkg", "PyPI"
        )
        buf = io.StringIO()
        osv_check.emit_breadcrumb(result, stream=buf)
        rec = json.loads(buf.getvalue().strip())
        # No raw-command / env / retry_delay fields leak.
        self.assertNotIn("command", rec)
        self.assertNotIn("env", rec)
        self.assertNotIn("retry_delay", rec)
        self.assertEqual(set(rec.keys()),
                         {"event", "verdict", "reason", "ecosystem", "package",
                          "advisory_ids", "ts"})

    def test_breadcrumb_never_raises(self):
        class _Boom:
            def write(self, *a, **k):
                raise IOError("disk full")

            def flush(self):
                raise IOError("disk full")

        # Must not raise.
        osv_check.emit_breadcrumb({"verdict": "ALLOW"}, stream=_Boom())


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

class CliTests(TestEnvContext):
    def test_main_requires_command_or_package(self):
        self.assertEqual(osv_check.main([]), 2)

    def test_main_package_requires_ecosystem(self):
        self.assertEqual(osv_check.main(["--package", "foo"]), 2)

    def test_main_advisory_mode_mal_returns_zero(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with _patch_post(_mal_body()):
                rc = osv_check.main(["--package", "evil", "--ecosystem", "npm"])
        self.assertEqual(rc, 0)  # advisory default — never blocks

    def test_main_block_mode_mal_returns_three(self):
        with mock.patch.dict("os.environ", {"CEO_OSV_GATE": "block"}, clear=True):
            with _patch_post(_mal_body()):
                rc = osv_check.main(["--package", "evil", "--ecosystem", "npm"])
        self.assertEqual(rc, 3)

    def test_main_command_unknown_returns_zero(self):
        with mock.patch.dict("os.environ", {"CEO_OSV_GATE": "block"}, clear=True):
            with _patch_post(_unknown_body()):
                rc = osv_check.main(["--command", "npx left-pad@1.0.0"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
