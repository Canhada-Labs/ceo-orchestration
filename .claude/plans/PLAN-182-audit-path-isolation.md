---
id: PLAN-182
title: Isolamento de runtime state por projeto — implementar o ADR-001 como escrito, quatro meses depois
status: reviewed
reviewed_at: 2026-08-20
reviewed_by: "Owner — autorizacao explicita em chat (S315, 2026-08-20): 'se ja esta pronto deixa como revisado e apto pra fazer'. Debate L3 round 1 fechado com veredito PROCEED (13 consensos) e ajustes do consenso incorporados ao corpo; validate_governance_fast = 0 findings; pair-rail codex 6 rodadas fechadas, 32 achados, todos curados."
created: 2026-08-20
owner: CEO
depends_on: []
blocked_on_adr: "emenda ao ADR-001 (obrigatoria, AC-7) e decisao sobre ADR-079 (semantica de per-installation, OQ-4) — nenhuma execucao de W1 abre antes"
budget_tokens: 300-450k (W0 levantamento 110-170k; W1 resolvedor+cerimonia 110-160k; W2 decisao do log historico 40-70k; W3 installer+adopters 40-60k) — re-orcado no round 1 do debate, onde dois criticos convergiram independentemente em 250-500k contra os 120-260k da primeira redacao
budget_sessions: 4-6
context_risk: high
external_wait: "nenhum"
tags: [runtime-state, audit, hmac, salt, confidentiality, isolation, adopter, adr-001]
---

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

### W1 — Resolvedor único (esboço; reemitir após a W0)

- [ ] `[P0]` Resolvedor derivado do projeto real, **conforme o ADR-001
      como escrito** (`<project-slug>`), importado por toda a família.
      Check: pytest — mesma entrada produz o mesmo caminho em todos os modulos da familia derivada na W0
- [ ] `[P0]` **Política de salt POR PROJETO (cura do r9 #2 — carry-over
      universal manteria salts byte-idênticos nos dois diretórios novos,
      preservando exatamente a correlação cross-project que o §2
      denuncia):** o projeto que herda a cadeia histórica (decisão da
      W2) herda o `.salt` legado byte-a-byte; todo OUTRO projeto cunha
      salt NOVO, com marcador de migração na cadeia e rotação
      REGISTRADA — nunca silenciosa (§2.2). Condicionado à emenda do
      ADR-079 (OQ-4), que o frontmatter já bloqueia antes da W1.
      Check: teste de distincao com fixture de dois projetos — salts distintos e prompt_sha256 nao correlacionavel entre eles; controle negativo: salts byte-identicos = vermelho; o projeto herdeiro preserva o valor legado byte-a-byte
- [ ] `[P0]` Chave de cache do `spool_writer` passa a cobrir o novo
      input, e `_state_dir()` ganha override; senão o vazamento
      cross-projeto **sobrevive à cura**.
      Check: teste com processo que troca de projeto no meio; o dir retornado acompanha, sem servir cache do anterior
- [ ] `[P0]` Teste de paridade com fixture de **dois**
      `CLAUDE_PROJECT_DIR`, produzindo dois diretórios e **duas chaves
      HMAC distintas**, com controle negativo.
      Check: remover o resolvedor deixa o teste VERMELHO; grep pelo literal nao e aceito como oraculo
- [ ] `[P0]` Modos: dir `0700`, chave `0600`, sidecars `0600`.
      Check: verify_chain pos-migracao como gate, com controle positivo — chave 0644 produz perm_error
- [ ] `[P0]` Atualizar o `CLAUDE.md` §5 **no mesmo lote**, declarando a
      limitação como **PERMANENTE sob mesmo UID** — antes E depois da
      migração (§4). A redação anterior dizia "enquanto a família não
      migrar", o que tornaria a ressalva falsa ou vazia no dia seguinte
      ao land (pair-rail r8).
      Check: o texto da claim declara a limitacao como permanente sob mesmo UID, sem condicionar a migracao; verificado por leitura no mesmo commit
