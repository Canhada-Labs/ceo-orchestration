---

id: SP-002
skill_slug: security-and-auth
archetype: security-engineer
proposed_at: 2026-04-20T09:16:54Z
source_lessons:
  - session-38-cont-sp-002-security-and-auth
scan_injection_pass: true
diff_size_added: 30
diff_size_removed: 0
sha256_of_diff: 4ead736755d4203d377874d7a1970e43543f62c2cbf755937da748d803dbe074
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T09:58:51Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-002 — skill patch proposal

**Target:** `.claude/skills/core/security-and-auth/SKILL.md`  
**Archetype:** security-engineer  
**Kind:** manual cross-link closure (Session 38 continuation)

## Rationale

PLAN-039 Wave C Phase 1 in-skill section. docs/OWASP-LLM-TOP-10.md + owasp-llm-top-10.yaml benchmark shipped 2026-04-19 (commit 9b1da26). This patch delivers the inference-path rubric so agents spawned with security-and-auth loaded carry the LLM-## checklist directly, not only at benchmark runtime. Closes awesome-plugins security-sweep audit BORROW.

## Provenance note

This proposal was hand-authored via `/tmp/gen_sp_proposals.py` as part of the Session 38 100%-closure sweep (Owner autorizou in-chat 2026-04-20). The diff is a pure addition — append-only — and applies cleanly via `skill-patch-apply.py` which collects `+`-prefixed lines from the ```diff fence below. No code execution / automated mutation; the amendment is a doc-only cross-link to already-shipped artifacts (PROTOCOL.md §Artifact Paradox, docs/OWASP-LLM-TOP-10.md + benchmark, reference/*.yaml under frontend skills).

## Proposed diff

```diff
--- a/.claude/skills/core/security-and-auth/SKILL.md
+++ b/.claude/skills/core/security-and-auth/SKILL.md
@@ -468,3 +468,33 @@
 Scenario edit policy: any change to code samples, expected tags, or
 severity bumps the scenario's `version:` and carries a `validated_by:
 YYYY-MM-DD` line. CODEOWNERS gates the benchmark YAML.
+## OWASP LLM Top 10 (2024) — inference-path rubric
+
+> Cross-ref: full rubric + framework-defense mapping at
+> `docs/OWASP-LLM-TOP-10.md`. Benchmark fixtures at
+> `benchmarks/owasp-llm-top-10.yaml` (14 positive + 6 control
+> scenarios, model_baseline_version = claude-opus-4-7).
+
+When reviewing LLM-adjacent code, the security specialist MUST
+verify each of the 10 categories:
+
+| ID | Category | First-pass audit question |
+|----|----------|---------------------------|
+| LLM01 | Prompt injection | Does untrusted input reach a prompt concatenated with system instructions without separator/pre-scan/escape? |
+| LLM02 | Insecure output handling | Is LLM output piped to an HTML / shell / SQL sink without sanitization? |
+| LLM03 | Training-data poisoning | Is a fine-tune pinned by hash + behavioral regression test before hot-path? |
+| LLM04 | Model DoS | Is there a per-caller rate limit + per-request max-token clamp + cumulative budget? |
+| LLM05 | Supply chain | Is every MCP server pinned (SHA + signature), not `npx -y`? |
+| LLM06 | Sensitive info disclosure | Is PII / secrets absent from prompt + logs + retrieved content? |
+| LLM07 | Insecure plugin design | Does every spawned agent carry `## SKILL CONTENT` or `## SKILL REFERENCE`? Tool scopes least-privilege? |
+| LLM08 | Excessive agency | Is destructive tool authority kill-switched + dry-run-able + human-confirmed? |
+| LLM09 | Overreliance | Is the merge gate re-verifying via CI, not accepting agent "tests pass" self-report? (PROTOCOL §Artifact Paradox) |
+| LLM10 | Model theft | Is the prompt library redacted before export to external sinks? |
+
+Failure to audit any category = reviewer strike (ADR-031 §Review
+discipline).
+
+Benchmark runs per quarter via
+`.claude/scripts/run-skill-benchmark.py --skill security-and-auth
+--benchmark owasp-llm-top-10`. Pass threshold 0.7, control threshold
+0.85 (stricter than owasp-basics).
```

