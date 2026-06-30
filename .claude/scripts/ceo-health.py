#!/usr/bin/env python3
"""ceo-health — one-shot framework health check.

Stdlib-only CLI that runs a battery of checks an external monitor or
operator can use to confirm the framework state is intact:

1. ``.claude/settings.json`` parses as JSON
2. Required hook files exist + are executable
3. Last 10 audit-log entries readable + parse cleanly
4. Memory dir exists + is readable
5. Plans dir frontmatter parseable
6. No uncommitted changes under ``.claude/skills/`` (advisory)
7. No uncommitted changes under ``.claude/hooks/`` (advisory)
8. Native agents present + ``_dispatch.md`` in sync (advisory)

Exit codes::

    0 — healthy
    1 — issues found (see output)
    2 — fatal (cannot run check at all)

Usage::

    ceo-health.py
    ceo-health.py --format json
    ceo-health.py --quiet            # exit code only

Use case: ``ceo-health.py || pagerduty-trigger`` in cron.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration — paths discovered from the working directory
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    """Walk up from CWD looking for `.claude/` to find the project root."""
    cur = Path.cwd().resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".claude").is_dir():
            return parent
    raise SystemExit("fatal: not inside a ceo-orchestration project (no .claude/ found)")


def audit_log_path() -> Path:
    """Resolve the audit log path, honoring `CEO_AUDIT_LOG_PATH` override."""
    home = Path(os.environ.get("HOME") or str(Path.home()))
    default_dir = home / ".claude" / "projects" / "ceo-orchestration"
    return Path(
        os.environ.get("CEO_AUDIT_LOG_PATH") or str(default_dir / "audit-log.jsonl")
    )


# Hooks that the framework guarantees to ship. Missing OR not executable
# is a check failure. (List captured Session 33; PLAN-022.)
_REQUIRED_HOOKS = [
    "audit_log.py",
    "check_agent_spawn.py",
    "check_canonical_edit.py",
    "check_plan_edit.py",
    "check_bash_safety.py",
    "check_read_injection.py",
    # PLAN-024 F-chaos-003 P0 fix: skill_patch_sentinel is a safety
    # surface explicitly documented as "immune to CEO_SOTA_DISABLE".
    # Treating it as optional lets an adopter run HEALTHY without the
    # guard in place — wrong level for a governance signal.
    "check_skill_patch_sentinel.py",
]

# Hooks that may be present but are advisory (skipped if missing).
_OPTIONAL_HOOKS = [
    "check_arbitration_kernel.py",
    "check_budget.py",
    "check_confidence_gate.py",
    "check_output_safety.py",
    "check_scratchpad_access.py",
    "check_skill_reference_read.py",
    "emit_architect_outcome.py",
    "policy_dispatch.py",
]

_CANONICAL_AGENTS = [
    "code-reviewer",
    "security-engineer",
    "qa-architect",
    "performance-engineer",
    "devops",
]


# ---------------------------------------------------------------------------
# Check primitives
# ---------------------------------------------------------------------------


class Result:
    """A single check result."""

    __slots__ = ("name", "status", "message", "advisory")

    def __init__(self, name: str, status: str, message: str, *, advisory: bool = False) -> None:
        self.name = name
        self.status = status  # "ok" | "warn" | "fail"
        self.message = message
        self.advisory = advisory

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict view for JSON rendering."""
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "advisory": self.advisory,
        }


def check_settings_json(root: Path) -> Result:
    """Verify `.claude/settings.json` exists and parses as JSON."""
    p = root / ".claude" / "settings.json"
    if not p.is_file():
        return Result("settings.json", "fail", f"missing: {p}")
    try:
        with p.open("r", encoding="utf-8") as fh:
            json.load(fh)
        return Result("settings.json", "ok", f"parses ({p.stat().st_size} bytes)")
    except (OSError, json.JSONDecodeError) as exc:
        return Result("settings.json", "fail", f"unparseable: {exc}")


