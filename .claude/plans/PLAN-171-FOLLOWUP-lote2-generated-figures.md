---
id: PLAN-171-FOLLOWUP-lote2-generated-figures
parent: PLAN-171
title: Resíduos do instrumento do censo W0 — figuras literais do lote 2 e censo W0-delta do check_workflow_launch
status: draft
created: 2026-10-10
owner: CEO
depends_on: [PLAN-171]
tags: [audit, census, instrument, followup]
---

## Context

O PLAN-171 fechou na W0 em 2026-10-10, com 52 de 52 linhas de gate providas
de controle positivo (adendo no §6 de `PLAN-171/w0/W0-consolidated-verdict-S348.md`).
Ficaram dois resíduos do instrumento do censo, nenhum deles critério da W0.

1. **Figuras literais do lote 2.** A cura pós-land do lote 2 converteu para
   geração por instrumento só a contagem do §2 e o Apêndice C. As figuras de
   §1, §4, §5 e dos Apêndices A, B e D de `PLAN-171/w0/lote-2-S347.md`
   continuam vindo do `gen-report.py` do pack do lote 2, como literais
   (`PLAN-171/w0/s345-p171-w0-lote2-fix/rail-land-round-1.md:54-57`).
   **Achado do fechamento:** nenhum gerador do pack está no repositório. Em
   2026-10-10, `git ls-files` não lista `gen-report.py`, `gen-count.py`,
   `measure-optin.py` nem `partition.py`. Re-derivar exige reconstruir o
   instrumento, ou declarar as figuras como literais datadas.
2. **Censo W0-delta do `check_workflow_launch.py` (opcional).** O hook entrou
   no `.claude/settings.json` em 2026-09-17 (`075beed9`), depois do censo. Tem
   suíte própria, mas não foi medido pelo método das três metades: verde como
   está, vermelho com o enforcement removido numa worktree descartável, verde
   de novo depois do `git restore`.

## Goal

Toda figura dos relatórios da W0 tem fonte reproduzível ou é declarada literal
com data, e o roster vivo de hooks tem censo completo.

## Items

### W1 — figuras do lote 2  [P3]  (livre: relatórios de plano)
- Reconstruir o gerador e commitá-lo junto do relatório, OU anotar cada figura
  como literal datada, com a fonte.

### W2 — censo W0-delta  [P3, opcional]  (livre: relatório novo em `PLAN-171/w0/`)
- Três metades sobre o `check_workflow_launch.py`, em worktree descartável
  com limpeza confinada.
- A síntese de fechamento da S363 estima 60–120k tokens, 1 sessão.

## Success criteria

- [ ] Nenhuma figura de `lote-2-S347.md` sem fonte reproduzível ou sem a marca de literal datado.
  Check: none (doc-only)
- [ ] (opcional) Relatório W0-delta com as três metades do `check_workflow_launch.py`.
  Check: `ls .claude/plans/PLAN-171/w0/` mostra o relatório novo
