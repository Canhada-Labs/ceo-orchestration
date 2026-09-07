---
plan: PLAN-176
round: 2
rounds_synthesized: [round-1, round-2]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "§Waves W1b (:325-336) — a AC do conjunto-vermelho invoca `.claude/data/model-currency-expected-reds.txt` e a bandeira `--expected-reds`; o arquivo NÃO existe em HEAD, nenhuma onda o cria e nenhuma AC declara a bandeira: o arquivo nasce na W0a (livre) e a bandeira ganha AC própria"
  - "§Waves W0a (:166) e W1b (:301) — os `Check:` `test $? -le 1` e `grep -qE '^status: (PROPOSED|ACCEPTED)'` são vacuamente verdes: aceitam a condição que a própria caixa proíbe; trocar por comando cujo vermelho é a condição descrita"
  - "§4 (:387) — `check-model-currency.py --state --json` é declarado como comando de leitura ÚNICO dos 7 critérios de morte e não é exercido por nenhuma das 31 caixas; ganha AC na W0a"
  - "§Waves W0b (:213-218, :239-247) — a lista de destinos é host+caminho, mas `_coerce_egress_destination` reduz o campo a host nu e os dois destinos permitidos diferem SÓ no caminho; a regra de redirecionamento cobre só host; a RECUSA de destino não emite evento"
  - "§Waves W1b (:291-297 × :298-336) — a onda declara 5 caminhos canônicos e suas ACs exigem 9; o registro T declarado não tem AC nenhuma; o pacote estoura o teto de 8 do modelo de operação v2"
  - "§Waves W3 (:367, :375) — as duas ACs citam `.claude/skills/core/{ceo-boot,nightly-hygiene}/SKILL.md`, que não existem; os alvos reais são `.claude/scripts/ceo-boot.py` + `.claude/commands/ceo-boot.md` e `.claude/workflows/nightly-hygiene.js`"
  - "§3.4 (:134-138) — o número ADR-198 já está reservado por `PLAN-186/debate/round-4/proposal.md:133`; e a aritmética «198 arquivos ⇒ 198 livre» é inválida (175 números distintos, 22 livres ≤197)"
  - "§3.1 (:98-100) e §3.3 (:121-124) — as duas decisões afirmam gravar campos (id recusado + origem; o MOTIVO da degradação) que os allowlists fechados de `_lib/audit_emit.py` descartam"
  - "§Waves W0a/W0b/W1b (:170, :251, :312) — as três garantias «sem rede» são `grep` de NOMES de primitiva; a própria W0b cria um módulo importável cuja importação não casa o padrão"
  - "§1 (:60-61) e §4 (:385-397) — «ciclo» é unidade sem TAXA: nenhuma cadência é fixada, logo K-3 e K-6 não têm limite de relógio e uma rotina que para de rodar nunca cruza limiar"
  - "frontmatter (:10-11, :13) — `budget_tokens` 390-610k × `budget_sessions` 5-6 são incompatíveis contra o piso de gate-boot MEDIDO (F=97.292, `CLAUDE.md:97`); e `budget_usd_estimate` é derivado 100 % ao preço do Opus 5 (9,00/Mtok) enquanto `tier_mix_estimate` 70/25/5 dá 7,29/Mtok"
  - "§Waves W1b (:313-316) — o bump de `.claude/governance/gate-scripts-manifest.txt` (9 membros medidos) colide com o pack W4b já autorizado pelo Owner (manifesto 9→12): ordenação declarada e baseline re-derivado no SIGN"
  - "§4 (:396) — K-6 desliga a única raia ativa e nenhum critério cobre «zero raias ativas»; K-5, o controle de falso-negativo, roda DENTRO da raia morta"
  - "frontmatter (:9) — `depends_on: [PLAN-169]` aponta para um plano `status: executing`, sem dizer qual entregável é a dependência dura"
  - "§Waves W0b (:198-200, :206-208) × W3 (:367-370) — o interruptor do fetcher não é nomeado (e, se for variável de ambiente, colide com o conjunto FECHADO do §3.2), a doutrina «nunca de dentro de um agente» não tem portão, e o artefato de cache que a W3 lê não é nomeado; W2 e W3 não têm linha `Paths:` nem pernas a/b, contra a regra de leitura do :145-148"
  - "§2 (:66-67) e Progress log (:476-477) — «medido nesta revisão, na árvore de trabalho» sobre 8 caminhos que não existem em HEAD (o oráculo decide por PADRÃO de caminho, e os 10 vereditos reproduzem); e «31 caixas, cada uma com um Check: declarado» quando 3 dos 35 `Check:` são `none`"
