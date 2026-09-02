# Mapa serial vs paralelo do orquestrador — S339

> Nota (AGENTS.md §0): os tempos e percentuais abaixo são wall-clock de gates e CI DESTE repo, medidos em runs nomeados ou estimados como alvo a confirmar. Não constituem claim de velocidade do framework.

**Data:** 2026-09-02
**Autor:** Performance Engineer (rung 2, W2.3)
**Escopo:** `ceo-orchestration` (cwd) — LAND V-blocks (PLAN-169/PLAN-179), CI
(Smoke Install / Validate), pair-rail Codex, night-run S338 (7 agentes),
confronto com PLAN-172 (E0b/E5/E6).

## Metodologia

- **LAND scripts:** leitura integral dos passos G0–G5/V1–V9 de
  `.claude/plans/PLAN-169/OWNER-S338-FABLE51-LAND.sh` e
  `.claude/plans/PLAN-179/OWNER-S338-179FU-LAND.sh`. Os tempos por V-passo
  **não são medidos** pelo script (não há `time` nem log de duração) — uso
  os números DECLARADOS nos comentários do próprio script/tarefa
  (verify-counts ~3 min, governança completa ~30 s, parity smoke ~35 s) e
  classifico dependência por LEITURA do código, não por medição.
- **CI:** `gh run list` + `gh run view --json jobs` sobre os SHAs pedidos
  (`8efe09b`, `ab56e76`) e, quando um desses runs estava incompleto/cancelado,
  sobre o run verde mais recente do MESMO workflow (`f0e98de3`) — nomeado
  explicitamente onde usado.
- **Pair-rail:** leitura de `rail-round-*.md` e `rail-materials-round-*.md`
  nas duas cerimônias. **Achado metodológico relevante:** o `git log
  --follow` mostra os 9 arquivos de rail das duas cerimônias com o MESMO
  timestamp de primeiro commit cada um (todos os registros de uma cerimônia
  entram juntos no commit final da wave) — não há como recuperar a duração
  REAL rodada-a-rodada pelo git. Uso então o timeline do night-run (item d)
  como proxy de tempo, e o TEXTO dos registros para achados/rodadas.
- **Night-run:** `journal.jsonl` do workflow (`wf_e3144372-b04`) não carrega
  timestamps por evento; uso o `mtime` de `agent-<id>.meta.json` (criação ≈
  início) e de `agent-<id>.jsonl` (última escrita ≈ fim) dos 7 agentes como
  proxy de linha do tempo real.
- Doutrina de estimativa (CLAUDE.md §ESTIMATION): esforço de IMPLEMENTAR cada
  oportunidade é dado em tokens+sessões; durações de gates/CI são
  wall-clock de máquina (medido ou declarado), não esforço humano — não são
  a mesma grandeza e a tabela final não as confunde.

---

## (a) LAND V-block — dependências e paralelizável?

Ambos os scripts (`OWNER-S338-FABLE51-LAND.sh`, `OWNER-S338-179FU-LAND.sh`)
são bash linear, sem `&`/`wait` em lugar nenhum. Ordem observada:
G-PRE → G0 → G1 → G2 → G3 → G4 → G5 → *aplica o patch* → V1 → V3 → V4 → V6
→ *(corte do `--dry-run` aqui)* → V2 → V7 (só fable51) → V8 → V9 → stage → commit → push.

**O que cada V faz e sobre o que ele opera** (fable51:629-876; 179fu:619-876):

