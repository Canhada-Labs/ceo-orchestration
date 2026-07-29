# G16 model probe (PLAN-163 T4.4)

- Workflow opts.model: `opus` (as declared by orchestrator)
- Agent self-identification: **claude-fable-5** (Fable 5 family — NOT opus)
- CLI version: `2.1.220 (Claude Code)`
- Date: 2026-07-28

Note: self-identification is weak evidence. The DEFINITIVE proof is the `model`
field recorded in the workflow journal for this spawn, to be verified by the
orchestrator. If the journal shows the session-default model rather than opus,
opts.model remains INERT (PLAN-134 W0a behavior); if it shows an opus id,
the parameter is now honored despite self-id (self-id can lag system-prompt
identity).

## Orchestrator verification (S284, 2026-07-28 — DEFINITIVE)

- `agent-*.meta.json` (workflow wf_87430d5b): records the REQUESTED override
  `model: opus` on all 8 probe agents.
- `agent-a0c594c6f683a309b.jsonl` (journal): all 29 API turns carry
  `"model":"claude-fable-5"` — the SESSION model, not opus.

**VERDICT: `opts.model` remains INERT on CC 2.1.220** (same class as
PLAN-134 W0a). The requested override is recorded but not applied; agents
inherit the main-loop model. G16 disposition: the subprocess workaround
(`claude -p --model <id>`) remains the only working override; the
"if fixed → simplification follow-up" branch is MOOT for 2.1.220.
