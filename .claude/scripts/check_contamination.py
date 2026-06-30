#!/usr/bin/env python3
"""check_contamination.py — detect project-specific references outside allowlist.

Sprint 3 Item E.2. Port of check-contamination.sh to Python, using the
shared _lib.file_walker.FileWalker. Per debate consensus R-VP2, the
bash script remains as a thin wrapper that invokes this module so
Sprint 4+ can retire the wrapper cleanly.

## What it detects

NFKC-normalized regex match against a hardcoded pattern:

    acme\\s*[Ll]edger | example[\\s._\\-]*owner | Example\\s+Owner
      | [Jj]oao[\\s._\\-]*[Cc]anhada | Jo[aã]o

The first three alternatives are EXAMPLE placeholders for an adopter's
own project name / handle (replace them when forking — see `_PATTERN`).
The last two defend the framework's own published core against leaking
the maintainer's real identity ("João" / "joao canhada") into shipped
surfaces (e.g. `.claude/skills/core/`). Without them the guard is a
false-green: it exits 0 even when the real name is provably present in
non-allowlisted, shipped files.

Files matching the pattern outside the allowlist fail the check.

## Allowlist

Exact paths + glob patterns (see `_ALLOWLIST_*` below). Binary file
suffixes are excluded by extension.

## Exit codes

- 0 — clean
- 1 — contamination found (printed to stdout)
- 2 — fatal error
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path
from typing import List

# Import the shared walker from _lib/
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.file_walker import FileWalker  # noqa: E402


# Identity tokens that must not leak into the distributed framework core.
#
# Two groups of alternatives:
#   1. EXAMPLE placeholders (acme ledger / example owner) — a maintainer
#      publishing their own fork should replace these with their personal
#      handle / private project names so this lint guards their identity
#      instead of the example ones.
#   2. The maintainer's REAL identity ([Jj]oao[\s._\-]*[Cc]anhada and the
#      bare first name Jo[aã]o) — these defend THIS framework's published
#      core (e.g. .claude/skills/core/) against shipping the real name.
#      They were dropped from the live pattern at some point while the
#      docstring still advertised them, turning the guard false-green
#      (it exited 0 while "João" was provably present in non-allowlisted
#      shipped files). Restored here so the guard actually fails-closed.
#      The bare Jo[aã]o alternative is intentionally case-sensitive
#      (capital J + a/ã + o) so it catches the proper noun ("João",
#      "Joao") without over-matching common lowercase substrings.
_PATTERN = re.compile(
    r"acme\s*[Ll]edger|example[\s._\-]*owner|Example\s+Owner"
    r"|[Jj]oao[\s._\-]*[Cc]anhada|Jo[aã]o"
)

# Allowlist — mirrors the case block in check-contamination.sh
#
# Philosophy: the check defends the FRAMEWORK CORE (hooks, scripts,
# skills/core, skills/frontend, templates) from leaking project-specific
# references. It does NOT apply to:
#   - Historical decision records (ADRs carry Accepted-By owner handles)
#   - Plan artifacts (PLAN-*/ subfolders document adopter context)
#   - Adopter-facing documentation (docs/ explains framework to adopters)
#   - Adopter-specific tooling (check-originator-residue, compare-adopters,
#     adopter-metrics, log-friction — explicitly about adopter workflow)
#   - Published compliance contract (SPEC/v1/ references concrete examples)
#   - Benchmarks against named peers (benchmarks/public/vs-*.md)
#   - Case studies (docs/case-studies/ inherits adopter names by design)
#   - Issue templates (.github/ISSUE_TEMPLATE surfaces project context)
#   - Historical archives (CLAUDE_FULL.md is the overflow-log for CLAUDE.md)
_ALLOWLIST_EXACT = {
    "LICENSE",
    "CHANGELOG.md",
    # ---- S214: audit report + plugin builder reference identity tokens by-design ----
    "MORNING-REPORT-S214.md",   # CTO audit report that AUDITS the Owner-identity leak (must name the tokens)
    "REPORT-S225-fable-audit.md",  # S225 Fable audit: documents identity-leak findings (E5-F10, E7) — same rationale as MORNING-REPORT-S214
    "scripts/build-plugin.py",  # plugin builder: sanitize_paths()/identity_report() match these tokens to strip/report them (same rationale as check_contamination.py itself)
    ".github/workflows/validate.yml",
    ".github/CODEOWNERS",
    ".claude/scripts/check-contamination.sh",
    ".claude/scripts/check_contamination.py",
    ".claude/scripts/tests/test_check_contamination.py",
    ".claude/hooks/tests/test_check_canonical_edit.py",
    "CLAUDE.md",
    "CLAUDE_FULL.md",
    "RELEASE.md",
    "SECURITY.md",
    "docs/QUICKSTART.md",
    "docs/QUICKSTART.pt-BR.md",
    "docs/GUIA-COMPLETO.md",
    "docs/GUIA-COMPLETO.pt-BR.md",
    "docs/HONEST-LIMITATIONS.md",
    "docs/ROADMAP-CLOSURE.md",
    "docs/threat-model.md",
    "docs/soc2-audit-mapping.md",
    "docs/fixture-budget.md",
    "docs/opus-4-7-baseline.md",
    "docs/opus-4-7-operations.md",
    "docs/opus-4-7-phase6-report.md",
    "docs/UPGRADE-PROCEDURE.md",
    "docs/SLO-SLA.md",
    ".claude/scripts/check-framework-updates.sh",
    ".claude/scripts/adopter-metrics.py",
    ".claude/scripts/compare-adopters.py",
    ".claude/scripts/check-originator-residue.py",
    ".claude/scripts/log-friction.sh",
    ".claude/scripts/tests/test_admin_invite.py",
    ".claude/scripts/tests/test_check_originator_residue.py",
    ".claude/scripts/tests/test_compare_adopters.py",
    ".claude/policies/.drift-manifest.json",
    # ---- audit-v2 Wave C-bis hot-fix (2026-04-27) ------------------
    # Pre-existing legitimate references to the Owner / canonical
    # repo URL surfaced after CLAUDE.md ADR-count drift was fixed
    # (which was masking these in CI). Each entry below is a
    # human-reviewed legitimate reference (Owner attribution in
    # ceremony scripts, GPG roster, design-intent github URLs, etc).
    # ----------------------------------------------------------------
    # Hook-lib files with Owner attribution in docstrings (canonical;
    # fix would require new sentinel ceremony — defer to future cleanup
    # ADR; allowlist now to unblock CI):
    ".claude/hooks/_lib/escalation_signals.py",
    ".claude/hooks/_lib/rag_events.py",
    ".claude/hooks/check_tier_policy.py",
    # Owner GPG fingerprint roster (by design — references Owner's key):
    ".claude/sentinel-signers.txt",
    ".claude/skill-patch-signers.txt",
    # Operational docs with design-intent github.com/<owner>/ URLs
    # (issue tracker, release page, etc.):
    "docs/READINESS-STATUS.md",
    "docs/CEO-MODEL-ROUTING.md",
    "docs/ROADMAP.md",
    "docs/SP-NNN-OWNER-WORKFLOW.md",
    "docs/rotation-log.md",
    "docs/SECURITY.md",
    # Detector test fixtures reference Owner repo paths in mock-event
    # bodies (legitimate test data):
    ".claude/scripts/detectors/tests/fixtures.py",
    # SBOM generator hard-codes upstream URL (single source of truth):
    ".claude/scripts/generate-sbom.py",
    # ---- S155 CI-cleanup (2026-05-22) ------------------------------
    # Same pattern as the 2026-04-27 batch above: pre-existing legitimate
    # Owner / canonical-repo references that were masked in CI by the
    # contract/ADR-count/perf red layers, surfaced once those were fixed.
    # Each is human-reviewed: non-template-content (not shipped to adopters)
    # OR a canonical-repo reference OR a detector test fixture. NOT personal
    # contamination in shipped template content.
    # ----------------------------------------------------------------
    # LLM03 supply-chain detector treats the framework's CANONICAL repo
    # (github.com/<owner>/) as trusted alongside github.com/anthropics/ —
    # adopters clone framework updates from it (canonical-repo reference):
    ".claude/hooks/_lib/output_scan.py",
    # Detector / canonical-edit / mcp-guard test fixtures carry Owner repo
    # paths in mock-event bodies as legitimate test data (same rationale as
    # detectors/tests/fixtures.py + replay/tests/* below):
    ".claude/hooks/tests/test_check_canonical_edit_markers.py",
    ".claude/hooks/tests/test_check_canonical_edit_mcp.py",
    ".claude/hooks/tests/test_mcp_canonical_guard.py",
    ".claude/scripts/tests/test_success_receipt.py",
    "tests/test_output_scan_llm03.py",
    # GPG sentinel-signer roster — references Owner key by design (like
    # sentinel-signers.txt / skill-patch-signers.txt above):
    ".claude/security/sentinel-signers-registry.yaml",
    # Owner brief + internal design docs (Owner attribution / setup paths;
    # like the operational docs allowlisted above):
    "BUNDLE-OWNER-BRIEF.md",
    "docs/GIF-CAPTURE-SPEC.md",
    "docs/PERMISSION-MODEL-DESIGN.md",
    "docs/security-bash-canonical-guards.md",
}

_ALLOWLIST_GLOBS = {
    # NOTE: fnmatch `*` matches across `/` boundaries here (unlike the
    # `glob` module). A single `*` after the directory prefix is enough
    # to cover all nested files — no need for `**`.
    # Plan artifacts (all file types under .claude/plans/, including
    # WAR-ROOM/, SPRINT-NN-ROADMAP.md, PLAN-NNN-*.md, PLAN-NNN/...).
    # Wave C-bis (2026-04-27): broadened from `PLAN-*.md` + `PLAN-*`
    # to `*` so non-PLAN- artifacts (WAR-ROOM, SPRINT-NN, README) get
    # covered without per-file additions.
    ".claude/plans/*",
    # Domain squads (by design — each domain lists real-world owners)
    ".claude/skills/domains/*",
    # CI workflow templates distributed to adopters
    "templates/.github/workflows/*",
    # NPM shim — URLs reference canonical repo owner
    "npm/*",
    # ADRs — architectural decision records carry Owner Accepted-By
    ".claude/adr/ADR-*.md",
    # Published SPEC — concrete examples reference owner/projects
    "SPEC/*",
    # Docs subfolders that document the framework's ecosystem:
    # case studies, research (external competitive analysis),
    # site HTML, etc.
    "docs/case-studies/*",
    "docs/research/*",
    "docs/site/*",
    # Benchmarks against named peers
    "benchmarks/*",
    # Issue templates
    ".github/ISSUE_TEMPLATE/*",
    # Owner ceremony archive (Wave C moved 17 OWNER-*.sh here; each
    # script references Owner's GPG key + project paths by design):
    ".claude/scripts/owner-ceremony/*",
    # Forensic ceremony archive — historical Owner ceremony scripts
    # retained for chain-of-custody. Never re-executed. PLAN-063 S5.
    "scripts/local/historical/*",
    # Architect ceremony sentinels — GPG-signed `approved.md` per round
    # MUST carry Owner handle + key fingerprint by design (the sentinel IS
    # the canonical Owner authorization artifact). PLAN-072 + PLAN-069 Wave D
    # surfaced this as latent debt (S81 2026-05-03).
    ".claude/architect/*",
    # Replay redaction test corpus — fixtures + tests in
    # .claude/scripts/replay/tests/ MUST contain `/Users/devuser/` and
    # similar OS-path shapes because they are the regression markers proving
    # the redactor strips them. Removing the literals defeats the test.
    # PLAN-069 Phase 1 Wave A+B canonical test surface (S81 2026-05-03).
    ".claude/scripts/replay/tests/*",
    # ---- S155 CI-cleanup (2026-05-22) — non-template-content zones ----
    # Owner-run ceremony / restart tooling at repo root + scripts/local/ +
    # the .claude mirror. Reference Owner path/key by design; never shipped
    # to adopters (extends the existing scripts/local/historical/* +
    # owner-ceremony/* allowlist):
    "scripts/local/*",
    ".claude/scripts/local/*",
    "OWNER-*.sh",
    # Historical Owner-ceremony archive at repo root (archive/): retired
    # ceremony scripts (OWNER-*-CEREMONY.sh) + the Owner bundle brief moved
    # here for chain-of-custody. Each references the Owner path / @handle /
    # GPG key by design; never re-executed, never shipped to adopters
    # (extends owner-ceremony/* + scripts/local/historical/*). S165 CI-green.
    "archive/*",
    # Detector test corpora — ATLAS + red-team fixtures MUST carry realistic
    # /Users/<owner>/ + canonical-repo-URL shapes because they are the
    # regression markers proving the LLM03 supply-chain + secret/path
    # detectors fire (same rationale as .claude/scripts/replay/tests/*):
    "tests/fixtures/atlas/*",
    "tests/fixtures/red-team-corpus/*",
}

# Suffixes to skip (binary / non-text files)
_SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".pdf", ".ico", ".zip",
}


def scan(repo_root: Path) -> List[Path]:
    """Return list of files where the pattern matched, excluding allowlist."""
    walker = FileWalker(
        repo_root=repo_root,
        mode="git",
        path_allowlist_exact=_ALLOWLIST_EXACT,
        path_allowlist_globs=_ALLOWLIST_GLOBS,
    )

    violations: List[Path] = []
    for path in walker.iter_files():
        # Skip binaries by suffix
        if path.suffix.lower() in _SKIP_SUFFIXES:
            continue
        if walker.is_allowlisted(path):
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        normalized = unicodedata.normalize("NFKC", text)
        if _PATTERN.search(normalized):
            violations.append(path)
    return violations


def main() -> int:
    """CLI entrypoint — scan templates for originator-repo contamination."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    if not (repo_root / ".git").exists() and not (repo_root / ".git").is_dir():
        # Not a git repo — exit 2
        print("FATAL: not inside a git repo", file=sys.stderr)
        return 2

    violations = scan(repo_root)
    if not violations:
        print("✓ No contamination outside allowed zones")
        return 0

    print("❌ Contamination found in the following files:")
    for v in violations:
        rel = v.relative_to(repo_root)
        print(f"  - {rel}")
    print("")
    print("Allowed zones:")
    print("  - LICENSE")
    print("  - CHANGELOG.md")
    print("  - .claude/skills/domains/**")
    print("  - .claude/plans/PLAN-*.md (all plan files)")
    print("  - npm/** (NPM shim — uses owner handle in URLs)")
    print("  - .github/workflows/validate.yml")
    print("  - .github/CODEOWNERS (live config — Owner handle expected)")
    print("  - .claude/scripts/check-contamination.sh")
    print("  - .claude/scripts/check_contamination.py")
    print("  - .claude/scripts/tests/test_check_contamination.py (uses pattern as fixture)")
    print("  - CLAUDE.md (framework master context — Owner path expected)")
    print("  - RELEASE.md (release procedure — Owner path + canonical repo URL)")
    print("  - SECURITY.md (vulnerability disclosure — Owner contact + canonical URL expected)")
    print("  - docs/QUICKSTART.md (install instructions — canonical repo URL)")
    print("  - docs/UPGRADE-PROCEDURE.md (upgrade playbook — canonical repo for gh CLI)")
    print("  - docs/SLO-SLA.md (SLO doc — references named adopter for production data point)")
    print("  - .claude/scripts/check-framework-updates.sh (tool — default upstream URL)")
    print("  - templates/.github/workflows/* (copies of live CI files)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