| V | O que faz | Custo declarado | Escreve em estado compartilhado? |
|---|---|---|---|
| V1 | `py_compile` + `bash -n`+shellcheck nos arquivos tocados | segundos | não — só lê `$TOUCHED_FILE`, escreve em `$TMPDIR_LAND` próprio |
| V3 | `git worktree add --detach` em HEAD + roda o derivador + `cmp` byte a byte | segundos–baixa dezena | cria um worktree PRÓPRIO (`$WT_REPRO`, índice separado) — não conflita com o índice principal, mas COMPARTILHA o `.git/objects` do mesmo repo (leitura concorrente é segura; a criação do próprio worktree grava uma entrada em `.git/worktrees/`) |
| V4 | `jq` sobre settings/base, `generate-available-models.py --check`, `shasum -c` do manifesto, `check_harness_config.py` (fable51) **ou** `check-hook-stdout-schema.py` que **EXECUTA os 4 hooks wired com fixtures** + `check-active-hooks-executable.py` + `check-test-env-hygiene.py` (179fu) | segundos | fable51: read-only. **179fu é diferente**: o comentário do próprio script chama isso de "o mais próximo de um live-fire que o repo tem" — hooks de verdade rodam, com fixtures. Risco de escrita na cadeia HMAC viva se a fixture não isolar (ver abaixo) |
| V6 | grep/jq sobre os paths tocados + `bash upgrade.sh --print-settings-baselines` (subprocess) + (179fu) roda pytest no ARQUIVO tocado | segundos | V6 do 179fu chama `python3 -m pytest -q -p no:cacheprovider "$TOUCHED_TEST"` — outro processo pytest |
| V2 | `pytest` sobre uma lista DECLARADA de 15 (fable51) / N (179fu) arquivos | não medido no script; a tarefa cita "verify-counts ~3 min" para V8, não para V2 — provavelmente segundos a ~1 min dado o tamanho da lista | **pytest real**, mesma classe de risco do V4/179fu |
| V7 | `bash scripts/local/smoke-install-parity.sh` (install real em tmp) — só fable51 | ~35 s (declarado no cabeçalho) | instala em `mktemp -d`, isolado |
| V8 | contagem de ADRs + `check-claude-md-claims.py` + `verify-counts.sh` | verify-counts ~3 min (declarado) | **`verify-counts.sh` invoca `python3 -m pytest --collect-only`** — a classe EXATA que a S326 mediu escrevendo 124 elos/execução na cadeia HMAC viva antes da cura estrutural (Axis 3, `9de4efc`/`965fb13`, ver `MEMORY.md` → `project-s326-collect-only-writes-live-chain.md`). A cura landou, mas é o ÚNICO ponto do V-block com esse histórico nomeado |
| V9 | `check-ceremony-script.py --json`, `validate-governance.sh` completo (SEM `--fast` — checa o limite de 40k bytes do CLAUDE.md), `gen-command-skill-hook-map.py --check` | governança completa ~30 s (declarado) | `validate-governance.sh` roda MUITOS sub-checks; não confirmei isoladamente se algum grava eventos de audit fora do isolamento de teste |

**Dependência real entre eles:** V1/V3/V4/V6 só precisam do patch já aplicado
(que acontece ANTES de V1) e leem a árvore/patch — **não dependem uns dos
outros**. V2/V7/V8/V9 também não leem saída um do outro (cada um escreve seu
próprio log em `$TMPDIR_LAND`). Em teoria, `V1 & V3 & V4 & V6; wait` e depois
`V2 & V7 & V8 & V9; wait` são executáveis sem quebrar a lógica dos `die`.

**Por que NÃO recomendo fazer isso** (risco > ganho, ver tabela final):

1. **O ganho é pequeno.** V1/V3/V4/V6 somados são segundos; o item caro é
   V8 (verify-counts ~3 min) e ele domina o V-bloco caro sozinho. Rodar
   V2/V7/V8/V9 em paralelo no melhor caso corta o V-bloco caro de
   (V2+V7+V8+V9) para `max(V2,V7,V8,V9)` ≈ V8 (~3 min) — uma economia de
   dezenas de segundos a ~1–2 min sobre um LAND que já leva minutos por
   outros motivos (G-bloco, aplicação do patch, staging).
2. **Risco de corrida na cadeia HMAC viva é REAL e nomeado no histórico
   deste repo** (S326: dois processos escrevendo `policy_*`/audit
   concorrentemente geraram 19.344 elos não-atribuíveis antes da cura). V2,
   V4 (179fu) e V8 todos podem tocar pytest/hooks live-fire; rodá-los em
   paralelo reabre exatamente a classe de flake que
   `feedback-live-audit-isolation-flakes-under-concurrent-session.md`
   descreve, mesmo que a cura estrutural (Axis 3) deva cobrir a maior parte.
3. **O trap/restore (`_restore()`, `RESTORE_ON_EXIT`, `STAGED_BY_LAND`) foi
   endurecido por 5+ rodadas de rail exatamente sobre a ORDEM sequencial**
   (lição P2-h: "exit status na ENTRADA do trap"). Introduzir paralelismo
   exigiria reabrir esse desenho — que é canônico, guardado por sentinel, e
   caro de re-certificar (nova rodada de rail completa).
