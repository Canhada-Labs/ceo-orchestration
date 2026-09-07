---
id: PLAN-176
title: Currency de modelos — detectar lançamento novo; adoção nunca automática
status: reviewed
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169]
budget_tokens: 390-610k
budget_sessions: 5-6
budget_usd_estimate: "3.5-5.5 USD"
tier_mix_estimate: "CEO Opus 5 ~70% (plano, refutacao, cerimonia); builders Sonnet 5 ~25% (docs e testes); Haiku 4.5 ~5% (leituras)"
context_risk: medium
external_wait: none
eta_calendar: "mesmo-dia a D+1"
tags: [model-currency, egress, automation, seed]
---

# PLAN-176 — Detectar modelo novo (a adoção continua sendo cerimônia)

> **O que este plano entrega, em uma frase.** Quando um fornecedor
> lança um modelo novo, o repositório **descobre sozinho** e **avisa**.
> Quem decide adotar continua sendo o Owner, por assinatura GPG
> (GNU Privacy Guard, a chave com que o Owner assina material
> canônico). Detecção automática, adoção nunca automática — é a regra
> já publicada em `CLAUDE.md` §5, e este plano constrói só a metade
> da detecção.

> **Revisão de 2026-09-06 (S348).** Este texto absorve os 16 must-fix
> do consenso do round 1 (`.claude/plans/PLAN-176/debate/round-1/consensus.md`)
> sob a decisão 4.14 do Owner («Autorizar a revisão do plano»). O
> veredito `ESCALATE-TO-OWNER` do round 1 está RESOLVIDO por essa
> decisão. `status:` permanece `reviewed`: o flip para `executing` é a
> decisão 4.10, e só acontece depois da rodada 2 do debate sobre este
> texto revisado.

> **Aviso de nomenclatura (leia antes de comparar com o consenso).** O
> consenso do round 1 propôs cortar a onda W0 em «W0a canônico / W0b
> livre». Esta revisão usa outro corte, autorizado no mesmo pacote: em
> **cada** onda, a perna `a` é **livre** e aterrissa PRIMEIRO, a perna
> `b` é **canônica** (exige assinatura GPG) e aterrissa DEPOIS. O corte
> por cerimônia que o consenso pediu está inteiro — ele mora em
> W1a/W1b. O corte por rede que o Owner pediu mora em W0a/W0b.

## 1. Vocabulário (siglas definidas uma vez)

- **Camada T (de *trust*, confiança).** O conjunto de identificadores
  de modelo que o Owner assinou. Fonte única: os dois blocos
  legíveis por máquina do `.claude/adr/ADR-149-model-id-allowlist.md`
  — `VETO_FLOOR_ALLOWED` (quem pode ocupar um assento com poder de
  VETO) e `AVAILABLE_MODELS_WORKING_SET` (o que o harness pode
  selecionar em qualquer superfície).
- **Camada P (de *preference*, preferência).** Apelidos estáveis
  (`claude-frontier`) resolvidos para um identificador concreto. Muda
  por Pull Request auditado, sem assinatura.
- **Oráculo de canonicidade.** `check_canonical_edit.py --is-canonical
  <path>` imprime `<path><TAB>1` (edição exige cerimônia) ou
  `<path><TAB>0` (edição livre).
- **Ciclo.** Uma execução da rotina de detecção. É a unidade em que
  este plano expressa limiar — nunca dia de calendário.

## 2. A tese central, medida (o que o round 1 confirmou)

