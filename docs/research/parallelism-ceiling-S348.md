# Teto de paralelismo — o que ficou medido (fechamento do PLAN-187, S348)

**Data:** 2026-09-06 · **Sessão:** S348 · **Autor:** Technical Writer (skill `technical-writing`)
**Fecha:** PLAN-187, por veredito 3/3 da revisão de portfólio S348
(`.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md:53` e `:70`).
**Fonte única dos números:** `.claude/plans/PLAN-187-parallelism-ceiling-study.md` §1 (fatos 1–26,
cada um já com o comando que o reproduz) e o CSV rastreado
`.claude/plans/PLAN-187/s345-night-sampler.csv` (102 amostras, `2026-09-04T20:36:35` →
`2026-09-05T05:01:54`).

> **Claim honesta (AGENTS.md §0, citada também em PLAN-187:26-28):** este relatório não afirma
> nenhum ganho de velocidade do framework. Ele descreve o teto de PARALELISMO DE SUBSTRATO
> observado — quantos agentes e revisores simultâneos o ambiente aguentou antes de algo recusar —
> não quanto tempo um plano leva para fechar.

## Glossário

- **pack** — um lote de trabalho (patch + evidência) preparado para revisão/assinatura, normalmente
  com menos de 400 linhas.
- **rodada de rail** — uma passada de revisão adversarial (por outro modelo, ex. Codex) sobre um
  pack ou sobre texto vivo, que aprova ou aponta defeitos.
- **cota** — o limite de uso da CONTA (janela de 5 horas + limite semanal), diferente da capacidade
  da máquina (CPU/memória).
- **worktree** — uma cópia de trabalho adicional do mesmo repositório Git (`git worktree add`),
  usada para construir em paralelo sem conflitar com a árvore principal.

## 1. O que foi medido

Todos os números abaixo já estavam landados antes deste relatório (noite autônoma de 2026-09-05,
sessão S345); nenhuma medição nova foi executada para fechar este plano — ver §2.

| Área | O que foi observado | Fonte |
|---|---|---|
| Capacidade nominal da máquina | cap de **14** agentes concorrentes por workflow (`min(16, CPUs−2)`, 16 núcleos nesta máquina); 1000 por vida do workflow | PLAN-187 fato #1, linha 34 |
| Cota é da CONTA, não do terminal | 3 contas Claude queimadas em ~2 h cada com 15–20 agentes; login na mesma sessão retoma o trabalho | fato #4, linha 37 |
| Máquina sob carga real (14 frentes + 11 revisões codex) | load **26** em 16 núcleos; memória livre **0,4 GB** de 48 GB; RSS total dos processos `claude` **2,5 GB** | fato #5, linha 38 |
| Codex sob carga | 11 revisões simultâneas medidas; 22 rodadas/hora; **11 rodadas com 429 real** no dia; brief de 60 KB em effort `max` estoura em 420 s | fato #6, linha 39 |
| Grok sob carga | brief de 25 KB (argv) e de 40 KB (artefato) mortos por alarme aos 5 e 15 min | fato #7, linha 40 |
| Teste controlado N=8 vs N=16 (S344) | N=8: 8/8 completos, 0 erros, 6 min. N=16: **6/16 completaram, 10 recusados pelo servidor** com o aviso explícito «Server is temporarily limiting requests (**not your usage limit**) · Rate limited» — a cota da conta estava em 50 % no momento | fato #10, linha 43 |
| Contaminação da medição N=16 | uma SEGUNDA sessão Claude, mesma conta e mesma máquina (outro repo), rodava 8 workflows com ≥8 agentes vivos durante o teste — o «6/16» é o teto da SOMA das duas sessões, não desta sessão isolada | fato #10, linha 43 |
| Memória mínima observada (noite passiva, sem stress sintético) | **27 MB** livres, com 40 worktrees registrados; **51 de 102** amostras abaixo de 1 GB | fato #16, linha 49 |
| Janela de cota subindo (Claude, 5 h) | **+22,63 pontos percentuais por hora**, de 0 % às `2026-09-05T00:01:43` a 100 % às `2026-09-05T04:26:53` (4h25min) | fato #20, linha 53 |
| Cota do Codex esgotada (declarado pelo ledger, não amostrado) | limite de uso batido às 22:55 (mensagem: «You have hit your usage limit … try again at Sep 7th»); restaurada às 01:23 por reset semanal | fato #22, linha 55 |

## 2. Por que o plano fecha sem as medições formais dos AC-1 a AC-4

