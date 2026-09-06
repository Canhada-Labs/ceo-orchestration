---
plan: PLAN-188
round: 2
rounds_synthesized: [round-1, round-2]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "§Approach:126-136 (cura do C1) + AC-1 Check:457-462 — a cura é de ENDEREÇO e a descoberta do lint é por CONTEÚDO e só `.sh` (`check-ceremony-script.py:137`, `:146`): `read_manifest.py` fica invisível e o controle positivo escolhido (`|| true` numa linha de `gpg`) fornece ele próprio o token que torna o arquivo descoberto"
  - "§Approach:129-133 — o plano afirma que o toolkit descoberto «herdaria QUATRO das cinco classes bloqueantes»; com a descoberta funcionando, R1 (`:165`, BLOCKING sem `AUTO-GENERATED` nem `CEREMONY-LINT: handwritten-exception:`) reprova TODO script escrito à mão: a decisão sobre a marca é entrega da W0, não consequência"
  - "§Approach (ausente) + §Riscos:302-336 — o plano nunca cita o ESCAPE do lint: `ceremony-lint-waivers.json` (44 entradas) isenta achado BLOCKING por sha256 de CONTEÚDO, com override `--waivers` (`check-ceremony-script.py:288-297`)"
  - "§Riscos:302-336 + AC-6:590-599 — os DOIS arquivos que carregam a autoridade do lint sobre o toolkit (`check-ceremony-script.py`, `ceremony-lint-waivers.json`) são oráculo **0**, fora de `_KERNEL_PATHS` e fora do manifesto ADR-192 (9 membros): a cura do C1 é desfeita por um Edit livre"
  - "§Approach:129-136 (alargamento da R8) — contradiz a razão escrita no próprio checador (`check-ceremony-script.py:192-194`: exec-bit em ferramenta invocada diretamente é legítimo) e o plano não declara COMO o Owner invoca `sign.sh`/`land.sh`"
  - "§Riscos:313-322 + AC-1 nota de custo:453-459 + OQ-9:704-711 — o QUARTO sítio põe o toolkit nos dois `paths:` do `smoke-install.yml`, cujo job é ÚNICO (`:193`), `timeout-minutes: 150` (`:337`) e ~1 h medido, para executar um `shasum -c` de segundos; a OQ-9 só cobre a metade barata"
  - "§Approach invariante 3:236-240 — a cura do C7 troca o literal de máquina por «variável de ambiente do harness OU sentinela de conteúdo no fixture»; o braço de conteúdo põe a isenção DENTRO do material assinado e o de env var é herdado por qualquer processo, inclusive o `sign.sh` do Owner"
  - "§Items W0:359-368 e :383-389 — a divisão W0a/W0b (5 + 6 = 11) não nomeia `lib.sh` em nenhuma das duas metades e chama de «manifesto» um artefato que a W0 não entrega (o `ceremony.tsv` é da W1, :397)"
  - "§Items W0:369-371 vs invariantes 1/4/5 (:225-226, :241-248) — o subconjunto «que `lib.sh` falsifica SOZINHO» inclui três invariantes definidas em termos de `finalize.sh`/`sign.sh`, entregas da W1; o plano deve dizer QUEM escreve o arquivo que o controle da W0 falsifica"
  - "OQ-7:689-696 vs §Approach:166 e :170-171 — o esquema congela `scope_generated_from` e o leitor recusa chave desconhecida/obrigatória-ausente: as duas leituras da OQ-7 produzem leitores DIFERENTES, e o leitor é entrega da W0"
  - "AC-2:471-474 — o Check tem a vacuidade que o round 1 curou só no AC-3: pacote fora do repo nunca referencia `OWNER-*.sh` próprios (`git ls-files | grep -icE 'w4b|w5a|w1a|w6a'` = 0), logo já é verde antes do trabalho"
  - "AC-3:486-503 — sem critério de morte pré-registrado (o AC-4 tem, :577-582): corpus `<PK>` indisponível ⇒ NÃO CONCLUSIVO, não «falhou»"
  - "AC-4:512-513 — o sha256 do instrumento é valor esperado DIGITADO que nenhum gate confere, num binário que a W3 vai editar por desenho"
  - "§Context:20 e §Items:348 — as citações `PLAN-SCHEMA.md:462-470` / `:441` não trazem o path que resolve no HEAD (`.claude/plans/PLAN-SCHEMA.md`); as faixas conferem"
  - "frontmatter / How to continue — o alvo indicado ao round («`.claude/plans/PLAN-188.md`») NÃO existe: o arquivo é `.claude/plans/PLAN-188-shared-ceremony-toolkit.md`; o ponteiro citado em prompts e runbooks é corrigido"
