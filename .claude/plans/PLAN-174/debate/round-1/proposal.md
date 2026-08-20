---
plan: PLAN-174
round: 1
created_at: 2026-08-20
scope: "W1-W2 (catálogo + lint) sob waiver do Owner S316; W3-W4 mantêm gate original"
---

# Proposta em debate — PLAN-174 round 1 (escopo W1-W2)

Plano completo: `.claude/plans/PLAN-174-ceremony-generation.md`.

## Tese

A MAIOR fatia isolada do custo de reviewer do trem v1.3.0 foi bash
descartável de cerimônia: 31 dos 38 rounds da madrugada revisaram
scripts one-shot (~94KB, 6 scripts OWNER-* num único trem), e ~40-50%
dos achados são 5-6 classes mecânicas RECORRENTES. Hipótese: se os
cortes rc/GA forem EMITIDOS por gerador a partir de input declarativo
(1-2KB), o rail revisa o INPUT + o gerador (uma vez, com soak) em vez
de 42KB de bash novo por trem.

## Escopo DESTE debate (waiver S316)

O Owner waivou o milestone "W3/W4 do 169" para **W1-W2 apenas**,
autorizando executá-las ANTES dos trens 182/183 exatamente para
baratear as cerimônias deles. W3 (gerador) e W4 (piloto shadow) mantêm
o gate original e NÃO estão em execução agora.

- **W1 — catálogo das classes recorrentes**, extraído dos rounds REAIS
  (`.claude/plans/PLAN-166/repass-rc3-scripts/`, 111 arquivos:
  diff-cures-round5..31.patch + payloads redacted + PROVENANCE +
  MANIFEST). As 6 classes conhecidas: rc engolido em
  command-substitution; `|| true` mascarando falha; `grep|tail -1` em
  VERDICT; `git add` de diretório; symlink em hash; set-equality
  ausente. Cada classe vira (a) regra de lint executável e (b)
  construção proibida/gerada no template. AC: ≥6 classes, cada uma com
  exemplo REAL citado (round/arquivo) e caso-vermelho executável, +
  qualquer classe NOVA achada na extração.
- **W2 — lint dedicado de ceremony-script** (Python stdlib, ≥3.9,
  fail-closed nas classes do W1) sobre `.claude/plans/*/OWNER-*.sh` e
  scripts de corte; roda em pre-commit E CI. ACs: positive control
  (remover o lint ⇒ vermelho; um caso-vermelho por classe no CI) e
  ZERO falso-positivo sobre os scripts de cerimônia HISTÓRICOS já
  landados (baseline de sanidade).

## Decisões já tomadas (não re-litigar)

- Ratificação S302f (Owner) + rail Codex r1→r3 GO no r2 cobrem o
  conjunto do plano; este debate cobre o Gate 3 da EXECUÇÃO de W1-W2.
- O gerador (W3) é superfície canônica com cerimônia própria — fora
  deste escopo.
- Doutrina: nenhuma mudança no CONTEÚDO das garantias de cerimônia
  (sentinel, anchor-sha, dois rails de signer, scope=∅ antes de
  commit).

## Questões abertas para os críticos

1. **Layout de entrega**: o plano não fixa paths — catálogo em
   `.claude/plans/PLAN-174/catalog.md`? Lint em
   `.claude/scripts/local/`(não-canônico, editável sem cerimônia) ou
   `.claude/scripts/` com testes? Onde mora o wire de pre-commit/CI?
2. **Fail-closed vs baseline**: o lint é fail-closed nas classes do W1,
   mas o AC exige zero falso-positivo sobre históricos — como tratar um
   histórico que VIOLA uma classe (violação real antiga)? Waiver por
   arquivo? Baseline pinada?
3. **Fronteira W2/CI**: o wire em CI toca `.github/workflows/` (vivo) —
   isso cruza com o gate de drift template-vs-vivo do PLAN-183 W2?
4. **Escopo do glob**: `.claude/plans/*/OWNER-*.sh` cobre os scripts de
   corte reais? (ex.: `OWNER-GA-CUT.sh`, `OWNER-RATIFY-*.sh` moram em
   lugares distintos — `~/canhada-labs/` fora do repo já apareceu no
   histórico.)
