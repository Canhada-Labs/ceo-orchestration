---
id: PLAN-186-FOLLOWUP-hint-discovery-walk-from-root
title: "discover_hint_dirs limita a caminhada de hints e sinaliza truncagem"
status: draft
created: 2026-09-05
owner: CEO
depends_on: [PLAN-186]
parent: PLAN-186
# Por que L3, e por que em linha propria: §0.1.
level: L3
budget_tokens: 180-360k   # derivacao em §0.2
budget_sessions: 2
context_risk: high   # split-session (`PLAN-SCHEMA:329-330`); §0.3
external_wait: "QUATRO bloqueios, nao um: (i) assinatura GPG do Owner num sentinel cujo Scope enumera todos os paths tocados; (ii) DOIS dos quatro sao KERNEL e sentinel assinado NAO destrava kernel; (iii) §1.4 — este followup so entra em `executing` depois que o PLAN-186 chegar a `done`; (iv) a cascata de VERSAO, com o PISO de 24 h entre a ultima tag RC e a tag **GA**. Enumeracao completa, com os paths, os oraculos e as citacoes, em §0.4."
eta_calendar: "D+1 no MINIMO, contado a partir do fecho do PLAN-186. DERIVADO por `PLAN-SCHEMA.md:336-350` (`eta_calendar = max(external_waits)`): das QUATRO esperas, tres sao gatilhos do Owner sem duracao propria e a quarta tem duracao medida em contrato — as 24 h do hold RC->GA (`VERSIONING.md:78-88`). Logo o maximo e o hold de 24 h e a wave NAO corta a tag **GA** no mesmo dia em que landa. Derivacao completa em §0.5."
tags: [hooks, guardrail, hint-discovery, bateria, followup, canonico, kernel]
---

# PLAN-186-FOLLOWUP — a caminhada de hints ganha limite e a truncagem fica visivel

## 0. Notas de frontmatter (e o leitor que impoe o limite)

O frontmatter deste plano carrega VALORES; as derivacoes ficam aqui. Nao e
estilo: e um leitor mecanico. `.claude/hooks/turbo_sessionstart.py:71-78` le
um prefixo de **4096 caracteres** e exige a cerca de fechamento dentro dele
(`_FRONTMATTER_RE.match(fh.read(4096))`); se a cerca cair depois disso, o
plano fica INVISIVEL para `_active_plan_id()` assim que entrar em
`executing` — a sessao perde o titulo, ou pior, nomeia OUTRO plano executando
como se nao houvesse ambiguidade. Foi exatamente o que aconteceu aqui: as
curas R2-A, R2-B e F9 (cada uma certa sobre o SEU leitor) engordaram o
frontmatter ate **4746** caracteres. Regra desta wave, verificada por
controle: o frontmatter fecha ANTES de 4096 e toda justificativa mora neste
§0.

### 0.1 Por que L3, e por que a justificativa fica fora do valor

Rail r6, ambas as lanes, P1: AGENTS.md §4 manda tratar QUALQUER diff sob
`.claude/hooks/` como L3+ — logo valem os gates de L3 (debate antes de
executar + ADR se a decisao for cross-cutting), nao so o sentinel do AC-6. O
escopo sao QUATRO paths canonicos (§3), DOIS deles de KERNEL (rail r11). A
justificativa nunca vem depois do valor: o leitor mecanico e
`_extract_plan_level` (`.claude/scripts/ceo-escalation-detector.py:186-205`),
cujo regex `^\s*level\s*:\s*(.+?)\s*$` captura TODA a cauda da linha — com o
comentario inline ele devolvia a string inteira, que nao pertence a
`_L3_PLUS_LEVELS` (`:120`), e o sinal de escalacao L3 morria em silencio
(rail r2 do land, P2, reproduzido executando a funcao contra o arquivo).

### 0.2 De onde sai `budget_tokens: 180-360k`

QUATRO modulos canonicos INCONDICIONAIS do §3 — o validador, o chamador, o
emissor `audit_emit.py` e `SPEC/v1/audit-log.schema.md` (rail r2 do land,
lane de TEXTO, P1: a redacao anterior dizia «se a truncagem virar evento
novo, emissor + schema» e CONDICIONAVA os dois, contradizendo o §3 e a «Regra
desta wave» do §4, que os declaram incondicionais mesmo SEM acao nova) — mais
os sitios do bump de VERSAO que todo diff em `SPEC/v1/` arrasta (§3-bis),
testes de contrato e medicao antes/depois. A cerimonia GPG, a autorizacao de
kernel e a espera de 24 h do RC sao o custo dominante.

### 0.3 Por que `context_risk: high`

`PLAN-SCHEMA:329-330` define `high` como ">300k OU split-session"; com
`budget_sessions: 2` esta wave e split-session, entao `high` e a
classificacao correta INDEPENDENTE do teto de tokens (rail r10, lane de
mecanismo: a justificativa anterior olhava so o teto).

### 0.4 Os QUATRO bloqueios de `external_wait`

Rail r9, r11 e r1 desta derivacao — a redacao anterior dizia TRES e enumerava
(i) a (iv).

1. **(i) Assinatura GPG do Owner** num sentinel cujo Scope enumera TODOS os
   paths tocados — os QUATRO canonicos INCONDICIONAIS do §3
   (`.claude/hooks/_lib/guardrail_validator.py`, `.claude/hooks/SessionStart.py`,
   `.claude/hooks/_lib/audit_emit.py`, `SPEC/v1/audit-log.schema.md`; oraculo
   `check_canonical_edit.py --is-canonical` = 1 em todos) mais o teste dos
   AC-1..AC-3 e as superficies condicionais do §4 se a wave escolher acao nova.
2. **(ii) DOIS deles sao KERNEL** — `SessionStart.py` e `audit_emit.py` estao
   em `_KERNEL_PATHS` (`check_arbitration_kernel.py:25-36,99,218`) e sentinel
   assinado NAO destrava path de kernel: a wave exige, no MESMO shell,
   `CEO_KERNEL_OVERRIDE=<motivo>` + `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` do
   Owner, com o evento de auditoria conferido depois (AC-6).
3. **(iii) §1.4 (lifecycle)** — este followup so entra em `executing` DEPOIS
   que o PLAN-186 chegar a `done`; hoje ele esta `executing`.
4. **(iv) A cascata de VERSAO** (rail r2 do land, lane de MECANISMO, P1) —
   como `SPEC/v1/audit-log.schema.md` e INCONDICIONAL, qualquer das duas
   opcoes do §4 dispara o contrato de versao do repo: `VERSIONING.md:12-19`
   («It moves on: Any change to a file under `SPEC/v1/`») faz o bump ser
   OBRIGATORIO, e `VERSIONING.md:81-84` impoe uma espera RC->GA de **24 h** a
   todo bump MINOR, mecanicamente cobrada pelo step «Assert 24h Codex re-pass
   window» da `release.yml`. Os sitios do bump entram no Scope do sentinel
   pelo §3-bis; um Scope que os omita nao consegue nem landar nem cortar a
   tag.

### 0.5 De onde sai `eta_calendar`

`PLAN-SCHEMA.md:336-350` manda `eta_calendar = max(external_waits)`. Das
QUATRO esperas de §0.4, tres sao GATILHOS do Owner sem duracao propria (fecho
do pai, assinatura GPG, override de kernel) e a quarta tem duracao MEDIDA em
contrato — as 24 h do hold RC->GA (`VERSIONING.md:78-88`, step «Assert 24h
Codex re-pass window» da `release.yml`, ADR-103), obrigatorias porque
`SPEC/v1/audit-log.schema.md` e INCONDICIONAL (§3-bis). Logo o maximo e o
hold de 24 h, que e um PISO entre a ultima tag RC e a tag **GA**: a tag RC
pode sair no mesmo dia do land, a tag GA nao.