synthesized_at: 2026-09-06T05:35:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-188 — consenso do round 2

Três críticos, três `ADJUST`, **10 bloqueantes somados** (4 + 3 + 3) — contra 13
no round 1. Nenhum pediu `REJECT` e nenhum atacou a TESE: os três a reafirmam.
Sobre os **15 must-fix do round 1**, o veredito deste sintetizador, verificado
linha a linha no arquivo revisado (`fad3d02`): **12 FECHADOS, 3 PARCIAIS**
(o C1, o C6 e o C7), **0 não fechados** — e todas as cifras que a revisão cita
batem em disco (manifesto ADR-192 = 9 membros; 33 de 48 `OWNER-*(SIGN|LAND)*.sh`
citam `sentinel-signers`; `git ls-files | grep -icE 'w4b|w5a|w1a|w6a'` = 0;
sha256 do instrumento = `d2234bd…181062`; R8 escopada em `:194`;
`DISCOVERY_ROOTS`/`EXPLICIT_FILES` em `:62-68`).

A forma dos dez bloqueantes é UMA e é nova — não é o round 1 repetido: **o
mecanismo NOVO que a revisão introduziu não responde à pergunta que o plano
lhe atribui**. A cura do C1 foi escrita como decisão de ENDEREÇO; a descoberta
do lint é por CONTEÚDO. Nenhum bloqueante pede arquitetura nova.

## Consensus findings (2+ agents flagged)

### D1 — CRITICAL — a cura do C1 é de endereço; a descoberta do lint é por conteúdo e só `.sh` (Critic-A, Critic-B, Critic-C)

Verificado no HEAD: `.claude/scripts/check-ceremony-script.py:137` —
`if not fn.endswith(".sh"): continue` — e `:146` —
`if SHEBANG_RE.match(body) and CEREMONY_OPS_RE.search(body)`, com
`CEREMONY_OPS_RE` em `:71-73` (`gpg|git tag|gh release|npm publish|sentinel|
approved\.md|VERDICT`). Consequências, todas dentro da W0 como escrita
(`PLAN-188-shared-ceremony-toolkit.md:359-368`):

1. `read_manifest.py` — o parser fail-CLOSED no ponto exato onde o Owner assina
   — **nunca é descoberto**, por ser `.py`. Alargar `DISCOVERY_ROOTS` não muda
   isso.
2. Um controle do toolkit sem token da `CEREMONY_OPS_RE` nasce invisível.
3. O controle POSITIVO que o AC-1 exige (`:459-462`: script do toolkit com
   `|| true` numa linha de `gpg`) contém `gpg` — ele fornece o próprio token que
   o torna descoberto. É verificação que um arquivo transplantado satisfaria:
   o Check não pode ficar vermelho pela razão que alega medir.

**Severidade acordada:** CRITICAL — é a mesma classe «instrumento verde cuja
pergunta envelheceu» que motivou o C1. **Mitigação:** a W0 declara o PREDICADO
de descoberta do toolkit (por diretório, não por conteúdo, e incluindo `.py`),
ou nomeia o gate que cobre `read_manifest.py`; e o controle positivo passa a ser
um arquivo SEM token de cerimônia — se ele não for descoberto, a cura é falsa.
**Landa em:** §Approach:126-136, AC-1 Check:457-462, §Items W0:359-368.

### D2 — CRITICAL — com a descoberta funcionando, R1 reprova TODO o toolkit (Critic-B; mecanismo confirmado por Critic-C via a rota do waiver)