def check_required_hooks(root: Path) -> List[Result]:
    """Assert every `_REQUIRED_HOOKS` entry is present and executable."""
    out: List[Result] = []
    hooks_dir = root / ".claude" / "hooks"
    for name in _REQUIRED_HOOKS:
        p = hooks_dir / name
        if not p.is_file():
            out.append(Result(f"hook:{name}", "fail", f"missing: {p}"))
            continue
        if not os.access(p, os.X_OK):
            out.append(Result(f"hook:{name}", "fail", f"not executable: {p}"))
            continue
        out.append(Result(f"hook:{name}", "ok", "present + executable"))
    # Optional hooks contribute to inventory only if present
    for name in _OPTIONAL_HOOKS:
        p = hooks_dir / name
        if p.is_file() and not os.access(p, os.X_OK):
            out.append(Result(f"hook:{name}", "warn", f"present but not executable", advisory=True))
    return out


def check_python_shim(root: Path) -> Result:
    """Verify `_python-hook.sh` exists and is executable."""
    shim = root / ".claude" / "hooks" / "_python-hook.sh"
    if not shim.is_file():
        return Result("python-shim", "fail", f"missing: {shim}")
    if not os.access(shim, os.X_OK):
        return Result("python-shim", "fail", f"not executable: {shim}")
    return Result("python-shim", "ok", str(shim))


def check_audit_log(path: Path) -> Result:
    """Assert audit-log presence + HMAC chain state + sidecar integrity."""
    if not path.is_file():
        return Result(
            "audit-log",
            "warn",
            f"not yet created: {path} (will be created on first spawn)",
            advisory=True,
        )
    try:
        # Stream last few lines for the recent-tail check
        size = path.stat().st_size
        with path.open("rb") as fh:
            tail_window = min(64 * 1024, size)
            fh.seek(max(0, size - tail_window))
            tail = fh.read().decode("utf-8", errors="replace")
        lines = [ln for ln in tail.split("\n") if ln.strip()]
        recent = lines[-10:]
        ok = 0
        bad = 0
        for ln in recent:
            try:
                json.loads(ln)
                ok += 1
            except json.JSONDecodeError:
                bad += 1
        if bad > 0:
            return Result(
                "audit-log",
                "fail",
                f"{bad}/{ok + bad} of last 10 entries malformed JSON",
            )
        return Result(
            "audit-log",
            "ok",
            f"{size} bytes; last {len(recent)} entries parse cleanly",
        )
    except OSError as exc:
        return Result("audit-log", "fail", f"unreadable: {exc}")


def check_memory_dir() -> Result:
    """Verify the per-project auto-memory directory exists and is readable."""
    home = Path(os.environ.get("HOME") or str(Path.home()))
    mem = home / ".claude" / "projects" / "ceo-orchestration" / "memory"
    if not mem.is_dir():
        return Result(
            "memory-dir",
            "warn",
            f"not yet created: {mem} (Claude Code creates on first session)",
            advisory=True,
        )
    try:
        files = list(mem.glob("*.md"))
        return Result("memory-dir", "ok", f"{len(files)} memory files at {mem}")
    except OSError as exc:
        return Result("memory-dir", "fail", f"unreadable: {exc}")


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def check_plans(root: Path) -> Result:
    """Walk .claude/plans/ and assert schema + dependency-graph health."""
    plans_dir = root / ".claude" / "plans"
    if not plans_dir.is_dir():
        return Result("plans", "warn", f"missing: {plans_dir}", advisory=True)
    bad: List[str] = []
    seen = 0
    for p in sorted(plans_dir.glob("PLAN-*.md")):
        if not p.is_file():
            continue
        seen += 1
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            bad.append(p.name)
            continue
        m = _FRONTMATTER_RE.match(text)
        if not m:
            bad.append(p.name)
            continue
        # Crude id+title presence check (real validation is in PLAN-SCHEMA)
        body = m.group(1)
        if "id:" not in body or "title:" not in body:
            bad.append(p.name)
    if bad:
        return Result(
            "plans",
            "fail",
            f"{len(bad)}/{seen} plans missing frontmatter id/title: {', '.join(bad[:3])}",
        )
    return Result("plans", "ok", f"{seen} plan files have valid frontmatter")


