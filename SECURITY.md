# Security Policy

<!-- last-reviewed: 2026-05-25 v1.0.0 -->

> **Status:** pre-adopter (framework dogfooded by Owner; no third-party
> install in production yet). This policy mirrors the maturity level
> honestly — no bug bounty, no SLA paid tier, no managed disclosure
> service. It DOES guarantee a single-Owner triage path with timelines.

## Scope

The framework's security boundary is the **arbitration kernel** —
mechanically-enforced governance that an adopter trusts to gate their
Claude Code session. In scope for vulnerability reports:

| Area | Path | What we mean by "vulnerability" |
|------|------|----------------------------------|
| Spawn governance | `.claude/hooks/check_agent_spawn.py` | Bypass of the persona + skill + file-assignment requirement |
| Canonical-edit guard | `.claude/hooks/check_canonical_edit.py` | Edit of a canonical path without an approved sentinel |
| Skill-reference observer | `.claude/hooks/check_skill_reference_read.py` | TOCTOU between SHA-pin and sub-agent Read |
| Audit-log integrity | `.claude/hooks/audit_log.py` | Silent drop, redaction failure, secret leak in `desc_preview` |
| Plan-edit gate | `.claude/hooks/check_plan_edit.py` | Illegal status transition slipping through |
| Bash safety | `.claude/hooks/check_bash_safety.py` | Bypass of the destructive-command block list |
| Read injection | `.claude/hooks/check_read_injection.py` | Prompt-injection family undetected by `scan-injection.py` |
| Output safety | `.claude/hooks/check_output_safety.py` | Sensitive-pattern leak past the redactor |
| Budget gate | `.claude/hooks/check_budget.py` | Bypass of `CEO_BUDGET_BYPASS` accounting |
| Skill-patch sentinel | `.claude/hooks/check_skill_patch_sentinel.py` | Unsigned skill-patch landing under `SP-NNN` chain |
| Native subagents | `.claude/agents/<archetype>.md` | Frontmatter trust-boundary breach (ADR-050 / ADR-051) |
| Install / upgrade | `scripts/install.sh`, `scripts/upgrade.sh` | Path traversal, unauthorized canonical overwrite |
| MCP server | `.claude/scripts/mcp-server/` | ACL bypass, `spawn_agent` deny-path failure |
| Live adapters | `.claude/hooks/_lib/adapters/live/` | Credential exfiltration, breaker bypass |
| SPEC contracts | `SPEC/v1/**` | Schema-drift between published contract and emitter |
| GitHub Actions | `.github/workflows/**` | Privilege escalation via fork-PR or unpinned action |

**Out of scope:**

