# LEDGER — PLAN-193 (v1.4.2 expressa)

> Só identificadores verbatim (paths, SHAs, branches, ids) — nunca corpo de
> transcript (repo público). Escrito em fronteira de unidade. Teto ≤ 2k tokens.

## Unidade corrente — manhã da S357; ordem do Owner (tips finais de 2026-09-25)

- Base: `main` = `5c6ab5f6dd01` (kit do corte GA v1.4.1). Plano:
  `.claude/plans/PLAN-193-release-v1-4-2-opus55-fasttrack.md` (`draft`), a cópia do tip de
  `s357/codex-pin` (sha256 `8e246ec6…`: OQ-8, OQ-9 e OQ-10). OQ-4 segue aberta no texto: a
  ordem abaixo executa DUAS cerimônias (re-pin, wave-opus55).
- **Tips finais** (branches locais `s357/*`, commits wip que NÃO landam como estão; a esteira
  confere cada tip antes de aplicar e landa só os caminhos da unidade):
  - `s357/codex-pin` `69b7a593` — plano + pack `PLAN-193/codex-pin-0156/`.
  - `s357/relaunch-optb` `1c94a19c` — opção B do `relaunch --out`.
  - `s357/fn04` `9cb92fb5` — `wave-fn04/fn04.patch` sha256 `cd31657c…`; rail r3 `APPROVE`.
  - `s357/wave-opus55` `1730312b` — `wave-opus55/WOPUS55.patch` sha256 `ed3dd914…` (76 paths,
    12 canônicos); rail r4 `APPROVE`; trailer `Pair-Rail-Reviewed` preenchido.
  - `s357/fastlane` `e63a4e1e` — via expressa (3 scripts, 3 testes, 1 doc).
  - `s357/freefix` `880300f6` — varredura (15 paths).
  - `s357/rckit`, `s357/relmeta` e `s357/docs`: tips fixados na integração (este commit não se
    auto-referencia).
- **Janelas sem commit:** entre um SIGN e o seu LAND (`OWNER-OPUS55-LAND.sh` exige
  `Anchor-SHA` = HEAD); fora de `PLAN-193/relmeta/`, entre a derivação da relmeta-142 e o SIGN
  dela (o SIGN recusa o patch como velho). O closeout do GA 1.4.1 (`CLAUDE.md` + LEDGER do
  PLAN-192) fica para DEPOIS da rc.1 da 1.4.2, citando só o PLAN-193.
- **Ordem da manhã (Owner; como a esteira a executa):**
  1. GA v1.4.1 — `.claude/plans/PLAN-192/OWNER-GA-CUT.sh` (`main` congelado do G0 ao passo 16).
     O passo 6 (re-pass) gasta cota do Codex, esgotada até 2026-09-25 16:43 (-03). Se o corte
     não terminar, nada abaixo roda.
  2. Lands livres, lote 1: `.tag-push-epoch` do GA; plano + pack do re-pin; kit da rc.1; o
     Owner ratifica as 6 decisões pendentes da opção B (gravadas em
     `.claude/plans/PLAN-190-FOLLOWUP-relaunch-out-partial-write.md` no mesmo land; sem isso
     nem a opção B nem o FN-04 landam e a 1.4.2 para); opção B; materiais do FN-04
     (`PLAN-193/wave-fn04/`, `PLAN-193/wave-fn04-approved.md`); push (o SIGN do re-pin exige
     HEAD = `origin/main`).
  3. SIGN do re-pin do codex 0.156.1 — `PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh` (o global
     0.156.1 já instalado — não reinstalar). Push.
  4. wave-opus55 — materiais (land livre) + push; `PLAN-193/wave-opus55/OWNER-OPUS55-SIGN.sh`
     e, SEM commit no meio, `PLAN-193/wave-opus55/OWNER-OPUS55-LAND.sh` (ADR-149 Amendment 3).
  4b. Lands livres, lote 2: via expressa + varredura, DEPOIS do LAND da wave (antes dele o
     `--derive-patch` do SIGN da wave sai com outro sha256), com o `env-inventory` regenerado
     com os 2 nomes novos. Push.
  5. FN-04 — `PLAN-193/wave-fn04/OWNER-FN04-SIGN.sh` (assina e landa num passo). Push.
  5b. Portão de docs, ANTES da derivação da relmeta: conferir o `[1.4.2]` contra os sentinels
     landados (`wave-opus55-approved.md`, `wave-fn04-approved.md`, `pin-0156-approved.md`) e
     contra o veredito do GA; landar o commit de `s357/docs` (`CHANGELOG.md` `[1.4.2]` + este
     LEDGER); push (o SIGN da relmeta exige HEAD = `origin/main`).
  6. relmeta-142 — branch `s357/relmeta`: derivar, commitar só `PLAN-193/relmeta/`, push, SIGN.
  7. CI verde no HEAD; rc.1 da 1.4.2 — kit da branch `s357/rckit` → hold ADR-103 ≥ 24 h → GA
     1.4.2 → npm. O re-pass da rc.1 também gasta cota do Codex.
- Checagens do 5b, antes de landar o docs: tag `v1.4.1` ancestral do HEAD;
  `.claude/governance/pair-rail-verdict-v1.4.1.md` no HEAD; plano no HEAD com OQ-8 e OQ-9; todo
  caminho que o `[1.4.2]` cita existe no HEAD; `derive-settings-baselines.py --check
  scripts/upgrade.sh` rc 0 na árvore com as tags GA (medido 2026-09-25 na árvore composta dos
  tips acima, ainda sem a tag `v1.4.1`: `CHECK: MATCH (5 leaf keys)`).
- Dívida assinada que a 1.4.2 re-declara: anexo P1 da v1.4.0 SEM release atribuída (OQ-3;
  condição 1 de `PLAN-192/repass-ga/CONDITIONS-ga.md`); os abertos da 1.4.1 (entrada `[1.4.1]`,
  condições e vereditos do GA). Condição 23: o FN-04 cura o CASO (o ledger do `Workflow`); a
  CLASSE fica declarada, não curada (residual do `wave-fn04-approved.md`), e o `[1.4.2]` diz
  isso (FN04-C1). O passo 5 é obrigatório antes do passo 7.
- Regras de parada do rail: W3 (wave-opus55) pré-registrada 2026-09-23, ≤ 3 rodadas; a OQ-10
  (2026-09-24) abriu UMA rodada 4 final; r1–r3 `REJECT` (um P2 cada, classes diferentes), r4
  `APPROVE` sobre `ed3dd914…`. FN-04: ≤ 3 rodadas; r3 `APPROVE` sobre `cd31657c…`. `NO-GO` só
  por P0 ou condição declarada FALSA.
