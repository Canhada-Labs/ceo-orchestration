from __future__ import annotations
from ._shared import *

def _resolve_codex_cli_shape():  # type: ignore[no-untyped-def]
    """Resolve the NEW non-kernel `_lib.codex_cli_shape` module.

    Mirrors the canonical-layout resolution used elsewhere: the
    `.claude/hooks/` dir that houses this file also houses `_lib/`. Returns
    the module or None (fail-OPEN — the caller treats None as
    CodexUnavailable, the ADR-106 fail-open path). NEVER raises.
    """
    try:
        hooks_dir = Path(__file__).resolve().parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import codex_cli_shape as _shape  # type: ignore
        return _shape
    except Exception:
        return None

# QDSAA-FUNCAO-LONGA: ciclo do subprocesso, arquivo seguro e limpeza permanecem atômicos para não abrir TOCTOU no payload.
def _invoke_codex_review(
    tool_name: str,
    file_path: str,
    proposed_content: str,
    timeout_s: float,
) -> str:
    """Invoke Codex review on codex-cli 0.139.0; return the REDACTED
    last-message file content (one structured JSON object) as a str.

    PLAN-142: the verdict is obtained by having the CLI write ONLY the final
    agent message to a private output file (verified on 0.139: a one-line
    JSON object). ALL flag-shape lives in the NON-kernel
    ``_lib.codex_cli_shape`` helper (D2); this kernel function constructs NO
    argv literals.

    Signature contract UNCHANGED for the consumer: returns a single str.
    But it is now the isolated last agent message (one structured object),
    ALREADY single-pass redacted (R-SEC-1 — redaction at the lowest-trust
    file-read site, before any json.loads in the consumer).

    No env-fixture path (PLAN-163 FXα): the former
    `CEO_PAIR_RAIL_FIXTURE_RESPONSE` short-circuit was REMOVED from
    production. Pin verification via `_resolve_codex_bin()` is now
    UNCONDITIONAL — no env can preset a review or skip the ADR-182 sha
    gate. Tests inject a Codex review by mocking THIS function at the
    invoke boundary (`mock.patch.object(<mod>, "_invoke_codex_review",
    return_value=<review>)`); the sha gate is covered directly in
    `test_check_pair_rail_payload_pin.py`.

    tmpfile TOCTOU hygiene (R-SEC-4 / R-VP-E): a private `mkdtemp(0o700)`
    dir per call; the output file is pre-created O_CREAT|O_EXCL|0o600 at an
    absolute path; after the run we REFUSE to read if it is a symlink / not
    a regular file / not owned by us; `finally:` unlink (output + schema) +
    rmdir on EVERY exit path (success, read error, timeout, exception).

    Degradation matrix → CodexUnavailable / CodexTimeout / CodexMalformed
    (all map to ADVISORY in `_decide`), NEVER raise past the typed wall:
      helper/binary missing, spawn error, non-zero exit → CodexUnavailable;
      timeout → CodexTimeout; output file missing-after-exit-0 / symlink /
      non-regular / not-owned / empty / oversize → CodexMalformed.

    ADR-182 (PLAN-163 T5.2) verify-then-invoke: `_resolve_codex_bin()`
    now returns the VERIFIED native payload path (sha256 checked against
    the pin manifest) and the subprocess argv below execs EXACTLY that
    path — the artifact that was hashed is the artifact that runs.

    Raises:
        CodexUnavailable, CodexTimeout, CodexMalformed (all consumed as
        ADVISORY fail-open by `_decide`);
        CodexPinMismatch (ADR-182 fail-CLOSED — consumed as a BLOCK by
        `_decide`, never advisory).
    """
    import os as _os  # local alias to avoid any chance of shadowing
    import stat as _stat
    import tempfile as _tempfile

    # PLAN-163 FXα: the CEO_PAIR_RAIL_FIXTURE_RESPONSE short-circuit was
    # REMOVED from production entirely. Pin verification is now
    # UNCONDITIONAL — no env (test-mode or otherwise) injects a preset
    # review before _resolve_codex_bin(), so "no env relaxes the sha
    # verification" is literally true. Tests inject a Codex review by
    # mocking THIS function (_invoke_codex_review) at the invoke boundary,
    # never via env; the ADR-182 sha gate is exercised directly in
    # test_check_pair_rail_payload_pin.py.

    # ADR-182: may raise CodexPinMismatch (fail-CLOSED) — deliberately
    # NOT caught here; `_decide` maps it to `{decision: block}`.
    codex_bin = _resolve_codex_bin()
    if codex_bin is None:
        raise CodexUnavailable(
            "codex binary not on PATH (or ADR-182 pin verification "
            "hit an INFRA arm — see pair_rail_codex_unavailable audit)"
        )

    shape = _resolve_codex_cli_shape()
    if shape is None:
        # The single argv builder is gone/unimportable. Fail-OPEN to
        # ADVISORY rather than hand-roll a (possibly rejected) argv.
        raise CodexUnavailable("codex_cli_shape helper unavailable")

    prompt = _build_codex_prompt(tool_name, file_path, proposed_content)
    # PLAN-084 Wave 0.5 (ADR-114 + AC9 — Codex egress redaction symmetry).
    # proposed_content is raw FILE CONTENT being reviewed (potentially
    # secret-laden source). Redact the OUTGOING prompt BEFORE it leaves the
    # framework. This stays fail-CLOSED per ADR-114: a redactor-import
    # failure REFUSES to ship the prompt.
    try:
        from _lib import codex_egress_redact as _redact
        _egress_bytes = len(prompt.encode("utf-8", "replace")) if isinstance(prompt, str) else 0
        prompt, _egress_findings = _redact.redact_outgoing_with_findings(prompt)
    except ImportError:
        # Fail-CLOSED per ADR-114: refuse to ship unredacted prompt to Codex.
        raise CodexUnavailable("codex_egress_redact unavailable — fail-CLOSED per ADR-114")
    # PLAN-112-FOLLOWUP-codex-egress-proof-telemetry (F-7.9): positive-proof
    # emit on EVERY outbound redaction (empty allowed). Fail-OPEN — wraps ONLY
    # the emit; the redact above stays fail-CLOSED per ADR-114.
    try:
        from _lib import audit_emit as _ae
        _ae.emit_pair_rail_outgoing_redaction_applied(
            signal="outbound",
            match_count=len(_egress_findings),
            bytes_scanned=_egress_bytes,
            callsite="check_pair_rail.py:_invoke_codex_review",
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:
        pass

    # -----------------------------------------------------------------
    # tmpfile setup — we own the dir (0o700) and pre-create the output
    # file with O_EXCL|0o600 to win the symlink race; the CLI writes to it
    # by absolute path. A sibling schema file (written by US, not the
    # untrusted binary) carries the CLI-enforced verdict shape.
    # -----------------------------------------------------------------
    tmp_dir = _tempfile.mkdtemp(prefix="ceo_pairrail_")
    try:
        _os.chmod(tmp_dir, 0o700)
    except OSError:
        pass  # mkdtemp already creates 0o700 on POSIX
    out_path = _os.path.join(tmp_dir, "codex_last_message.json")
    schema_path = _os.path.join(tmp_dir, "codex_verdict_schema.json")

    def _cleanup() -> None:
        """Unlink both tmpfiles + rmdir the dir; never raises."""
        for _p in (out_path, schema_path):
            try:
                _os.unlink(_p)
            except OSError:
                pass
        try:
            _os.rmdir(tmp_dir)
        except OSError:
            pass

    try:
        # Pre-create O_CREAT|O_EXCL|0o600 — if a symlink/file already sits
        # at out_path, O_EXCL fails and we treat it as unavailable.
        try:
            fd = _os.open(out_path, _os.O_CREAT | _os.O_EXCL | _os.O_WRONLY, 0o600)
            _os.close(fd)
        except FileNotFoundError:
            raise CodexUnavailable("tmpdir vanished before pre-create")
        except FileExistsError:
            raise CodexUnavailable("tmpfile pre-create lost O_EXCL race")
        except OSError as e:
            raise CodexUnavailable(f"tmpfile pre-create failed: {type(e).__name__}")

        # Write the CLI-enforced verdict schema to our schema tmpfile
        # (PLAN-142 §3 [P1], R-SEC-2). Best-effort: if the helper cannot
        # serialize it, proceed WITHOUT enforcement (parser-side
        # parse_verdict_strict still validates the shape).
        schema_arg: Optional[str] = None
        try:
            schema_json = shape.verdict_output_schema_json()
            sfd = _os.open(schema_path, _os.O_CREAT | _os.O_EXCL | _os.O_WRONLY, 0o600)
            try:
                _os.write(sfd, schema_json.encode("utf-8"))
            finally:
                _os.close(sfd)
            schema_arg = schema_path
        except Exception:
            schema_arg = None

        # Build argv via the NON-kernel helper. The live-rail shape writes
        # the verdict to our output file and drops usage telemetry (R-SEC-5);
        # we pass only semantic intent — the helper owns flag names, the
        # model id, and the dead-flag migration.
        try:
            cli_args = shape.build_verdict_argv(
                prompt,
                output_file=out_path,
                schema_file=schema_arg,
            )
        except Exception as e:
            raise CodexUnavailable(
                f"codex_cli_shape.build_verdict_argv failed: {type(e).__name__}"
            )
        if not isinstance(cli_args, (list, tuple)) or not cli_args:
            raise CodexUnavailable("codex_cli_shape returned empty argv")

        # ADR-182 verify-then-invoke: `codex_bin` is the VERIFIED native
        # payload path returned by `_resolve_codex_bin()` (or the
        # test-only CEO_PAIR_RAIL_CODEX_BIN override). Invoking the
        # exact verified path — not `codex` re-resolved from $PATH —
        # closes the hash-launcher/execute-payload gap of the retired
        # codex-cli-binary-sha256.txt pin.
        cmd = [codex_bin] + list(cli_args)

        # Invoke. The prompt is the trailing positional built by the helper;
        # close stdin via input="" so the child never blocks on a pipe.
        try:
            proc = subprocess.run(
                cmd,
                input="",
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise CodexTimeout(f"codex invoke exceeded {timeout_s}s")
        except (FileNotFoundError, PermissionError, OSError, ConnectionError) as e:
            raise CodexUnavailable(f"codex invoke failed: {type(e).__name__}: {e}")
        except ValueError as e:
            # UnicodeDecodeError IS-A ValueError; map to malformed so
            # `_decide` degrades to ADVISORY (preserve concrete name).
            raise CodexMalformed(f"codex invoke {type(e).__name__}: {e}")

        # Post-subprocess audit breadcrumb (UNCHANGED behavior).
        try:
            from _lib import audit_emit as _ae  # type: ignore  # noqa: F811
            if hasattr(_ae, "emit_generic"):
                _ae.emit_generic("codex_invoke_dispatched", exit_code=int(proc.returncode))
        except Exception:
            pass

        if proc.returncode != 0:
            # Non-zero exit → unavailable (fail-OPEN). A present output file
            # after a non-zero exit is IGNORED (not read) and cleaned up.
            raise CodexUnavailable(
                f"codex returned exit={proc.returncode}; stderr_head="
                f"{(proc.stderr or '')[:240]!r}"
            )

        # -------------------------------------------------------------
        # Read back the output file with TOCTOU re-validation. Re-stat via
        # os.lstat (NOT following symlinks) and refuse anything that is not
        # a regular file we own.
        # -------------------------------------------------------------
        try:
            st = _os.lstat(out_path)
        except FileNotFoundError:
            raise CodexMalformed("codex last-message file missing after exit-0")
        except OSError as e:
            raise CodexMalformed(f"codex last-message lstat failed: {type(e).__name__}")

        if _stat.S_ISLNK(st.st_mode):
            raise CodexMalformed("codex last-message path is a symlink; refusing to read")
        if not _stat.S_ISREG(st.st_mode):
            raise CodexMalformed("codex last-message path is not a regular file; refusing")
        try:
            if st.st_uid != _os.getuid():
                raise CodexMalformed("codex last-message file not owned by us; refusing")
        except AttributeError:
            # os.getuid absent (non-POSIX) — the 0o700 mkdtemp + O_EXCL
            # pre-create are the primary controls; skip the uid check.
            pass
        if st.st_size == 0:
            raise CodexMalformed("codex last-message file is empty")
        if st.st_size > _MAX_OUTPUT_FILE_BYTES:
            raise CodexMalformed(
                f"codex last-message oversize ({st.st_size} > {_MAX_OUTPUT_FILE_BYTES})"
            )

        # Open refusing to follow a symlink swapped in post-lstat.
        try:
            open_flags = _os.O_RDONLY
            if hasattr(_os, "O_NOFOLLOW"):
                open_flags |= _os.O_NOFOLLOW
            rfd = _os.open(out_path, open_flags)
        except OSError as e:
            raise CodexMalformed(f"codex last-message open failed: {type(e).__name__}")
        try:
            raw_bytes = _os.read(rfd, _MAX_OUTPUT_FILE_BYTES + 1)
        finally:
            try:
                _os.close(rfd)
            except OSError:
                pass
        if len(raw_bytes) > _MAX_OUTPUT_FILE_BYTES:
            raise CodexMalformed("codex last-message grew past cap during read")

        content = raw_bytes.decode("utf-8", errors="replace")

        # -------------------------------------------------------------
        # SINGLE-PASS redact the FULL byte-string BEFORE returning (and
        # thus before any json.loads in the consumer). R-SEC-1. Ingress
        # redaction is fail-OPEN to ADVISORY (distinct from the ADR-114
        # fail-CLOSED *egress* contract above): if the redactor is
        # unavailable we refuse to hand un-redacted text to the parser and
        # degrade to ADVISORY via CodexMalformed.
        # -------------------------------------------------------------
        try:
            from _lib import codex_egress_redact as _redact  # noqa: F811
            redacted = _redact.redact(content)
        except Exception:
            raise CodexMalformed(
                "codex_egress_redact unavailable on ingress; refusing raw parse"
            )
        return redacted
    finally:
        _cleanup()

def _sentinel_grants_pair_rail_bypass(
    file_path: str, repo_root: Path
) -> bool:
    """True if any Architect sentinel covers `file_path` in its scope.

    Production: piggybacks on `check_canonical_edit._sentinel_grants_path`
    if that helper is importable. Otherwise returns False (no bypass).
    """
    try:
        # Best-effort import; staging file should not depend on
        # production import path. Fail soft.
        hooks_dir = repo_root / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        try:
            import check_canonical_edit as _cce  # type: ignore
        except Exception:
            return False
        try:
            rel = (
                Path(file_path).resolve().relative_to(repo_root.resolve())
            )
        except (ValueError, OSError):
            return False
        rel_str = str(rel).replace(os.sep, "/")
        sentinels = _cce._find_sentinels(repo_root)  # type: ignore[attr-defined]
        for sentinel in sentinels:
            try:
                if _cce._sentinel_grants_path(sentinel, rel_str):  # type: ignore[attr-defined]
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False

_AUDIT_REVIEW_PASSED = "pair_rail_review_passed"

_AUDIT_CODEX_VIOLATION = "pair_rail_codex_violation"

_AUDIT_CODEX_UNAVAILABLE = "pair_rail_codex_unavailable"

_AUDIT_SENTINEL_BYPASS = "pair_rail_sentinel_bypass"

_AUDIT_OUT_OF_SCOPE = "pair_rail_out_of_scope"

_AUDIT_KILL_SWITCH = "pair_rail_kill_switch_used"

_AUDIT_PIN_MISMATCH = "pair_rail_codex_pin_mismatch"

_AUDIT_FATAL_FAILOPEN = "pair_rail_fatal_failopen"

def _emit_audit(action: str, **fields: Any) -> None:
    """Best-effort audit. Production fallback: stderr breadcrumb when no audit sink configured.

    Phase 1 wires through `_lib/audit_emit.emit_generic` after
    register-ceremony lands the action labels in `_KNOWN_ACTIONS`.
    """
    # Test capture hook: env-controlled file sink for unit tests.
    sink = os.environ.get("CEO_PAIR_RAIL_AUDIT_SINK")
    if sink:
        try:
            event = {"action": action, **fields}
            with open(sink, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass  # advisory; never blocks
    # Stderr breadcrumb (spike — visible in test output).
    try:
        preview = ", ".join(
            f"{k}={v!r}" for k, v in list(fields.items())[:5]
        )
        sys.stderr.write(
            f"[check_pair_rail SPIKE] {action} {preview}\n"
        )
    except Exception:
        pass

def _emit_codex_review_invoked(review_text: str, grammar: "Optional[str]") -> None:
    """Emit codex_review_invoked for a completed Codex review (best-effort).

    ``grammar`` is the write-shaped-patch verdict from ``_detect_write_shaped_patch``
    (``None`` == clean/passed; non-``None`` == a flagged violation/failed). We feed
    the review through the WS-3 driver (the single redaction source) so the raw
    text is hashed, never echoed, then route the redacted PhaseReview fields
    through ``optimizer._skeleton.safe_emit`` (silent until the action registers).
    """
    try:
        repo_root = Path(__file__).resolve().parents[2]
        scripts_dir = str((repo_root / ".claude" / "scripts").resolve())
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from optimizer import codex_phase_gate as _pg  # type: ignore[import]
        from optimizer import _skeleton as _sk  # type: ignore[import]

        # Map the already-obtained review into a driver result. We INJECT a
        # closure returning that result so review_phase does the verdict
        # classification + redaction (status, violation-count normalisation,
        # thread/summary hashing) — we never re-implement that boundary here.
        # The kill-switch is intentionally bypassed: we only reach this site
        # AFTER a real invocation completed, so we drive review_phase with
        # CEO_CODEX_REVIEW unset semantics via a direct injected result.
        verdict = "block" if grammar is not None else "accept"
        injected = {
            "status": verdict,
            "summary": review_text if isinstance(review_text, str) else "",
        }
        review = _pg.review_phase(
            0, "", codex_invoke=lambda _p, _m: injected,
        )
        # review_disabled_signal is NOT forwarded — it routes the disabled
        # sibling instead; forwarding a bool would break canonical-json/HMAC.
        _sk.safe_emit(
            "codex_review_invoked",
            repo_root=repo_root,
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            phase_number=review.phase_number,
            review_status=review.review_status,
            summary_hash=review.summary_hash,
            thread_id_redacted=review.thread_id_redacted,
            codex_model=review.codex_model,
            duration_ms=review.duration_ms,
            violations_found_count=review.violations_found_count,
        )
    except Exception:
        # FAIL-CLOSED on the emit only — an audit-emit failure must NEVER block
        # or crash the Pair-Rail hook (ADR-005 never-blocks), and must NEVER
        # launder unredacted text (we simply emit nothing on any error).
        return

def _load_codex_adapter():  # type: ignore[no-untyped-def]
    """Resolve `_lib.adapters.codex` (the structured-verdict parser).

    Same canonical-layout resolution as the other `_lib` loaders. Returns
    the module or None (fail-OPEN — caller degrades to ADVISORY). NEVER
    raises.
    """
    try:
        hooks_dir = Path(__file__).resolve().parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib.adapters import codex as _codex  # type: ignore
        return _codex
    except Exception:
        return None

_VALID_VERDICTS_LOCAL: Tuple[str, ...] = ("PASS", "ADVISORY", "BLOCK")

def _consume_codex_review(redacted_review: str) -> Tuple[str, Optional[str]]:
    """Derive (verdict, secondary_patch_grammar) from a REDACTED review.

    PRIMARY signal (D3): `parse_verdict_strict` — the verdict is accepted
    ONLY from a structured, schema-validated object (verdict ∈
    `_VALID_VERDICTS_LOCAL`). A forged free-text 'PASS' with no structured
    object → ADVISORY (fail-CLOSED-to-ADVISORY per R-SEC-2 / ADR-106).

    SECONDARY signal (D3): `_detect_write_shaped_patch` runs on the SAME
    redacted text as defense-in-depth annotation ONLY — it never upgrades a
    verdict to a hard block; the structured verdict is authoritative.

    Returns (verdict, patch_grammar) where verdict ∈ {"PASS","ADVISORY",
    "BLOCK"} and patch_grammar is the `_detect_write_shaped_patch` tag (or
    None). NEVER raises.
    """
    # Secondary defense-in-depth scan (advisory annotation only).
    try:
        patch_grammar = _detect_write_shaped_patch(redacted_review)
    except Exception:
        patch_grammar = None

    codex = _load_codex_adapter()
    if codex is None:
        # Adapter unimportable — fail-CLOSED-to-ADVISORY (cannot validate a
        # structured verdict, so we do not trust one).
        return "ADVISORY", patch_grammar

    # parse_verdict_strict is fail-CLOSED-to-ADVISORY and never raises, but
    # wrap defensively anyway and coerce any surprise to ADVISORY. We do NOT
    # fall back to the free-text patch scan as the verdict — it stays SECONDARY.
    try:
        envelope = codex.parse_verdict_strict(redacted_review)
        verdict = envelope.get("verdict")
        if verdict not in _VALID_VERDICTS_LOCAL:
            return "ADVISORY", patch_grammar
        return str(verdict), patch_grammar
    except Exception:
        return "ADVISORY", patch_grammar

_CURRENT_REVIEW_ID: str = ""

__all__ = (
    '_resolve_codex_cli_shape',
    '_invoke_codex_review',
    '_sentinel_grants_pair_rail_bypass',
    '_AUDIT_REVIEW_PASSED',
    '_AUDIT_CODEX_VIOLATION',
    '_AUDIT_CODEX_UNAVAILABLE',
    '_AUDIT_SENTINEL_BYPASS',
    '_AUDIT_OUT_OF_SCOPE',
    '_AUDIT_KILL_SWITCH',
    '_AUDIT_PIN_MISMATCH',
    '_AUDIT_FATAL_FAILOPEN',
    '_emit_audit',
    '_emit_codex_review_invoked',
    '_load_codex_adapter',
    '_VALID_VERDICTS_LOCAL',
    '_consume_codex_review',
    '_CURRENT_REVIEW_ID',
)
