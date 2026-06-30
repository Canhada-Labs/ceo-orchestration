# LLM03:2025 Supply Chain — Threat Hunting Playbook

> **Status:** SHIPPED PLAN-095 Wave B.7 (S128 2026-05-17)
> **Detection rule:** `_lib/output_scan.py::_LLM_PATTERN_GROUPS["LLM03_2025_supply_chain"]` (PLAN-095 Wave B.3)
> **Family kill-switch:** `CEO_OUTPUT_SCAN_LLM03=0`
> **Audit emit:** `output_scan_finding` with `family="LLM03_2025_supply_chain"`
> **Alert dedup:** DEFERRED to PLAN-095-FOLLOWUP-dedup-wave-b6
> (Codex R2 iter-1 P0; ships when `check_output_secrets.py` aggregate
> emit contract is refactored to per-pattern emit + dedup wire-in).
> Phase 1 meta-hunt §4 operates against aggregate `output_scan_finding`
> counts only.
> **Cross-references:** `.claude/plans/PLAN-086/llm03-supplement.md` (supplement) · `docs/EXT-011-mitre-atlas.md` §2.1 (cross-link)

## Why a hunting playbook (not just a detection rule)

Per SKILL §Detection-as-Code §6 (alert-fatigue mitigation): a single
LLM03:2025 detection rule firing 1000× per day trains the SOC to
ignore the channel. The defender's leverage is **hypothesis-driven
hunting**, not alert-driven response. This playbook ships **3 hunt
queries** plus a meta-query that grounds re-tuning decisions in
empirical data.

The detection rule (`_LLM_PATTERN_GROUPS["LLM03_2025_supply_chain"]`)
generates `output_scan_finding` events that hunters JOIN against
known-good baselines + corpus data to surface real adversary activity
rather than developer noise.

---

## Hunt query #1 — Uncited package install bursts from a single session

**Hypothesis**: an attacker (or compromised plugin) within a single
agent session installs ≥3 uncited packages within a 5-minute window.
Legitimate developer activity rarely cluster-installs uncited packages;
it usually flows through `requirements.txt` / `package.json` /
`Cargo.lock`. Bursts of uncited installs == provenance breakdown.

**Source events**: `audit-log.jsonl` entries where
`action == "output_scan_finding"` AND
`family_counts.LLM03_2025_supply_chain > 0`.

> **Phase 1 limitation**: `check_output_secrets.py` currently emits an
> aggregate `output_scan_finding` event with per-family counts (no
> per-pattern `pattern_id`). Wave A.7 patterns are not individually
> queryable until PLAN-095-FOLLOWUP refactors the emission shape to
> per-hit events. Phase 1 hunt groups by `family_counts.LLM03_2025_supply_chain`
> count + session_id timing burst.

**Query (jq pseudo-code)**:

```bash
jq -s '
  . | group_by(.session_id)
    | map({
        session: .[0].session_id,
        burst_count: [.[] | select(
          .action == "output_scan_finding" and
          .family == "LLM03_2025_supply_chain" and
          (.pattern_id | startswith("install_"))
        )] | length,
        timespan_min: (
          ([.[].wall_ns] | (max - min) / 60000000000)
        )
      })
    | map(select(.burst_count >= 3 and .timespan_min <= 5))
' < ~/.claude/projects/ceo-orchestration/audit-log.jsonl
```

**Investigation steps**:
1. Pull session transcript via `audit-query.py --session-id <id>`.
2. Cross-check the listed packages against
   `.claude/policies/dependency-allowlist.yaml` (when shipped).
3. Inspect git diff of `requirements.txt` / `package.json` /
   `Cargo.toml` from the same session. If diff is empty BUT installs
   happened → probable lateral movement OR compromised LLM tool.
4. If session is interactive (Owner-driven), validate intent with
   Owner. If session is autonomous (sub-agent), inspect the dispatch
   trail — was the spawn approved with package-install permissions?

**False-positive guards**: dev-environment bootstrap sessions
legitimately burst-install on first run. Tune by adding a
session-age check (`session_age_hours < 1` reduces FP).

---

## Hunt query #2 — Unrecognized MCP server invocations