Verificado: `check-ceremony-script.py:165` marca **R1 BLOCKING** quando o corpo
não contém `PROVENANCE_MARK` nem `EXCEPTION_MARK` (`:84-85` =
`"AUTO-GENERATED"` e `"CEREMONY-LINT: handwritten-exception:"`). O toolkit é
escrito à mão: descoberto, ele fica VERMELHO no dia 1 em R1, e o único verde é
a marca de exceção por arquivo. O plano (`:129-133`) diz que o toolkit
descoberto «herdaria QUATRO das cinco classes bloqueantes» — herda cinco, e a
quinta é exatamente a que a marca anula.

**Severidade acordada:** CRITICAL para o sequenciamento da W0 (é o que decide se
a W0 pode fechar verde). **Mitigação:** decisão escrita e por arquivo — marca
`CEREMONY-LINT: handwritten-exception: <razão>` com razão auditável, ou o
toolkit gerado com a marca de proveniência. Sem isso, a W0 nasce vermelha ou
verde-por-exceção silenciosa. **Landa em:** §Approach:129-136, §Items W0.

### D3 — HIGH — o escape do lint (waivers por sha256 de conteúdo) não é citado, e a autoridade do lint mora fora de todo gate (Critic-B, Critic-C)

Verificado: `.claude/scripts/ceremony-lint-waivers.json` tem **44** entradas e
`check-ceremony-script.py:288-297` isenta achados por `sha256` de CONTEÚDO, com
override `--waivers` (`:261-262`). E os DOIS arquivos que carregam a autoridade
do lint sobre o toolkit são desprotegidos: o oráculo responde
`.claude/scripts/check-ceremony-script.py	0` e
`.claude/scripts/ceremony-lint-waivers.json	0`; nenhum casa `_KERNEL_PATHS`
(113 padrões, testados por `fnmatch`); nenhum está entre os 9 membros do
`.claude/governance/gate-scripts-manifest.txt`. A cura do C1 — `DISCOVERY_ROOTS`
e o escopo da R8 — pode ser desfeita por um Edit livre ou por um append de
waiver, sem cerimônia. O PLAN-188 não menciona nem o arquivo nem a rota.

**Severidade acordada:** HIGH (CRITICAL se a OQ-6 fechar sem cobri-los).
**Mitigação:** o AC-6 absorve os dois arquivos (é entrega, não gosto), ou o
plano abre a pergunta explicitamente e escreve o limite. **Landa em:**
§Riscos:302-336, AC-6:590-599, +OQ-10.

### D4 — HIGH — o alargamento da R8 contradiz a razão escrita no próprio checador (Critic-A, Critic-B, Critic-C)

Verificado: `check-ceremony-script.py:192-194` — «R8 só na superfície de binding
assinado (`.claude/plans/`): exec-bit em ferramenta de `scripts/local/` é
legítimo (invocada diretamente)». O plano (`:129-136`) alarga a R8 ao toolkit
sem reconciliar essa razão e sem declarar COMO o Owner invoca `sign.sh` /
`land.sh`. Medido: `generate-ceremony.sh` e `verify-counts.sh` são `100755` no
índice; os `OWNER-*.sh` de plano são `100644`. E `CLAUDE.md` §4 registra que o
exec-bit volta no primeiro `git add -A` se largado só no índice.

**Severidade acordada:** HIGH. **Mitigação:** o plano declara o modo de
invocação (`bash <path>`, modo 100644) e reconcilia — ou não alarga a R8 e
nomeia o que a substitui. A rota de recuperação por waiver é o D3.
**Landa em:** §Approach:129-136.

### D5 — MEDIUM — o AC-1 exige um runner de controles que ninguém executa (Critic-A, Critic-B)

Verificado: `.github/workflows/validate.yml:341-359` roda `shellcheck -S
warning` sobre `find .claude/scripts .claude/hooks -name '*.sh'` — a metade
barata do AC-1 é automática. A metade CARA (o runner que imprime 5/5) não tem
workflow, step nem custo, e a OQ-9 (`:704-711`) segue aberta. É a classe «a red
gate nobody runs».

**Severidade acordada:** MEDIUM — não bloqueia a W0 ser ESCRITA, bloqueia o AC-1
ser FECHADO. **Mitigação:** a OQ-9 é reduzida, antes da W0, a «qual evento
executa o runner»; o custo em runner-minutos pode vir depois.
**Landa em:** AC-1:453-459, OQ-9.

## Single-agent insights kept

Cada um verificado por mim em disco antes de virar ajuste.

