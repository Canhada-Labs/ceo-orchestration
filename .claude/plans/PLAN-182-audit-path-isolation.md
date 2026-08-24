---
id: PLAN-182
title: Isolamento de runtime state por projeto — implementar o ADR-001 como escrito, quatro meses depois
status: executing
reviewed_at: 2026-08-20
reviewed_by: "Owner — autorizacao explicita em chat (S315, 2026-08-20): 'se ja esta pronto deixa como revisado e apto pra fazer'. Debate L3 round 1 fechado com veredito PROCEED (13 consensos) e ajustes do consenso incorporados ao corpo; validate_governance_fast = 0 findings; pair-rail codex 6 rodadas fechadas, 32 achados, todos curados."
created: 2026-08-20
owner: CEO
depends_on: []
blocked_on_adr: "RESOLVIDO (S318): emenda ao ADR-001 (AC-7) e emenda ao ADR-079 (OQ-4) LANDADAS em 32e29b1 — a W1 executou na S319 sob o sentinel SENT-S319"
budget_tokens: 300-450k (W0 levantamento 110-170k; W1 resolvedor+cerimonia 110-160k; W2 decisao do log historico 40-70k; W3 installer+adopters 40-60k) — re-orcado no round 1 do debate, onde dois criticos convergiram independentemente em 250-500k contra os 120-260k da primeira redacao
budget_sessions: 4-6
context_risk: high
external_wait: "nenhum"
tags: [runtime-state, audit, hmac, salt, confidentiality, isolation, adopter, adr-001]
---

> ## 🎯 PRÓXIMO FOCO RATIFICADO pelo Owner (2026-08-24): o CLI do resolvedor único
>
> Dar um `__main__` a `.claude/hooks/_lib/runtime_paths.py` é a cura de MAIOR
> retorno por cerimônia hoje, porque **um** patch canônico fecha TRÊS dívidas
> que estão bloqueadas pela mesma ausência:
>
> 1. **O bypass de governança dos dois templates de pre-push** (achado do
>    pair-rail na S325): `templates/{codex,grok}/pre-push-review-gate.sh`
>    constroem `.../projects/ceo-orchestration/state`, então os gates de
>    revisão cross-model **compartilham state entre projetos** — um APPROVE
>    gravado para um fingerprint de path-set num adopter SATISFAZ o gate em
>    outro. São consumidores SHELL: sem CLI não há como resolver
>    corretamente. Estão hoje em `_DECLARED_DEBT` (com anti-rot) em
>    `.claude/scripts/tests/test_templates_use_single_resolver.py`.
> 2. **`ceo-backup.sh` / `ceo-restore.sh`** operarem sobre o diretório
>    resolvido — mesma ausência de CLI (runbook da S325 §2).
> 3. **Alargar o censo M1** para ver `${VAR:-literal}`: simulado, o
>    offender-set de `--assert-migrated` vai de 0 para 2, e os dois são
>    exatamente os scripts do item 2. Sem o CLI, alargar tornaria VERMELHO um
>    gate que o `CLAUDE.md` §5 publica como verde.
>
> **A armadilha a não cair:** contornar com `python3 -c` inline criaria uma
> segunda convenção de invocação contra arquitetura já ratificada — a classe
> "ramo local reabre a classe" que o `CLAUDE.md` §4 proíbe. O CLI é a rota já
> decidida (OQ-6); o que falta é a cerimônia.

## 1. O que este plano realmente é

Achado na S315 durante os probes da W4 do PLAN-169: o fallback de
resolução do diretório de runtime state é o literal
`$HOME/.claude/projects/ceo-orchestration`, de modo que **todo projeto
com o framework instalado e sem env explícita compartilha o mesmo
diretório** — log, chave HMAC, salt, locks e state.

**O debate round 1 achou o enquadramento correto, e ele muda a natureza
do plano** (consenso F5): isto **não é uma decisão em aberto**. O
`ADR-001-runtime-state-directory.md` está **ACCEPTED desde 2026-04-11**,
com decision drivers literais *"prevent secret leakage via git, align
with Claude Code native memory, single canonical location"*, e define o
caminho como:

```
${CLAUDE_PROJECT_DIR_NATIVE:-$HOME/.claude/projects/<project-slug>}/
```

**`<project-slug>` — não um literal.** E `CLAUDE_PROJECT_DIR_NATIVE` é
consumido por **zero** arquivos `.py`/`.sh` do repositório: aparece
apenas no próprio ADR (`:73`, `:79`). O próprio ADR já previu este
plano, na consequência `(-)`: *"the `<project-slug>` derivation is
implicit … Both work; Sprint 3 may align them"*.

Portanto: **o literal é um defeito contra decisão ACCEPTED, adiado desde
abril**, e este plano é o alinhamento que o ADR-001 nomeou e nunca
recebeu. Isso tem duas consequências normativas: o blast radius
declarado no ADR (L2) está desatualizado perante os números medidos
(L3+), e **a emenda ao ADR-001 é entregável obrigatório antes da W1**
(AC-7), não documentação posterior.

### Evidência medida (histograma completo, substituindo o número errado da 1ª redação)

Log vivo, **15.355 linhas**. Distribuição do campo `project`:

| rótulo | eventos |
|---|---|
| `""` (vazio) | **10.254** |
| `/Users/…/<tenant-a>` | **2.136** |
| `/Users/…/<tenant-b>` | **1.706** |
| `/Users/…/ceo-orchestration` | **1.053** |
| `ceo-orchestration` | **7** |

Correções à primeira redação, todas apontadas pelo debate: são **dois**
tenants estrangeiros, não um; **este repositório emite sob dois rótulos
distintos**; e o número **310** que a primeira redação citava **não
reproduz sob nenhum predicado** (a soma na janela é 302). Eventos de
segurança de tenant estrangeiro confirmados exatos: `env_var_hijack_blocked`
28, `veto_triggered` 3, `git_hook_bypass_blocked` 1,
`output_scan_finding_suppressed` 841.

**Nota de redação (K9), registrada porque é contraintuitiva:** o log
**não** redige o que esta prosa redige — `project` é gravado como
caminho absoluto em claro, no mesmo registro em que `repo_path_hash` é
hasheado.

### O que é atribuível, e por que isso decide a W2

**68% do log (10.453 de 15.355) não é atribuível a projeto nenhum** —
10.254 com `project` vazio mais 199 sem o campo. A causa é código, não
env faltando: `project` é parâmetro do chamador com default `""`,
propagado por ~40 assinaturas em `audit_emit.py`.

**Nuance que o debate mediu e que muda a W2:** entre duas medições
sucessivas o total cresceu **+2.519** enquanto os não-atribuíveis
cresceram apenas **+149** (~6% dos novos). **Classificação corrigida
pelo pair-rail r9: isto é vazamento de TAXA REDUZIDA, não janela
fechada** — 149 eventos novos provam que ainda existem emissores
omitindo atribuição. "Janela histórica fechada" só pode ser declarada
depois de observar **ZERO** não-atribuíveis novos entre dois snapshots;
até lá a W2 trata a massa como legado quase-estático **e inclui a
identificação dos emissores que ainda omitem**. Isso mantém a opção
"segregar" da W2 **indisponível para a maior parte do log**, e desloca a
decisão para "declarar a janela (condicionada a zerar o fluxo)" contra
"arquivar e recomeçar a cadeia".

> ### ⚠️ Re-medição S321 — os números desta seção descrevem um corpus que NÃO EXISTE MAIS
>
> A W1 arquivou a cadeia medida acima e iniciou uma nova. **Nenhum dos
> três números desta seção reproduz hoje**, e eles ficam preservados como
> registro histórico, não como evidência viva:
>
> | claim da §1 | reproduz? | medido em 2026-08-22 |
> |---|---|---|
> | corpus de 15.355 linhas | **não** | 20.582 linhas na cadeia nova (2 segmentos) + 3.010 no dir legado |
> | 68% não-atribuível | **não** | **94,6%** na cadeia nova; 2,8% no legado (o adopter que o alimenta PASSA `project`) |
> | +149 novos ≈ 6% do fluxo ("taxa reduzida") | **não** | 15.208 novos = **~94%** do fluxo pós-land |
>
> A leitura correta inverte o diagnóstico da redação anterior: **não era
> vazamento de taxa reduzida em declínio** — 99,5% do fluxo era a suíte
> de testes escrevendo na cadeia viva (curado na S321, ver o Registro de
> execução da W2), e o resto é uma classe única de causa —
> o chamador omite `project=` e o default do emissor é `""`.
> A conclusão estrutural da §1 **sobrevive** (a atribuição é decisão do
> chamador, não do env); os números que a sustentavam foram substituídos.

