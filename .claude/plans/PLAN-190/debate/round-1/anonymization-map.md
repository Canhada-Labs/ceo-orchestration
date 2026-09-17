# Anonymization map — PLAN-190 debate round 1 (audit record, DEBATE-SCHEMA §13.2)

The synthesis in `consensus.md` consumed ONLY the anonymized critique text. This file is the
label ↔ archetype mapping, kept for audit; it is not an input to the synthesis.

| label | archetype | file | verdict |
|---|---|---|---|
| Critic-A | Security Engineer (skill `security-and-auth`) | `security-engineer.md` | ADJUST |
| Critic-B | DevOps Engineer (skill `devops-ci-cd`) | `devops-engineer.md` | ADJUST |
| Critic-C | VP Engineering (skill `architecture-decisions`) | `vp-engineering.md` | ADJUST |

Spawn record: three `general-purpose` agents on Fable 5.1, prompts built by
`inject-agent-context.sh --mode=reference`, FILE ASSIGNMENT = one critique file each; `debate-emit`
`start` + three `agent-done` events emitted. A fourth, cross-vendor lane (Codex, read-only, cold)
reviewed the same patch as the V2 truth gate; its findings are in `../../w1/rail-round-1.md` and were
merged with the critiques in the synthesis under the label **Rail-1**.