O split T/P preserva a cerimônia **por construção**, sem alargar a
lista de guardas do hook canônico. Medido nesta revisão, na árvore de
trabalho, com o oráculo acima:

    .claude/governance/models-registry.json      1   (T — exige assinatura)
    .claude/hooks/_lib/model_registry.py         1   (resolver — exige assinatura)
    .claude/hooks/_lib/model_feed_fetch.py       1   (fetcher — exige assinatura)
    .claude/adr/ADR-198-...md                    1   (o ADR — exige assinatura)
    .claude/governance/gate-scripts-manifest.txt 1   (manifesto — exige assinatura)
    .github/workflows/validate.yml               1   (CI — exige assinatura)
    .claude/data/models-preference.json          0   (P — Pull Request livre)
    .claude/scripts/check-model-literals.py      0   (lint — Pull Request livre)
    .claude/scripts/check-model-currency.py      0   (detector — Pull Request livre)
    .claude/hooks/tests/test_model_feed_fetch.py 0   (teste — Pull Request livre)

Nenhuma extensão da lista de guardas é necessária. É a decisão mais
barata e mais forte do plano, e a revisão não a toca.

## 3. Arquitetura — o que decide o quê

### 3.1 A camada T é TETO, não último recurso

O texto anterior dizia `Precedência: caller > env > preference >
default do schema` e era genuinamente ambíguo: dava para ler a camada
assinada como o último fallback. Fica assim, sem ambiguidade:

1. **A camada T SELECIONA e VALIDA.** Nenhum identificador servido por
   qualquer origem é entregue se não for membro do conjunto T
   aplicável — `VETO_FLOOR_ALLOWED` para superfícies com poder de
   VETO, `AVAILABLE_MODELS_WORKING_SET` para as demais. Fora do teto,
   **toda** origem é recusada, inclusive quem chamou.
2. **Dentro do teto**, a ordem de escolha é: quem chamou > variável de
   ambiente > camada P > valor padrão do esquema.
3. Recusa pelo teto emite `model_routing_enforced` (ação já existente
   na taxonomia fechada de `.claude/hooks/_lib/audit_emit.py`) — não
   se inventa ação nova.

### 3.2 A variável de ambiente é um conjunto FECHADO de um elemento

O repositório já pagou essa classe duas vezes (`BASH_ENV` e
`argparse.py` em `sys.path[0]` na S345; o portador de diretório
neutralizado nas S321/S322). Portanto:

- O conjunto é **exatamente** `{CEO_MODEL_PREFERENCE}`. Qualquer outro
  nome é ignorado pelo resolver.
- A gramática do valor é `^[a-z0-9][a-z0-9.-]{0,63}$`. Sem barra, sem
  contrabarra, sem ponto inicial: a variável **não consegue** carregar
  um caminho para o arquivo da camada T.
- Valor fora da gramática emite `env_var_hijack_blocked` (ação já
  existente) e é descartado — não degrada para padrão em silêncio.

### 3.3 "Fora do esquema" não é fail-closed, é degradação declarada

O texto anterior chamava de `fail-closed p/ default` o caminho em que
um valor da camada P não valida contra o esquema. Não é fechamento: é
**degradação para o valor padrão do esquema**, que é uma decisão
diferente e precisa ser vista. Semântica final: valor P inválido é
descartado, o padrão do esquema é servido, e a troca emite
`model_choice_recommended` com o motivo. Quem lê: o `/ceo-boot`
(advisory da onda W3) e o relatório noturno.

### 3.4 Onde a doutrina T/P ganha autoridade

Hoje ela **não tem** autoridade em disco: o §1 do texto anterior a
citava como «decidida no ADR-149 Amendment 2», mas esse número está
ocupado por material que o Owner assinou (`ADR-149-model-id-allowlist.md:209`,
cerimônia `wave-fable51`). Correção:

- O rascunho `PLAN-176/adr-149-amendment2-draft.md` vira
  **`.claude/adr/ADR-198-model-trust-preference-split.md`**, um ADR
  próprio. **ADR-198 é o próximo número livre, medido nesta revisão:**
  o diretório tem 198 arquivos, o maior número em uso é 197
  (`ADR-197-user-profile-derivation.md`) e não existe arquivo
  `ADR-198-*`.