## 2. O salt é o item mais grave, e a primeira redação não o mencionou

Dois mecanismos distintos, ambos verificados (consenso F2):

1. **Compartilhamento HOJE.** O `.salt` é único por `$HOME`
   (`injection_salt.py:63-70`), logo `prompt_sha256` correlaciona
   **entre projetos** — exatamente o oráculo que o ADR-079 existe para
   fechar. **A garantia do ADR-079 já é falsa** na fronteira de tenancy.
2. **Rotação silenciosa NA CURA.** `get_instance_salt()` (`:124-148`)
   **cunha e persiste na primeira chamada** quando o arquivo não existe,
   devolvendo `b""` apenas em falha de I/O. Mudar o diretório rotaciona
   o salt **sem erro, sem log, sem sinal** — contra o `## No rotation`
   do próprio módulo, cuja razão declarada é que a rotação invalida a
   correlação de `prompt_sha256` de todo o histórico.

A W1 precisa de carry-over explícito **ou** de emenda ao ADR-079. A
primeira redação discutia re-chavear o log e não citava o salt uma vez.

## 3. Por que curar pela metade é pior que não curar

Migrar um subconjunto **parte a cadeia**: se o estado HMAC se move
enquanto escritores permanecem no literal, `verify_chain()` passa a
acusar quebra onde não houve adulteração.

**Correção de tempo verbal (K12):** a primeira redação dizia "os
leitores seguem medindo o log contaminado". Isso é **falso** para
`token-estimator.py` e `ceo-cost.py`, que **já leem um log inexistente**
sempre que `CLAUDE_PROJECT_DIR` está setado — o predicado
`scoped.exists() or scoped.parent.is_dir()` passa pelo segundo disjunto
porque o diretório de transcripts existe, e o fallback legado é
inalcançável. Ou seja: **a migração parcial já está em curso**, sem
ninguém ter decidido. O plano trata disso como triagem, não como risco
futuro.

**O lock é o artefato mais perigoso da migração** (F12) e a primeira
redação não o listava: dois processos com resolvedores divergentes
seguram locks diferentes sobre o mesmo log. A ordem de migração do lock
é decidida na W0-US5, não improvisada na W1.

**Correção de fato (F8):** a primeira redação dizia "39 em
`.claude/scripts/` (tier NÃO-canônico)". **Não existe tier.**
`check_canonical_edit.py` casa por glob `.claude/hooks/*.py` (`:30`),
`_lib/*.py` (`:33`), `_lib/**/*.py` (`:35`) — **100% dos hooks e do
`_lib` são canônicos** — e enumera exatamente **5** arquivos de
`.claude/scripts/`. A justificativa correta para plano separado nunca
foi "escapa da cerimônia": é que **adiciona ~50 arquivos não-cerimoniais
a um pack de escopo fechado**.

## 4. Modelo de adversário e a propriedade de segurança em jogo

Escrito porque o debate mostrou que sem isto a W1 não sabe o que está
comprando (K7/K8).

- **Fronteira de confiança:** processos do mesmo UID. Entre eles não há
  origem inforjável — quem executa Bash já controla a sessão.
- **A propriedade que se perde hoje NÃO é "tamper-evidence degradada":
  é tamper-evidence AUSENTE na fronteira de tenancy.** Uma chave HMAC
  compartilhada significa que o projeto A pode forjar cadeia válida para
  eventos atribuídos ao projeto B. Chave-por-projeto e dir-por-projeto
  são decisões **separadas**, e a W0 tem de dizer qual compra o quê.
- **O QUE A MIGRAÇÃO NÃO COMPRA — corrigido pelo pair-rail r7, e é um
  erro de raciocínio da redação anterior, não de redação.** Sob o
  modelo de adversário declarado acima (mesmo UID), **chaves distintas
  por projeto NÃO restauram tamper-evidence entre tenants**: um processo
  comprometido do projeto A **lê** o diretório `0700` e a chave `0600` do
  projeto B, porque ambos pertencem ao mesmo UID. Modo de arquivo não é
  fronteira contra quem já está do lado de dentro dela. O que a migração
  compra, e é o que a W1 pode declarar: **fim da mistura ACIDENTAL** —
  cadeias que não se entrelaçam, atribuição correta, e `verify_chain()`
  com significado por projeto. Tamper-evidence de verdade entre tenants
  exigiria fronteira mais forte (UID separado, ou chave fora do alcance
  do processo), o que **não** está no escopo deste plano e é registrado
  aqui como limite declarado.
- **Consequência de honestidade:** a claim de tamper-evidence do
  `CLAUDE.md` §1 **não vale entre projetos do mesmo `$HOME` — nem antes
  nem depois desta migração**. A W1 atualiza esse texto no mesmo lote,
  e o texto novo declara a limitação como PERMANENTE sob mesmo UID, não
  como pendência que a migração resolve.

## RESIDUAL DO r9 — CURADO em S316 (registro histórico)