A revisão de portfólio S348 (`.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md`)
votou **3/3 fechar** o PLAN-187, com a razão registrada na própria tabela (linha 53): *"a pergunta
já foi respondida e o AC-4 é inobservável por construção (RSS por agente não é observável; custo por
worktree não é derivável)"*. O item 3 da mesma revisão (linha 70) já previa que o único entregável
deste fechamento seria o relatório do AC-5.

Razão por acceptance criterion:

- **AC-1 e AC-3** (teto de agentes por máquina; teto de revisões Codex/Grok) — a pergunta original
  pedia um stress test controlado com o instrumento `stress-parallelism` (PLAN-187 §4). Esse
  instrumento nunca chegou a rodar em degraus completos; em vez disso, os fatos 11–26 (medidos na
  própria noite autônoma de 2026-09-05, land livre `p187-night-facts` — PLAN-187 linha 169) e o
  teste parcial de fato #10 já respondem à pergunta prática: o teto que efetivamente interrompeu
  trabalho foi cota + recusa do servidor (§4 abaixo), não uma contagem fixa de agentes por máquina.
  Repetir o instrumento não mudaria essa resposta.
- **AC-2** (dois workflows na mesma sessão; dois terminais em duas contas) — esta mesma medição já
  tem dono no `PLAN-186-orchestrator-operating-model.md:192` («AC-2 (W0) Teto de concorrência: N
  máximo sem 429 em 3/3 repetições por N... p50/p95 e consumo da janela por N»). Medir de novo aqui
  duplicaria esse AC de outro plano.
- **AC-4** (RAM por agente e por worktree) — inobservável por construção, não por falta de tempo. O
  próprio PLAN-187 documenta por quê (linhas 76–89, resumido na linha 169): o amostrador viu
  exatamente **um** processo casando o binário `claude` nas 102 amostras (fato #18, linha 51), então
  o RSS medido (fato #17) é de um processo, não de um agente — dividir por N produziria um número
  que muda só porque N muda, sem o RSS mudar. Por worktree, a única relação calculável no CSV é uma
  correlação de Pearson bruta de **−0,7502** entre `worktrees` e `mem_free_mb` (PLAN-187 linha 84),
  confundida pelo tempo (as duas séries sobem/descem ao longo da mesma noite) — não isola um custo
  por unidade.

## 3. O que este estudo NÃO mediu

- **RSS por agente individual.** O amostrador da noite S345 só enxerga um processo casando o
  binário `claude` (fato #18); não há como decompor esse número por agente vivo dentro dele.
- **Custo de RAM por worktree.** Existe só uma correlação descritiva (Pearson −0,7502, PLAN-187
  linha 84), sem baseline nem atribuição por processo — não é um custo por unidade.
- **A topologia multi-terminal.** A topologia candidata de três terminais (PLAN-187 §3, linhas
  121–134: um terminal de construção, um terminal em clone próprio, um terminal para medições
  isoladas) nunca foi testada na prática. A pergunta que decidiria se ela merece um ADR próprio
  (OQ-2, PLAN-187 linha 160) segue sem resposta.

## 4. Conclusão em 3 linhas

1. **Não foi CPU nem memória que parou o trabalho.** Com 14 frentes e 11 revisões Codex ativas ao
   mesmo tempo, a memória livre caiu a 0,4 GB e o load subiu a 26 (fato #5) — carga real, mas sem
   nenhuma falha atribuída diretamente a isso nos fatos medidos.
2. **Dois tetos diferentes da máquina pararam o trabalho: concorrência do servidor e cota da
   conta.** Um teste de 16 chamadas Claude simultâneas devolveu 10 recusas explicitamente rotuladas
   pelo servidor como «not your usage limit» — um limite de CONCORRÊNCIA, não de cota, e a cota da
   conta estava em 50 % no momento (fato #10). Em paralelo, a cota realmente se esgotou ao longo da
   noite: a janela de 5 horas do Claude foi de 0 % a 100 % em 4h25min (fato #20) e uma conta do
   Codex bateu seu limite de uso e ficou bloqueada por horas (fato #22).
3. **Trocar de conta ou abrir mais terminais não resolve nenhum dos dois.** O próprio teste de
   N=16 já estava contaminado por uma segunda sessão na MESMA conta (fato #10); nada neste estudo
   isolou um limite físico de máquina ou de terminal como o fator que realmente interrompeu o
   trabalho. É por isso que a revisão de portfólio fechou o plano nos fatos já medidos, em vez de
   exigir o experimento controlado original.

## Status deste fechamento

AC-5 entregue por este documento. AC-1 a AC-4 encerrados sem medição nova, pelas razões do §2 —
ver o checklist e a seção `## Abandonment reason` em
`.claude/plans/PLAN-187-parallelism-ceiling-study.md`.
