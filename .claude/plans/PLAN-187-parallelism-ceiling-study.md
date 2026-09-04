---
id: PLAN-187
title: "Estudo do teto de paralelismo: agentes, revisores externos, cópias do repo, terminais e contas"
status: draft
created: 2026-09-04
owner: CEO
depends_on: [PLAN-186]
level: L3
budget_tokens: "estudo 150-300k (medições + relatório); a wave de adoção é plano próprio"
budget_sessions: 1-2
context_risk: low
external_wait: "nenhuma para o estudo; a adoção (topologia multi-terminal) exige decisão do Owner e ADR"
eta_calendar: "estudo em 1 sessão dedicada (outro terminal, outra conta); adoção depois"
tags: [paralelismo, quota, workflow, worktree, multi-terminal, codex, grok, substrato]
---

# PLAN-187 — Estudo do teto de paralelismo

> **Pedido do Owner (S344, 2026-09-04, verbatim):** «faz um stress test tentando pararelizar o
> maximo pra gente ganhar velocidade, usa GROK tbm, e me diz quantos vc aguenta aqui tbm de
> agentes etc.. meu objetivo é ganhar velocidade bem orchestrada quanto mais pararelo melhor,
> inclusive vc poderia fazer copias do repo pra trabalhar sem conflito em varias frentes e planos
> ao mesmo tempo nao poderia ? varios terminais ? […] quero um estudo aprofundado disso qual o
> maximo de pararelismo possivel.»
>
> **Claim honesta do repo (AGENTS.md §0):** não há speedup GERAL do framework. Este plano mede o
> teto de paralelismo do SUBSTRATO (máquina, harness, contas, revisores externos) e propõe uma
> topologia; ele não promete tempo de fechamento de plano.

## 1. O que JÁ se sabe (medido, não lembrado)

| # | fato | valor | fonte |
|---|---|---|---|
| 1 | Cap de agentes concorrentes por Workflow | `min(16, CPUs−2)` = **14** nesta máquina (16 núcleos); 1000 por vida do workflow | doc do Workflow; `PLAN-186/w0/concurrency-probe-S339.md` (o 15.º espera slot) |
| 2 | API sem 429 até 14 concorrentes (tarefa trivial, n=1 por N) | p50 5 s (N=4) → 11 s (N=16): contenção suave | mesma sonda S339 |
| 3 | Custo fixo por spawn | ~95 k tokens de contexto por agente | mesma sonda; `PLAN-179/w0-measurement.md` (F≈97 k) |
| 4 | Quota é da CONTA, não do terminal | S344: 3 contas Claude queimadas em ~2 h cada com 15–20 agentes; `/login` na mesma sessão retoma (Workflow `resumeFromRunId` + `args.resume`) | S344, memória `project-s344-session-state` |
| 5 | Máquina sob 14 frentes + 11 revisões codex | load 26 em 16 núcleos; **memória livre 0,4 GB** de 48 GB (35 worktrees, 52 processos claude, 28 codex); RSS total claude 2,5 GB | S344 ~15:10 |
| 6 | Codex (ChatGPT plan, `gpt-5.6-sol`, effort `max`) | 11 revisões simultâneas medidas; 22 rodadas/h; **11 rodadas com 429 real** no dia (rajadas 11:29, 12:58–13:30); brief de 60 KB em `max` estoura 420 s | S344, `s344-packs/*/codex-*.txt` |
| 7 | Grok 0.2.106 (`grok-4.6-build`, sandbox `council`) | responde em 10 s a prompt trivial (US$ 0,012); **brief de 25 KB em argv e de 40 KB por artefato: morto por alarme aos 5 e 15 min, saída vazia** — sob carga de máquina | S344 sondas `xlane/` |
| 8 | Um land por vez na árvore viva | landers serializados por gate de árvore limpa; dois landers = colisão de index | S343 lição `feedback-workflow-script-authoring-lessons-s343` |
| 9 | Worktrees por frente já são a prática | cada construtor deriva numa sombra `git worktree add --detach`; refutadores em worktree próprio | S343/S344 |
| 10 | **Stress test S344 (instrumento §4, `[8,16]×1`, Sonnet, tarefa fixa ~1,2 k palavras, com 14 frentes + revisões codex rodando ao mesmo tempo)** | N=8: 8/8, 0 erros, 6 min, mem livre 12,3→10,8 GB, load 27→34. **N=16: 6/16 devolvidos; 10 mortos com «Server is temporarily limiting requests (not your usage limit) · Rate limited»** — teto de CONCORRÊNCIA do servidor, não a quota da conta (que estava em 50 %); o classificador de segurança do modo auto morreu pelo mesmo motivo no mesmo instante. **Conclusão preliminar: nesta máquina e sob a carga de hoje, o teto útil de chamadas Claude simultâneas fica entre 8 e 16 (somando TUDO: frentes, sondas, classificador); trocar de conta zera a quota mas NÃO sobe esse teto — só distribuir por máquina/IP ou escalonar lançamentos.** Repetir com a máquina ociosa (3 reps) para separar o teto do servidor da carga local. **CONTAMINAÇÃO DECLARADA (Owner, ~15:50): uma SEGUNDA sessão Claude na MESMA conta e na MESMA máquina (outro repo, `arbitrage-monitor`) rodava 8 workflows com ≥8 agentes vivos durante a medição — a barra dela mostrava 76 % da mesma janela de 5 h. O «8–16» é portanto o teto da SOMA das duas sessões (~14 + 8 + classificador + 16 sondas), não desta sessão; o número só vale como piso do teto conjunto.** | run `wf_5aa7b0e9-926`, journal no scratchpad da S344 |

