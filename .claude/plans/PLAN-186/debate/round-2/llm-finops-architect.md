---
round: 2
archetype: LLM FinOps Architect
skill: llm-routing-and-finops
agent_persona: LLM FinOps Architect (Principal, advisory — NO VETO)
generated_at: 2026-09-02T18:20:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- **Dos meus 6 must-fix do round 1: 4 RESOLVIDOS, 2 PARCIAIS, 0 não resolvidos.**
  RESOLVIDOS — (2) piso VETO, em §W3 + AC-5, e o plano foi além do que pedi: `~9 sítios
  derivados mecanicamente`, `VETO_HARDCODE` + `VETO_HARDCODE_APPLY` com o sha256
  regenerado no mesmo patch, um oráculo por sítio, controle positivo com spawn real;
  (3) precedência `inherit` × pin, em §W0-US4 + AC-10, com a W3 explicitamente gated
  nela; (4) desenho do A/B, em §W2, que trocou os quatro pontos (ABBA em duas semanas,
  custo de troca pré-registrado, contagem de bloqueios como primária, censura tratada)
  e pôs o MDE no AC-4; (6) AC-1, reancorado no que a W0 provou, com AC-1b abrindo a
  integração que segue pendente.
- **PARCIAL (1) envelope de custo:** aceito a refutação. `PLAN-SCHEMA.md:324` define
  mesmo `budget_tokens` como «CEO-context token range», minha aritmética comparava
  contra a unidade do instrumento, e adotar 1,25 G tornaria o plano incomparável. A
  estrutura que eu pedi chegou inteira (unidade declarada, `budget_tokens_billable_est`,
  `budget_usd_estimate`, `tier_mix_estimate` em dois blocos, `tier_mix_rationale` com a
  recusa de Haiku registrada). O que resta é outro defeito, verificável na unidade do
  PRÓPRIO schema: R-FIN16.
- **PARCIAL (5) eixo da matriz:** §2b trocou o eixo exatamente como pedi, mas o
  artefato que a W1 vai aplicar ainda codifica o eixo antigo, e nenhum AC prova a
  conformidade entre os dois. R-FIN15.

## Risks

### R-FIN15 — HIGH — o derivador da W1 codifica o eixo que a §2b substituiu, e o AC-3a não vê a diferença

§2b lista, na classe **DEFINE uma pergunta → `claude-opus-5`**, os termos «gate, oráculo,
instrumento, **censo**, critério de aceite, refutação». O derivador da W1
(`.claude/plans/PLAN-186/w1/apply-w1-explicit-model.py`, descrito como pronto e com
patch sha256 pinado) atribui `claude-sonnet-5` a quatro sítios, entre eles:

| sítio | rótulo no derivador | como o DESIGN-W1 §2 o descreve | §2b |
|---|---|---|---|
| `nightly-hygiene.js` | `hygiene:${d.key}` → `claude-sonnet-5` | «9 agentes de **censo** read-only» | DEFINE ⇒ Opus 5 |
| `audit-fanout.js` | `find:${d.key}` → `claude-sonnet-5` | 8 finders por dimensão | DEFINE (produz claims) |
| `council-audit.js` | `lane:${vendor}` → `claude-sonnet-5` | lane de auditoria | DEFINE (produz claims) |

O primeiro é inequívoco: o próprio material de origem chama de censo, e censo está
nomeado na lista DEFINE. §2b admite o problema sem resolvê-lo — «o classificador de
"tarefa especificada" é entregável da **W5-US2** — enquanto não existir, a regra não
decide nada» — mas a **W1 roda antes da W5**, e o texto da W1 diz «roteados pela matriz
§2b». O AC-3a exige só «zero `agent()` sem `model:`, provado pelo campo servido»: passa
verde com a classificação antiga aplicada sob o nome da regra nova.

Consequência de custo, e ela é grande: se três dos quatro sítios Sonnet viram Opus 5, o
que sobra da economia da W1 no caminho de workflow é o `eval:batch`. Somado ao fato 5
(«NÃO É FATO até re-derivação»), a W1 entra na fila sem número de retorno em nenhum dos
dois caminhos.

**Mitigação (~15-25k tokens, dentro da W1, 0 sessão extra):** re-classificar os 10
sítios sob o eixo §2b e regravar o derivador ANTES do land; o AC-3a ganha uma segunda
perna — «o `model` de cada sítio bate com a classe §2b do sítio, tabela publicada». Se
o Owner preferir esperar o classificador da W5-US2, então a W1 sai da frente da W5 no
sequenciamento e isso fica escrito. As duas rotas servem; ficar como está, não.

### R-FIN16 — MEDIUM — o campo tem unidade, mas a âncora que o calibra está desatualizada 3,6×, e `PLAN-SCHEMA:328` é o sítio que o varrimento de folclore da S325 perdeu