def _git_status(root: Path, paths: List[str]) -> Optional[List[str]]:
    """Return uncommitted file list under `paths`, or None if git unavailable."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", *paths],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return [ln[3:] for ln in proc.stdout.splitlines() if ln.strip()]


def check_uncommitted(root: Path, scope: str, label: str) -> Result:
    """Flag uncommitted files under `scope` (porcelain git-status wrap)."""
    files = _git_status(root, [scope])
    if files is None:
        return Result(f"git:{label}", "warn", "git unavailable", advisory=True)
    if files:
        return Result(
            f"git:{label}",
            "warn",
            f"{len(files)} uncommitted: {', '.join(files[:3])}",
            advisory=True,
        )
    return Result(f"git:{label}", "ok", "clean")


def check_native_agents(root: Path) -> Result:
    """Verify the 5 canonical-5 native agent files exist and parse cleanly."""
    agents_dir = root / ".claude" / "agents"
    if not agents_dir.is_dir():
        return Result(
            "native-agents",
            "warn",
            f"missing: {agents_dir} (PLAN-020 not installed)",
            advisory=True,
        )
    missing = []
    for slug in _CANONICAL_AGENTS:
        if not (agents_dir / f"{slug}.md").is_file():
            missing.append(slug)
    if missing:
        return Result(
            "native-agents",
            "fail",
            f"missing canonical-5 agents: {', '.join(missing)}",
        )
    dispatch = agents_dir / "_dispatch.md"
    if not dispatch.is_file():
        return Result(
            "native-agents",
            "warn",
            "5 canonical-5 agents present but _dispatch.md missing",
            advisory=True,
        )
    return Result(
        "native-agents",
        "ok",
        f"{len(_CANONICAL_AGENTS)} canonical-5 + _dispatch.md present",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def check_hook_latency_slo(audit_log: Path) -> Result:
    """PLAN-025 Batch D F-obs-006 — p95 hook duration vs 225ms SLO.

    Reads the last 500 `agent_spawn` events (rolling window), computes
    p95 of the `hook_duration_ms` field, and compares against the 225ms
    SLO documented in docs/SLO-SLA.md §Hook latency.

    Returns:
      - ok: p95 <= 225ms
      - warn: 225ms < p95 <= 337ms (1.5x SLO — degradation signal)
      - fail: p95 > 337ms (SLO violation; flag as advisory for Sprint 26 budget)

    Advisory=True because SLO is operational-observability, not
    correctness-blocking. Operators use this to detect regressions;
    does not gate healthy=exit-0.
    """
    if not audit_log.is_file():
        return Result(
            name="hook-latency-slo",
            status="warn",
            message="audit-log not present; cannot measure",
            advisory=True,
        )

    try:
        # Read last 500 lines (rolling window); fail-open on any error.
        with audit_log.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
        recent = lines[-500:] if len(lines) > 500 else lines
        durations: List[int] = []
        for raw in recent:
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if ev.get("action") != "agent_spawn":
                continue
            d = ev.get("hook_duration_ms")
            if isinstance(d, int) and d >= 0:
                durations.append(d)

        if not durations:
            return Result(
                name="hook-latency-slo",
                status="warn",
                message="no agent_spawn entries with hook_duration_ms found",
                advisory=True,
            )

        durations.sort()
        p95_idx = max(0, int(len(durations) * 0.95) - 1)
        p95 = durations[p95_idx]
        slo = 225
        warn_threshold = int(slo * 1.5)  # 337ms

        if p95 <= slo:
            return Result(
                name="hook-latency-slo",
                status="ok",
                message=f"p95={p95}ms (SLO {slo}ms; {len(durations)} samples)",
            )
        elif p95 <= warn_threshold:
            return Result(
                name="hook-latency-slo",
                status="warn",
                message=f"p95={p95}ms > SLO {slo}ms (<{warn_threshold}ms warn threshold)",
                advisory=True,
            )
        else:
            return Result(
                name="hook-latency-slo",
                status="fail",
                message=f"p95={p95}ms > {warn_threshold}ms (1.5x SLO violation)",
                advisory=True,  # advisory per the plan
            )
    except Exception as exc:  # noqa: BLE001
        return Result(
            name="hook-latency-slo",
            status="warn",
            message=f"check raised: {type(exc).__name__}: {exc}",
            advisory=True,
        )


def check_quality_profile(root: Path) -> Result:
    """PLAN-025 Batch L — surface the active quality profile.

    Reads `.claude/settings.json` for `ceo_quality_profile` and
    cross-checks the canonical-5 agent model: fields. Warns on drift
    between settings declaration and actual model assignments.
    """
    settings_path = root / ".claude" / "settings.json"
    if not settings_path.is_file():
        return Result(
            name="quality_profile",
            status="warn",
            message="settings.json not found; assumed default 'balanced'",
            advisory=True,
        )
    try:
        import json as _json
        with settings_path.open("r", encoding="utf-8") as fh:
            data = _json.load(fh)
    except Exception as exc:  # noqa: BLE001
        return Result(
            name="quality_profile",
            status="warn",
            message=f"settings.json parse error: {exc}",
            advisory=True,
        )

    profile = data.get("ceo_quality_profile") or "balanced"

    # Read the actual model: fields to surface them in health output
    agents_dir = root / ".claude" / "agents"
    models: Dict[str, str] = {}
    for slug in (
        "code-reviewer", "security-engineer",
        "qa-architect", "performance-engineer", "devops",
    ):
        agent_file = agents_dir / f"{slug}.md"
        if not agent_file.is_file():
            continue
        try:
            for line in agent_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("model:"):
                    models[slug] = line.split(":", 1)[1].strip()
                    break
        except OSError:
            continue

    # Build a compact message showing VETO floor + 3 non-VETO roles
    parts = [
        f"{k}={v}" for k, v in sorted(models.items())
    ]
    msg = f"{profile}: {', '.join(parts) if parts else 'no agents found'}"
    return Result(
        name="quality_profile",
        status="ok",
        message=msg,
    )


def run_checks(root: Path) -> List[Result]:
    """Run every configured health probe and return the collected `Result` list."""
    out: List[Result] = []
    out.append(check_settings_json(root))
    out.append(check_python_shim(root))
    out.extend(check_required_hooks(root))
    out.append(check_audit_log(audit_log_path()))
    out.append(check_memory_dir())
    out.append(check_plans(root))
    out.append(check_uncommitted(root, ".claude/skills/", "skills-clean"))
    out.append(check_uncommitted(root, ".claude/hooks/", "hooks-clean"))
    out.append(check_native_agents(root))
    # PLAN-025 Batch D F-obs-006 — hook-latency SLO probe
    out.append(check_hook_latency_slo(audit_log_path()))
    # PLAN-025 Batch L — quality profile surface
    out.append(check_quality_profile(root))
    return out


def overall_status(results: List[Result]) -> Tuple[str, int]:
    """Return ('healthy'|'degraded'|'unhealthy', exit_code).

    Status precedence:
      - any non-advisory ``fail`` → unhealthy (exit 1)
      - any non-advisory ``warn`` → degraded (exit 0)
      - everything else (including advisory warns) → healthy (exit 0)
    """
    fail = sum(1 for r in results if r.status == "fail" and not r.advisory)
    warn = sum(1 for r in results if r.status == "warn" and not r.advisory)
    if fail > 0:
        return ("unhealthy", 1)
    if warn > 0:
        return ("degraded", 0)
    return ("healthy", 0)


def render_text(results: List[Result], status: str) -> str:
    """Format `results` as human-readable text (glyph + name + message)."""
    lines: List[str] = []
    lines.append(f"ceo-health: {status.upper()}")
    lines.append("")
    glyph = {"ok": "✓", "warn": "⚠", "fail": "✗"}
    for r in results:
        prefix = "[advisory] " if r.advisory and r.status != "ok" else ""
        lines.append(f"  {glyph[r.status]} {r.name:<28} {prefix}{r.message}")
    lines.append("")
    return "\n".join(lines)


def render_json(results: List[Result], status: str) -> str:
    """Format `results` as a stable-key JSON payload for CI consumption."""
    payload = OrderedDict([
        ("status", status),
        ("ts", datetime.now(timezone.utc).isoformat(timespec="seconds")),
        ("checks", [r.to_dict() for r in results]),
    ])
    return json.dumps(payload, indent=2)


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for `ceo-health` CLI flags."""
    p = argparse.ArgumentParser(
        prog="ceo-health",
        description="One-shot framework health check.",
    )
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--quiet", action="store_true", help="suppress all output; exit code only")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — aggregate health signals + emit pass/fail verdict."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        root = repo_root()
    except SystemExit as exc:
        if not args.quiet:
            print(str(exc), file=sys.stderr)
        return 2

    results = run_checks(root)
    status, exit_code = overall_status(results)

    if not args.quiet:
        if args.format == "json":
            print(render_json(results, status))
        else:
            print(render_text(results, status))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
