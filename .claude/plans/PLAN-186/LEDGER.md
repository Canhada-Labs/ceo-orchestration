# LEDGER — PLAN-186 (modelo operacional do orquestrador)

> Só identificadores verbatim (paths, SHAs, ids) — nunca corpo de transcript
> (repo público). Escrito em fronteira de unidade. Teto ≤ 2k tokens.

## Unidade corrente — S363 (2026-10-12)

- Status do plano: `executing`. Base conferida: `c76b61c1`. Lista completa de commits = `related_commits` do plano, re-derivada nesta unidade (55 SHAs).
- Fechados desde a S348: AC-13 ✅ S361 em `82736c9` (relatório `PLAN-186/w0/ac13-routing-invariant-S361.md`).
- PLAN-188 CONGELADO desde 2026-10-01 (S361; `PLAN-188-shared-ceremony-toolkit.md`): a W6a e a `w4b-gates-v2` seguem pelo molde por onda. Isso supera, abaixo, «aguarda rodada 12» e «materiais esperam o toolkit».
- W1: não landou. Só volta como pack NOVO, re-arquitetado (regra R3; Q4 do bloco B da S348). O pin do assento é `claude-opus-5-5` desde a Emenda 3 do ADR-149 (S357); o alvo da W1 é a OQ-11 do plano, aberta para o Owner.
- CI (`PLAN-186/w4/validate-push-runs-S363.md`): o Validate de `push` roda no self-hosted `canhada-ci` desde 2026-10-11, 6/6 ≤ 14 min; o Smoke mede 73m45s–115m47s, 0/6 ≤ 45 min.
- Follow-ups, todos `draft` (PLAN-SCHEMA §1.4: nenhum entra em `executing` antes de o PLAN-186 ficar `done`): `PLAN-186-FOLLOWUP-census-runtime.md` (W0 landada em `cad21f0`; trabalho não landado em sombra na S363); `PLAN-186-FOLLOWUP-hint-discovery-walk-from-root.md` e `PLAN-186-FOLLOWUP-sentinel-gpg-verification.md` (em edição em outras sombras na S363); `PLAN-186-FOLLOWUP-seat-fable51-row.md` (novo nesta unidade, decisão 4.4 da S347).
- Decisões do Owner desde a S348: `1059f23` (S348-c, `PLAN-186/debate/owner-decisions-S348-c.md`), S353 (`PLAN-186/debate/owner-decisions-S353.md`), S361 (`6a9abb1`, Q1–Q14).
- Próxima unidade: resposta do Owner à OQ-11; depois, a fila canônica da S348 (W4b → W6a → W1 re-arquitetada), cada uma com cerimônia GPG.

## Unidade anterior — S348 (2026-09-06 → 07), noite autônoma (histórico)

