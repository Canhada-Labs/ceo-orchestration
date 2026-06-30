#!/usr/bin/env python3
"""benchmark-judge.py — LLM-as-judge CLI for skill benchmarks.

PLAN-011 Phase 3. Implements the §H5 + §H6 + §H7 consensus bundle:

- Committed `judge-prompt.md` with pinned SHA-256 (golden-prompt test).
- **Two-pass grading** (position-bias control): forward pass (task →
  rubric → response) and reverse pass (task → response → rubric). Both
  scores are reported; `|forward-reverse|>0.5` flags the candidate for
  human review.
- **Default-deny payload** per `SPEC/v1/judge-payload.schema.md`. The
  judge sees ONLY: rubric, redacted response, minimal task context.
  Extra fields raise.
- **Cross-provider guard**: the judge adapter MUST differ from the main
  adapter (`CEO_HOOK_ADAPTER`). Same-adapter invocations exit 3.
- **Stdlib-only**. Real LLM calls are mocked in tests; production
  usage pairs with `--judge-adapter=<gemini|openai>` and the
  adapter-specific backend invocation is wrapped behind the mock-safe
  `invoke_adapter()` hook.

## Usage

    python3 benchmark-judge.py \\
        --benchmark owasp-basics \\
        --response-file response.txt \\
        --rubric-file rubric.json \\
        --task-context "review this code for SQL injection" \\
        --judge-adapter=gemini

    # Testing / CI
    python3 benchmark-judge.py ... --mock-judge

Output is a single JSON object:

    {
      "benchmark": "owasp-basics",
      "judge_adapter": "gemini",
      "golden_prompt_hash": "297e...",
      "forward": {"score": 0-10, "refused": false, "flags": [], "reasoning": "..."},
      "reverse": {"score": 0-10, "refused": false, "flags": [], "reasoning": "..."},
      "delta": 1.2,
      "recommend_human_review": false
    }

## Exit codes

    0  — grades produced successfully
    2  — input / config error (missing files, bad JSON, invalid rubric)
    3  — same-adapter collision (judge == main)
    4  — judge unreachable / mock flag missing in offline mode
    5  — payload default-deny violation (dev-time only)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if _HOOKS_DIR.exists() and str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.redact import redact_secrets  # type: ignore
except ImportError:  # pragma: no cover — exercised only when _lib unreachable
    def redact_secrets(text, max_chars: int = 0) -> str:
        if text is None:
            return ""
        if max_chars and len(text) > max_chars:
            return text[:max_chars]
        return text


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default-deny: exactly these three keys (and no others) reach the judge.
JUDGE_PAYLOAD_ALLOWED_KEYS = frozenset({"task_context", "rubric", "response"})

# Two-pass delta threshold for flagging human review (H5 consensus).
DEFAULT_REVIEW_DELTA = 0.5

# Known judge adapters (must NOT include the main-process adapter value).
KNOWN_JUDGE_ADAPTERS = ("gemini", "openai", "local")

# Path to the committed judge prompt. Hash is pinned in ADR-030 and
# asserted in tests via `prompt_sha256()`.
DEFAULT_PROMPT_PATH = (
    _REPO_ROOT / ".claude" / "benchmarks" / "_schemas" / "judge-prompt.md"
)

# Truncation cap for the redacted response before it reaches the judge
# (defence-in-depth; prevents an adversarial response from ballooning the
# judge prompt and smuggling hidden context).
RESPONSE_MAX_CHARS = 8000
TASK_CONTEXT_MAX_CHARS = 4000


# ---------------------------------------------------------------------------
# Structured Outputs (opt-in; PLAN-136 SO1)
# ---------------------------------------------------------------------------
#
# When env CEO_STRUCTURED_OUTPUTS=1, the real judge call passes the grade
# json_schema (strict) to the adapter's call(response_format=...) pass-through,
# replacing prompt-instructed-JSON. DEFAULT (env unset) leaves response_format
# unset → the current path (mock judge / injected invoker / prompt-instructed)
# is preserved byte-for-byte.
#
# Default-OFF rationale: the judge is the epistemic core of skill grading.
# Flipping the structured-output path on by default mutates that core, so it
# must be validated (two-pass delta + grade parity on the benchmark suite)
# BEFORE the default flips to ON. Opt-in lets us measure first.

_STRUCTURED_OUTPUTS_ENV = "CEO_STRUCTURED_OUTPUTS"

# Grade shape per SPEC/v1/judge-payload.schema.md output contract — the object
# mock_judge_call() returns and the real judge is expected to emit. Strict
# mode: object, additionalProperties:false, no numeric range constraints
# (those are validated downstream); enum-free flags array.
_GRADE_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "score": {"type": "integer"},
        "reasoning": {"type": "string"},
        "refused": {"type": "boolean"},
        "flags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "reasoning", "refused", "flags"],
}


def structured_outputs_enabled() -> bool:
    """True iff opt-in env CEO_STRUCTURED_OUTPUTS=1 (default UNSET → False)."""
    return os.environ.get(_STRUCTURED_OUTPUTS_ENV) == "1"


def build_grade_response_format() -> Optional[Dict[str, Any]]:
    """Return the response_format payload for the judge adapter, or None.

    Returns None when CEO_STRUCTURED_OUTPUTS is unset (the default) — the
    judge call then omits response_format and the current prompt-instructed
    grading path is preserved byte-for-byte.

    When CEO_STRUCTURED_OUTPUTS=1, returns the json_schema (strict) payload the
    adapter's call(response_format=...) pass-through forwards to the API body.
    """
    if not structured_outputs_enabled():
        return None
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "grade",
            "strict": True,
            "schema": _GRADE_JSON_SCHEMA,
        },
    }


# ---------------------------------------------------------------------------
# Golden prompt hash helper
# ---------------------------------------------------------------------------


def prompt_sha256(path: Optional[Path] = None) -> str:
    """Return the SHA-256 hex digest of the committed judge prompt."""
    target = Path(path) if path else DEFAULT_PROMPT_PATH
    data = target.read_bytes()
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Payload validation (SPEC/v1/judge-payload.schema.md — default-deny)
# ---------------------------------------------------------------------------


def validate_payload(payload: Dict[str, Any]) -> None:
    """Raise ValueError if payload contains keys outside the allowlist.

    Per H6: the judge sees ONLY task_context + rubric + response. Any
    unexpected top-level key is a programming error (or a smuggled
    field from downstream refactors) and MUST be rejected before the
    payload reaches the adapter.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    extras = set(payload.keys()) - JUDGE_PAYLOAD_ALLOWED_KEYS
    if extras:
        raise ValueError(
            "judge-payload default-deny violation; extra keys: "
            + ", ".join(sorted(extras))
        )
    missing = JUDGE_PAYLOAD_ALLOWED_KEYS - set(payload.keys())
    if missing:
        raise ValueError(
            "judge-payload missing required keys: " + ", ".join(sorted(missing))
        )
    # Type checks
    if not isinstance(payload["task_context"], str):
        raise ValueError("task_context must be a string")
    if not isinstance(payload["response"], str):
        raise ValueError("response must be a string")
    if not isinstance(payload["rubric"], dict):
        raise ValueError("rubric must be a JSON object")


