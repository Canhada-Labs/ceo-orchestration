---
plan: PLAN-166
round: 1
created_at: 2026-08-05
---

# PLAN-166 — Proposta para debate (round 1)

Plano completo: `.claude/plans/PLAN-166-release-hold-findings-closure.md`.
Evidência do re-pass: `.claude/plans/PLAN-166/repass-r1/` (verdito NO-GO,
payload redigido, MANIFEST verificado).

## Tese

O re-pass ADR-103 do codex contra `v1.3.0-rc.1` voltou **NO-GO** com 6
findings, todos verificados manualmente contra o código (nenhum refutado).
O Owner decidiu: **corrigir todos os 6 antes do GA**. Como F1/F3/F4 mudam
superfícies congeladas na rc.1 (workflows, upgrade, teste de paridade), o
GA passa a ser via **rc.2 + novo hold de 24h**.

## Os 6 findings (resumo; detalhe no plano)

- **F1 (P0, canonical):** `npm-publish.yml` e `release.yml` disparam ambos
  em `push: tags: v*` e nada acopla o publish ao `release-gate` — a única
  barreira é a aprovação manual do environment `production-npm`. O driver
  ainda afirma (linha 515) que `release.yml` publica no npm — claim falsa.
- **F2 (P1, livre):** `bump --stable` no dia seguinte NÃO é no-op: os 4
  stamps `last-reviewed:` re-datam com `date.today()`, o índice fica sujo,
  nasce um commit pós-preflight que `tag()` assina sem CI ter visto (tag
  valida só VERSION). O fix r4 cobriu "VERSION já correta"; o hold de 24h
  GARANTE que a data muda.
- **F3 (P0, canonical):** upgrade v1.2→v1.3 entrega os hooks novos mas NÃO
  `SPEC/v1` nem `VERSION` (fora do `_framework_manifest_set.sh`; o install
  entrega). Adopter fica com enforcement v1.3 + contrato v1.2 + VERSION
  1.2.0 — e `sentinel-format.schema.md` mudou +21 linhas NESTA release
  (trust boundary do unlock).
- **F4 (P1, teste):** gate de paridade install/upgrade compara
  `_framework_target_entries()` consigo mesma — "identical by
  construction" (admitido em comentário). Não pode falhar.
- **F5 (P1, livre):** `README.pt-BR.md` com 4 contagens stale e AUSENTE do
  `verify-counts.sh` (classe unwatched-doc).
- **F6 (P2, misto):** help do driver descreve v1.2.0/"six sites";
  `INSTALL.md:627` descreve migração obsoleta 60→150.

## Estrutura proposta

- **W0 (L2, sem cerimônia):** landar evidência (feito); F2 + F5 + F6-livre.
- **W1 (L3+, cerimônia única):** F1 + F3 + F4 + F6-canonical, staged com
  MANIFEST rastreado + `shasum -c` fail-closed.
- **W2:** re-pass r2 → rc.2 → hold 24h → re-pass final → GA.

## Decisões de design ABERTAS (o que o debate deve resolver)

**OQ-1 — Direção do F1.** Duas opções:
  (a) `npm-publish.yml` ganha step pré-publish que verifica conclusão
      SUCCESS do `release.yml` para o MESMO SHA da tag (poll via `gh api`),
      mantendo trigger e environment atuais;
  (b) mover o job de publish para dentro de `release.yml` com
      `needs: release-gate`.
  Restrição dura: npm OIDC trusted publishing está configurado para o
  workflow ATUAL (`npm-publish.yml`) — mudar o workflow de origem pode
  quebrar o publish. (b) só é viável com reconfiguração coordenada no
  npmjs.com. Risco assimétrico: errar aqui falha para "não publica"
  (custa um ciclo), não para "publica sem gate".

**OQ-2 — Semântica de idempotência do F2.** Duas opções:
  (a) bump em árvore já na versão alvo vira no-op TOTAL (não re-data
      stamps — datas continuam as do bump original);
  (b) comparar o diff pós-substituição IGNORANDO os stamps; se só datas
      mudariam, restaurar e declarar no-op.
  Tensão: os stamps `last-reviewed:` existem para dizer quando o doc foi
  revisado por último; re-datá-los num no-op é claim falsa (ninguém
  re-revisou), então (a) parece mais honesto — mas o GA promove a MESMA
  árvore, e há quem espere o stamp do dia do GA. Decidir e justificar.

**OQ-3 — Escopo do F3.** `SPEC/v1` + `VERSION` viram superfícies de
  upgrade. Semântica de backup/classificação para adopter que EDITOU seu
  SPEC local: sobrescrever com backup? three-way? Recusar e instruir?
  A resposta define o patch do `_framework_manifest_set.sh`.

**OQ-4 — F4 sem tautologia.** Derivação independente dos dois conjuntos:
  executar install e upgrade em fixtures reais e comparar árvores
  resultantes, com controle positivo (divergência plantada TEM de falhar).
  Custo/benefício de e2e no CI vs teste local-only.

## Restrições

- Python stdlib-only ≥3.9; hooks fail-open em infra, fail-closed em input.
- Cerimônia canonical exige sentinel GPG do Owner; agrupar TODOS os
  patches canônicos numa cerimônia única.
- Sem claim de speedup em qualquer superfície.
- Gate novo nasce com controle positivo (contrato S291).