synthesized_at: 2026-09-07T00:25:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-176 — consenso do round 2

Três críticos, três `ADJUST`, **12 itens bloqueantes somados (5 + 4 + 3)**.
Nenhum pediu `REJECT`. Toda claim abaixo foi re-verificada em disco, em HEAD,
antes de virar ajuste; as que não sobreviveram estão em `## Single-agent
insights rejected / deferred`. O plano não contém caminho pessoal
absoluto (varredura pelo prefixo de diretório de usuário = **0**
ocorrências).

**O que o round 2 CONFIRMA — a revisão `a6629d0` funcionou.** Os três críticos
re-verificaram independentemente e eu reproduzi:

- **A tese central segue verdadeira e mecânica.** Os 10 vereditos do §2
  (:69-78) reproduzem linha a linha com
  `python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>`:
  `models-registry.json 1`, `model_registry.py 1`, `model_feed_fetch.py 1`,
  `ADR-198-…md 1`, `gate-scripts-manifest.txt 1`, `validate.yml 1`,
  `models-preference.json 0`, `check-model-literals.py 0`,
  `check-model-currency.py 0`, `test_model_feed_fetch.py 0`. **Zero extensão da
  guard-list é necessária**, e nenhum ajuste abaixo a toca.
- **O must-fix 2 do round 1 está CURADO na forma forte.** O fetcher saiu de
  `check-substrate-watch.py` (cujo cabeçalho :8-11 diz o que o plano cita, e
  `grep -cE 'urllib|urlopen|socket|http[.]client|requests'` sobre ele = **0**)
  para `.claude/hooks/_lib/model_feed_fetch.py`, oráculo **1** — a lista de
  destinos passa a morar sob cerimônia. O precedente citado (`otel_emit.py`
  com `urllib` e oráculo 1) confere.
- Curados e re-verificados: T como TETO (§3.1), conjunto de env fechado em um
  elemento com gramática (§3.2), `canonical_models.json` decidido FORA de
  classe com follow-up nomeado (§5), critérios de morte com arquivo rastreado e
  dono (§4), 31 caixas de seleção contra 0 antes, e os três diretórios de teste
  citados estão em `pytest.ini` `testpaths` (`.claude/hooks/tests`,
  `.claude/hooks/_lib/tests`, `.claude/scripts/tests`) — logo coletáveis.
- **15 dos 16 must-fix do round 1 estão cumpridos.** O 16.º (aritmética de
  budget) foi cumprido na SOMA (390-610k fecha) e reaberto na COERÊNCIA das
  duas outras chaves do cabeçalho — ver C7 abaixo.

## Consensus findings (2+ agents flagged)

### C1 — CRITICAL — a AC do conjunto-vermelho invoca um arquivo que não existe e que onda nenhuma cria (Critic-A, Critic-B, Critic-C)

`PLAN-176:336` — `Check: python3 .claude/scripts/check-model-currency.py
--expected-reds .claude/data/model-currency-expected-reds.txt`. Medido:
`ls .claude/data/model-currency-expected-reds.txt` ⇒ **No such file**;
`grep -n 'expected-reds'` sobre o plano retorna **uma única linha, a :336** — a
bandeira `--expected-reds` não é declarada por AC nenhuma. O caminho não está
nos três da W0a (:158-159) nem nos cinco canônicos da W1b (:291-297). A caixa
nasce permanentemente vermelha e, se o arquivo for criado onde a caixa mora,
some um caminho ao pacote canônico (ver C2). Os três críticos convergem no
mesmo corte: o arquivo e a bandeira nascem na W0a, que é livre.

### C2 — CRITICAL — a W1b declara 5 caminhos e suas ACs exigem 9; o registro T declarado não tem AC (Critic-A, Critic-B)

