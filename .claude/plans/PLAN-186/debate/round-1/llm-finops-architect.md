---
round: 1
archetype: LLM FinOps Architect
skill: llm-routing-and-finops
agent_persona: LLM FinOps Architect (Principal, advisory — NO VETO)
generated_at: 2026-09-02T16:40:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano acerta o diagnóstico (herança, não política) e acerta a moeda (a decisão
  do assento é de quota, não de dólar). A W1 é a alavanca certa e está pronta.
- O envelope de custo do próprio plano é o item mais fraco: `budget_tokens:
  850k-1.45M` está entre **21× e 49× abaixo** do consumo medido de 9-12 sessões
  descontando cache read, e **850×-1.900×** abaixo em tokens brutos. Não há
  `tier_mix_estimate` nem `budget_usd_estimate`. O plano que existe para tornar o
  custo falsificável declara um orçamento que o instrumento dele refuta na primeira
  execução.
- Duas armadilhas mecânicas fecham waves inteiras: `claude-fable-5-1` **não está**
  em `VETO_FLOOR_ALLOWED`, e a precedência entre `CLAUDE_CODE_SUBAGENT_MODEL=inherit`
  e o pin de arquétipo nunca foi medida — ela decide se a W3 tem efeito de custo e
  se o piso VETO é enforcement ou papel.

## Risks

### R-FIN1 — CRITICAL — o `budget_tokens` não é denominado na mesma unidade do instrumento

Medido agora, mesma janela de 30 d, mesmo resolvedor de projeto
(`ceo-cost-transcripts.py --since 30d --by session`), 56 sessões de assento:

| grandeza | por sessão (mediana) | 9-12 sessões |
|---|---:|---:|
| tokens brutos | 137,3 M | 1,24-1,65 G |
| tokens sem cache read | 3,47 M | 31,2-41,6 M |
| USD API-equivalente | $147,08 | ~$1.324-1.765 |

O plano declara `budget_tokens: 850k-1.45M` para 9-12 sessões. Contra tokens brutos
o erro é de 850× a 1.900×; contra a classe faturável sem cache read é de 21× a 49×.
**Uma única sessão mediana, já descontado o cache read, consome 2,4× o teto do
orçamento inteiro do plano.** Não há `tier_mix_estimate` nem `budget_usd_estimate`
no frontmatter. Pela minha AC-1 de skill isso é BLOCKED por si só, e aqui é pior que
o normal: é o plano de FinOps que herda o defeito que veio corrigir.

**Mitigação:** declarar a unidade explicitamente e derivá-la do instrumento. Proponho
`budget_tokens: 1_250_000_000` (brutos, mediana × 9) com `budget_tokens_billable:
31_000_000` (sem cache read) e `budget_usd_estimate: 1_400`. O `tier_mix_estimate`
tem de ser **dois blocos**, assento e subagente, porque são camadas de controle
diferentes (T e P) e o assento é 71,6 % do gasto medido ($7.523,68 de $10.514,26):
mexer só em subagente move 28 % da conta.

### R-FIN2 — CRITICAL — `claude-fable-5-1` não está no piso VETO; a W3 como escrita quebra os 5 spawns

`.claude/hooks/_lib/agent_frontmatter.py:135` define
`VETO_FLOOR_ALLOWED = {claude-opus-4-8, claude-fable-5, claude-opus-5}`. `claude-fable-5-1`
**não é membro**. Os 5 arquivos de arquétipo (`code-reviewer`, `security-engineer`,
`identity-trust-architect`, `incident-commander`, `threat-detection-engineer`) hoje
declaram `claude-fable-5`. Se a W3 landar só os 5 pins,
`validate_veto_floor_models` reporta violação nos cinco e `check_agent_spawn.py`
— fail-closed por contrato — passa a bloquear todo spawn VETO. O corpo da W3 diz
«`VETO_FLOOR_ALLOWED` coerente» em quatro palavras; o **AC-5 não nomeia esse path**,
e AC é o que a cerimônia verifica.