- **K1 (Critic-B) — o quarto sítio arrasta o job mais caro do repo.**
  Verificado: `smoke-install.yml` tem UM job (`smoke`, `:193`, `ubuntu-latest`
  `:196`) com `timeout-minutes: 150` (`:337`); `CLAUDE.md` §5 mede 1h08 e 58 min.
  O step de integridade (`:355-360`) é um `shasum -a 256 -c` de segundos. Pôr
  `.claude/scripts/ceremony/**` nos dois `paths:` faz todo PR do toolkit pagar a
  hora inteira. **Ajuste:** o plano mede ou nomeia a alternativa (job próprio, ou
  o step movido para um workflow barato) — e a OQ-9 passa a cobrir este custo.
- **K2 (Critic-C) — os dois braços da invariante 3 são inseguros de formas
  opostas.** Verificado no plano `:236-240`: «variável de ambiente do harness,
  ou sentinela de conteúdo no fixture». O braço de conteúdo põe a isenção DENTRO
  do material que o guard existe para julgar; o de env var é herdado por
  qualquer processo filho, inclusive o `sign.sh` do Owner — a classe de carrier
  que `CLAUDE.md` §5 já registra ter sido curada por NEUTRALIZAÇÃO no import.
  **Ajuste:** o braço é decidido ANTES da W0, com controle vermelho que reprove
  material MARCADO fora do self-test.
- **K3 (Critic-A) — a OQ-7 trava um artefato da W0.** Verificado: o esquema
  congela `scope_generated_from` (`:166`) e as recusas nomeadas incluem «chave
  desconhecida» e «chave obrigatória ausente» (`:170-171`); o leitor é entrega da
  W0 (`:359-360`) e a OQ-7 (`:689-696`) deixa em aberto se a chave existe.
  **Ajuste:** ou a OQ-7 vira pré-condição da W0 (como a OQ-3 virou), ou o esquema
  declara a chave OPCIONAL-por-construção e o leitor aceita as duas formas — mas
  isso é escrito, não deduzido.
- **K4 (Critic-A) — a divisão W0a/W0b perde `lib.sh`.** Verificado `:383-389`:
  W0a = «manifesto + leitor + os TRÊS arquivos de gate = 5 paths», W0b = «os seis
  arquivos de controle». 5 + 6 = 11 = o total, e `lib.sh` (`:359`) não é nomeado
  em nenhuma; «manifesto» só fecha a aritmética se significar `lib.sh`, mas o
  `ceremony.tsv` é entrega da W1 (`:397`). **Ajuste:** a divisão nomeia os
  arquivos, não as categorias.
- **K5 (Critic-A) — três das cinco invariantes da W0 são definidas por escritores
  da W1.** Verificado: inv. 1 «pinados por sha256 gravado pelo `finalize`»
  (`:225-226`), inv. 4 «escritos SÓ pelo finalize; `sign.sh` regenera»
  (`:241-242`), inv. 5 «`sign.sh` regenera e compara» (`:246-248`) — contra a
  justificativa «todas predicados sobre ARQUIVOS» (`:369-371`) e contra o C6, que
  tirou 2/6/7/8 da W0 por dependerem de `land.sh`/`harness.sh`. **Não é fatal**
  (um controle pode plantar o arquivo por fixture), **mas é incoerente como
  escrito**. **Ajuste:** a W0 declara, por invariante, QUEM escreve o arquivo que
  o controle falsifica — fixture do controle, ou `lib.sh`.
- **K6 (Critic-A) — o Check do AC-2 é vácuo pela razão do C2.** Reproduzido:
  `git ls-files | grep -icE 'w4b|w5a|w1a|w6a'` = **0**, e o plano (`:58-60`) diz
  que os pacotes ficam fora do repo. O Check (`:471-474`) já é verde antes do
  trabalho. **Ajuste:** o AC-2 herda a cura do AC-3 (`:495-503`): mapa
  pacote→path + controle POSITIVO que o faça ficar VERMELHO.
- **K7 (Critic-B) — o AC-3 não tem critério de morte, o AC-4 tem.** Verificado:
  `:577-582` pré-registra NÃO CONCLUSIVO / INVÁLIDO para o AC-4; o AC-3
  (`:486-503`) mede diretórios fora do repo e não diz o que acontece quando o
  `<PK>` não está disponível. **Ajuste:** «corpus indisponível ⇒ NÃO CONCLUSIVO».
