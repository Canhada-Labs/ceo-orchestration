#!/usr/bin/env python3
"""run-skill-benchmark.py — execute a skill benchmark YAML against the
Anthropic API and emit a Markdown + JSON report.

Sprint 2 Item C.2. Advisory mode by default (exits 0 unless `--strict`
is passed or the overall score falls below the CRITICAL floor).

## Contract

    python3 run-skill-benchmark.py <benchmark.yaml> [options]

Options:
    --output-json <path>    Write full JSON results to this path
    --markdown              Emit a Markdown table on stdout (default: on)
    --json                  Emit full JSON on stdout
    --concurrency N         Max concurrent API calls (default 3)
    --strict                Exit 1 if any scenario fails
    --allow-expensive       Bypass the $1.00 pre-flight budget cap
    --model <id>            Override model (default: claude-haiku-4-5-20251001)
    --skip-if-no-key        Exit 0 with SKIPPED if ANTHROPIC_API_KEY unset
    --max-tokens N          Max output tokens per call (default 2000)
    --seed N                Seed for deterministic scenario order (default 0)
    --repetitions N         Runs-per-scenario for the aggregation (default 3)

## Determinism + variance

Per PLAN-002 §15 debate finding #2: `temperature=0`, `top_p=1`, fixed
model ID (not `latest`), N runs per scenario. Raw per-run scores are
stored in `raw_scores:` so variance can be tracked historically.

### Aggregation (PLAN-133 C1 — worst-of-N + flaky)

The per-scenario score across the N repetitions is aggregated with the
**worst-of-N** rule by default (the conservative floor — a skill that
passes only sometimes is a latent regression). A `flaky` flag is set on
any scenario whose N runs disagree on pass/fail. The legacy median is
reachable via `CEO_BENCH_AGGREGATION=median` for historical comparison;
an unknown value fails open to "worst". The aggregated value is stored
under both `aggregated_score` and the stable `median_score` key.

## Safety

- Output of every API call is passed through `_lib.redact.redact_secrets()`
  before being written to disk (defends against a prompt-inject scenario
  that asks the model to echo its own credentials into the report).
- Per-scenario input content is capped at 4000 chars.
- Per-run output is capped at 2000 tokens.
- Pre-flight cost estimate refuses runs over $1.00 unless
  `--allow-expensive`.
- `paths:` filter in CI (Item C.3) ensures the job only runs on changes
  to `.claude/skills/**`.

## SDK dependency

Imports `anthropic` lazily inside `call_api()`. If the SDK is missing,
the runner prints a clear install message and exits 2 (unless
`--skip-if-no-key` is passed, which short-circuits earlier).

## Architecture

- `load_benchmark(path)` → dict
- `estimate_cost(bench)` → dollars
- `score_scenario(response, expected, scoring)` → dict with score + breakdown
- `run_one_scenario(client, scenario, bench, model, max_tokens)` → dict
- `run_all(bench, args)` → full results dict
- `emit_markdown(results)` → str
- `emit_json(results)` → str

The scorer is fully deterministic: given a response JSON and expected
spec, it returns the same score every time. This means C.4's unit tests
can exercise every code path with mocked API calls.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make the hook _lib importable so we can reuse redact_secrets()
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if _HOOKS_DIR.exists() and str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.redact import redact_secrets  # type: ignore
except ImportError:
    # Fallback: identity redactor if the _lib isn't reachable (e.g. running
    # from an unusual cwd). The main code path covers the normal case.
    def redact_secrets(text, max_chars: int = 120) -> str:
        if text is None:
            return ""
        return text[:max_chars] if len(text) > max_chars else text


# ---------------------------------------------------------------------------
# Defaults and constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 2000
DEFAULT_REPETITIONS = 3
DEFAULT_CONCURRENCY = 3
DEFAULT_COST_CAP_USD = 1.00
DEFAULT_MAX_INPUT_CHARS = 4000
DEFAULT_MAX_SCENARIOS = 50

# Haiku 4.5 pricing (2026-04-11, subject to change — update on model switch)
#   Input:  $0.25 / 1M tokens
#   Output: $1.25 / 1M tokens
HAIKU_INPUT_PER_MTOK = 0.25
HAIKU_OUTPUT_PER_MTOK = 1.25

# PLAN-133 C1 — per-scenario aggregation across the N repetitions.
#
# Goose-harvest eval doctrine: a skill that passes only *sometimes* is a
# latent regression, so the conservative "worst-of-N" aggregation surfaces
# the floor (the worst run) rather than the median. A `flaky` flag is set
# whenever the N runs disagree on pass/fail — independent of which
# aggregation is selected.
#
# Behavioral switch is reversible (cross-cutting doctrine §1 — default-OFF /
# measure-first): the default is the NEW conservative "worst" aggregation,
# but operators may pin the legacy median via CEO_BENCH_AGGREGATION=median
# to compare a historical run. Any unrecognised value fails OPEN back to the
# safe "worst" default (infra fail-open: never crash the harness on a typo).
BENCH_AGGREGATION_ENV = "CEO_BENCH_AGGREGATION"
DEFAULT_AGGREGATION = "worst"
_VALID_AGGREGATIONS = ("worst", "median")


def _resolve_aggregation() -> str:
    """Resolve the per-scenario aggregation mode from the environment.

    Returns one of ``_VALID_AGGREGATIONS``. Unknown / empty values
    fail OPEN to ``DEFAULT_AGGREGATION`` ("worst") so a typo in the env
    can never crash the harness (fail-open-on-infra). The legacy median
    aggregation is reachable via ``CEO_BENCH_AGGREGATION=median``.
    """
    raw = os.environ.get(BENCH_AGGREGATION_ENV, "")
    mode = raw.strip().lower()
    if mode in _VALID_AGGREGATIONS:
        return mode
    return DEFAULT_AGGREGATION


def aggregate_scores(
    scores: List[float],
    *,
    mode: str = DEFAULT_AGGREGATION,
) -> float:
    """Aggregate the per-run scores into one scalar per the mode.

    - ``"worst"`` → the minimum score (conservative floor).
    - ``"median"`` → the legacy median-of-N (upper-median for even N,
      matching the historical ``sorted[len//2]`` selection).

    Empty input → 0.0. An unknown mode falls back to "worst".
    """
    if not scores:
        return 0.0
    ordered = sorted(scores)
    if mode == "median":
        return ordered[len(ordered) // 2]
    # default + "worst"
    return ordered[0]


def detect_flaky(run_passed: List[bool]) -> bool:
    """Return True when the per-run pass/fail verdicts disagree.

    A scenario is *flaky* when at least one repetition passed and at
    least one failed (non-deterministic verdict across the N runs).
    Fewer than two runs can never be flaky.
    """
    if len(run_passed) < 2:
        return False
    return any(run_passed) and not all(run_passed)


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def load_benchmark(path: Path) -> Dict[str, Any]:
    """Load a benchmark YAML. Raises ValueError on missing fields."""
    try:
        import yaml  # type: ignore
    except ImportError as e:
        print(
            "[run-skill-benchmark] FATAL: PyYAML is required. "
            "Install with `pip install pyyaml`.",
            file=sys.stderr,
        )
        raise SystemExit(2) from e

    if not path.is_file():
        raise FileNotFoundError(f"benchmark file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level must be a mapping")
    for required in ("skill", "scenarios", "scoring"):
        if required not in data:
            raise ValueError(f"{path}: missing required field `{required}`")
    if not isinstance(data["scenarios"], list):
        raise ValueError(f"{path}: `scenarios` must be a list")
    return data


def load_skill_content(skill_name: str) -> str:
    """Read the SKILL.md for a named skill from any tier."""
    for tier in ("core", "frontend"):
        candidate = _REPO_ROOT / ".claude" / "skills" / tier / skill_name / "SKILL.md"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    domains_dir = _REPO_ROOT / ".claude" / "skills" / "domains"
    if domains_dir.is_dir():
        for domain in domains_dir.iterdir():
            candidate = domain / "skills" / skill_name / "SKILL.md"
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
    raise FileNotFoundError(f"skill {skill_name!r} not found in any tier")


# ---------------------------------------------------------------------------
# Cost estimation + budget guard
# ---------------------------------------------------------------------------


def estimate_cost_usd(
    bench: Dict[str, Any],
    *,
    max_tokens: int,
    repetitions: int,
    approx_input_tokens_per_scenario: int = 4000,
) -> float:
    """Return a dollar estimate for one full run of the benchmark."""
    n_scenarios = len(bench.get("scenarios", []))
    input_mtok = (n_scenarios * repetitions * approx_input_tokens_per_scenario) / 1_000_000
    output_mtok = (n_scenarios * repetitions * max_tokens) / 1_000_000
    return round(
        input_mtok * HAIKU_INPUT_PER_MTOK + output_mtok * HAIKU_OUTPUT_PER_MTOK,
        4,
    )


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def build_prompt(
    skill_content: str,
    scenario: Dict[str, Any],
    *,
    max_input_chars: int,
) -> Tuple[str, str]:
    """Build (system_prompt, user_prompt) for a single scenario call."""
    content = scenario.get("input", {}).get("content", "")
    if len(content) > max_input_chars:
        content = content[:max_input_chars] + "\n# ... truncated for benchmark ..."

    language = scenario.get("input", {}).get("language", "text")
    template = scenario.get("prompt_template", "")

    system_prompt = (
        "You are a senior security engineer reviewing code. "
        "Loaded skill follows.\n\n"
        "=== SKILL START ===\n"
        f"{skill_content}\n"
        "=== SKILL END ===\n\n"
        "When the user asks for a review, respond ONLY with valid JSON "
        "matching the schema the user specifies. No prose, no markdown "
        "fences — JSON only."
    )

    user_prompt = (
        f"{template}\n\n"
        f"```{language}\n{content}\n```\n"
    )

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Response parsing + scoring
# ---------------------------------------------------------------------------


_JSON_EXTRACT_RE = re.compile(r"\{[\s\S]*\}", re.MULTILINE)


def parse_response(text: str) -> Dict[str, Any]:
    """Extract a JSON object from the model response, tolerating fences.

    The prompt asks for JSON only, but models sometimes wrap it in
    ```json ... ``` fences or add a trailing explanation. We find the
    outermost `{...}` block and parse it. Returns `{"issues": []}` on
    parse failure so scoring can still run (scored as 0 recall).
    """
    if not text:
        return {"issues": []}
    match = _JSON_EXTRACT_RE.search(text)
    if not match:
        return {"issues": [], "_parse_error": "no JSON object found"}
    blob = match.group(0)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as e:
        return {"issues": [], "_parse_error": f"JSON decode: {e.msg}"}
    if not isinstance(data, dict):
        return {"issues": [], "_parse_error": "top-level not an object"}
    if "issues" not in data:
        data["issues"] = []
    return data


def score_scenario(
    response: Dict[str, Any],
    expected: Dict[str, Any],
    scoring: Dict[str, Any],
    *,
    is_control: bool = False,
) -> Dict[str, Any]:
    """Score a single scenario response against the expected spec.

    Returns a dict with `score` (0.0–1.0), `breakdown`, and `explanation`.

    Positive scenarios score on (tag_weight, suggestion_weight, severity_weight).
    Control scenarios score 1.0 if no must_not_flag_tags appear at MEDIUM+,
    0.0 otherwise.
    """
    tag_weight = scoring.get("tag_weight", 0.5)
    suggestion_weight = scoring.get("suggestion_weight", 0.3)
    severity_weight = scoring.get("severity_weight", 0.2)

    issues = response.get("issues", [])
    if not isinstance(issues, list):
        issues = []

    flagged_tags = [
        str(i.get("tag", "")).lower().strip()
        for i in issues
        if isinstance(i, dict)
    ]
    flagged_suggestions = [
        str(i.get("suggestion", "")).lower() for i in issues if isinstance(i, dict)
    ]
    flagged_severities = [
        str(i.get("severity", "")).upper() for i in issues if isinstance(i, dict)
    ]

    if is_control:
        must_not = [t.lower() for t in expected.get("must_not_flag_tags", [])]
        high_sev = {"MEDIUM", "HIGH", "CRITICAL"}
        leaked = []
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            tag = str(issue.get("tag", "")).lower().strip()
            sev = str(issue.get("severity", "")).upper()
            if sev not in high_sev:
                continue
            if any(forbidden in tag or tag in forbidden for forbidden in must_not):
                leaked.append(tag)
        passed = len(leaked) == 0
        return {
            "score": 1.0 if passed else 0.0,
            "passed": passed,
            "breakdown": {
                "leaked_tags": leaked,
                "must_not_flag_tags": must_not,
            },
            "explanation": (
                "PASS — no forbidden tags at MEDIUM+"
                if passed
                else f"FAIL — control leaked: {leaked}"
            ),
        }

    # Positive scenario scoring
    must_flag = [t.lower() for t in expected.get("must_flag_tags", [])]
    alt_flag = [t.lower() for t in expected.get("acceptable_alternative_tags", [])]
    must_suggest = [kw.lower() for kw in expected.get("must_suggest_keywords", [])]
    must_severity = expected.get("must_identify_severity", "").upper()

    # --- tag score ---
    tag_hit_primary = any(
        any(tag in f_tag or f_tag in tag for f_tag in flagged_tags) for tag in must_flag
    )
    tag_hit_alt = any(
        any(tag in f_tag or f_tag in tag for f_tag in flagged_tags) for tag in alt_flag
    )
    if tag_hit_primary:
        tag_score = tag_weight
    elif tag_hit_alt:
        tag_score = tag_weight * 0.5
    else:
        tag_score = 0.0

    # --- suggestion score ---
    suggestion_blob = " ".join(flagged_suggestions)
    suggestion_hit = any(kw in suggestion_blob for kw in must_suggest)
    suggestion_score = suggestion_weight if suggestion_hit else 0.0

    # --- severity score ---
    if must_severity:
        severity_hit = must_severity in flagged_severities
        severity_score = severity_weight if severity_hit else 0.0
    else:
        severity_score = severity_weight  # no expectation → full credit

    total = round(tag_score + suggestion_score + severity_score, 3)
    pass_threshold = scoring.get("pass_threshold", 0.7)
    return {
        "score": total,
        "passed": total >= pass_threshold,
        "breakdown": {
            "tag_score": round(tag_score, 3),
            "suggestion_score": round(suggestion_score, 3),
            "severity_score": round(severity_score, 3),
            "tag_hit_primary": tag_hit_primary,
            "tag_hit_alt": tag_hit_alt,
            "suggestion_hit": suggestion_hit,
        },
        "flagged_tags": flagged_tags,
        "explanation": (
            f"tag={round(tag_score,3)} "
            f"sugg={round(suggestion_score,3)} "
            f"sev={round(severity_score,3)}"
        ),
    }


# ---------------------------------------------------------------------------
# Anthropic API client (lazy import)
# ---------------------------------------------------------------------------


async def call_api(
    client,
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> str:
    """Call the API once and return the text response.

    Retries with exponential backoff on rate limits / transient errors.
    Max 3 attempts. Raises on final failure.
    """
    from anthropic import RateLimitError, APIError  # type: ignore

    delay = 1.0
    last_error = None
    for attempt in range(3):
        try:
            resp = await asyncio.to_thread(
                client.messages.create,
                model=model,
                max_tokens=max_tokens,
                temperature=0,
                top_p=1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            # Extract text content from the response
            parts = []
            for block in resp.content:
                if hasattr(block, "text"):
                    parts.append(block.text)
                elif isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
            return "".join(parts)
        except (RateLimitError, APIError) as e:
            last_error = e
            if attempt == 2:
                break
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                raise
            except Exception:  # pragma: no cover — sleep should not raise other types
                pass
            delay *= 2
    raise RuntimeError(f"API call failed after 3 attempts: {last_error}")


# ---------------------------------------------------------------------------
# Per-scenario runner (worst-of-N + flaky flag — PLAN-133 C1)
# ---------------------------------------------------------------------------


async def run_one_scenario(
    client,
    scenario: Dict[str, Any],
    *,
    skill_content: str,
    model: str,
    max_tokens: int,
    repetitions: int,
    scoring: Dict[str, Any],
    max_input_chars: int,
) -> Dict[str, Any]:
    """Run a scenario `repetitions` times, score each, aggregate the runs.

    PLAN-133 C1 — aggregation switched from median-of-N to **worst-of-N**
    (the conservative floor) and a ``flaky`` flag is set whenever the N
    runs disagree on pass/fail. The aggregation mode is selectable via
    ``CEO_BENCH_AGGREGATION`` (default "worst"; "median" restores legacy).

    The aggregated score is exposed BOTH as ``aggregated_score`` (new,
    explicit) and ``median_score`` (kept as the stable key the downstream
    ``median_score_bps`` emit consumer + SPEC + markdown reporter read).
    """
    system_prompt, user_prompt = build_prompt(
        skill_content, scenario, max_input_chars=max_input_chars
    )
    expected = scenario.get("expected", {})
    is_control = bool(scenario.get("control", False))

    raw_runs = []
    for run_idx in range(repetitions):
        t0 = time.monotonic()
        try:
            text = await call_api(
                client,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            )
            # Redact before storing (defense in depth)
            text_safe = redact_secrets(text, max_chars=0)
            parsed = parse_response(text_safe)
            result = score_scenario(
                parsed, expected, scoring, is_control=is_control
            )
            result["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
            result["parse_error"] = parsed.get("_parse_error")
            raw_runs.append(result)
        except Exception as e:
            raw_runs.append(
                {
                    "score": 0.0,
                    "passed": False,
                    "error": str(e),
                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                    "skipped": True,
                }
            )

    # PLAN-133 C1 — worst-of-N (default) aggregation + flaky detection.
    mode = _resolve_aggregation()
    raw_scores = [r["score"] for r in raw_runs]
    aggregated = aggregate_scores(raw_scores, mode=mode)
    run_passed = [bool(r.get("passed", False)) for r in raw_runs]
    all_passed = all(run_passed) if run_passed else False
    flaky = detect_flaky(run_passed)

    return {
        "id": scenario["id"],
        "name": scenario.get("name", ""),
        "control": is_control,
        "category": scenario.get("category", ""),
        # `median_score` remains the stable downstream key (emit consumer,
        # SPEC median_score_bps, markdown reporter) but now carries the
        # selected aggregation — "worst" by default. `aggregated_score`
        # and `aggregation` make the new semantics explicit.
        "median_score": round(aggregated, 3),
        "aggregated_score": round(aggregated, 3),
        "aggregation": mode,
        "flaky": flaky,
        "all_runs_passed": all_passed,
        "passed": aggregated >= scoring.get("pass_threshold", 0.7),
        "raw_scores": raw_scores,
        "raw_runs": raw_runs,
        "version": scenario.get("version"),
        "validated_by": scenario.get("validated_by"),
    }


# ---------------------------------------------------------------------------
# Full runner
# ---------------------------------------------------------------------------


async def run_all_async(
    bench: Dict[str, Any], args, client
) -> Dict[str, Any]:
    """Run every benchmark scenario through the dispatcher with bounded concurrency."""
    skill_name = bench["skill"]
    scoring = bench["scoring"]
    scenarios = bench["scenarios"]

    skill_content = load_skill_content(skill_name)

    sem = asyncio.Semaphore(args.concurrency)

    async def bounded(scenario) -> Dict[str, Any]:
        async with sem:
            return await run_one_scenario(
                client,
                scenario,
                skill_content=skill_content,
                model=args.model,
                max_tokens=args.max_tokens,
                repetitions=args.repetitions,
                scoring=scoring,
                max_input_chars=DEFAULT_MAX_INPUT_CHARS,
            )

    tasks = [bounded(s) for s in scenarios]
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        raise
    except Exception as gather_err:  # pragma: no cover — gather(return_exceptions=True) absorbs per-task errors
        print(
            f"benchmark: asyncio.gather failed unexpectedly: {gather_err}",
            file=sys.stderr,
        )
        results = [gather_err] * len(tasks)

    per_scenario: List[Dict[str, Any]] = []
    for r in results:
        if isinstance(r, Exception):
            per_scenario.append({"error": str(r), "passed": False})
        else:
            per_scenario.append(r)

    passed_count = sum(1 for r in per_scenario if r.get("passed"))
    total_count = len(per_scenario)
    overall_score = passed_count / total_count if total_count else 0.0

    return {
        "benchmark": {
            "skill": skill_name,
            "version": bench.get("benchmark_version"),
            "owner": bench.get("owner"),
            "scenario_count": total_count,
        },
        "model": args.model,
        "repetitions": args.repetitions,
        "overall": {
            "passed": passed_count,
            "total": total_count,
            "score": round(overall_score, 3),
            "health": _health_label(overall_score, scoring.get("health_thresholds", {})),
        },
        "scenarios": per_scenario,
        "timestamp": _now_iso(),
    }


def _health_label(score: float, thresholds: Dict[str, float]) -> str:
    critical = thresholds.get("critical", 0.4)
    warning = thresholds.get("warning", 0.6)
    healthy = thresholds.get("healthy", 0.8)
    if score < critical:
        return "CRITICAL"
    if score < warning:
        return "WARNING"
    if score >= healthy:
        return "HEALTHY"
    return "OK"


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Reporters
# ---------------------------------------------------------------------------


def emit_markdown(results: Dict[str, Any]) -> str:
    """Render benchmark results as a markdown table for PR preview."""
    lines: List[str] = []
    bench = results["benchmark"]
    overall = results["overall"]
    lines.append(f"## Benchmark: `{bench['skill']}` (v{bench.get('version')})")
    lines.append("")
    lines.append(f"- **Owner:** {bench.get('owner', 'unknown')}")
    lines.append(f"- **Model:** `{results['model']}`")
    scenarios = results.get("scenarios", [])
    agg_mode = next(
        (s.get("aggregation") for s in scenarios if s.get("aggregation")),
        DEFAULT_AGGREGATION,
    )
    flaky_count = sum(1 for s in scenarios if s.get("flaky"))
    lines.append(
        f"- **Repetitions:** {results['repetitions']}× ({agg_mode}-of-N)"
    )
    lines.append(
        f"- **Overall:** {overall['passed']} / {overall['total']} passed "
        f"({int(overall['score'] * 100)}%) — **{overall['health']}**"
    )
    if flaky_count:
        lines.append(f"- **Flaky scenarios:** {flaky_count} ⚠")
    lines.append(f"- **Timestamp:** {results['timestamp']}")
    lines.append("")
    lines.append("| ID | Scenario | Score | Status | Type | Flaky |")
    lines.append("|---|---|---:|---|---|---|")
    for s in results["scenarios"]:
        sid = s.get("id", "?")
        name = s.get("name", "")
        score = s.get("median_score", 0.0)
        status = "✓ PASS" if s.get("passed") else "✗ FAIL"
        stype = "control" if s.get("control") else "positive"
        flaky = "⚠ FLAKY" if s.get("flaky") else ""
        lines.append(
            f"| `{sid}` | {name} | {score} | {status} | {stype} | {flaky} |"
        )
    return "\n".join(lines)


def emit_json(results: Dict[str, Any]) -> str:
    return json.dumps(results, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the skill-benchmark CLI."""
    p = argparse.ArgumentParser(
        prog="run-skill-benchmark.py",
        description="Run a skill benchmark YAML against the Anthropic API",
    )
    p.add_argument("benchmark", help="Path to the benchmark YAML file")
    p.add_argument("--output-json", default=None, help="Write full results to path")
    p.add_argument("--markdown", action="store_true", help="Emit Markdown report to stdout")
    p.add_argument("--json", dest="as_json", action="store_true", help="Emit JSON to stdout")
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--strict", action="store_true", help="Exit 1 on any scenario failure")
    p.add_argument("--allow-expensive", action="store_true", help="Bypass $1 cost cap")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--skip-if-no-key", action="store_true")
    p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS)
    p.add_argument(
        "--cost-cap-usd",
        type=float,
        default=DEFAULT_COST_CAP_USD,
        help="Max dollars per invocation (default 1.00)",
    )
    p.add_argument(
        "--floor",
        type=float,
        default=None,
        help=(
            "Absolute floor (0.0-1.0) — overall score below this fails the "
            "run with exit 1. Sprint 3 Item B. Default: no absolute floor "
            "(only CRITICAL health floor applies)."
        ),
    )
    p.add_argument(
        "--write-lessons",
        action="store_true",
        help=(
            "On scenario failures, write lesson files for the Reflexion "
            "loop. Sprint 3 Item A. See .claude/scripts/lessons.py."
        ),
    )
    # PLAN-011 Phase 3 — LLM-as-judge mode selector
    p.add_argument(
        "--judge-mode",
        choices=("fixture", "llm", "both", "fallback"),
        default="fixture",
        help=(
            "Judge mode (PLAN-011 Phase 3): "
            "'fixture' (default, preserves current behavior) · "
            "'llm' (run LLM judge, fail if unreachable) · "
            "'both' (run both fixture + judge, record both in audit "
            "log; disagreement >0.2 emits veto event) · "
            "'fallback' (deterministic keyword-match scorer)"
        ),
    )
    p.add_argument(
        "--judge-adapter",
        choices=("gemini", "openai", "local"),
        default="gemini",
        help="Judge provider adapter when --judge-mode=llm|both",
    )
    p.add_argument(
        "--judge-mock",
        action="store_true",
        help="Use mock judge (deterministic; for CI)",
    )
    p.add_argument(
        "--judge-rubric-file",
        default=None,
        help="Optional rubric JSON for judge/fallback (falls back to synthesised per-scenario rubric)",
    )
    return p


def _judge_mode_resolved(args) -> str:
    """Resolve effective judge mode, honoring CEO_SOTA_DISABLE (S4).

    Returns one of: 'fixture', 'llm', 'both', 'fallback'. When
    `CEO_SOTA_DISABLE=1`, force 'fixture' and print a WARNING on stderr.
    """
    mode = getattr(args, "judge_mode", "fixture")
    if os.environ.get("CEO_SOTA_DISABLE") == "1" and mode != "fixture":
        print(
            f"[run-skill-benchmark] WARNING: CEO_SOTA_DISABLE=1 overrides "
            f"--judge-mode={mode} → fixture",
            file=sys.stderr,
        )
        return "fixture"
    return mode


def _synth_rubric_from_bench(bench: Dict[str, Any]) -> Dict[str, Any]:
    """Synthesize a minimal rubric from a benchmark YAML when none provided.

    Produces a rubric with one item per positive scenario. Items are
    weighted equally. Used by `--judge-mode={llm,both,fallback}` when
    the operator did not pass `--judge-rubric-file`.
    """
    scenarios = [
        s for s in bench.get("scenarios", [])
        if not s.get("control", False)
    ]
    if not scenarios:
        # Fall back to a one-item generic rubric so scoring is still possible
        scenarios = [{"id": "default", "name": bench.get("skill", "benchmark")}]
    weight = round(1.0 / max(len(scenarios), 1), 4)
    items = [
        {
            "id": s.get("id", f"item{i}"),
            "description": s.get("name", "") or s.get("id", ""),
            "weight": weight,
        }
        for i, s in enumerate(scenarios)
    ]
    return {
        "version": 1,
        "rubric_id": f"auto-{bench.get('skill','unknown')}",
        "items": items,
        "scoring": "weighted_average",
    }


def _run_judge_mode(
    bench: Dict[str, Any],
    fixture_results: Dict[str, Any],
    args,
) -> Optional[Dict[str, Any]]:
    """Run LLM judge + fallback per `--judge-mode`. Returns grade dict or None.

    - 'fixture' → None (caller skips)
    - 'llm' → LLM judge (mock OK); on JudgeUnreachable, return None
    - 'both' → LLM judge AND keep fixture score; audit event marks disagreement
    - 'fallback' → deterministic scorer
    """
    mode = _judge_mode_resolved(args)
    if mode == "fixture":
        return None

    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    # Synthesize the response from per-scenario medians (representative sample).
    overall = fixture_results.get("overall", {})
    sample_response = json.dumps({
        "overall": overall,
        "scenarios": [
            {
                "id": s.get("id"),
                "score": s.get("median_score"),
                "passed": s.get("passed"),
            }
            for s in fixture_results.get("scenarios", [])[:10]
        ],
    })

    # Rubric: from file if provided, otherwise synthesised
    if getattr(args, "judge_rubric_file", None):
        try:
            rubric = json.loads(
                Path(args.judge_rubric_file).read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as e:
            print(
                f"[run-skill-benchmark] WARN: rubric file unreadable ({e}); "
                "synthesising",
                file=sys.stderr,
            )
            rubric = _synth_rubric_from_bench(bench)
    else:
        rubric = _synth_rubric_from_bench(bench)

    skill = bench.get("skill", "unknown")
    if mode == "fallback":
        # Late import to keep stdlib-only at module load time.
        import importlib.util
        scorer_path = scripts_dir / "benchmark-fallback-scorer.py"
        spec = importlib.util.spec_from_file_location(
            "benchmark_fallback_scorer", scorer_path
        )
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.grade(sample_response, rubric, benchmark_slug=skill)

    # llm or both
    import importlib.util
    judge_path = scripts_dir / "benchmark-judge.py"
    spec = importlib.util.spec_from_file_location("benchmark_judge", judge_path)
    if spec is None or spec.loader is None:
        return None
    judge_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(judge_mod)

    adapter_name = getattr(args, "judge_adapter", "gemini")
    main_adapter = os.environ.get("CEO_HOOK_ADAPTER", "claude")
    try:
        judge_mod.assert_cross_provider(adapter_name, main_adapter)
    except judge_mod.CrossProviderCollision as e:
        print(f"[run-skill-benchmark] judge skipped: {e}", file=sys.stderr)
        return None

    try:
        template_text = judge_mod.DEFAULT_PROMPT_PATH.read_text(encoding="utf-8")
        grade = judge_mod.two_pass_grade(
            task_context=f"skill benchmark: {skill}",
            rubric=rubric,
            response=sample_response,
            adapter_name=adapter_name,
            template_text=template_text,
            mock=bool(getattr(args, "judge_mock", False)),
        )
    except judge_mod.JudgeUnreachable:
        if mode == "llm":
            return None
        # 'both' mode: degrade to fallback silently
        return None

    return {
        "benchmark": skill,
        "judge_adapter": adapter_name,
        "golden_prompt_hash": judge_mod.prompt_sha256(),
        **grade,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — run the skill-benchmark harness end-to-end."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # API key check
    if not os.environ.get("ANTHROPIC_API_KEY"):
        if args.skip_if_no_key:
            print("SKIPPED: ANTHROPIC_API_KEY not set (advisory mode)")
            return 0
        print(
            "ERROR: ANTHROPIC_API_KEY not set. "
            "Set the env var or pass --skip-if-no-key for advisory mode.",
            file=sys.stderr,
        )
        return 2

    # Load benchmark
    bench_path = Path(args.benchmark)
    try:
        bench = load_benchmark(bench_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Sanity caps
    n_scenarios = len(bench.get("scenarios", []))
    if n_scenarios > DEFAULT_MAX_SCENARIOS:
        print(
            f"ERROR: benchmark has {n_scenarios} scenarios "
            f"(cap {DEFAULT_MAX_SCENARIOS}). Refuse to run.",
            file=sys.stderr,
        )
        return 2

    # Cost estimate + cap
    estimated_cost = estimate_cost_usd(
        bench, max_tokens=args.max_tokens, repetitions=args.repetitions
    )
    print(
        f"[run-skill-benchmark] estimated cost: ${estimated_cost:.4f} "
        f"({n_scenarios} scenarios × {args.repetitions} reps × model={args.model})",
        file=sys.stderr,
    )
    if estimated_cost > args.cost_cap_usd and not args.allow_expensive:
        print(
            f"ERROR: estimated cost ${estimated_cost:.4f} > cap "
            f"${args.cost_cap_usd:.2f}. Pass --allow-expensive to override.",
            file=sys.stderr,
        )
        return 2

    # Lazy-import anthropic
    try:
        from anthropic import Anthropic  # type: ignore
    except ImportError:
        print(
            "ERROR: `anthropic` SDK not installed. "
            "Install with: pip install anthropic",
            file=sys.stderr,
        )
        return 2

    client = Anthropic()

    # Run
    t0 = time.monotonic()
    results = asyncio.run(run_all_async(bench, args, client))
    duration_s = round(time.monotonic() - t0, 3)

    # Emit
    default_md = args.markdown or (not args.as_json and not args.output_json)
    if default_md:
        print(emit_markdown(results))
    if args.as_json:
        print(emit_json(results))
    if args.output_json:
        Path(args.output_json).write_text(emit_json(results), encoding="utf-8")

    # Sprint 3 Item A — write lessons for failed scenarios
    lessons_written = 0
    if args.write_lessons:
        lessons_written = _write_lessons_for_failures(results, bench)

    # PLAN-011 Phase 3 — LLM judge / fallback (opt-in via --judge-mode)
    judge_result = None
    try:
        judge_result = _run_judge_mode(bench, results, args)
    except Exception as e:  # pragma: no cover — fail-open
        print(f"[run-skill-benchmark] judge mode errored: {e}", file=sys.stderr)
        judge_result = None

    # Sprint 5 A.1 — emit benchmark_run event to audit log (fail-open)
    _emit_benchmark_audit_event(results, args, duration_s, lessons_written, judge_result)

    # Exit code
    overall = results["overall"]
    if overall["health"] == "CRITICAL":
        # Hard floor: CRITICAL fails CI even in advisory mode
        print(f"CRITICAL: overall score {overall['score']} below floor", file=sys.stderr)
        return 1
    # Sprint 3 Item B — absolute floor (rc=1 per debate consensus R-DEV1)
    if args.floor is not None and overall["score"] < args.floor:
        print(
            f"FLOOR: overall score {overall['score']} below absolute floor "
            f"{args.floor}",
            file=sys.stderr,
        )
        return 1
    if args.strict and overall["passed"] < overall["total"]:
        return 1
    return 0


def _write_lessons_for_failures(
    results: Dict[str, Any], bench: Dict[str, Any]
) -> int:
    """For each failed scenario, write a lesson file via lessons.py.

    Silent on errors — lesson-writing is best-effort telemetry, not a
    gate on the benchmark run. Returns count of lessons successfully
    written (used by the Sprint 5 A.1 audit emitter).
    """
    try:
        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import lessons as lessons_mod  # type: ignore
    except ImportError:
        print(
            "[run-skill-benchmark] WARN: lessons.py not importable; "
            "skipping lesson writes",
            file=sys.stderr,
        )
        return 0

    skill_name = bench.get("skill", "unknown")
    owner = bench.get("owner", "unknown")
    written = 0
    for s in results.get("scenarios", []):
        if s.get("passed"):
            continue
        scenario_id = s.get("id") or "unknown"
        expected = s.get("expected", "")
        response = s.get("response_raw", "") or s.get("response", "")
        remember = (
            f"Scenario {scenario_id} failed on skill {skill_name} "
            f"(score {s.get('median_score', 0.0)})"
        )
        try:
            lessons_mod.write_lesson(
                scenario_id=scenario_id,
                archetype=owner,
                remember_this=remember,
                scope_tags=[skill_name, scenario_id],
                agent_response=str(response)[:4000],
                expected_response=str(expected)[:4000],
            )
            written += 1
        except Exception as e:  # pragma: no cover
            print(
                f"[run-skill-benchmark] WARN: lesson write failed for "
                f"{scenario_id}: {e}",
                file=sys.stderr,
            )
    if written:
        print(
            f"[run-skill-benchmark] wrote {written} lesson(s) to reflect "
            f"on next run",
            file=sys.stderr,
        )
    return written


def _emit_benchmark_audit_event(
    results: Dict[str, Any],
    args: argparse.Namespace,
    duration_s: float,
    lessons_written: int,
    judge_result: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a benchmark_run event to the audit log. Fail-open.

    PLAN-011 Phase 3: when ``judge_result`` is provided, the emitted
    event carries judge-mode fields (forward/reverse/delta/adapter).
    When fixture-score vs judge-score differ by >0.2 under ``--judge-mode=both``,
    an additional ``veto_triggered`` event is emitted with reason_code
    ``"benchmark_judge_disagreement"``.
    """
    try:
        hooks_dir = Path(__file__).resolve().parent.parent / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib.audit_emit import (  # type: ignore
            emit_benchmark_run,
            emit_veto_triggered,
            _write_event,
        )
    except Exception:
        return

    try:
        bench = results.get("benchmark", {})
        overall = results.get("overall", {})
        scenarios = results.get("scenarios", [])
        # PLAN-133 C1 — aggregate the per-scenario scores into the
        # `median_score_bps` field using the SAME aggregation as the
        # per-scenario runner (worst-of-N by default; CEO_BENCH_AGGREGATION
        # =median restores the legacy median). The field name stays
        # `median_score_bps` (SPEC-stable / audit-chain-stable) but now
        # carries the selected aggregation floor.
        agg_mode = _resolve_aggregation()
        per_scenario_scores = [
            float(s.get("median_score", 0.0)) for s in scenarios if s
        ]
        median_score = aggregate_scores(per_scenario_scores, mode=agg_mode)
        flaky_count = sum(1 for s in scenarios if s and s.get("flaky"))
        benchmark_id = f"{bench.get('skill','unknown')}@v{bench.get('version','?')}"

        # Build the v2 event manually so we can add judge-mode fields.
        # Float fields use the int-encoded basis-points / cents / ms form
        # required by canonical_json (no-float invariant on HMAC fields).
        # PLAN-011 Phase 3 adds optional judge-mode fields; they are also
        # int-encoded (score_bps / delta_bps).
        fixture_score_f = float(overall.get("score", 0.0))
        floor_f = float(args.floor) if args.floor is not None else 0.0
        event: Dict[str, Any] = {
            "action": "benchmark_run",
            "benchmark_id": benchmark_id,
            "skill": str(bench.get("skill", "unknown")),
            "pass_count": int(overall.get("passed", 0)),
            "fail_count": int(overall.get("total", 0) - overall.get("passed", 0)),
            "pass_rate_bps": max(0, min(1000, int(round(fixture_score_f * 1000)))),
            "median_score_bps": max(0, min(1000, int(round(float(median_score) * 1000)))),
            "floor_bps": max(0, min(1000, int(round(floor_f * 1000)))),
            "cost_usd_cents": 0,
            "duration_ms": max(0, int(round(float(duration_s) * 1000))),
            "lessons_written": int(lessons_written),
            # PLAN-133 C1 — worst-of-N aggregation provenance + flaky count.
            # Ints only (no-float HMAC invariant); additive forward-compat
            # fields per AUDIT-LOG-SCHEMA §2 (SPEC update staged C1.proposal).
            "aggregation": str(agg_mode),
            "flaky_count": int(flaky_count),
            "session_id": "",
            "project": "",
        }
        judge_mode = getattr(args, "judge_mode", "fixture")
        event["judge_mode"] = judge_mode

        fixture_score = fixture_score_f
        judge_score_forward: Optional[float] = None
        judge_score_reverse: Optional[float] = None

        if judge_result:
            event["judge_adapter"] = judge_result.get("judge_adapter")
            fwd = (judge_result.get("forward") or {}).get("score")
            rev = (judge_result.get("reverse") or {}).get("score")
            if fwd is not None:
                judge_score_forward = float(fwd)
                # score_bps: judge scores are 0..10; normalize to 0..1 then ×1000.
                # int(round((score / 10.0) * 1000)) so 8 → 800, 10 → 1000, 7 → 700.
                event["judge_score_forward_bps"] = max(
                    0, min(1000, int(round((judge_score_forward / 10.0) * 1000)))
                )
            if rev is not None:
                judge_score_reverse = float(rev)
                event["judge_score_reverse_bps"] = max(
                    0, min(1000, int(round((judge_score_reverse / 10.0) * 1000)))
                )
            delta = judge_result.get("delta")
            if delta is not None:
                # delta_bps: judge delta is 0..10 range; normalize to 0..1 then ×1000.
                # signed bps; clamp to -1000..1000.
                event["judge_delta_bps"] = max(
                    -1000, min(1000, int(round((float(delta) / 10.0) * 1000)))
                )
            if judge_result.get("judge_adapter") == "fallback":
                # fallback_score_bps: same scale as judge_score_forward_bps (0..10 → bps)
                if fwd is not None:
                    event["fallback_score_bps"] = max(
                        0, min(1000, int(round((float(fwd) / 10.0) * 1000)))
                    )

        _write_event(event)

        # Disagreement audit (judge_mode=both): fixture vs judge delta > 0.2
        # (normalise judge to [0,1] scale for comparison with fixture).
        if (
            judge_mode == "both"
            and judge_score_forward is not None
        ):
            judge_normalised = judge_score_forward / 10.0
            if abs(fixture_score - judge_normalised) > 0.2:
                emit_veto_triggered(
                    hook="run_skill_benchmark",
                    reason_code="benchmark_judge_disagreement",
                    reason_preview=(
                        f"benchmark={benchmark_id} fixture={fixture_score:.3f} "
                        f"judge={judge_normalised:.3f} delta="
                        f"{abs(fixture_score - judge_normalised):.3f}"
                    ),
                    blocked_tool="",
                )
    except Exception:
        return


if __name__ == "__main__":
    sys.exit(main())