A 9a rodada do pair-rail devolveu **REJECT** com 3 achados contra ESTE
plano. **Curados em S316 (2026-08-20), ANTES de qualquer execução**, com
as emendas apontadas item a item. A rodada r10 confirmou 182-1 e 182-2
CLOSED e devolveu REJECT parcial: 182-3 sem unidade executável na W2, e
dois achados novos (carve-out da W0 contradizendo o US3; "confirmação
por r10" registrada antes do veredito) — todos curados na mesma sessão.
r11 confirmou 3/4 e apontou sobra textual na nota histórica (N1);
**r12 = GO (2026-08-20)** — cadeia r9→r12 fechada. Registro histórico.

1. **[P1] `derive-audit-family.py` NAO EXISTE.** A W0 e declarada
   read-only e a AC-1 exige que esse comando torne o censo reproduzivel.
   Um executor teria de criar ferramenta rastreada (violando o contrato
   da wave) ou usar script temporario (que nao satisfaz a AC-1).
   **Cura:** permitir explicitamente que a W0 crie a instrumentacao, ou
   adicionar passo de setup de ferramenta antes dela.
   **→ CURADO (S316):** o cabeçalho da W0 ganhou carve-out explícito de
   escrita — a W0 PODE criar `derive-audit-family.py` + testes como
   passo de setup E anexar registros/saídas brutas ao próprio plano
   (exigência do US3); nada além dessas duas classes.
2. **[P1] O carry-over do salt PRESERVA o defeito.** Dois projetos que
   hoje compartilham o `.salt` legado, ao receberem esse mesmo valor nos
   dois diretorios novos, ficam com salts **byte-identicos** — mantendo
   exatamente a correlacao cross-project que o §2 denuncia. O check
   atual so exige chaves HMAC distintas, entao **passaria violando o
   ADR-079** (`ADR-079:186-202`, distincao cross-installation).
   **Cura:** politica explicita de salt POR PROJETO + teste de
   distincao de hash entre dois projetos — ou emenda ao ADR-079
   abandonando a propriedade.
   **→ CURADO (S316):** o item de salt da W1 agora fixa política POR
   PROJETO com teste de DISTINÇÃO entre dois projetos (controle
   negativo: salts byte-idênticos = vermelho); o projeto que herda a
   cadeia histórica (decisão W2) herda o salt legado, os demais cunham
   salt novo com rotação REGISTRADA — condicionado à emenda do ADR-079
   (OQ-4) que o frontmatter já bloqueia antes da W1.
3. **[P2] "Janela historica fechada" e classificacao errada.** Foram
   **149 eventos nao-atribuiveis novos** entre dois snapshots: taxa
   reduzida, nao fluxo encerrado. Tratar como arquivo faz a W2 ignorar
   emissores que ainda omitem atribuicao. **Cura:** condicionar a
   classificacao a observar ZERO novos, ou descrever como vazamento de
   taxa reduzida.
   **→ CURADO (S316):** §1 reclassificado como vazamento de taxa
   reduzida; "janela fechada" agora exige ZERO novos entre snapshots, e
   a W2 inclui identificar os emissores remanescentes.

## Waves

> **W1-W3 abaixo são ESBOÇO NÃO-NORMATIVO.** Foram escritas antes da W0
> para registrar direção, não para executar como estão. Cada uma é
> REEMITIDA a partir da tabela da W0, e a reemissão substitui
> integralmente o texto atual (AC-6). Dado o tamanho do delta produzido
> pelo round 1, **a reemissão da W1 passa por sua própria rodada de
> crítica**.

### W0 — Levantamento (read-only quanto ao runtime state e à família; nenhuma outra wave EXECUTA antes desta fechar — AC-6)

> **Carve-out de escrita da W0 (cura do r9 #1, redação do r10):** a W0
> PODE escrever exatamente duas coisas: (a) a ferramenta rastreada
> `derive-audit-family.py` (+ seus testes) como passo de setup, e
> (b) os registros de execução e anexos de saída bruta NO PRÓPRIO
> plano — que o US3 exige. Runtime state, módulos da família e qualquer
> outra superfície seguem intocados. Sem o carve-out (a), a AC-1 seria
> insatisfazível por construção; sem o (b), o US3 contradiria a wave.

- [x] `[P0][US1]` (fechado S316 — `derive-audit-family.py` + anexo `PLAN-182/w0-censo-familia-S316.md`: família = 587, na cura = 562, 102 runtime constroem o literal; `--assert-migrated` VERMELHO por design) Derivar a família COMPORTAMENTALMENTE com predicado
      executável e regra de allowlist explícita. A família inclui
      escritores, leitores, **templates, installer, CI, SPEC e testes** —
      não apenas módulos de runtime.
      Check: derive-audit-family.py --json lista modulo/artefato/papel; grep pelo literal NAO e oraculo, porque SPEC, docs e testes legados o mantem legitimamente
- [x] `[P0][US2]` **(FECHADO S317 — extensão entregue e assertada):**
      `derive-audit-family.py --matrix` passou de 3 resolvedores × 5
      colunas para **19 anchors de artefato × 14 colunas de env = 266
      células, zero degradadas**, numa única subprocess por coluna com
      HOME isolado (a forma ingênua custaria 19× mais processos; medido:
      2,7 s para a matriz inteira). O `--env-domain` novo publica a
      bounding rule.
      Check: pytest da matriz artefato x env; cada celula asserta o caminho resolvido de cada modulo
      **Dois números do enunciado não sobreviveram à medição, e ambos
      ficam corrigidos aqui:**
      - **"11+ células" → 19 anchors.** A lista da US5 é colapsada por
        DONO: as 19 rotações de `audit-log-*.jsonl` têm um único dono, e
        a matriz prova QUEM decide o caminho, não quantos arquivos o
        padrão gerou. `filelock` e `scratchpad_lib` ficam de fora **por
        declaração** (`ANCHORLESS_MODULES`) — o primeiro recebe o path
        pronto do chamador, o segundo resolve por sessão; anchor
        inventado para eles seria célula verde sem sujeito.
      - **"as 33 vars de `env-inventory.json`" → 21, derivadas do
        CÓDIGO.** Nem 33 nem as **500** que o inventário de fato lista:
        o domínio é o conjunto que os 8 módulos da família LEEM,
        derivado por `--env-domain` (que falha o pytest se alguém o
        trocar por um número de memória). **Achado colateral: `HOME`,
        `USER` e `PYTEST_CURRENT_TEST` estão no domínio e AUSENTES do
        `env-inventory.json`** — o inventário não cobre a própria
        família. Das 21, seis são flags de COMPORTAMENTO
        (`BEHAVIOR_ONLY_ENVS`) e ficam fora da matriz de caminho por
        classificação auditável, não por omissão.
      **E a claim a registrar estava com o dedo na coluna errada.** O
      enunciado mandava registrar que "sob `PATH`-only o lock e o errors
      não acompanham o log". Medido: sob `PATH`-only (coluna `sem-env`)
      os três são **co-locados** — não há divergência ali. Quem PARTE a
      família é **`CEO_AUDIT_LOG_PATH`**: move o log e deixa para trás o
      `audit-log.lock` e o `audit-log.errors`. Consequência de tenancy:
      dois projetos com logs distintos ainda **serializam no mesmo lock**
      e despejam breadcrumb no **mesmo arquivo de errors**. O botão
      COERENTE é `CEO_AUDIT_LOG_DIR`, que move os 12 juntos.
      **Correção de uma afirmação que esta seção chegou a carregar (S317,
      pega pelo CI):** a `audit-key` **acompanha** o log — ela NÃO fica
      para trás. A redação anterior dizia o contrário e concluía que dois
      projetos poderiam escrever sob a MESMA chave HMAC; era artefato do
      symlink `/tmp` → `/private/tmp` do macOS lido por comparação de
      **prefixo de string**, e o Linux do CI reprovou. As asserções agora
      normalizam com `realpath` dos dois lados — sem isso o teste media o
      formato do caminho, não o destino. Assertado nos dois sentidos
      (`test_log_path_leaves_lock_and_errors_behind` carrega o controle
      negativo do `sem-env` co-locado e a asserção positiva de que a chave
      acompanha), e ambas passaram por **controle positivo**: plant de
      anchor quebrado e plant que apaga a divergência deixam o pytest
      vermelho.
- [x] `[P0][US3]` (medido S316 — anexo `PLAN-182/w0-medicao-S316.md`) Medir o estado do log histórico com **os dois**
      instrumentos — `audit-verify-chain.py` para a pergunta de cadeia e
      `check-audit-hmac-null.py` — porque **o delta entre eles é a
      resposta**. Anexar a saída bruta.
      Check: as duas saidas brutas anexadas ao plano, com o delta explicado por escrito
- [x] `[P0][US5]` (medido S316 — anexo `PLAN-182/w0-medicao-S316.md`; 46 entradas de topo) Inventário do **diretório** por artefato: dono,
      semântica de compartilhamento e **modo de arquivo**. Hoje há 45
      entradas de topo, `state/` com 129.661 arquivos, e modos 0644/0600
      misturados.
      Check: tabela artefato/dono/compartilhamento/modo cobrindo as 45 entradas de topo
- [x] `[P0][US6]` (medido S316 — anexo; veredito de junção: PARCIAL, 46,6% sem rota) Atribuibilidade: histograma de `project`, presença de
      `session_id`, e **veredito explícito sobre existir chave de
      junção** — hoje medida como inexistente.
      Check: veredito escrito "existe chave de juncao: sim/nao", com o comando que o produz
- [x] `[P0][US7]` (medido S316 — anexo; veredito por família registrado) Reconciliar os resolvedores **já shipados**: as quatro
      implementações divergentes mais a convenção repo-local
      (`<repo>/.claude/state/audit-log.jsonl`, escrita por
      `_lib/federation/handlers/audit_event_push.py:234` e lida como
      primeiro candidato por `check_skill_bootstrap_post.py:129-131`).
      Dizer qual vence e o que cada uma já possui.
      Check: tabela dos 4+1 resolvedores com veredito de qual vence; sem isso a W1 entrega uma TERCEIRA convencao
- [x] `[P1][US4]` (fechado S316 — `--surfaces` no anexo 2: templates 34, settings.base.json, dist/ceo-plugin/hooks 167 — e o censo achou 92 membros da família em dist/) Inventariar superfícies de entrega: adopters
      instalados, `templates/`, `install.sh`, `upgrade.sh`,
      `settings.base.json`, `dist/ceo-plugin/hooks/`.
      Check: none (levantamento — a saida e a lista de superficies)

### Registro de execução — W0 medição por fan-out (S316, 2026-08-20)

Unidades US3/US5/US6/US7 executadas por fan-out read-only
(`wf_87d4181b-bba`, 4 agentes; saída bruta anexada em
`PLAN-182/w0-medicao-S316.md`). Manchetes que reemitem a W1:

- **US3 (o delta entre os dois instrumentos É a resposta):** hmac-null
  = verde nos 20 arquivos (0 defeitos-de-nascença em 293.720 linhas);
  verify-chain = 17/19 rotacionados REPROVAM. Censo completo (mesma
  `_lib`): **45.783 elos quebrados (15,6%)**, 99,8% em eventos
  spool-drenados `policy_*` com `project:""`. Sondas de re-link TODAS
  negativas ⇒ assinatura de **FORK por escritores concorrentes
  multi-tenant**, não de adulteração pós-hoc (que produziria 1 quebra
  isolada com sucessor íntegro). Só 2 arquivos (dias mono-escritor) e o
  log vivo pós-rotação verificam ponta a ponta. **A cadeia histórica é
  irrecuperável por-tenant — a decisão da W2 (arquivar e recomeçar)
  fica corroborada pela medição.**
- **US6:** junção = **PARCIAL** — 53,4% juntam a projeto; **46,6%
  (136.877 eventos) sem NENHUMA rota**. Janela S315 reconstruída EXATA
  (prefixo [0:15355] de `audit-log-2026-08-17.jsonl`). Delta pós-S315:
  +1.530 eventos, **226 não-atribuíveis (~14,8% do fluxo novo)** — a
  taxa do vazamento é MAIOR que os ~6% estimados no §1; a unidade de
  emissores remanescentes da W2 é obrigatória, não opcional.
- **US5:** 46 entradas de topo mapeadas a dono lógico; TODAS as
  famílias caem no literal (semântica real = por-`$HOME`); modos
  INCONSISTENTES (5 logs rotacionados 0644; `cache/` e
  `tool-lifecycle/` 0755); `speculative-ledger.json` ÓRFÃO (zero
  escritores vivos); **DOIS locks de convenções distintas coexistem**
  (`audit-log.lock` via audit_emit vs `audit-log.jsonl.lock` via
  filelock) — o F12 confirmado; `state/` = 133.124 arquivos.
- **US7:** 4 famílias + repo-local, com veredito por consumidor:
  auditoria ⇒ literal vence e readers DELEGAM ao resolvedor do writer
  (precedente PLAN-105); memória/transcripts ⇒ slug nativo do harness;
  CLIs ⇒ colapsar as 6 cópias da cadeia 4-step em delegação.
  `state_store._state_root()` é o único resolvedor parametrizado — o
  candidato natural da W1. **BUG VIVO novo achado:**
  `check_anti_ceo_overhead.py:213` escreve HOJE num dir slug de
  duplo-traço (`--Users-…`) — terceira grafia da família slug; entra na
  família derivada da US1 e na cura da W1.

**Atualização S316 (mesma sessão):** US1 e US4 FECHADOS —
`derive-audit-family.py` landada (+ 6 testes verdes) com censo
comportamental: **família = 587 arquivos** (562 na cura; 102 módulos
runtime constroem o literal — o número "63" do achado original media só
hooks+scripts com literal; a família REAL inclui dist/ com 92 membros).
US2 **FECHADA (S317)**: matriz de 19 anchors × 14 colunas (266 células,
zero degradadas) + bounding rule derivada do código (domínio = 21 vars,
não 33 nem 500). O achado que a extensão produziu:
`CEO_AUDIT_LOG_PATH` separa o log do lock, do errors e da `audit-key` —
tenancy partida na chave que sustenta o ADR-079. **A W0 está completa.**
A reemissão da W1 consome o censo + a matriz + os vereditos do anexo 1;
a W1 segue bloqueada pela emenda ao ADR-001 (AC-7) e pela OQ-4 do
ADR-079, que são decisão do Owner.

### W1 — Resolvedor único (REEMITIDA a partir da W0; EXECUTADA em S319)

> **Reemissão registrada (AC-6, S321).** O texto abaixo deixou de ser
> esboço: os itens são os que a W0 fechou e a S319 executou, e os
> checkboxes estão marcados contra o `### Registro de execução` logo
> após esta lista — que é a evidência, item a item. A ambiguidade que o
> AC-6 deixava em aberto ("o pair-rail conta como rodada própria de
> crítica?") fica RESOLVIDA aqui, e a resposta é **não**: o rail revisa
> TEXTO, o debate revisa MODELO ([[feedback-debate-revises-model-rail-revises-text]]).
> A rodada de crítica da W1 reemitida foi entregue na **S321**, por
> fan-out read-only de 4 lanes com verificação comportamental — e ela
> achou o que 27 rodadas de rail não tinham achado (o falso-verde do
> `--assert-migrated`, §W2/W3 abaixo).


- [x] `[P0]` Resolvedor derivado do projeto real, **conforme o ADR-001
      como escrito** (`<project-slug>`), importado por toda a família.
      Check: pytest — mesma entrada produz o mesmo caminho em todos os modulos da familia derivada na W0
- [x] `[P0]` **Política de salt POR PROJETO (cura do r9 #2 — carry-over
      universal manteria salts byte-idênticos nos dois diretórios novos,
      preservando exatamente a correlação cross-project que o §2
      denuncia):** o projeto que herda a cadeia histórica (decisão da
      W2) herda o `.salt` legado byte-a-byte; todo OUTRO projeto cunha
      salt NOVO, com marcador de migração na cadeia e rotação
      REGISTRADA — nunca silenciosa (§2.2). Condicionado à emenda do
      ADR-079 (OQ-4), que o frontmatter já bloqueia antes da W1.
      Check: teste de distincao com fixture de dois projetos — salts distintos e prompt_sha256 nao correlacionavel entre eles; controle negativo: salts byte-identicos = vermelho; o projeto herdeiro preserva o valor legado byte-a-byte
- [x] `[P0]` Chave de cache do `spool_writer` passa a cobrir o novo
      input, e `_state_dir()` ganha override; senão o vazamento
      cross-projeto **sobrevive à cura**.
      Check: teste com processo que troca de projeto no meio; o dir retornado acompanha, sem servir cache do anterior
- [x] `[P0]` Teste de paridade com fixture de **dois**
      `CLAUDE_PROJECT_DIR`, produzindo dois diretórios e **duas chaves
      HMAC distintas**, com controle negativo.
      Check: remover o resolvedor deixa o teste VERMELHO; grep pelo literal nao e aceito como oraculo
- [x] `[P0]` Modos: dir `0700`, chave `0600`, sidecars `0600`.
      Check: verify_chain pos-migracao como gate, com controle positivo — chave 0644 produz perm_error
- [x] `[P0]` Atualizar o `CLAUDE.md` §5 **no mesmo lote**, declarando a
      limitação como **PERMANENTE sob mesmo UID** — antes E depois da
      migração (§4). A redação anterior dizia "enquanto a família não
      migrar", o que tornaria a ressalva falsa ou vazia no dia seguinte
      ao land (pair-rail r8).
      Check: o texto da claim declara a limitacao como permanente sob mesmo UID, sem condicionar a migracao; verificado por leitura no mesmo commit
- [x] `[P1]` Escritores e leitores migram no MESMO lote (ver §3).
      Check: derive-audit-family.py --assert-migrated sai 0

### Registro de execução — W1 EXECUTADA (S319, 2026-08-21, sentinel SENT-S319)

Reemitida e executada após a W0 fechar, com as duas emendas landadas em
`32e29b1`. Entregue no pack `PLAN-182/staged-w1/` (105 arquivos,
`MANIFEST.sha256`; commits de prep `796f809` → `71ef682`):

- **Resolvedor único** `_lib/runtime_paths.py` — slug nativo path-based
  (`/`→`-`, grafia ATUAL do harness), `CLAUDE_PROJECT_DIR_NATIVE` com seu
  primeiro consumidor, `legacy_state_dir()` como único handle sancionado
  do literal, `ensure_state_dir()` central (mkdir + tighten 0700 que NÃO
  aperta dir escolhido por override e não segue symlink).
- **Família migrada:** 6 âncoras à mão + sweep mecânico + batch manual;
  **5 grafias divergentes colapsadas** (literal, basename-lowered de
  `memory_shared`, basename de `optimizer/fanout`, `lstrip+resolve` de
  `ceo-cost`, duplo-traço de `check_anti_ceo_overhead`).
  **`--assert-migrated`: 102 → 0.**
- **Family-atomicity:** lock/errors/key seguem o LOG EFETIVO (PATH-first
  unificado nos 4 resolvedores) — o split medido na W0-US2 está curado,
  com preservação da cadeia legada quando `LOG_DIR`/`LOG_PATH` divergem
  numa instalação existente (migração = cerimônia, nunca efeito de
  import).
- **Salt POR PROJETO** com mint OBSERVÁVEL: ação nova
  `salt_rotation_registered` registrada na família completa
  (`_KNOWN_ACTIONS` 326→327 + allowlist + branch de scrub + SPEC v2.58 +
  golden + 6 pins) e sidecar `salt-minted.json` como ground truth.
- **Caches keyed por path ABSOLUTO** (key e salt): a troca de projeto
  mid-process deixa de servir o cache do projeto anterior — inclusive com
  overrides relativos + `chdir`.
- **Aceitação:** `test_audit_family_two_projects.py` (paridade dois
  projetos com DUAS chaves HMAC + controle negativo comportamental; salts
  distintos + `prompt_sha256` não-correlacionável + herdeiro preserva
  bytes; spool switch mid-process; family-follows-log; ambos-overrides;
  mint observável) + `test_runtime_paths.py`. Suíte CI-equivalente
  **P1=0 / P2=0 / P3=0**.
- **Rail codex: 12 rodadas até RODADA LIMPA** (6→12→2→1→3→3→2→1→2→4→1→0),
  35 achados curados. Residual declarado: slug não-injetivo para paths
  que diferem só em traço-vs-barra — é a derivação NATIVA do harness
  (mesma colisão nos dirs de memória); divergir quebraria a co-locação
  ratificada no ADR-001 S318.
- **CLAUDE.md §5 curado no mesmo lote** (AC [P0]) e este frontmatter
  destravado.

**Fora do lote, com dono:** templates (`templates/scripts/statusline-ceo.py`,
`templates/{codex,grok}/pre-push-review-gate.sh`) → W3; unificação dos
DOIS locks (F12) e semântica do campo `project` (US6) → W2; `dist/` não é
rastreado (regenera das fontes).

### W2 — O log histórico (decisão, não implementação)

> **ORDEM CORRIGIDA pelo pair-rail r8:** esta decisão é **pré-requisito
> da W1 reemitida**, não sucessora dela. Redirecionar escritores na W1
> já obriga a escolher entre copiar o log/chave/salt misturados ou
> inicializar estado novo — que é exatamente a escolha "declarar a
> janela" contra "arquivar e recomeçar". Executar a W1 antes **tomaria a
> decisão P0 do Owner por omissão**, e poderia rotacionar o salt ou
> reiniciar a cadeia prematuramente.


> **⚠️ Este bloco é o ESBOÇO original da W2/W3, preservado como registro.
> A execução real está no `### Registro de execução — W2 e W3 (S321)`
> mais abaixo, e é ELE que carrega os checkboxes válidos.** Os itens
> daqui ficam marcados conforme o que o registro PROVOU, para que o
> documento não afirme duas coisas ao mesmo tempo — foi exatamente a
> ambiguidade que o AC-6 pegou na W1 (texto de esboço apenso a um
> registro de execução).

- [x] `[P0]` Decidir e REGISTRAR. **"Segregar" está indisponível para
      ~68% do log** (não atribuível, §1), então a escolha real é
      "declarar a janela" contra "arquivar e recomeçar a cadeia".
      Incluir decisão sobre o **salt** e emitir marcador de migração na
      cadeia.
      Check: none (decisao do Owner — o gate e a decisao REGISTRADA com justificativa; ausencia mantem o AC aberto)
      **DECISÃO DO OWNER REGISTRADA (S316, 2026-08-20, chat):**
      **ARQUIVAR E RECOMEÇAR A CADEIA.** O log/chave/salt atuais viram
      cópia forense read-only no dia do land da W1; cada projeto inicia
      cadeia NOVA com marcador de migração. Justificativa: a cadeia
      histórica nunca terá semântica por-projeto (68% não-atribuível +
      2 tenants estrangeiros sob a mesma chave), e "declarar a janela"
      preservaria continuidade de uma cadeia sem significado por
      tenant. Consistente com a política de salt POR PROJETO da W1
      (nenhum projeto é "herdeiro" da cadeia arquivada — todos cunham
      salt novo com rotação REGISTRADA; a cláusula de herdeiro do salt
      fica vazia por esta decisão). A unidade de emissores remanescentes
      (abaixo) permanece obrigatória. O checkbox fecha quando o arquivo
      + marcador forem EXECUTADOS na W1 reemitida.
- [x] `[P1]` **Emissores remanescentes (cura do r10 sobre o r9 #3):**
      derivar COMPORTAMENTALMENTE quais emissores ainda produzem
      eventos não-atribuíveis (os +149 do §1) e dispor CADA um — curar a
      atribuição ou registrar aceite por escrito. "Janela fechada" só
      pode ser declarada depois desta unidade.
      Check: dois snapshots consecutivos com ZERO nao-atribuiveis novos, OU tabela emissor→disposicao cobrindo 100% dos novos do intervalo medido; a decisao P0 da W2 cita esta evidencia
- [ ] `[P1]` Reavaliar `ceo-boot`, `audit-tokens` e `skill-health` como
      **eficácia de controle**, não como medição — e prever a rajada de
      advisories pós-migração.
      **ABERTO, e é o único item da W2 que sobra.** O "antes" existe; o
      "depois" precisa de uma janela — o vazamento da suíte parou na
      S321, então a re-medição só é significativa depois de alguns dias
      de fluxo normal. Parcial já entregue: o `sentinels_pending_gpg` do
      `ceo-boot` foi curado na mesma sessão (era cego a 9 dos 10
      formatos de sentinel).
      Check: vereditos antes e depois diffados; toda mudanca de cor explicada por escrito

### W3 — Instalação e adopters (esboço)

- [ ] `[P0]` Rota do installer: chave em `settings.base.json` e merge
      aditivo no `upgrade.sh`, usando o backup que já existe; curar
      `templates/{codex,grok}/pre-push-review-gate.sh`.
      **ABERTO por DECISÃO, não por trabalho.** A metade do e2e está
      provada em campo (S321): o upgrade real do `arbitrage-monitor`
      migrou o adopter, e ele passou a resolver para o próprio diretório
      com chave HMAC distinta — **sem chave nenhuma em
      `settings.base.json`**. Isso é evidência a favor de NÃO acrescentar
      a chave (ela viajaria hardcoded e é a var de MAIOR precedência).
      O que resta é a decisão do Owner + os dois templates de pre-push,
      que precisam de um resolvedor em SHELL.
      Check: e2e de upgrade sobre instalacao existente — migra ou declara aceite; falha se nenhum dos dois
- [ ] `[P1]` `ceo-backup.sh` / `ceo-restore.sh` e `dist/ceo-plugin/hooks/`.
      **ABERTO.** `dist/` foi resolvido na S321 (regenerado por
      `build-plugin.py`; o gate M4 fecha em 0). Os dois scripts seguem
      defaultando para `${CEO_PROJECT_NAME:-ceo-orchestration}` e são
      INVISÍVEIS ao censo — o regex M1 exige aspas colando no literal e a
      forma `${VAR:-literal}` escapa. Composto: backup lê o dir legado,
      restore escreve nele, então um restore nunca repovoa o dir vivo.
      Check: os dois scripts operam sobre o dir resolvido, nao sobre o literal
- [x] `[P1]` Dois adopters no mesmo `$HOME` sem env resolvem para
      caminhos e chaves distintos.
      Check: e2e com dois projetos; logs e chaves distintos

### Registro de execução — W2 e W3 (S321, 2026-08-22)

> **Método.** Fan-out read-only de 4 lanes (`wf_f2943bd9-c0a`), cada
> número derivado COMPORTAMENTALMENTE — parse do JSONL, execução do
> resolvedor em processo, controle positivo em árvore-sombra. Nenhum
> número desta seção veio de grep de texto nem do corpo do plano.
> Onde a medição contradiz o próprio plano, o plano está corrigido
> abaixo e o número antigo fica nomeado como não-reprodutível.

#### O que a W2 encontrou, e por que ela não fecha como estava escrita

**(a) O arquivamento aconteceu; o marcador de migração não.**
`~/.claude/projects/ceo-orchestration.pre-W1-archive` existe, modo
`dr-x------`, 47 entradas, 7.892 elos — criado pelo brace ARCHIVE de
`OWNER-S319-LAND.sh:211-217` no land da W1. Mas o censo de ações sobre
TODOS os segmentos da cadeia nova casando `migrat|archiv|reset|salt|
custod|legacy` devolve **2 hits apenas**: `salt_rotation_registered`
(o mint da W1) e `chain_reset_marker` — e este último **não é** o
marcador de migração: é o marcador de ROTAÇÃO do ADR-055-AMEND-2, com
`rotation_trigger=size_threshold` e `previous_archive_path` apontando
para o próprio segmento rotacionado do dir NOVO. `grep pre-W1-archive`
em toda a cadeia nova = **0 linhas**.

Consequência exata: **um verificador que leia só a cadeia nova não tem
como saber que existiu cadeia anterior arquivada.** O elo de custódia
entre `new-chain` e `archive` não está escrito em lugar nenhum que o
`verify_chain()` alcance.

**(b) A W1 não curou a atribuição — e a taxa PIOROU.** Corte no land
(`832891e`, 2026-08-21T14:21:10Z) sobre 20.582 linhas: 4.254
não-atribuíveis PRÉ-land contra **15.208 PÓS-land**. O log agregado
está em **94,6% não-atribuível**, contra os ~68% que o §1 deste plano
afirma. A W1 curou ONDE o evento é gravado (diretório por projeto);
nunca curou O QUE ele carrega (o campo `project`).

**(c) 99,5% desse fluxo era VAZAMENTO DA SUÍTE, não telemetria.**
Assinatura por processo: 156 pids emitindo EXATAMENTE 124 eventos cada
(19.344 no total), todos com `session_id` vazio, todos no mesmo segundo
por pid. A identidade aritmética que fecha o emissor:
`82 fixtures (46 bash-safety + 36 plan-edit) + 42 expected_decision
"block" = 124`, campo a campo. O arquivo é
`.claude/hooks/tests/test_migrated_hooks_fixtures.py`, que tinha ZERO
construto de isolamento — cada rodada da suíte injetava 124 elos
ASSINADOS e não-atribuíveis na cadeia HMAC viva.

**CURADO nesta sessão** (as três classes herdam `TestEnvContext`, e o
`load()` saiu de `setUpClass` para `setUp` de propósito: o isolamento é
por INSTÂNCIA, então o que ficasse em `setUpClass` rodaria antes do
sandbox existir). Controle positivo em árvore-sombra, com HOME
redirecionado: **antes** ⇒ o canário recebe
`state/audit-pending.<pid>.journal` com os eventos; **depois** ⇒ o
journal some. O resíduo de 5 entradas (`audit-log.lock` + `state/`
vazio) é **idêntico ao baseline de um teste com um único `assert
True`** — é da infraestrutura de import, já declarado, e não deste
arquivo.

**(d) Tabela emissor → disposição (o entregável P1), 100% dos novos.**
Corte pós-land, 15.208 eventos, 11 ações, sem bucket residual:

| ação | eventos | causa medida | disposição |
|---|---|---|---|
| `policy_evaluated` | 10.004 | vazamento de suíte (c) | **CURADO** (isolamento) |
| `policy_denied` | 5.124 | vazamento de suíte (c) | **CURADO** (isolamento) |
| `statusline_sidecar_write` | 41 | chamador omite `project=`; `emit_generic` não injeta; scrub INOCENTE (`project` está em `_FEDERATION_ENVELOPE`) | **CURADO** (`statusline-ceo.py`) |
| `notification_lifecycle` | 16 | `check_notification.py:115` omite `project=` | CERIMÔNIA (path canônico) |
| `codex_review_verdict` | 11 | idem classe | CERIMÔNIA |
| `ceo_boot_persona_coverage_score` | 4 | idem classe | CERIMÔNIA |
| `config_change_observed` | 2 | idem classe | CERIMÔNIA |
| `ceo_boot_emitted` | 2 | idem classe | CERIMÔNIA |
| `ceo_boot_task_candidate_emitted` | 2 | idem classe | CERIMÔNIA |
| `veto_triggered` | 1 | idem classe | CERIMÔNIA |
| `chain_reset_marker` | 1 | `project` HARDCODED vazio em `audit_emit.py:2537-2550` — o marcador é por-ARQUIVO e ancora em GENESIS_PREV, não pertence a sessão nenhuma | **ACEITE ESCRITO**: o arquivo já é por-projeto pós-W1; atribuir o marcador seria redundante |

A causa é UMA e sempre a mesma: **o chamador omite o kwarg e o default
do emissor é a string vazia.** A hipótese "o scrub remove `project`" foi
testada e é FALSA (`'project' in _STATUSLINE_SIDECAR_WRITE_ALLOWLIST`
⇒ True).

**(e) A janela NÃO fechou, e o critério de ZERO é inalcançável por
construção.** Dois snapshots consecutivos separados por ~5 min:
15.206 → 15.208 (+2 novos), com o último não-atribuível emitido pela
PRÓPRIA sessão que rodava a medição. O AC fecha pela OUTRA via que ele
mesmo oferece — a tabela emissor→disposição cobrindo 100% dos novos,
entregue em (d) — nunca pelo critério de ZERO.

**(f) O diretório literal legado está VIVO e recebendo escrita.**
`~/.claude/projects/ceo-orchestration/` tem 3.010 linhas, última
escrita durante a própria medição. Censo do campo `project` lá dentro:
**2.967 eventos de `/Users/<owner>/canhada-labs/arbitrage-monitor`** —
um ADOPTER rodando cópia PRÉ-W1 (`ls .../arbitrage-monitor/.claude/
hooks/_lib/runtime_paths.py` ⇒ não existe). Isto reordena a W2: **a
cadeia que a decisão de custódia ia arquivar não é o histórico deste
projeto** — é um fork multi-tenant ainda em CRESCIMENTO, alimentado por
um terceiro repositório. A decisão ARCHIVE registrada em S316 continua
válida para o corpus pré-W1; o que ela não previa é que o dir seguiria
recebendo escrita de fora. **Isso é da W3 (rota de upgrade do adopter),
não da W2.**

- [x] `[P0]` Decidir e REGISTRAR a custódia — ARCHIVE, executado em S319 (evidência acima, item (a)).
      Check: o dir `<literal>.pre-W1-archive` existe com modo dr-x------ e a decisao esta no sentinel assinado lido fail-closed pelo land script
- [ ] `[P0]` **REABERTO como item próprio:** emitir o elo de custódia `new-chain ↔ archive`, ou registrar por escrito que `salt_rotation_registered` basta. Hoje nenhum dos dois existe (item (a)).
      Check: um evento na cadeia nova cujo payload cite o caminho do archive e o ultimo hmac dele, OU uma linha de aceite escrita aqui com a razao
- [x] `[P1]` Emissores remanescentes derivados COMPORTAMENTALMENTE e dispostos um a um — tabela em (d), cobertura 11/11 ações, soma conferida contra a contagem independente (15.208 = 15.208).
      Check: tabela emissor->disposicao cobrindo 100% dos nao-atribuiveis novos, com a soma conferida contra a contagem independente do mesmo corte
- [ ] `[P1]` Reavaliar `ceo-boot`, `audit-tokens` e `skill-health` como eficácia de controle — pendente; a rajada pós-cura ainda não foi medida (o vazamento parou nesta sessão, então o "depois" precisa de uma janela).
      Check: vereditos antes e depois diffados; toda mudanca de cor explicada por escrito

#### O que a W3 encontrou: o gate da W1 é VERDE pela pergunta errada

O `--assert-migrated` responde "0 módulos runtime constroem o LITERAL" —
e isso é verdade. Mas o contrato que `runtime_paths` declara tem uma
segunda metade que **nenhum instrumento media**: nenhum arquivo pode
re-derivar o slug localmente. Medido: **16 módulos runtime** o faziam,
em 4 grafias, produzindo diretórios DIVERGENTES para o mesmo projeto:

```
project_dir            resolvedor único          .lstrip('-')            .resolve()+slug
/tmp/adopter-one       -tmp-adopter-one          tmp-adopter-one         -private-tmp-adopter-one
```

Três diretórios para um projeto. Para 3 projetos as grafias geram
**7 diretórios distintos onde deveria haver 3**. É a classe
*instrumento verde cuja pergunta envelheceu*, dentro do próprio
instrumento que a W1 usou como prova.

**CURADO nesta sessão:**
1. `derive-audit-family.py` ganhou o marcador **M4** (re-derivação local
   do slug, com contexto de estado) e o modo `--assert-no-local-slug`.
   O M4 fica **FORA** do offender-set do `--assert-migrated` de
   propósito: as duas perguntas são diferentes e a resposta de uma não
   pode mascarar a outra. O modo novo é ADVISORY, com enforcement por
   `CEO_AUDIT_FAMILY_M4_REQUIRED=1` (molde do
   `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED`) — o flip é decisão do Owner.
   O `--assert-migrated` passou a IMPRIMIR seu próprio escopo.
2. `tests/` entrou em `SCAN_ROOTS` — a raiz estava fora do censo, que é
   como a regressão da S320 passou. Isso muda o CONJUNTO reportado
   (580 → 603 arquivos), não o veredito do gate (`test` continua fora
   do offender-set).
3. **9 call sites não-canônicos delegados ao resolvedor**:
   `audit-log-retain.py`, `audit-telemetry.py`, `ceo-diagnose.py`,
   `token-estimator.py`, `budget-summary.py`, `ceo-boot.py`,
   `ceo-info.py` (3 sites), `memory-prioritize.py`, `lesson_evolve.py`.
   Sete deles JÁ IMPORTAVAM `runtime_paths` e mesmo assim re-derivavam
   — migração meio-feita que passava em todos os gates.
   **M4: 16 → 7.** Os 7 restantes são os 4 canônicos + seus 3 espelhos
   em `dist/` (que regeneram das fontes) — exatamente o lote da
   cerimônia.
4. **Migração de dados: não é necessária, e isso foi MEDIDO** — as
   grafias A e B coincidem com o canônico neste repositório (divergem
   só sob symlink, ex. `/tmp` no macOS), e o diretório da grafia C
   (`lessons`, sem o traço inicial) **não existe**.

**Três controles negativos VÁCUOS, curados:**
`tests/integration/test_full_session.py`, e dois em
`.claude/scripts/tests/test_hook_profiler.py`, todos asserindo contra
`~/.claude/projects/ceo-orchestration/audit-log.jsonl` — um caminho que
pós-W1 **nada neste repo escreve**. "O log real não cresceu" era
verdade independentemente do que vazasse. Agora resolvem pelo slug e
apontam para o log VIVO (verificado: mesmo arquivo).

**Portabilidade de adopter:** `test_env_persist_allowlist.py` decidia a
raiz do repo por `if "ceo-orchestration" in parts` — falso em todo
checkout de adopter, onde o fallback degradava em silêncio para
`parents[5]`. Agora ancora no layout do framework
(`.claude/hooks/_lib`), não no nome do diretório.

- [ ] `[P0]` Rota do installer: chave em `settings.base.json` e merge aditivo no `upgrade.sh`; curar `templates/{codex,grok}/pre-push-review-gate.sh`.
      **Evidência da W3 que muda o item:** `install.sh`/`upgrade.sh` NÃO tocam estado (censo por grep de path de estado = 0 hits), e sem env nenhuma o resolvedor JÁ separa dois adopters (provado com HOME fake e dois `CLAUDE_PROJECT_DIR`). Uma chave `CLAUDE_PROJECT_DIR_NATIVE` literal em `settings.base.json` viajaria HARDCODED para o adopter e é a var de MAIOR precedência — pinar errado quebraria a isolação que a W1 comprou. **Recomendação do CEO: NÃO acrescentar chave; o veículo pronto, se a decisão for outra, é `_T54_BASELINES_JSON` em `upgrade.sh:153-188`, nunca o merge de hooks.** Decisão do Owner.
      Check: e2e de upgrade sobre instalacao existente — migra ou declara aceite; falha se nenhum dos dois
- [x] `[P0]` **RESOLVIDO (S321, 2026-08-23T00:15Z):** o adopter `arbitrage-monitor` rodava cópia PRÉ-W1 e escrevia no literal. **Upgrade executado**, com as quatro pernas medidas (ver AC-5): resolvedor presente, dir próprio, chave HMAC distinta, e o literal com delta **0** entre dois snapshots sob controle positivo — um `emit` real no contexto do adopter aterrissou no diretório NOVO dele, não no literal. A mistura acidental sob o mesmo `$HOME` acabou de fato, não por declaração.
      Check: upgrade do adopter para uma versao com runtime_paths, OU aceite escrito de que o literal permanece como estado legitimo dele
- [ ] `[P1]` `ceo-backup.sh` / `ceo-restore.sh`: os dois ainda defaultam para `${CEO_PROJECT_NAME:-ceo-orchestration}` e são **INVISÍVEIS ao censo** — rodar o `_m1_hit()` do próprio derivador nos dois devolve `False`, porque o regex M1 exige aspas colando no literal e a forma `${VAR:-literal}` escapa. A exclusão é acidente de regex, não allowlist. Composto: backup lê o dir legado, restore escreve nele — um restore **nunca repopula o dir vivo**.
      Check: os dois scripts operam sobre o dir resolvido, nao sobre o literal; round-trip backup->restore->verify_chain no dir VIVO
- [ ] `[P1]` **Templates com dono declarado:** `templates/grok/pre-push-review-gate.sh:144` é ENTREGUE ao adopter (`_grok_harness.sh:227`, a doc o chama de "the teeth") e constrói o literal; o gêmeo `templates/codex/pre-push-review-gate.sh:90` é ÓRFÃO (não aparece em `_codex_planned_pairs()`). `templates/scripts/statusline-ceo.py` é duplicata órfã — zero rota de entrega, zero teste; o adopter recebe a cópia VIVA já migrada. Curar exige um resolvedor em SHELL, que `runtime_paths.py` não expõe (não tem `__main__`). Decisão do Owner: expor CLI no módulo, ou aceitar.
      **DECIDIDO — Owner, 2026-08-22 (S322), via AskUserQuestion, texto verbatim da opção escolhida:** "Expor CLI no runtime_paths.py (Recomendado) — Adiciono `__main__` ao módulo, os templates passam a chamar o resolvedor único em vez de reconstruir o literal. Fecha o item e mata a classe na raiz — o adopter deixa de receber o defeito. É a cura, não o contorno."
      Check: nenhum template entregue constroi o literal; orfaos deletados ou sincronizados com teste de paridade
- [x] `[P1]` Dois adopters no mesmo `$HOME` sem env resolvem para caminhos e chaves distintos — **provado em processo** com HOME isolado; inclusive dois projetos de mesmo BASENAME em pais diferentes (a classe que a W1 curou). Residual conhecido reproduzido: `/srv/a-b/c` e `/srv/a/b-c` colidem em `-srv-a-b-c`, que é a derivação NATIVA do harness.
      Check: dois CLAUDE_PROJECT_DIR distintos sob HOME isolado resolvem dirs e chaves HMAC distintos; mesmo-basename em pais diferentes NAO colide
- [ ] `[P1]` **NOVO:** e2e de dois adopters via `install.sh` real não existe (`smoke-install.sh` instala UM alvo e não toca `HOME`). O único oráculo de dois projetos é in-process. Candidato a nightly, não a per-PR (custo: install real ×2).
      Check: HOME isolado, install.sh em dois alvos, hook disparado em cada, dois dirs + duas chaves + verify_chain verde em cada


## Acceptance criteria

> Estado verificado por execução na S321 — cada linha traz o comando que
> a fecha ou o que falta. Um AC marcado sem comando é a classe que este
> repo caça.

- [x] AC-1 [P0] A família é derivada comportamentalmente e a derivação é
      REPRODUZÍVEL por comando — não por prosa nem por grep.
      `derive-audit-family.py --assert-migrated` ⇒ EXIT 0; `--json` ⇒
      603 arquivos (o escopo cresceu na S321 com `tests/`; ver W3);
      `pytest .claude/scripts/tests/test_derive_audit_family.py` ⇒ 11 passed.
      **Emenda S321:** o AC agora exige que o instrumento DECLARE seu
      escopo — `--assert-migrated` imprime quantos módulos re-derivam o
      slug localmente, e `--assert-no-local-slug` responde por essa
      metade do contrato.
- [x] AC-2 [P0] Teste de paridade com controle negativo demonstrado no
      mesmo commit, usando fixture de dois projetos.
      `pytest test_audit_family_two_projects.py test_runtime_paths.py`
      ⇒ 27 passed, com dois dirs + duas chaves HMAC, salts distintos,
      `prompt_sha256` não-correlacionável e herdeiro preservando bytes.
- [x] AC-3 [P0] Matriz de precedência por artefato, sobre a lista
      **fechada na US5** — não sobre os 5 artefatos da primeira redação.
      **Fechado na S321** por
      `.claude/scripts/tests/test_us5_family_coverage.py` (4 passed).
      A cobertura deixou de ser PROSA (um comentário dizendo "os anchors
      cobrem a US5" + um teste que só exigia `len(m) >= 11`) e passou a
      ser **resolução**: cada dono da US5 — incluindo os três que
      faltavam, `advisory_dampen._state_base_dir`,
      `tool_lifecycle._audit_dir` e
      `check_bash_safety._fact_gate_state_dir` — resolve num subprocess
      com `HOME` e `CLAUDE_PROJECT_DIR` sintéticos, e o teste assere que
      o caminho cai sob `runtime_state_dir()`. Os anchorless carregam
      razão por item (`filelock` recebe o path pronto; `scratchpad_lib`
      resolve por sessão; `speculative-ledger.json` é ÓRFÃO, item 45).
      **Controle positivo executado:** um dono plantado com a grafia
      local (`replace('/','-').lstrip('-')`) deixa o teste VERMELHO
      nomeando o plant; restaurado do backup do plant, volta a 4 passed.
      **Achado do próprio fixture:** sem limpar os carriers da suíte, os
      anchors de `audit_hmac` resolviam para o sandbox do conftest — a
      lista de limpeza é DERIVADA de `_lib.test_isolation.ALL_AUDIT_CARRIERS`,
      nunca recordada.
- [x] AC-4 [P0] Decisão sobre o log histórico registrada com
      justificativa — ARCHIVE, registrada em S316 e amarrada no sentinel
      assinado (`S319-approved.md`, lido fail-closed por
      `OWNER-S319-LAND.sh:67-74`). A EXECUÇÃO do arquivo está feita; o
      elo de custódia `new-chain ↔ archive` **não** — item próprio,
      reaberto na W2.
- [x] AC-5 [P1] Rota de adopter fechada ou explicitamente aceita.
      **FECHADO por EXECUÇÃO (S321, 2026-08-23T00:15Z).** O Owner
      autorizou assim que o `arbitrage-monitor` ficou ocioso; o upgrade
      real rodou com backup próprio (269 MB) antes do backup que o
      próprio `upgrade.sh` faz.

      **As quatro pernas do Check, medidas:**

      | perna | resultado |
      |---|---|
      | `runtime_paths.py` no adopter | **existe** (7.688 B) |
      | o adopter resolve para o próprio dir | `-Users-…-arbitrage-monitor`, não mais o literal |
      | chave HMAC própria | **DIFERENTE** da canônica (`cmp` ⇒ isolamento real) |
      | literal, dois snapshots consecutivos | 10.349 → 10.349 — **delta 0** |

      **Controle positivo, não observação passiva:** disparei um `emit`
      REAL no contexto do adopter. O literal **não cresceu** e o evento
      aterrissou no diretório novo dele. Melhor que esperar dois
      snapshots ociosos, porque prova que a escrita MUDOU DE DESTINO em
      vez de apenas ter parado.

      **Achado colateral que fecha o ciclo:** o evento do adopter saiu
      com `project=/Users/…/arbitrage-monitor` **preenchido** — a cura de
      atribuição do `statusline-ceo.py` feita nesta mesma sessão viajou
      no upgrade e funciona em campo. Os `config_change_observed` do
      mesmo lote ainda saem com `project` vazio: é exatamente a classe
      que fica no pacote de cerimônia pendente.

      **Nota de custódia:** as "customizações do adopter" que o dry-run
      avisou que seriam sobrescritas eram **apenas placeholder
      substituído** (`{{OWNER_NAME}}` → nome real) — 16 linhas de diff,
      zero personas próprias, medido antes de executar. `CLAUDE.md`,
      `MEMORY.md` e `agent-metrics.md` foram preservados pelo upgrade.

      Registro histórico da decisão: **ATUALIZAR O ADOPTER** — não aceite
      escrito. A rota fecha pelo upgrade real do
      `arbitrage-monitor` para uma versão com `runtime_paths`, não por
      uma linha declarando o literal como estado legítimo.
      Estado medido que torna isto urgente-mas-não-emergência: o dir
      literal recebe escrita ATIVA (2.967 dos 3.010 eventos de lá são do
      adopter), então a mistura sob o mesmo `$HOME` continua até o
      upgrade — mas ela não contamina a cadeia DESTE repositório, que
      resolve por projeto desde a W1.
      Check: `ls <adopter>/.claude/hooks/_lib/runtime_paths.py` existe E o dir literal para de receber escrita nova em dois snapshots consecutivos
- [x] AC-6 [P0] W1-W3 são esboço não-normativo e nenhuma EXECUTA antes
      de ser reemitida a partir da W0; a reemissão da W1 passa por sua
      própria rodada de crítica.
      **Fechado na S321:** a W1 foi reemitida no documento (cabeçalho +
      7 checkboxes contra o registro de execução), e a rodada própria de
      crítica foi entregue — 4 lanes read-only com verificação
      comportamental. A ambiguidade "o pair-rail conta como crítica?"
      está resolvida no texto da W1: **não conta** (rail revisa texto,
      debate revisa modelo).
- [x] AC-7 [P0] Emenda ao ADR-001 registrada ANTES de qualquer execução
      da W1 (com a decisão SPEC v1 contra v2).
      **FECHADO no land de `965fb13`:** o quarto quarto que faltava é o
      `## Amendment 2 (2026-08-22, S321)` do ADR-001 — "amend `SPEC/v1`
      IN PLACE; do NOT cut a `SPEC/v2`", com a razão (a localização já
      era um parâmetro; mudou o default, não o parâmetro) e a linha
      testável do que TERIA exigido um v2. Registro do estado anterior
      preservado abaixo.
      **3/4 (S321, antes do land).** A emenda existe (`ADR-001` §Amendment 2026-08-20,
      landada em `32e29b1`, ANTES da W1 em `832891e`) e cobre slug
      normativo, resolvedor único, family-atomicity e blast radius
      L2→L3. **Falta a peça que o próprio AC nomeia:** a decisão SPEC v1
      contra v2 foi TOMADA na prática (`SPEC/v1/*.md` editados in-place,
      sem `SPEC/v2`) e nunca REGISTRADA — `grep -i SPEC` no ADR-001
      devolve 2 hits, ambos irrelevantes. Vai no lote de cerimônia.

## Open questions

1. **W2** — declarar a janela ou arquivar e recomeçar a cadeia?
   ("segregar" está marcado indisponível para ~68% do log). Decisão do
   Owner; muda a semântica retroativa de `verify_chain()`.
2. **Namespace, não slug.** A pergunta não é `CLAUDE_PROJECT_DIR` contra
   `git rev-parse`: é **em que namespace o framework tem direito de
   escrever**, dado que `~/.claude/projects/` é do harness, tem 120
   entradas, e o slug "óbvio" aterrissa exatamente onde vive o
   `memory/` que o `CLAUDE.md` §0.3 manda carregar. Inclui normalização
   contra traversal e colisão.
3. **Esquemas de nome** — `CEO_PROJECT_NAME`, path-slug,
   basename-lowercase e a convenção repo-local: quais ficam, quais viram
   alias, quais saem.
4. **ADR-079** — "per-installation" significa `$HOME` ou projeto? As
   duas leituras exigem ações **opostas** sobre o salt.
5. **Ordem de execução** — installer-first, por-artefato, ou
   writers-atômico com leitores por candidate-list. Decidir **depois** da
   W0, não agora.
6. **Resolvedor em SHELL para os templates** — **FECHADA (Owner,
   2026-08-22, S322).** Decisão verbatim: *"Expor CLI no runtime_paths.py
   (Recomendado) — Adiciono `__main__` ao módulo, os templates passam a
   chamar o resolvedor único em vez de reconstruir o literal. Fecha o item
   e mata a classe na raiz — o adopter deixa de receber o defeito. É a
   cura, não o contorno."* Consequência: `.claude/hooks/_lib/runtime_paths.py`
   ganha um `__main__` com contrato de CLI próprio; `templates/grok/`
   e `templates/codex/pre-push-review-gate.sh` deixam de construir o
   literal; o censo M1 precisa passar a VER a forma `${VAR:-literal}`
   (hoje o regex exige aspas colando no literal, e por isso
   `ceo-backup.sh`/`ceo-restore.sh` escapam por acidente, não por
   allowlist).

## Reference links

- `.claude/adr/ADR-001-runtime-state-directory.md` — a decisão ACCEPTED
  que este plano implementa; ver a consequência `(-)` sobre
  `<project-slug>` implícito.
- `.claude/adr/ADR-079` — salt por instalação; ver OQ-4.
- `.claude/plans/PLAN-182/debate/round-1/consensus.md` — round 1,
  veredito PROCEED, 13 consensos.
- `.claude/plans/PLAN-169-closure-and-cross-session-evolution.md` —
  `### Registro de execução — W4 ABERTA`: a evidência original.
- `SPEC/v1/audit-log.schema.md`, `SPEC/v1/state-stores.schema.md`.