- Enquanto o ADR-198 não estiver `ACCEPTED`, **nenhum trecho deste
  plano cita a doutrina T/P como decidida.** Ela é uma proposta deste
  plano, ratificada na onda W1b.

## Waves

> Regra de leitura: em cada onda a perna `a` é livre (Pull Request
> auditado) e aterrissa primeiro; a perna `b` é canônica (assinatura
> GPG do Owner) e aterrissa depois. Cada caixa de seleção declara o
> comando cujo código de saída a fecha.

### Wave W0a — detecção OFFLINE (livre, zero rede)

Compara o que o Owner assinou (os dois blocos do ADR-149) contra as
tabelas locais do repositório e reporta divergência. **Não faz nenhuma
requisição de rede.** É a onda mais barata e a que sozinha já responde
"apareceu identificador novo em alguma superfície?".

Paths: `.claude/scripts/check-model-currency.py`,
`.claude/data/model-currency-state.json`,
`.claude/scripts/tests/test_check_model_currency.py`. Oráculo = 0 nos três.

- [ ] `[P0][US1][.claude/scripts/check-model-currency.py]` O detector lê os
      blocos `VETO_FLOOR_ALLOWED` e `AVAILABLE_MODELS_WORKING_SET` do
      ADR-149 e os compara com `cost-table.yaml`,
      `model-deprecations.json` e `settings.json`; divergência sai como
      achado nomeado, nunca como diferença crua.
      Check: `python3 .claude/scripts/check-model-currency.py --check; test $? -le 1`
- [ ] `[P0][US1][.claude/scripts/check-model-currency.py]` Controle
      NEGATIVO de rede: o detector não importa nem invoca primitiva de
      rede alguma.
      Check: `! grep -qE 'urllib|urlopen|socket|http[.]client|requests' .claude/scripts/check-model-currency.py`
- [ ] `[P0][US1][.claude/scripts/check-model-currency.py]` Controle
      POSITIVO da detecção: injetar um identificador falso
      (`claude-opus-6`) no bloco do ADR numa cópia descartável faz o
      detector ficar VERMELHO; sem a injeção, VERDE.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k injected_model_turns_red`
- [ ] `[P1][US1][.claude/data/model-currency-state.json]` O estado de
      cada ciclo é gravado em arquivo RASTREADO pelo git, com o número
      do ciclo, o resultado por raia e a soma de falsos-positivos.
      Check: `git ls-files --error-unmatch .claude/data/model-currency-state.json && python3 -m json.tool .claude/data/model-currency-state.json >/dev/null`
- [ ] `[P1][US1][.claude/scripts/check-model-currency.py]` **A raia de um
      fornecedor só abre se ele for ATIVO**, definido como: membro do
      conjunto de trabalho do ADR-149 **e** com linha de preço em
      `cost-table.yaml`. Fornecedor sem linha de preço é INERTE por
      construção — fail-closed, nunca uma raia que reporta vazio. Medido
      nesta revisão: a tabela de preços tem 12 identificadores, todos
      `claude-*`; zero `gpt`, zero `gemini`, zero `grok`. **Na abertura,
      portanto, existe exatamente UMA raia ativa: Anthropic.**
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k active_lanes_is_anthropic_only`

### Wave W0b — busca upstream OPCIONAL, desligada por padrão (canônica)

A única perna com rede do plano inteiro. Ela existe para responder
"o fornecedor lançou algo que ainda não está em lugar nenhum do
repositório?" — pergunta que a W0a, por ser offline, não alcança.

**Por que módulo próprio e não `check-substrate-watch.py`.** Aquele
arquivo declara no próprio cabeçalho (linhas 10-11) que agentes
permanecem sem rede sob o ADR-136-AMEND-1, e mede zero ocorrências de
primitiva de rede. Além disso o oráculo dá `0` para ele: injetar rede
ali poria a lista de destinos permitidos — o único lastro da garantia
de egresso — num arquivo editável sem assinatura. O fetcher vai para
`.claude/hooks/_lib/model_feed_fetch.py`, cujo oráculo dá **1**:
**criar ou editar esse arquivo é cerimônia GPG**, e a lista de
destinos permitidos mora DENTRO dele.

