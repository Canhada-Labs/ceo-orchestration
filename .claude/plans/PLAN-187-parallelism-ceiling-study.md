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
| 11 | Processos `codex` vivos (amostras de 5 min). A coluna conta PROCESSOS do SO; **ela não mede «revisões»** — o amostrador não vê rodadas | p50 **7**, max **9** (o max cai em `2026-09-05T02:06:48`) | `python3 -c "import csv,statistics as s;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));v=[int(x['codex_procs']) for x in r];m=max(r,key=lambda x:int(x['codex_procs']));print(s.median(v),max(v),m['ts'])"` → `7.0 9 2026-09-05T02:06:48` |
| 12 | Sequência de amostras CONSECUTIVAS com zero processo `codex` (o comando verifica que os índices são consecutivos). Isso **não prova janela contínua**: um processo que nasça e morra ENTRE duas amostras é invisível ao amostrador | **30 amostras consecutivas**, de `2026-09-04T22:56:40` a `2026-09-05T01:21:46` | `python3 -c "import csv;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));i=[n for n,x in enumerate(r) if x['codex_procs']=='0'];print(len(i),r[i[0]]['ts'],r[i[-1]]['ts'],i[-1]-i[0]+1==len(i),r[i[-1]+1]['ts'],r[i[-1]+1]['codex_procs'])"` → `30 2026-09-04T22:56:40 2026-09-05T01:21:46 True 2026-09-05T01:26:46 1` |
| 13 | `load1` da máquina (a contagem de 16 núcleos vem do fato #1, NÃO deste CSV) | p50 **6,495**, max **32,96** em `2026-09-04T22:36:39` | `python3 -c "import csv,statistics as s;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));v=[float(x['load1']) for x in r];m=max(r,key=lambda x:float(x['load1']));print(s.median(v),max(v),m['ts'])"` → `6.495 32.96 2026-09-04T22:36:39` |
| 14 | Worktrees REGISTRADOS (`git worktree list`) — registrado não é «em uso»: o comando não observa atividade | min **10**, max **45** | `python3 -c "import csv;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));v=[int(x['worktrees']) for x in r];print(min(v),max(v))"` → `10 45` |
| 15 | Processos `pytest` simultâneos (a coluna conta processos casando `[p]ytest`; workers do xdist contam como processos) | max **26** em `2026-09-04T22:36:39`, amostra cujo `load1` é **32,96** — o mesmo instante do fato #13 (coincidência REGISTRADA, ver a nota) | `python3 -c "import csv;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));m=max(r,key=lambda x:int(x['pytest_procs']));print(m['pytest_procs'],m['ts'],m['load1'])"` → `26 2026-09-04T22:36:39 32.96` |
| 16 | Memória livre (`Pages free` do `vm_stat`) — é a memória LIVRE, não a memória consumida por nenhuma lane | min **27 MB** em `2026-09-05T03:11:50` (com 40 worktrees registrados); **51 de 102** amostras abaixo de 1 GB | `python3 -c "import csv;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));m=min(r,key=lambda x:int(x['mem_free_mb']));print(m['mem_free_mb'],m['ts'],m['worktrees'],sum(1 for x in r if int(x['mem_free_mb'])<1024),len(r))"` → `27 2026-09-05T03:11:50 40 51 102` |
| 17 | RSS somado dos processos que casam o binário `claude` | p50 **958,5 MB**, max **1050 MB**, min **709 MB** | `python3 -c "import csv,statistics as s;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));v=[int(x['claude_rss_mb']) for x in r];print(s.median(v),max(v),min(v))"` → `958.5 1050 709` |
| 18 | `claude_procs` vale **1** nas 102 amostras. O que isso PROVA: **em cada amostra** havia exatamente um processo casando o binário — logo o RSS do fato #17 é de UM processo por amostra. O que isso NÃO prova: que seja SEMPRE o mesmo processo (o PID não foi registrado), nem que todos os subagentes vivam dentro dele (o amostrador não inspeciona a árvore de processos) | valor único **1** em 102 amostras | `python3 -c "import csv;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));print(sorted({x['claude_procs'] for x in r}),len(r))"` → `['1'] 102` |
| 19 | RSS somado dos processos `codex` | max **1792 MB** em `2026-09-05T02:46:49`, amostra com 9 processos | `python3 -c "import csv;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));m=max(r,key=lambda x:int(x['codex_rss_mb']));print(m['codex_rss_mb'],m['ts'],m['codex_procs'])"` → `1792 2026-09-05T02:46:49 9` |
| 20 | Inclinação da janela Claude de 5 h entre a 1.ª amostra observada em 0 % e a 1.ª observada em 100 % — o comando imprime também as duas amostras VIZINHAS anteriores | **+22,63 pontos percentuais por hora** em **4,42 h**, de `2026-09-05T00:01:43` (0 %; a amostra anterior, `23:56:42`, marcava 91 %) a `2026-09-05T04:26:53` (100 %; a anterior, `04:21:53`, marcava 99 %). **INFERÊNCIA rotulada:** um reset da janela caiu entre `23:56:42` e `00:01:43` — o amostrador não observa resets, só a queda de 91 % para 0 % | `python3 -c "import csv,datetime as d;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));q=[(x['ts'],float(x['five_hour_pct'])) for x in r if x['five_hour_pct'] not in ('NA','')];i0=next(n for n,x in enumerate(q) if x[1]==0.0);i1=next(n for n,x in enumerate(q) if x[1]==100.0);h=(d.datetime.fromisoformat(q[i1][0])-d.datetime.fromisoformat(q[i0][0])).total_seconds()/3600;print(q[i0-1],q[i0],q[i1-1],q[i1],round(h,2),round((q[i1][1]-q[i0][1])/h,2))"` → `('2026-09-04T23:56:42', 91.0) ('2026-09-05T00:01:43', 0.0) ('2026-09-05T04:21:53', 99.0) ('2026-09-05T04:26:53', 100.0) 4.42 22.63` |
| 21 | Cobertura e cadência REAL da amostragem (o comando conta os intervalos) | **102 amostras** de `2026-09-04T20:36:35` a `2026-09-05T05:01:54`; intervalos: **82× exatamente 300 s e 19× 301 s** (o `sleep 300` mais o custo da própria amostra) | `python3 -c "import csv,datetime as d,collections;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));t=[d.datetime.fromisoformat(x['ts']) for x in r];print(len(r),r[0]['ts'],r[-1]['ts'],dict(collections.Counter(int((t[i+1]-t[i]).total_seconds()) for i in range(len(t)-1))))"` → `102 2026-09-04T20:36:35 2026-09-05T05:01:54 {300: 82, 301: 19}` |
| 22 | **Declarado pelo ledger do CEO, NÃO amostrado e NÃO verificável dentro deste pack:** a conta codex bateu o limite de uso às 22:55 (texto do erro citado no ledger: «You have hit your usage limit … try again at Sep 7th»); restaurada às 01:23 por reset semanal | 22:55 → 01:23 | ledger da noite S345. O CSV é COMPATÍVEL com a declaração (fato #12, cujo comando imprime a corrida de zeros e a amostra seguinte: o primeiro `1` volta em `2026-09-05T01:26:46`) mas não a demonstra: compatibilidade não é evidência da CAUSA |
| 23 | **Declarado pelo ledger do CEO, NÃO amostrado:** a janela Claude de 5 h chegou a 100 % por volta das 04:25 com **8–9 lanes vivas** (lane = um construtor ou um refutador); resets às 00:00 e às 05:00 | 8–9 lanes | ledger da noite S345. O CSV não tem coluna de lanes (fato #18) e a amostra de `05:01:54` traz `NA` — ele NÃO observa o reset das 05:00 |
| 24 | **Declarado pelo ledger do CEO, NÃO amostrado:** o portão de concorrência do codex segurou **8 slots** e a fila chegou a **19 wrappers** às 22:31 | 8 slots / fila 19 | ledger da noite S345. O CSV não tem coluna de slots nem de fila; a amostra de `22:31:39` traz 8 processos codex (`python3 -c "import csv;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));x=[y for y in r if y['ts']=='2026-09-04T22:31:39'][0];print(x['ts'],x['codex_procs'])"` → `2026-09-04T22:31:39 8`) — compatível, não probatório. **INFERÊNCIA rotulada:** o max de 9 processos (fato #11) cai em `2026-09-05T02:06:48`, OUTRO instante, então ele não refuta nem confirma o portão de 8 slots das 22:31 |
| 25 | **Declarado pelo ledger do CEO, NÃO amostrado:** o portão de baterias foi alargado de **2 para 5 slots** às 22:10, depois de 15 esperando com load 4,3 em 16 núcleos | 2 → 5 slots | ledger da noite S345. O CSV não tem coluna de slots nem de espera, e o `4,3` NÃO aparece nele: a amostra vizinha traz `load1` **5,68** (`python3 -c "import csv;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));x=[y for y in r if y['ts']=='2026-09-04T22:11:39'][0];print(x['ts'],x['load1'])"` → `2026-09-04T22:11:39 5.68`) — a leitura do ledger caiu entre amostras |
| 26 | **Declarado pelo ledger do CEO, NÃO amostrado:** o portão do grok rodou 2 e depois 3 slots; grok lançado com cwd DENTRO do repo herda o hook `Stop` do próprio repo e cola um rabo fora de assunto em cada veredito | 2 → 3 slots | ledger da noite S345. O CSV não observa grok, cwd, hooks nem vereditos — zero evidência in-pack |

> **Instrumento das linhas 11–21 (noite S345, 2026-09-04→05):** amostrador passivo
> (`night-sampler.sh`, `sleep 300` entre amostras) rodando ao LADO das lanes reais — não houve
> stress sintético. O CSV viaja RASTREADO em `.claude/plans/PLAN-187/s345-night-sampler.csv` e é um
> SNAPSHOT CONGELADO de 102 amostras; todo número das linhas 11–21 é reproduzível pelo comando da
> própria célula executado sobre ESSE arquivo. As colunas vêm de `ps -eo rss,command`
> (claude/codex), `grep -c '[p]ytest'`, `sysctl -n vm.loadavg`, `git worktree list`, `vm_stat`
> (`Pages free`) e do snapshot de statusline (quota).
>
> **O amostrador NÃO atribui causa e não observa lanes.** Ele não sabe qual lane gerou qual carga;
> o pico de `load1` e o pico de `pytest_procs` caírem na MESMA amostra (fatos #13 e #15) é
> COINCIDÊNCIA REGISTRADA, não causalidade medida. Falsificador: para atribuir seria preciso
> amostrar por PID a árvore de processos de cada lane — não feito. As linhas 22–26 são declarações
> do ledger do CEO: onde o CSV é COMPATÍVEL com elas, isso está dito na célula, e compatibilidade
> não é prova da causa alegada.
>
> **AC-4 (RAM por agente e por worktree) fica PARCIALMENTE informado — e mais fraco do que parece.**
> (i) Por AGENTE: **não observável** aqui. O fato #18 mostra UM único processo casando o binário
> em todas as 102 amostras, então o RSS do fato #17 é de um processo, não de um agente; qualquer
> «RSS por agente» obtido dividindo #17 por N é inválido — falsificador: mude N e o resultado muda
> sem que o RSS mude. (ii) Por WORKTREE: **também não derivável deste CSV**. #14 dá a contagem e
> #16 a memória livre, mas sem baseline, sem controle das outras cargas e sem atribuição por
> processo não há CUSTO por unidade. Existe, sim, correlação DESCRITIVA calculável neste CSV —
> Pearson bruto entre `worktrees` e `mem_free_mb` ≈ **−0,75**
> (`python3 -c "import csv,statistics as s;r=list(csv.DictReader(open('.claude/plans/PLAN-187/s345-night-sampler.csv')));w=[int(x['worktrees']) for x in r];m=[int(x['mem_free_mb']) for x in r];mw=s.mean(w);mm=s.mean(m);print(round(sum((a-mw)*(b-mm) for a,b in zip(w,m))/((sum((a-mw)**2 for a in w)*sum((b-mm)**2 for b in m))**0.5),4))"` → `-0.7502`)
> — mas ela é confundida pelo tempo (as duas séries têm tendência ao longo da noite) e não isola
> worktree de agente, pytest ou codex: o mínimo de memória livre (27 MB) ocorreu com **40**
> worktrees, e o máximo de **45** worktrees veio depois, com mais memória livre. O que estes
> fatos dão a AC-4 são LIMITES da noite (quantos worktrees coexistiram; quão baixa a memória livre
> chegou) e uma correlação sem atribuição, não um custo por unidade.


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
- 2026-09-05 (S345, noite autônoma, land livre): `p187-night-facts` landado — a §1 ganha os fatos 11–26 medidos na PRÓPRIA noite, cada número acompanhado do comando que o reproduz, e o CSV do amostrador (102 amostras, `2026-09-04T20:36:35` → `2026-09-05T05:01:54`) passa a viajar RASTREADO em `.claude/plans/PLAN-187/s345-night-sampler.csv`. AC-4 fica PARCIALMENTE informado e a nota diz por quê: RSS por agente NÃO é observável (um único processo casa o binário nas 102 amostras) e custo por worktree NÃO é derivável (correlação de Pearson −0,7502, confundida pelo tempo e sem atribuição). Rail de land r1 APPROVE nas duas lanes (mecanismo sem defeito acionável; texto com 4 residuais declarados, 3 deles contra a redação do brief e não contra os bytes); bateria: 14/14 linhas re-derivadas da árvore viva, 9 pernas de recusa reproduzidas (idempotência rc=3 com sha do plano inalterado; escape por symlink rc=3 com 0 arquivos fora da árvore), `validate-governance.sh` COMPLETO Errors 0, staleness/claims/env-hygiene/contaminação rc 0, oráculo 0 nos 3 paths.