4. **Semântica de erro muda:** hoje um `die` para tudo com UMA mensagem
   clara; com `&`+`wait`, um erro em um dos ramos paralelos exige agregação
   de rc's e não interrompe os irmãos no meio — mais código de
   coordenação para um ganho de segundos.

**Veredito (a):** V-bloco do LAND é uma paralelização de **baixo ganho /
risco desproporcional**. NÃO recomendado.

## (b) CI — Smoke Install e Validate

### Runs usados

| Run | SHA | Workflow | Status | Duração |
|---|---|---|---|---|
| 33582381725 | `f0e98de3` (S337, o run verde mais recente completo — `ab56e76`/`8efe09b` estavam `cancelled`/`in_progress` no momento da coleta) | Smoke Install | success | **87m50s** (02:12:57→03:40:47) |
| 33627209709 | `ab56e76` | Validate CEO Orchestration governance | success | **~23m27s** (11:56:23→12:19:50, ponta a ponta dos 6 jobs) |
| 33627209790 | `ab56e76` | Smoke Install | **cancelled** | n/a |
| 33630753302/33630753334 | `8efe09b` | Smoke Install / Validate | `in_progress` no momento da coleta | n/a |

### Smoke Install: 1 job, ~26 steps, TUDO serial

`.github/workflows/smoke-install.yml:192-296` documenta o próprio orçamento
do `timeout-minutes: 126` como soma de MEDIÇÕES incrementais por feature
landada — nunca houve uma decisão de arquitetura, só acréscimo de steps a
UM job. Decomposição real do run 33582381725 (soma dos deltas de
`startedAt`→`completedAt` por step, linha 482-703 do workflow):

| Step | Duração |
|---|---|
| Upgrade historical-adopter delivery (D1+OQ-5) | **32m43s** |
| Upgrade hook-roster derivation (W-E) | **17m37s** |
| Upgrade oracle — exclusion parity (U2/U3) | 7m39s |
| Installer write-confinement e2e (F1/F2) | 6m37s |
| Delivery-route oracle (doctor, D4) | 5m40s |
| Upgrade SPEC/marker ownership (S1-S8) | 4m39s |
| night-mode ignore efficacy | 3m54s |
| Install/upgrade parity e2e | 2m45s |
| Install/upgrade parity — positive control | 2m43s |
| Run smoke install | 1m48s |
| (demais 16 steps) | ≤ 1m cada, soma ~1m30s |
| **Total (soma dos steps = wall clock do job)** | **≈87m50s** |

Os DOIS maiores steps (historical-adopter + hook-roster) somam **50m20s —
57% do job inteiro**. Cada um é, pelo próprio comentário do workflow
(linhas 218-278), um e2e AUTOCONTIDO: monta fixtures próprias com `mktemp`,
roda instalações/upgrades reais em diretórios isolados, não lê saída de
nenhum step anterior (exceto o "Deepen git history", que só precisa ter
rodado ANTES — não durante).

**Isso É matrizável por step.** Praticamente todo step deste job é
independente dos outros no sentido de dado (cada `.sh` cria seu próprio
`mktemp -d`/`git init`); as únicas ordens reais são:
(1) "Gate-scripts integrity" antes de tudo (barato, segundos);
(2) "Fetch the parity pin tag" + "Deepen git history" antes de qualquer
step que precise de tags/histórico completo (parity e2e, historical-adopter
e2e, schema-pins guard) — os comentários do workflow (linhas 429-471) são
explícitos sobre essa dependência.
Fora isso, nada impede rodar os ~15 e2e/oracle steps como jobs de uma
`strategy: matrix`, cada um com seu próprio checkout+deepen.

**Estimativa paralela:** bound pelo maior step isolado — historical-adopter
delivery, 32m43s — mais overhead de checkout (`fetch-depth:1` + deepen,
~3-10s cada) e setup Python/jq por job (~10-15s). Com uma matrix de ~15
jobs, o wall-clock do workflow cairia de **~88 min para ~35-40 min**
(bound pelo step mais lento + margem), um corte de **~55%**. O CUSTO sobe:
runner-minutos TOTAIS aumentam (cada job repete checkout/deepen/setup —
overhead pequeno × N jobs) e o repo passaria a consumir ~15 slots
concorrentes de runner por push em vez de 1 (o Validate já faz isso hoje
com 6 jobs, então não é um padrão novo para este repo).