> **Lineage (PLAN-SCHEMA §1.4).** O defeito foi encontrado DURANTE a execucao
> do PLAN-186 (W1, pacote `w1-widen`, S345): a bateria completa de hooks nao
> fechava na maquina do mantenedor, o que bloqueia o `EXPECTED-BASELINE` e,
> por consequencia, o SIGN da propria wave-mae. A cura de ENTRADA (o teste)
> saiu no pacote `walkroot-test-fix`; a cura de CODIGO foi descopada dali
> — ela toca um path canonico e pede cerimonia propria — e e o escopo deste
> followup. Ele **nao reabre** nenhum AC do PLAN-186 e **nao abre escopo
> novo**.
>
> **Status honesto do parentesco:** o PLAN-186 esta `status: executing`, nao
> `done`. Por isso este plano nasce e permanece em `status: draft`; a
> restricao de ciclo de vida da §1.4 («A followup … cannot enter
> `status: executing` until its parent reaches `done`») e o gate de partida,
> nao uma formalidade.
>
> **Nome (levantado por varias lanes do rail).** O slug tem cinco palavras
> (`hint-discovery-walk-from-root`), dentro do 2-5 de `PLAN-SCHEMA.md:171-177`.
> A `PLAN-SCHEMA.md:156-160` **nao exprime preferencia: e uma REGRA**, e a
> citacao literal e «**Do NOT use when:** — The work is net-new scope
> unrelated to the parent's residuals → allocate a new monotonic `NNN`
> instead». **rail r7 [J1], P1:** a redacao anterior chamava essa clausula
> de «PREFERENCIA declarada», fundindo numa unica frase duas afirmacoes
> separadas — o que a clausula MANDA, e o que os gates fazem com ela:
>
> - **forca normativa** — a clausula diz «Do NOT», nao «prefira». A
>   parafrase estava ERRADA e esta corrigida aqui;
> - **verificacao** — o que foi MEDIDO e SO isto: com este arquivo
>   presente na arvore, `.claude/scripts/validate-governance.sh` COMPLETO
>   passa com `Errors: 0`. **rail r8 [K2], P2:** dai NAO se conclui que
>   nenhum gate implementa a clausula, e a redacao anterior concluia. Um
>   gate que a implementasse aceitaria um plano que se qualifica pelo
>   «Use when» — que e exatamente o que este plano alega ser —, entao a
>   medicao e compativel com as DUAS leituras e nao decide entre elas.
>   O que ela estabelece, e so isso, e que este arquivo nao esta sendo
>   REJEITADO pela governanca de hoje.
>
> Este plano **nao alega que a clausula nao existe**. Alega que o
> ANTECEDENTE dela nao se aplica: o escopo aqui e RESIDUAL — a cura de
> CODIGO descopada do PLAN-186 durante a execucao dele — que e literalmente
> o «Use when» da §1.4 (`PLAN-SCHEMA.md:147-154`), e `-FOLLOWUP-` e a forma
> que a §1.4 prescreve para esse caso, ja usada neste repo
> (`PLAN-185-FOLLOWUP-*`).
> **Se o Owner ler o antecedente ao contrario** — escopo net-new, nao
> residual — entao este nome e um **DESVIO DECLARADO** da regra de
> `PLAN-SCHEMA.md:156-160`, e nao uma leitura dela; e a saida ja esta
> pre-computada e e barata: um `mv` mais as linhas `id`/`title`, antes de
> qualquer execucao. Quem decide e o Owner, no debate que o `level: L3` ja
> exige — e este paragrafo existe para que ele decida sobre a regra COMO
> ELA ESTA ESCRITA, nunca sobre uma parafrase dela. As lanes anteriores
> levantaram o NOME; a lane de texto do land levantou a PARAFRASE.

## 1. O defeito, em uma frase

`_lib/guardrail_validator.discover_hint_dirs(project_dir)` aceita QUALQUER
diretorio como raiz — inclusive `/` — e limita a caminhada por
**profundidade** (`MAX_HINT_DIR_DEPTH = 25`) e por **contagem de hints
ENCONTRADOS** (`MAX_HINT_FILES = 64`), mas nao limita o **numero de
diretorios visitados** nem o **tempo**. Com raiz `/` os dois limites
existentes sao vacuos: a profundidade 25 ainda admite uma quantidade
astronomica de diretorios, e o contador de hints so avanca quando um hint e
achado — numa arvore que nao tem nenhum, ele nunca corta.

**O que NAO e (medido, nao suposto):** o processo nao esta travado num
syscall. Amostrado com `sample` do macOS por 5 s enquanto pendurado, a
thread principal da **3811 amostras**, das quais **835 em `__opendir2`** e
**686 em `readdir`** (684 delas dentro de `__getdirentries64`, que e
ANINHADO sob ele — os dois nao se somam). Sao PESOS somados do grafo de
chamadas, nao contagens de linha; o comando esta no §2 (4b).
Durante os 5 s AMOSTRADOS ele estava PROGREDINDO — a amostra nao diz nada
sobre o resto da corrida e nao e uma TAXA de iteracoes. O que falta nao e
progresso, e FIM UTIL. Bruto em `sample-raw-s345.txt`, artefato do pacote
`walkroot-test-fix`, que NAO viaja no commit — o que viaja e o comando (§2).

## 2. A evidencia

Tudo abaixo foi medido em 2026-09-05 pelo pacote `walkroot-test-fix`, que
guarda os artefatos brutos (`before-hang-s345.txt`, `after-cure-s345.txt`,
`final-run-s345.txt`, `flake-control-s345.txt`). As linhas "antes" foram
tomadas em worktree PRISTINA no HEAD `2292979`; as linhas "depois", no HEAD
`2f6cde1`, para onde o main andou durante a sessao. Os dois bases sao
intercambiaveis PARA ESTA MEDICAO, e isso foi verificado e nao suposto:
`git show <base>:<path> | shasum -a 256` da o MESMO digest nos dois bases
tanto para `test_session_start.py` quanto para `guardrail_validator.py`, e
`git diff --name-only 2292979 2f6cde1 -- <os 2 paths>` e vazio.