O raio também é maior que «5 arquivos + settings»: 9 arquivos de teste leem essa
superfície (`test_veto_floor_bijection.py`, `test_adr149_validator_parity.py`,
`test_available_models_mirror.py`, `test_adr_052_role_to_model_coverage.py`,
`test_model_routing.py`, entre outros).

**Mitigação:** reescrever o AC-5 para exigir, no MESMO patch assinado, a entrada de
`claude-fable-5-1` em `VETO_FLOOR_ALLOWED` + a emenda ADR-052/ADR-149 + os 9 arquivos
de teste verdes, e um controle POSITIVO: um spawn VETO real servido e verificado pelo
campo `model` da resposta, não por grep.

### R-FIN3 — HIGH — a precedência `inherit` × pin de arquétipo nunca foi medida, e ela decide duas coisas

O relatório 05 §4.3 conclui que «`CLAUDE_CODE_SUBAGENT_MODEL: "inherit"` fecha o caso:
tudo que não é despachado com `model` explícito herda o assento». A skill
`llm-routing-and-finops` afirma o oposto para despacho nomeado: «Claude Code
substitutes that model at spawn». As duas não podem estar certas, e ninguém mediu o
caso decisivo — spawn de arquétipo nomeado **sem** `model:` explícito.

Consequências, ambas materiais:

1. Se `inherit` vence, o piso VETO **não é enforcement de runtime**: o hook valida que
   o ARQUIVO diz a coisa certa, nunca que o modelo SERVIDO obedece. Um `code-reviewer`
   despachado de um assento Sonnet roda Sonnet com o gate verde. Isso é uma falha de
   governança, não de custo, e é do tamanho do V-block.
2. Se o pin vence, a W3 é uma alavanca de dólar real e não a higiene de camada T que o
   plano descreve: `claude-fable-5` custa $1,00/MTok de cache read, 4× o 5.1 e 2× o
   Opus 5, e é a maior linha da fatura medida ($6.161,62 = 58,6 % dos 30 d).

**Mitigação:** a W0 ganha uma sonda de 3 spawns (um VETO, um IC, um `general-purpose`),
todos sem `model:`, com o modelo servido lido do transcript. É barata e responde à
pergunta que a W3 inteira pressupõe. O AC-3 já tem a forma certa («pelo campo `model`
da resposta servida, não por grep») — falta aplicá-la ao piso VETO, não só aos workflows.

### R-FIN4 — HIGH — o A/B tem um custo de troca assimétrico que enviesa a favor da hipótese testada

Alternar o modelo do assento dia a dia invalida o prompt cache a cada troca: cada dia
re-paga um gate-boot frio. Este repo já mediu esse piso — `F ≈ 97.292` tokens na
fronteira de uma compactação real, com spread de 51,7 % da média em n=41 (CLAUDE.md §5).
O problema não é o custo em si, é que **ele é assimétrico entre os braços**: cache write
do `claude-fable-5-1` é $12,50/$20,00 por MTok contra $6,25/$10,00 do `claude-opus-5`.
O braço A paga o dobro pelo re-aquecimento que o desenho impõe, e paga isso dentro da
métrica primária («minutos úteis por janela antes do primeiro bloqueio»). O desenho
penaliza sistematicamente o braço cuja refutação ele busca.

**Mitigação:** ou (a) o primeiro turno de cada janela é excluído da métrica por
pré-registro, ou (b) as janelas são longas o bastante para o re-aquecimento virar ruído
e isso é declarado com número, ou (c) o custo de troca entra como covariável medida.
Qualquer das três serve; nenhuma está no plano.

### R-FIN5 — HIGH — os dois braços dividem UMA janela semanal, e só um deles tem teto de 50 %

