# Resposta ao relatório de campo — adopter na `v1.4.2` (rascunho)

> **Autor:** CEO (`ceo-orchestration`). **Entrega:** do Owner, no canal
> que ele escolher. Este documento é o conteúdo, não o envio.
> **Fecha:** `PLAN-183` AC-16 (`[P3]`, não-bloqueante).
> **Data:** 2026-10-01 (S361). **Base:** `main` em `6f7069d3`; a tag
> `v1.4.2` aponta para `b55084da`.
> **Estado:** RASCUNHO. Nada foi enviado ao adopter.

O relatório trouxe sete achados, de A1 a A7. Essa numeração é a do
relatório da 1.4.2. Ela **não** é a da resposta anterior
(`resposta-ao-campo.md`, relatório da 1.3.0): os mesmos rótulos nomeiam
defeitos diferentes.

**Resultado:** cinco achados confirmados e dois parciais. Em quatro deles
(A1, A5, A6 e A7), a causa sugerida no relatório não se sustenta. O
relatório descreveu corretamente os sintomas dos sete.

**Nenhuma correção de código dos sete chegou ainda a quem já está
instalado.** A seção «O que já está curado» diz o que existe e o que está
planejado.

Cada causa abaixo foi conferida em 2026-10-01, no código do framework, no
histórico git ou nos arquivos do próprio adopter. O que veio só da
triagem de 30/09, sem nova conferência, leva a marca «da triagem». Onde
nada foi medido, o texto diz «não medido». Todas as horas estão em UTC-3.
As siglas estão no glossário, no fim.

---

## Resumo

| # | O que você viu | Veredito | Gravidade | Estado hoje |
|---|---|---|---|---|
| A1 | validador vermelho e fixtures de replay ausentes | sintoma confirmado; **causa sugerida não se sustenta** | grave | aberto — ondas W7a e W7b |
| A2 | `VERSION` da raiz parado em 1.3.0 | confirmado; é decisão documentada | menor | aberto — aviso na W8 |
| A3 | leitura de arquivo protegido recusada com «use Edit/Write» | confirmado; a recusa é deliberada e a mensagem está errada | menor | aberto — PLAN-195 |
| A4 | regra P4 do anti-overhead bloqueia greps de diagnóstico | confirmado | importante | aberto — W9 |
| A5 | aviso «RISKY DIFF» com lista de ~85 KB | **parcial** | importante | aberto — W9 |
| A6 | 5 skills «não referenciadas» e `_dispatch.md` ausente | **parcial**; as skills são roteadas | menor | aberto — W10 e W8 |
| A7 | servidor MCP do Codex com `CONNECTION_CLOSED` | confirmado; **causa medida é outra** | importante | template curado (`3c2fb8e9`); instalação existente aberta — W8 |

Gravidade: **grave** (P1), **importante** (P2), **menor** (P3).

---

## Correções de causa

### A1 — o vermelho não veio de upgrade

**Causa sugerida no relatório (lida na triagem):** um upgrade entregou as
fixtures de replay, e o horário dos arquivos em 10/09 é o do upgrade.

**Verificado, em quatro pontos:**

1. **A instalação nova nunca entrega a pasta de testes.** O `install.sh`
   exclui `.claude/hooks/tests` desde a 1.0.0
   (`scripts/install.sh:1468`; o comentário já existe na tag `v1.0.0`).
2. **O upgrade entregou a pasta só antes da 1.2.0.** O `upgrade.sh` da `v1.1.0`
   copiava a árvore `.claude/hooks` inteira, testes incluídos
   (`backup_and_replace ".claude/hooks"`; PLAN-161, defeito 2b). O commit
   `e718cd89` (27/07/2026, primeira tag `v1.2.0-rc.1`) corrigiu isso. Desde
   então, `_framework_path_excluded` (`scripts/_framework_manifest_set.sh:95-107`)
   exclui a pasta nas duas rotas. O corpo dessa função é idêntico nas tags
   `v1.2.0`, `v1.3.0`, `v1.4.0` e `v1.4.2`.
