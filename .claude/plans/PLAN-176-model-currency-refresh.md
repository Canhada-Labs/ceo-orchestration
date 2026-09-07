---
id: PLAN-176
title: Currency de modelos — detectar lançamento novo; adoção nunca automática
status: executing
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169]
budget_tokens: 1.09-1.54M
budget_sessions: 6-8
budget_usd_estimate: "9.8-13.9 USD"
tier_mix_estimate: "CEO Opus 5 ~70% (plano, refutacao, cerimonia); builders Sonnet 5 ~25% (docs e testes); Haiku 4.5 ~5% (leituras) — a mistura vale sobre a metade de TRABALHO; o piso re-pago de gate-boot e 100% contexto do CEO (Opus 5)"
context_risk: high
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

> **Cura de 2026-09-07 (rodada 2 do debate).** Este texto absorve os 16
> ajustes do `.claude/plans/PLAN-176/debate/round-2/consensus.md`
> (veredito `RUN-ANOTHER-ROUND`, três críticos `ADJUST`). As mudanças de
> substância: o ADR sai de 198 (reivindicado por outro material) para
> **ADR-180**, por regra determinística publicada no §3.4; a W1b se
> re-corta em **W1b + W1c**, cada uma com a lista de caminhos igual ao
> conjunto das suas ACs; o arquivo de vermelhos-esperados e a bandeira
> que o lê **nascem na W0a**, que é livre; a **W3 ganha pernas a/b**
> porque um dos seus dois alvos reais é canônico; as promessas de
> auditoria do §3 e da W0b **degradam para os campos que a taxonomia
> fechada carrega**, com a rota cara nomeada como **OQ** (*open
> question* — pergunta que só o Owner responde; as três deste plano
> estão no §5b, cada uma com a rota barata já executada ao lado da cara
> e do que a cara custa); e o orçamento
> passa a incluir o piso de gate-boot re-pago. `status:` permanece
> `reviewed` — o flip é a decisão 4.10 do Owner e não é matéria desta
> cura.

## 0. A dependência dura do PLAN-169, nomeada

`depends_on: [PLAN-169]` era um identificador nu. O entregável concreto
é a **W4.3 / W4-C — a parte de DECISÃO do fleet-currency**
(`.claude/plans/PLAN-169-closure-and-cross-session-evolution.md:661-675`),
e dela dois itens:

- **(i) F1-P1** — os perfis passam a ter alvo na geração corrente com o
  **mapa DERIVADO da autoridade ADR-149**. É a mesma autoridade de que
  a camada T deste plano é o registro; sem ela, o registro T deste plano
  seria uma segunda tabela paralela, exatamente o defeito que o
  PLAN-169 nomeia («duas tabelas papel→modelo paralelas sem dono»).
- **(iv)** — a **dimensão `fleet-currency` no `nightly-hygiene`**
  (manifesto de superfícies portadoras de identificador de modelo +
  oráculo por superfície). É a superfície que a W3b deste plano estende.

Palavra do Owner na abertura daquela wave (S315, registrada em
`PLAN-169:721`): «É o gargalo de 170, 174, **176** e 181.»

**O que espera e o que não espera.** Medido:
`grep -n '^status:' .claude/plans/PLAN-169-closure-and-cross-session-evolution.md`
⇒ `status: executing`. Decisão de sequenciamento deste plano:

- **W0a, W0b, W1a, W1b, W1c, W2a e W3a NÃO esperam** o fechamento do
  PLAN-169. Nenhuma delas toca as superfícies do fleet-currency; a
  camada T é criada aqui e é derivada do ADR-149 diretamente.
- **Só a W3b espera o item (iv)**, porque é ela que adiciona uma
  dimensão ao mesmo arquivo de varredura noturna. Abrir a W3b antes é
  editar um arquivo que outra wave está reescrevendo — a classe do
  baseline vivo, que este repositório já pagou na S329.

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
- **Ciclo.** Uma execução da rotina de detecção — uma execução da
  varredura noturna (`.claude/workflows/nightly-hygiene.js`), a mesma
  que já carrega as nove dimensões existentes. É a unidade em que este
  plano expressa limiar de QUALIDADE.
- **Cadência, e por que ela não é opcional.** A varredura noturna é
  **invocada pelo operador**, não por `cron`: medido,
  `grep -c 'schedule:' .claude/workflows/nightly-hygiene.js` = 0, e o
  arquivo é um script de Workflow, não um workflow do GitHub Actions.
  Logo a taxa-alvo é declarada, não garantida: **um ciclo por 24 h**.
  A consequência é mecânica e o round 2 a nomeou: um limiar contado só
  em ciclos é **infalsificável** quando a rotina PARA — zero execuções
  nunca cruzam «3 ciclos». Por isso todo limiar deste plano tem **duas
  pernas**: a perna de ciclos (qualidade da detecção) e uma **perna de
  relógio de parede** ancorada no campo `ts` que cada ciclo grava em
  `.claude/data/model-currency-state.json` (§4). A perna de relógio é a
  única que enxerga a rotina morta.

## 2. A tese central, medida (o que o round 1 confirmou)

O split T/P preserva a cerimônia **por construção**, sem alargar a
lista de guardas do hook canônico. Medido com o oráculo acima —  que
decide por **PADRÃO de caminho**, não por conteúdo de arquivo. É por
isso que a tabela é verificável ANTES de existir código, e é também o
seu limite: **8 destes 10 caminhos ainda não existem em disco**
(existem hoje só `gate-scripts-manifest.txt` e `validate.yml`; medido
com `ls`). Os dez vereditos, reproduzíveis com
`python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>`:

    .claude/governance/models-registry.json      1   (T — exige assinatura)
    .claude/hooks/_lib/model_registry.py         1   (resolver — exige assinatura)
    .claude/hooks/_lib/model_feed_fetch.py       1   (fetcher — exige assinatura)
    .claude/adr/ADR-180-...md                    1   (o ADR — exige assinatura)
    .claude/governance/gate-scripts-manifest.txt 1   (manifesto — exige assinatura)
    .github/workflows/validate.yml               1   (CI — exige assinatura)
    .claude/data/models-preference.json          0   (P — Pull Request livre)
    .claude/scripts/check-model-literals.py      0   (lint — Pull Request livre)
    .claude/scripts/check-model-currency.py      0   (detector — Pull Request livre)
    .claude/hooks/tests/test_model_feed_fetch.py 0   (teste — Pull Request livre)

Três vereditos que o round 2 acrescentou e que MUDAM o corte das ondas
(medidos do mesmo modo):

    .claude/hooks/_lib/tests/test_model_registry.py  1  (o teste do resolver TAMBÉM é canônico)
    .claude/workflows/nightly-hygiene.js             1  (a varredura noturna é canônica ⇒ a W3 se parte em W3a/W3b)
    .claude/data/model-currency-expected-reds.txt    0  (o conjunto-vermelho é livre ⇒ nasce na W0a)

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

**O que esse evento consegue carregar — e o que ele NÃO carrega.** O
texto anterior prometia gravar «o identificador recusado e a origem que
o pediu». Medido, o allowlist fechado do action
(`.claude/hooks/_lib/audit_emit.py:1601-1608`) é exatamente
`{action, ts, session_id, project, event_schema, tokens_in, tokens_out,
tokens_total, hmac, hmac_error, archetype, mode, recommended_model,
killswitch_armed, decision}` — **não há campo para o identificador
recusado nem para a origem**, e o scrub os descarta antes do fio.
A promessa fica sendo a que sobrevive ao scrub: o evento registra QUE
houve recusa (`decision`) e QUAL identificador foi servido no lugar
(`recommended_model`); o identificador recusado e a origem vivem no
relatório do detector, **fora** da cadeia HMAC. Consequência declarada:
a forense de «quem pediu o quê» não é respondida pelo log — é
respondida pelo relatório, que não é à prova de adulteração.

