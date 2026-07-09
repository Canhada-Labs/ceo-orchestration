<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/security-and-auth/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

## Detection-as-Code — runbook for security alerts

Preventive controls are necessary but never sufficient — every
deployed control eventually has a bypass that ships ahead of the
patch. The Detection-as-Code (DaC) pipeline catches that bypass via
log-pattern alerts mapped to MITRE ATT&CK techniques, with rules
under version control and continuous regression-tested against
attacker-replay fixtures.

### Pipeline shape

```
detections/<technique-id>/<rule-id>.yaml
    │
    ├── version-controlled in git
    ├── peer-reviewed via PR
    ├── compiled to target SIEM in CI (Sigma → SPL/KQL/EQL)
    ├── replayed against attacker-fixture corpus in CI
    └── deployed to SIEM via main-branch CD (no console edits, ever)
```

Console-edited rules are forbidden — they bypass review, they erode
the audit trail, and they desynchronize prod from git. If the SIEM
console allows direct edit, the IAM grant for that role is itself
the finding.

### Required metadata on every detection rule

A rule without metadata is a rule the SOC will silence within a
quarter. The framework requires the following fields at minimum:

| Field                 | Purpose                                                    | Reject if missing |
|-----------------------|------------------------------------------------------------|-------------------|
| `rule_id` (UUID)      | Stable cross-SIEM identifier; survives compilation         | yes               |
| `mitre_attack`        | At least one technique ID (e.g. `T1110.003`)               | yes               |
| `severity`            | informational / low / medium / high / critical             | yes               |
| `data_source`         | Which log stream the rule consumes                         | yes               |
| `false_positive_note` | Documented benign scenarios this rule will hit             | yes               |
| `validation_fixture`  | Path to attacker-replay sample that MUST trigger the rule  | yes               |
| `last_validated_utc`  | ISO timestamp of most recent CI fixture pass               | yes               |
| `kill_chain_phase`    | Where in the kill chain this rule sits                     | recommended       |
| `owner_archetype`     | Who triages the alert (typically `security-engineer`)      | recommended       |

### Tuning targets

The pipeline is graded on signal quality, not rule count. Three
operational thresholds are non-negotiable:

| Metric                              | Target                  | Action when out of bound                            |
|-------------------------------------|-------------------------|-----------------------------------------------------|
| False-positive rate per rule        | ≤ 15% (rolling 30-day)  | Tune allowlist, narrow logsource, or retire rule    |
| Time-to-triage on critical alert    | ≤ 10 min during waking  | Re-prioritize rule severity, page on schedule       |
| Alert-to-incident conversion        | ≥ 25% (rolling quarter) | Below this, the rule trains the SOC to ignore alerts|
| Coverage of MITRE techniques used by sector adversaries | ≥ 60% on critical kill-chain phases | Detection-roadmap escalation |

A rule that fires 50 times a day with three true positives is worse
than no rule at all — it consumes an analyst hour and produces alert
fatigue that bleeds into the rules that matter. Retire it or fix it
within one tuning cycle.

### CI replay fixture format

Every rule MUST ship with at least one attacker-replay fixture that
the rule WOULD fire on. CI replays the fixture nightly and on every
rule edit. A rule whose fixture stops triggering is a regression and
the build fails.

```yaml
# fixtures/T1110.003-credential-stuffing/sample-01.yaml
fixture_id: cs-sample-01
technique: T1110.003
rule_under_test: f8a2-credstuff-burst
description: |
  Replays 50 login failures from one IP within 60 seconds against
  unique usernames; rule must fire with severity=high.
expected_outcome:
  rule_fires: true
  severity: high
  enrichment_present: ["source_ip", "user_count", "time_window"]
log_events:
  - { ts: "2026-05-06T14:00:00Z", event: login_failed, ip: 203.0.113.5, user: a@example.com }
  - { ts: "2026-05-06T14:00:01Z", event: login_failed, ip: 203.0.113.5, user: b@example.com }
  # ... 48 more
```

### Anti-patterns specific to detection rules

| Anti-Pattern                                 | Why It's Wrong                                                 | Correct Approach                                          |
|----------------------------------------------|----------------------------------------------------------------|-----------------------------------------------------------|
| Indicator-of-compromise (IOC) regex on IP    | Attacker rotates infrastructure within hours                   | Behavioral pattern (process tree, command-line shape)     |
| Rule deployed without fixture                | Rule may already be broken; nobody knows until breach          | CI gate fails the build if `validation_fixture` missing   |
| Severity=critical on every rule              | Page-fatigue; SOC silences the channel                         | Severity matches blast-radius of the technique, not author worry |
| Missing MITRE mapping                        | Cannot reason about coverage; cannot prioritize                | Mapping required; field validated in CI                   |
| Console hot-fix during incident              | Change desyncs from git; lost on next deploy                   | Open PR even mid-incident; hot-fix via expedited review   |
| Disabling rule "temporarily" without ticket  | Temporarily becomes permanent; control silently absent         | Disable requires ticket + 7-day auto-reenable             |
| Same finding alerted from three rules        | Duplicate pages; analyst confusion                             | Deconfliction layer suppresses overlap; one canonical rule|