Aceita a refutação sobre a UNIDADE, sobra a CALIBRAÇÃO. Quatro linhas abaixo da
definição que refutou minha aritmética, o mesmo bloco declara:
`PLAN-SCHEMA.md:328` — «Each new session pays gate-boot cost **~27k tokens**».

Este repo mediu esse piso: `F = 97.292` na fronteira de uma compactação real, com
controle independente cold-F em `97.097`, n=41, spread de 51,7 % da média (CLAUDE.md §5,
S322). Censo mecânico: **`PLAN-SCHEMA.md:328` é a ÚNICA ocorrência de `~27k` na
superfície de governança**, e nenhum dos 10 arquivos que carregam a medição de 97k é o
PLAN-SCHEMA — ou seja, o varrimento dos «outros 9 sítios do folclore» da S325 passou por
cima justamente do sítio que calibra o `budget_tokens` de todos os planos.

Aritmética na unidade do próprio schema, para este plano: 9-12 sessões × ~97k =
**873k-1,164M só de gate-boot**. O plano declara `850k-1.45M`. O limite INFERIOR é menor
que o piso de boot da contagem mínima de sessões, e o superior deixa ~286k para o
trabalho das sete waves. A quebra por wave confirma que o boot não está contado: W1 =
40-80k para 1 sessão, abaixo do piso de boot daquela sessão.

Não é defeito de unidade nem de comparabilidade — os outros ~15 planos herdam a mesma
âncora e por isso continuam comparáveis entre si e errados juntos. É exatamente a classe
«instrumento verde cuja pergunta envelheceu», e este é o plano que tem o instrumento
para notá-la.

**Mitigação (~5-8k tokens, 0 sessão extra):** uma linha no frontmatter dizendo se o
gate-boot está DENTRO ou FORA do campo e, se fora, um `budget_tokens_gateboot: 875k-1.17M`
ao lado, para o total ficar visível. E a **OQ-6 ganha uma segunda cláusula**: além de
qual das três definições é normativa, se o boot entra no campo e qual é a âncora — com
`PLAN-SCHEMA:328` nomeado como sítio a corrigir (o valor honesto é uma faixa, não uma
constante: spread de 51,7 % em n=41). Não peço recalibrar os outros planos aqui; peço
que a OQ-6 pare de perguntar só metade.

### R-FIN17 — MEDIUM — a transição do piso VETO não tem fim declarado, e o piso efetivo é o membro mais fraco

A W3 decide, com razão, que «os DOIS ids ficam aceitos no piso durante a transição»,
para que o rollback seja mudança de settings e não uma segunda cerimônia GPG. Com isso
`VETO_FLOOR_ALLOWED` passa a quatro membros: `claude-opus-4-8`, `claude-fable-5`,
`claude-opus-5`, `claude-fable-5-1`. Como o piso é MEMBRESIA num conjunto, o piso
efetivo é o membro mais fraco — hoje `claude-opus-4-8`, uma geração inteira atrás — e o
comentário no código declara a doutrina aditiva («the previous flagship stays valid
during migration (intentional N-1 tolerance window)»). Nenhuma cerimônia de despejo
existe, e a palavra «transição» não vem com gatilho: por omissão ela é permanente, que é
como o conjunto chegou a três membros.

Levantei isto no round 1 («Unseen» item 2); não foi adotado nem refutado no consenso —
saiu em silêncio. A revisão o torna mais material, não menos, porque adiciona o quarto
membro.

O ângulo do revert silencioso do `set-quality-profile.sh` (que deriva o modelo de
`VETO_HARDCODE`, hoje `claude-fable-5`, e reescreve os pins) **está coberto**: o AC-5 já
exige `VETO_HARDCODE` + `VETO_HARDCODE_APPLY` com o sha256 regenerado no mesmo patch, e
essa asserção é em tempo de import. Por isso classifico MEDIUM e não bloqueante.

**Mitigação (~3-5k tokens, dentro da W3):** o sentinel da W3 declara o GATILHO que fecha
a transição (p.ex. «após N dias sem spawn VETO servido em `claude-fable-5`, medido pelo
detector permanente da W1/K2») e a cerimônia que remove o id. Uma linha, na assinatura
que já vai acontecer.

### R-FIN18 — LOW — o bloco `seat` do `tier_mix_estimate` descreve uma wave, não o plano

`seat: {fable_5_1: 0.50, opus_5: 0.50}` é o split do A/B, e o comentário diz isso
(«50/50 durante o A/B da W2»). Mas a W2 é 1 sessão de 9-12 e 30-50k de 850k-1.45M: nas
outras ~8-11 sessões o assento roda o que o pin disser (hoje `claude-opus-5` em
`.claude/settings.json:772`, ou `claude-fable-5-1` se o Owner escrever
`settings.local.json`). O bloco que existe para descrever 71,6 % da conta descreve ~4 %
das sessões do plano. É o único campo novo do frontmatter que ainda não fecha.