`:291-297` diz «Cinco caminhos canônicos, um pacote, uma assinatura — dentro do
teto de oito caminhos do modelo de operação v2». Extração mecânica dos caminhos
citados nas 8 ACs da onda (`:298-336`) dá **nove**:
`ADR-198-model-trust-preference-split.md`, `model-currency-expected-reds.txt`,
`gate-scripts-manifest.txt`, `_lib/model_registry.py`,
`_lib/tests/test_model_registry.py`, `check-model-currency.py`,
`scripts/tests/test_check_model_literals.py`,
`scripts/tests/test_gate_scripts_manifest.py`, `validate.yml`. E
`.claude/governance/models-registry.json` — o registro T, primeiro dos cinco
declarados — **não aparece em nenhuma AC da W1b**; sua única citação é a AC da
W2 (:344). Duas seções do mesmo plano dizem números diferentes, e o pacote como
ACado estoura o teto de 8.

### C3 — HIGH — o `Check:` de duas caixas é vacuamente verde (Critic-A, Critic-B, Critic-C)

`:166` — `python3 .claude/scripts/check-model-currency.py --check; test $? -le 1`
aceita 0 **e** 1: um detector sempre-cego e um detector sempre-divergente
satisfazem a caixa identicamente, e só um crash (rc ≥ 2) a derruba. A caixa
afirma medir «divergência sai como achado nomeado» e não mede nada disso. Mesma
família em `:301` — `grep -qE '^status: (PROPOSED|ACCEPTED)'` aceita os DOIS
valores, logo não detecta o flip indevido que o texto da própria caixa proíbe
(«o flip para `ACCEPTED` é o arquivo `.asc` assinado, nunca o commit que
reescreve o campo»). O controle POSITIVO separado (`:171-175`) mitiga
parcialmente a primeira, não a segunda.

### C4 — HIGH — a AC de egresso da W0b não pode ser satisfeita como escrita (Critic-A, Critic-B)

`:244-247` exige que cada despacho emita `egress_destination_detected` **«com
host e caminho»**. Medido em `.claude/hooks/_lib/audit_emit.py`: a
chamada `event["destination"] = _coerce_egress_destination(event["destination"])`
roda no ramo de scrub da ação, e `_coerce_egress_destination` documenta-se como
«Reduce a destination to a bare host string (no scheme/path/query/cred)»,
cortando em `/`, `?` e `#`. A lista de destinos do plano (:217-218) é
`platform.claude.com` **duas vezes**, diferindo SÓ no caminho — o evento, por
construção, não distingue os dois despachos. Segunda perna, do Critic-B e
confirmada: a allowlist é host+caminho mas a regra de redirecionamento (:242)
cobre só **host**, então um 302 same-host para outro caminho escapa metade da
allowlist; e a RECUSA de destino não exige evento (só o despacho o exige),
deixando o caso forense sem rastro.

### C5 — HIGH — as duas ACs da W3 apontam para arquivos que não existem (Critic-A; alvo confirmado, e o Critic-C o toca pela perna do gatilho)

`:367` e `:375` citam `.claude/skills/core/ceo-boot/SKILL.md` e
`.claude/skills/core/nightly-hygiene/SKILL.md`. Medido:
`ls -d .claude/skills/core/ceo-boot .claude/skills/core/nightly-hygiene` ⇒ **No
such file or directory** nos dois. O que existe e é rastreado:
`.claude/commands/ceo-boot.md`, `.claude/scripts/ceo-boot.py` e
`.claude/workflows/nightly-hygiene.js`. A AC :375 é um `grep -q` contra um
arquivo inexistente — nasce **permanentemente vermelha**, e a cura do must-fix
15 do round 1 (trocar o id de gatilho truncado por âncora de configuração)
trocou uma âncora irrecuperável por outra.

### C6 — MEDIUM — «ciclo» é a unidade dos 7 critérios de morte e não tem TAXA, e o comando único que os lê não é exercido (Critic-A, Critic-C)

`:60-61` define ciclo como «uma execução da rotina de detecção» e `:385` fixa
todos os limiares nessa unidade. Nenhuma cadência é fixada em lugar algum do
plano — a âncora de gatilho foi substituída por um `grep` de MENÇÃO (:381) —
logo K-3 («mais velho que 4 ciclos») e K-6 («3 ciclos ⇒ raia desligada») não
têm limite de relógio: uma rotina que **para de rodar** nunca cruza limiar
nenhum. E `:387` declara `check-model-currency.py --state --json` como comando
de leitura ÚNICO dos sete critérios; medido, `--state` aparece **uma vez no
plano inteiro, nessa linha**, e nenhuma das 31 caixas o exercita.