3. **No seu repositório, as fixtures já existiam antes do upgrade de
   10/09.** O `.claude/.install-state.json` registra cinco execuções: 16/08,
   22/08, 24/08, 10/09 e 30/09. Nenhuma ocorreu em 19/08, dia em que as três
   fixtures nasceram (17:43). Os backups `.claude.bak/` de 22/08 e de 24/08
   já continham `hooks/tests/fixtures`.
4. **O horário de 10/09 é de uma cópia manual.** O upgrade de 10/09 gravou
   o estado às 20:43 (UTC-3). As três fixtures têm data de modificação às
   20:50, sete minutos depois. O backup do próprio upgrade guarda a versão
   anterior, com conteúdo diferente da fonte. Depois da cópia, os três
   arquivos ficaram byte-idênticos aos da tag `v1.3.0` e da `v1.4.2`. A
   triagem atribuiu a cópia a uma sessão do mantenedor, que aplicava o
   contorno do defeito já conhecido. Esse autor vem da triagem: os arquivos
   não o registram.

**A causa real é um defeito de classe do framework, em duas formas.**

- **Forma 1 — o gate exige o que o instalador não entrega.** O
  `check_harness_config.py` lê as fixtures, por padrão, em
  `.claude/hooks/tests/fixtures/harness-config/replay` (`:156`). Esse é o
  caminho que o instalador exclui. Toda instalação nova a partir da 1.1.0
  nasce com o `harness_config_gate` vermelho no `/ceo-boot`. O gate existe desde
  `24d2a278` (primeira tag `v1.1.0-rc.1`).
- **Forma 2 — o contorno arma um segundo gate.** O
  `validate-governance.sh:1165` arma o gate PLAN-119 quando a pasta
  `.claude/hooks/tests` existe, mesmo vazia. O
  `check-test-audit-isolation.py:600` lê o `testpaths` do `pytest.ini` do
  diretório corrente. No seu repositório, esse valor aponta para `tests/`.
  O gate passa a varrer os seus testes de negócio (da triagem: 2 achados em
  arquivos seus). Criar a pasta à mão, como contorno, arma esse gate.

O relatório do defeito existe no repositório do framework desde
17/08/2026 (`92929755`). Pelo histórico dos planos, nenhuma onda de
correção o cobriu antes da triagem de 30/09 (`985a028e`). Esse atraso é do
framework.

**Perda de proteção em runtime: nenhuma.** O gate é advisory: o
`/ceo-boot` avisa e nunca bloqueia (`.claude/scripts/ceo-boot.py:2522`).

### A7 — não veio da 1.4.2 nem do pin

**Causa sugerida no relatório (lida na triagem):** o upgrade para a 1.4.2,
ou o pin do Codex em 0.156.1, quebrou o servidor MCP do Codex.

**Verificado, em quatro pontos:**