O teto documentado de Fable é **50 % do limite semanal**, e o limite semanal é um
recurso único. Alternando A-B-A-B-A-B-A dentro de uma semana, o consumo de A no dia 1
reduz a folga de A no dia 7, enquanto B saca do mesmo bolso sem esse teto. Os braços
não são independentes e a ordem de depleção está confundida com o efeito de modelo:
o dia 7 (braço A) é estruturalmente pior que o dia 1 (braço A) por construção, o que
produz exatamente o resultado «Fable esgota mais rápido» mesmo se os modelos forem
idênticos.

Somam-se dois problemas de poder: com n=3-4 janelas por braço e um spread medido de
$147 (mediana) a $481 (p90) por sessão — 3,3× — um efeito de 20 % não é detectável;
e «minutos até o primeiro bloqueio» é uma observação **censada à direita** nas janelas
que nunca bloqueiam, sem tratamento definido. O critério «< 4 janelas ⇒ inválido» é
piso de quantidade, não de poder.

**Mitigação:** contrabalançar em duas semanas (ABBA/BAAB) para que cada braço veja
início e fim de janela semanal, pré-registrar o tratamento das janelas censadas (p.ex.
métrica secundária «% da janela consumida ao fim das 5 h», que é observável sempre), e
declarar o efeito mínimo detectável com o spread medido. Como (a) `/usage` já foi
medido como não-provador de exaustão nesta casa (`five_hour`=35 % no instante de uma
recusa `session limit`, S328), o instrumento primário deve ser a contagem de eventos de
bloqueio, com `/usage` como secundário.

### R-FIN6 — HIGH — o split 80/20 que sustenta o −$1.369/mês vem do corpus contaminado pelo defeito de dedup

A W0 isolou que a chave `(requestId, apiBlockIndex, message.id)` do relatório 05 não
colapsa por mensagem nos 58 arquivos mais novos, inflando `claude-fable-5-1` em
~2,7-2,9×. O próprio relatório da W0 (§3.4) registra que a tabela §2.1 do 05 — o
night-run S338 — deriva **inteiramente** desses arquivos. Essa tabela é a única fonte
do split «builders 80 % / refutadores 20 %», que por sua vez é a hipótese de mix que
produz o **−$1.369/mês** citado como fato #5 do plano.

O agravante é mecânico e não está registrado em lugar nenhum: a inflação é **por bloco
de conteúdo por mensagem**, e o perfil de blocos difere por papel — builders emitem
muito `tool_use`, refutadores muito `thinking`/`text`. Logo o fator de inflação não é
constante entre os dois grupos e **o próprio split 80/20 é um artefato do instrumento
defeituoso**, não só os dólares absolutos.

**Mitigação:** re-derivar o split com o instrumento novo sobre os mesmos 7 transcripts
do S338 antes de citar o −$1.369 de novo. É uma execução de 3 s. Se o split mudar, a
ordem de retorno das waves muda com ele.

### R-FIN7 — HIGH — a matriz roteia MODELO por blast radius enquanto a regra de effort roteia por incerteza de especificação

A regra declarada é «effort escala por incerteza de especificação, não por blast
radius». A coluna de modelo faz o contrário: «builder canônico / KERNEL → Opus 5» e
«builder livre / docs → Sonnet 5» é uma partição por raio de dano. E dentro da própria
tabela a regra de effort está invertida: o refutador — que precisa **inventar** a
falsificação, o papel de maior incerteza de especificação da matriz — recebe `xhigh`,
enquanto o builder canônico, que trabalha contra uma spec escrita, recebe `max`.

Isso responde à pergunta 1 da proposta com um caso concreto. A classe de defeito
dominante deste repo não é «código canônico errado», é **«instrumento verde cuja
pergunta envelheceu»** — um gate/oráculo/derivador que responde a pergunta errada com
convicção. Essa classe mora quase toda no balde «builder livre» (censos, oráculos,
docs gerados) e é justamente a que o refutador estrutural**mente** não pega: o rail
revisa a SUPERFÍCIE do diff e aprova um check plausível (CLAUDE.md: «rodada limpa prova
a superfície revisada, não o entregável»). Sonnet 5 num derivador anchor-exact é
seguro; Sonnet 5 escrevendo o ORÁCULO que decide se o derivador está certo, não é.