> **OQ-2 (Owner).** A rota cara existe e está precificada: emendar o
> allowlist em `.claude/hooks/_lib/audit_emit.py` (oráculo = **1**,
> medido) somaria **+1 caminho canônico e +1 assinatura** à onda que a
> fizesse, e traria a forense para dentro da cadeia. A rota barata é a
> degradação acima. Este plano executa a barata enquanto o Owner não
> escolher a cara; nenhuma onda abre com a decisão pendente porque a
> forma degradada já é executável.

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
`model_choice_recommended` com **`fell_back_to_static: true`**. Quem
lê: o `/ceo-boot` (advisory da onda W3a) e o relatório noturno.

**Por que `fell_back_to_static` e não «o motivo».** O texto anterior
prometia gravar o MOTIVO da degradação. Medido, o allowlist do action
(`.claude/hooks/_lib/audit_emit.py:1359-1362`, sobre o envelope
`_OPTIMIZER_ENVELOPE = ("action", "session_id")` da linha 1349) é
`{action, session_id, subtask_index, model_recommended,
confidence_basis_points, cost_governed, fell_back_to_static}` — **não
existe campo de motivo**, e o scrub (`:5290-5291`) dropa o que sobra,
deixando apenas um breadcrumb. `fell_back_to_static` é o único campo
que carrega o FATO da degradação; o motivo em texto vive no relatório
do detector. Vale aqui a mesma OQ-2 do §3.1: emendar o allowlist é
cerimônia, e este plano não a gasta sem decisão do Owner.

### 3.4 Onde a doutrina T/P ganha autoridade

Hoje ela **não tem** autoridade em disco: o §1 do texto anterior a
citava como «decidida no ADR-149 Amendment 2», mas esse número está
ocupado por material que o Owner assinou (`ADR-149-model-id-allowlist.md:209`,
cerimônia `wave-fable51`). Correção:

- O rascunho `PLAN-176/adr-149-amendment2-draft.md` vira
  **`.claude/adr/ADR-180-model-trust-preference-split.md`**, um ADR
  próprio.
- Enquanto o ADR-180 não estiver `ACCEPTED`, **nenhum trecho deste
  plano cita a doutrina T/P como decidida.** Ela é uma proposta deste
  plano, ratificada na onda W1b.

**Por que 180 e não 198 — a aritmética anterior era inválida.** O texto
anterior escolhia 198 por «o diretório tem 198 arquivos, logo 198 está
livre». Isso não se sustenta em nenhum dos dois lados:

- **O antecedente é falso e a inferência também.** Medido:
  `ls .claude/adr | grep -cE '^ADR-[0-9]{3}-'` = **197 arquivos**, mas
  só **175 números distintos** — 22 arquivos compartilham um número já
  usado (a família `AMEND`, entre outros). Contar ARQUIVOS nunca
  respondeu «qual número está livre».
- **198 já estava reivindicado por outro material.** Medido:
  `grep -rn 'ADR-198' .claude/plans/` acusa
  `.claude/plans/PLAN-186/debate/round-4/proposal.md:133`
  (`ADR-198-spawn-step0-dependency-and-fixed-cost.md`), consumido pelo
  consenso daquela mesma rodada (`round-4/consensus.md:137,178`). O
  teste do «próximo livre» é o mesmo para os dois planos: os dois o
  passam e colidem no land. **199 e 200 também estão falados** —
  `ADR-199-cross-terminal-coordination.md` no mesmo `proposal.md:134`,
  e `ADR-200-shared-ceremony-toolkit.md` em
  `.claude/plans/PLAN-188/debate/round-3/`.

**A regra que substitui a aritmética, e é reproduzível.** O número
deste plano é *o maior número livre ≤ 197 com ZERO menção em qualquer
arquivo do repositório* — livre porque nenhum arquivo o usa, e sem
menção porque nenhum plano o reservou em texto. Derivação, gerada e não
digitada:

```
python3 - <<'PY'
import os, re, subprocess
usados = {int(m.group(1)) for f in os.listdir('.claude/adr')
          if (m := re.match(r'^ADR-(\d{3})-', f))}
livres = [n for n in range(1, 198) if n not in usados]
zero = [n for n in livres
        if not subprocess.run(['grep', '-rl', 'ADR-%03d' % n,
                               '--exclude-dir=.git', '.'],
                              capture_output=True, text=True).stdout.strip()]
print(len(livres), livres); print(len(zero), zero); print(max(zero))
PY
```

Saída medida em HEAD: **22 livres** `[68, 130, 134, 166-180, 184, 187,
188, 189]`; **13 com zero menção** `[68, 166, 167, 168, 169, 170, 171,
172, 176, 177, 178, 179, 180]`; escolhido **180**.

**A reserva é o próprio pacote, não esta linha.** A lição que o round 2
extraiu é que alocação de número de ADR não é medição local por plano —
uma medição verdadeira hoje colide amanhã. Portanto o número só fica
reservado quando o arquivo `PROPOSED` aterrissa no MESMO pacote que o
cita (a W1b), e a AC do ADR carrega a checagem de colisão.

## Waves

> **Regra de leitura (corrigida na rodada 2).** A perna `a` é livre
> (Pull Request auditado); a perna `b` é canônica (assinatura GPG do
> Owner). **Quando as duas existem, a livre aterrissa primeiro** — é o
> que a ordem W1a → W1b exige por razão mecânica (o manifesto não pode
> fixar o byte de um arquivo que ainda não existe). Uma onda pode ter
> **só** a perna `a` (nenhum caminho canônico) ou **só** a perna `b`; o
> texto anterior dizia «em cada onda a perna `a`… a perna `b`…», o que
> lia como se toda onda tivesse as duas — e W2/W3 não tinham nenhuma
> declarada. Toda onda abaixo declara agora: uma linha `Paths:` com o
> conjunto EXATO dos caminhos que ela toca, o veredito do oráculo em
> cada um, e a que perna pertence. Cada caixa de seleção declara o
> comando cujo código de saída a fecha, e esse comando fica VERMELHO na
> condição que a caixa proíbe.

### Wave W0a — detecção OFFLINE (livre, zero rede)

Compara o que o Owner assinou (os dois blocos do ADR-149) contra as
tabelas locais do repositório e reporta divergência. **Não faz nenhuma
requisição de rede.** É a onda mais barata e a que sozinha já responde
"apareceu identificador novo em alguma superfície?".

Paths (4, todos com oráculo = 0 — medido):
`.claude/scripts/check-model-currency.py`,
`.claude/data/model-currency-state.json`,
`.claude/data/model-currency-expected-reds.txt`,
`.claude/scripts/tests/test_check_model_currency.py`. Nenhum existe em
HEAD: **os quatro são CRIADOS por esta onda.** O diretório de testes
está em `pytest.ini` `testpaths` (`.claude/scripts/tests`, linha 41),
logo tudo o que as caixas abaixo invocam é coletável.