| Fato | Como foi medido | Resultado |
|---|---|---|
| `SessionStart.decide(repo_root=Path("/"))` alcanca a caminhada, e a cadeia tem UM elo de producao por passo | `grep -rn "discover_hint_dirs\|validate_hierarchical_hints" --include="*.py" . \| grep -v "^\./dist/" \| grep -v "^\./npm/" \| grep -v "/PLAN-155/staged/"`, medido NA DERIVACAO FINAL (worktree limpa): **11 linhas com e sem as exclusoes**, porque uma worktree limpa nao tem os espelhos gerados. As exclusoes ficam no comando porque num checkout POPULADO (com `dist/`, `npm/` e o staged do PLAN-155 no disco) elas sao o que separa producao de espelho — a contagem crua e do ESTADO DA ARVORE, nao do repo, e por isso nenhum numero cru e citado como fato do repo | unico chamador nao-teste de `validate_hierarchical_hints`: `SessionStart.py:397`; unico call-site de `discover_hint_dirs`: `guardrail_validator.py:469`, dentro dela. `_validate_injection_channels` repassa `project_dir = str(repo_root)` |
| o teste nao terminou na janela medida | comando **(1)** abaixo | **rc 142, 300 s** |
| a caminhada sozinha nao terminou na janela medida (isola o mecanismo do pytest) | comando **(2)** abaixo | **rc 142, 120 s** |
| depois da cura de ENTRADA o mesmo teste passa | comando **(3)** abaixo, na arvore com o pacote `walkroot-test-fix` | **rc 0, 1 passed em 0,08 s** |
| e a bateria COMPLETA passa a FECHAR | comando **(4)** abaixo, **5 execucoes** na arvore curada (a serie COMPLETA registrada por este pacote; lista integral em `EVIDENCE.md`) | fecha nas CINCO: **46,44 / 48,93 / 49,42 / 57,52 / 62,04 s** (mediana **49,42 s**; espalhamento max/min = **1,34x** na MESMA arvore, sem mudanca nenhuma entre as corridas). Os vermelhos sao PRE-EXISTENTES, de duas classes, e **cada um esta atribuido ao comando que o COLETA** (nota (b)) — (A) gates de relogio: `test_case_a_p99_under_5ms` (`.claude/hooks/tests/test_check_pair_rail_matrix.py:1152`), `test_prompt_submit_1mb_completes` (`.claude/hooks/tests/test_lifecycle_edge_cases.py:131`), `test_p99_1kb` (`.claude/hooks/tests/test_lifecycle_edge_cases.py:398`), `test_100k_by_skill_streams_under_budget` (`.claude/scripts/tests/test_audit_query.py:1095`); (B) UM observador de tmpdir compartilhado: `test_no_sandbox_leak` (`.claude/hooks/tests/test_adequacy_gate.py:78`), que sob `-n auto` enxerga o sandbox em voo de OUTRO worker. O comando **(4)** coleta `.claude/hooks/tests/` e portanto so pode produzir QUATRO deles (`test_case_a_p99_under_5ms`, `test_prompt_submit_1mb_completes`, `test_p99_1kb`, `test_no_sandbox_leak`); `test_100k_by_skill_streams_under_budget` e definido somente sob `.claude/scripts/tests/`, fora dessa colecao, e vem do comando **(6)**. O conjunto acima e a UNIAO do que foi OBSERVADO nas corridas que o pacote `walkroot-test-fix` registrou em `flake-control-s345.txt` (ADDENDUM 2: baterias de hooks e corridas da suite de scripts), nunca a saida de UMA execucao. **rail r8 [K1], P2:** essa uniao NAO e a serie de CINCO execucoes citada no inicio desta linha, e a redacao anterior narrava as duas como se fossem uma so. Sao duas amostras com propositos diferentes — a serie mede TERMINACAO da bateria de hooks; o censo de vermelhos e o conjunto do que reprovou nas corridas que o ADDENDUM 2 DECLARA cobrir, e ele declara a propria fronteira no cabecalho: «across 4 battery runs + 3 scripts-suite runs». **rail r9 [L1], P2:** a redacao anterior dizia «qualquer corrida registrada», que e mais do que o censo cobre — a serie de tempos tem CINCO baterias de hooks e o censo cobre QUATRO delas; a quinta esta FORA, e o `EVIDENCE.md` do pacote de origem guarda para ela um RESULTADO (quantos vermelhos), nao os NOMES. Consequencia pratica, e e a unica que importa aqui: **este conjunto e um PISO, nao um fecho.** Quem escrever o AC-5 NAO herda esta lista — re-deriva o baseline rodando os comandos (4) e (6) na propria arvore, e usa esta linha so para saber ONDE cada nome mora. **rail r7 [J2], P1:** a redacao anterior listava os CINCO como vermelhos do comando **(4)**, que nao coleta nem consegue coletar `test_100k_by_skill_streams_under_budget`; como este paragrafo e o baseline do AC-5, a atribuicao errada contaminava o proprio criterio de "nenhum vermelho NOVO". Atribuicao recitada nunca mais: esta linha e GERADA pelo censo da nota (b). A arvore PRISTINA no mesmo base tambem reprova (2 vermelhos) — mas note o que essa comparacao pode e nao pode ser: a bateria PRISTINA so termina COM o teste pendurado DESELECIONADO, entao ela e um controle do conjunto de vermelhos, NAO uma corrida completa comparavel em tempo. Detalhe e controles em `flake-control-s345.txt` |
| o caso `/` continua real, so que opt-in | comando **(5)** abaixo | **rc 142, 90 s** — e este e o oraculo de fecho deste plano |

> **(b) Censo dos vermelhos — DERIVADO, nunca recitado.** A atribuicao
> de cada vermelho a um comando e a saida deste censo de `def`, rodado na
> arvore em que este plano foi derivado: `grep -rnE '^[[:space:]]*def (test_case_a_p99_under_5ms|test_prompt_submit_1mb_completes|test_p99_1kb|test_100k_by_skill_streams_under_budget|test_no_sandbox_leak)\(' --include='*.py' .claude | grep -v '/staged'`
> — hoje CINCO nomes, QUATRO sob `.claude/hooks/tests/` (comando (4)) e UM sob `.claude/scripts/tests/` (comando (6)).
> RODE-O DE NOVO antes de usar §2 como baseline do AC-5: um teste que muda
> de suite muda de dono. Foi exatamente uma atribuicao RECITADA que o rail
> do land pegou aqui (P1), com um vermelho creditado a um comando que nao
> o coleta.

**Os comandos, INTEIROS (rail r9, P2).** A tabela abreviava com `…` e
`idem`, e os brutos citados sao artefatos do pacote `walkroot-test-fix` que
NAO viajam neste commit. O que viaja, e o que reproduz, sao estes comandos,
todos rodados da RAIZ do repo:

```bash
# (1) o teste sozinho, janela de 300 s  ->  rc 142 (nao terminou na janela)
perl -e 'alarm 300; exec @ARGV' -- python3 -m pytest -q -p no:cacheprovider \
  .claude/hooks/tests/test_session_start.py::TestSessionStartDecide::test_decide_never_raises

# (2) so a caminhada, janela de 120 s  ->  rc 142
#     (RE-EXECUTADO em 2026-09-05 no HEAD `de42dfb` para este plano poder
#      citar o comando exato, e nao uma abreviacao: rc=142, elapsed_s=120)
PYTHONPATH=.claude/hooks perl -e 'alarm 120; exec @ARGV' -- python3 -c \
  'from _lib.guardrail_validator import discover_hint_dirs; print(len(discover_hint_dirs("/")))'

# (3) o MESMO teste, com a cura de ENTRADA aplicada  ->  rc 0
python3 -m pytest -q -p no:cacheprovider \
  .claude/hooks/tests/test_session_start.py::TestSessionStartDecide::test_decide_never_raises

# (4) a bateria COMPLETA de hooks, na arvore curada  ->  FECHA
python3 -m pytest -q -n auto .claude/hooks/tests/

# (4b) de onde vieram os numeros de amostragem do §1. O processo do
#      comando (2), enquanto PENDURADO, foi amostrado por 5 s; o total da
#      thread sai da linha do "Call graph" e os demais sao SOMAS DE PESO
#      por simbolo. Um `grep -c` NAO serve aqui: ele conta LINHAS (daria
#      30 e 54), nao os pesos do grafo - foi o defeito que a rodada 11 do
#      rail pegou nesta mesma secao.
sample <PID do comando (2)> 5       # grava /tmp/Python_<data>.sample.txt
grep -m1 "Thread_" <relatorio>      # -> 3811 amostras na thread
python3 - <relatorio> <<'PY'
import re, sys
tot = {}
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    m = re.search(r"(\d+)\s+(__opendir2|readdir|__getdirentries64)\s+\(in", line)
    if m:
        tot[m.group(2)] = tot.get(m.group(2), 0) + int(m.group(1))
print(tot)   # -> __opendir2 835, readdir 686, __getdirentries64 684
PY

# (5) o caso opt-in continua real  ->  rc 142  (este e o oraculo do AC-4)
CEO_TEST_WALK_ROOT=1 perl -e 'alarm 90; exec @ARGV' -- python3 -m pytest -q \
  -p no:cacheprovider \
  .claude/hooks/tests/test_session_start.py::TestSessionStartDecide::test_decide_never_raises

# (6) a suite que o comando (4) NAO coleta — e a unica que DEFINE
#     test_100k_by_skill_streams_under_budget (nota (b)).
#     O vermelho daquele nome saiu de uma das TRES corridas desta suite
#     registradas pelo pacote `walkroot-test-fix` (as duas cujos brutos
#     viajam nele deram rc 0), nunca do comando (4).
perl -e 'alarm 1800; exec @ARGV' -- python3 -m pytest -q -p no:cacheprovider \
  .claude/scripts/tests/
```

> Ler o `rc` sem pipe: neste shell `cmd | tail; rc=$?` devolve o `rc` do
> `tail`. A serie de medicoes desta lane teve de ser refeita por causa disso.

**Sobre VELOCIDADE, este plano nao afirma nada.** Os tempos acima sao
evidencia de TERMINACAO (terminou / nao terminou), nunca de ganho de
desempenho — o repo nao faz claim de velocidade e este followup tambem nao.

**Sobre CI, este plano nao afirma nada.** Nenhuma medicao deste pacote e um
job, log ou SHA de CI; tudo acima e este host macOS. Se o comportamento em
CI importar para a wave, ele tem de ser MEDIDO la — nao herdado daqui.

