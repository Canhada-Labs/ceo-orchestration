---
id: PLAN-190-FOLLOWUP-consumer-adoption-metrics
parent: PLAN-190
title: Adoção no consumidor, métricas da janela de 2 semanas e as ondas não entregues do PLAN-190 (W4.2, W4.3, W5, W6)
status: draft
created: 2026-10-10
owner: CEO
depends_on: [PLAN-190]
level: L3
tags: [workflow, recovery, quota, consumer, distribution, followup]
---

## Context

O PLAN-190 fechou em 2026-10-10 com W1, W1.1, W2 (CLIs) e W3 entregues
(`## Success criteria` e `## Progress log` do pai). O que não foi entregue
vem para cá. Escopo copiado do pai, sem os nomes nem os dados do consumidor
(regra do pai: fixtures neutras).

1. **Adoção no consumidor.** `upgrade.sh` no consumidor depois de cada wave.
   Bloco COMMON de aprovação (`approval_gate.py`, W3) no gate do script do
   consumidor. Prompts de fase que leem e escrevem o `phase_checkpoint.py`
   (W2). `ceo-launches.py check` no rito de retomada. O código do consumidor
   fica fora do repositório público.
2. **Métricas da janela de observação de 2 semanas depois da adoção** (critério do pai): fases perdidas
   < 2 % dos starts (baseline S354: 15,5 %); reexecução de chave concluída = 0
   (baseline: 16 % dos starts); tokens por entrega aprovada REPORTADOS por
   sessão (roteiro da W0.2 em `docs/workflow-recovery.md`, seção «Measuring
   "quota per approved delivery"»).
3. **W4.2 — `.claude/scripts/quota_watch.py`** (livre, determinístico, sem
   LLM). Lê o snapshot `statusline-snapshot.json` (a W4.1 do pai), trata
   ausência ou idade > N min como desconhecido, nunca como saldo livre.
   Classifica o último erro de quota em «esperar o reset» × «parar e avisar»
   (`session limit`, `spend limit`, `org_spend_cap_reached`). `admit --max-heavy
   N` responde `ADMIT|HOLD|UNKNOWN`. Dois fatos medidos depois que o pai foi
   escrito mudam o desenho:
   - o `used_pct` do sidecar NÃO prova exaustão: `five_hour` estava em 35 % no
     instante de uma recusa (`CLAUDE.md` §5, night-runs S328/S329);
   - o `autoContinueAtUsageLimit` nativo retoma a sessão principal (desfecho
     (a) do AC-4 do `PLAN-169-FOLLOWUP-quota-resume-and-probes`), e o registro
     `.claude/plans/PLAN-169/ac4-quota-window-S362-S363.md` viu também
     «weekly limit» e «individual spend limit». O `quota_watch` serve à
     ADMISSÃO, não à retomada.
4. **W4.3 — enforce no hook de lançamento.** Só depois de uma janela advisory
   com tabela would-block (regra de parada do pai).
5. **W5.1 — `.claude/scripts/repin.py`** (manifesto TSV arquivo × marcador ×
   comando-de-medida; re-mede e reescreve o valor exato; conflito semântico ⇒
   lista para análise).
6. **W5.2/W5.3 — contexto e effort por fase.** `omitClaudeMd` e contrato mínimo
   por papel; spec por fase; saídas de teste com log completo em arquivo;
   effort avaliado com qualidade medida. Modelos do perímetro financeiro não
   descem.
7. **W6 — pernas no smoke-install** (`scripts/tests/smoke-install.sh`, oráculo
   0): presença do hook e das CLIs, registração por cerimônia, `ceo-launches.py
   check` funcional, `upgrade.sh --dry-run` NO-OP na segunda passada, e uma
   perna por caso da precondição de distribuição declarada em
   `docs/workflow-recovery.md:232-233`.

## Goal

O consumidor roda a execução autônoma com o ledger, o checkpoint e a aprovação
por código, e as métricas da janela de 2 semanas mostram se as perdas demonstradas caíram.

## Items

### W1 — pernas do smoke-install (item 7)  [P0]  (livre)
### W2 — `quota_watch.py` (item 3)  [P1]  (livre; enforce só depois de medir)
### W3 — adoção no consumidor e janela de 2 semanas (itens 1 e 2)  [P1]
### W4 — W4.3 em modo bloqueante (item 4)  [P2]  (canônico: hook de lançamento)
### W5 — `repin.py` e contexto/effort por fase (itens 5 e 6)  [P2]

## Open questions

- **OQ-1.** O `repin.py` (item 5) ainda tem comprador? A síntese de fechamento
  da S363 recomendou declará-lo obsoleto, sem registrar o motivo. Decisão do
  Owner.
- **OQ-2.** W5.2/W5.3 ficam aqui ou vão para a W4 do PLAN-191 («Poda local de
  resultados de ferramenta»), como a mesma síntese sugeriu?
- **OQ-3.** O custo fica a firmar no refinamento, em tokens e sessões
  (ADR-081). A síntese estima 60–120k para as pernas do smoke e 150–250k para
  o `quota_watch.py`.

## Success criteria

- [ ] Smoke-install verde com as pernas do item 7; um consumidor isolado recebe hook e CLIs pelo `upgrade.sh`.
  Check: `bash scripts/tests/smoke-install.sh <dir-descartável>`
- [ ] `quota_watch` distingue reset de teto de gasto em todos os tipos de recusa vistos; desconhecido nunca vira «livre».
  Check: teste unitário com uma fixture por tipo de recusa
- [ ] Métricas do consumidor depois da janela de observação de 2 semanas de adoção, reportadas com data e substrato.
  Check: none (medição no consumidor, fora deste repositório)
- [ ] W4.3 decidida pela tabela would-block da janela advisory (flip ou não-flip registrado).
  Check: none (decisão registrada)