**Mitigação:** trocar o eixo. A partição deve ser «o artefato DEFINE uma pergunta
(gate, oráculo, instrumento, censo, critério de aceite) → Opus 5» versus «o artefato
EXECUTA uma derivação com pergunta já fixada (anchor-exact, rename, docs a partir de
fonte) → Sonnet 5». Isso mantém o −$1.369 quase inteiro (a W1 é derivação pura) e
fecha o buraco que a partição por blast radius deixa aberto.

### R-FIN8 — MEDIUM — o critério de morte não é falsificável

«Dois P1 consecutivos que o refutador não pegue ⇒ reverter» não nomeia (a) o canal
que detecta o P1 que o refutador perdeu, (b) a janela, (c) o denominador. Sem canal de
detecção o critério só dispara por acidente: se o defeito passar e nunca for
encontrado, o critério nunca fira — ausência de resultado sendo lida como aprovação.
«Consecutivos» também não tem sequência definida (waves? patches? rodadas?).

**Mitigação:** canal = o LAND (bateria + V-block) e o CI pós-land, que são os dois
lugares onde um P1 que passou pelo rail aparece; janela = 6 waves ou 30 dias, o que
vier primeiro; denominador = P1 por wave com builder Sonnet, comparado ao histórico
de waves com builder Opus (o repo tem os dois: `wave-fable51` 7 achados em 5 rodadas,
PLAN-179 83 defeitos em 27 rodadas).

### R-FIN9 — MEDIUM — o AC-1 é insatisfazível como escrito, e a proposta apresenta a W0 como entregue

O AC-1 exige que **`ceo-cost.py --since 30d`** reproduza o total do relatório 05 com
delta ≤ 2 %. Três coisas impedem isso simultaneamente: o que foi construído é um
script SEPARADO (`ceo-cost-transcripts.py`; a limitação #4 do relatório da W0 diz
explicitamente que a integração com `ceo-cost.py` e `budget-summary.py` continua
aberta); o delta medido é 5,6 %, acima do teto; e a W0 demonstrou que **o número de
referência é que está errado**. Ainda assim a proposta lista a W0 em «Evidência já
produzida» sem marcar o AC como não atingido.

**Mitigação:** reancorar o AC-1 no que a W0 provou — «o instrumento reproduz
`claude-fable-5`, `claude-opus-5` e `claude-opus-4-8` byte a byte em todas as 5 classes
de token, e a reconstrução deliberada do defeito converge a +0,41 % do total publicado»
— e abrir um AC próprio para a integração em `ceo-cost.py`, que é o item 3 da sequência
recomendada do estudo e o único que torna tudo o resto falsificável.

### R-FIN10 — MEDIUM — a W3 reverte a recomendação explícita do estudo sem evidência nova

O relatório 05 §5.1 linha 2 diz, sobre os pins VETO: «manter... é a única onde
recomendo **não mexer**: o ganho é ~$5/sessão e o custo é uma cerimônia sobre
`VETO_FLOOR_ALLOWED`». A W3 faz exatamente a cerimônia que o estudo desaconselhou, e
o plano não registra o que mudou de evidência entre os dois documentos. Ao mesmo tempo,
o «~$5/sessão» do estudo é contradito pela tabela do próprio estudo (§1.2: subagentes
em `claude-fable-5` = **$682,12** em 30 dias) e essa quantia nunca foi atribuída a
causa — é herança de um assento historicamente em fable-5, ou é o pin sendo honrado?
É a mesma pergunta do R-FIN3, e é ela que decide se a W3 vale $0 ou ~$500/mês.