- [ ] `[P0][US1][.claude/scripts/check-model-currency.py]` O detector lê os
      blocos `VETO_FLOOR_ALLOWED` e `AVAILABLE_MODELS_WORKING_SET` do
      ADR-149 e os compara com `cost-table.yaml`,
      `model-deprecations.json` e `settings.json`; divergência sai como
      achado NOMEADO (identificador, superfície e autoridade que
      diverge), nunca como diferença crua. **O código de saída separa
      EXECUÇÃO de ACHADO** — `0` executou sem achado, `1` executou com
      achado, `≥2` o detector quebrou — e a asserção do achado é do
      teste, não do `$?`.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k names_the_finding_and_separates_exit_codes`
- [ ] `[P0][US1][.claude/scripts/check-model-currency.py]` **Controle
      NEGATIVO de rede por oráculo de RUNTIME, não por texto.** O
      detector roda com `socket.socket` e `socket.create_connection`
      substituídos por uma função que levanta; a execução completa. O
      **controle POSITIVO reproduz o MECANISMO** que derrota um `grep`
      de nomes: um módulo sintético que adquire egresso por importação
      transitiva (`from _lib import model_feed_fetch`) faz o MESMO
      oráculo ficar VERMELHO.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k no_network_runtime_oracle_with_transitive_import_control`
- [ ] `[P0][US1][.claude/scripts/check-model-currency.py]` Controle
      POSITIVO da detecção: injetar um identificador falso
      (`claude-opus-6`) no bloco do ADR numa cópia descartável faz o
      detector ficar VERMELHO; sem a injeção, VERDE.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k injected_model_turns_red`
- [ ] `[P1][US1][.claude/data/model-currency-state.json]` O estado de
      cada ciclo é gravado em arquivo RASTREADO pelo git, com o número
      do ciclo, o resultado por raia, a soma de falsos-positivos **e o
      carimbo `ts` do relógio de parede** (§1 — é a perna que enxerga a
      rotina parada). O teste assere os quatro campos, não só que o
      arquivo é JSON válido.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k state_file_contract_has_cycle_lanes_fp_and_ts`
- [ ] `[P0][US1][.claude/scripts/check-model-currency.py]` **A bandeira
      de leitura `--state --json` existe e serve os SETE critérios de
      morte.** É o comando único do §4: o teste enumera os sete
      critérios e assere que cada um encontra o seu campo na saída. Um
      critério sem campo deixa a caixa VERMELHA — que é o defeito que a
      rodada 2 encontrou (o comando era declarado e não era exercido
      por caixa nenhuma).
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k state_json_serves_all_seven_death_criteria`
**O conjunto VERMELHO conhecido, e por que ele mudou de onda.** O texto
anterior punha esta caixa na perna canônica da W1b, invocando um arquivo
que onda nenhuma criava e uma bandeira que AC nenhuma declarava — a
caixa nascia permanentemente vermelha. O arquivo é livre (oráculo = 0,
medido), o detector que o lê nasce aqui, e portanto o lugar dele é a
W0a. O conteúdo do achado não muda: o oráculo `replacements ⊆
valid_override_ids` como escrito no texto original é um **erro de
categoria** — compara substitutos Anthropic contra `_VALID_MODELS`, que
é a lista de revisores da linha OpenAI. Na forma correta, por família de
fornecedor, **quatro identificadores estão vermelhos hoje**:
`claude-haiku-4-5-20251001`, `claude-mythos-5` e `claude-opus-4-8-fast`
fora do conjunto de trabalho do ADR-149, e `gpt-5.6-sol` fora de
`_VALID_MODELS`. Publicados, não escondidos.

- [ ] `[P1][US1][.claude/data/model-currency-expected-reds.txt]` **O
      conjunto VERMELHO conhecido nasce aqui, em arquivo rastreado**, no
      molde de `scripts/tests/ownership-expected-reds.txt` (comentários
      com a causa de cada linha; uma linha por identificador). Ele é
      livre (oráculo = 0), e por isso NÃO entra no pacote assinado da
      W1b — foi o defeito nomeado pelo round 2.
      Check: `git ls-files --error-unmatch .claude/data/model-currency-expected-reds.txt && python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k expected_reds_file_has_a_cause_per_line`
- [ ] `[P0][US1][.claude/scripts/check-model-currency.py]` **A bandeira
      `--expected-reds` compara o conjunto EXATO e falha em QUALQUER
      diferença — inclusive encolhimento**, como o
      `ownership-nightly-gate.sh` faz: um vermelho que some sem
      explicação é motivo para PARAR, não para comemorar
      (`CLAUDE.md` §4). O controle positivo planta um identificador a
      mais e outro a menos, e as duas plantas ficam VERMELHAS.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k expected_reds_exact_set_with_shrinkage_control`
