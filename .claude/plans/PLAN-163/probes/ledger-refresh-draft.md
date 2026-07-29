# PLAN-163 T5.1 — substrate-watch ledger refresh draft (probe artifact)

Generated: 2026-07-28. DRAFT ONLY — do NOT apply outside the T5.4 canonical-edit path.
Files touched by this draft (both canonical; Owner/ceremony applies):
- `.claude/scripts/substrate-watch.json`
- `.claude/scripts/check-substrate-watch.py` (grok `_PROBE_ARGV` registration)

## Fresh probe values (collected live on Owner machine, 2026-07-28)

| component      | ledger last_seen | fresh value | probe |
|----------------|------------------|-------------|-------|
| claude_code    | 2.1.198 (2026-07-01) | **2.1.220** | `claude --version` -> `2.1.220 (Claude Code)` |
| agent_sdk_ts   | 0.3.198 (2026-07-01) | **0.3.220** | `npm view @anthropic-ai/claude-agent-sdk version` |
| agent_sdk_py   | 0.2.110 (2026-07-01) | **0.2.128** | `curl -s https://pypi.org/pypi/claude-agent-sdk/json` -> `.info.version` |
| codex_cli      | 0.144.1 (2026-07-12) | **0.144.6** | `codex --version` -> `codex-cli 0.144.6` |
| codex_harness  | 0.139.0 (2026-07-07) | **0.144.6** (same binary probe) | `codex --version` |
| grok_cli       | 0.2.93 (2026-07-12)  | **0.2.106** | `grok --version` -> `grok 0.2.106 (bde89716f679) [stable]` |

Note: codex_harness `last_seen` semantics = "host-harness schema surface RECONCILED against";
the fixture re-record runbook (`_DRIFT_RUNBOOKS`) applies before bumping it to 0.144.6 —
draft below bumps it, but the Owner may hold it at 0.139.0 until fixtures are re-recorded
(T5.4 tie-break decides; both options shown, default in diff = bump WITH runbook executed).

## model-deprecations.json — PENDING-OWNER refresh recipe

File: `/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/model-deprecations.json`
Current `_meta.fetched`: **2026-06-12** (46 days stale as of 2026-07-28), `source_stale: false`.

Recipe (network step, Owner-run, no model tokens):
1. Fetch `https://platform.claude.com/docs/en/docs/about-claude/model-deprecations`
   (original `https://docs.anthropic.com/en/docs/about-claude/model-deprecations` 301s there).
2. Reconcile the `models` array (ids, deprecation/retirement dates, aliases) against the live table —
   Claude 5 family launches (Fable 2026-06-09, Sonnet 5 2026-06-30, Opus 5 2026-07-24) likely added
   new deprecation lines for the 4.x generation.
3. Bump `_meta.fetched` to the fetch date; keep `source_stale=false` only if populated from the live page.
4. Re-run `.claude/scripts/check-model-deprecations.py --check` and record `LIVE-BREAKS-REMAINING: <n>`.

Status: **PENDING-OWNER** (agents no-network for canonical ledgers under ADR-136-AMEND-1).

## Proposed unified diff — substrate-watch.json

```diff
--- a/.claude/scripts/substrate-watch.json
+++ b/.claude/scripts/substrate-watch.json
@@ _meta @@
-    "fetched": "2026-07-01",
+    "fetched": "2026-07-28",
@@ component claude_code @@
       "key": "claude_code",
       "label": "Claude Code CLI",
       "last_seen": {
-        "version": "2.1.198",
-        "date": "2026-07-01"
+        "version": "2.1.220",
+        "date": "2026-07-28"
       },
@@ component agent_sdk_ts @@
       "key": "agent_sdk_ts",
       "label": "Claude Agent SDK (TypeScript)",
       "last_seen": {
-        "version": "0.3.198",
-        "date": "2026-07-01"
+        "version": "0.3.220",
+        "date": "2026-07-28"
       },
@@ component agent_sdk_py @@
       "key": "agent_sdk_py",
       "label": "Claude Agent SDK (Python)",
       "last_seen": {
-        "version": "0.2.110",
-        "date": "2026-07-01"
+        "version": "0.2.128",
+        "date": "2026-07-28"
       },
@@ component codex_cli @@
       "key": "codex_cli",
       "label": "Codex CLI (pair-rail reviewer)",
       "last_seen": {
-        "version": "0.144.1",
-        "date": "2026-07-12"
+        "version": "0.144.6",
+        "date": "2026-07-28"
       },
@@ component codex_harness @@
       "key": "codex_harness",
       "label": "Codex CLI (host harness: hooks/config/rules)",
       "last_seen": {
-        "version": "0.139.0",
-        "date": "2026-07-07"
+        "version": "0.144.6",
+        "date": "2026-07-28"
       },
@@ component grok_cli @@
       "key": "grok_cli",
       "label": "Grok Build CLI (third host harness)",
       "last_seen": {
-        "version": "0.2.93",
-        "date": "2026-07-12"
+        "version": "0.2.106",
+        "date": "2026-07-28"
       },
```

Conditional variant: if the codex_harness fixture re-record runbook is NOT executed at apply
time, drop the codex_harness hunk (leave 0.139.0) — check-substrate-watch.py will then keep
reporting the drift with the runbook attached, which is the intended fail-loud behavior.

## Proposed unified diff — check-substrate-watch.py (_PROBE_ARGV grok registration)

Target: `/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-substrate-watch.py`,
inside the `_PROBE_ARGV` dict (dict opens at line 76; insertion point = after line 92,
`    "codex_harness": ["codex", "--version"],`, before the closing `}` at line 93).

```diff
--- a/.claude/scripts/check-substrate-watch.py
+++ b/.claude/scripts/check-substrate-watch.py
@@ -90,6 +90,9 @@ _PROBE_ARGV: Dict[str, List[str]] = {
     "codex_cli": ["codex", "--version"],
     "codex_harness": ["codex", "--version"],
+    # PLAN-163 T5.1: grok third-harness code-registered probe (same posture:
+    # ledger can only SELECT the key, never supply argv). Binary ~/.grok/bin/grok.
+    "grok_cli": ["grok", "--version"],
 }
```

Probe output shape note for the version parser: `grok --version` emits
`grok 0.2.106 (bde89716f679) [stable]` — verify the existing version-extraction
regex in check-substrate-watch.py tolerates the `(hash) [channel]` suffix before landing.

Verdict: sdk-ts=0.3.220; sdk-py=0.2.128; diff-pronto=sim