- **K8 (Critic-B) — o digest do instrumento é prosa.** Verificado: o sha256 do
  plano (`:512-513`) bate com `shasum -a 256`, e o binário NÃO está entre os 9
  membros do manifesto ADR-192; a W3 (`:531-541`) manda editá-lo por desenho.
  **Ajuste:** uma linha de manifesto conferida por `shasum -c`, ou a declaração
  explícita de que o pin é documental e o controle é a re-medição classe-a-classe.
- **K9 (Critic-C, nota FAVORÁVEL que o plano não faz) — a mudança de endereço
  tem um ganho de segurança não escrito:** `.claude/scripts/check_contamination.py`
  isenta `scripts/local/historical/*` (`:299-301`) e `archive/*` (`:321-326`) por
  cadeia de custódia; mover a cerimônia para `.claude/scripts/ceremony/` a
  RETIRA dessas isenções. **Ajuste:** escrever o ganho (é argumento a favor do
  endereço escolhido, hoje ausente).
- **K10 (Critic-C) — a invariante 10 escolheu a raiz certa.** Verificado:
  `.claude/sentinel-signers.txt` casa `_KERNEL_PATHS` — consolidar 33 checagens
  nela NÃO cria ponto único forjável. **Ajuste (cosmético):** a invariante nomeia
  o rail duplo (`check_canonical_edit.py`), para o leitor não supor gate único.
- **K11 (Critic-A) — citações sem path.** Verificado: `PLAN-SCHEMA.md` resolve em
  `.claude/plans/PLAN-SCHEMA.md`; as faixas `:441` e `:462-470` conferem.
  **Ajuste:** path completo nas duas citações (`:20`, `:348`).
- **K12 (nota de forma, Critic-B) — o ponteiro do plano está errado nos prompts:**
  `.claude/plans/PLAN-188.md` NÃO existe (o arquivo é
  `.claude/plans/PLAN-188-shared-ceremony-toolkit.md`; `.claude/plans/PLAN-188/`
  é o diretório de materiais). Corrigir onde o runbook o cita.

## Single-agent insights rejected / deferred

- **DEFERIDO (Critic-C, R-SEC6):** `ceremony-lint.yml:52-57` faz `json.load` do
  waivers sem `try` num step `if: always()`, enquanto o lint é fail-CLOSED em
  waivers ilegíveis (`check-ceremony-script.py:293-301`). Verificado e real, mas
  é defeito PRÉ-EXISTENTE do workflow, fora do mandato desta revisão: some o
  SUMÁRIO, não o gate. Vai como land livre de docs/CI, não como must-fix do
  PLAN-188.
- **ABSORVIDO (Critic-B, R-DO7):** «o controle vermelho da invariante 10 exige
  chaveiro GPG descartável e nenhum runner o semeia» — verificado
  (`validate.yml:341-359` é o único step de shell relevante e não tem `gpg`).
  Não é achado separado: é exatamente o custo que a OQ-9 tem de passar a cobrir
  (D5 + K1). Registrado ali.
- **NÃO RE-LITIGADO:** OQ-1 (número `ADR-2xx` e wave da emenda), OQ-2/OQ-8
  (ordem das subwaves, destino dos clones), OQ-4 (5 chaves de orçamento), OQ-5
  (corrigir × congelar o classificador), OQ-6 (`_CANONICAL_GUARDS`) — são do
  Owner por desenho. Nenhuma delas esconde decisão que trave a W0. As DUAS que
  travam artefato da W0 estão promovidas acima: **OQ-7** (leitor, K3) e **OQ-9**
  (executor do runner, D5+K1).

## Plan adjustments

