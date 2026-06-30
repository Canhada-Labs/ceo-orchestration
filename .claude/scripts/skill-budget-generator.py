#!/usr/bin/env python3
"""skill-budget-generator.py — PLAN-135 W1 S7: skill-listing budget recommender.

Recommends a `skillListingBudgetFraction` + a name-only `skillOverrides`
map for RARE DOMAIN-TIER skills (0 dispatches in the window), so the
fixed per-session skill-listing context tax is spent on the skills that
actually fire. Core/frontend-tier skills are NEVER demoted.

Knob reality (Doctrine 3 probe, Claude Code CLI 2.1.176 binary, S231):
- `skillListingBudgetFraction`: number().gt(0).lte(1).optional() —
  "Fraction of the context window (in characters) reserved for the skill
  listing sent to Claude (default: 0.01 = 1%)."
  Internally: budget_chars = context_window_tokens(200000) *
  chars_per_token(4) * fraction  → 8000 chars at the 0.01 default.
- `skillOverrides`: record(skillName, enum["on","name-only",
  "user-invocable-only","off"]) — '"name-only" lists the skill without
  its description'.
- `skillListingMaxDescChars` default: 1536 (per-skill desc cap).

Inputs:
- Skill inventory: the skills tree itself (`.claude/skills/`), the same
  source `generate-skill-inventory.sh` reads. Tiers:
    core/<name>/SKILL.md            → core      (never demoted)
    frontend/<name>/SKILL.md        → frontend  (never demoted)
    domains/<d>/skills/<name>/SKILL.md → domain (demotable)
    domains/<d>/<name>/SKILL.md        → domain (legacy layout, demotable)
- Dispatch counts: the audit JSONL, resolved the way audit-query.py does
  (`CEO_AUDIT_LOG_PATH` env or `$HOME/.claude/projects/ceo-orchestration/
  audit-log.jsonl`, + rotated `audit-log*.jsonl` siblings). A dispatch =
  any entry whose `skill` field (audit-query `by-skill` semantics; set by
  audit_log.py extract_skill on agent_spawn) or `skill_slug` field
  (skill_patch_applied) names the skill. FAIL-SOFT: a missing/unreadable
  log yields zero counts (stderr breadcrumb + `"fail_soft": true` in the
  report) — the tool never exits non-zero for absent telemetry.

Modes:
  --json          full machine-readable report (default)
  --jq-fragment   idempotent jq merge body for settings.json targets
                  (PLAN-135 staged-merge convention: NN-<unit>-<slug>.jq)

Advisory only: output is embedded into staged merge fragments and applied
at the Owner ceremony; this script never writes settings files itself.

Stdlib-only. Python >= 3.9. NO third-party deps.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants probed from the Claude Code CLI binary (2.1.176, S231 probe).
# These are ESTIMATION inputs only — the CLI owns the real arithmetic.
# ---------------------------------------------------------------------------
CLI_DEFAULT_FRACTION = 0.01  # pT3 in the 2.1.176 bundle
CLI_DEFAULT_MAX_DESC_CHARS = 1536  # UT3
CLI_DEFAULT_CONTEXT_WINDOW_TOKENS = 200000  # BT3
CLI_DEFAULT_CHARS_PER_TOKEN = 4  # jL7
CLI_VERSION_PROBED = "2.1.176"

# Recommendation ladder: never ABOVE the CLI default — this unit reduces
# the context tax, it does not raise it. Smallest fraction whose char
# budget still fits the post-override listing estimate wins.
FRACTION_LADDER = (0.005, 0.0075, 0.01)

# Rough per-entry formatting overhead (separators, bullets) for the
# listing-size estimate. Deliberately conservative (over-estimates size).
ENTRY_OVERHEAD_CHARS = 16

PROVENANCE = "PLAN-135 W1 S7 — .claude/scripts/skill-budget-generator.py"


# ---------------------------------------------------------------------------
# Path resolution (mirrors audit-query.py conventions)
# ---------------------------------------------------------------------------


def default_log_path() -> Path:
    """Audit log path: CEO_AUDIT_LOG_PATH env or the conventional default."""
    home = Path(os.environ.get("HOME") or str(Path.home()))
    default_dir = home / ".claude" / "projects" / "ceo-orchestration"
    return Path(
        os.environ.get("CEO_AUDIT_LOG_PATH") or str(default_dir / "audit-log.jsonl")
    )


def discover_logs(primary: Path, include_rotated: bool) -> List[Path]:
    """Log files to read, oldest first (mirrors audit-query.discover_logs)."""
    if not include_rotated:
        return [primary] if primary.is_file() else []
    if not primary.parent.is_dir():
        return []
    stem = primary.stem  # "audit-log"
    siblings = []
    for candidate in primary.parent.glob(f"{stem}*.jsonl"):
        if candidate.is_file():
            siblings.append(candidate)
    siblings.sort(key=lambda p: p.stat().st_mtime)
    return siblings


def default_repo_root() -> Path:
    """CLAUDE_PROJECT_DIR env, else two levels above this script."""
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Skill inventory (the skills tree is the source generate-skill-inventory.sh
# reads; the SKILL.md auto-generated block is derived FROM it)
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
_DESC_RE = re.compile(
    r"^description:\s*(.*?)(?=^\w[\w_-]*:|\Z)", re.DOTALL | re.MULTILINE
)
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(skill_md: Path) -> Tuple[str, str]:
    """Return (name, description) from a SKILL.md frontmatter; fail-soft."""
    try:
        content = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", ""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return "", ""
    fm = m.group(1)
    name = ""
    nm = _NAME_RE.search(fm)
    if nm:
        name = nm.group(1).strip().strip("\"'")
    desc = ""
    dm = _DESC_RE.search(fm)
    if dm:
        desc = " ".join(dm.group(1).split())
    return name, desc


def load_inventory(repo_root: Path) -> List[Dict[str, Any]]:
    """Walk the skills tree; return [{name, dir_name, tier, domain, desc_len}]."""
    skills_root = repo_root / ".claude" / "skills"
    out: List[Dict[str, Any]] = []
    if not skills_root.is_dir():
        return out
    seen: set = set()

    def add(skill_md: Path, tier: str, domain: Optional[str]) -> None:
        resolved = str(skill_md)
        if resolved in seen:
            return
        seen.add(resolved)
        dir_name = skill_md.parent.name
        name, desc = _parse_frontmatter(skill_md)
        out.append(
            {
                "name": name or dir_name,
                "dir_name": dir_name,
                "tier": tier,
                "domain": domain,
                "desc_len": len(desc),
            }
        )

    for tier in ("core", "frontend"):
        tier_dir = skills_root / tier
        if tier_dir.is_dir():
            for skill_md in sorted(tier_dir.glob("*/SKILL.md")):
                add(skill_md, tier, None)

    domains_dir = skills_root / "domains"
    if domains_dir.is_dir():
        # Canonical layout: domains/<d>/skills/<name>/SKILL.md
        for skill_md in sorted(domains_dir.glob("*/skills/*/SKILL.md")):
            add(skill_md, "domain", skill_md.parents[2].name)
        # Legacy/flat layout: domains/<d>/<name>/SKILL.md
        for skill_md in sorted(domains_dir.glob("*/*/SKILL.md")):
            if skill_md.parent.name == "skills":
                continue
            add(skill_md, "domain", skill_md.parents[1].name)

    out.sort(key=lambda s: (s["tier"], s["name"]))
    return out


# ---------------------------------------------------------------------------
# Dispatch counts (streamed, fail-soft — audit-query.py read semantics)
# ---------------------------------------------------------------------------


def _parse_ts(ts: str) -> Optional[datetime]:
    """Parse an audit-log `ts` (e.g. 2026-06-13T00:44:40Z); None on failure."""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_entries(paths: Iterable[Path]) -> Iterator[Dict[str, Any]]:
    """Yield parsed JSON entries; malformed lines skipped with a breadcrumb."""
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(entry, dict):
                        yield entry
        except OSError as e:
            sys.stderr.write(
                f"[skill-budget-generator] WARN: cannot read {path}: {e}\n"
            )


def count_dispatches(
    log_paths: List[Path], window_days: int
) -> Tuple[Dict[str, int], Dict[str, Any]]:
    """Count skill dispatches per skill name from the audit JSONL.

    A dispatch = entry with a truthy `skill` field != "unknown"
    (audit-query `by-skill` semantics) or a truthy `skill_slug` field.
    Entries with an unparseable/missing `ts` are COUNTED even when a
    window is set (conservative: bad telemetry never demotes a skill).
    """
    counts: Dict[str, int] = {}
    meta: Dict[str, Any] = {
        "files_read": [str(p) for p in log_paths],
        "found": bool(log_paths),
        "entries_scanned": 0,
        "dispatch_entries": 0,
        "window_days": window_days,
        "fail_soft": not log_paths,
    }
    if not log_paths:
        sys.stderr.write(
            "[skill-budget-generator] NOTE: audit log not found — "
            "FAIL-SOFT to zero dispatch counts (every domain-tier skill "
            "will look rare; see --audit-log / CEO_AUDIT_LOG_PATH).\n"
        )
        return counts, meta

    cutoff: Optional[datetime] = None
    if window_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    for entry in read_entries(log_paths):
        meta["entries_scanned"] += 1
        if cutoff is not None:
            ts = _parse_ts(entry.get("ts", ""))
            if ts is not None and ts < cutoff:
                continue
        hit = False
        for field in ("skill", "skill_slug"):
            value = entry.get(field)
            if isinstance(value, str):
                value = value.strip()
                if value and value != "unknown":
                    counts[value] = counts.get(value, 0) + 1
                    hit = True
        if hit:
            meta["dispatch_entries"] += 1
    return counts, meta


def dispatches_for(skill: Dict[str, Any], counts: Dict[str, int]) -> int:
    """Dispatch count for a skill: frontmatter name + dir name spellings."""
    total = counts.get(skill["name"], 0)
    if skill["dir_name"] != skill["name"]:
        total += counts.get(skill["dir_name"], 0)
    return total


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


def estimate_listing_chars(
    inventory: List[Dict[str, Any]],
    overrides: Dict[str, str],
    max_desc_chars: int,
) -> Tuple[int, int]:
    """Return (full_listing_chars, post_override_listing_chars) estimates."""
    full = 0
    post = 0
    for skill in inventory:
        name_cost = len(skill["name"]) + ENTRY_OVERHEAD_CHARS
        desc_cost = min(skill["desc_len"], max_desc_chars)
        full += name_cost + desc_cost
        if (
            overrides.get(skill["name"]) == "name-only"
            or overrides.get(skill["dir_name"]) == "name-only"
        ):
            post += name_cost
        else:
            post += name_cost + desc_cost
    return full, post


def recommend(
    inventory: List[Dict[str, Any]],
    counts: Dict[str, int],
    *,
    min_dispatches: int,
    max_desc_chars: int,
    context_window_tokens: int,
    chars_per_token: int,
) -> Dict[str, Any]:
    """Build the recommendation: overrides map + budget fraction.

    Override keys: `skillOverrides` is indexed by the LOADED skill's name
    (CLI 2.1.176: `skillOverrides?.[skill.name]`). When a skill's
    frontmatter `name` differs from its directory name, BOTH spellings are
    emitted (an unmatched key is a harmless no-op) — EXCEPT any spelling
    that collides with a core/frontend skill's name or dir name, which is
    suppressed so a demotion key can never reach a protected-tier skill
    (e.g. fintech `frontend-patterns/` dir vs the frontend-tier skill
    named `frontend-patterns`).
    """
    protected: set = set()
    for skill in inventory:
        if skill["tier"] in ("core", "frontend"):
            protected.add(skill["name"])
            protected.add(skill["dir_name"])

    overrides: Dict[str, str] = {}
    demoted = 0
    collisions_skipped: List[str] = []
    for skill in inventory:
        if skill["tier"] != "domain":
            continue  # NEVER demote core/frontend
        if dispatches_for(skill, counts) >= min_dispatches:
            continue
        demoted += 1
        for key in {skill["name"], skill["dir_name"]}:
            if key in protected:
                collisions_skipped.append(key)
            else:
                overrides[key] = "name-only"

    full_chars, post_chars = estimate_listing_chars(
        inventory, overrides, max_desc_chars
    )
    window_chars = context_window_tokens * chars_per_token

    fraction = CLI_DEFAULT_FRACTION
    fits = False
    for candidate in FRACTION_LADDER:
        if post_chars <= int(window_chars * candidate):
            fraction = candidate
            fits = True
            break

    if fits:
        rationale = (
            f"smallest ladder fraction whose char budget "
            f"({int(window_chars * fraction)}) fits the post-override "
            f"listing estimate ({post_chars} chars)"
        )
    else:
        rationale = (
            f"post-override listing estimate ({post_chars} chars) exceeds "
            f"every ladder budget — keep the CLI default "
            f"{CLI_DEFAULT_FRACTION} (never raised above default; the CLI "
            f"shortens descriptions to fit and the name-only overrides "
            f"decide WHO keeps theirs)"
        )

    return {
        "skillListingBudgetFraction": fraction,
        "skillOverrides": dict(sorted(overrides.items())),
        "demoted_domain_skills": demoted,
        "override_keys": len(overrides),
        "protected_collisions_skipped": sorted(set(collisions_skipped)),
        "fits_at_recommended": fits,
        "rationale": rationale,
        "estimates": {
            "full_listing_chars": full_chars,
            "post_override_listing_chars": post_chars,
            "budget_chars_at_recommended": int(window_chars * fraction),
            "budget_chars_at_cli_default": int(
                window_chars * CLI_DEFAULT_FRACTION
            ),
        },
    }


# ---------------------------------------------------------------------------
# Output modes
# ---------------------------------------------------------------------------


def build_report(
    repo_root: Path,
    inventory: List[Dict[str, Any]],
    counts: Dict[str, int],
    audit_meta: Dict[str, Any],
    rec: Dict[str, Any],
) -> Dict[str, Any]:
    tiers = {"core": 0, "frontend": 0, "domain": 0}
    for skill in inventory:
        tiers[skill["tier"]] = tiers.get(skill["tier"], 0) + 1
    dispatched_domain = sorted(
        s["name"]
        for s in inventory
        if s["tier"] == "domain" and dispatches_for(s, counts) > 0
    )
    return {
        "provenance": PROVENANCE,
        "cli_probe": {
            "version_probed": CLI_VERSION_PROBED,
            "defaults": {
                "skillListingBudgetFraction": CLI_DEFAULT_FRACTION,
                "skillListingMaxDescChars": CLI_DEFAULT_MAX_DESC_CHARS,
                "context_window_tokens": CLI_DEFAULT_CONTEXT_WINDOW_TOKENS,
                "chars_per_token": CLI_DEFAULT_CHARS_PER_TOKEN,
            },
        },
        "inventory": {
            "skills_root": str(repo_root / ".claude" / "skills"),
            "total": len(inventory),
            "core": tiers["core"],
            "frontend": tiers["frontend"],
            "domain": tiers["domain"],
        },
        "audit_log": audit_meta,
        "dispatched_domain_skills": dispatched_domain,
        "recommendation": rec,
    }


def emit_jq_fragment(rec: Dict[str, Any]) -> str:
    """Idempotent jq merge body (PLAN-135 staged-merge convention).

    - `skillListingBudgetFraction` is set unconditionally (data change).
    - `skillOverrides` MERGES into any pre-existing map: operator-added
      entries for other skills are preserved; generated entries win for
      the skills they name (re-running the merge is a no-op).
    """
    fraction = rec["skillListingBudgetFraction"]
    overrides = rec["skillOverrides"]
    lines = [
        "# PLAN-135 W1 S7 — skill-listing budget (generated by",
        "#   python3 .claude/scripts/skill-budget-generator.py --jq-fragment ).",
        "# Idempotent: re-applying yields the same document. Apply with:",
        "#   jq -f <this file> <target> > tmp && mv tmp <target>",
        f"# skillListingBudgetFraction {fraction} == CLI default kept explicit;"
        if fraction == CLI_DEFAULT_FRACTION
        else f"# skillListingBudgetFraction {fraction} (below CLI default 0.01);",
        f"# {rec.get('demoted_domain_skills', len(overrides))} domain-tier "
        f"skills demoted to name-only via {len(overrides)} override keys"
        " (0 dispatches in window; both name+dir spellings where they"
        " differ; core/frontend never demoted, collisions suppressed).",
        ". + {",
        '  "_skill_budget_comment": "PLAN-135 W1 S7: skillListingBudgetFraction'
        " caps the skill-listing context tax (fraction of context window in"
        " chars; CLI default 0.01 = 8000 chars at a 200k window);"
        " skillOverrides name-only demotes 0-dispatch domain-tier skills."
        " Regenerate: python3 .claude/scripts/skill-budget-generator.py"
        ' --jq-fragment",',
        f'  "skillListingBudgetFraction": {json.dumps(fraction)},',
        '  "skillOverrides": ((.skillOverrides // {}) + {',
    ]
    items = sorted(overrides.items())
    for i, (name, mode) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        lines.append(f"    {json.dumps(name)}: {json.dumps(mode)}{comma}")
    lines.append("  })")
    lines.append("}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skill-budget-generator.py",
        description=(
            "Recommend skillListingBudgetFraction + name-only skillOverrides "
            "for rare domain-tier skills (PLAN-135 W1 S7)."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--json", action="store_true", help="full JSON report (default)"
    )
    mode.add_argument(
        "--jq-fragment",
        action="store_true",
        help="emit the idempotent jq merge body for a settings.json target",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="framework repo root (default: CLAUDE_PROJECT_DIR or derived)",
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=None,
        help="audit-log.jsonl path (default: CEO_AUDIT_LOG_PATH or ~)",
    )
    parser.add_argument(
        "--no-rotated",
        action="store_true",
        help="read only the primary log, not rotated audit-log*.jsonl siblings",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=0,
        help="dispatch-count window in days (0 = all available history)",
    )
    parser.add_argument(
        "--min-dispatches",
        type=int,
        default=1,
        help="domain skills below this count are demoted (default 1 → 0-dispatch)",
    )
    parser.add_argument(
        "--max-desc-chars",
        type=int,
        default=CLI_DEFAULT_MAX_DESC_CHARS,
        help="per-skill description cap used for the size estimate",
    )
    parser.add_argument(
        "--context-window-tokens",
        type=int,
        default=CLI_DEFAULT_CONTEXT_WINDOW_TOKENS,
        help="assumed context window tokens for the budget estimate",
    )
    parser.add_argument(
        "--chars-per-token",
        type=int,
        default=CLI_DEFAULT_CHARS_PER_TOKEN,
        help="assumed chars-per-token for the budget estimate",
    )
    args = parser.parse_args(argv)

    repo_root = (args.repo_root or default_repo_root()).resolve()
    primary = args.audit_log or default_log_path()
    log_paths = discover_logs(primary, include_rotated=not args.no_rotated)

    inventory = load_inventory(repo_root)
    if not inventory:
        sys.stderr.write(
            f"[skill-budget-generator] NOTE: no skills found under "
            f"{repo_root / '.claude' / 'skills'} — empty recommendation.\n"
        )
    counts, audit_meta = count_dispatches(log_paths, args.window_days)
    audit_meta["primary"] = str(primary)

    rec = recommend(
        inventory,
        counts,
        min_dispatches=args.min_dispatches,
        max_desc_chars=args.max_desc_chars,
        context_window_tokens=args.context_window_tokens,
        chars_per_token=args.chars_per_token,
    )

    if args.jq_fragment:
        sys.stdout.write(emit_jq_fragment(rec))
    else:
        report = build_report(repo_root, inventory, counts, audit_meta, rec)
        json.dump(report, sys.stdout, indent=2, sort_keys=False)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