- Status do plano: `executing` (`.claude/plans/PLAN-186-orchestrator-operating-model.md`). Waves: W0 landada; W4a landada `8003b65` e medida `0b5e6ed`; W4b (`s344-packs/w4b-ci-matrix`) RESCINDIDA na S348 (52 registros de rail) → pack sucessor `s344-packs/w4b-gates-v2` (construído, 0 rodadas); W6a (`s344-packs/w6-adapter`) sujeito APPROVE, materiais com arquitetura de congelamento construída, aguarda rodada 12; W1 (`s344-packs/w1-widen`, 40 registros) só re-arquitetada; W5 doutrina em debate (`de42dfb`).
- Follow-ups: `PLAN-186-FOLLOWUP-census-runtime.md` (W0 landada `cad21f0`), `PLAN-186-FOLLOWUP-hint-discovery-walk-from-root.md` (`3f8f4f0`, curas `a3425ba`), `PLAN-186-FOLLOWUP-sentinel-gpg-verification.md` (draft).
- Decisões do Owner registradas: `bc52016` (S344), `c05ecdc` (S347, 19 decisões — `PLAN-186/debate/owner-decisions-S347.md`), `26cf9c1` (S348 bloco B, 8 respostas), `7f6b564` (revisão de portfólio S348 — `PLAN-186/portfolio-review-S348/`).
- Lander compartilhado: `s344-land-combined` (regra R1 do Owner, 2026-09-06: land livre = zero codex). Commits que o citam, do mais novo ao mais antigo:
  - `cad21f0` 2026-09-07 — PLAN-186 s344-land-combined p186fu-census-runtime-w0
  - `26cf9c1` 2026-09-07 — PLAN-186 owner-decisions-S348-b
  - `d414a6a` 2026-09-07 — PLAN-176 debate round-2
  - `690c3e2` 2026-09-06 — PLAN-186 s344-land-combined p171-w0-lote6
  - `2a36e5c` 2026-09-06 — PLAN-186 s344-land-combined p188-plan-r3
  - `ef4c1b3` 2026-09-06 — PLAN-186 s344-land-combined p171-w0-lote5
  - `7f6b564` 2026-09-06 — PLAN-186 portfolio-review-S348 + PLAN-187 close
  - `c05ecdc` 2026-09-06 — PLAN-186 owner-decisions-S347
  - `3b4300a` 2026-09-06 — PLAN-186 s344-land-combined p171-w0-lote4
  - `fad3d02` 2026-09-06 — PLAN-186 s344-land-combined p188-plan-r2
  - `00839a6` 2026-09-06 — PLAN-186 s344-land-combined p171-w0-lote3
  - `db05586` 2026-09-06 — PLAN-186 s344-land-combined contamination-gate-v4
  - `14892ab` 2026-09-06 — PLAN-186 s344-land-combined p171-w0-lote2-fix
  - `3f8f4f0` 2026-09-06 — PLAN-186 s344-land-combined walkroot-followup-plan
  - `bb68edf` 2026-09-06 — PLAN-186 s344-land-combined p188-plan-draft
  - `184a1a2` 2026-09-06 — PLAN-186 s344-land-combined p171-w0-lote2
  - `a3425ba` 2026-09-05 — PLAN-186 s344-land-combined walkroot-fix
  - `b00ba27` 2026-09-05 — PLAN-186 s344-land-combined p187-night-facts
  - `1e2f657` 2026-09-05 — PLAN-186 s344-land-combined p171-w0-lote1
  - `de42dfb` 2026-09-05 — PLAN-186 round-4
  - `2f6cde1` 2026-09-05 — PLAN-186 s344-land-combined us5-followup-docs
  - `5ceae29` 2026-09-04 — PLAN-186 s344-land-combined p183-ac2-evidence
  - `2ef423e` 2026-09-04 — PLAN-186 s344-land-combined ac1-close+p184-derive-ci-cost
  - `f71a0b3` 2026-09-04 — ci s344-npm-smoke-hermetic-v2
  - `bc52016` 2026-09-04 — PLAN-186 W-ROTA
  - `5cae2f6` 2026-09-04 — PLAN-186 W4a
  - `0b5e6ed` 2026-09-04 — PLAN-186 W4a
  - `532ad22` 2026-09-04 — chore(PLAN-186 W4a): corrida de medição 3/3 — commit vazio
  - `0bd0620` 2026-09-04 — chore(PLAN-186 W4a): corrida de medição 2/3 — commit vazio
  - `8003b65` 2026-09-04 — ceremony(PLAN-186 wave-s343-w4a): deleta os 2 steps duplicados do job validate (cob
  - `93efbb1` 2026-09-04 — chore(PLAN-186 W4a s343-ceremony-w4a): EXPECTED-BASELINE re-derivado em 449f157 — +
  - `449f157` 2026-09-04 — S343
  - `37fd85b` 2026-09-04 — PLAN-186 AC-10 s343-ac10-below-floor-v4
  - `b53fec1` 2026-09-04 — PLAN-186 AC-14 s343-ac14-classifier-v2
  - `685868a` 2026-09-04 — PLAN-186 AC-1 s343-ac1-verify-v2
  - `44c16f4` 2026-09-04 — chore(PLAN-186 W4a s343-ceremony-w4a): materiais da cerimônia wave-s343-w4a — deleç
  - `b590f00` 2026-09-03 — PLAN-186 W0 s341-cost-integration-v2
  - `7535b2f` 2026-09-03 — PLAN-186 W0+W4a s340/s341
  - `400638e` 2026-09-02 — docs+plan(PLAN-186 S339): estudo do modelo operacional do orquestrador → PLAN-186 r
- Próxima unidade: respostas do Owner às perguntas 1-11 de `s344-packs/MORNING-S348.md` §4; depois closeout S348 (`CLAUDE.md` §5 linha S348). ↘ S363: respondidas em `1059f23` (`owner-decisions-S348-c.md`).
