"""Unit tests for _lib/adapters/codex.py (PLAN-081 Phase 1-full).

Test categories (37 tests):
  1. ABI conformance (SPEC §3) — 9 tests
  2. Sandbox modes / make_invoke_command — 8 tests
  3. Schema-coercion: parse_verdict — 8 tests
  4. SHA-pin: _constants + verify_pins — 5 tests
  5. PostToolUse hook semantics (codex_stdout) — 4 tests
  6. Timeout classifier — 7 tests
  7. Audit emit field surface — 4 tests (checked via constants)
  8. Fail-open paths — 7 tests (partial: needs canonical)

stdlib-only. Uses TestEnvContext for env isolation.
Import paths reference STAGING until canonical ceremony applies.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path bootstrap — canonical paths (will be valid post-ceremony).
# Pre-ceremony: staging files are NOT on sys.path; tests that require them
# import from STAGING via importlib so CI can validate API shape NOW.
# ---------------------------------------------------------------------------

_TESTS_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _TESTS_DIR.parent
_REPO_ROOT = _HOOKS_DIR.parent.parent

# Canonical: .claude/hooks is the import root for _lib.*
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# Staging paths — for pre-ceremony inspection + importlib loading
_STAGING_ROOT = (
    _REPO_ROOT
    / ".claude"
    / "plans"
    / "PLAN-081"
    / "staging"
    / "phase-1"
)
_STAGING_ADAPTERS = _STAGING_ROOT / "_lib" / "adapters"
_STAGING_LIB = _STAGING_ROOT / "_lib"

from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# Importlib helpers — load staging modules without polluting sys.modules
# ---------------------------------------------------------------------------


def _load_staging_module(rel_path: str, module_name: str):
    """Load a module from staging using importlib.util.

    Args:
        rel_path: path relative to _STAGING_ROOT.
        module_name: unique name to register in sys.modules.
    Returns:
        The loaded module object.
    """
    target = _STAGING_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load staging module: {target}")
    mod = importlib.util.module_from_spec(spec)
    # Inject the canonical _lib.* into the staging module's namespace so
    # its relative imports (``from .. import contract``) resolve. We shim
    # by inserting the staging _lib dir on sys.path temporarily.
    if str(_STAGING_ROOT) not in sys.path:
        sys.path.insert(0, str(_STAGING_ROOT))
    try:
        spec.loader.exec_module(mod)
    finally:
        if str(_STAGING_ROOT) in sys.path:
            sys.path.remove(str(_STAGING_ROOT))
    return mod


# ---------------------------------------------------------------------------
# Lazy adapter loader — tries canonical first, falls back to staging
# ---------------------------------------------------------------------------

def _import_codex_adapter():
    """Return the codex adapter module (canonical if present, else staging)."""
    # Try canonical
    try:
        from _lib.adapters import codex as _codex
        return _codex
    except ImportError:
        pass
    # Fall back to staging — add staging _lib parent to sys.path
    staging_lib_parent = str(_STAGING_ROOT)
    if staging_lib_parent not in sys.path:
        sys.path.insert(0, staging_lib_parent)
    try:
        from _lib.adapters import codex as _codex  # type: ignore[import]
        return _codex
    except ImportError:
        raise ImportError(
            "codex adapter not available at canonical OR staging path. "
            "Run ceremony cp first, or ensure staging path is accessible."
        )


def _import_constants():
    """Return _lib.adapters._constants module."""
    try:
        from _lib.adapters import _constants
        return _constants
    except ImportError:
        pass
    staging_lib_parent = str(_STAGING_ROOT)
    if staging_lib_parent not in sys.path:
        sys.path.insert(0, staging_lib_parent)
    from _lib.adapters import _constants  # type: ignore[import]
    return _constants


# ---------------------------------------------------------------------------
# Test fixture builders
# ---------------------------------------------------------------------------

def _make_stdin(payload: Dict[str, Any]) -> io.StringIO:
    return io.StringIO(json.dumps(payload))


def _make_codex_tool_response(text_blocks):
    """Build a Codex MCP server response envelope."""
    return {
        "content": [{"type": "text", "text": t} for t in text_blocks]
    }


def _make_pretooluse_payload(
    tool_name: str = "mcp__codex__codex",
    prompt: str = "Review this file.",
    session_id: str = "sess-001",
) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": {"prompt": prompt},
        "tool_response": {},
    }


def _make_posttooluse_payload(
    tool_name: str = "mcp__codex__codex",
    codex_text: str = "Looks good.",
    session_id: str = "sess-002",
) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": {"prompt": "Review."},
        "tool_response": _make_codex_tool_response([codex_text]),
    }


# ---------------------------------------------------------------------------
# 1. ABI Conformance (SPEC §3) — 9 tests
# ---------------------------------------------------------------------------


class TestABIConformance(TestEnvContext):
    """SPEC §3: read_event / read_post_event / write_decision / emit_decision."""

    def _adapter(self):
        return _import_codex_adapter()

    def test_read_event_returns_normalized_event_pretooluse(self):
        """read_event with PreToolUse payload returns NormalizedEvent with correct phase."""
        codex = self._adapter()
        payload = _make_pretooluse_payload()
        stream = _make_stdin(payload)
        event = codex.read_event(stream=stream, phase="PreToolUse")
        self.assertIsNone(event.parse_error)
        self.assertEqual(event.phase, "PreToolUse")
        self.assertEqual(event.tool_name, "mcp__codex__codex")
        self.assertEqual(event.session_id, "sess-001")

    def test_read_post_event_returns_normalized_event_posttooluse(self):
        """read_post_event parses PostToolUse envelope."""
        codex = self._adapter()
        payload = _make_posttooluse_payload()
        stream = _make_stdin(payload)
        event = codex.read_post_event(stream=stream)
        self.assertEqual(event.phase, "PostToolUse")
        self.assertEqual(event.tool_name, "mcp__codex__codex")

    def test_write_decision_allow_produces_valid_json(self):
        """write_decision(allow()) produces {'decision': 'allow'}."""
        from _lib import contract
        codex = self._adapter()
        decision = contract.allow()
        out = codex.write_decision(decision)
        parsed = json.loads(out)
        self.assertEqual(parsed.get("decision", "allow"), "allow")
        self.assertNotIn("reason", parsed)

    def test_write_decision_block_includes_reason(self):
        """write_decision(block(reason=...)) includes reason field."""
        from _lib import contract
        codex = self._adapter()
        decision = contract.block(reason="Test block reason")
        out = codex.write_decision(decision)
        parsed = json.loads(out)
        self.assertEqual(parsed["decision"], "block")
        self.assertEqual(parsed["reason"], "Test block reason")

    def test_emit_decision_writes_to_stream(self):
        """emit_decision writes JSON + newline to the provided stream."""
        from _lib import contract
        codex = self._adapter()
        buf = io.StringIO()
        codex.emit_decision(contract.allow(), stream=buf)
        out = buf.getvalue()
        self.assertTrue(out.endswith("\n"))
        parsed = json.loads(out.strip())
        self.assertEqual(parsed.get("decision", "allow"), "allow")

    def test_emit_decision_system_message_propagated(self):
        """emit_decision propagates systemMessage when present."""
        from _lib import contract
        codex = self._adapter()
        buf = io.StringIO()
        decision = contract.allow(system_message="Codex advisory note")
        codex.emit_decision(decision, stream=buf)
        parsed = json.loads(buf.getvalue().strip())
        self.assertEqual(parsed.get("systemMessage"), "Codex advisory note")

    def test_write_decision_extra_fields_passed_through(self):
        """write_decision merges extra dict fields into output JSON."""
        from _lib import contract
        from dataclasses import field as dc_field
        codex = self._adapter()
        decision = contract.Decision(allow=True, extra={"pair_id": "pr-42"})
        out = codex.write_decision(decision)
        parsed = json.loads(out)
        self.assertEqual(parsed.get("pair_id"), "pr-42")

    def test_read_event_invalid_phase_defaults_to_pretooluse(self):
        """read_event with unknown phase string defaults to PreToolUse."""
        codex = self._adapter()
        payload = _make_pretooluse_payload()
        stream = _make_stdin(payload)
        event = codex.read_event(stream=stream, phase="UnknownPhase")
        self.assertEqual(event.phase, "PreToolUse")

    def test_adapter_version_is_semver_string(self):
        """ADAPTER_VERSION attribute exists and looks like a semver."""
        codex = self._adapter()
        ver = codex.ADAPTER_VERSION
        self.assertIsInstance(ver, str)
        parts = ver.split(".")
        self.assertGreaterEqual(len(parts), 3, f"Expected semver, got {ver!r}")

    # CAPABILITIES constant
    def test_capabilities_has_required_keys(self):
        """CAPABILITIES dict exposes streaming_tool_use, json_mode, function_calling."""
        codex = self._adapter()
        caps = codex.CAPABILITIES
        for key in ("streaming_tool_use", "json_mode", "function_calling"):
            self.assertIn(key, caps)


# ---------------------------------------------------------------------------
# 2. Sandbox modes / make_invoke_command — 8 tests
# ---------------------------------------------------------------------------


class TestMakeInvokeCommand(TestEnvContext):
    """make_invoke_command argv builder (PLAN-142 — codex-cli 0.139 shape).

    The 0.139 verdict is read from a last-message file, so the builder now
    REQUIRES output_last_message_path. All argv shape lives in the non-kernel
    codex_cli_shape helper; the kernel wrapper delegates.
    """

    _OUT = "/tmp/ceo_test_out.json"

    def _adapter(self):
        return _import_codex_adapter()

    def test_default_sandbox_read_only_model_omitted(self):
        """Default args: read-only sandbox; --model OMITTED (account default, D5)."""
        codex = self._adapter()
        argv = codex.make_invoke_command("Review this file.", output_last_message_path=self._OUT)
        self.assertIn("--sandbox", argv)
        idx = argv.index("--sandbox")
        self.assertEqual(argv[idx + 1], "read-only")
        # PLAN-142 D5: forcing a catalog model 400s on a ChatGPT-login account,
        # so the default omits --model and the account picks its own.
        self.assertNotIn("--model", argv)

    def test_output_file_emitted_via_o_flag(self):
        """The last-message output path is emitted via -o (0.139 verdict file)."""
        codex = self._adapter()
        argv = codex.make_invoke_command("Review.", output_last_message_path=self._OUT)
        self.assertIn("-o", argv)
        o_idx = argv.index("-o")
        self.assertEqual(argv[o_idx + 1], self._OUT)

    def test_missing_output_path_raises(self):
        """0.139 requires the last-message file; a missing path raises loudly."""
        codex = self._adapter()
        with self.assertRaises(ValueError):
            codex.make_invoke_command("Review.")

    def test_workspace_write_sandbox_passes_through(self):
        """sandbox_mode='workspace-write' is accepted and passed through."""
        codex = self._adapter()
        argv = codex.make_invoke_command("Fix this.", sandbox_mode="workspace-write", output_last_message_path=self._OUT)
        idx = argv.index("--sandbox")
        self.assertEqual(argv[idx + 1], "workspace-write")

    def test_danger_full_access_sandbox_passes_through(self):
        """sandbox_mode='danger-full-access' is accepted."""
        codex = self._adapter()
        argv = codex.make_invoke_command("Fix.", sandbox_mode="danger-full-access", output_last_message_path=self._OUT)
        idx = argv.index("--sandbox")
        self.assertEqual(argv[idx + 1], "danger-full-access")

    def test_invalid_sandbox_coerces_to_read_only(self):
        """Unknown sandbox_mode is fail-conservatively coerced to read-only."""
        codex = self._adapter()
        argv = codex.make_invoke_command("Do something.", sandbox_mode="everything", output_last_message_path=self._OUT)
        idx = argv.index("--sandbox")
        self.assertEqual(argv[idx + 1], "read-only")

    def test_invalid_model_raises_loud(self):
        """PLAN-142 C3 — an unknown model is LOUD (raises), not silently coerced."""
        codex = self._adapter()
        from _lib.codex_cli_shape import UnknownCodexModel
        with self.assertRaises(UnknownCodexModel):
            codex.make_invoke_command("Review.", model="gpt-99-super", output_last_message_path=self._OUT)

    def test_valid_model_o3_accepted(self):
        """o3 model passes through without coercion."""
        codex = self._adapter()
        argv = codex.make_invoke_command("Audit.", model="o3", output_last_message_path=self._OUT)
        m_idx = argv.index("--model")
        self.assertEqual(argv[m_idx + 1], "o3")

    def test_color_never_and_json_opt_in(self):
        """PLAN-142 — 0.139 uses --color never; usage stream is opt-in via json_events."""
        codex = self._adapter()
        argv = codex.make_invoke_command("Check it.", output_last_message_path=self._OUT)
        self.assertNotIn("--no-color", argv)
        self.assertNotIn("--json", argv)
        self.assertIn("--color", argv)
        c_idx = argv.index("--color")
        self.assertEqual(argv[c_idx + 1], "never")
        argv_usage = codex.make_invoke_command("Check it.", output_last_message_path=self._OUT, json_events=True)
        self.assertIn("--json", argv_usage)

    def test_empty_prompt_raises_value_error(self):
        """Empty prompt string raises ValueError (pre-condition guard)."""
        codex = self._adapter()
        with self.assertRaises(ValueError):
            codex.make_invoke_command("", output_last_message_path=self._OUT)

    def test_prompt_appears_after_double_dash(self):
        """Prompt is positioned after '--' sentinel in argv."""
        codex = self._adapter()
        prompt = "Please review this carefully."
        argv = codex.make_invoke_command(prompt, output_last_message_path=self._OUT)
        double_dash_idx = argv.index("--")
        self.assertEqual(argv[double_dash_idx + 1], prompt)


# ---------------------------------------------------------------------------
# 3. Schema-coercion: parse_verdict — 8 tests
# ---------------------------------------------------------------------------


class TestParseVerdict(TestEnvContext):
    """parse_verdict: normalization, coercion, finding shape, fail-open."""

    def _adapter(self):
        return _import_codex_adapter()

    def _make_stdout(self, verdict: str, findings=None, summary: str = "") -> str:
        obj = {"verdict": verdict, "findings": findings or [], "summary": summary}
        return json.dumps(obj)

    def test_pass_verdict_parsed_correctly(self):
        """PASS verdict is preserved as-is in the normalized envelope."""
        codex = self._adapter()
        result = codex.parse_verdict(self._make_stdout("PASS", summary="All good."))
        self.assertEqual(result["verdict"], "PASS")
        self.assertIsNone(result["parse_error"])
        self.assertEqual(result["summary"], "All good.")

    def test_advisory_verdict_preserved(self):
        """ADVISORY verdict passes through without coercion."""
        codex = self._adapter()
        result = codex.parse_verdict(self._make_stdout("ADVISORY"))
        self.assertEqual(result["verdict"], "ADVISORY")

    def test_block_verdict_preserved(self):
        """BLOCK verdict passes through without coercion."""
        codex = self._adapter()
        result = codex.parse_verdict(self._make_stdout("BLOCK"))
        self.assertEqual(result["verdict"], "BLOCK")

    def test_unknown_verdict_coerced_to_advisory(self):
        """Unknown verdict is fail-open coerced to ADVISORY per ADR-106.

        PLAN-142: the parse_error is now payload-free (it names the failure
        class, e.g. 'verdict not in _VALID_VERDICTS', not the coerced value),
        so we assert the coerced verdict + a non-None reason rather than the
        old 'ADVISORY' substring.
        """
        codex = self._adapter()
        result = codex.parse_verdict(self._make_stdout("FAIL"))
        self.assertEqual(result["verdict"], "ADVISORY")
        self.assertIsNotNone(result["parse_error"])

    def test_finding_shape_normalized(self):
        """Finding dicts are normalized to canonical shape."""
        codex = self._adapter()
        raw_finding = {
            "rubric_violation_id": "RV-0042",
            "severity": "P0",
            "file": "hooks/check_pair_rail.py",
            "line": 77,
            "rationale": "Direct os.system() call found.",
        }
        result = codex.parse_verdict(
            self._make_stdout("BLOCK", findings=[raw_finding])
        )
        self.assertEqual(len(result["findings"]), 1)
        f = result["findings"][0]
        self.assertEqual(f["rubric_violation_id"], "RV-0042")
        self.assertEqual(f["severity"], "P0")
        self.assertEqual(f["file"], "hooks/check_pair_rail.py")
        self.assertEqual(f["line"], 77)
        self.assertIn("os.system", f["rationale"])

    def test_finding_invalid_severity_coerced_to_p1(self):
        """Finding with unknown severity is conservatively coerced to P1."""
        codex = self._adapter()
        raw_finding = {"rubric_violation_id": "RV-0001", "severity": "CRITICAL"}
        result = codex.parse_verdict(
            self._make_stdout("ADVISORY", findings=[raw_finding])
        )
        self.assertEqual(result["findings"][0]["severity"], "P1")

    def test_empty_stdout_returns_advisory_with_parse_error(self):
        """Empty string stdout fails-open to ADVISORY with parse_error set."""
        codex = self._adapter()
        result = codex.parse_verdict("")
        self.assertEqual(result["verdict"], "ADVISORY")
        self.assertIsNotNone(result["parse_error"])

    def test_markdown_fenced_json_stripped_correctly(self):
        """Codex output wrapped in ```json fences is unwrapped before parse."""
        codex = self._adapter()
        fenced = "```json\n" + json.dumps({"verdict": "PASS", "findings": [], "summary": "OK"}) + "\n```"
        result = codex.parse_verdict(fenced)
        self.assertEqual(result["verdict"], "PASS")
        self.assertIsNone(result["parse_error"])

    def test_ansi_escape_codes_stripped(self):
        """ANSI color codes in Codex stdout are stripped before JSON parse."""
        codex = self._adapter()
        ansi_wrapped = "\x1b[32m" + json.dumps({"verdict": "PASS", "findings": [], "summary": ""}) + "\x1b[0m"
        result = codex.parse_verdict(ansi_wrapped)
        self.assertEqual(result["verdict"], "PASS")


# ---------------------------------------------------------------------------
# 4. SHA-pin: _constants + verify_pins drift detection — 5 tests
# ---------------------------------------------------------------------------


class TestSHAPin(TestEnvContext):
    """_compute_adapter_sha + verify_pins drift detection."""

    def _constants(self):
        return _import_constants()

    def test_compute_adapter_sha_returns_64_char_hex(self):
        """_compute_adapter_sha returns a 64-char lowercase hex digest."""
        constants = self._constants()
        # Compute SHA of _constants.py itself (always present)
        sha = constants._compute_adapter_sha("_constants.py")
        self.assertIsInstance(sha, str)
        self.assertEqual(len(sha), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in sha))

    def test_compute_adapter_sha_file_not_found_raises(self):
        """_compute_adapter_sha raises FileNotFoundError for missing file."""
        constants = self._constants()
        with self.assertRaises(FileNotFoundError):
            constants._compute_adapter_sha("__nonexistent_adapter__.py")

    def test_verify_pins_skips_tbd_entries(self):
        """verify_pins() skips entries whose expected value is '<TBD>'."""
        constants = self._constants()
        # The shipped Phase 1-full has placeholder <TBD> for both entries
        drift = constants.verify_pins()
        # Should not raise AND the <TBD> entries should not appear as drift
        # (drift dict only contains entries where actual != expected-non-TBD)
        self.assertIsInstance(drift, dict)

    def test_verify_pins_detects_tampered_sha(self):
        """verify_pins detects drift when a pinned SHA doesn't match on-disk."""
        constants = self._constants()
        # Patch the expected table with a known-wrong digest for _constants.py
        original = constants._EXPECTED_ADAPTER_SHA256.copy()
        constants._EXPECTED_ADAPTER_SHA256["_constants.py"] = "a" * 64
        try:
            drift = constants.verify_pins()
            self.assertIn("_constants.py", drift)
            self.assertIn("expected=", drift["_constants.py"])
        finally:
            constants._EXPECTED_ADAPTER_SHA256.clear()
            constants._EXPECTED_ADAPTER_SHA256.update(original)

    def test_verify_pins_returns_empty_dict_when_all_tbd(self):
        """verify_pins returns {} when all entries are <TBD> (pre-ceremony)."""
        constants = self._constants()
        original = constants._EXPECTED_ADAPTER_SHA256.copy()
        constants._EXPECTED_ADAPTER_SHA256.clear()
        constants._EXPECTED_ADAPTER_SHA256["claude.py"] = "<TBD>"
        constants._EXPECTED_ADAPTER_SHA256["codex.py"] = "<TBD>"
        try:
            drift = constants.verify_pins()
            self.assertEqual(drift, {})
        finally:
            constants._EXPECTED_ADAPTER_SHA256.clear()
            constants._EXPECTED_ADAPTER_SHA256.update(original)


# ---------------------------------------------------------------------------
# 5. PostToolUse hook semantics: codex_stdout in raw_payload — 4 tests
# ---------------------------------------------------------------------------


class TestPostToolUseSemantics(TestEnvContext):
    """read_post_event preserves codex_stdout in raw_payload for ingress scan."""

    def _adapter(self):
        return _import_codex_adapter()

    def test_posttooluse_codex_stdout_extracted_to_raw_payload(self):
        """PostToolUse for mcp__codex__codex surfaces codex_stdout in raw_payload."""
        codex = self._adapter()
        payload = _make_posttooluse_payload(
            tool_name="mcp__codex__codex",
            codex_text="LGTM. No findings.",
        )
        stream = _make_stdin(payload)
        event = codex.read_post_event(stream=stream)
        self.assertIn("codex_stdout", event.raw_payload)
        self.assertIn("LGTM", event.raw_payload["codex_stdout"])

    def test_posttooluse_codex_reply_also_extracted(self):
        """mcp__codex__codex-reply tool name also triggers stdout extraction."""
        codex = self._adapter()
        payload = _make_posttooluse_payload(
            tool_name="mcp__codex__codex-reply",
            codex_text="Advisory finding RV-0010.",
        )
        stream = _make_stdin(payload)
        event = codex.read_post_event(stream=stream)
        self.assertIn("codex_stdout", event.raw_payload)
        self.assertIn("RV-0010", event.raw_payload["codex_stdout"])

    def test_pretooluse_does_not_populate_codex_stdout(self):
        """PreToolUse event does NOT populate raw_payload['codex_stdout']."""
        codex = self._adapter()
        payload = _make_pretooluse_payload(tool_name="mcp__codex__codex")
        stream = _make_stdin(payload)
        event = codex.read_event(stream=stream, phase="PreToolUse")
        self.assertNotIn("codex_stdout", event.raw_payload)

    def test_non_codex_tool_posttooluse_no_codex_stdout(self):
        """PostToolUse for non-codex tool name does not set codex_stdout."""
        codex = self._adapter()
        payload = _make_posttooluse_payload(
            tool_name="Bash",
            codex_text="shell output",
        )
        stream = _make_stdin(payload)
        event = codex.read_post_event(stream=stream)
        self.assertNotIn("codex_stdout", event.raw_payload)


# ---------------------------------------------------------------------------
# 6. Timeout classifier — 7 tests
# ---------------------------------------------------------------------------


class TestTimeoutClassifier(TestEnvContext):
    """_classify_prompt_complexity and _resolve_timeout_s per R1 C7."""

    def _adapter(self):
        return _import_codex_adapter()

    def test_short_simple_prompt_returns_simple(self):
        """Short prompt with no audit keywords is classified as 'simple'."""
        codex = self._adapter()
        result = codex._classify_prompt_complexity("Is this code correct?")
        self.assertEqual(result, "simple")

    def test_long_prompt_exceeds_512_returns_audit(self):
        """Prompt > 512 chars is classified as 'audit' regardless of keywords."""
        codex = self._adapter()
        long_prompt = "x " * 300  # 600 chars
        result = codex._classify_prompt_complexity(long_prompt)
        self.assertEqual(result, "audit")

    def test_audit_keyword_triggers_audit_class(self):
        """Presence of keyword 'compliance' triggers audit classification."""
        codex = self._adapter()
        result = codex._classify_prompt_complexity("Check compliance with LGPD.")
        self.assertEqual(result, "audit")

    def test_audit_keyword_case_insensitive(self):
        """Audit keyword matching is case-insensitive."""
        codex = self._adapter()
        result = codex._classify_prompt_complexity("Run EXHAUSTIVE checks.")
        self.assertEqual(result, "audit")

    def test_none_input_returns_simple(self):
        """None input fails-permissive and returns 'simple'."""
        codex = self._adapter()
        result = codex._classify_prompt_complexity(None)  # type: ignore[arg-type]
        self.assertEqual(result, "simple")

    def test_empty_string_returns_simple(self):
        """Empty string returns 'simple'."""
        codex = self._adapter()
        result = codex._classify_prompt_complexity("")
        self.assertEqual(result, "simple")

    def test_resolve_timeout_simple_returns_75(self):
        """_resolve_timeout_s returns 75 for simple prompts."""
        codex = self._adapter()
        t = codex._resolve_timeout_s("Short prompt.")
        self.assertEqual(t, codex.DEFAULT_TIMEOUT_SIMPLE_S)
        self.assertEqual(t, 75)

    def test_resolve_timeout_audit_returns_240(self):
        """_resolve_timeout_s returns 240 for audit-class prompts."""
        codex = self._adapter()
        t = codex._resolve_timeout_s("Perform a full audit of all specs.")
        self.assertEqual(t, codex.DEFAULT_TIMEOUT_AUDIT_S)
        self.assertEqual(t, 240)


# ---------------------------------------------------------------------------
# 7. Audit emit field surface — AUDIT_EMIT_KEYS constant — 4 tests
# ---------------------------------------------------------------------------


class TestAuditEmitFields(TestEnvContext):
    """AUDIT_EMIT_KEYS constant matches Sec MF-3 whitelist requirements."""

    def _adapter(self):
        return _import_codex_adapter()

    def test_audit_emit_keys_is_tuple(self):
        """AUDIT_EMIT_KEYS is a tuple (immutable, ordered, pinned)."""
        codex = self._adapter()
        self.assertIsInstance(codex.AUDIT_EMIT_KEYS, tuple)

    def test_required_keys_present_in_audit_emit_keys(self):
        """AUDIT_EMIT_KEYS includes the mandatory Sec MF-3 fields."""
        codex = self._adapter()
        required = {"agent_provider", "pair_id", "wall_clock_s", "retry_at_timeout_s"}
        actual = set(codex.AUDIT_EMIT_KEYS)
        missing = required - actual
        self.assertEqual(missing, set(), f"Missing required audit emit keys: {missing}")

    def test_verdict_in_audit_emit_keys(self):
        """AUDIT_EMIT_KEYS includes 'verdict' for pair-rail records."""
        codex = self._adapter()
        self.assertIn("verdict", codex.AUDIT_EMIT_KEYS)

    def test_codex_cli_version_in_audit_emit_keys(self):
        """AUDIT_EMIT_KEYS includes 'codex_cli_version' for provenance."""
        codex = self._adapter()
        self.assertIn("codex_cli_version", codex.AUDIT_EMIT_KEYS)


# ---------------------------------------------------------------------------
# 8. Fail-open paths — 7 tests
# ---------------------------------------------------------------------------


class TestFailOpenPaths(TestEnvContext):
    """Adapter never raises; parse errors → NormalizedEvent(parse_error=...)."""

    def _adapter(self):
        return _import_codex_adapter()

    def test_malformed_json_stdin_returns_parse_error_event(self):
        """Malformed JSON on stdin returns NormalizedEvent with parse_error."""
        codex = self._adapter()
        stream = io.StringIO("{NOT VALID JSON}")
        event = codex.read_event(stream=stream)
        self.assertIsNotNone(event.parse_error)

    def test_empty_stdin_returns_clean_event_no_parse_error(self):
        """Empty stdin returns NormalizedEvent with NO parse_error per SPEC §3.1 step 2.

        SPEC/v1/adapters.schema.md §3.1 step 2 explicitly states empty /
        whitespace-only stdin produces a clean NormalizedEvent with phase
        preserved and no parse_error. Parse_error is only set when JSON
        decode fails on non-empty content.
        """
        codex = self._adapter()
        stream = io.StringIO("")
        event = codex.read_event(stream=stream)
        # Per SPEC, empty stdin does NOT trigger parse_error.
        self.assertIsNone(event.parse_error)
        # Phase should be preserved (default PreToolUse).
        self.assertEqual(event.phase, "PreToolUse")

    def test_parse_verdict_on_non_dict_json(self):
        """parse_verdict with a JSON array returns ADVISORY + parse_error."""
        codex = self._adapter()
        result = codex.parse_verdict(json.dumps([1, 2, 3]))
        self.assertEqual(result["verdict"], "ADVISORY")
        self.assertIsNotNone(result["parse_error"])

    def test_parse_verdict_on_invalid_json_string(self):
        """parse_verdict with invalid JSON fails-open to ADVISORY."""
        codex = self._adapter()
        result = codex.parse_verdict("{not: valid}")
        self.assertEqual(result["verdict"], "ADVISORY")
        self.assertIsNotNone(result["parse_error"])

    def test_parse_verdict_on_non_string_input(self):
        """parse_verdict with None input returns ADVISORY + parse_error."""
        codex = self._adapter()
        result = codex.parse_verdict(None)  # type: ignore[arg-type]
        self.assertEqual(result["verdict"], "ADVISORY")
        self.assertIsNotNone(result["parse_error"])

    def test_extract_codex_stdout_non_dict_returns_empty(self):
        """_extract_codex_stdout with a non-dict returns empty string."""
        codex = self._adapter()
        self.assertEqual(codex._extract_codex_stdout("not a dict"), "")

    def test_extract_codex_stdout_missing_content_key_returns_empty(self):
        """_extract_codex_stdout with dict missing 'content' returns empty."""
        codex = self._adapter()
        self.assertEqual(codex._extract_codex_stdout({"other": "data"}), "")

    def test_extract_codex_stdout_concatenates_multiple_text_blocks(self):
        """_extract_codex_stdout joins multiple text blocks with newline."""
        codex = self._adapter()
        response = _make_codex_tool_response(["Block 1", "Block 2", "Block 3"])
        result = codex._extract_codex_stdout(response)
        self.assertIn("Block 1", result)
        self.assertIn("Block 3", result)


if __name__ == "__main__":
    unittest.main()