### C7 — MEDIUM — duas chaves do frontmatter contradizem uma terceira e o piso medido do repo (Critic-C; a perna do orçamento também tocada pelo Critic-A via depends_on)

`:10-11` — `budget_tokens: 390-610k` com `budget_sessions: 5-6`. O piso de
gate-boot re-pago deste repositório é MEDIDO: `CLAUDE.md:97` publica
`F = 97.292` tokens na fronteira de uma compactação real (controle cold-F
97.097, spread 51,7 %, n=41, instrumento `PLAN-179/w0/gateboot_repay.py`).
5 × 97.292 = 486.460 e 6 × 97.292 = 583.752 — o piso de 5 sessões já ultrapassa
o limite INFERIOR do orçamento, e 6 sessões consomem 96 % do superior **antes de
qualquer trabalho**. Segunda perna, verificada aritmeticamente: `:13`
`tier_mix_estimate` 70/25/5 contra os preços de `cost-table.yaml` (Opus 5
5,00/25,00; Sonnet 5 2,00/10,00; Haiku 4.5 1,00/5,00) e as proporções
`blended_input_share 0.80` / `blended_output_share 0.20` dá 7,29/Mtok ⇒
**2,84-4,45 USD**, enquanto `budget_usd_estimate` «3.5-5.5 USD» é derivado em
`:415-421` 100 % ao preço do Opus 5 (9,00/Mtok ⇒ 3,51-5,49). A mistura de
camadas declarada é decorativa.

### C8 — LOW — `depends_on` aponta para plano em execução (Critic-A, Critic-B)

Frontmatter `:9` — `depends_on: [PLAN-169]`. Medido:
`.claude/plans/PLAN-169-*.md:4` = `status: executing`. O plano não nomeia qual
entregável do 169 é a dependência dura, então «a W1b espera o 169?» não tem
resposta no texto.

## Single-agent insights kept

- **K1 (Critic-A) — ADR-198 já está reivindicado, e a aritmética que o escolhe é
  inválida.** Medido: `.claude/plans/PLAN-186/debate/round-4/proposal.md:133`
  reserva `ADR-198-spawn-step0-dependency-and-fixed-cost.md`, e o consenso
  daquele round o consome (`:137`, `:178`). O plano repete a FORMA do C1 do
  round 1 (colidir com um número já falado) um número adiante. Duas correções
  minhas ao critic: (i) nenhum arquivo `ADR-198-*.md` existe em disco, então a
  CONCLUSÃO do plano é verdadeira hoje e o defeito é de reserva, não de
  colisão em disco; (ii) o censo dá **175 números distintos em 198 arquivos**
  (18 prefixos duplicados) e **22** números livres ≤197 —
  `[68, 130, 134, 166-180, 184, 187, 188, 189]`, dois a mais do que o critic
  listou. O argumento «o diretório tem 198 arquivos, logo 198 está livre»
  (:135-138) é inválido de qualquer modo.
- **K2 (Critic-A) — duas decisões do §3 afirmam gravar campos que a taxonomia
  fechada descarta.** `:121-124` diz que a degradação emite
  `model_choice_recommended` «com o motivo»; o allowlist do evento é
  `("action","session_id") + ("subtask_index","model_recommended",
  "confidence_basis_points","cost_governed","fell_back_to_static")` — não há
  campo de motivo. `:98-100` diz que a recusa pelo teto emite
  `model_routing_enforced`; o allowlist é `{action, ts, session_id, project,
  event_schema, tokens_*, hmac*, archetype, mode, recommended_model,
  killswitch_armed, decision}` — sem campo para o id RECUSADO nem para a
  origem que o pediu. A promessa forense do §3 não sobrevive ao scrub.