def build_payload(
    task_context: str,
    rubric: Dict[str, Any],
    response: str,
    *,
    reverse: bool = False,
) -> Dict[str, Any]:
    """Construct the default-deny payload for either the forward or reverse pass.

    Two-pass control means the same three fields reach the judge in
    both passes — the "reverse" aspect is realised by the adapter
    template order, not by smuggling a new field. Position bias is
    controlled at the prompt-render level (see `render_prompt`).
    """
    # Apply redaction + length caps here (not at adapter time) so the
    # default-deny validator sees the exact bytes the judge will see.
    redacted_response = redact_secrets(response, max_chars=0) or ""
    if len(redacted_response) > RESPONSE_MAX_CHARS:
        redacted_response = redacted_response[:RESPONSE_MAX_CHARS] + "...[truncated]"

    redacted_ctx = redact_secrets(task_context, max_chars=0) or ""
    if len(redacted_ctx) > TASK_CONTEXT_MAX_CHARS:
        redacted_ctx = redacted_ctx[:TASK_CONTEXT_MAX_CHARS] + "...[truncated]"

    # The reverse-pass bit is carried by a marker in the task context
    # (NOT a new top-level key). Adapters inspect the marker when
    # rendering the prompt. This preserves the three-key invariant.
    if reverse:
        redacted_ctx = "[REVERSE-PASS] " + redacted_ctx

    payload = {
        "task_context": redacted_ctx,
        "rubric": rubric,
        "response": redacted_response,
    }
    validate_payload(payload)
    return payload


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