**A postura do ADR-136-AMEND-1 não muda, e isto é desenho, não
omissão.** Nenhum agente ganha rede: o fetcher é invocado pelo Owner ou
pela rotina agendada, nunca de dentro de um agente. Precedente medido
para um módulo de biblioteca com rede sob cerimônia:
`.claude/hooks/_lib/otel_emit.py` já usa `urllib.request` e o oráculo
também dá 1 para ele.

**Lista de destinos permitidos (concreta — o texto anterior nomeava
zero destinos).** Exatamente dois pares host+caminho, ambos já citados
como proveniência dentro da árvore:

    platform.claude.com  /docs/en/about-claude/models/overview
    platform.claude.com  /docs/en/docs/about-claude/model-deprecations

A fonte `models.dev` fica FORA: preço é assunto do ADR-148, não desta
classe (ver §5).

**Garantia de egresso, reescopada para esta onda.** Requisições são
`GET`, sem corpo, sem parâmetro de consulta além do caminho fixo, sem
cabeçalho customizado: nada do repositório sai. A garantia vale **aqui**
— a onda W2 declara o egresso dela em separado. A citação do ADR-114
sai do lugar de controle de egresso: aquele ADR redige prompts enviados
a um modelo externo, e um `GET` sem corpo não tem o que redigir. Fica,
no máximo, como nota de simetria.

Paths canônicos: `.claude/hooks/_lib/model_feed_fetch.py` (1 path, UMA
assinatura). O teste vai para `.claude/hooks/tests/test_model_feed_fetch.py`,
que o oráculo dá 0 e o `pytest.ini` coleta.

- [ ] `[P0][US2][.claude/hooks/_lib/model_feed_fetch.py]` O fetcher nasce
      DESLIGADO: sem opção explícita de habilitação, ele não abre soquete
      e retorna "desabilitado".
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k disabled_by_default`
- [ ] `[P0][US2][.claude/hooks/_lib/model_feed_fetch.py]` A lista de
      destinos permitidos é constante no módulo; destino fora dela é
      recusado NOMEADAMENTE, e redirecionamento para outro host não é
      seguido.
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k "allowlist or redirect"`
- [ ] `[P0][US2][.claude/hooks/_lib/model_feed_fetch.py]` Cada despacho
      emite `egress_destination_detected` com host e caminho — ação já
      existente na taxonomia fechada, nenhuma ação nova.
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k emits_egress_event`
- [ ] `[P0][US2][.claude/scripts/check-substrate-watch.py]` Controle de
      NÃO-REGRESSÃO da postura: o instrumento que se declara sem rede
      continua sem rede depois desta onda.
      Check: `! grep -qE 'urllib|urlopen|socket|http[.]client|requests' .claude/scripts/check-substrate-watch.py`
- [ ] `[P0][US2][.claude/hooks/_lib/model_feed_fetch.py]` Controle de
      cerimônia: o oráculo confirma que o módulo exige assinatura.
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k oracle_says_canonical`
- [ ] `[P1][US2][.claude/hooks/_lib/model_feed_fetch.py]` Resposta
      malformada, ambígua ou acima do limite de tamanho é FAIL-CLOSED:
      relatório, nunca proposta.
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k "malformed or oversize"`

### Wave W1a — camada P, lint e registro de exceções (livre; aterrissa ANTES da W1b)

**Ordem obrigatória, e o motivo é mecânico.** O manifesto de scripts de
portão fixa o resumo criptográfico de cada script que protege. Ele não
consegue fixar o byte de um arquivo que ainda não existe. Logo o lint
nasce aqui, livre, e só na W1b entra no manifesto e no CI.

Paths: `.claude/data/models-preference.json`,
`.claude/scripts/check-model-literals.py`,
`.claude/scripts/model-literals-grandfather.txt`, testes. Oráculo = 0
em todos.

- [ ] `[P0][US3][.claude/data/models-preference.json]` A camada P existe,
      valida contra o esquema e resolve pelo menos um apelido para um
      identificador concreto.
      Check: `python3 -m pytest .claude/scripts/tests/test_model_preference.py -q`
- [ ] `[P0][US3][.claude/scripts/check-model-literals.py]` O lint acusa
      identificador literal novo fora de autoridade, com registro de
      exceções e catraca (o registro só encolhe).
      Check: `python3 .claude/scripts/check-model-literals.py --check`
- [ ] `[P0][US3][.claude/scripts/check-model-literals.py]` Controle
      POSITIVO da catraca: plantar um literal novo num arquivo
      descartável faz o lint ficar VERMELHO.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_literals.py -q -k planted_literal_turns_red`