**Mitigação:** a sonda do R-FIN3 resolve os dois. Com a resposta, ou a W3 ganha uma
justificativa de custo declarada, ou é rebaixada a higiene de camada T e pode esperar.

### R-FIN11 — MEDIUM — a W4 tem AC de relógio sem teto de minutos faturados

O AC-6 mede wall-clock (Validate ≤ 14 min, Smoke ≤ 45 min). Uma matriz que corta 55 %
do relógio triplicando os jobs sobe os **runner-minutos totais**, e nenhum AC enxerga
isso. O plano remete o custo ao PLAN-184 mas define o critério de sucesso sem ele: é
possível passar o AC-6 e piorar a conta. Além disso, replicar `checkout+deepen` por job
reencontra exatamente o defeito de S327 (checkout raso ⇒ o hash-gate não vê a geração
v1.2.0 ⇒ `STALE 3` em vez de 0), agora multiplicado pelo número de células.

**Mitigação:** AC-6 ganha uma segunda perna — runner-minutos totais ≤ 1,3× do
baseline pré-matriz, medida em 3 runs. E o «teste de matriz correta» que o plano já
prevê inclui um controle de profundidade de histórico por célula.

### R-FIN12 — MEDIUM — o Step 0 (W5) barateia a decisão de fan-out sem modelo de custo do fan-out

A sonda da W0 mediu ~**95 k tokens de contexto por spawn** (prefixo do harness +
`CLAUDE.md` + skills), quase todo cache read. A W5-US1 torna o teste de decomposição
mais permissivo em um eixo (dependência sequencial) sem acoplar o custo fixo: 14
concorrentes são ~1,33 M tokens de overhead por barreira, antes de qualquer trabalho.
O plano trata Step 0 como alavanca de velocidade e a §2 do próprio plano já contém a
frase certa — «paralelismo não cria quota, gasta-a mais rápido» — sem transformá-la em
regra operável.

**Mitigação:** a doutrina do Step 0 declara o custo fixo por spawn (medido, não
estimado) e um piso de trabalho: um agente cujo trabalho útil esperado não excede
alguma múltipla do próprio overhead de contexto não deve ser despachado — deve virar
uma chamada de ferramenta no assento.

### R-FIN13 — LOW — 4 pins de IC ficaram em `claude-sonnet-4-6`, uma geração atrás

`qa-architect`, `devops`, `performance-engineer` e `llm-finops-architect` declaram
`model: claude-sonnet-4-6`. O cache read desse id é $0,30/MTok contra $0,20 do
`claude-sonnet-5` — 50 % mais caro para a mesma classe de trabalho — e a W3 não os
inclui. Se a resposta do R-FIN3 for «o pin vence», esses 4 são over-spend silencioso;
se for «`inherit` vence», são documentação apodrecida que o `check-model-deprecations.py`
da higiene noturna vai eventualmente sinalizar.

**Mitigação:** incluir os 4 no escopo da W3 (não custa cerimônia adicional — é a mesma
assinatura) ou declarar por escrito que ficam fora e por quê.

### R-FIN14 — LOW — o §1 do plano corrige o total de 30 d mas carrega os números inflados do night-run

O fato #1 da tabela de contexto aplica a correção da W0 (−5,6 %); o fato #9, três
linhas abaixo, cita «assento US$ 457 de US$ 681» — números que vêm de `05 §2.2`, ou
seja, exatamente dos arquivos que a W0 mostrou estarem inflados ~2,8×. O documento
fica auto-contraditório na mesma tabela. As RAZÕES de §2.2 sobrevivem (A/B/C são
contrafactuais sobre o mesmo perfil, a inflação cancela: −14,2 % e −38,9 % continuam
válidos; a proporção «o assento custa 2× o fan-out» também), mas os **absolutos não**:
o ganho real do cenário C naquele night-run é da ordem de $30, não de $87.