def render_prompt(
    template_text: str,
    payload: Dict[str, Any],
    *,
    reverse: bool = False,
) -> str:
    """Substitute the three placeholders into the committed template.

    The template is the committed `judge-prompt.md`. Placeholders are
    literal tokens (`<TASK_CONTEXT_REDACTED>`, `<RUBRIC_YAML>`,
    `<RESPONSE_REDACTED>`). Reverse-pass reorders response vs rubric
    in the rendered text so position bias is observable.
    """
    validate_payload(payload)
    rubric_json = json.dumps(payload["rubric"], indent=2, ensure_ascii=False)

    if reverse:
        # Swap order: response appears BEFORE rubric in the rendered
        # prompt so the judge's attention pattern differs from forward.
        text = template_text
        # Two-step template rewrite: swap the two sections.
        text = text.replace("<RESPONSE_REDACTED>", "__RSP__")
        text = text.replace("<RUBRIC_YAML>", "__RUB__")
        # Swap header order at the section boundary. The committed
        # prompt always has "## Rubric" before "## Candidate response".
        rubric_block = "## Rubric (authoritative)\n\n__RUB__"
        response_block = "## Candidate response (redacted)\n\n__RSP__"
        if rubric_block in text and response_block in text:
            text = text.replace(rubric_block, "___TMP_RUBRIC___")
            text = text.replace(response_block, rubric_block)
            text = text.replace("___TMP_RUBRIC___", response_block)
        text = text.replace("__RSP__", payload["response"])
        text = text.replace("__RUB__", rubric_json)
        text = text.replace("<TASK_CONTEXT_REDACTED>", payload["task_context"])
        return text

    # Forward: direct substitution
    return (
        template_text
        .replace("<TASK_CONTEXT_REDACTED>", payload["task_context"])
        .replace("<RUBRIC_YAML>", rubric_json)
        .replace("<RESPONSE_REDACTED>", payload["response"])
    )


# ---------------------------------------------------------------------------
# Mock judge (deterministic; used for tests + offline runs)
# ---------------------------------------------------------------------------


def mock_judge_call(prompt: str, *, reverse: bool = False) -> Dict[str, Any]:
    """Deterministic judge that scores based on hashed prompt.

    Returns the structured JSON grade the real judge would emit.
    """
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    # Map the first byte into 0..10, reversed pass shifts by 1 (bounded)
    # so the two-pass delta is non-zero in mock mode (exercises tests).
    base = int(digest[:2], 16) % 11  # 0..10
    if reverse:
        base = max(0, min(10, base + (1 if base < 10 else -1)))
    refused = digest.startswith("00")  # ~1/256 chance
    return {
        "score": 0 if refused else base,
        "reasoning": "mock judge deterministic grade",
        "refused": refused,
        "flags": [],
    }


# ---------------------------------------------------------------------------
# Adapter invocation (real path — lazy import, pluggable)
# ---------------------------------------------------------------------------