- [ ] `[P0][US3][.claude/scripts/model-literals-grandfather.txt]` O
      registro de exceções é arquivo rastreado, uma linha por exceção,
      com motivo.
      Check: `git ls-files --error-unmatch .claude/scripts/model-literals-grandfather.txt`

### Wave W1b — registro T, resolver e o ADR (canônica, UMA assinatura)

Cinco caminhos canônicos, um pacote, uma assinatura — dentro do teto de
oito caminhos do modelo de operação v2. São: o registro T em
`.claude/governance/`, o resolver em `.claude/hooks/_lib/`, o ADR-198
em `.claude/adr/`, o manifesto de scripts de portão em
`.claude/governance/`, e o arquivo de validação do CI em
`.github/workflows/`.

- [ ] `[P0][US4][.claude/adr/ADR-198-model-trust-preference-split.md]` O
      ADR-198 entra `PROPOSED` no pacote; o flip para `ACCEPTED` é o
      arquivo `.asc` assinado, nunca o commit que reescreve o campo.
      Check: `grep -qE '^status: (PROPOSED|ACCEPTED)' .claude/adr/ADR-198-model-trust-preference-split.md`
- [ ] `[P0][US4][.claude/hooks/_lib/model_registry.py]` O resolver aplica
      a camada T como TETO (§3.1): identificador fora do conjunto é
      recusado mesmo quando pedido por quem chamou.
      Check: `python3 -m pytest .claude/hooks/_lib/tests/test_model_registry.py -q -k ceiling_rejects_caller`
- [ ] `[P0][US4][.claude/hooks/_lib/model_registry.py]` O conjunto de
      variáveis de ambiente é fechado em um elemento e a gramática do
      valor recusa caminho (§3.2), emitindo `env_var_hijack_blocked`.
      Check: `python3 -m pytest .claude/hooks/_lib/tests/test_model_registry.py -q -k "closed_env_set or env_value_grammar"`
- [ ] `[P0][US4][.claude/hooks/_lib/model_registry.py]` Sem rede e só
      biblioteca padrão, como o resto da camada de hooks.
      Check: `! grep -qE 'urllib|urlopen|socket|http[.]client|requests' .claude/hooks/_lib/model_registry.py`
- [ ] `[P0][US4][.claude/governance/gate-scripts-manifest.txt]` O lint da
      W1a entra no manifesto com o resumo criptográfico do byte que
      aterrissou, e a verificação do manifesto passa.
      Check: `python3 -m pytest .claude/scripts/tests/test_gate_scripts_manifest.py -q`