**Risco:** médio. O padrão `if: always()` em 8 dos steps existe
precisamente para que um step tardio não vire `skipped` quando um anterior
falha (lição §9.8/PLAN-183, "instrumento verde cuja pergunta envelheceu") —
matrizar por job RESOLVE esse problema de forma mais limpa (cada job já é
independente por natureza), mas exige reescrever o workflow inteiro e
re-provar CADA step isoladamente (positive controls incluídos) antes de
confiar no novo formato. Nenhum teste de "job matrix correto" existe hoje.

### Validate: já matrizado no topo, mas o job "validate" é o novo monolito

`.github/workflows/validate.yml` já roda **6 jobs em paralelo** sem
`needs:` entre eles (linhas 29, 1229, 1279, 1336, 1571, 1606, 1674) — isso
é o motivo do workflow terminar em ~23 min quando o job mais longo
individualmente (o job `validate`, 1200 linhas de steps sequenciais) leva
~22m22s (11:57:28→12:19:50, medido no run `ab56e76`/33627209709). Ou seja:
**Validate já pratica o padrão que falta no Smoke Install** — o gargalo
agora é o MESMO padrão em escala menor, dentro do job `validate`.

Dentro desse job, os 3 maiores blocos:

| Step (dentro do job `validate`) | Duração |
|---|---|
| Run Python script unit tests | 8m05s |
| Run Python hook unit tests | 5m57s |
| Installer --harness codex+grok matrix | 5m29s |
| (demais ~40 steps) | soma ~2m50s |

Esses 3 blocos somam **19m31s dos 22m22s do job** (87%). Separá-los em 3
jobs paralelos ao lado de `hook-tests-python-matrix`/`hook-tests-dual-rail`
(que já existem como jobs próprios, mostrando que o padrão é conhecido
neste repo) reduziria o critical path do Validate de **~23 min para
~13 min** (bound pelo próximo maior job, `hook-tests-python-matrix (3.12)`,
10m39s medido). Corte de **~43%**.

**Risco:** baixo-médio. Mesma classe de trabalho que já existe 2x no
arquivo (não é padrão novo); precisa confirmar que os 3 blocos não
dependem de artefato deixado por um step anterior do MESMO job (não
verifiquei `GITHUB_ENV`/artifact upload entre eles — ficaria como
verificação de pré-condição antes de implementar).

## (c) Pair-rail Codex — patch vs materiais, e rodadas

**Rodadas por cerimônia:**
- fable51: 5 rodadas de rail sobre o PATCH (`rail-round-1..5.md`), achando
  7 defeitos reais (3 P1 + 4 P2) nas 4 primeiras, r5 = APPROVE limpa.
- 179fu: 3 rodadas sobre o PATCH (`rail-round-1..3.md`, achados registrados
  fora deste escopo de leitura) **+ 1 rodada SEPARADA sobre os MATERIAIS**
  (SIGN/LAND/finalize/harness — `rail-materials-round-1.md`), que achou 1
  P1 real: `OWNER-S338-179FU-LAND.sh:838` referenciava `$VALIDATE_SH` sem
  jamais defini-la (bug de clonagem do molde fable51 — sob `set -u` o LAND
  completo abortaria no V9b, DEPOIS dos ~7,5 min do V2, e o `--dry-run` não
  alcança esse ponto, então T2-T12 do harness passaram e só o T15b
  acusaria).

**Duração por rodada:** não recuperável do git (todos os arquivos de rail
de uma cerimônia entram no MESMO commit final, mesmo `git log --follow`
timestamp). Não há log de duração dentro dos próprios `.md`.

**Patch-track e materiais-track já rodam sobre ÁRVORES FISICAMENTE
DIFERENTES**, o que é o fato que importa para paralelismo: o rail do PATCH
roda numa **sombra re-derivada** (clone separado, `sandbox_mode:
"workspace-write"`, base `dc72bf1`); o rail dos MATERIAIS roda **na árvore
VIVA** com os materiais marcados `git add -N` (intent-to-add) para aparecer
no diff, `sandbox_mode: "read-only"`. Como são processos `codex exec`
distintos sobre diretórios distintos, **já são paralelizáveis hoje sem
mudança nenhuma** — bastaria disparar as duas chamadas Codex ao mesmo tempo
em vez de sequencialmente. O ganho é limitado porque o materials-track é
curto (1 rodada, achado único) — o ganho real seria só a LATÊNCIA de
esperar uma rodada terminar antes de começar a outra, não o trabalho em si.