**Hypothesis**: an `mcp__*` tool call references a server NOT in
`.claude/settings.json` registered MCPs list. Either the server was
registered out-of-band (governance bypass) OR the tool call is a
LLM hallucination crafted by a poisoned prompt to exfiltrate via a
fake MCP server name (Risk #5 Weak Provenance + Risk #7 Exploit
Collaborative Development Processes).

**Source events**: `audit-log.jsonl` entries where
`action == "output_scan_finding"` AND
`pattern_id == "mcp_unrecognized_server"`.

**Query**:

```bash
# Extract server names from MCP calls in audit log
jq -r '
  select(.action == "output_scan_finding" and
         .pattern_id == "mcp_unrecognized_server") |
  .context_preview
' < ~/.claude/projects/ceo-orchestration/audit-log.jsonl |
grep -oE 'mcp__[a-zA-Z0-9_]+__' | sort -u > /tmp/mcp-seen.txt

# Diff against the canonical registered list
jq -r '.mcpServers | keys[]' .claude/settings.json > /tmp/mcp-registered.txt

comm -23 /tmp/mcp-seen.txt /tmp/mcp-registered.txt
```

Any output line is a hunt candidate.

**Investigation steps**:
1. For each unknown server, search the session transcript for the
   user prompt that triggered the MCP call. Was it a legitimate
   user request OR a prompt-injection vector?
2. Check if the MCP server name appears in
   `~/.claude/projects/*/audit-log.jsonl` historically — first-time
   appearance is higher-suspicion.
3. Cross-reference with `_KNOWN_ACTIONS` audit-emit registry —
   actions emitted by the unknown MCP should match registered
   contract.

**False-positive guards**: testing/development sessions sometimes
mock MCP servers via `mcp__test_*__` patterns. Add session-tag
exclusion: `select(.session_tags | any(. == "test-mode") | not)`.

---

## Hunt query #3 — Unverified external fetches with executable disposition

**Hypothesis**: `curl` / `wget` fetch from external URL WITHOUT
checksum verification, where the response body is then piped to
shell or written to an executable path. The classic supply-chain
attack surface: install scripts from untrusted sources execute as
root with no integrity check (Risk #1 Traditional + Risk #5 Weak
Provenance).

**Source events**: `audit-log.jsonl` entries where
`action == "output_scan_finding"` AND
`pattern_id == "curl_unverified_url"` AND
the context preview shows `| sh`, `| bash`, `> /usr/local/bin/`, or
`chmod +x`.

**Query**:

```bash
jq -s '
  [.[] | select(
    .action == "output_scan_finding" and
    .pattern_id == "curl_unverified_url" and
    (.context_preview | test("\\| ?(ba)?sh|chmod \\+x|> ?/usr/(local/)?bin/"))
  )] |
  group_by(.session_id) |
  map({
    session: .[0].session_id,
    hit_count: length,
    samples: [.[0:3] | .[] | .context_preview]
  })
' < ~/.claude/projects/ceo-orchestration/audit-log.jsonl
```

**Investigation steps**:
1. For each hit, pull the full tool-call payload via
   `audit-query.py --session-id <id> --action Bash`.
2. Verify the URL host against a known-good install-script
   provider list (rust-lang.org, docker.com, hashicorp.com, etc.).
3. If the URL host is unknown, treat as a **medium-severity
   incident** and escalate to the incident-commander archetype.
4. Compute the fetched content sha256 from corpus if cached:
   `find ~/.claude/projects/*/cache -name '*.sh' -exec sha256sum {} \;`
   — compare against known-good install-script SHAs.

**False-positive guards**: legitimate one-shot installers (e.g.
`curl https://sh.rustup.rs | sh`) are well-known and trusted.
Maintain an allowlist of `(host, path_prefix)` tuples in
`.claude/policies/install-script-allowlist.yaml` and skip those
from the hunt. Re-tune quarterly per `D-2` post-ship signature drift
audit.

---

## Meta-hunt — Suppression rate as a tuning signal (PLAN-106 Wave H dedup-aware)