- **K3 (Critic-B) — as três garantias «sem rede» são `grep` de NOMES, e a
  própria W0b ensina o contorno.** `:170`, `:251` e `:312` usam
  `! grep -qE 'urllib|urlopen|socket|http[.]client|requests' <arquivo>`. A W0b
  cria `.claude/hooks/_lib/model_feed_fetch.py`, importável;
  `from _lib import model_feed_fetch` não casa o padrão, e o detector offline
  poderia adquirir egresso com as três ACs verdes. É exatamente a classe que
  `CLAUDE.md` §5 registra («instrumento que prevê código por TEXTO não
  converge») — a cura conhecida é oráculo de runtime confinado, ou o ponto cego
  declarado por escrito.
- **K4 (Critic-B) — o bump do manifesto colide com um pack já autorizado.**
  Medido: `grep -vc '^#' .claude/governance/gate-scripts-manifest.txt` = **9**,
  e `CLAUDE.md` §5 (linha S347) registra o W4b do Owner levando o «manifesto
  9→12». Sem ordenação declarada, o land de um invalida o material do outro —
  a classe S329 «BASELINE é o hash do vivo», que este repo já pagou duas vezes.
- **K5 (Critic-C) — K-6 desliga o produto inteiro e não há critério para «zero
  raias».** O próprio plano mede UMA raia ativa (`:186-187`; confirmei:
  `cost-table.yaml` tem 12 ids, todos `claude-*`). K-6 (`:396`) desliga uma raia
  após 3 ciclos de falha — com uma só raia, isso é o produto inteiro — e K-5, o
  controle de falso-NEGATIVO, roda DENTRO da raia que acabou de ser marcada
  morta. Nenhum dos sete critérios cobre o estado «zero raias ativas».
- **K6 (Critic-A, Critic-B) — a doutrina do chamador não tem portão e o
  interruptor não tem nome.** `:206-208` («o fetcher é invocado pelo Owner ou
  pela rotina agendada, nunca de dentro de um agente») é doutrina: o módulo mora
  em `.claude/hooks/_lib/`, importável por todo hook, e nenhuma das 6 ACs da W0b
  verifica o chamador. O interruptor de habilitação (`:198-200`, «sem opção
  explícita de habilitação») não é nomeado e, se for variável de ambiente,
  colide com o conjunto FECHADO `{CEO_MODEL_PREFERENCE}` do §3.2 (`:108-109`).
  Some-se: o artefato de cache de upstream que a W3 lê (`:367-370`) não é
  nomeado, e W2/W3 não têm linha `Paths:` nem pernas `a`/`b`, contra a regra de
  leitura do `:145-148` («em **cada** onda»).

## Single-agent insights rejected / deferred

- **REJEITADO como bloqueante — «§2 diz *medido na árvore de trabalho* sobre 8
  arquivos que não existem» (Critic-C, R-FIN8).** Confirmei que 8 dos 10
  caminhos estão MISSING em disco, mas rodei o oráculo sobre os dez e os **dez
  vereditos reproduzem exatamente** o que o plano publica — o oráculo decide por
  PADRÃO de caminho, não por conteúdo. A medição é válida; só a palavra «árvore
  de trabalho» promete mais do que foi feito. Vira correção de uma frase, não
  must-fix próprio (absorvido no ajuste 12).
- **REJEITADO como must-fix separado — «31 caixas, cada uma com um `Check:`»
  (Critic-A, R-VP10).** Medido: 31 checkboxes, 35 linhas `Check:`, das quais 3
  são `none` (uma delas, `:363`, é fronteira de escopo declarada e legítima; 2
  estão no progress log). A afirmação do progress log é imprecisa, não falsa
  sobre a substância. Absorvida no mesmo ajuste 12.
- **DIFERIDO ao round que preceder a W2 — «o redator do ADR-114 sem módulo
  nomeado e sem controle positivo» (Critic-B, S-R9).** Verifiquei que
  `.claude/hooks/_lib/codex_egress_redact.py` existe e que
  `ADR-114:18-25` define o objeto como prompts ao Codex, não corpo de PR. Mas
  isso vive na W2, que o §6 do próprio plano já difere para a rodada que a
  preceder — e a AC `body_is_redacted` (:355) é o gancho onde isso será medido.
  Registrado ali, não aqui.