Consequencia operacional: enquanto o caso `/` rodava por padrao, **a bateria
completa nao TERMINOU em nenhuma das janelas medidas neste host** — e sem
bateria completa nao ha `EXPECTED-BASELINE`, logo nao ha SIGN. (rail r1
desta derivacao, P2: a redacao anterior dizia "era impossivel numa maquina
de desenvolvimento"; os experimentos mostram ausencia de termino nas
janelas observadas AQUI, nao impossibilidade geral. O que fica provado e o
bloqueio OPERACIONAL do baseline naquela execucao, que ja basta para
justificar esta wave.)

## 3. Escopo canonico declarado

**Quatro** paths canonicos, todos INCONDICIONAIS (r7 provou que um nao
bastava; r10 e r11 provaram que dois tambem nao):

- `.claude/hooks/_lib/guardrail_validator.py` — `discover_hint_dirs` (e as
  constantes de limite ao seu lado);
- `.claude/hooks/SessionStart.py` — o CHAMADOR. Hoje ele faz
  `loaded, blocked = _gv.validate_hierarchical_hints(project_dir)` dentro de
  um `try: … except Exception: pass` (`SessionStart.py:397-410`): uma forma
  de retorno nova seria engolida em SILENCIO, sem breadcrumb. Ou o chamador
  entra no escopo, ou o requisito de truncagem visivel deste plano e
  inexequivel.
- `.claude/hooks/_lib/audit_emit.py` — **incondicional** (r11). Carregar a
  incompletude na provenance mexe nele mesmo SEM acao nova: a allowlist do
  `hint_provenance_recorded` nao tem campo de completude e a razao e enum
  fechado (detalhe no §4). **Tambem e KERNEL** (`check_arbitration_kernel.py:99`);
- `SPEC/v1/audit-log.schema.md` — **incondicional** pelo mesmo motivo, mais
  o espelho `guardrail_validator.HINT_PROVENANCE_REASONS` e o teste de
  paridade entre os dois.

Condicionais (so se a wave escolher ACAO NOVA em vez de estender o evento
existente): as superficies enumeradas no §4 — ADR, golden, pins de contagem
e o indice de ADRs.

### 3-bis. A cascata de VERSAO — INCONDICIONAL, e nao estava aqui

**Achado do rail r2 do land (lane de MECANISMO, P1), verificado no repo.**
`SPEC/v1/audit-log.schema.md` esta no escopo INCONDICIONAL acima; logo o
contrato de versao do repositorio dispara nas DUAS opcoes do §4, nao so na
opcao (ii). `VERSIONING.md:12-19` diz que o `VERSION` da raiz «moves on: Any
change to a file under `SPEC/v1/`» — e a mudanca aqui e ADITIVA (campo/razao
novos, ou acao nova), portanto **MINOR**. E `VERSIONING.md:78-88` impoe a
todo bump MAJOR ou MINOR uma espera **RC -> GA de 24 h**, cobrada
mecanicamente pelo step «Assert 24h Codex re-pass window» da
`.github/workflows/release.yml` (ADR-103).

Consequencias que o §3 anterior OMITIA e que passam a valer:

- Os sitios do bump entram no **Scope do sentinel** junto com os quatro
  canonicos. A lista exata e a que a cerimonia de release do repo ja usa e
  tem de ser **DERIVADA na hora** (nunca recitada de memoria) — o
  `release.sh bump` e os testes de `test_release_bump_sites.py` sao a fonte;
  um Scope que os omita reprova no proprio land.
- O **AC-6** passa a exigir, alem do `--write-golden` e do
  `generate-adr-index.py`, que o conjunto assinado inclua esses sitios.
- O `external_wait` ganha o quarto bloqueio (iv): as 24 h nao sao
  calendario de conforto, sao gate de CI — a wave pode cortar a tag **RC**
  no mesmo dia do land, mas nao a **GA** (rail r2 desta derivacao, P2: a
  redacao anterior proibia «cortar tag no mesmo dia» sem qualificar, e
  contradizia o `eta_calendar`, que permite a RC).
- O orcamento do `budget_tokens` foi re-derivado para 180-360k por causa
  disto e da correcao do escopo incondicional.

Nada disto muda a CURA tecnica (§4); muda o que precisa estar escrito no
sentinel antes de o Owner assinar.

**Onde a truncagem pode ser afirmada HOJE (medido, rail r9 lane de mecanismo,
P1).** Nao existe, no repo de hoje, consumidor que CARREGUE o conteudo dos
hints para dentro do contexto do agente: `_validate_injection_channels`
(`SessionStart.py:396-414`) chama `validate_hierarchical_hints`, emite
`hint_provenance_recorded` para cada entrada de `loaded + blocked` e devolve
**apenas contagens** (`instructions_blocked, hints_blocked`) — as duas listas
sao DESCARTADAS ali mesmo. Consequencia para este plano: a fronteira
fail-closed e a do PRODUTOR (a descoberta nao entrega como aceita a saida de
uma varredura incompleta) MAIS o registro de provenance; ela NAO pode ser
afirmada num consumidor que ainda nao existe. Se a wave criar (ou descobrir)
um consumidor que injete conteudo de hint, ele entra NESTE escopo e passa a
ter de consultar o flag — e isso e requisito escrito, nao suposicao.

Fora de escopo: o teste ja curado por `walkroot-test-fix` e qualquer outro
consumidor de `HINT_SKIP_DIRS`.

## 4. A cura proposta (UMA: limitar a caminhada e mostrar a truncagem)

> **Ordem revista pela medicao.** Antes da amostragem do `sample` este plano
> tratava a limitacao de (b) — "nao salva de um bloqueio dentro de UMA
> chamada de `opendir`" — como razao para nao usar (b). A amostragem (§1)
> mostra que, NAQUELA janela de 5 s e naquele host, o processo estava
> PERCORRENDO e nao parado num syscall: das 3811 amostras da thread, 835
> estao em `__opendir2` e 686 em `readdir`. Logo um teto por iteracao chega
> a rodar, que era o ponto. **A limitacao em si continua VALIDA** (rail r1
> desta derivacao, P2: a redacao anterior dizia "REFUTADO", e observar
> progresso numa janela nao refuta uma afirmacao geral sobre bloqueio) — o
> proprio §4(b) reafirma que uma unica chamada pode demorar arbitrariamente
> antes de devolver controle. **O que a medicao NAO
> diz:** uma TAXA de iteracoes. `sample` conta observacoes de pilha, nao
> voltas do laco; qualquer numero de "N iteracoes por segundo" precisaria de
> um contador, e este plano nao tem um.

**(a) NAO existe mais recusa de raiz — a rodada 7 do rail matou a segunda
versao dela pelo MESMO motivo que a primeira.** A proposta anterior devolvia
`[]` sem caminhar quando `root.parent == root`. Mas `/` pode ser um projeto
LEGITIMO: em container ou chroot, `CLAUDE_PROJECT_DIR` (ou o cwd) e `/`, e
`SessionStart.main()` aceita isso — nada no codigo proibe. Recusar ali
deixaria `/.claude/hints.md` e os hints aninhados **sem validacao e sem
provenance**: exatamente o furo de deteccao que a retirada da regra de
marcador (r6) tinha acabado de fechar.

> **A licao, pela segunda vez na mesma wave:** ausencia de evidencia de
> projeto NAO e evidencia de ausencia de hints. Toda variante de "recuso e
> devolvo `[]` sem olhar" fecha um canal de seguranca para ganhar custo. A
> resposta certa e LIMITAR a caminhada, nao pula-la.

**(b) A cura, agora UNICA: orcamento entre-yields + teto de diretorios
VISITADOS.** Um teto `MAX_HINT_WALK_SECONDS` (proposta: 2,0 s) verificado a
cada iteracao do `os.walk`, **mais** um teto deterministico
`MAX_HINT_DIRS_VISITED` (proposta: 5.000).