**Mitigação:** duas linhas — `seat` do período W2 e `seat` das demais sessões — ou uma
única linha com o pin corrente e a nota de que a W2 o divide por desenho.

## Must-fix (blocking)

1. **Reconciliar o derivador da W1 com o eixo §2b** (R-FIN15): re-classificar os 10
   sítios sob DEFINE/EXECUTA e regravar o derivador antes do land, OU mover a W1 para
   depois do classificador da W5-US2 e escrever a mudança de sequência. Em qualquer das
   duas, o AC-3a ganha a perna que compara o `model` de cada sítio contra a classe §2b
   publicada — sem ela o AC fica verde sobre a classificação antiga.
2. **Declarar se o gate-boot está dentro do `budget_tokens` e corrigir a âncora**
   (R-FIN16): uma linha no frontmatter (com `budget_tokens_gateboot` se estiver fora) e
   uma segunda cláusula na OQ-6 nomeando `PLAN-SCHEMA:328` como sítio de folclore
   remanescente, com faixa em vez de constante.

## Nice-to-have (advisory)

1. Gatilho e cerimônia que fecham a transição de dois ids no piso VETO, escritos no
   sentinel da W3 (R-FIN17).
2. `tier_mix_estimate.seat` desdobrado em período-W2 e resto do plano (R-FIN18).
3. A W2 escolhe qual das três opções de tratamento do custo de troca vai usar — o plano
   hoje escreve «Escolher UMA: (a)/(b)/(c)» e deixa a escolha para a execução. Escolher
   agora é o que torna o pré-registro pré.
4. A tabela de decisão da W2 fica sem ramo para o caso em que o MDE declarado no AC-4
   sair acima de 20 %: a regra «Opus ≥ 20 % melhor ⇒ adotar (iii)» dispararia sobre
   ruído. Um ramo «MDE > 20 % ⇒ estender ou não decidir» fecha o buraco sem mudar o
   desenho.

## Unseen by the original plan

1. **A OQ-6 pergunta metade.** Ela pergunta qual das três DEFINIÇÕES é normativa, mas
   não pergunta o que compõe o campo escolhido. Duas autoridades podem concordar na
   definição («CEO-context») e discordar sobre se o gate-boot conta — e é o gate-boot
   que domina em planos de muitas sessões curtas, que é a forma deste. A pergunta
   normativa completa é «definição + composição + âncora».
2. **O eixo novo é mais caro que o antigo, e ninguém re-precificou.** A partição por
   blast radius mandava «canônico/KERNEL → Opus»; a partição por incerteza de
   especificação manda «tudo que DEFINE uma pergunta → Opus», e no corpus de workflows
   deste repo isso é a maioria dos sítios (finders, censos, lanes de auditoria são
   todos produtores de claims). Trocar o eixo foi correto por qualidade — foi o meu
   pedido e mantenho — mas ele reduz a economia esperada da W1, e nenhum número do
   plano reflete isso ainda. O plano deve declarar que a W1 passou a ser uma wave de
   CORREÇÃO DE ROTEAMENTO, não de economia, até a re-derivação do C2 dizer outra coisa.

## What I would NOT change

1. **A refutação da minha própria aritmética.** Foi feita contra o disco, com o número
   de linha certo, e a conclusão está correta: adotar a unidade do instrumento tornaria
   este plano incomparável com os outros ~15. Escalar para OQ-6 repo-wide em vez de
   consertar localmente é a decisão certa — é a diferença entre curar a classe e criar
   a quinta grafia, a mesma lição que a K1 aplica ao roteamento.
2. **A W3 gated na resposta da W0-US4.** Uma cerimônia GPG que espera uma sonda de três
   spawns é o sequenciamento correto, e o plano ainda registra que o estudo recomendava
   não mexer. É assim que uma reversão de recomendação deve aparecer.
3. **Fato 5 marcado «NÃO É FATO» e fato 9 dividido em RAZÃO/ABSOLUTO.** Preferiu-se
   marcar o número contaminado a apagá-lo. Quem ler depois vê o que foi retirado e por
   quê — é a forma que impede a restauração silenciosa.
4. **`tier_mix_rationale` registrando a RECUSA do Haiku com a razão.** Pedi isso no
   round 1 exatamente para que um editor futuro não «restaure» a linha mais barata do
   estudo; está escrito com o critério de torneio (n≥30/célula, gap≥25pp) junto.
5. **O enforce de `model` nascendo como emissão visível `spawn_model_recorded`, com
   flip por variável UNSET.** É a forma measure-first que o
   `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` já provou nesta casa, e é o oposto do reflexo
   de ligar o gate no mesmo patch que o introduz.
6. **AC-11 (runner-minutos ≤ 1,3× do baseline) como AC e não nota de rodapé.** Um alvo
   de wall-clock sem teto de minutos faturados é a definição de otimizar a métrica
   errada; o plano agora tem as duas pernas e gated contra o teto do PLAN-184.