| § do plano | mudança |
|---|---|
| §Approach:126-136 | a cura do C1 passa a nomear o PREDICADO de descoberta (diretório, não conteúdo; `.py` incluído) ou o gate que cobre `read_manifest.py`; o controle positivo vira um arquivo SEM token de cerimônia (D1) |
| §Approach:129-133 | «quatro das cinco classes» corrigido para cinco; decisão escrita e por arquivo sobre `CEREMONY-LINT: handwritten-exception:` × `AUTO-GENERATED` (D2) |
| §Approach (novo) | o ESCAPE do lint entra no plano: `ceremony-lint-waivers.json` (44 entradas, waiver por sha256 de conteúdo, override `--waivers`) — e a constatação de que ele e o checador são oráculo 0, kernel 0 e fora do ADR-192 (D3) |
| §Approach:129-136 | o alargamento da R8 reconcilia `check-ceremony-script.py:192-194` e declara o modo de invocação do toolkit (`bash <path>`, 100644), ou não alarga (D4) |
| §Approach inv. 3 (:236-240) | o BRAÇO do marcador é decidido antes da W0, com controle vermelho que reprove material MARCADO fora do self-test (K2) |
| §Approach inv. 10 (:270-281) | nomear o rail duplo do signatário (K10) |
| §Approach (novo) | escrever o ganho de custódia: sair das isenções de `check_contamination.py:299-301`/`:321-326` (K9) |
| §Riscos:313-322 | custo do quarto sítio medido ou alternativa nomeada — o job `smoke` é único, `timeout-minutes: 150`, ~1 h medido (K1) |
| §Items W0:359-389 | a divisão W0a/W0b nomeia ARQUIVOS (o `lib.sh` some hoje) e não chama de «manifesto» o que a W1 entrega (K4); por invariante, QUEM escreve o arquivo que o controle da W0 falsifica (K5) |
| AC-1:453-462 | Check da descoberta refeito (D1); a metade cara ganha executor nomeado (D5) |
| AC-2:471-474 | mapa pacote→path + controle POSITIVO, como o AC-3 (K6) |
| AC-3:486-503 | critério de morte pré-registrado: corpus `<PK>` indisponível ⇒ NÃO CONCLUSIVO (K7) |
| AC-4:512-513 | verificador mecânico do digest, ou declaração de que o pin é documental (K8) |
| AC-6:590-599 | absorve `check-ceremony-script.py` e `ceremony-lint-waivers.json`, ou o plano escreve o limite (D3) |
| Open questions | **OQ-7** promovida a pré-condição da W0 (K3); **OQ-9** alargada ao custo do quarto sítio e ao chaveiro GPG do controle da inv. 10 (D5, K1); **+OQ-10** proteção do lint e do seu arquivo de isenções, se o AC-6 não a absorver (D3) |
| §Context:20, §Items:348 | path completo nas citações do `PLAN-SCHEMA.md` (K11) |
| runbook/ponteiro | o plano é `.claude/plans/PLAN-188-shared-ceremony-toolkit.md`; `.claude/plans/PLAN-188.md` não existe (K12) |
| Progress log | entrada «round 2 sintetizado» |

## Round verdict

**RUN-ANOTHER-ROUND**

Regra aplicada: risco levantado por 2+ críticos ⇒ o plano MUDA (cinco findings,
D1-D5, todos aplicados); risco de um só crítico ⇒ decisão escrita do
sintetizador (12 mantidos com verificação em disco, 1 deferido, 1 absorvido).

Por que não `PROCEED`: os três críticos retornaram `ADJUST` com **10
bloqueantes somados**, e o rótulo **design-coherent NÃO é concedido** — ele
exige zero bloqueantes nas três críticas. O round 2 fez o que devia (12 dos 15
must-fix do round 1 estão FECHADOS e verificados em disco), mas os três
PARCIAIS são o mesmo eixo: a cura do C1 endereçou o LUGAR e não o MECANISMO,
e a doutrina desta casa é que rodada limpa prova a superfície revisada, não o
entregável. Um round 3 sobre o texto que absorver D1-D5 é barato; uma W0 que
land com um controle positivo verde-por-construção não é.

Por que não `ESCALATE-TO-OWNER`: nenhum dos dez bloqueantes pede arquitetura
nova nem reescreve o MODELO do plano — todos são o TEXTO da W0 (predicado de
descoberta, marca de proveniência, escape do waiver, escopo da R8, executor do
runner). As duas decisões que o Owner precisa dar ANTES da W0 já estão nomeadas
como promoções de OQ existentes (OQ-7 e OQ-9), e podem ser colhidas em PARALELO
ao round 3 — como foram as três do round 1.