- **DIFERIDO como follow-up de PREÇO — `cost_table_valid_until: 2026-09-13`
  (Critic-B, S-R8).** Confirmado em `.claude/scripts/cost-table.yaml:29` (6 dias
  a partir de hoje). Mas «raia ativa» depender de uma tabela de preço expirável
  é a MESMA classe que o §5 já decidiu mandar para
  `PLAN-176-FOLLOWUP-canonical-models-expiry`: é defeito de preço sob o ADR-148,
  fora desta classe. A metade que SOBREVIVE — «tabela expirada pode tornar todas
  as raias inertes em silêncio» — está coberta pelo ajuste 10 (critério para
  zero raias), não por um must-fix próprio.
- **NÃO ESCALADO — o teto de 8 caminhos e a emenda à taxonomia de auditoria.**
  Os dois têm rota de cura dentro da autoridade do CEO (re-cortar a W1b em
  W1b/W1c; degradar as ACs aos campos que os allowlists já carregam), então
  nenhum deles é a classe D1/D2 do round 1 («decisão sobre material que o Owner
  assinou»). Ficam como OQ nomeadas no ajuste 2 e no ajuste 5, para o Owner
  escolher a rota mais cara se quiser — não para desbloquear o round.

## Plan adjustments (must-fix)

1. **O arquivo de vermelhos-esperados e a bandeira `--expected-reds` nascem na
   W0a** (livre), com AC própria que os cria e os lê; a caixa `:336` passa a
   citar o caminho já existente. — §Waves W0a (`:157-159`), W1b (`:325-336`). [C1]
2. **Re-cortar a W1b**: a lista de caminhos da onda e o conjunto de caminhos das
   suas ACs têm de ser o MESMO conjunto, com o registro T ganhando AC própria e
   o pacote ficando ≤8 caminhos (W1b/W1c, ou autorização explícita do Owner para
   o excedente). — §Waves W1b `:291-297` × `:298-336`. [C2]
3. **Trocar os dois `Check:` vacuamente verdes** por comandos cujo VERMELHO é a
   condição que a caixa descreve (`--check` com código de saída que separa cego
   de divergente; verificação do `.asc` para o flip do ADR, não `grep` de campo).
   — §Waves W0a `:166`, W1b `:301`. [C3]
4. **Reescrever a AC de egresso da W0b para o que o evento consegue carregar**:
   o campo `destination` é reduzido a host nu, então distinguir os dois destinos
   exige outro campo permitido (ou uma emenda canônica à taxonomia, que é
   cerimônia a mais — decidir e declarar qual). — §Waves W0b `:244-247`. [C4]
5. **Fechar as duas metades restantes do egresso**: regra de redirecionamento
   sobre host **e** caminho, e evento auditado também na RECUSA de destino;
   acrescentar AC de tempo-limite e verificação de certificado. — §Waves W0b
   `:239-247`. [C4]
6. **Degradar as promessas do §3 aos campos que a taxonomia fechada carrega**
   (ou trazer a emenda a `_lib/audit_emit.py` para dentro do escopo, somando uma
   cerimônia): «com o motivo» e «id recusado + origem» não sobrevivem ao scrub.
   — §3.1 `:98-100`, §3.3 `:121-124`. [K2]
7. **Trocar os alvos das duas ACs da W3** pelos arquivos que existem
   (`.claude/scripts/ceo-boot.py` + `.claude/commands/ceo-boot.md`;
   `.claude/workflows/nightly-hygiene.js`). — §Waves W3 `:367`, `:375`. [C5]
8. **Escolher outro número de ADR** (o censo dá 22 livres ≤197) ou registrar no
   plano o acordo de alocação com o `PLAN-186/debate/round-4`, e **remover a
   aritmética inválida** «198 arquivos ⇒ 198 livre». — §3.4 `:134-138`. [K1]
9. **Fixar a CADÊNCIA da rotina** (o que é um ciclo por unidade de relógio) e
   dar AC ao comando de leitura `--state --json`, sem o qual nenhum dos sete
   critérios de morte pode ser cruzado nem lido. — §1 `:60-61`, §4 `:385-387`.
   [C6]
10. **Acrescentar o critério «zero raias ativas»** e mover o controle de
    falso-negativo (K-5) para fora da raia que K-6 pode marcar morta. — §4
    `:391-397`. [K5]