## 2. Perguntas do estudo (cada uma com falsificador)

- **Q0 — Pré-condição de TODA medição: inventário de concorrência EXTERNA.** Antes de cada degrau, listar as outras sessões Claude da mesma conta/máquina (`ListAgents` + `pgrep -f claude`) e registrar quantos agentes vivos elas têm; uma medição com sessão concorrente ativa é rotulada CONTAMINADA e não entra na tabela do AC-1 (lição S344: o stress rodou com outra sessão de 8 workflows na mesma conta).
- **Q1 — Teto de agentes por máquina.** Quantos agentes Claude simultâneos esta máquina sustenta
  antes de (a) memória livre < 1 GB, (b) p95 de turno > 3× o p50 de N=4, (c) primeiro 429?
  Método: workflow `stress-parallelism` (§4) em degraus N ∈ {8, 16, 24, 32} com guarda de saúde
  (aborta o degrau se mem livre < 1 GB ou load > 2,5× núcleos), 3 repetições, tarefa fixa de
  ~2 k tokens de saída. Falsificador: se N=16 já degrada > 3×, o teto é 14 (o cap) e não vale
  abrir um 2.º workflow na mesma máquina.
- **Q2 — Dois workflows na mesma sessão.** O cap de 14 é por workflow; dois workflows dão 28?
  Medir com dois `stress-parallelism` lançados juntos (a S344 já rodou 5 workflows ao mesmo
  tempo com 19 agentes vivos: o cap por workflow NÃO limita a sessão).
- **Q3 — Dois terminais, duas contas, mesma máquina.** A quota some (é por conta); a CPU/memória
  não. Medir N=8 em cada terminal simultaneamente e comparar p95 com N=16 num só.
- **Q4 — Cópias do repo (clones/worktrees) por frente/plano.** Já é assim para CONSTRUÇÃO
  (sombras). O que NÃO paraleliza é o LAND (uma árvore viva, um commit por vez) e as
  ASSINATURAS (uma por vez, do Owner). Estudo: um clone completo por PLANO (não por frente),
  com `main` local próprio, landers landando no clone e um ÚNICO integrador fazendo `git
  pull --rebase` + push serializado. Risco: dois clones editando o mesmo arquivo canônico
  ⇒ conflito no integrador; mitigação = partição por PATH entre planos (tabela de posse).
- **Q5 — Revisores externos.** Codex: quantas revisões simultâneas antes do 429 (medir com
  N ∈ {4, 8, 12, 16} `codex exec --sandbox read-only` sobre briefs de 20 KB, 3 repetições);
  o efeito de effort `max` vs `xhigh` na duração; uma 2.ª conta via `--profile`. Grok: qual o
  MAIOR brief que responde em < 5 min sob carga (bissecção 5/10/20 KB); se < 20 KB, grok
  fica restrito a revisões de TEXTO/EVIDÊNCIA curtas.
