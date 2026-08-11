---
id: PLAN-174
title: Geração de cerimônia de release — template endurecido + lint de classes + cortes rc/GA declarativos
status: draft
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169]
budget_tokens: 200-400k (firmar no refinamento pré-reviewed)
budget_sessions: 3-5
context_risk: medium
external_wait: "milestone: pós-GA v1.3.0 + W3/W4 do 169 landados (NÃO o 169 inteiro). DEADLINE: slice W1-W3 verde até D-2 do corte v1.4.0-rc.1, senão ABORT-PATH: o corte usa a cerimônia manual e o piloto migra p/ o trem seguinte"
tags: [release, ceremony, codegen, review-cost, seed]
---

# PLAN-174 — A máquina gera o que hoje se revisa

> **SEMENTE (S302, 2026-08-11).** Nascida da auditoria total
> (framework-total-audit, 14 agentes): a MAIOR fatia isolada do custo
> de reviewer do trem v1.3.0 foi bash descartável de cerimônia — 31
> dos 38 rounds da madrugada revisaram scripts one-shot (~94KB de
> bash bespoke, 6 scripts OWNER-* distintos num único trem), não
> produto. E ~40-50% dos achados desses rounds são 5-6 classes
> mecânicas RECORRENTES que se repetem literalmente entre rounds.

## 1. Hipótese

Se os cortes rc/GA forem EMITIDOS por um gerador a partir de um input
declarativo pequeno (1-2KB: versão, tag, superfícies, gates, ordem),
o rail passa a revisar o INPUT + o gerador (uma vez, com soak) em vez
de 42KB de bash novo por trem. Efeito esperado (a medir): a classe
"27 rounds de scripts" cai para ~5.

## 2. Escopo

- **W1 — catálogo das classes recorrentes** extraído dos rounds reais
  (PLAN-166 repass-rc3-scripts/): rc engolido em command-substitution;
  `|| true` mascarando falha; `grep|tail -1` em VERDICT; `git add` de
  diretório; symlink em hash; set-equality ausente. Cada classe vira
  (a) regra de lint executável e (b) construção proibida/gerada no
  template.
- **W2 — lint dedicado de ceremony-script** (stdlib, roda no
  pre-commit e no CI) sobre `.claude/plans/*/OWNER-*.sh` e scripts de
  corte; fail-closed nas classes do W1.
- **W3 — estender `generate-ceremony.sh`** para emitir cortes rc/GA
  de input declarativo; o gerado passa `bash -n` + lint W2 por
  construção; corpo ASCII-safe (lição heredoc-em-$()); retomada
  (MONITOR/SKIP_TO_PUSH/TERMINAL) vira feature do template, não
  reinvenção por trem.
- **W4 — piloto no primeiro corte da v1.4.0**: rail revisa input
  declarativo + diff do gerador; contar rounds e comparar com a
  baseline v1.3.0 (12-17h de reviewer externo/trem).

## 2b. Controles e rollback (Codex r1 — obrigatórios antes de W4)

- **Positive control do lint (W2):** o gate só entra com controle que
  FALHA quando o enforcement é removido (alinhado ao censo do
  PLAN-171 W0); cada classe do W1 tem caso-vermelho no CI.
- **Equivalência de invariantes (W3):** cerimônia GERADA passa suíte
  de equivalência — sentinel/anchor-sha/scope/dois-rails-de-signer
  PRESENTES e verificados; dry-run em clone compara as GARANTIAS
  (não os bytes) contra a cerimônia manual baseline; qualquer
  divergência de garantia = vermelho.
- **Rollback e modo do piloto (r2 P2 — desambiguado):** trem 1
  (v1.4.0) = piloto SHADOW: a cerimônia gerada roda em dry-run em
  clone, EM PARALELO à cerimônia manual que executa o corte real;
  trem 2 = produção com a gerada, com último ponto seguro de fallback
  ANTES de tag/publish (a fronteira irreversível nunca roda pela via
  nova sem a manual disponível). A manual permanece CANÔNICA até os
  dois trens verdes (1 shadow + 1 produção); falha em qualquer ponto
  ⇒ fallback manual sem cerimônia extra.

## 3. Guard-rails

- O gerador é superfície canônica: cerimônia + pair-rail no gerador,
  UMA vez — é exatamente a troca que paga (revisão amortizada).
- Nenhuma mudança no CONTEÚDO das garantias da cerimônia (sentinel,
  anchor-sha, dois rails de signer, scope=∅ antes de commit).
- Se o piloto W4 não reduzir rounds ≥40% vs baseline, reportar
  NEGATIVO e manter template+lint (W1/W2 valem sozinhos).