- Adopter-authored skills, plans, ADRs, or domain personas (those are the
  adopter's content — review them yourself).
- Claude Code itself, the Anthropic SDK, or upstream Anthropic API
  vulnerabilities — report to https://www.anthropic.com/security.
- Bugs in `claude-in-chrome` or other MCP servers shipped by third parties.
- Information-disclosure via the audit log if the adopter has chosen to
  store it on a shared filesystem (see `docs/threat-model.md` §I-04).
- DoS via deliberate user input (the framework defends against accidental
  resource exhaustion, not motivated abuse from the operator themselves).

A 33-scenario STRIDE catalog with explicit residual risks lives in
[`docs/threat-model.md`](docs/threat-model.md). Read the §Executive
summary first.

## Reporting a vulnerability

Report **privately** to the Owner via:

1. **GitHub Security Advisory** — preferred. Open
   `https://github.com/Canhada-Labs/ceo-orchestration/security/advisories/new`.
   Private to the Owner until coordinated disclosure.
2. **Email** — Owner email configured at install time (edit `CLAUDE.md`
   in your installed project to set your contact address). Subject:
   `[ceo-orchestration security]`. PGP key not yet published; use the
   GitHub channel for sensitive payloads.

Do **not** open a public GitHub issue for a security defect. Public
issues become indexed within minutes and tip off opportunistic
attackers.

### What to include

- Affected component (file path or hook name)
- Affected version (output of `cat VERSION`)
- Reproduction steps (or proof-of-concept payload)
- Impact assessment (what an attacker gains)
- Suggested mitigation, if you have one

### What we ask of reporters

- **No public disclosure** until we coordinate a fix or 90 days have
  passed (whichever first), per industry convention.
- **No exploitation** beyond what is needed to demonstrate the issue.
  Specifically: do not exfiltrate adopter audit logs, do not run the
  PoC against repositories you do not own.
- **No social engineering** of the Owner or maintainers. We will
  acknowledge legitimate reports promptly.

## Response timeline (Owner SLA, best-effort)

| Stage | Target | What happens |
|-------|--------|--------------|
| **Acknowledgement** | ≤ 48 hours | Owner confirms receipt; assigns severity tier (Critical / High / Medium / Low). |
| **Initial assessment** | ≤ 7 days | Owner reproduces or refutes; opens a tracking ADR if accepted; communicates the plan. |
| **Critical fix** | ≤ 14 days | Patch lands on `main`; cut a `-rc` tag; 48-hour expedited RC hold instead of 7. |
| **High fix** | ≤ 30 days | Patch lands; standard 7-day RC hold; advisory published. |
| **Medium / Low fix** | next MINOR release | Tracked in plan + ADR; rolls into the next scheduled release. |
| **Coordinated disclosure** | with you | Joint statement on the GitHub Security Advisory; CHANGELOG entry under `### Security`. |

This is a one-Owner project. SLA is best-effort, not contractual. If
you need a contractual response time, talk to the Owner about a
support agreement (none exists today; see [`SUPPORT.md`](SUPPORT.md)).

## Breach escalation (post-incident)

> **Scope:** this section covers what happens AFTER a vulnerability
> has been confirmed exploited in the wild OR a security-relevant
> incident has affected an installed framework. PLAN-024 F-comp-001
> flagged this as a gap; this section closes it.

### What counts as a breach

- Confirmed exploitation of a reported vulnerability before the fix ships
- Secret material leaked via a framework component (audit-log,
  sentinel, skill-by-reference verification) — Owner's or adopter's
- Kernel guard bypass used to land code without the governance contract
  (`check_agent_spawn.py`, `check_canonical_edit.py`,
  `check_arbitration_kernel.py`, `check_skill_patch_sentinel.py`)
- Supply-chain compromise of the published NPM package or GitHub
  release tarball (SHA mismatch, tampered `install.sh`)
- Upstream provider incident that exposes audit-log data to a third
  party (e.g., the Claude Code runtime transmits redacted payloads
  elsewhere)

### Owner's breach-response steps

| Stage | Target | Action |
|-------|--------|--------|
| **Contain** | ≤ 6 hours from confirmation | Cut an emergency `-hotfix` tag on `main`; disable the affected code path behind a kill switch (`CEO_SOTA_DISABLE=1` or the targeted `CEO_*_DISABLE` env var); publish a GitHub Security Advisory in **draft** state. |
| **Notify** | ≤ 24 hours | Publish the GitHub Security Advisory (public). Email the reporter with the fix plan. Post to `CHANGELOG.md` under `### Security`. Reach out to known adopters (the Owner maintains an informal adopter list — currently: internal only, see `docs/HONEST-LIMITATIONS.md` §2). |
| **Remediate** | ≤ 14 days for Critical; ≤ 30 days for High | Land the real fix on `main` + cut the next `-rc` with 48-hour RC hold (Critical) or standard 7-day hold (High). Update the GitHub Advisory with CVE ID once assigned. |
| **Disclose** | Joint with reporter | Public post-mortem in `docs/incidents/YYYY-MM-DD-<slug>.md` including timeline, affected versions, root cause, and prevention measures. |
| **Learn** | Within 60 days | Author an ADR if the incident reveals a structural gap. Add a regression test or threat-model entry. Update this SECURITY.md if the gap is in the policy itself. |

### Adopter's breach-response steps (if you installed the framework)

1. **If you receive a security notification from the Owner:**
   - Apply the recommended env-var kill switch IMMEDIATELY (no code changes).
   - Review your `~/.claude/projects/<slug>/audit-log.jsonl` for the impact window.
   - Plan the upgrade per `docs/UPGRADE-PROCEDURE.md` with the
     ≤ 24-hour target for Critical, ≤ 7-day target for High.
2. **If you detect a breach yourself** (before Owner notifies):
   - Report privately per §Reporting a vulnerability above.
   - Apply `CEO_SOTA_DISABLE=1` to halt governance-dependent workflows
     while the Owner triages.
   - Preserve your audit-log: `cp ~/.claude/projects/<slug>/audit-log.jsonl
     ~/breach-evidence-$(date -u +%Y%m%dT%H%M%SZ).jsonl` (do NOT
     email this — it contains redacted but still-sensitive context).
3. **If your own environment is compromised** (unrelated to framework
   but uses it):
   - Rotate any `ANTHROPIC_API_KEY` referenced in your session.
   - Rotate GitHub Personal Access Tokens used with `gh`.
   - Run `bash .claude/scripts/ceo-backup.sh` before any remediation
     to preserve state.
   - See `docs/INCIDENT-RESPONSE.md` for the general operational
     playbook (framework-independent).

### Contact channels (ranked by urgency)

| Urgency | Channel | SLA |
|---------|---------|-----|
| Active exploitation | GitHub Security Advisory (draft) + email + mark `URGENT` | Owner acknowledges ≤ 4 hours |
| Confirmed vulnerability | GitHub Security Advisory | ≤ 48 hours |
| Suspected vulnerability | GitHub Security Advisory | ≤ 72 hours |
| Question / clarification | GitHub Issue | Next business day |

No paid-tier SLA exists; see `SUPPORT.md`. For a contractual commitment
around incident response time, contact the Owner to discuss a support
agreement (none exists today).

## Severity tiers

We use the residual-risk language from `docs/threat-model.md`:

- **Critical** — arbitration kernel bypass, audit-log silent drop,
  credential exfiltration, supply-chain compromise of `install.sh`.
- **High** — sentinel forgery on a single canonical path, redaction
  miss exposing a category of secrets, governance gate fail-open under
  predictable input.
- **Medium** — denial of audit log under specific input, schema-drift
  between SPEC and emitter that breaks downstream consumers, hook
  fail-open under malformed payload (advisory only).
- **Low** — documentation inaccuracy that misleads adopters about a
  defense, naming inconsistency that confuses operators, missing
  validation on cosmetic field.

## Coordinated disclosure & credit

- Reporters are credited in the GitHub Security Advisory and
  CHANGELOG under `### Security` unless they request anonymity.
- We do **not** offer monetary bounties. We do publish thanks. If your
  employer requires a public credit for compliance reporting, say so
  in the report and we will make it visible.
- Reporters may publish their own write-up after the fix ships and the
  advisory is public. We ask for a 24-hour heads-up on the publication
  date so we can prepare adopter-facing notes.

## Hardening you can do today (adopter-side)

Even before adopting the framework into production:

1. **Enable branch protection** on your fork. Required checks:
   `validate.yml`, `coverage.yml`, `red-team.yml`. See
   [`docs/BRANCH-PROTECTION.md`](docs/BRANCH-PROTECTION.md).
2. **Read** [`docs/threat-model.md`](docs/threat-model.md) §CTO reading
   path (15 minutes) and decide which Tier-2/3 attackers you actually
   defend against.
3. **Pin** the framework to a tagged release via
   `bash scripts/upgrade.sh --pin vX.Y.Z` (use the current tag from `git tag -l 'v*' --sort=-version:refname | head -1`) and refuse uncommitted
   `.claude/` deltas (the `--pin` path enforces this).
4. **Rotate** any `ANTHROPIC_API_KEY` that touches the framework on the
   schedule defined in [`docs/rotation-log.md`](docs/rotation-log.md).
5. **Subscribe** to release notifications on this repository so you
   learn about a fix when it lands, not when an exploit lands.

## Known residuals (carried in the threat model, NOT bugs)

These are **accepted** trade-offs. Reporting them as new issues will
get a "by-design" response:

- **Owner workstation compromise** — a Tier-2 insider with the Owner's
  GPG key can sign sentinels. The framework's authority chain ends at
  the Owner. See `docs/threat-model.md` §Primary residual risk #1.
- **Same-LLM critique** — independent agents share the same model
  family. We mitigate via skills-as-checklists + verifiable outputs.
  See [`docs/HONEST-LIMITATIONS.md`](docs/HONEST-LIMITATIONS.md) §Same-LLM.
- **Audit-log HMAC chain is detection-only, not prevention** (PLAN-023
  Phase B / ADR-055 / v1.6.0). Per-entry
  `hmac = hmac_sha256(key, prev_hmac || canonical_json(entry))` with
  key at `~/.claude/projects/<slug>/audit-key` (0600, 32 random bytes).
  Verifier: `python3 .claude/scripts/audit-verify-chain.py`. Defends
  forgery / reorder / interior deletion. Does NOT defend tail
  truncation, key theft, rollback, or log+key co-deletion. On suspected
  tamper, **preserve audit-log.jsonl + audit-key TOGETHER** before
  remediation — the forensics depend on the pair. Full residual list
  in `docs/HONEST-LIMITATIONS.md` §7 and ADR-055 §Threat Model.
- **Nation-state attacker** — out of scope. The framework cannot defend
  against a Tier-4 adversary that compromises Anthropic's TLS stack or
  the Claude model itself.

## Versions covered by this policy

Active support window per [`SUPPORT.md`](SUPPORT.md):

- **Current MINOR** (`v1.45.x`) — full security support.
- **Previous MINOR** (`v1.44.x`) — security-only patches for 6 months
  after the next MINOR ships.
- **Older** — best-effort; we will tell you the upgrade path, not ship
  a back-port.

If your report concerns a version that is end-of-life, we will validate
it on `main` and patch forward; no back-port.

## Contact

- **Primary:** GitHub Security Advisory on this repository
- **Backup:** Owner email (configure in your installed project's `CLAUDE.md`)
- **Public discussion of accepted vulnerabilities:** GitHub Releases +
  CHANGELOG `### Security` section

Last reviewed: 2026-05-25 (Session 160 / PLAN-112-FOLLOWUP-canonical-doc-refresh-gate).