- [ ] `[P1][US1][.claude/scripts/check-model-currency.py]` **A raia de um
      fornecedor só abre se ele for ATIVO**, definido como: membro do
      conjunto de trabalho do ADR-149 **e** com linha de preço em
      `cost-table.yaml`. Fornecedor sem linha de preço é INERTE por
      construção — fail-closed, nunca uma raia que reporta vazio. Medido
      nesta revisão: a tabela de preços tem 12 identificadores, todos
      `claude-*`; zero `gpt`, zero `gemini`, zero `grok`. **Na abertura,
      portanto, existe exatamente UMA raia ativa: Anthropic.**
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_currency.py -q -k active_lanes_is_anthropic_only`

**Ponto cego declarado do oráculo de runtime.** Ele prova os caminhos de
código que o teste EXERCITA, não o arquivo inteiro. Um ramo nunca
exercitado pode abrir soquete sem que o oráculo o veja. É estreitamente
melhor que o `grep` de nomes — que a própria W0b ensinaria a contornar,
porque `from _lib import model_feed_fetch` não casa o padrão — e é o
que `CLAUDE.md` §5 registra como a cura conhecida da classe
«instrumento que prevê código por TEXTO não converge». O residual fica
escrito para que ninguém o descubra como surpresa.

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

**«Nunca de dentro de um agente» é CONVENÇÃO DECLARADA, não portão — e
esta linha é a correção.** O round 2 mostrou que a frase não tinha
mecanismo: o módulo mora em `.claude/hooks/_lib/`, importável por todo
hook, e nenhuma AC verificava o chamador. Procurei um marcador de
contexto de agente para construir o portão e **não existe**: medido,
`grep -rn 'CLAUDE_AGENT\|is_subagent\|agent_context' .claude/hooks/_lib/*.py`
= 0 ocorrências. Sem marcador, um portão só pode ser adivinhado, e um
portão adivinhado é pior que nenhum. Portanto a doutrina fica rebaixada
ao que o repositório já faz com o piso VETO (`CLAUDE.md` §5, S343+S344:
«piso VETO = convenção + detector, não gate»): **convenção declarada,
com o interruptor desligado por padrão como a defesa REAL** — sem a
bandeira, nenhum chamador (agente ou não) abre soquete. Construir o
portão de verdade exige primeiro um marcador de contexto no substrato,
que é escopo de outro plano.

**O interruptor tem nome e camada: `--enable-upstream-fetch`, bandeira
de linha de comando.** Não é variável de ambiente, e isso é decisão, não
acaso: o §3.2 fecha o conjunto de variáveis em **exatamente**
`{CEO_MODEL_PREFERENCE}`, e um interruptor em `env` ou tornaria aquela
frase falsa ou deixaria o fetcher sem forma de ser ligado. Fica
registrado que o conjunto fechado do §3.2 descreve a superfície de
ambiente **do resolver**; o fetcher não acrescenta nenhuma variável a
ela.

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
— a onda W2a declara o egresso dela em separado. A citação do ADR-114
sai do lugar de controle de egresso: aquele ADR redige prompts enviados
a um modelo externo, e um `GET` sem corpo não tem o que redigir. Fica,
no máximo, como nota de simetria.

**O que o LOG consegue guardar do egresso — e o que ele não guarda.**
O texto anterior prometia um evento «com host e caminho». Medido, isso é
impossível sem emenda canônica: o allowlist fechado do action
(`.claude/hooks/_lib/audit_emit.py:8480-8488`) é
`{action, session_id, project, egress_class, destination, ts,
event_schema, tokens_in, tokens_out, tokens_total, hmac, hmac_error}`, e
o valor de `destination` passa por `_coerce_egress_destination`
(`:8506-8531`), que **corta em `/`, `?` e `#`** e devolve host nu. Como
os dois destinos permitidos têm o MESMO host e diferem só no caminho,
**o log não distingue qual dos dois foi buscado** — e não há como
distingui-los sem campo novo. Consequência declarada: a evidência do
CAMINHO vive no relatório do fetcher, fora da cadeia HMAC; o que a
cadeia carrega é host + `egress_class` (`network_http`, valor do enum
fechado de `:8495-8498`) + a decisão. Vale aqui a **OQ-2** do §3.1: a
rota cara é emendar `_lib/audit_emit.py` (oráculo = 1) e traz +1
caminho canônico e +1 assinatura a esta onda.

Paths (2): `.claude/hooks/_lib/model_feed_fetch.py` (oráculo = **1**,
canônico — é o que faz da onda uma cerimônia) e
`.claude/hooks/tests/test_model_feed_fetch.py` (oráculo = **0**, e o
`pytest.ini` o coleta, linha 39). Nenhum dos dois existe em HEAD: os
dois são criados aqui. `.claude/scripts/check-substrate-watch.py`
aparece numa caixa abaixo como alvo **somente de leitura** — a onda não
o edita, e por isso ele não é caminho do pacote. O fetcher também
ESCREVE `.claude/data/model-currency-upstream-cache.json`, que a W3a lê:
é artefato de tempo de execução, **não rastreado**, e por isso também
não é caminho do pacote.

- [ ] `[P0][US2][.claude/hooks/_lib/model_feed_fetch.py]` O fetcher nasce
      DESLIGADO: sem a bandeira `--enable-upstream-fetch`, ele não abre
      soquete e retorna "desabilitado". O controle positivo substitui
      `socket.socket` por uma função que levanta e prova que a chamada
      padrão completa mesmo assim.
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k disabled_by_default_opens_no_socket`
- [ ] `[P0][US2][.claude/hooks/_lib/model_feed_fetch.py]` A lista de
      destinos permitidos é constante no módulo e casa o par **(host,
      caminho)**; destino fora dela é recusado NOMEADAMENTE. **O
      redirecionamento é re-casado contra o par inteiro, não só contra o
      host** — um `302` do mesmo host para outro caminho é recusado,
      que era metade da allowlist escapando.
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k allowlist_matches_host_and_path_including_redirect`
- [ ] `[P0][US2][.claude/hooks/_lib/model_feed_fetch.py]` Cada despacho
      emite `egress_destination_detected` com **host e `egress_class`** —
      ação já existente na taxonomia fechada, nenhuma ação nova, nenhum
      campo novo. O teste assere os campos que SOBREVIVEM ao scrub e
      assere também que o caminho **não** aparece no evento gravado (é o
      controle de que a promessa degradada é a verdadeira).
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k emits_egress_event_without_path`
- [ ] `[P0][US2][.claude/hooks/_lib/model_feed_fetch.py]` **A RECUSA de
      destino também é auditada.** Um destino fora da allowlist emite
      `egress_destination_detected` com o host recusado e a decisão —
      sem isso o caso forense que mais interessa («alguém tentou um
      destino fora da lista») ficava sem rastro na cadeia HMAC.
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k refused_destination_emits_event`
- [ ] `[P0][US2][.claude/hooks/_lib/model_feed_fetch.py]` **Tempo-limite e
      verificação de certificado.** Toda requisição tem tempo-limite
      explícito (conexão e leitura); a verificação de certificado do
      contexto TLS padrão — *Transport Layer Security*, a camada de
      cifra do HTTPS — é exigida, e um contexto sem verificação faz o
      teste ficar VERMELHO.
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k explicit_timeout_and_certificate_verification`
- [ ] `[P0][US2][.claude/scripts/check-substrate-watch.py]` Controle de
      NÃO-REGRESSÃO da postura, por oráculo de RUNTIME: o instrumento
      que se declara sem rede roda com `socket.socket` substituído por
      uma função que levanta e completa. O `grep` de nomes que este
      plano usava antes fica como sinal complementar — sozinho ele é
      cego a `from _lib import model_feed_fetch`, que é exatamente o que
      esta onda passa a oferecer.
      Check: `python3 -m pytest .claude/hooks/tests/test_model_feed_fetch.py -q -k substrate_watch_no_network_runtime_oracle`
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
nasce aqui, livre, e só na W1c entra no manifesto e no CI.

Paths (5, todos com oráculo = 0 — e a lista é o conjunto EXATO dos
caminhos que as caixas abaixo tocam ou invocam):
`.claude/data/models-preference.json`,
`.claude/scripts/check-model-literals.py`,
`.claude/scripts/model-literals-grandfather.txt`,
`.claude/scripts/tests/test_model_preference.py`,
`.claude/scripts/tests/test_check_model_literals.py`. Nenhum existe em
HEAD: os cinco são criados aqui.

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

**Por que esta onda foi re-cortada.** O texto anterior dizia «cinco
caminhos canônicos» e as suas ACs exigiam **nove** — duas seções do
mesmo plano com números diferentes, e um pacote acima do teto de oito
do modelo de operação v2. Além disso o registro T era declarado no
pacote e **não tinha AC nenhuma**. O corte agora é: **W1b** leva o que
decide CONFIANÇA (registro T, resolver, ADR), **W1c** leva o que fia o
PORTÃO (manifesto e CI). Duas assinaturas em vez de uma; a razão é que
a W1c tem uma dependência de ordenação que a W1b não tem (ver lá).

Paths (4 canônicos, oráculo = **1** nos quatro — medido), e esta lista é
o conjunto EXATO dos caminhos que as caixas abaixo editam:
`.claude/governance/models-registry.json`,
`.claude/hooks/_lib/model_registry.py`,
`.claude/hooks/_lib/tests/test_model_registry.py`,
`.claude/adr/ADR-180-model-trust-preference-split.md`. Nenhum existe em
HEAD: os quatro são criados aqui. **Atenção ao terceiro** — o teste do
resolver também é canônico (`.claude/hooks/_lib/tests/` está sob o
guarda), ao contrário dos testes em `.claude/scripts/tests/`; o texto
anterior o tratava como livre.

Material de cerimônia (livre, oráculo = 0, no molde
`PLAN-169/wave-*-approved.md`): `.claude/plans/PLAN-176/wave-w1b-approved.md`
e o `.asc` do Owner sobre ele.

- [ ] `[P0][US4][.claude/governance/models-registry.json]` **O registro T
      existe, é rastreado e é DERIVADO** dos dois blocos do ADR-149 —
      nunca uma segunda tabela digitada à mão. O controle positivo
      altera um dos blocos do ADR numa cópia descartável e prova que o
      registro derivado muda junto; um registro que não muda fica
      VERMELHO.
      Check: `python3 -m pytest .claude/hooks/_lib/tests/test_model_registry.py -q -k trust_registry_is_derived_from_adr149_with_divergence_control`
- [ ] `[P0][US4][.claude/adr/ADR-180-model-trust-preference-split.md]` O
      ADR-180 entra `PROPOSED` no pacote; o flip para `ACCEPTED` é o
      arquivo `.asc` assinado, nunca o commit que reescreve o campo. **O
      comando fica VERMELHO exatamente na condição que a caixa proíbe**
      — `ACCEPTED` sem `.asc` rastreado:
      Check: `f=.claude/adr/ADR-180-model-trust-preference-split.md; grep -qx 'status: PROPOSED' "$f" || { grep -qx 'status: ACCEPTED' "$f" && git ls-files --error-unmatch .claude/plans/PLAN-176/wave-w1b-approved.md.asc; }`
- [ ] `[P0][US4][.claude/adr/ADR-180-model-trust-preference-split.md]`
      **A reserva do número é verificada no pacote, não confiada ao
      texto.** Nenhum outro arquivo `ADR-180-*` existe e nenhum outro
      plano reserva 180 — a checagem roda no momento do land, porque uma
      medição verdadeira na véspera colide no dia (§3.4).
      Check: `test "$(ls .claude/adr | grep -c '^ADR-180-')" -eq 1 && test "$(grep -rl 'ADR-180' .claude/plans --exclude-dir=debate | grep -vc 'PLAN-176')" -eq 0`
- [ ] `[P0][US4][.claude/hooks/_lib/model_registry.py]` O resolver aplica
      a camada T como TETO (§3.1): identificador fora do conjunto é
      recusado mesmo quando pedido por quem chamou, e a recusa emite
      `model_routing_enforced` com os campos que o allowlist carrega
      (§3.1 — `decision` e `recommended_model`; o identificador recusado
      NÃO sobrevive ao scrub, e o teste assere essa ausência).
      Check: `python3 -m pytest .claude/hooks/_lib/tests/test_model_registry.py -q -k ceiling_rejects_caller_and_refused_id_is_scrubbed`
- [ ] `[P0][US4][.claude/hooks/_lib/model_registry.py]` O conjunto de
      variáveis de ambiente é fechado em um elemento e a gramática do
      valor recusa caminho (§3.2), emitindo `env_var_hijack_blocked`.
      Check: `python3 -m pytest .claude/hooks/_lib/tests/test_model_registry.py -q -k "closed_env_set or env_value_grammar"`
- [ ] `[P0][US4][.claude/hooks/_lib/model_registry.py]` Sem rede e só
      biblioteca padrão — **por oráculo de RUNTIME**, como na W0a: o
      resolver roda com `socket.socket` substituído por uma função que
      levanta e completa; o controle positivo planta a importação
      transitiva do fetcher e prova VERMELHO. O `grep` de nomes que o
      texto anterior usava não casa `from _lib import model_feed_fetch`,
      que é o caminho que a W0b passa a oferecer.
      Check: `python3 -m pytest .claude/hooks/_lib/tests/test_model_registry.py -q -k no_network_runtime_oracle_with_transitive_import_control`
- [ ] `[P0][US4][.claude/hooks/_lib/tests/test_model_registry.py]`
      **Teste-mestre do split**, com os dois controles: um identificador
      falso injetado no registro T aparece em todas as superfícies da
      camada P sem uma linha de código editada, e o oráculo confirma que
      o arquivo T exige assinatura enquanto o P não.
      Check: `python3 -m pytest .claude/hooks/_lib/tests/test_model_registry.py -q -k split_oracle_contract`

### Wave W1c — manifesto de portões e fiação no CI (canônica, UMA assinatura)

Esta onda é separada da W1b por uma razão de ORDENAÇÃO, não de tamanho.
Medido: `grep -vc '^#' .claude/governance/gate-scripts-manifest.txt` =
**9 membros** hoje, e o Owner já autorizou outro pacote que leva o mesmo
arquivo de **9 para 12** (decisão 4.8 de
`.claude/plans/PLAN-186/debate/owner-decisions-S347.md:21`, pack
`w4b-ci-matrix`; prioridade de WIP canônico W1 → W6a → W4b na decisão
4.17, `:55`). É a classe que este repositório já pagou na S329 — «enquanto
um pack baseado em manifesto espera assinatura, nenhum destino
pré-existente dele pode ser editado; o BASELINE é o hash do vivo». Por
isso, declarado:

- **A W1c só abre depois do land do `w4b-ci-matrix`.** A W1b não espera
  nada disso — foi o ganho do re-corte.
- **O baseline do manifesto é re-derivado no momento do SIGN**, nunca
  copiado do material escrito antes.

Paths (4): `.claude/governance/gate-scripts-manifest.txt` (oráculo = 1),
`.github/workflows/validate.yml` (oráculo = 1),
`.claude/scripts/tests/test_gate_scripts_manifest.py` (oráculo = 0),
`.claude/scripts/tests/test_check_model_literals.py` (oráculo = 0 — é
editado aqui para ganhar o caso `wired_into_ci`; nasceu na W1a). O
pacote mistura material canônico e livre de propósito: o teste que prova
o bump tem de aterrissar com o bump, senão nasce vermelho.

Material de cerimônia: `.claude/plans/PLAN-176/wave-w1c-approved.md` e
o `.asc` do Owner sobre ele.

- [ ] `[P0][US4][.claude/governance/gate-scripts-manifest.txt]` O lint da
      W1a entra no manifesto com o resumo criptográfico do byte que
      aterrissou, e a verificação do manifesto passa.
      Check: `python3 -m pytest .claude/scripts/tests/test_gate_scripts_manifest.py -q`
- [ ] `[P0][US4][.claude/governance/gate-scripts-manifest.txt]`
      **Controle da ordenação contra o `w4b-ci-matrix`.** O teste lê a
      contagem de membros do manifesto VIVO e recusa aterrissar sobre um
      baseline que não é o do disco — um material escrito quando o
      manifesto tinha 9 e aplicado quando tem 12 fica VERMELHO.
      Check: `python3 -m pytest .claude/scripts/tests/test_gate_scripts_manifest.py -q -k baseline_is_rederived_from_live_manifest`
- [ ] `[P0][US4][.github/workflows/validate.yml]` O lint roda no CI como
      passo próprio, e o passo aparece no arquivo de validação.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_literals.py -q -k wired_into_ci`
- [ ] `[P0][US4][.github/workflows/validate.yml]` **O critério de morte
      K-2 tem instrumento fiado.** Uma proposta que toque a camada T
      aparece como passo VERMELHO fail-closed no arquivo de validação —
      sem isto, K-2 é declaração e não catraca.
      Check: `python3 -m pytest .claude/scripts/tests/test_check_model_literals.py -q -k k2_trust_layer_touch_is_red_in_ci`

### Wave W2a — proposta auditada que toca SÓ a camada P (livre; perna única)

**Perna única `a`.** Nenhum caminho desta onda é canônico, logo ela não
tem perna `b` e não pede assinatura. Os dois arquivos de camada citados
nas tags abaixo (`models-preference.json`, `models-registry.json`) já
existirão — o primeiro nasce na W1a, o segundo na W1b — e aqui são
**alvo de controle**, não caminho editado.

Paths (2, oráculo = 0 nos dois — medido; nenhum existe em HEAD, os dois
são criados aqui): `.claude/scripts/model-currency-propose.py`,
`.claude/scripts/tests/test_model_currency_proposal.py`.

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
- [ ] `[P0][US5]` **Egresso próprio da W2a, declarado aqui e não herdado
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

### Wave W3a — advisory no boot (livre)

**Os alvos mudaram, e a razão é que os antigos não existem.** O texto
anterior citava `.claude/skills/core/ceo-boot/SKILL.md` e
`.claude/skills/core/nightly-hygiene/SKILL.md`. Medido:
`ls -d .claude/skills/core/ceo-boot .claude/skills/core/nightly-hygiene`
⇒ *No such file or directory* nos dois; o `grep -q` contra o segundo
saía com código 2 e a caixa nascia **permanentemente vermelha** — a cura
do must-fix 15 do round 1 tinha trocado uma âncora irrecuperável por
outra. O que existe e é rastreado (`git ls-files`):
`.claude/scripts/ceo-boot.py`, `.claude/commands/ceo-boot.md` e
`.claude/workflows/nightly-hygiene.js`.

Paths (3, oráculo = 0 nos três — medido):
`.claude/scripts/ceo-boot.py` e `.claude/commands/ceo-boot.md` (os dois
EXISTEM em HEAD e são editados aqui),
`.claude/scripts/tests/test_ceo_boot_model_currency.py` (criado aqui).

**O artefato de cache que o boot lê, nomeado.** O `/ceo-boot` roda
dentro da sessão do CEO e **não busca nada** — se buscasse, quebraria a
convenção da W0b. Ele lê
`.claude/data/model-currency-upstream-cache.json` (oráculo = 0). Ele é
**artefato de tempo de execução, NÃO rastreado pelo git** e por isso não
é caminho de onda nenhuma: quem o escreve é o fetcher da W0b, e só
quando roda com `--enable-upstream-fetch`. É a diferença dele para
`model-currency-state.json`, que é rastreado e é caminho da W0a. Cache
ausente ou velho não é erro: a coluna `upstream` sai como «sem dado» com
a idade em horas, que é informação, não bloqueio.

- [ ] `[P0][US6][.claude/scripts/ceo-boot.py]` O `/ceo-boot` mostra, por
      raia ativa, o trio {instalado, fixado, upstream} — e **nunca
      bloqueia**.
      Check: `python3 -m pytest .claude/scripts/tests/test_ceo_boot_model_currency.py -q -k shows_triple_per_active_lane`
- [ ] `[P0][US6][.claude/scripts/ceo-boot.py]` Controle de que é advisory
      mesmo: com um upstream falso à frente do valor fixado, o boot
      continua com código de saída 0.
      Check: `python3 -m pytest .claude/scripts/tests/test_ceo_boot_model_currency.py -q -k advisory_never_blocks`
- [ ] `[P0][US6][.claude/scripts/ceo-boot.py]` **O boot LÊ o cache e
      nunca busca.** Com `socket.socket` substituído por uma função que
      levanta, o boot completa; e com o cache ausente a coluna sai «sem
      dado» com a idade, não vazia e não vermelha.
      Check: `python3 -m pytest .claude/scripts/tests/test_ceo_boot_model_currency.py -q -k boot_reads_cache_never_fetches_and_degrades_visibly`
- [ ] `[P1][US6][.claude/commands/ceo-boot.md]` A superfície de comando
      documenta a dimensão nova, para que o que o boot imprime seja
      legível sem ler o código.
      Check: `grep -q 'model-currency' .claude/commands/ceo-boot.md`

### Wave W3b — dimensão na varredura noturna (canônica, UMA assinatura)

**Esta perna é canônica, e a descoberta é da rodada 2.** Medido,
`python3 .claude/hooks/check_canonical_edit.py --is-canonical .claude/workflows/nightly-hygiene.js`
⇒ **1**. O texto anterior tratava a varredura noturna como material
livre porque a citava por um caminho de skill que não existe; o arquivo
real exige assinatura GPG. A onda ganha, por isso, perna própria.

**Ela espera o PLAN-169.** É a única onda deste plano que espera: o item
(iv) da W4.3/W4-C acrescenta a dimensão `fleet-currency` a este mesmo
arquivo (§0). Abrir a W3b antes é editar um arquivo que outra wave está
reescrevendo — a classe S329 do baseline vivo, outra vez.

Paths (2): `.claude/workflows/nightly-hygiene.js` (oráculo = 1, existe
em HEAD),
`.claude/scripts/tests/test_nightly_hygiene_model_currency.py`
(oráculo = 0, criado aqui). Material de cerimônia:
`.claude/plans/PLAN-176/wave-w3b-approved.md` e o `.asc` do Owner.

- [ ] `[P1][US6][.claude/workflows/nightly-hygiene.js]` A dimensão nova
      entra na varredura noturna por CONFIGURAÇÃO, não por identificador
      opaco: ela aparece no `meta.description` e no vetor de dimensões
      que o script despacha, e o teste conta as dimensões antes e depois.
      Check: `python3 -m pytest .claude/scripts/tests/test_nightly_hygiene_model_currency.py -q -k dimension_is_wired_by_configuration`
- [ ] `[P1][US6][.claude/workflows/nightly-hygiene.js]` **O bloco COMMON
      do ADR-191 viaja com a dimensão nova.** Um workflow que ganha
      agente sem PROMPT DEFENSE ≥6, FILE ASSIGNMENT explícito e o
      marcador de HARD-RULES nasce descoberto (`CLAUDE.md` §5): o teste
      assere os três no prompt da dimensão.
      Check: `python3 -m pytest .claude/scripts/tests/test_nightly_hygiene_model_currency.py -q -k adr191_common_block_present`

## 4. Critérios de morte — cada um com arquivo, comando e dono

Os limiares de QUALIDADE são em **ciclos da rotina**. Os limiares de
VIDA são em relógio de parede, e a razão está no §1: um limiar contado
só em ciclos é infalsificável quando a rotina para de rodar — zero
execuções nunca cruzam «3 ciclos». Cadência-alvo declarada: **um ciclo
por 24 h** (a varredura noturna é invocada pelo operador, não por
`cron` — medido).

Arquivo de estado único e rastreado: `.claude/data/model-currency-state.json`.
Comando de leitura único: `check-model-currency.py --state --json` — **e
ele agora tem AC própria** (W0a, `state_json_serves_all_seven_death_criteria`);
o texto anterior o declarava sem que caixa nenhuma o exercitasse.

| # | critério | limiar | dono |
|---|---|---|---|
| K-1 | falsos-positivos (proposta de lançamento inexistente) | > 2 em 8 ciclos ⇒ abertura automática desligada, vira relatório | CEO |
| K-2 | proposta tocando a camada T | qualquer ocorrência ⇒ vermelho fail-closed no CI (fiado pela W1c) | CEO |
| K-3 | feed velho ou parcial | mais velho que 4 ciclos **ou que 96 h de relógio**, ou campo ausente ⇒ só relatório | CEO |
| K-4 | esquema do feed mudou (quebra do leitor) | qualquer ocorrência ⇒ fail-closed e rastro no log | CEO |
| K-5 | controle de falso-NEGATIVO | a cada 4 ciclos, lançamento conhecido injetado TEM de ser detectado; falhou ⇒ raia marcada morta. **Roda FORA da raia** (ver abaixo) | CEO |
| K-6 | falhas consecutivas de uma raia | 3 ciclos ⇒ raia desligada com alerta. **Declarado:** são 3 ciclos cego | CEO |
| K-7 | fase 2 (fusão automática) | só abre com ADR próprio ratificado | Owner |
| K-8 | **zero raias ativas** | qualquer ciclo que abra com nenhuma raia ativa ⇒ VERMELHO fail-closed, nunca verde-vazio | CEO |
| K-9 | **rotina parada** | `ts` do ciclo mais recente mais velho que 96 h ⇒ VERMELHO; é a única perna que enxerga a rotina morta | CEO |

**Por que K-8 e K-9 existem, e por que K-5 saiu da raia.** O plano mede
que existe **exatamente UMA raia ativa** hoje (Anthropic; a tabela de
preços tem 12 identificadores, todos `claude-*`). Nesse regime, K-6
«3 ciclos ⇒ raia desligada» desliga **o produto inteiro**, e nenhum dos
sete critérios anteriores cobria o estado resultante: a rotina passaria a
rodar verde e vazia, que é a assinatura visual de saúde. Pior, K-5 — o
controle de falso-NEGATIVO, o único detector de morte — rodava **dentro**
da raia que K-6 acabara de marcar morta. As três correções:

- **K-8** torna «zero raias ativas» um vermelho explícito.
- **K-5 roda num executor separado**, fora de qualquer raia, para que
  desligar uma raia não desligue o detector que enxerga a raia morta.
- **K-9** ancora a vida da rotina no relógio, não no contador de ciclos.

Uma consequência que fica declarada: a tabela de preços de que «raia
ativa» depende tem validade (`cost_table_valid_until`, medido em
`.claude/scripts/cost-table.yaml:29`). Tabela expirada pode tornar todas
as raias inertes — e é K-8 que impede isso de passar em silêncio. O
defeito de PREÇO em si é do ADR-148 e sai por
`PLAN-176-FOLLOWUP-canonical-models-expiry` (§5), não por esta classe.

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
- **Aritmética do orçamento, reconciliada com o piso MEDIDO deste
  repositório.** O texto anterior declarava `budget_tokens: 390-610k`
  com `budget_sessions: 5-6`, o que dá 65k a 102k por sessão. O piso de
  gate-boot re-pago deste repositório é medido e publicado em
  `CLAUDE.md:97`: **`F` = 97.292 tokens** na fronteira de uma
  compactação real, com controle independente cold-F em 97.097
  (delta 0,20 %). Ou seja, as duas chaves se contradiziam: 5 sessões
  já consumiam mais do que o limite inferior do orçamento **antes de
  qualquer trabalho**. Fica assim, e a decisão é explícita:

  **`budget_tokens` é o TOTAL — trabalho MAIS o piso re-pago.** É a
  chave que manda; `budget_sessions` é o multiplicador do piso.

  - *Trabalho, por onda (oito ondas agora, não seis — o re-corte da
    rodada 2 criou W1c e W3b, e cada perna canônica custa a sua
    cerimônia + as 2 rodadas de trilho do modelo de operação v2):*
    W0a 70-100k, W0b 90-130k, W1a 60-90k, W1b 90-130k, W1c 60-90k,
    W2a 60-100k, W3a 40-60k, W3b 40-60k = **510-760k**.
  - *Piso re-pago:* 6 a 8 sessões × 97.292 = **584k a 778k**.
  - *Total:* **1,09M a 1,54M**, que é o valor do cabeçalho.

  **`F` não é um ponto, é uma banda.** O mesmo `CLAUDE.md:97` registra
  que a série cold-F de n=41 tem spread de **51,7 % da média** — usar
  só a média subestima. O número acima é a média medida; o instrumento
  rastreado é `.claude/plans/PLAN-179/w0/gateboot_repay.py`, e é dele
  que a próxima revisão deve gerar a faixa em vez de digitá-la.

- **O valor em dólares é TETO, e isso agora está dito.** O cabeçalho
  carrega o teto conservador: total × preço do Opus 5. Insumos, todos
  lidos de `.claude/scripts/cost-table.yaml`: Opus 5 a 5,00 de entrada
  e 25,00 de saída por milhão (`:85-87`), com
  `blended_input_share: 0.80` / `blended_output_share: 0.20`
  (`:45-46`) ⇒ **9,00 por milhão**; 1,09M a 1,54M ⇒ **9,84 a 13,85
  dólares**, publicado como «9.8-13.9 USD».

  A `tier_mix_estimate` do cabeçalho **não é decorativa e não é o
  mesmo número** — ela vale sobre a metade de TRABALHO. Aplicando
  70/25/5 aos preços do mesmo arquivo (Sonnet 5 2,00/10,00 em
  `:110-112`; Haiku 4.5 1,00/5,00 em `:115-117`) dá **7,29 por
  milhão**; o piso re-pago é 100 % contexto do CEO e não admite
  mistura. Total pela derivação mista: **8,97 a 12,55 dólares**. As
  duas figuras coexistem por desenho — o cabeçalho leva o teto, o
  texto leva o esperado —, e a rodada 2 tinha razão: o defeito era
  publicar uma só e derivá-la dos insumos da outra. Ambas excluem
  contexto de subagentes e desconto de leitura de cache.
- **Nome do arquivo deste plano.** É
  `.claude/plans/PLAN-176-model-currency-refresh.md`. O caminho
  `.claude/plans/PLAN-176.md`, citado no material de abertura do
  debate, nunca existiu em disco.

## 5b. OQ nomeadas para o Owner — as rotas CARAS que este plano não gastou

Cada item abaixo tem uma rota barata já executada no texto e uma rota
cara que só o Owner autoriza. **Nenhuma onda fica bloqueada por elas** —
a forma barata é executável hoje; a cara compra mais garantia por mais
cerimônia.

| OQ | rota barata (executada) | rota cara (se o Owner quiser) | o que a cara custa |
|---|---|---|---|
| **OQ-1** — número do ADR | este plano usa **ADR-180**, escolhido por regra determinística (§3.4) | arbitrar que **198 fica com este plano** e o `PLAN-186/debate/round-4` se muda | reescrita do material daquele round, que já consome 198 no consenso |
| **OQ-2** — forense de auditoria | ACs degradadas aos campos que os allowlists fechados carregam (§3.1, §3.3, W0b) | emendar `.claude/hooks/_lib/audit_emit.py` para carregar caminho de egresso, identificador recusado e motivo | +1 caminho canônico e +1 assinatura na onda que a fizer; o arquivo tem oráculo = 1 |
| **OQ-3** — corte da W1b | re-cortada em **W1b (4 caminhos) + W1c (4 caminhos)**, duas assinaturas | autorizar **um pacote único de 8 caminhos numa assinatura** — exatamente no teto do modelo de operação v2, e sem folga para material de cerimônia | uma assinatura a menos, mas o pacote perde a independência de ordenação: a W1b passaria a esperar o land do `w4b-ci-matrix` junto com a W1c, que é a dependência que o re-corte tirou dela |

## 6. Diferido para a rodada que preceder a W2a

Dois achados do round 1 são reais e vivem na W2a, que só abre depois da
W1b: conteúdo de feed como entrada não confiável terminando no corpo do
Pull Request (endereçado em parte pela AC `untrusted_feed_is_fenced`,
que a rodada deve re-verificar), e critério de morte auto-referente ao
ramo que a própria rotina escreve.

A rodada 2 acrescentou dois, pela mesma razão — vivem na W2a:

- **O redator do ADR-114 precisa de módulo nomeado e de controle
  positivo.** A AC `body_is_redacted` promete «o redator do ADR-114» sem
  dizer qual módulo. Medido: ele é
  `.claude/hooks/_lib/codex_egress_redact.py` (existe em HEAD; oráculo =
  **1**), e o ADR-114 §:18-25 o define para **prompts enviados ao
  revisor externo**, não para corpo de Pull Request. Reusá-lo aqui é
  superfície nova: a rodada que preceder a W2a deve exigir o nome do
  módulo na AC e um controle positivo com segredo plantado (chave
  plantada no relatório ⇒ ausente no corpo).
- **A tabela de preços expira, e o efeito é silencioso.** Medido:
  `.claude/scripts/cost-table.yaml:29` traz
  `cost_table_valid_until: 2026-09-13`. «Raia ativa» depende dessa
  tabela (W0a), então uma tabela expirada pode tornar todas as raias
  inertes. A metade que este plano já cobre é o critério **K-8** (§4);
  a metade de PREÇO é do ADR-148 e sai por
  `PLAN-176-FOLLOWUP-canonical-models-expiry` (§5).

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

- 2026-09-07 (S348, docs): **cura da rodada 2 do debate executada.** Este
  texto absorve os 16 ajustes de
  `.claude/plans/PLAN-176/debate/round-2/consensus.md` (veredito
  `RUN-ANOTHER-ROUND`; três críticos `ADJUST` com 12 bloqueantes
  somados), cada um re-verificado em disco antes de virar cura. Mudou,
  em substância: o ADR sai de **198** — reivindicado por
  `PLAN-186/debate/round-4/proposal.md:133`, com 199 e 200 igualmente
  falados — para **ADR-180**, escolhido por regra determinística
  publicada e reprodutível (§3.4), e a aritmética inválida «198 arquivos
  ⇒ 198 livre» foi removida; a W1b se re-corta em **W1b + W1c**, cada
  uma com a linha `Paths:` igual ao conjunto das suas ACs (4 e 4, contra
  «cinco declarados / nove exigidos» antes), e o registro T ganha AC
  própria; o arquivo `.claude/data/model-currency-expected-reds.txt` e a
  bandeira `--expected-reds` **nascem na W0a**, que é livre, em vez de
  serem invocados de dentro do pacote assinado sem existir; a **W3 se
  parte em W3a/W3b** porque o alvo real da varredura noturna
  (`.claude/workflows/nightly-hygiene.js`) tem oráculo **1** — e os dois
  caminhos de skill que o texto anterior citava não existem em disco; os
  dois `Check:` vacuamente verdes (`test $? -le 1` e o `grep` que aceita
  `PROPOSED|ACCEPTED`) foram trocados por comandos cujo VERMELHO é a
  condição que a caixa proíbe; as três garantias «sem rede» por `grep`
  de nomes viraram **oráculo de runtime** com controle positivo por
  importação transitiva, e o ponto cego residual está declarado por
  escrito; as promessas de auditoria do §3 e da W0b **degradaram para os
  campos que os allowlists fechados de `_lib/audit_emit.py` carregam**,
  com a rota cara nomeada como OQ-2 do Owner; a lista de destinos passa
  a casar (host, caminho) inclusive **após redirecionamento**, a RECUSA
  passa a ser auditada, e entram ACs de tempo-limite e de verificação de
  certificado; o interruptor do fetcher ganha nome e camada
  (`--enable-upstream-fetch`, linha de comando, para não quebrar o
  conjunto fechado do §3.2) e a doutrina «nunca de dentro de um agente»
  é rebaixada a **convenção declarada** porque não existe marcador de
  contexto de agente em disco para construir o portão; «ciclo» ganha
  cadência e toda a §4 ganha **perna de relógio de parede**, mais os
  critérios **K-8 (zero raias ativas)** e **K-9 (rotina parada)**, com
  K-5 movido para fora da raia que K-6 pode matar; a ordenação
  **W1c × `w4b-ci-matrix`** sobre o manifesto de portões fica declarada,
  com baseline re-derivado no SIGN; o entregável duro do PLAN-169 é
  nomeado no novo §0; e as três chaves de orçamento são reconciliadas
  contra o piso medido `F = 97.292` (`CLAUDE.md:97`). Contagem após a
  cura: **42 caixas — 41 com comando executável e 1 fronteira de escopo
  declarada** (8+8+4+7+4+5+4+2 nas oito ondas). `status:` NÃO muda.
  Check: none (doc-only — a cura é o próprio texto)
- 2026-09-06 (S348, docs): **revisão executada.** Este texto absorve os
  16 must-fix do consenso do round 1
  (`PLAN-176/debate/round-1/consensus.md`, veredito `ESCALATE-TO-OWNER`)
  sob a decisão 4.14 do Owner («Autorizar a revisão do plano»,
  `PLAN-186/debate/owner-decisions-S347.md`). Mudou: ADR renumerado para
  **ADR-198** — *superado pela cura de 2026-09-07, que o levou a
  ADR-180: 198 já estava reivindicado por outro material, e a regra que
  o escolhia era inválida*; fetcher movido para um módulo
  canônico próprio em `.claude/hooks/_lib/` (oráculo = 1, cerimônia
  GPG), o que preserva a postura sem rede do ADR-136-AMEND-1 em vez de
  alterá-la; ondas cortadas em perna livre `a` e perna canônica `b`;
  camada T redefinida como TETO; conjunto de variáveis de ambiente
  fechado em um elemento; lista de destinos permitidos com dois pares
  host+caminho concretos; «fornecedor ativo» definido e medido em UMA
  raia; critérios de morte em ciclos com arquivo, comando e dono; **31
  caixas de seleção nas seis ondas de então — 30 com comando executável
  e 1 fronteira de escopo declarada** (o texto original desta linha
  dizia «cada uma com um `Check:` declarado», o que era literalmente
  verdadeiro e operacionalmente enganoso; corrigido na cura de
  2026-09-07), contra zero de cada antes, medido pelas mesmas expressões
  do §13.2 do esquema de planos; aritmética de orçamento fechada em
  390-610k com estimativa em dólares e mistura de camadas —
  *reconciliada em 2026-09-07 contra o piso medido de gate-boot*. O
  conjunto vermelho do oráculo foi RE-MEDIDO e são **quatro**
  identificadores, não um.
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

- **2026-09-07 (S348, Owner acordado; verbatim):** OQ-1 (número do ADR) — «Manter ADR-180 (Recomendado)». OQ-2 e OQ-3 apresentadas a seguir na mesma sessão.
- **2026-09-07 (S348, Owner acordado; verbatim):** OQ-2 (forense de auditoria) — «Emendar o audit_emit.py na W1 (rota cara)» (contra a recomendação): a W1 ganha `.claude/hooks/_lib/audit_emit.py` como caminho canônico adicional e a assinatura cobre o `_lib`. OQ-3 (corte da W1b) — «Duas assinaturas: W1b + W1c (Recomendado)». Flip — «Sim: executing agora; W0a (offline, livre) começa hoje (Recomendado)»: `status: reviewed → executing` neste commit; a W0a (detecção OFFLINE a partir do ADR-149 e da tabela local) é a unidade corrente.