**O que NÃO é paralelizável:** rodadas DENTRO da mesma track. A doutrina do
repo é explícita (`feedback-clean-rail-round-not-proof.md`,
`feedback-fix-of-fix-means-change-the-cure-architecture.md`,
`feedback-rail-clone-must-follow-commit.md`): cada rodada revisa a sombra
RE-DERIVADA depois da cura da rodada anterior — rodar rodada N e N+1 em
paralelo significaria revisar a MESMA falha duas vezes ou revisar código
que ainda não incorporou a cura. É sequencial por construção do protocolo,
não por limitação de ferramenta.

**Veredito (c):** ganho pequeno e já parcialmente praticado
(cross-track); intra-track é estruturalmente serial — não é uma
oportunidade de otimização, é uma invariante do protocolo de cura-depois-
revisão.

## (d) Night-run S338 (`wf_e3144372-b04`) — timeline real dos 7 agentes

Timeline reconstruída por `mtime` de `agent-<id>.meta.json` (início) e
`agent-<id>.jsonl` (fim), cruzado com `journal.jsonl` (ordem de
started/result) e os `pack_dir`/`rail_rounds` de cada resultado:

| Agente | Papel | Início | Fim | Duração | Pack / nota |
|---|---|---|---|---|---|
| `a27d43c4…` | builder (fix direto) | 22:31:36 | 22:56:32 | 24m56s | schema `defect_confirmed`/`e2e_pass` — não é pacote de cerimônia, sem refutador dedicado |
| `a506a7af…` | builder | 22:31:36 | 23:19:18 | 47m42s | `PLAN-169/s338-fu-sonnet5-pricing`, 3 rodadas rail, APPROVE |
| `ab057190…` | builder | 22:31:40 | 23:31:01 | 59m21s | `PLAN-179/s338-followup-flip`, 2 rodadas, CHANGES-REQUESTED (P1 de processo, não funcional) |
| `aeee4ec1…` | builder | 22:31:40 | **00:37:36** | **2h05m56s** | `PLAN-183/s338-w1-draft`, 3 rodadas, CHANGES-REQUESTED, **status=partial**, sem rodada limpa — este É o draft que o CLAUDE.md registra como "refutado como landável" |
| `a4df5635…` | refutador de `a506a7af` | 23:19:37 | 23:44:53 | 25m16s | |
| `aaaed057…` | refutador de `ab057190` | 23:31:26 | 23:45:45 | 14m19s | |
| `aaec11aa…` | refutador de `aeee4ec1` | 00:37:56 | 01:00:38 | 22m42s | |

**Total do workflow:** 22:31:36 → 01:00:38 = **2h29m02s** (bate com o "2h29m"
citado na tarefa).

**Achados:**

1. **4 builders sobem em paralelo** (2 pares de 4s de diferença no início
   — essencialmente simultâneo). Isso já é o máximo de paralelismo de
   builder que este pacote de trabalho tinha.
2. **Pipelining builder→refutador com WIP≈2 já está em produção**: o
   refutador de `a506a7af` (`a4df5635`) inicia às 23:19:37 e o refutador de
   `ab057190` (`aaaed057`) inicia às 23:31:26 — **os dois rodam
   concorrentemente** por ~14 min (23:31→23:45), exatamente o padrão "WIP=2"
   que o PLAN-172 E5 propõe medir formalmente. **[JÁ NO PLAN-172]** como
   conceito — mas rodando de forma NÃO instrumentada/NÃO comparada contra
   controle serial (o pré-registro E5 exige braço A serial token-matched;
   isso aqui é produção, não experimento).
3. **O critical path do workflow inteiro é UM agente**: `aeee4ec1…`
   (PLAN-183 W1 draft) sozinho consome 2h05m56s de 2h29m02s totais —
   **84% do wall-clock**. Os outros 3 builders + seus refutadores (no pior
   caso, `ab057190`+`aaaed057` ≈ 74 min) terminam com folga enorme antes
   disso. Nenhuma reorganização de agendamento entre os 4 builders muda o
   tempo total: o gargalo é o CONTEÚDO de um único pacote, não a
   orquestração.
4. **Ironia mensurável:** o item que dominou 84% do wall-clock foi
   justamente o que **não fechou** — 3 rodadas sem "rodada limpa"
   (`status=partial`, sem convergência), acabou virando insumo do
   `/debate` em vez de pacote assinável. O tempo do workflow foi gasto
   proporcionalmente ao inverso do valor entregue.