11. **Reconciliar as três chaves de orçamento do cabeçalho**: declarar se
    `budget_tokens` inclui o piso de gate-boot re-pago (`F = 97.292`,
    `CLAUDE.md:97`) — e, se não, qual das duas chaves manda —, e escolher se
    `budget_usd_estimate` é TETO ao preço do Opus 5 ou o valor da mistura de
    camadas declarada (2,84-4,45 contra 3,51-5,49). — frontmatter `:10-13`,
    §5 `:415-421`. [C7]
12. **Corrigir as duas frases que prometem demais**: «medido nesta revisão, na
    árvore de trabalho» (o oráculo decide por padrão de caminho; 8 dos 10
    arquivos não existem) e «31 caixas, cada uma com um `Check:` declarado»
    (3 dos 35 `Check:` são `none`). — §2 `:66-67`, Progress log `:476-477`.
    [rejeitado-parcial R-FIN8, R-VP10]
13. **Declarar a ordenação W1b × W4b sobre `gate-scripts-manifest.txt`** e
    re-derivar o baseline no momento do SIGN (medido: 9 membros hoje; o W4b leva
    a 12). — §Waves W1b `:313-316`. [K4]
14. **Substituir a garantia «sem rede» de `grep` de nomes** por oráculo de
    runtime confinado (soquete substituído + controle positivo por importação
    transitiva), OU declarar o ponto cego por escrito no plano. — §Waves W0a
    `:170`, W0b `:251`, W1b `:312`. [K3]
15. **Nomear o interruptor do fetcher e sua camada** (bandeira de linha de
    comando × variável de ambiente — e, se for env, dizer se o conjunto fechado
    do §3.2 vale só para o resolver), **dar portão ou declarar sem portão** a
    doutrina «nunca de dentro de um agente», **nomear o artefato de cache** que
    a W3 lê, e **dar linha `Paths:` e pernas `a`/`b` a W2 e W3**, como a regra
    de leitura do `:145-148` exige. — §Waves W0b `:198-208`, W3 `:367-370`,
    W2 `:339`. [K6]
16. **Nomear o entregável do PLAN-169 que é a dependência dura** e dizer se a
    W1b espera o fechamento daquele plano (`status: executing` em HEAD). —
    frontmatter `:9`. [C8]

## Round verdict

**RUN-ANOTHER-ROUND.**

**12 itens bloqueantes abertos** — o rótulo `design-coherent` **NÃO** é
registrado, porque o round termina com bloqueantes vivos. `PROCEED` está fora
de questão por essa mesma regra.

Mas a diferença para o round 1 é material e vale registrar: **este round não
escala.** O round 1 terminou em `ESCALATE-TO-OWNER` por dois itens que nenhuma
reescrita podia resolver (o número de um Amendment Owner-signed; a postura
no-network do ADR-136-AMEND-1). Os 12 bloqueantes de agora são **todos
curáveis por reescrita de texto ou re-corte de escopo dentro da autoridade do
CEO** — inclusive os dois que parecem pedir o Owner, porque cada um tem rota
barata: a W1b se re-corta em W1b/W1c sem tocar no teto ratificado, e as ACs de
auditoria degradam para os campos que a taxonomia já carrega sem abrir uma
cerimônia nova. Três OQ ficam NOMEADAS para o Owner escolher a rota cara, se
quiser: (i) autorizar 9 caminhos numa assinatura em vez de re-cortar; (ii)
trazer a emenda a `_lib/audit_emit.py` para dentro do escopo; (iii) arbitrar a
alocação do número ADR-198 entre este plano e o `PLAN-186/debate/round-4`.

O plano permanece `status: reviewed` — o flip para `executing` é a decisão 4.10
do Owner e não é matéria deste round. **Nenhuma onda abre**: a W0a depende do
ajuste 1 e do ajuste 3, e as pernas `b` exigem assinatura GPG que não existe
esta noite (regra da noite S348). Sequência recomendada: o CEO absorve os
ajustes 1-16 num pack de docs livre; o **round 3** re-verifica o texto corrigido
— e, pela regra de teto de rodadas do Owner (R2/R3), se a abertura do round 3
não couber, o registro correto é parar aqui com esta lista como a dívida
declarada, nunca declarar o plano coerente. Os itens diferidos (redator do
ADR-114 no corpo do Pull Request; tabela de preço expirando) entram no round que
preceder a W2, como o §6 do plano já manda.