**Active tuning signal (PLAN-106 Wave H ship)**. Now that the dedup
wire-in to `check_output_secrets.py` is live (PLAN-106 v1.37.0),
the meta-hunt switches from the aggregate finding-rate heuristic to
the **suppression rate** heuristic. Suppression rate is the fraction
of `output_scan_finding_suppressed` events over the union of
`output_scan_finding` (per-pattern) + `output_scan_finding_suppressed`
in a 7d rolling window per project session:

    suppression_rate := count(output_scan_finding_suppressed) /
                        (count(output_scan_finding[pattern_id present]) +
                         count(output_scan_finding_suppressed))

**Thresholds (advisory, NOT blocking)**:

- `suppression_rate > 30%` over a 7d window → patterns are too noisy
  (many repeat fires of the same `(repo, command, pattern)` tuple
  within 24h). Tune the regex tighter or split the pattern.
- `suppression_rate < 5%` over a 7d window → patterns are too narrow
  (almost no repeat fires; either the pattern fires once and rotates
  away, or the rule is silent). Consider broadening the regex or
  retiring the rule per SKILL §Detection-as-Code §Retire-or-tune.
- `5% ≤ suppression_rate ≤ 30%` → healthy detection volume; no
  tuning action required.

The legacy aggregate finding-rate heuristic (50 events/24h sustained
7d → tune; <1 event/7d for 30d → silent rule check) remains a
fallback for sessions whose `output_scan_finding` events still carry
the pre-Wave-H aggregate shape (no `pattern_id` field). Past the 24h
deprecation window per AC15b, the aggregate sidecar disappears and
the suppression-rate heuristic becomes the SOLE meta-hunt signal.

**Query**:

```bash
WINDOW_DAYS=7
NOW_NS=$(date +%s%N)
WINDOW_NS=$((NOW_NS - WINDOW_DAYS * 24 * 3600 * 1000000000))

jq -s --argjson cutoff "$WINDOW_NS" '
  [.[] | select(.wall_ns >= $cutoff and
                .family == "LLM03_2025_supply_chain")] |
  {
    total_findings: [.[] | select(.action == "output_scan_finding")] | length,
    total_suppressed: [.[] | select(.action == "output_scan_finding_suppressed")] | length,
    suppression_rate: (
      ([.[] | select(.action == "output_scan_finding_suppressed")] | length) /
      ([.[] | select(.action == "output_scan_finding")] | length // 1)
    )
  }
' < ~/.claude/projects/ceo-orchestration/audit-log.jsonl
```

If `suppression_rate > 0.30`, run the per-pattern breakdown:

```bash
jq -s '
  [.[] | select(.family == "LLM03_2025_supply_chain")] |
  group_by(.pattern_id) |
  map({
    pattern_id: .[0].pattern_id,
    findings: [.[] | select(.action == "output_scan_finding")] | length,
    suppressed: [.[] | select(.action == "output_scan_finding_suppressed")] | length,
  })
'
```

The pattern(s) with the highest suppression count are tune candidates.
Open a `PLAN-095-FOLLOWUP` ticket OR retire the noisy pattern per
SKILL §Detection-as-Code §Retire-or-tune.

---

## Backlog (post-ship monitoring per PLAN-095 §6b D-1)

- **D-1**: 7d post-ship FPR observation report at
  `.claude/plans/PLAN-095/post-ship-fpr-report.md`. Required hunt
  output: empirical FPR per pattern + qualitative noise assessment
  + retire-or-tune decisions.
- **D-3**: Promote LLM03:2025 advisory → blocking via PLAN-100
  confidence-gate trajectory; gate by suppression rate ≤ 5% + alert-
  to-incident-conversion ≥ 25%.

## References

- PLAN-086/llm03-supplement.md (OWASP 2025 supplement)
- PLAN-095-tier-7-final-plan084-closure.md (this rule's ship plan)
- docs/EXT-011-mitre-atlas.md §2.1 (ATLAS registry cross-link)
- ADR-049 Detection-as-Code corpus + ATT&CK + SIEM doctrine
- ADR-115 Maintenance mode (anti-churn)
- ADR-125 Tier-A risk-tiered defaulting
- SKILL: `.claude/skills/core/security-and-auth/SKILL.md` §Detection-as-Code