def invoke_adapter(
    adapter_name: str,
    prompt: str,
    *,
    mock: bool,
    reverse: bool = False,
    response_format: Optional[Dict[str, Any]] = None,
    _inject_invoker=None,
) -> Dict[str, Any]:
    """Invoke the judge via the named adapter. Returns structured grade JSON.

    In mock mode (tests, `--mock-judge`, or when the runtime cannot
    reach the judge provider) returns a deterministic grade. The
    `_inject_invoker` hook is used by tests to simulate specific
    provider-side behaviors (refusal, malformed JSON, timeout).

    `response_format` (PLAN-136 SO1) is the opt-in structured-output payload
    built by `build_grade_response_format()`. It is None by default (env
    CEO_STRUCTURED_OUTPUTS unset) — the mock path ignores it, and the injected
    invoker receives it so the real adapter's call(response_format=...) can
    forward it to the API body. The mock judge is deterministic regardless.
    """
    if mock:
        return mock_judge_call(prompt, reverse=reverse)

    if _inject_invoker is not None:
        # Default-OFF: when response_format is None (env unset), call the
        # injector exactly as before — no extra kwarg — so the legacy path is
        # byte-identical and existing injectors keep their original signature.
        if response_format is None:
            return _inject_invoker(adapter_name, prompt, reverse=reverse)
        return _inject_invoker(
            adapter_name,
            prompt,
            reverse=reverse,
            response_format=response_format,
        )

    # Real-path: we only ship stubs in PLAN-011 Phase 3. Attempting a
    # real judge call without `--mock-judge` and without an injected
    # invoker returns an explicit reachability error so the runner can
    # fall back to the deterministic fallback scorer per H7.
    raise JudgeUnreachable(
        f"No real invoker wired for adapter={adapter_name!r}; "
        "pass --mock-judge or install a provider SDK."
    )


class JudgeUnreachable(RuntimeError):
    """Raised when the judge adapter cannot be invoked.

    Per H7, the caller SHOULD catch this and fall back to the
    deterministic scorer rather than failing the whole run.
    """


# ---------------------------------------------------------------------------
# Two-pass grading
# ---------------------------------------------------------------------------


def two_pass_grade(
    task_context: str,
    rubric: Dict[str, Any],
    response: str,
    *,
    adapter_name: str,
    template_text: str,
    mock: bool,
    review_delta: float = DEFAULT_REVIEW_DELTA,
    _inject_invoker=None,
) -> Dict[str, Any]:
    """Run forward + reverse passes, compute delta, recommend review if large."""
    # Opt-in structured-output payload (None by default; PLAN-136 SO1).
    response_format = build_grade_response_format()

    # Forward
    fwd_payload = build_payload(task_context, rubric, response, reverse=False)
    fwd_prompt = render_prompt(template_text, fwd_payload, reverse=False)
    forward = invoke_adapter(
        adapter_name,
        fwd_prompt,
        mock=mock,
        reverse=False,
        response_format=response_format,
        _inject_invoker=_inject_invoker,
    )

    # Reverse
    rev_payload = build_payload(task_context, rubric, response, reverse=True)
    rev_prompt = render_prompt(template_text, rev_payload, reverse=True)
    reverse = invoke_adapter(
        adapter_name,
        rev_prompt,
        mock=mock,
        reverse=True,
        response_format=response_format,
        _inject_invoker=_inject_invoker,
    )

    delta = abs(float(forward.get("score", 0)) - float(reverse.get("score", 0)))
    recommend = delta > review_delta

    return {
        "forward": forward,
        "reverse": reverse,
        "delta": round(delta, 3),
        "recommend_human_review": bool(recommend),
    }


# ---------------------------------------------------------------------------
# Cross-provider guard
# ---------------------------------------------------------------------------


def assert_cross_provider(judge_adapter: str, main_adapter_env: Optional[str]) -> None:
    """Raise CrossProviderCollision if judge == main.

    Per H5: judge-model ≠ judged-model is a methodological principle.
    Same-adapter invocation is a developer error; CLI exits 3.
    """
    main = (main_adapter_env or "").strip().lower()
    if not main:
        # No main adapter declared — allow (user is likely running
        # judge stand-alone / exploratory).
        return
    if judge_adapter.strip().lower() == main:
        raise CrossProviderCollision(
            f"judge adapter ({judge_adapter}) must differ from main "
            f"adapter ({main}); set CEO_HOOK_ADAPTER to a different "
            "provider or pick a different --judge-adapter."
        )


class CrossProviderCollision(ValueError):
    """Raised when judge adapter equals main adapter."""