5. **Um dos 4 builders não teve refutador dedicado** (`a27d43c4…`, o mais
   rápido) — por ser uma tarefa de fix direto com verificação própria
   (`e2e_pass`/`positive_control` no schema do resultado), não um pacote de
   cerimônia. Não é uma lacuna, é uma ramificação correta do workflow.

**Oportunidade real aqui:** não é "mais paralelismo entre os 4 builders"
(já é o máximo dado 4 pacotes) — é **decompor pacotes historicamente
grandes/incertos** (como o draft W1, que nunca teve rodada limpa) em
sub-pacotes menores e independentes ANTES de disparar o workflow, cada um
como seu próprio slot builder→refutador. Isso é [NOVO] em relação ao
PLAN-172 (E5 agenda uma FILA fixa de tarefas com WIP=2; não propõe
decompor uma tarefa grande em tarefas menores). É também o tipo de
fan-out que a lição `feedback-parallel-fanout-needs-integration-pass.md`
avisa ser perigoso SE os sub-pacotes compartilharem símbolos/API — exigiria
um passe de integração explícito antes de qualquer assinatura, não fan-out
ingênuo.

## (e) Confronto com PLAN-172 (status: `reviewed`, não `done`)

- **E0b (gate de financiamento do E5) e E5 (pipelining WIP=2)**: não
  encontrei, na leitura do arquivo, um veredito registrado de E0b (quota de
  tempo-morto medida) nem um pré-registro assinado de E5 rodando como
  experimento formal (braço A serial token-matched vs braço B WIP=2). O
  único "Registro de execução" no arquivo (S316) é sobre um item DIFERENTE
  (W-IM#4, varredura de substrate-drift), não sobre E0b/E5. **O item (d)
  acima mostra E5 ACONTECENDO NA PRÁTICA (WIP≈2 observado no workflow real
  de produção) sem nunca ter sido formalmente medido/comparado** — um gap
  entre "o padrão já é usado" e "o padrão foi cientificamente validado
  como este plano propõe". Recomendação: usar o próprio `wf_e3144372-b04`
  como piloto observacional retroativo de E5 antes de gastar o orçamento
  de 2-4M tokens / 6-9 sessões que o plano reserva para o experimento
  completo — o dado já existe, só falta o braço de controle serial
  comparável.
- **E6 (cascata de filtros baratos-antes-de-caros no review)**: o padrão
  JÁ está implementado no desenho do LAND V-block — os gates baratos
  (G-PRE...G5, V1, V3, V4, V6) rodam ANTES dos caros (V2, V7, V8, V9), e o
  corte do `--dry-run` fica deliberadamente "depois dos gates baratos... e
  antes dos caros" (comentário explícito nos dois scripts). **[JÁ NO
  PLAN-172]**, e já executado — não é uma oportunidade nova, é confirmação
  de que o desenho atual já segue a doutrina do E6.
- **CLAUDE.md §1**: a ausência de "speedup geral" medido em 6 experimentos
  internos é sobre velocidade de DESENVOLVIMENTO (autoria), não sobre
  wall-clock de gates/CI — as oportunidades (b) e (c) desta análise são
  estritamente sobre tempo de máquina em CI/LAND, um eixo diferente e não
  contradito por essa nota.

---

## Tabela final (ordenada por ganho/risco)

