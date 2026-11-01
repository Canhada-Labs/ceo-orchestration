#!/usr/bin/env python3
"""PLAN-091 PRODUCTION pair-rail hook compatibility facade.

Implementation is split into private declarations while this module owns all
runtime globals. That preserves dynamic monkeypatch lookups by callers.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import cli_currency as _cli_currency  # noqa: F401
from _lib._pair_rail_parts import install as _install_parts

_install_parts(globals(), ('part_01', 'part_02', 'part_03', 'part_04'))

_PRODUCTION_PROMOTED_BY_PLAN_091: bool = True


def _invoke_codex_review(
    tool_name: str,
    file_path: str,
    proposed_content: str,
    timeout_s: float,
) -> str:
    """Invoke Codex review on codex-cli 0.139.0; return the REDACTED
    last-message file content (one structured JSON object) as a str.
    """
    import os as _os
    import stat as _stat
    import tempfile as _tempfile

    codex_bin = _resolve_codex_bin()
    if codex_bin is None:
        raise CodexUnavailable(
            "codex binary not on PATH (or ADR-182 pin verification "
            "hit an INFRA arm — see pair_rail_codex_unavailable audit)"
        )

    shape = _resolve_codex_cli_shape()
    if shape is None:
        raise CodexUnavailable("codex_cli_shape helper unavailable")

    prompt = _build_codex_prompt(tool_name, file_path, proposed_content)
    try:
        from _lib import codex_egress_redact as _redact
        _egress_bytes = len(prompt.encode("utf-8", "replace")) if isinstance(prompt, str) else 0
        prompt, _egress_findings = _redact.redact_outgoing_with_findings(prompt)
    except ImportError:
        raise CodexUnavailable("codex_egress_redact unavailable — fail-CLOSED per ADR-114")
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

    tmp_dir = _tempfile.mkdtemp(prefix="ceo_pairrail_")
    try:
        _os.chmod(tmp_dir, 0o700)
    except OSError:
        pass
    out_path = _os.path.join(tmp_dir, "codex_last_message.json")
    schema_path = _os.path.join(tmp_dir, "codex_verdict_schema.json")

    def _cleanup() -> None:
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
        try:
            fd = _os.open(out_path, _os.O_CREAT | _os.O_EXCL | _os.O_WRONLY, 0o600)
            _os.close(fd)
        except FileNotFoundError:
            raise CodexUnavailable("tmpdir vanished before pre-create")
        except FileExistsError:
            raise CodexUnavailable("tmpfile pre-create lost O_EXCL race")
        except OSError as e:
            raise CodexUnavailable(f"tmpfile pre-create failed: {type(e).__name__}")

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

        cmd = [codex_bin] + list(cli_args)

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
            raise CodexMalformed(f"codex invoke {type(e).__name__}: {e}")

        try:
            from _lib import audit_emit as _ae  # type: ignore  # noqa: F811
            if hasattr(_ae, "emit_generic"):
                _ae.emit_generic("codex_invoke_dispatched", exit_code=int(proc.returncode))
        except Exception:
            pass

        if proc.returncode != 0:
            raise CodexUnavailable(
                f"codex returned exit={proc.returncode}; stderr_head="
                f"{(proc.stderr or '')[:240]!r}"
            )

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
            pass
        if st.st_size == 0:
            raise CodexMalformed("codex last-message file is empty")
        if st.st_size > _MAX_OUTPUT_FILE_BYTES:
            raise CodexMalformed(
                f"codex last-message oversize ({st.st_size} > {_MAX_OUTPUT_FILE_BYTES})"
            )

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

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify-codex-pin":
        sys.exit(_verify_pin_cli(sys.argv[2:]))
    sys.exit(main())