# ---------------------------------------------------------------------------
# Rubric loading
# ---------------------------------------------------------------------------


def load_rubric(path: Path) -> Dict[str, Any]:
    """Load a rubric JSON file. Raises ValueError on structural errors.

    Accepts the JSON twin (`judge-rubric-example.json` shape). Callers
    that want to ship YAML keep a JSON mirror under `_schemas/`.
    """
    if not path.is_file():
        raise ValueError(f"rubric file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"rubric JSON parse error: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("rubric top-level must be an object")
    for required in ("version", "rubric_id", "items", "scoring"):
        if required not in data:
            raise ValueError(f"rubric missing required field: {required}")
    if not isinstance(data["items"], list) or not data["items"]:
        raise ValueError("rubric.items must be a non-empty list")
    for item in data["items"]:
        if not isinstance(item, dict):
            raise ValueError("rubric item must be an object")
        for required in ("id", "description", "weight"):
            if required not in item:
                raise ValueError(f"rubric item missing field: {required}")
    if data["scoring"] not in ("weighted_average", "all_or_nothing"):
        raise ValueError(f"rubric.scoring unknown: {data['scoring']!r}")
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the benchmark-judge CLI."""
    p = argparse.ArgumentParser(
        prog="benchmark-judge.py",
        description="LLM-as-judge grader for skill benchmarks (PLAN-011 Phase 3)",
    )
    p.add_argument("--benchmark", required=True, help="Benchmark slug")
    p.add_argument("--response-file", required=True, help="Path to candidate response")
    p.add_argument("--rubric-file", required=True, help="Path to rubric JSON")
    p.add_argument("--task-context", default="", help="Short task description")
    p.add_argument(
        "--judge-adapter",
        required=True,
        choices=KNOWN_JUDGE_ADAPTERS,
        help="Adapter for the judge (must differ from CEO_HOOK_ADAPTER)",
    )
    p.add_argument(
        "--mock-judge",
        action="store_true",
        help="Use the deterministic mock judge (CI / offline)",
    )
    p.add_argument(
        "--prompt-file",
        default=str(DEFAULT_PROMPT_PATH),
        help="Override path to committed judge prompt (advanced)",
    )
    p.add_argument(
        "--review-delta",
        type=float,
        default=DEFAULT_REVIEW_DELTA,
        help="Forward-reverse delta threshold for human review flag",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — run the benchmark judge on a prior benchmark run."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # CEO_SOTA_DISABLE short-circuit (S4)
    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        print(
            json.dumps(
                {
                    "benchmark": args.benchmark,
                    "judge_adapter": args.judge_adapter,
                    "skipped": True,
                    "reason": "CEO_SOTA_DISABLE=1",
                }
            )
        )
        return 0

    # Cross-provider guard (H5 / cross-provider principle)
    try:
        assert_cross_provider(args.judge_adapter, os.environ.get("CEO_HOOK_ADAPTER"))
    except CrossProviderCollision as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3

    # Load files
    try:
        template_text = Path(args.prompt_file).read_text(encoding="utf-8")
    except OSError as e:
        print(f"ERROR: cannot read judge prompt at {args.prompt_file}: {e}", file=sys.stderr)
        return 2

    try:
        rubric = load_rubric(Path(args.rubric_file))
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    try:
        response = Path(args.response_file).read_text(encoding="utf-8")
    except OSError as e:
        print(f"ERROR: cannot read response file: {e}", file=sys.stderr)
        return 2

    # Grade
    try:
        grade = two_pass_grade(
            task_context=args.task_context,
            rubric=rubric,
            response=response,
            adapter_name=args.judge_adapter,
            template_text=template_text,
            mock=args.mock_judge,
            review_delta=args.review_delta,
        )
    except JudgeUnreachable as e:
        print(f"ERROR: judge unreachable: {e}", file=sys.stderr)
        return 4
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 5

    out = {
        "benchmark": args.benchmark,
        "judge_adapter": args.judge_adapter,
        "golden_prompt_hash": prompt_sha256(Path(args.prompt_file)),
        **grade,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
