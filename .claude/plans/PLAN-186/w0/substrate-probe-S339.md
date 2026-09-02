# substrate-watch --probe-installed — S339 2026-09-02 (read-only; --refresh é receita PENDING-OWNER, não rodada)

```
advisory: run --refresh for the PENDING-OWNER recipe
substrate-watch: drift — installed substrate differs from last-reconciled for: ['claude_code', 'codex_cli', 'codex_harness', 'cc_native_usage']
  [DRIFT] Claude Code CLI              last_seen=2.1.198 installed=2.1.258 (ok)
  [ok] Claude Agent SDK (TypeScript) last_seen=0.3.198 installed=(not probed) (probe exit 1 (not installed?))
  [ok] Claude Agent SDK (Python)    last_seen=0.2.110 installed=(not probed) (probe exit 1 (not installed?))
  [DRIFT] Codex CLI (pair-rail reviewer) last_seen=0.144.1 installed=0.147.0 (ok)
         runbook: codex-cli drift — fixture re-record runbook (PLAN-155 debate A12): do NOT re-record fixtures against the new binary directly. (1) bump the pin FIRST via the ADR-182 pin ceremony (codex-cli-pin.txt semver range + codex-cli-pin-manifest.json per-triple PAYLOAD sha256 — the retired codex-cli-binary-sha256.txt launcher hash is a tombstone); (2) THEN re-record the PLAN-155 Wave-1 host-adapter fixtures under .claude/hooks/tests/fixtures/adapters/codex/ (each fixture carries _meta.codex_cli_version; the pin-range test stays RED until fixtures are re-recorded or explicitly waived); (3) run the per-bump re-verification checklist in ADR-161 (hook envelope schema, PreToolUse interception surface, /hooks trust-hash keying, SubagentStart continue:false, Stop decision:block, execpolicy prefix_rule syntax).
  [DRIFT] Codex CLI (host harness: hooks/config/rules) last_seen=0.139.0 installed=0.147.0 (ok)
         runbook: codex-cli drift — fixture re-record runbook (PLAN-155 debate A12): do NOT re-record fixtures against the new binary directly. (1) bump the pin FIRST via the ADR-182 pin ceremony (codex-cli-pin.txt semver range + codex-cli-pin-manifest.json per-triple PAYLOAD sha256 — the retired codex-cli-binary-sha256.txt launcher hash is a tombstone); (2) THEN re-record the PLAN-155 Wave-1 host-adapter fixtures under .claude/hooks/tests/fixtures/adapters/codex/ (each fixture carries _meta.codex_cli_version; the pin-range test stays RED until fixtures are re-recorded or explicitly waived); (3) run the per-bump re-verification checklist in ADR-161 (hook envelope schema, PreToolUse interception surface, /hooks trust-hash keying, SubagentStart continue:false, Stop decision:block, execpolicy prefix_rule syntax).
  [ok] Grok Build CLI (third host harness) last_seen=0.2.93 installed=(not probed) (no probe registered for component 'grok_cli')
  [DRIFT] Claude Code native per-agent usage (on-disk) last_seen=2.1.232 installed=2.1.258 (ok)
  [ok] Claude Code Workflow rail vs spawn-gate boundary last_seen=2.1.237 installed=(not probed) (no probe registered for component 'cc_workflow_rail')
```
