# PLAN-142 STAGING DRAFT — apply to .claude/hooks/_lib/codex_cli_shape.py under the GPG ceremony; NOT YET TESTED.
"""Single source of truth for codex-cli 0.139.0 CLI-shape (PLAN-142 D2).

This NEW non-kernel module owns ALL Codex CLI-shape so that the kernel
files (`check_pair_rail.py`, `_lib/adapters/codex.py`) keep ZERO CLI
literals — no flag names, no model-id list, no subcommand strings. The
kernel files DELEGATE every argv build to `build_exec_argv` here. This is
the structural fix for the recurring GPG tax: after this module ships,
the NEXT codex-cli bump is a NON-kernel edit (PLAN-142 §3 grep gate, D2).

=== Verified 0.139.0 CLI surface (hands-on, S245) ===
REJECTED on 0.139 (exit 2 / "unexpected argument" — NEVER emit these):
  - ``--read-only``     (sandbox is now ``-s/--sandbox <mode>``)
  - ``--no-color``      (color is now ``--color <never|always|auto>``)
  - ``--strict-json``   (removed; use ``--output-schema`` to enforce shape)
  - ``--resume <id>``   (now an ``exec resume`` SUBCOMMAND, not a flag)

VALID on 0.139 (the only flags this module emits):
  - ``exec``                         the subcommand
  - ``-s/--sandbox <read-only|workspace-write|danger-full-access>``
  - ``--color <never|always|auto>``  (we always pass ``never``)
  - ``-o/--output-last-message <FILE>``  writes ONLY the final agent
        message to <FILE> (verified: a one-line JSON object)
  - ``--output-schema <FILE>``       JSON Schema the CLI ENFORCES at
        generation time (makes the structured-verdict shape CLI-enforced,
        not prompt-dependent — PLAN-142 §3 [P1], R-SEC-2 CLI-enforced)
  - ``--json``                       JSONL event stream on stdout (usage
        telemetry consumer ONLY — the live verdict rail does NOT use this)

Verified compose: ``codex exec -o <f> --color never --sandbox read-only \
  -- "<prompt>"`` writes ONLY the final agent message to <f>. ``-o`` and
``--json`` COMPOSE (the promotion path adds ``--json`` for usage).

=== argv ordering / two modes (PLAN-142 §4 D1) ===
mode='verdict' (LIVE rail — check_pair_rail.py):
    [exec, --color, never, --sandbox, <mode>, -o, <output_file>,
     (--output-schema <schema_file>)?, --, <prompt>]
    NO ``--json``: the live rail has no token-usage consumer; usage
    telemetry is consciously DROPPED on the rail (R-SEC-5).

mode='verdict+usage' (PROMOTION path — codex_invoke.py / run-promotion-gate.py):
    same as 'verdict' PLUS ``--json`` so the promotion path can read
    per-line usage events from the JSONL stdout (R-VP-A, R-OPS-3).

This module is stdlib-only and NEVER shells out — it returns argv lists
ONLY. The binary name (``codex``) is prepended by the CALLER (the rail
resolves it via ``_resolve_codex_bin``; codex_invoke prepends ``"codex"``).

# TARGET PATH (apply via Owner-signed sentinel ceremony):
#   .claude/hooks/_lib/codex_cli_shape.py  (NON-kernel — not in _KERNEL_PATHS)
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Module identity / version
# ---------------------------------------------------------------------------

#: SemVer for the CLI-shape contract. Bump whenever the emitted flag
#: surface changes (e.g. the NEXT codex-cli bump edits THIS module —
#: that is the whole point of D2).
CLI_SHAPE_VERSION: str = "0.1.0-draft"

#: The codex-cli version this shape targets. Kept in sync with
#: ``.claude/governance/codex-cli-pin.txt`` (informational; the pin file
#: is the enforced supply-chain gate, not this constant).
CODEX_CLI_TARGET_VERSION: str = "0.139.0"


# ---------------------------------------------------------------------------
# Model-id catalog (MOVED here from _lib/adapters/codex.py — PLAN-142 §3 D2)
# ---------------------------------------------------------------------------
#
# This list is the SINGLE validation surface for Codex reviewer model ids.
# After the ceremony, `_lib/adapters/codex.py` must import `_VALID_MODELS`
# and `DEFAULT_MODEL` from here (no local copy) so the grep gate finds no
# `gpt-5*`/`o3*`/`o4*`/`_VALID_MODELS` literal in the kernel files.
#
# OPEN ITEM for execution (PLAN-142 D5 / OQ1): the historical wrapper
# default `gpt-5.5` is NOT in this catalog and was being SILENTLY coerced
# to `gpt-5-codex` at codex.py:643. This draft does NOT add `gpt-5.5` —
# the execution session MUST reconcile the live 0.139 model catalog and
# pick the real default (gpt-5-codex vs gpt-5.5), then update this list +
# DEFAULT_MODEL. Coercion is now LOUD (see `coerce_model`), never silent.

#: Allowed Codex reviewer model ids. Carried over verbatim from the
#: pre-migration `_lib/adapters/codex.py:_VALID_MODELS` (S120 demotion
#: kept `gpt-5-codex`). DRAFT — confirm against the live 0.139 catalog.
_VALID_MODELS: Tuple[str, ...] = (
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-codex",
    "o3",
    "o3-mini",
    "o4-mini",
)

#: Default reviewer model when the caller passes None / "".
#: DRAFT — confirm against the live 0.139 catalog at execution (D5).
DEFAULT_MODEL: str = "gpt-5-codex"


# ---------------------------------------------------------------------------
# Sandbox modes (MOVED here from _lib/adapters/codex.py:_VALID_SANDBOX_MODES)
# ---------------------------------------------------------------------------

#: Allowed sandbox modes per codex-cli 0.139 ``-s/--sandbox`` enum.
_VALID_SANDBOX_MODES: Tuple[str, ...] = (
    "read-only",
    "workspace-write",
    "danger-full-access",
)

#: Conservative default sandbox for a read-only reviewer rail.
DEFAULT_SANDBOX_MODE: str = "read-only"


# ---------------------------------------------------------------------------
# Invocation modes (PLAN-142 §4 D1 — the only two shapes we emit)
# ---------------------------------------------------------------------------

#: Live verdict rail: ``-o`` only, NO ``--json`` (no usage consumer).
MODE_VERDICT: str = "verdict"

#: Promotion path: ``-o`` PLUS ``--json`` (usage via JSONL stdout).
MODE_VERDICT_USAGE: str = "verdict+usage"

_VALID_MODES: Tuple[str, ...] = (MODE_VERDICT, MODE_VERDICT_USAGE)


# ---------------------------------------------------------------------------
# Verdict JSON Schema for ``--output-schema`` (PLAN-142 §3 [P1], R-SEC-2)
# ---------------------------------------------------------------------------
#
# Passing this schema via ``--output-schema <FILE>`` makes the CLI ENFORCE
# the structured-verdict shape at generation time, so the trust model is
# CLI-enforced rather than prompt-dependent. The caller writes this object
# to a tmpfile (json.dump) and passes that path as `schema_file`.
#
# The shape mirrors `_lib/adapters/codex.py:parse_verdict_strict` exactly
# so the parser and the generator agree:
#   { "verdict": PASS|ADVISORY|BLOCK,
#     "findings": [ {rubric_violation_id, severity, file, line, rationale} ],
#     "summary": "" }
#
# `additionalProperties` is permissive on `usage`/`model` (promotion path
# may attach them) but the REQUIRED keys pin the verdict contract.

#: The canonical verdict-object JSON Schema (Draft-07 compatible subset).
VERDICT_OUTPUT_SCHEMA: Dict[str, object] = {
    "type": "object",
    "additionalProperties": True,
    "required": ["verdict", "findings", "summary"],
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["PASS", "ADVISORY", "BLOCK"],
        },
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "required": ["rubric_violation_id", "severity", "rationale"],
                "properties": {
                    "rubric_violation_id": {"type": "string"},
                    "severity": {"type": "string", "enum": ["P0", "P1"]},
                    "file": {"type": "string"},
                    "line": {"type": "integer", "minimum": 0},
                    "rationale": {"type": "string"},
                },
            },
        },
    },
}


def verdict_output_schema_json() -> str:
    """Serialize ``VERDICT_OUTPUT_SCHEMA`` to a stable JSON string.

    Helper for the caller that writes the schema to the
    ``--output-schema`` tmpfile. Sorted keys → deterministic bytes (so a
    fixture / inputs-hash over the schema file is stable). NEVER raises on
    the constant above (it is pure-JSON-serializable by construction).
    """
    return json.dumps(VERDICT_OUTPUT_SCHEMA, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Model / sandbox coercion — LOUD on unknown (PLAN-142 C3 / D5)
# ---------------------------------------------------------------------------


class UnknownCodexModel(ValueError):
    """Raised when a caller requests a model id not in ``_VALID_MODELS``.

    PLAN-142 C3 / D5: the pre-migration code SILENTLY coerced an unknown
    model (e.g. the wrapper default ``gpt-5.5``) to ``gpt-5-codex`` at
    ``make_invoke_command:643``, masking a real misconfiguration. The
    migration makes this LOUD: ``build_exec_argv`` raises this so the argv
    NEVER carries a model the caller did not intend.

    Carries the requested id and the valid set for the breadcrumb. The
    requested id is a model NAME (e.g. "gpt-5.5"), not secret-laden — safe
    to surface in the message.
    """

    def __init__(self, requested: str, valid: Tuple[str, ...]) -> None:
        self.requested = requested
        self.valid = valid
        super().__init__(
            "[codex-cli-shape] unknown model "
            + repr(requested)
            + "; valid="
            + repr(list(valid))
            + " (PLAN-142 C3: coercion is LOUD, not silent)"
        )


def coerce_model(model: Optional[str]) -> str:
    """Resolve a caller-supplied model id to a valid 0.139 model.

    Contract (PLAN-142 C3 — LOUD, never silent):
      - None / "" → ``DEFAULT_MODEL`` (an explicit, audited default).
      - a value IN ``_VALID_MODELS`` → returned unchanged.
      - a value NOT in ``_VALID_MODELS`` → raises ``UnknownCodexModel``.

    Callers that prefer fail-open-to-default (the rail wrapper, if it
    decides an unknown model should degrade rather than abort) MUST catch
    ``UnknownCodexModel`` and emit an audit breadcrumb themselves — this
    module refuses to make that policy decision silently. The default-on-
    empty branch is the ONLY implicit substitution and it is intentional.

    NEVER coerces a present-but-unknown id to the default — that was the
    exact S120 footgun this migration removes.
    """
    if model is None or model == "":
        return DEFAULT_MODEL
    if model in _VALID_MODELS:
        return model
    raise UnknownCodexModel(model, _VALID_MODELS)


def coerce_sandbox_mode(sandbox_mode: Optional[str]) -> str:
    """Resolve a caller-supplied sandbox mode to a valid 0.139 mode.

    Unlike ``coerce_model``, an unknown sandbox mode is coerced to the
    conservative ``DEFAULT_SANDBOX_MODE`` (``read-only``) rather than
    raised: a tighter-than-requested sandbox is fail-safe (the reviewer
    can only ever READ less), so silent tightening here does not create
    the masked-misconfiguration risk that the model case does. None / ""
    also map to the conservative default.
    """
    if sandbox_mode in _VALID_SANDBOX_MODES:
        return sandbox_mode  # type: ignore[return-value]  # narrowed by membership
    return DEFAULT_SANDBOX_MODE


# ---------------------------------------------------------------------------
# THE single argv builder (PLAN-142 §4 D2)
# ---------------------------------------------------------------------------


def build_exec_argv(
    prompt: str,
    *,
    mode: str,
    model: Optional[str],
    sandbox_mode: str,
    output_file: str,
    schema_file: Optional[str] = None,
) -> List[str]:
    """Build the codex-cli 0.139 ``exec`` argv (WITHOUT the binary name).

    This is THE single argv builder for the whole framework (PLAN-142 D2).
    `make_invoke_command`, `codex_invoke.py`, and `check_pair_rail.py` all
    DELEGATE here so no CLI literal survives in the kernel files.

    Args:
        prompt: the (already-redacted) prompt text. Empty → ValueError
            (an empty prompt is a caller bug, not a runtime condition).
        mode: ``MODE_VERDICT`` (live rail — ``-o`` only) or
            ``MODE_VERDICT_USAGE`` (promotion path — ``-o`` PLUS ``--json``).
            Unknown mode → ValueError.
        model: reviewer model id; resolved via ``coerce_model`` (None/""
            → ``DEFAULT_MODEL``; present-but-unknown → ``UnknownCodexModel``).
        sandbox_mode: one of ``_VALID_SANDBOX_MODES``; resolved via
            ``coerce_sandbox_mode`` (unknown → conservative ``read-only``).
        output_file: absolute path for ``-o/--output-last-message``. The
            CLI writes ONLY the final agent message here (a JSON object).
            The CALLER owns this tmpfile's secure lifecycle (mkdtemp 0o700,
            O_CREAT|O_EXCL|0o600, symlink/owner refusal, finally-unlink —
            PLAN-142 §3 R-SEC-4). Empty → ValueError.
        schema_file: optional absolute path to a JSON Schema file for
            ``--output-schema``. When provided, the CLI ENFORCES the
            verdict shape at generation time (PLAN-142 §3 [P1], R-SEC-2).
            The caller writes ``verdict_output_schema_json()`` there.

    Returns:
        argv list (WITHOUT the binary). The caller prepends the resolved
        ``codex`` binary path before ``subprocess.run``.

    Argv ordering (verified composable on 0.139):
        exec --color never --sandbox <mode> -o <output_file>
             [--output-schema <schema_file>] [--json] -- <prompt>

    NEVER emits ``--no-color`` / ``--read-only`` / ``--strict-json`` /
    ``--resume`` (all REJECTED or relocated on 0.139). The ``--`` sentinel
    guards a prompt that begins with ``-``.

    Raises:
        ValueError: empty prompt, empty output_file, or unknown mode.
        UnknownCodexModel: present-but-unknown model id (LOUD, C3).
    """
    if not isinstance(prompt, str) or not prompt:
        raise ValueError("[codex-cli-shape] build_exec_argv: prompt must be non-empty str")
    if not isinstance(output_file, str) or not output_file:
        raise ValueError("[codex-cli-shape] build_exec_argv: output_file must be non-empty str")
    if mode not in _VALID_MODES:
        raise ValueError(
            "[codex-cli-shape] build_exec_argv: unknown mode "
            + repr(mode)
            + "; valid="
            + repr(list(_VALID_MODES))
        )

    resolved_model = coerce_model(model)  # LOUD on unknown (C3)
    resolved_sandbox = coerce_sandbox_mode(sandbox_mode)

    argv: List[str] = [
        "exec",
        "--color", "never",
        "--sandbox", resolved_sandbox,
        "-o", output_file,
    ]

    # The model flag. 0.139 keeps ``--model <id>`` on ``exec``; the
    # migration carries the INTENDED model into argv (no silent default
    # substitution — coerce_model already guaranteed validity above).
    argv.extend(["--model", resolved_model])

    # CLI-enforced verdict shape (P1). Optional — absence falls back to the
    # prompt-requested shape + parser-side parse_verdict_strict.
    if schema_file:
        if not isinstance(schema_file, str):
            raise ValueError("[codex-cli-shape] build_exec_argv: schema_file must be str or None")
        argv.extend(["--output-schema", schema_file])

    # ``--json`` ONLY on the promotion path: the live verdict rail has no
    # token-usage consumer and consciously DROPS usage telemetry (R-SEC-5).
    if mode == MODE_VERDICT_USAGE:
        argv.append("--json")

    # ``--`` then the prompt as the final positional (guards a leading ``-``).
    argv.extend(["--", prompt])
    return argv


# ---------------------------------------------------------------------------
# Convenience wrappers mirroring the two call sites (optional sugar)
# ---------------------------------------------------------------------------


def build_verdict_argv(
    prompt: str,
    *,
    model: Optional[str] = None,
    sandbox_mode: str = DEFAULT_SANDBOX_MODE,
    output_file: str,
    schema_file: Optional[str] = None,
) -> List[str]:
    """LIVE-rail shape: ``MODE_VERDICT`` (``-o`` only, NO ``--json``).

    Thin sugar so ``check_pair_rail.py`` reads
    ``build_verdict_argv(prompt, output_file=f, schema_file=s)`` with no
    mode literal at the call site. Delegates to ``build_exec_argv``.
    """
    return build_exec_argv(
        prompt,
        mode=MODE_VERDICT,
        model=model,
        sandbox_mode=sandbox_mode,
        output_file=output_file,
        schema_file=schema_file,
    )


def build_verdict_usage_argv(
    prompt: str,
    *,
    model: Optional[str] = None,
    sandbox_mode: str = DEFAULT_SANDBOX_MODE,
    output_file: str,
    schema_file: Optional[str] = None,
) -> List[str]:
    """PROMOTION-path shape: ``MODE_VERDICT_USAGE`` (``-o`` PLUS ``--json``).

    Thin sugar so ``codex_invoke.py`` / ``run-promotion-gate.py`` read
    ``build_verdict_usage_argv(prompt, output_file=f)`` with no mode
    literal. Delegates to ``build_exec_argv``.
    """
    return build_exec_argv(
        prompt,
        mode=MODE_VERDICT_USAGE,
        model=model,
        sandbox_mode=sandbox_mode,
        output_file=output_file,
        schema_file=schema_file,
    )


__all__ = [
    "CLI_SHAPE_VERSION",
    "CODEX_CLI_TARGET_VERSION",
    "_VALID_MODELS",
    "DEFAULT_MODEL",
    "_VALID_SANDBOX_MODES",
    "DEFAULT_SANDBOX_MODE",
    "MODE_VERDICT",
    "MODE_VERDICT_USAGE",
    "VERDICT_OUTPUT_SCHEMA",
    "verdict_output_schema_json",
    "UnknownCodexModel",
    "coerce_model",
    "coerce_sandbox_mode",
    "build_exec_argv",
    "build_verdict_argv",
    "build_verdict_usage_argv",
]