**Mitigação:** anotar em cada número derivado do S338 se ele é razão (sobrevive) ou
absoluto (inflado ~2,8×), ou re-derivar os sete transcripts com o instrumento novo.

## Must-fix (blocking)

1. **Reescrever o envelope de custo do frontmatter** (R-FIN1): `budget_tokens` com a
   unidade declarada e derivada do instrumento (bruto e faturável), `budget_usd_estimate`,
   e `tier_mix_estimate` em **dois blocos separados, assento e subagente**, com
   `tier_mix_rationale` citando a medição. Sem isso o plano não tem envelope, tem um
   número.
2. **AC-5 passa a exigir `claude-fable-5-1` em `VETO_FLOOR_ALLOWED` no mesmo patch
   assinado** (R-FIN2), com a emenda ADR-052/ADR-149, os 9 arquivos de teste da
   superfície verdes, e um spawn VETO real verificado pelo campo `model` servido.
3. **Acrescentar à W0 a sonda de precedência `inherit` × pin de arquétipo** (R-FIN3):
   3 spawns sem `model:` (um VETO, um IC, um `general-purpose`), modelo servido lido do
   transcript. A W3 não deve ser desenhada antes dessa resposta, e o resultado é uma
   afirmação de governança sobre o piso VETO, não só de custo.
4. **Recorrigir o desenho do A/B da W2** (R-FIN4 + R-FIN5): contrabalanceamento em duas
   semanas, tratamento pré-registrado do custo de troca assimétrico, tratamento das
   janelas censadas, efeito mínimo detectável declarado contra o spread medido, e
   contagem de eventos de bloqueio como instrumento primário no lugar de `/usage`.
5. **Trocar o eixo da matriz de modelo de blast radius para incerteza de especificação**
   (R-FIN7): «define uma pergunta» → Opus 5; «executa uma derivação» → Sonnet 5. Isso
   é a resposta direta à pergunta 1 da proposta e preserva quase toda a economia.
6. **Reancorar o AC-1** (R-FIN9) no que a W0 efetivamente provou, e abrir AC separado
   para a integração em `ceo-cost.py`/`budget-summary.py`, que segue aberta.

## Nice-to-have (advisory)

1. Re-derivar o split builder/refutador com o instrumento novo sobre os 7 transcripts
   do S338 antes de voltar a citar o −$1.369/mês (R-FIN6). Custa 3 s de execução.
2. Segunda perna no AC-6: runner-minutos totais ≤ 1,3× do baseline pré-matriz (R-FIN11).
3. Incluir os 4 pins de IC em `claude-sonnet-4-6` no escopo da W3, ou declarar a
   exclusão por escrito (R-FIN13).
4. Anotar por número do §1 se ele é razão ou absoluto quando derivado do S338 (R-FIN14).
5. Declarar os limiares de burn-rate do plano (fast/medium/slow) no corpo, para que a
   resposta a um estouro esteja escrita antes de o estouro acontecer.
6. A sonda de concorrência está citada na proposta como se tivesse respondido a OQ-4
   («a sonda respondeu»), mas é n=1 por N e o AC-2 exige 3/3. Ou a citação recua para
   «indicativo», ou a sonda repete. Ela também mede só contenção de despacho numa
   tarefa trivial: não vê contenção de output nem a janela de 5 h, que é a restrição
   que de fato vincula.

## Unseen by the original plan

1. **O piso VETO pode não existir em runtime.** Se `inherit` vence o pin de arquétipo,
   `check_agent_spawn.py` valida o texto do arquivo e nunca o modelo servido — o piso
   é documental. O relatório 05 §4.2 já mediu essa divergência para arquétipos não-VETO
   («o `model` passado pelo dispatcher vence tudo») e ninguém estendeu a pergunta ao
   caso VETO. É a maior descoberta possível deste plano e ele não a persegue.