> **Isto NAO e um deadline duro, e o plano nao vai chama-lo assim (rail r6,
> P1).** `next(os.walk(...))` pode ficar arbitrariamente tempo dentro de
> `scandir` num unico diretorio gigantesco ou num mount lento ANTES de
> devolver o controle ao corpo do laco — nesse caso o teto de 2,0 s so e
> observado depois. Logo: (i) o AC nao pode prometer
> `MAX_HINT_WALK_SECONDS + 1 s` incondicionalmente; (ii) o teto de
> diretorios visitados existe porque ele NAO depende do relogio; (iii) um
> limite realmente duro exigiria fronteira de processo matavel — fora de
> escopo aqui, e nomeado como tal. O que sustenta o caso `/` e o teto
> DETERMINISTICO de diretorios visitados, que nao depende do relogio.

**Truncar tem de ser FAIL-CLOSED, nao so visivel.** A regra do repo para
matcher de seguranca e: entrada que o guard nao conseguiu processar e
BLOQUEADA, nunca aceita na duvida (CLAUDE.md §4). Inundar de diretorios e uma
entrada MOLDADA pelo atacante: quem quiser esconder um `hints.md` envenenado
so precisa estourar o teto antes que ele seja visitado. Entao a wave entrega
`complete=False` propagado ate o consumidor e, com `complete=False`, os hints
hierarquicos NAO sao carregados/aceitos — mais o teste de regressao
"inundacao ANTES do envenenado". Um breadcrumb sozinho seria aviso, nao
defesa.

**E `complete=False` vale para TODA saida incompleta, nao so para os dois
tetos novos (rail r8, P1).** As saidas incompletas de hoje foram ENUMERADAS
uma a uma no corpo atual de `discover_hint_dirs` (rail r9, P2 — uma classe
agregada de "erro de walk" nao falsifica as outras):

| # | ponto | linha (HEAD `de42dfb`) | efeito |
|---|---|---|---|
| 0 | `if not project_dir: return out` | `guardrail_validator.py:308-309` | devolve `[]` sem olhar (entrada vazia; classificar: e COMPLETO por definicao ou incompleto?) |
| 1 | `root.resolve()` / `is_dir()` falham | `guardrail_validator.py:311-315` | devolve `[]` — NADA foi olhado |
| 2 | `Path(dirpath).resolve()` falha | `:322-325` | **poda a subarvore inteira** |
| 3 | containment `relative_to` levanta | `:327-331` | poda a subarvore inteira |
| 4 | poda por `HINT_SKIP_DIRS` (DUAS pernas: a poda de `dirnames` e o `_is_under_skip_dir(rel): continue`) | `:334-337` **e** `:341-342` | politica DELIBERADA (nao e incompletude; fica declarada para nao virar surpresa) |
| 5 | teto `MAX_HINT_DIR_DEPTH` | `:339-340` | poda tudo abaixo |
| 6 | `hint.is_file()` levanta `OSError` | `:344-345,349-350` | perde o hint DAQUELE diretorio |
| 7 | corte por `MAX_HINT_FILES` | `:347-348` | `break` — para de olhar |
| 8 | `except Exception` externo | `:351-352` | devolve o parcial acumulado |
| 9 | `scandir` falha DENTRO do `os.walk` | (sem linha: `onerror=None`) | o diretorio some em SILENCIO — e o `onerror` NAO cobre tudo, ver abaixo |
| 10 | `DirEntry.is_dir()` levanta `OSError` dentro do `os.walk` | (sem linha) | a subarvore INTEIRA some sem excecao **e sem `onerror`** |