- **Q6 — Memória.** Custo de memória por agente Claude (RSS/agente) e por worktree (páginas
  do checkout); quanto desse custo é `__pycache__`/node_modules duplicados; se `git worktree`
  compartilhando objetos já resolve o disco (sim: 456 GB livres) e NÃO resolve a RAM.

## 3. Topologia candidata (para o debate — não é decisão)

```
Owner ─┬─ Terminal A (conta 1): CEO principal — PLAN-186 (construção em sombras + lands + cerimônias)
       ├─ Terminal B (conta 2): CEO-B — PLAN-183 + PLAN-169 em CLONE próprio; sem land no main;
       │                        entrega packs em ~/.claude/projects/<slug>/sNNN-packs/
       ├─ Terminal C (conta 3): CEO-C — medições que exigem conta dedicada (AC-2 concorrência,
       │                        sondas cross-session) + revisões externas (codex/grok)
       └─ Integrador (Terminal A): um lander por vez; SIGN/LAND só aqui
```

Regras que a topologia exige (todas já têm precedente na S344): packs em disco como contrato entre
terminais; `ListAgents`/`SendMessage` ANTES de tocar estado compartilhado (doutrina W5-US3);
partição de PATHS por plano; a árvore viva do main é de UM terminal só.

## 4. Instrumento — workflow `stress-parallelism`

Script em `<scratchpad>/stress-parallelism.js` (S344): degraus N com barreira, tarefa fixa,
guarda de saúde por Bash entre degraus (memória livre, load, 429 nos transcripts), saída JSON
por célula (`N, repetição, devolvidos, erros, p50, p95, max, mem_livre_antes/depois, load`).
Custo estimado: 8+16+24+32 = 80 agentes × 3 rep × ~95 k = ~23 M tokens de contexto (cache read
domina) — rodar em conta DEDICADA, nunca na conta do terminal principal.

## Acceptance criteria

- [ ] AC-1 Q1 medida: tabela N × {p50, p95, erros, mem, load} com 3 repetições e o teto NOMEADO
      com o critério que o definiu (memória, latência ou 429).
- [ ] AC-2 Q2/Q3 medidas: 2 workflows na mesma sessão e 2 terminais em 2 contas, com p95
      comparado ao caso de 1 workflow.
- [ ] AC-3 Q5 medida: teto de revisões codex simultâneas sem 429 (3/3 repetições) e o maior
      brief que o grok responde em < 5 min; recomendação de uso por tamanho de brief.
- [ ] AC-4 Q4/Q6: custo de RAM por agente e por worktree medido; proposta de topologia
      multi-terminal com partição de paths, levada a `/debate` (L3) antes de qualquer adoção.
- [ ] AC-5 Relatório `docs/research/parallelism-ceiling-S34x.md` com todo número acompanhado
      do comando; nenhuma claim de speedup do framework (AGENTS.md §0).

## Open questions

- OQ-1 (Owner): quantas contas Claude e quantas contas Codex podem ser dedicadas ao estudo?
- OQ-2 (Owner): a topologia multi-terminal vale um ADR próprio ou entra como wave do PLAN-186 W5-US3?

## Progress log

- 2026-09-04 (S344): plano criado como rascunho a pedido do Owner; fatos §1 medidos na própria
  S344; instrumento §4 escrito no scratchpad da sessão e lançado uma vez em degrau reduzido
  (ver nota abaixo quando existir).
- 2026-09-04 (S344, ~15:30): stress `[8,16]×1` executado sob carga (fato §1 #10): N=8 limpo, N=16 com 10/16 recusados pelo SERVIDOR («not your usage limit»). Q1 ganha a hipótese H1: o teto observado é por servidor+carga, não por conta; falsificador = repetir com a máquina ociosa e ver N=16 limpo.
- 2026-09-04 (S344, ~15:50): o Owner mostrou uma 2.ª sessão Claude (mesma conta, mesma máquina, repo `arbitrage-monitor`, 8 workflows, ≥8 agentes) ativa durante o stress — medição #10 marcada CONTAMINADA; Q0 (inventário de concorrência externa) adicionada como pré-condição de toda célula.