- [ ] `[P0][US4][.github/workflows/validate.yml]` O lint roda no CI como
      passo próprio, e o passo aparece no arquivo de validação.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_literals.py -q -k wired_into_ci`
- [ ] `[P0][US4]` **Teste-mestre do split**, com os dois controles: um
      identificador falso injetado no registro T aparece em todas as
      superfícies da camada P sem uma linha de código editada, e o
      oráculo confirma que o arquivo T exige assinatura enquanto o P não.
      Check: `python3 -m pytest .claude/hooks/_lib/tests/test_model_registry.py -q -k split_oracle_contract`
- [ ] `[P1][US4]` **O conjunto VERMELHO conhecido é publicado, não
      escondido.** Medido nesta revisão, o oráculo `replacements ⊆
      valid_override_ids` como escrito no texto anterior é um erro de
      categoria: ele compara substitutos Anthropic contra
      `_VALID_MODELS`, que é a lista de revisores da linha OpenAI. Na
      forma correta, por família de fornecedor, **quatro identificadores
      estão vermelhos hoje**: `claude-haiku-4-5-20251001`,
      `claude-mythos-5` e `claude-opus-4-8-fast` fora do conjunto de
      trabalho do ADR-149, e `gpt-5.6-sol` fora de `_VALID_MODELS`. Ou a
      cura entra nesta onda, ou o conjunto exato é publicado em arquivo
      rastreado, no molde do conjunto-vermelho da tabela de posse.
      Check: `python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt`

### Wave W2 — proposta auditada que toca SÓ a camada P

- [ ] `[P0][US5][.claude/data/models-preference.json]` A rotina abre um
      Pull Request que toca exclusivamente a camada P, carregando o
      relatório e os resumos criptográficos como evidência.
      Check: `python3 -m pytest .claude/scripts/tests/test_model_currency_proposal.py -q -k touches_only_preference`
- [ ] `[P0][US5][.claude/governance/models-registry.json]` **Controle
      POSITIVO do guarda certo.** O texto anterior mandava o lint
      `check-model-literals` ficar vermelho num Pull Request que tocasse
      a camada T — mas aquele lint varre literais em CÓDIGO e nunca
      acenderia num campo de JSON. Quem fica vermelho é o hook canônico.
      Check: `python3 -m pytest .claude/scripts/tests/test_model_currency_proposal.py -q -k trust_layer_edit_is_blocked`
- [ ] `[P0][US5]` **Egresso próprio da W2, declarado aqui e não herdado
      da W0b.** Destino: a interface de Pull Requests da forja. Corpo: o
      relatório e os resumos criptográficos, que são dados derivados do
      repositório. Redação: o redator do ADR-114 se aplica a ESTE corpo,
      porque aqui existe conteúdo a redigir.
      Check: `python3 -m pytest .claude/scripts/tests/test_model_currency_proposal.py -q -k body_is_redacted`
- [ ] `[P1][US5]` Conteúdo vindo de fonte externa nunca é colado cru no
      corpo do Pull Request: entra cercado e truncado, com o
      truncamento envenenando a dimensão dona.
      Check: `python3 -m pytest .claude/scripts/tests/test_model_currency_proposal.py -q -k untrusted_feed_is_fenced`
- [ ] `[P1][US5]` Fase 2 (fusão automática com janela de veto) fica FORA
      deste plano: só abre com ADR próprio e ratificação explícita do
      Owner.
      Check: none (fronteira de escopo — a prova é a ausência de qualquer AC de auto-merge acima)

### Wave W3 — advisory no boot e no relatório noturno

- [ ] `[P0][US6][.claude/skills/core/ceo-boot/SKILL.md]` O `/ceo-boot`
      mostra, por raia ativa, o trio {instalado, fixado, upstream} — e
      **nunca bloqueia**.
      Check: `python3 -m pytest .claude/scripts/tests/test_ceo_boot_model_currency.py -q`
- [ ] `[P0][US6]` Controle de que é advisory mesmo: com um upstream
      falso à frente do valor fixado, o boot continua com código de
      saída 0.
      Check: `python3 -m pytest .claude/scripts/tests/test_ceo_boot_model_currency.py -q -k advisory_never_blocks`
- [ ] `[P1][US6][.claude/skills/core/nightly-hygiene/SKILL.md]` A
      dimensão nova entra na varredura noturna por CONFIGURAÇÃO, não por
      identificador opaco. **O texto anterior ancorava a AC num
      identificador de gatilho truncado (`trig_014Y…`) que, medido,
      aparece só dentro do próprio plano** — âncora irrecuperável,
      substituída por esta.
      Check: `grep -q 'check-model-currency' .claude/skills/core/nightly-hygiene/SKILL.md`

## 4. Critérios de morte — cada um com arquivo, comando e dono

Todos os limiares em **ciclos da rotina**, nunca em dias de calendário.
Arquivo de estado único e rastreado: `.claude/data/model-currency-state.json`.
Comando de leitura único: `check-model-currency.py --state --json`.

| # | critério | limiar | dono |
|---|---|---|---|
| K-1 | falsos-positivos (proposta de lançamento inexistente) | > 2 em 8 ciclos ⇒ abertura automática desligada, vira relatório | CEO |
| K-2 | proposta tocando a camada T | qualquer ocorrência ⇒ vermelho fail-closed no CI | CEO |
| K-3 | feed velho ou parcial | mais velho que 4 ciclos, ou campo ausente ⇒ só relatório | CEO |
| K-4 | esquema do feed mudou (quebra do leitor) | qualquer ocorrência ⇒ fail-closed e rastro no log | CEO |
| K-5 | controle de falso-NEGATIVO | a cada 4 ciclos, lançamento conhecido injetado TEM de ser detectado; falhou ⇒ raia marcada morta | CEO |
| K-6 | falhas consecutivas de uma raia | 3 ciclos ⇒ raia desligada com alerta. **Declarado:** são 3 ciclos cego | CEO |
| K-7 | fase 2 (fusão automática) | só abre com ADR próprio ratificado | Owner |

## 5. Decisões que o round 1 exigiu e ficam registradas

- **`.claude/data/canonical_models.json` fica FORA desta classe, com
  razão medida.** Ele é a fonte de PREÇO sob o ADR-148, apontado por
  `canonical_models_ref` na tabela de preços — não é identidade nem
  preferência de modelo. Não é absorvido nem apagado por este plano. O
  que é verdade e não some: ele está expirado (`valid_until:
  2026-09-01`). Isso é defeito de preço e ganha follow-up próprio,
  `PLAN-176-FOLLOWUP-canonical-models-expiry`.
- **Custo declarado do resolver ser canônico.** Todo conserto no
  resolver custa uma cerimônia. Isso é consequência desejada do desenho
  — quem decide confiança fica sob assinatura — e não defeito. Fica
  escrito para que ninguém o descubra como surpresa.
- **Aritmética do orçamento, fechada.** Soma das ondas: W0a 60-90k,
  W0b 70-110k, W1a 80-120k, W1b 90-140k, W2 60-100k, W3 30-50k =
  **390-610k**, que é o valor do cabeçalho (o texto anterior somava
  350-550k contra um teto declarado de 300-550k). O valor em dólares
  do cabeçalho vem de: preço do Opus 5 na tabela de preços (5,00 de
  entrada e 25,00 de saída por milhão de tokens) e as proporções
  `blended_input_share: 0.80` / `blended_output_share: 0.20` do mesmo
  arquivo, o que dá 9,00 por milhão; 390k a 610k tokens ⇒ **3,51 a
  5,49 dólares**. Exclui contexto de subagentes e desconto de leitura
  de cache.
- **Nome do arquivo deste plano.** É
  `.claude/plans/PLAN-176-model-currency-refresh.md`. O caminho
  `.claude/plans/PLAN-176.md`, citado no material de abertura do
  debate, nunca existiu em disco.

## 6. Diferido para a rodada que preceder a W2

Dois achados do round 1 são reais e vivem na W2, que só abre depois da
W1b: conteúdo de feed como entrada não confiável terminando no corpo do
Pull Request (endereçado em parte pela AC `untrusted_feed_is_fenced`,
que a rodada deve re-verificar), e critério de morte auto-referente ao
ramo que a própria rotina escreve.

## 7. Fundamentação externa do split T/P (advisory, anexo S305)

A literatura de cascata e roteamento (linha 5 de
`PLAN-178/research-S305.md`) fundamenta a arquitetura do §3: roteamento
sensível a custo vive na camada de preferência, troca barata e
auditada, enquanto decisões de confiança ficam assinadas. Nada muda no
escopo; a referência entra no debate como evidência de que o split não
é idiossincrasia nossa.

## 8. Anexo — inventário S302d (não re-descobrir)

Bugs vivos: forma do revisor externo congelada em 0.139 contra binário
0.144.6 (três arquivos); `_VALID_MODELS` rejeita o substituto
recomendado pelo próprio registro de descontinuações; o adaptador vivo
da Anthropic sem a geração 5 na lista de modelos só-adaptativos; o
instrumento de substrato sem sonda de `grok` (débito PLAN-163:295); o
roteador de tarefas mandando detentores de VETO para literais; o recibo
de sucesso sem preço da geração 5. Rot: defaults de provedor com
`gpt-4o`; duas tabelas papel→modelo paralelas sem dono; cabeçalho de
versão da API em 6 arquivos; registro do substrato velho.
Fora da classe modelo: publicação em npm sobre Node 20 (fim de vida
desde 30/04); chave de assinatura fixa no script de release; executor
de CI sem alternativa em 6 lugares; versão de Python misturada entre
3.11 e 3.12; o verificador de workflows triplicado com uma cópia sem
resumo criptográfico.

## Progress log

- 2026-09-06 (S348, docs): **revisão executada.** Este texto absorve os
  16 must-fix do consenso do round 1
  (`PLAN-176/debate/round-1/consensus.md`, veredito `ESCALATE-TO-OWNER`)
  sob a decisão 4.14 do Owner («Autorizar a revisão do plano»,
  `PLAN-186/debate/owner-decisions-S347.md`). Mudou: ADR renumerado para
  **ADR-198** (próximo livre, medido); fetcher movido para um módulo
  canônico próprio em `.claude/hooks/_lib/` (oráculo = 1, cerimônia
  GPG), o que preserva a postura sem rede do ADR-136-AMEND-1 em vez de
  alterá-la; ondas cortadas em perna livre `a` e perna canônica `b`;
  camada T redefinida como TETO; conjunto de variáveis de ambiente
  fechado em um elemento; lista de destinos permitidos com dois pares
  host+caminho concretos; «fornecedor ativo» definido e medido em UMA
  raia; critérios de morte em ciclos com arquivo, comando e dono; 31
  caixas de seleção (5+6+4+8+5+3 nas seis ondas), cada uma com um
  `Check:` declarado — o texto anterior tinha zero de cada, medido
  pelas mesmas expressões do §13.2 do esquema de planos; aritmética
  de orçamento fechada em
  390-610k com estimativa em dólares e mistura de camadas. O conjunto
  vermelho do oráculo foi RE-MEDIDO e são **quatro** identificadores,
  não um.
  Check: none (doc-only — a revisão é o próprio texto)
- 2026-09-06 (S347, docs): **Decisão do Owner (item 4.14 de
  `PLAN-186/debate/owner-decisions-S347.md`, AskUserQuestion):**
  «Autorizar a revisão do plano (Recomendado)» — autoriza o pack docs:
  renumerar ADR, mover o fetcher para um módulo canônico próprio, W0a/W0b,
  e dar `Check:` a cada AC; a rodada 2 do debate roda depois dessa
  revisão. **Decisão derivada (item 4.10 do mesmo ledger):** o flip deste
  plano para `status: executing` só acontece DEPOIS da revisão landar —
  não volta a ser perguntado. `status:` permanece `reviewed` até lá.
  Check: none (doc-only)