| Oportunidade | Serial hoje | Paralelo (estimado) | Pré-condição | Risco | Esforço | PLAN-172? |
|---|---|---|---|---|---|---|
| **Matrizar `validate` (job monolítico do Validate) em 3 jobs — unit hooks / unit scripts / installer-harness-matrix** | ~22m22s (job único, 87% em 3 steps) | ~13 min (bound por `hook-tests-python-matrix 3.12`, 10m39s) — Validate cai de ~23 para ~13 min | confirmar ausência de estado partilhado (env/artifact) entre os 3 blocos | Baixo-médio | ~80-150k tokens / 1-2 sessões | NOVO |
| **Matrizar Smoke Install por step/e2e (`strategy: matrix`)** | ~88 min, 1 job, 26 steps sequenciais | ~35-40 min (bound pelo maior step isolado, historical-adopter 32m43s) — corte de ~55% | checkout+deepen replicado por job; steps já são autocontidos (mktemp/git init próprios); preservar a ordem "pin+deepen ANTES dos e2e que precisam de histórico" | Médio (reescrita completa do workflow; runner-minutos totais sobem; nenhum teste de "matrix correta" existe hoje) | ~150-300k tokens / 2-3 sessões | NOVO |
| **Rodar rail patch-track \|\| materials-track em paralelo (2 chamadas Codex concorrentes)** | Sequencial hoje (uma depois da outra) | Latência de espera eliminada; trabalho em si não muda | as duas já rodam em árvores fisicamente distintas (sombra vs viva+`git add -N`) — só falta disparar simultaneamente | Baixo | ~seg. de mudança de runbook | NOVO (mas já praticado informalmente) |
| **Usar `wf_e3144372-b04` como piloto observacional retroativo de E5 (WIP=2)** | n/a (medição, não execução) | n/a | braço de controle serial token-matched ainda não existe | Baixo | ~30-50k tokens / 1 sessão | JÁ NO PLAN-172 (E5), gap de instrumentação |
| **Decompor pacotes grandes/incertos do night-run (ex.: draft que nunca teve rodada limpa) em sub-pacotes menores antes do fan-out** | 1 builder consumindo 84% do wall-clock (2h06m de 2h29m) | Depende de quão divisível é o conteúdo — não estimável sem um caso concreto | pacote tem de ser logicamente divisível; PASSE DE INTEGRAÇÃO obrigatório se sub-pacotes compartilham símbolos (lição S313) | Médio-alto (classe "fan-out sem passe de integração degrada em silêncio") | Alto, arquitetural — não estimado sem plano próprio | NOVO |
| **Paralelizar V1/V3/V4/V6 e/ou V2/V7/V8/V9 dentro do LAND V-block** | ~3-5 min de V-bloco caro (dominado por verify-counts ~3 min) | ~poucas dezenas de segundos a ~1-2 min — ganho marginal | reabrir o trap/restore endurecido por 5+ rodadas de rail; resolver semântica de erro agregado | **Alto** (risco de corrida na cadeia HMAC viva — classe nomeada S326 — para ganho pequeno) | N/A — **não recomendado** | NOVO, mas descartado |
| **Paralelizar rodadas DENTRO de uma mesma track de rail** | Sequencial por protocolo (cura→re-revisão) | N/A | — | — | — | Estruturalmente impossível, não é uma oportunidade |

**Recomendação de prioridade:** as duas oportunidades de CI (Validate e
Smoke Install) são as únicas com ganho de wall-clock GRANDE e mensurável
(43% e 55% de corte respectivamente) sobre gates que rodam em TODO push —
o benefício composto ao longo de sessões é maior que qualquer coisa dentro
de uma única cerimônia. O LAND V-block deve ficar como está.

## Fontes

- `.claude/plans/PLAN-169/OWNER-S338-FABLE51-LAND.sh:136-876`
- `.claude/plans/PLAN-179/OWNER-S338-179FU-LAND.sh:127-876`
- `.github/workflows/smoke-install.yml:1-296` (budget/dependências), `:300-703` (steps)
- `.github/workflows/validate.yml:1-30,1229,1279,1336,1571,1606,1674` (estrutura de jobs)
- `gh run view 33582381725 --json jobs` (Smoke Install, SHA `f0e98de3`, success, 87m50s)
- `gh run view 33627209709 --json jobs` (Validate, SHA `ab56e76`, success, ~23m27s)
- `gh run list` (runs de `8efe09b` e `ab56e76`, incl. `33627209790` cancelled, `33630753302/33630753334` in_progress no momento da coleta)
- `.claude/plans/PLAN-179/s338-followup-flip/rail-materials-round-1.md:1-56`
- `.claude/plans/PLAN-169/s338-ceremony-fable51/rail-round-5.md:1-43`
- `/Users/<user>/.claude/projects/<project-slug>/f52979b1-4c83-4346-9217-5f07d8d51bde/subagents/workflows/wf_e3144372-b04/journal.jsonl` e `agent-*.{meta.json,jsonl}` (mtimes)
- `.claude/plans/PLAN-172-honest-speed-e0b-e5-e6.md:1-330`
- Memória: `feedback-parallel-fanout-needs-integration-pass.md`,
  `project-s326-collect-only-writes-live-chain.md`,
  `feedback-live-audit-isolation-flakes-under-concurrent-session.md`,
  `feedback-clean-rail-round-not-proof.md`,
  `feedback-fix-of-fix-means-change-the-cure-architecture.md`,
  `feedback-rail-clone-must-follow-commit.md`