- [ ] `[P1]` Escritores e leitores migram no MESMO lote (ver §3).
      Check: derive-audit-family.py --assert-migrated sai 0

### W2 — O log histórico (decisão, não implementação)

> **ORDEM CORRIGIDA pelo pair-rail r8:** esta decisão é **pré-requisito
> da W1 reemitida**, não sucessora dela. Redirecionar escritores na W1
> já obriga a escolher entre copiar o log/chave/salt misturados ou
> inicializar estado novo — que é exatamente a escolha "declarar a
> janela" contra "arquivar e recomeçar". Executar a W1 antes **tomaria a
> decisão P0 do Owner por omissão**, e poderia rotacionar o salt ou
> reiniciar a cadeia prematuramente.

- [ ] `[P0]` Decidir e REGISTRAR. **"Segregar" está indisponível para
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
- [ ] `[P1]` **Emissores remanescentes (cura do r10 sobre o r9 #3):**
      derivar COMPORTAMENTALMENTE quais emissores ainda produzem
      eventos não-atribuíveis (os +149 do §1) e dispor CADA um — curar a
      atribuição ou registrar aceite por escrito. "Janela fechada" só
      pode ser declarada depois desta unidade.
      Check: dois snapshots consecutivos com ZERO nao-atribuiveis novos, OU tabela emissor→disposicao cobrindo 100% dos novos do intervalo medido; a decisao P0 da W2 cita esta evidencia
- [ ] `[P1]` Reavaliar `ceo-boot`, `audit-tokens` e `skill-health` como
      **eficácia de controle**, não como medição — e prever a rajada de
      advisories pós-migração.
      Check: vereditos antes e depois diffados; toda mudanca de cor explicada por escrito

### W3 — Instalação e adopters (esboço)

- [ ] `[P0]` Rota do installer: chave em `settings.base.json` e merge
      aditivo no `upgrade.sh`, usando o backup que já existe; curar
      `templates/{codex,grok}/pre-push-review-gate.sh`.
      Check: e2e de upgrade sobre instalacao existente — migra ou declara aceite; falha se nenhum dos dois
- [ ] `[P1]` `ceo-backup.sh` / `ceo-restore.sh` e `dist/ceo-plugin/hooks/`.
      Check: os dois scripts operam sobre o dir resolvido, nao sobre o literal
- [ ] `[P1]` Dois adopters no mesmo `$HOME` sem env resolvem para
      caminhos e chaves distintos.
      Check: e2e com dois projetos; logs e chaves distintos

## Acceptance criteria

- [ ] AC-1 [P0] A família é derivada comportamentalmente e a derivação é
      REPRODUZÍVEL por comando — não por prosa nem por grep.
- [ ] AC-2 [P0] Teste de paridade com controle negativo demonstrado no
      mesmo commit, usando fixture de dois projetos.
- [ ] AC-3 [P0] Matriz de precedência por artefato, sobre a lista
      **fechada na US5** — não sobre os 5 artefatos da primeira redação.
- [ ] AC-4 [P0] Decisão sobre o log histórico registrada com
      justificativa — "não decidido" mantém o plano aberto.
- [ ] AC-5 [P1] Rota de adopter fechada ou explicitamente aceita.
- [ ] AC-6 [P0] W1-W3 são esboço não-normativo e nenhuma EXECUTA antes
      de ser reemitida a partir da W0. Dado o tamanho do delta do round
      1, a reemissão da W1 passa por sua própria rodada de crítica.
- [ ] AC-7 [P0] **Emenda ao ADR-001 registrada ANTES de qualquer
      execução da W1** (com a decisão SPEC v1 contra v2), porque o
      literal é violação de decisão ACCEPTED e o blast radius declarado
      lá (L2) não bate com o medido (L3+).

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