Se so os tetos novos marcarem incompletude, o atacante volta a esconder o
`hints.md` envenenado — basta po-lo depois de 64 hints benignos (#7), abaixo
do teto de profundidade (#5), ou atras de um diretorio que faz o `scandir`
falhar (#9/#10).

> **O latch `os.walk(onerror=...)` NAO basta (rail r10, P1) — verificado no
> interpretador que roda aqui.** `inspect.getsource(os._walk)` mostra, no
> CPython 3.9.6:
>
> ```
>     is_dir = entry.is_dir()
> except OSError:
>     # If is_dir() raises an OSError, consider that the entry is not
>     is_dir = False
> ```
>
> Ou seja: `onerror` e chamado para a falha do `scandir` do diretorio (#9),
> mas **nao** para a falha de classificacao de uma entrada (#10) — a entrada
> vira "arquivo", a subarvore inteira desaparece e a caminhada segue se
> dizendo completa. Portanto a wave **nao** pode fechar #10 com `onerror`:
> ou troca o `os.walk` por uma travessia propria com `os.scandir`, que POSSUI
> e registra os tres erros (abrir o diretorio, iterar, classificar a
> entrada), ou instrumenta os tres de outro jeito comprovado. Se o `os.walk`
> sair, o AC-1 passa a patchar o simbolo NOVO da travessia.

Entao a wave: (i) CLASSIFICA a linha #0 (entrada vazia: completo por
definicao, ou incompleto?) e escreve a decisao no §3; (ii) marca
`complete=False` nos pontos 1,2,3,5,6,7,8,9,10 — o #4 fica de fora, como
politica DELIBERADA e declarada; (iii) cobre com oraculo SEPARADO **cada
ponto incompleto** (parametrizado ou um teste por ponto), incluindo os que um
teste de "erro de walk" nao alcanca: `no-project-dir` (#0),
`root-resolve-error` (#1), `dir-resolve-error` (#2),
`containment-violation` (#3), `poison-below-depth-prune` (#5),
`poison-behind-stat-error` (#6), `poison-after-file-cap` (#7),
`outer-exception` (#8), `poison-behind-scandir-error` (#9) e
`poison-behind-is-dir-error` (#10), alem da inundacao do AC-3. **E um controle
NEGATIVO para o #4** (rail r11): um `hints.md` envenenado DENTRO de um
`HINT_SKIP_DIRS` continua sendo ignorado e **sem** marcar `complete=False` —
se a troca do `os.walk` por travessia propria perder a poda, esse controle
fica vermelho em vez de a politica sumir em silencio. Um teste
agregado de "erro de walk" ficaria verde com a maioria dos pontos
esquecidos.

**E as superficies disso sao declaradas AQUI, nao descobertas no meio.** A
forma de retorno (uniforme, com o flag de completude) e o canal do breadcrumb
sao decisao do §3. Sobre o canal, o rail r10 (lane de mecanismo) mostrou que
"dois arquivos" era uma cascata SUBDECLARADA: registrar UMA acao nova de
auditoria arrasta, verificado no repo em `de42dfb`, **oito** superficies
(a redacao anterior dizia «cinco» e contradizia a propria tabela, que sempre
teve OITO linhas numeradas — rail r2 do land, lane de MECANISMO, P2; como o
AC-6 DERIVA daqui o conjunto exato de paths assinados, uma contagem menor
produzia cerimonia sub-escopada. As linhas 6 e 8 AGRUPAM mais de um arquivo,
entao o conjunto de paths CONCRETOS e maior que oito e tem de ser expandido
na hora de escrever o Scope):

| # | superficie | por que |
|---|---|---|
| 1 | `.claude/hooks/_lib/audit_emit.py` | `_KNOWN_ACTIONS` + a allowlist por acao |
| 2 | `SPEC/v1/audit-log.schema.md` | tabela de acoes + bump MINOR |
| 3 | um **ADR novo** | `SPEC/v1/audit-log.schema.md` §Additivity: "Adding a new action literal → MINOR bump + new ADR" |
| 4 | `.claude/data/audit-registry.golden.txt` | golden gerado; `check-audit-registry-coverage.py --check` compara byte a byte e falha com diff |
| 5 | `.claude/hooks/tests/test_audit_emit_api_contract.py:861` | pina `sha256(sorted(_KNOWN_ACTIONS))` **e** a contagem (`331`) — as duas asercoes quebram; e o unico pin do censo (nota (a)) que quebra DUAS vezes, por isso tem linha propria |
| 6 | os DEMAIS pins exatos de `331`, DERIVADOS do censo da nota (a) — hoje **5**: `.claude/hooks/tests/test_audit_emit_plan163_lifecycle_actions.py:173`, `.claude/hooks/tests/test_check_ledger_checkpoint.py:1148`, `.claude/hooks/tests/test_codex_egress_proof_telemetry.py:125`, `.claude/hooks/tests/test_git_bypass_guard.py:885`, `.claude/hooks/tests/test_w5_scrub_enforcement.py:97` | cada um asserta `len(_KNOWN_ACTIONS) == 331`; com a acao nova a contagem vira 332 e cada pin vira um vermelho. **rail r5 [I1], P2:** a redacao anterior RECITAVA «mais DOIS» e nomeava dois destes 5 — os outros ficavam fora do Scope assinado e o AC-5 (nenhum vermelho novo) era insatisfazivel. Contagem recitada nunca mais: esta linha e GERADA pelo comando da nota (a) |
| 7 | `.claude/adr/README.md` | indice GERADO; `generate-adr-index.py --check` compara |
| 8 | `CLAUDE.md:54`, `README.md:186`, `README.pt-BR.md:166` | espelhos com a contagem EXATA de ADRs (hoje `198`), cobertos por `verify-counts` |

> **(a) Censo dos pins de `331` — DERIVADO, nunca recitado.** As linhas 5 e 6
> desta tabela sao a saida deste comando, rodado na arvore em que este plano
> foi derivado: `grep -rn 'len(.*_KNOWN_ACTIONS.*), *331' --include='*.py' .claude | grep -v '/staged'`
> — hoje **6** arquivos (1 na linha 5, 5 na linha 6). RODE-O DE NOVO ao
> escrever o Scope do AC-6 e compare com a lista acima: ela e o estado de UM
> commit, nao uma constante. Foi exatamente uma contagem RECITADA que o rail
> r5 pegou aqui (P2), com tres pins fora do escopo assinado.

**E nao ha caminho "de graca" (rail r10, P2 — verificado no repo).** A ideia
de "usar o canal ja existente e nao mexer em auditoria" NAO se sustenta: o
evento que existe hoje, `hint_provenance_recorded`, tem allowlist FECHADA
(`audit_emit.py:8583-8590`: `reason, rel_dir_depth, family_hits,
bytes_scanned` + envelope) — **nao ha campo de completude** — e a razao e um
enum FECHADO (`:8597-8599`: `loaded, blocked_injection, blocked_oversize,
read_error, other`) em que qualquer valor de fora e COAGIDO para `other`.
Carregar a incompletude na provenance exige, portanto, mexer em
`audit_emit.py` **e** no espelho `guardrail_validator.HINT_PROVENANCE_REASONS`
**e** no schema, mesmo SEM acao nova — mais o teste de paridade entre os
dois espelhos.

**Regra desta wave, por causa disso:** `.claude/hooks/_lib/audit_emit.py` e
`SPEC/v1/audit-log.schema.md` entram no §3 e no Scope do sentinel
**INCONDICIONALMENTE**. A decisao que sobra e apenas *como* carregar a
incompletude: (i) campo/razao novos no evento existente (superficies 1, 2 e o
espelho + paridade), ou (ii) acao NOVA, que soma as OITO superficies da
tabela acima (paths concretos expandidos das linhas agrupadas) — e o pathname exato do ADR novo tem de ser ALOCADO antes de
assinar, porque ele entra no Scope — e faz o AC-6 exigir o `--write-golden`
**e** o `generate-adr-index.py` no MESMO commit. A opcao
e do §3 e e tomada ANTES de comecar; um escopo que declare menos reprova nos
gates de auditoria ou obriga a alargar o Scope no meio da wave, que e
exatamente o que a cerimonia proibe.

**Truncar tem de ser VISIVEL.** Devolver uma lista parcial calada faz
`validate_hierarchical_hints` nao conseguir distinguir "acabou" de "estourou
o orcamento" — hints mais profundos ficariam sem validacao E sem
provenance, sem ninguem saber. Entao a funcao sinaliza a truncagem ao
chamador (campo/flag no retorno, sem levantar) e o `SessionStart` emite
breadcrumb de timeout. Contrato preservado: continua **nunca levantando** e
continua shallow-first; o que muda e que a truncagem passa a ser
observavel.

**E o caso `/` do teste?** Ele passa a terminar NA ARVORE DO AC-4 (e enquanto
os yields continuarem chegando) porque a caminhada e
limitada: o corte vem depois de um numero DETERMINISTICO de diretorios
visitados — o que fica limitado e o NUMERO de diretorios, nao o tempo (um
unico `scandir` pode demorar arbitrariamente; nota de (b)). O resultado sai
parcial e SINALIZADO, e um `/` que seja projeto de verdade continua tendo
seus hints validados ate o teto. **Este plano nao promete custo de boot nem
tempo de parede em arvore nenhuma.**

O contrato publico muda de UM jeito, deliberado e testado: a truncagem
passa a ser observavel (acima). O resto fica — nunca levanta, shallow-first.

## 5. Acceptance criteria (falsificaveis, com o oraculo)

- **AC-1 [P0] a caminhada PARA por construcao, nao por cronometro — e o
  oraculo do CONTADOR nao pode depender do relogio (rail r9, P2).** Com
  `os.walk` substituido no namespace do modulo por um gerador que produz
  diretorios INDEFINIDAMENTE **e com o teto de TEMPO neutralizado no mesmo
  teste** (`MAX_HINT_WALK_SECONDS` patchado para infinito, ou o relogio
  monotonico injetado e congelado), `discover_hint_dirs("/")` retorna — sem
  excecao, com resultado parcial e sinalizado — depois de EXATAMENTE
  `MAX_HINT_DIRS_VISITED` diretorios. **O teste conta PEDIDOS DE AVANCO, nao
  ENTREGAS** (rail r1 desta derivacao, P2 — as duas medidas divergem: se a
  sentinela e levantada ANTES da entrega seguinte, o gerador «entregou»
  exatamente o teto mesmo SEM limitador nenhum, e uma igualdade sobre
  entregas passaria). O gerador falso incrementa `requests` no TOPO de cada
  avanco, ANTES de qualquer checagem, e marca `sentinel_requested` quando e
  puxado alem do teto; o AC exige as DUAS coisas —
  `requests == MAX_HINT_DIRS_VISITED` **e** `sentinel_requested is False`.
  Sem esse par, um `return []` especial
  para `/` (a recusa que este plano acabou de matar, se alguem a
  reintroduzir) passaria como se tivesse cortado. **Por que a neutralizacao
  do relogio e obrigatoria:** com os dois tetos ativos ao mesmo tempo, uma
  maquina carregada faz o teto de 2,0 s cortar ANTES do contador, e a
  igualdade exata vira flake — o teste mediria a carga do host, nao a
  existencia do contador. **O caminho de FALHA e FINITO por construcao (rail
  r2 do land, P2):** o gerador falso nao e infinito de verdade — ele entrega
  no maximo `MAX_HINT_DIRS_VISITED + 1` diretorios e, ao ser pedido o de
  indice `cap + 1`, LEVANTA uma excecao sentinela do proprio teste. Com o teto
  implementado esse pedido nunca acontece; sem ele, o teste morre em UM passo
  extra, com mensagem propria, em vez de pendurar ate o alarme do runner (que
  e o defeito que este followup existe para curar — reproduzi-lo no red
  control seria mediocre). **Segunda perna, porque o contrato e «nunca
  levanta»:** se a implementacao ENGOLIR a sentinela (`except Exception`) e
  devolver parcial, nada chega ao teste pela via da excecao — por isso o
  oraculo que DECIDE e o par de contadores acima, e ele reprova por DUAS
  condicoes independentes: `requests != MAX_HINT_DIRS_VISITED` (a caminhada
  parou cedo ou tarde demais) ou `sentinel_requested is True` (foi puxada
  alem do teto e a excecao foi engolida). **Terceira perna,
  belt-and-braces:** a probe roda com um limite de parede curto e explicito
  (subprocesso com timeout, ou `signal.alarm` no proprio caso), e estourar
  esse limite e FALHA NOMEADA do teste, nunca um verde por omissao.
- **AC-1b [P1] o teto de TEMPO tem oraculo PROPRIO — e ele mede o CORTE, nao
  a etiqueta.** Com o contador neutralizado (`MAX_HINT_DIRS_VISITED`
  patchado para infinito) e o RELOGIO INJETADO (um `monotonic` falso que
  avanca por chamada), a chamada retorna com `complete=False` depois de o
  orcamento estourar. **`complete=False` sozinho NAO fecha este AC** (rail
  r1 desta derivacao, P2): uma implementacao que apenas MARQUE a
  incompletude quando o relogio passa do orcamento, continue percorrendo a
  arvore inteira e devolva o resultado no fim satisfaz a etiqueta sem ter
  teto de tempo algum — e neutralizar o contador nao elimina esse falso
  verde. Entao o oraculo e de CONSUMO: a arvore falsa e uma sequencia
  FINITA e conhecida, o relogio injetado estoura o orcamento num avanco
  ESCOLHIDO (digamos o k-esimo), e o AC exige que **nenhum diretorio depois
  do k-esimo tenha sido pedido**. **Metade VERMELHA:** sem o corte temporal,
  esse mesmo caso falha, porque a sequencia inteira e consumida.
  **Relogio injetado, nao `sleep` (rail r11):** dormir de verdade faz o
  teste pagar o orcamento em tempo de parede e o torna sensivel a carga
  do host; um relogio falso e deterministico e instantaneo. Este AC e separado do
  AC-1 justamente porque cada teto tem de ser falsificavel SOZINHO: remover
  so o contador ainda pararia pelo relogio, e remover so o relogio ainda
  pararia pelo contador — um teste unico nao acusaria nenhuma das duas
  remocoes. **O que este AC nao afirma:** um limite superior de tempo valido
  para qualquer arvore (nota de (b) sobre `scandir`).
- **AC-2 [P0] o limite NAO fecha canal de deteccao — controle POSITIVO de
  SEGURANCA.** Este AC existe porque DUAS versoes deste plano ja tentaram
  ganhar custo pulando a caminhada (§4(a)). Com `os.walk` REAL e dentro do
  teto: (i) `discover_hint_dirs()` sobre um tmpdir SEM `.git` e SEM
  `.claude/.framework-version`, com um `.claude/hints.md` ENVENENADO num
  subdiretorio, **continua achando o hint**; (ii) o mesmo vale para uma
  raiz que seja `/` num container — nenhuma raiz e recusada sem ser olhada.
  `test_poisoned_nested_hint_is_recorded` continua verde sem tocar na
  fixture.
- **AC-3 [P1] o teto de DIRETORIOS dispara, a truncagem e FAIL-CLOSED, e a
  inundacao nao esconde nada.** (O teto de TEMPO nao e exercitado aqui: ele
  e o AC-1b. Como no AC-1, o orcamento de tempo fica NEUTRALIZADO neste
  teste — senao, num host carregado, o corte por relogio acontece antes de
  a inundacao chegar ao hint envenenado e o AC passa sem nunca provar a
  defesa por contagem.) Numa arvore sintetica com mais de
  `MAX_HINT_DIRS_VISITED` diretorios rasos (baratos de escanear, para o laco
  de fato re-entrar): a chamada retorna sem excecao, com `complete=False`, e
  o `SessionStart` emite o breadcrumb pelo canal declarado no §3.
  **O teste que FECHA o AC usa um hint LIMPO, nao um envenenado — e essa
  escolha e o AC inteiro (rail r2 do land, P1).** A redacao anterior plantava
  um `hints.md` ENVENENADO ATRAS da inundacao e exigia que nenhum hint saisse
  como aceito: oraculo VACUO, porque as duas unicas posicoes possiveis passam
  sem provar nada — depois do teto o hint nunca chega a ser descoberto, e
  antes do teto quem o barra e o scanner de injecao que JA existe. Nas duas, a
  assercao fica verde com a truncagem fail-closed AUSENTE. A forma correta:
  1. o hint plantado e **LIMPO** — conteudo que o scanner de injecao aceita
     hoje, verificado no MESMO teste pelo controle positivo do item 3;
  2. ele fica **ANTES** do corte, na ordem de visita FIXADA pelo teste (o
     gerador falso entrega os diretorios numa ordem declarada, nao a ordem do
     sistema de arquivos), e o teto estoura DEPOIS dele: o hint E descoberto,
     e o resultado da descoberta e INCOMPLETO;
  3. **oraculo de tres vias, e nenhuma delas passa por acidente:**
     (a) VERDE — com a truncagem fail-closed implementada, esse hint limpo
     NAO aparece em `loaded`; aparece em `blocked` com razao de
     INCOMPLETUDE, distinta de qualquer razao de conteudo;
     (b) VERMELHO — removida SO a checagem de `complete=False` (a linha da
     cura, nada mais), o MESMO hint volta a `loaded`; um AC que nao exiba
     esta metade nao esta provando a cura, esta descrevendo-a;
     (c) CONTROLE POSITIVO — na MESMA arvore, com o teto elevado de modo que
     a descoberta termine `complete=True`, o hint limpo carrega
     normalmente. E isto que atribui a retencao a INCOMPLETUDE e nao ao
     conteudo do hint nem a arvore.
  4. **quarto caso, pelo `SessionStart`: incompletude com as DUAS listas
     VAZIAS** (rail r1 desta derivacao, P2). Os tres casos acima sempre
     colocam algo em `blocked`, entao uma implementacao que emita
     provenance apenas ao ITERAR essa lista passa nos tres — e a
     descoberta incompleta que nao achou hint NENHUM continuaria sem
     breadcrumb, que e exatamente a possibilidade descrita no defeito de
     origem (truncar em silencio). O caso: o teto estoura ANTES de qualquer
     hint; `loaded` e `blocked` saem vazias; o AC exige mesmo assim um
     evento PERSISTIDO de incompletude no canal do §3, verificado no log,
     nao no valor de retorno.
  O caso ENVENENADO continua no teste como NAO-REGRESSAO (o scanner nao pode
  ter afrouxado), mas explicitamente NAO e o oraculo desta AC. **Por que nao
  "o consumidor nao carrega":** hoje NAO existe consumidor que carregue
  conteudo de hint (§3, medido em `SessionStart.py:396-414`), entao um AC
  escrito sobre ele passaria sem gatear coisa nenhuma — a fronteira que
  EXISTE, e a unica que este AC mede, e a particao `loaded`/`blocked` que
  `validate_hierarchical_hints` devolve.
- **AC-3b [P0] a travessia NOVA nao passa a seguir symlink de diretorio —
  invariante de SEGURANCA congelado ANTES da reescrita.** Achado do rail r2
  do land (lane de TEXTO, P2): o §4 admite trocar `os.walk` por uma
  travessia propria com `os.scandir` para poder registrar os TRES erros, e
  nenhum dos ACs acima prende a propriedade que o `os.walk` de hoje entrega
  de graca — `followlinks=False`
  (`guardrail_validator.py:319`, documentado em `:296-301`: «symlinked dirs
  are NOT followed»). Sem este AC, TODOS os outros podem passar enquanto um
  diretorio symlinkado volta a ser atravessavel, que e exatamente a classe
  que o PLAN-133 G3 fechou. **Oraculo, e ele e ADVERSARIAL:** numa arvore
  temporaria, um subdiretorio real `alvo/` contendo `.claude/hints.md` e um
  symlink `atalho -> alvo` plantado na raiz da caminhada. **O oraculo observa
  as OPERACOES DE ENUMERACAO, nao o resultado** (rail r1 desta derivacao,
  P1): comparar achados nao decide nada, porque uma implementacao que
  ATRAVESSE o symlink, resolva os caminhos e deduplique devolve exatamente o
  mesmo conjunto — e, no caso do symlink que aponta para FORA da arvore, um
  containment aplicado DEPOIS da travessia descarta os achados externos com
  a mesma aparencia. Os dois passariam com `followlinks=False` ausente.
  Entao: o teste instrumenta a camada de enumeracao (`os.scandir` /
  `os.listdir` do modulo, ou o proprio `os.walk`) e registra TODO caminho
  para o qual ela e chamada; o AC exige que **nenhuma chamada de enumeracao
  tenha como alvo o caminho do symlink nem qualquer descendente por ele**.
  **Metade VERMELHA obrigatoria:** com a travessia de symlink HABILITADA
  (`followlinks=True`, ou a travessia propria seguindo `is_dir()` sem
  `follow_symlinks=False`), o MESMO teste tem de falhar apontando a chamada
  proibida. Um AC que so compare achados nao exibe essa metade — e o defeito
  que esta redacao corrige. Os dois casos (symlink interno e symlink para
  fora da arvore) continuam, agora como cenarios da mesma assercao de
  enumeracao. **Este AC vale nas DUAS opcoes do §4** — se a wave mantiver
  `os.walk`, ele e um teste de nao-regressao barato; se trocar, ele e a
  unica coisa que impede a reescrita de perder a defesa em silencio.
- **AC-4 [P0] o caso opt-in do `walkroot-test-fix` passa a TERMINAR.**
  O oraculo mantem o MESMO envelope de hoje — sem o alarme ele nao
  falsifica, so pendura: `CEO_TEST_WALK_ROOT=1 perl -e 'alarm 90; exec @ARGV'
  -- python3 -m pytest -q -p no:cacheprovider
  .claude/hooks/tests/test_session_start.py::TestSessionStartDecide::test_decide_never_raises`
  — que e o comando **(5)** do §2, verbatim, com o mesmo
  `-p no:cacheprovider` — deve sair **rc 0**. Hoje ele sai **rc 142**
  (§2). Este AC e o oraculo de fecho do plano.
  **O que o `alarm 90` e, e o que ele NAO e:** e o timeout do HARNESS,
  escolhido porque hoje o mesmo comando o estoura; ele afirma que ESTA
  arvore, com a caminhada limitada, termina dentro dele. **Nao** e
  promessa de tempo para arvore nenhuma — o que o plano garante e o
  corte por numero DETERMINISTICO de diretorios visitados, e um unico
  `scandir` pode demorar arbitrariamente (nota de (b)).
  **rc 0 sozinho e fraco** (rail r8): o teste so afirma JSON de lifecycle
  valido, entao um caminho que devolva rapido por OUTRO motivo — recusa
  especial de `/` reintroduzida, ou o import do validador engolido — tambem
  passaria. Por isso AC-4 fecha SOMENTE junto com AC-1 (o caminhador falso
  precisa ter sido chamado) e com o controle POSITIVO de raiz montada:
  `/.claude/hints.md` num container e de fato INSPECIONADO, com provenance.
- **AC-5 [P1] a bateria de hooks continua FECHANDO.** O oraculo e
  TERMINACAO e ausencia de vermelho NOVO — nao é "zero vermelhos" (§2 nomeia
  os pre-existentes) e **nao e tempo**. (i) a bateria completa
  (comando **(4)** do §2: `python3 -m pytest -q -n auto
  .claude/hooks/tests/`) termina ANTES e DEPOIS do patch,
  3 execucoes de cada lado, alternadas na MESMA sessao (pareado — e o unico
  jeito de nao confundir carga da maquina com efeito); (ii) nenhum vermelho
  fora do conjunto ja nomeado em §2, e todo vermelho novo tem de ser
  MEDIDO nas DUAS arvores, COM e SEM o patch, antes de contar — e a
  comparacao e que decide, nao a reproducao: um vermelho que aparece SO
  com o patch e, por definicao, a regressao que este AC procura, entao ele
  CONTA (rail r2 desta derivacao, P2: exigir que ele fosse «reproduzido em
  arvore COM e SEM o patch» excluia exatamente essa classe). **O nome nao
  basta — a ASSINATURA tambem entra** (rail r1 desta derivacao, P2): um
  teste ja vermelho por orcamento que passe a falhar por uma excecao NOVA
  continuaria autorizado pela lista de nomes do §2, entao a comparacao e
  (nome, tipo de falha) COM e SEM o patch, e uma assinatura diferente sob o
  mesmo nome conta como vermelho novo. E a reproducao ISOLADA e
  diagnostico, nao pre-requisito: um vermelho observado sob `-n auto` que
  nao reproduz sozinho e uma regressao dependente de concorrencia — a
  classe que o proprio §2 documenta — e continua contando.
  **Por que nao ha criterio de tempo:** medido nesta maquina, o espalhamento
  max/min entre execucoes da MESMA arvore, sem mudanca nenhuma, foi de
  **1,34x** (46,44 → 62,04 s, n=5) — qualquer teto plausivel cabe dentro do
  proprio ruido, entao um numero de tempo aqui nao falsifica nada e nao entra
  como AC.
- **AC-6 [P1] cerimonia — sentinel NAO basta, `SessionStart.py` e KERNEL.**
  Verificado no repo: `SessionStart.py` esta na lista de kernel de
  `check_arbitration_kernel.py:218`, e o proprio hook diz (`:25-36`) que um
  sentinel assinado NAO destrava um path de kernel. Entao a cerimonia desta
  wave e:
  1. sentinel assinado pelo Owner cujo **Scope enumera TODOS os paths que a
     wave vai tocar** — os canonicos do §3 MAIS o teste que os AC-1..AC-3
     mudam MAIS qualquer emenda de plano/ADR. `touched − scope = ∅` so fecha
     se o Scope for o conjunto REAL, nao so os dois arquivos "interessantes"
     (rail r8, P1);
  2. o escape hatch do Owner, no MESMO shell: `CEO_KERNEL_OVERRIDE=<motivo>`
     e `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`, com o evento de auditoria
     conferido depois;
  3. `audit_emit.py` e `SPEC/v1/audit-log.schema.md` entram no Scope
     **INCONDICIONALMENTE**, nas DUAS opcoes do §4 — nao "se o breadcrumb
     virar evento NOVO". Esta era a redacao anterior e ela contradizia o
     proprio §3 e a "Regra desta wave" do §4, que os declaram incondicionais
     mesmo SEM acao nova (rail r2 do land, P2). O que e CONDICIONAL a acao
     nova sao as outras superficies do §4 (ADR, golden, pins de contagem,
     indice de ADRs);
  4. os sitios do **bump de VERSAO** do §3-bis entram no MESMO Scope. Eles
     sao obrigatorios porque o item 3 e incondicional: `VERSIONING.md:12-19`
     move o `VERSION` da raiz a qualquer mudanca sob `SPEC/v1/`. A lista
     exata e DERIVADA na hora — `release.sh bump` e
     `test_release_bump_sites.py` sao a fonte, e recitar de memoria e o
     modo conhecido de sub-escopar a cerimonia; um Scope que os omita nao
     landa e nao corta tag. Junto com eles vem a espera de 24 h do hold
     RC->GA, que ja esta no `external_wait` (iv) e no `eta_calendar`.

## 6. Riscos e o que NAO fazer

- **Nao** transformar o corte num `raise`: o contrato "nunca levanta" e o
  que mantem o boot fail-open (ADR-005) — truncar e um RESULTADO sinalizado,
  nao uma excecao.
- **Nao** recusar raiz nenhuma sem olhar: nem por marcador (r6), nem por ser
  `/` (r7). As duas tentativas fecharam canal de deteccao.
- **Nao** ressuscitar a regra de marcador dentro desta wave: recusar toda
  raiz sem `.git`/`.claude/.framework-version` fecha um canal de deteccao de
  hint envenenado (§4(a)) e reprova
  `test_poisoned_nested_hint_is_recorded`. Se ela voltar, volta como wave
  propria, com contrato de seguranca redesenhado e teste dedicado.
- **Nao** vender o teto de 2,0 s como deadline duro: entre dois yields do
  `os.walk` o processo pode ficar preso em `scandir`. O teto de diretorios
  VISITADOS existe exatamente por nao depender do relogio.
- **Nao** truncar em silencio: parcial-sem-sinal e indistinguivel de
  completo, e some com a validacao dos hints mais profundos.
- **Nao** reverter a cura de entrada do teste ao landar esta: o caso finito
  (`None`/`""` -> tmpdir vazio) continua sendo o caso PADRAO da bateria, e
  o que ele garante e TERMINACAO sobre uma arvore finita, nao velocidade
  (este repo nao faz claim de velocidade); o caso `/` continua opt-in, e a
  partir daqui ele termina no oraculo do AC-4 — nao "em qualquer arvore":
  um unico `scandir` ainda pode demorar arbitrariamente.