2. **`VETO_FLOOR_ALLOWED` é aditivo por doutrina e não tem cerimônia de despejo.** O
   comentário no código declara a intenção: «the previous flagship stays valid during
   migration (intentional N-1 tolerance window)». Como o piso é a MEMBRESIA num
   conjunto, o piso efetivo é o **membro mais fraco** — hoje `claude-opus-4-8`. Cada
   geração adicionada sem remover a anterior baixa o piso real enquanto parece elevá-lo.
   A W3 adiciona a quarta entrada sem tocar nisso.
3. **A conta do plano é dominada por uma linha que o plano não modela.** O assento é
   71,6 % do gasto medido e roda o tempo todo em que o plano é executado, independente
   de como os subagentes são roteados. Um `tier_mix_estimate` só de subagente descreve
   28 % da fatura — a mesma cegueira de instrumento que o estudo acabou de diagnosticar,
   reproduzida no plano que veio curá-la.
4. **A inflação do dedup é por bloco de conteúdo, logo é enviesada por papel.** Builders
   (`tool_use` denso) e refutadores (`thinking`/`text` denso) têm perfis de bloco
   diferentes, então o defeito não infla os dois igualmente. Isso não contamina só os
   dólares do night-run: contamina o **split 80/20** que é insumo de toda a §5.2. O
   relatório da W0 registrou que §2.1 está afetada, mas ninguém notou que o split
   herdado dela também está.
5. **O custo fixo por spawn é a variável que falta no Step 0.** 95 k tokens de contexto
   por agente significa que a decisão «decompor ou não» tem um piso de trabalho útil
   abaixo do qual o fan-out perde dinheiro e janela mesmo quando é logicamente
   paralelizável. O plano discute dependência e sobreposição; não discute tamanho mínimo.
6. **`claude-fable-5` é 58,6 % da fatura medida ($6.161,62 de $10.514,26)** e nenhuma
   wave deste plano o toca — a cura está numa cerimônia externa (`wave-fable51`). Vale
   registrar a dependência explicitamente no `depends_on`, porque a ordem de retorno
   das waves do PLAN-186 muda conforme aquela cerimônia tenha ou não landado.

## What I would NOT change

1. **A escolha de moeda.** Decidir o assento por quota e não por dólar está certa, e é
   a coisa mais difícil que o plano acertou. Os $318/mês de diferença entre os cenários
   não pagam nem uma sessão perdida por bloqueio de janela.
2. **A ordem: W1 antes de W3.** A camada P é livre, reversível e concentra a economia
   verificável; a camada T custa assinatura e depende de medições que ainda não existem.
   Mantenha essa ordem mesmo que a W3 fique mais atraente depois do R-FIN3.
3. **A recusa a Haiku.** O estudo recomendou `claude-haiku-4-5` para pesquisa/leitura
   (§5.1 linha 7); a matriz do plano trocou por `claude-sonnet-5` e fez certo. Haiku é
   PROIBIDO sem evidência de torneio (n≥30/célula, gap≥25pp) — a recomendação do estudo
   teria sido um achado CRITICAL da minha AC-4. Peço que a **razão** dessa troca fique
   escrita no plano, senão um editor futuro «restaura» a linha mais barata do estudo.
4. **Manter o V-block do LAND fora da paralelização.** Corrida na cadeia HMAC viva por
   um ganho de segundos é exatamente o trade errado, e o plano já o recusa.
5. **`model:` explícito como exigência do dispatcher, advisory antes de bloqueante.**
   É a forma que este repo já provou funcionar (a janela advisory do
   `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED`), e é o oposto do reflexo de ligar o gate no
   mesmo patch que o introduz.
6. **Instrumento antes de decisão.** Que o item de maior prioridade não economize nada
   e apenas torne o resto falsificável é a inversão correta de prioridade, e é a razão
   pela qual esta crítica pôde ser escrita com números em vez de opinião.