1. **O Codex removeu o subcomando.** O servidor registrado no `.mcp.json`
   executa `codex mcp-server`. O Codex CLI 0.154.0 removeu esse subcomando
   (nota de release #42993, de 09/09/2026, citada em `INSTALL.md:1002-1010`).
   Na 0.156.1 desta máquina, `codex mcp-server --help` imprime a ajuda
   geral do `codex`: o texto virou um prompt do CLI interativo.
2. **O seu `.mcp.json` não mudou desde a instalação.** Ele é byte-idêntico
   ao template das tags `v1.0.0` a `v1.4.1` (sha256 `5a5bfc40…`, conferido
   no adopter e com `git show v1.4.1:templates/.mcp.json`).
3. **O upgrade não toca o `.mcp.json`.** O `scripts/upgrade.sh` tem zero
   menções a `mcp.json`, e o `scripts/doctor.sh` tem zero menções a `mcp`. A
   1.4.2 mudou só o **template**, para `mcpServers` vazio (`3c2fb8e9`,
   28/09/2026). O upgrade de 30/09 não alterou o seu arquivo.
4. **O pin não escreve nada no adopter.** O pin do Codex vive em
   `.claude/governance/`, pasta que a instalação não entrega
   (`INSTALL.md:1027`; o seu repositório não a tem). Ele só decide qual
   binário o revisor cruzado aceita, dentro do checkout do framework.

**A data.** No log do Claude Code do adopter, a última conexão bem-sucedida
ao servidor é de 15/09 (10:15). A primeira falha é do mesmo dia
(18:59), com `stdin is not a terminal`. Os 13 registros desde então
falharam com `CONNECTION_CLOSED`. A remoção do subcomando explica a falha.
A data em que o Codex local passou à 0.154.0 ou a uma versão posterior não
foi medida. O framework registrou um re-pin no mesmo dia (`928825cc`), mas
o re-pin só passou a aceitar a versão que já estava instalada.

**Alcance.** O defeito atinge toda instalação feita por cerimônia
`maintainer` até a 1.4.1 cujo Codex seja 0.154.0 ou posterior. O `.mcp.json`
é semeado uma vez e nunca refeito.

**Efeito no framework.** O revisor cruzado (pair-rail) **não** usa esse
servidor: ele roda `codex exec` (`INSTALL.md:1021-1023`). O servidor morto
causa ruído na inicialização e deixa ociosos dois hooks
(`check_codex_filewrite.py` e `check_codex_response.py`), que só disparam
quando existe um servidor chamado `codex`.

### A6 — as skills são roteadas; o defeito é do validador

**Leitura do relatório (da triagem):** as cinco skills não estão ligadas
a nenhum agente.

**Verificado:**

1. **Três das cinco são roteadas.** O `.claude/team.md` cita
   `core/pii-data-flow`, `core/consent-lifecycle` e `core/dpo-reporting`
   na linha do Compliance Specialist (`team.md:140`, `:200` e `:539`). As
   três pastas existem em `.claude/skills/core/`.
2. **O validador só reconhece o nome curto.** Ele procura o nome entre
   crases, sem prefixo (`validate-governance.sh:200`). A forma
   `core/<skill>` não casa, e o validador emite o aviso.
3. **As outras duas não têm rota por desenho.** `pre-plan-brainstorm` roda
   antes de planos L3 (ADR-058). `terse-mode` é o comando `/terse`. O
   framework as isenta, e a isenção mora em
   `.claude/skill-governance-grandfather.yaml`.
4. **O arquivo da isenção não chega ao adopter.** Ele está marcado como
   depreciado, e nenhuma rota de `scripts/` ou `templates/` o cita. O
   validador lê só ele (`validate-governance.sh:130`). A política que o
   substitui, `.claude/policies/grandfather-cap.policy.yaml`, **é**
   entregue (`scripts/install.sh:1735`).
5. **`_dispatch.md` não é gerado no upgrade.** A função
   `upgrade_agents_canonical_only` (`scripts/upgrade.sh:4496`) instala cinco
   agentes e nunca gera o `_dispatch.md`. A instalação nova não entrega os
   agentes. O validador avisa (`validate-governance.sh:810`).

**Armadilha.** Se você gerar o `_dispatch.md` à mão, o próximo upgrade que
mudar um agente o deixa velho. O validador completo então o reporta como
ERRO (`validate-governance.sh:790`).

### A5 — «a cada parada» não se confirma; a falta de teto, sim

**Leitura do relatório (da triagem):** a lista de arquivos arriscados, de
~85 KB, aparece a cada parada.

**Verificado:**

1. **A lista não tem teto.** O hook `codex_review_user_code.py` monta a
   mensagem com `", ".join(files)` (`:303`). O `DIFF_CAP = 16000` (`:50`)
   corta só o texto do diff enviado ao revisor (`:117`), não a lista.
   Medido numa emulação da triagem: 1.622 arquivos e 86.834 bytes. Quanto
   disso o Claude Code injeta no contexto: não medido.
2. **Existe deduplicação, mas ela é fraca.** A chave é o sha256 do diff já
   cortado nos primeiros 16.000 caracteres (`:117`, `:146`). O aviso volta
   quando esse trecho muda, por exemplo depois de um upgrade. Uma mudança
   real do seu código que fique depois desse ponto não altera a chave, e o
   aviso novo não aparece (`:296`).

---

## Os achados A2, A3 e A4

- **A2.** A raiz `VERSION` é semeada uma vez (`scripts/install.sh:1829-1840`,
  só em cerimônia diferente de `user`). O upgrade nunca a refaz, por
  decisão: reescrevê-la poderia tomar um arquivo seu (ADR-155-AMEND-1 §2,
  tag `v1.3.0`). A versão real está em `.claude/.framework-version`.
- **A3.** Ver a seção seguinte.
- **A4.** A regra P4 bloqueia no 4.º comando de Bash que começa por
  `grep`, `find`, `rg` ou `ag`, dentro de 5 minutos. Os comandos precisam
  ser lexicalmente distintos (`check_anti_ceo_overhead.py:175`, `:184`,
  `:198`, `:553`, `:715`). O hook não sabe se um grep depende do anterior.
  Da triagem: quatro greps de diagnóstico bloqueiam no quarto.

---

## O vínculo do A3 com o PLAN-195

O A3 não tem onda no `PLAN-183`. A recusa vem do guarda de Bash
(`.claude/hooks/check_bash_safety.py:2332-2345`), um arquivo canônico: só
muda por cerimônia, com pacote revisado e assinatura GPG do Owner.

O guarda recusa um comando quando um interpretador inline recebe, no texto
do próprio comando, o nome de um arquivo protegido. Ele decide pela
**menção** do caminho e não separa «lê» de «escreve». A recusa é
deliberada. O defeito é a **mensagem**: ela manda usar Edit/Write, o que
não se aplica a uma leitura.

O guarda pertence ao `PLAN-195`, que trata uma classe de contornos de
guardas de shell. O plano registra a cura do A3 como item da sua W2:

- A mensagem passa a apontar Read, `cat` ou `grep` para leitura.
- O ramo de texto não tokenizável ganha mensagem própria.
- **Não** entra lista de leituras permitidas. A lista abriria um caminho
  de escrita. A regra do guarda, de negar o que ele não consegue provar
  seguro, rejeita esse desenho.
- A mensagem corrigida entra antes, ou junto, de qualquer regra nova que
  torne a recusa mais frequente.

**Estado.** O `PLAN-195` está em `reviewed`, e o debate de nível L3 fechou
em PROCEED (01/10/2026). A W2 não tem vaga reservada e vem depois da parte
A do mesmo plano. Este documento não descreve as formas da classe. O plano
público também não, por decisão do Owner.

---

## O que já está curado

| Item | Commit | O que mudou | Alcance |
|---|---|---|---|
| A7 | `3c2fb8e9` e `f0e219c2` (28/09/2026; ambos na tag `v1.4.2`) | `templates/.mcp.json` passa a `mcpServers` vazio, e o `INSTALL.md` (§Troubleshooting) explica a remoção manual (`3c2fb8e9`); o `CHANGELOG.md` [1.4.2] repete o aviso (`f0e219c2`) | **só instalações novas.** O seu `.mcp.json` não muda |
| A2 | `9d3f21d0` (07/08/2026; na tag `v1.3.0`) | o ADR-155-AMEND-1 §2 e o `INSTALL.md` documentam que a raiz `VERSION` é cópia do momento da instalação | **só documentação.** Nenhum comportamento mudou |

**Nada além disso.** Desde a `v1.4.2`, nenhum commit toca o código dos
sete achados. A conferência foi um `git log v1.4.2..HEAD` sobre os hooks
envolvidos, o `install.sh`, o `upgrade.sh`, o `doctor.sh` e o
`_framework_manifest_set.sh`. Ela cobriu também o validador,
`.claude/policies`, `templates/.mcp.json` e o `INSTALL.md`. O resultado veio
vazio. Dos 12 commits desde a tag, 11 são de plano e de documentação; o
`985a028e` cria as ondas W7 a W10. O outro, `6f7069d3`, ajusta o `/ceo-boot`
e o ledger de substrato e não toca nenhum dos sete achados.

## O que está em onda

| Onda | Cobre | O que muda | Depende de |
|---|---|---|---|
| **W7a** | A1 (forma 1) | as 3 fixtures passam a morar em `.claude/hooks/_lib/harness_replay/`, caminho que o instalador entrega; o marcador de runtime muda de forma; emenda aditiva no ADR-158 | vaga na fila de pacotes protegidos |
| **W7b** | A1 (forma 2) | **um** predicado de «isto é o repositório-fonte?» (o marcador do ADR-001); o gate PLAN-119 deixa de armar pela pasta e de varrer o `tests/` do adopter; teste que instala a v1.4.2 e atualiza | W7a publicada no `main` |
| **W8** | A7, A2, A6 (`_dispatch.md`) | o upgrade avisa pelo nome sobre a entrada `codex` morta e troca o arquivo só em caso de prova de origem (decisão em debate); avisa quando `VERSION` diverge, sem escrever; gera o `_dispatch.md`; o `doctor.sh` acusa a entrada morta | outras ondas que tocam os mesmos arquivos |
| **W9** | A4, A5 | P4 vira aviso no Bash, e a liberação (override) deixa de gerar registros repetidos; «RISKY DIFF» ganha teto de 2 KB, chave com o conjunto completo e aviso só do delta | vaga na fila de pacotes protegidos |
| **W10** | A6 (validador) | o validador aceita `<nível>/<skill>` e lê as isenções da política entregue | W7b publicada no `main` |
| **PLAN-195 W2** | A3 | mensagem da recusa de leitura | parte A do PLAN-195 |

**Sem data.** O mantenedor não fixou datas. Cada onda canônica passa por
debate (quando L3), revisão cruzada do Codex e assinatura GPG antes de
entrar no `main`. A ordem no plano: a W7a vem primeiro, porque o A1 é o único achado
grave; a W7b vem logo depois.

**Três decisões seguem em debate.** A proposta de partida de cada uma:

- **`.mcp.json`:** o upgrade troca o arquivo sozinho, com backup, **só**
  quando ele for byte-idêntico a um template que o framework entregou. Um
  `.mcp.json` customizado nunca é tocado: o upgrade só avisa.
- **P4:** vira aviso, porque o hook não sabe se um grep depende do outro.
- **«RISKY DIFF»:** não tirar do escopo o que o framework entregou nesta
  onda. O teto, a chave completa e o delta já resolvem o custo.

---

## O que fazer hoje

### A1 — ler o vermelho e decidir sobre a pasta de testes

1. Leia o vermelho do `harness_config_gate` no `/ceo-boot` como aviso. Ele
   nunca bloqueia, e nenhuma proteção em runtime se perde.
2. Evite criar `.claude/hooks/tests/` à mão. A pasta arma o gate PLAN-119
   do validador completo, que varre o seu `tests/`.
3. Se a pasta já existe, escolha um dos dois caminhos:
   - **Remover, com backup.** Rode, a partir de um checkout do framework
     na tag `v1.4.2`, primeiro a pré-visualização e depois a execução:

     ```bash
     bash scripts/upgrade.sh /caminho/do/seu-repo --dry-run --purge-misinstalled
     bash scripts/upgrade.sh /caminho/do/seu-repo --purge-misinstalled
     ```

     A pré-visualização imprime linhas `would PURGE`. A execução faz backup
     em `.claude.bak/` antes de apagar. O purge só apaga arquivo idêntico a
     um que o framework tem: um arquivo editado por você fica e aparece como
     `KEPT`. Ele remove também as pastas que ficarem vazias. Se o purge
     limpar a pasta inteira, o validador completo deixa de acusar o PLAN-119.
     O `/ceo-boot` mantém o aviso do A1, como em todo adopter, até a W7a.
   - **Manter.** O gate do harness encontra os arquivos que exige, e o
     validador completo segue acusando o PLAN-119, o que pode esconder uma
     falha real.

### A2 — ler a versão no lugar certo

Leia a versão do framework em `.claude/.framework-version`. Não use a raiz
`VERSION` para isso.

### A3 — ler arquivo protegido

Leia o arquivo com a ferramenta Read do Claude Code ou com `cat` e `grep`
direto no arquivo. A recusa atinge comandos em que um interpretador recebe
o caminho protegido no próprio texto.

### A4 — greps de diagnóstico em sequência

Espere a janela de 5 minutos passar. Use a ferramenta Grep do Claude Code,
que o contador não considera. A variável `CEO_OVERHEAD_ACK=1` reconhece o
aviso e libera o comando. Cada uso grava o evento de auditoria
`anti_ceo_overhead_override_used`.

### A5 — lista longa de «RISKY DIFF»

1. Faça commit dos arquivos que o upgrade entregou. A lista cobre só o que
   difere de `HEAD`, mais os arquivos não rastreados.
2. Se a lista continuar longa, a variável `CEO_CODEX_USER_REVIEW=0`
   desliga o aviso (`codex_review_user_code.py:285`). Ela desliga também o
   lembrete de revisão cruzada que o aviso faz.

### A6 — avisos de skill e `_dispatch.md`

1. Ignore os cinco avisos de skill «não referenciada». São `WARN`, não
   `ERROR`, e as skills existem e são roteadas.
2. Evite gerar o `_dispatch.md` à mão. Se gerar, regenere-o depois de cada
   upgrade:

   ```bash
   python3 .claude/scripts/generate-dispatch.py --write
   ```

### A7 — remover a entrada morta

Rode na raiz do seu repositório:

```bash
claude mcp list                      # a linha "codex: codex mcp-server" é a entrada morta
claude mcp remove codex -s project   # remove a entrada do .mcp.json
```

No Claude Code 2.1.280, o `claude mcp remove` também apagou a chave
`_comment` do arquivo (`INSTALL.md:1052-1054`). Se você guarda notas nele, apague
à mão a chave `codex` dentro de `mcpServers`. O revisor cruzado continua
funcionando sem esse servidor.

---

## Glossário

- **Adopter:** repositório que instalou o framework.
- **Advisory:** aviso que nunca bloqueia a sessão.
- **Canônico:** arquivo protegido. Mudar um exige cerimônia.
- **Cerimônia:** pacote revisado mais assinatura GPG do mantenedor.
- **Fixture (de replay):** arquivo de entrada de um teste de controle. O gate
  do harness o reexecuta contra o hook real.
- **Gate:** verificação que passa ou reprova.
- **Hook:** script que o Claude Code roda antes ou depois de uma ferramenta.
- **L3:** nível de risco que exige debate antes de executar.
- **MCP:** protocolo pelo qual o Claude Code conversa com servidores de
  ferramentas.
- **Onda (W7a, W7b, W8, W9, W10):** pacote de correção do `PLAN-183`.
- **Pair-rail:** revisão cruzada de uma edição canônica por um segundo
  modelo (Codex).
- **PLAN-119:** gate do validador que confere o isolamento de auditoria nos
  testes do próprio framework.
- **Pin:** versão do Codex travada por hash.
- **Semeado uma vez:** arquivo que o instalador cria se não existir, e que o
  upgrade nunca refaz.
- **Validador:** `.claude/scripts/validate-governance.sh`.

---

## Notas ao Owner — remover antes de enviar

1. **Decisão pendente (OQ-18).** Purgar ou manter as fixtures neste
   adopter fica a critério do Owner. O texto acima oferece os dois
   caminhos, sem escolher. A recomendação do CEO é purgar.
2. **A afirmação «nenhuma versão entregou as fixtures»** da síntese de 30/09
   foi estreitada. O `upgrade.sh` da 1.1.0 copiava `.claude/hooks`
   inteiro. A afirmação vale para o histórico deste adopter (instalado em
   16/08, na 1.3.0), não para todo adopter.
3. **Fatos que só existem nos arquivos do adopter:** o histórico de
   execuções, as datas das fixtures, os backups e o log MCP do Claude Code.
   Foram conferidos em 2026-10-01, só por leitura. Não estão neste
   repositório, e o adopter pode refazer cada conferência.
4. **A autoria da cópia de 10/09** vem da triagem de 30/09, não dos
   arquivos. O texto diz isso. Cabe ao Owner decidir se mantém a frase.
5. **O vínculo do A3 fica na classe.** O documento não traz nenhuma forma
   concreta de comando.
6. **Sem datas.** O documento não promete nenhuma.
