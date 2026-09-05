---
plan: PLAN-186
round: 4
archetype: LLM FinOps Architect
skill: llm-routing-and-finops
agent_persona: LLM FinOps Architect (Principal, advisory — NO VETO)
scope: W5 — o TEXTO da doutrina Step 0 (US1, US2, US3)
tree_reviewed: pack w5-doctrine APLICADO (sombra do builder, 28 paths)
generated_at: 2026-09-05T04:20:00Z
---

## Verdict

ADJUST — **2 blocking**, ambos de UMA cláusula, nenhum toca o MODELO.

`design-coherent`: **SIM quanto ao modelo** (C-K3/C-K4/C-K5/C9 sobrevivem
intactos ao meu escrutínio). O ADJUST é sobre o TEXTO, que é o que esta
rodada foi contratada para achar.

## Summary (≤ 3 bullets)

- **Os três alarmes da minha lente foram verificados e NÃO dispararam.** O
  número carrega insumos em todos os sítios que o citam; a subordinação do
  «>=3» está feita; e o evento que a skill exige é declarado impossível **com
  a contagem certa** — eu re-derivei por AST: `_KNOWN_ACTIONS` tem
  **331** entradas e `parallelization_recommended` **não** é membro
  (`.claude/hooks/_lib/audit_emit.py:156`). Superfícies geradas
  regeneradas: 201 ADRs em disco, **201** citados em 8 docs.
- **O que o CEO não viu é o mesmo defeito de FinOps duas vezes: a fronteira
  do carve-out não tem CARDINALIDADE, e o número não tem POPULAÇÃO.** O
  carve-out isenta uma CLASSE, não «o revisor exigido» — três refutadores
  em paralelo (doutrina desta casa) são ~285 k de custo fixo que o Check 2
  nunca pesa. E os ~95 k foram medidos na classe MAIS BARATA de spawn
  (`general-purpose`, `effort: low`, 3 comandos) e aplicados à classe cujo
  prefixo é estritamente maior (spawn nomeado com `## SKILL CONTENT`
  inline). O viés é de SUBESTIMAÇÃO e não está escrito.
- **Uma dívida nasce sem dono:** `FU-PARALLELIZATION-ACTION-REGISTER` existe
  só dentro de um blockquote de skill, e o único instrumento do repo que
  cobriria a classe é cego a ela por construção.

## Risks

### R-W5-1 — P2 — o carve-out do Check 2 não tem limite de CARDINALIDADE

Os quatro sítios definem o carve-out pelo PRODUTO («julgamento independente
sobre trabalho de outro») e dizem que ele «nunca é dobrado no assento» e
«nunca é descartado por serem poucos itens»:
`PROTOCOL.md:245-247`, `.claude/team.md:655-662`,
`.claude/commands/spawn.md:149-155`,
`.claude/skills/core/ceo-orchestration/SKILL.md:494`.

Nenhum deles diz quantos. Verificado: `grep -n "second reviewer|more than
one|redundan|cardinal"` sobre os quatro sítios ⇒ **0 hits**.

A proposta enuncia o limite certo — «o custo fixo não pode remover **um
revisor exigido**» — mas o texto que aterrissa isenta a **classe**, não o
mínimo exigido. Consequência operável, e ela já é doutrina desta casa:
«refutação = 3 fornecedores em paralelo» (`CLAUDE.md` §5, lição da S344).
Três refutadores = 3 × ~95 k ≈ **285 k de custo fixo que o Check 2 é
proibido de olhar**, porque cada um deles é, individualmente, «julgamento
independente». O critério que existe para impedir que o fan-out pague o
custo fixo N vezes tem um buraco exatamente no lugar onde este repo
despacha N.

**Cura (uma cláusula, nos quatro sítios):** o carve-out cobre o revisor que a
tabela EXIGE; um SEGUNDO revisor do MESMO produto é discricionário e volta a
ser avaliado pelo Check 2. Isso preserva 100 % do que o P1 da r3 protegia
(nenhum revisor exigido some) e fecha o único caminho pelo qual o Check 2 vira
decorativo por multiplicação.

### R-W5-2 — P2 — a POPULAÇÃO medida não é a população que a regra governa

A sonda: «agentes `general-purpose` em `model: sonnet` …, `effort: low`,
tarefa fixa de 3 comandos Bash»
(`.claude/plans/PLAN-186/w0/concurrency-probe-S339.md`, §Método).

O Step 0 governa **spawn nomeado**, que por contrato carrega
`## AGENT PROFILE` + `## SKILL CONTENT` (corpo inline) + `## PROMPT DEFENSE`
+ `## FILE ASSIGNMENT` (`CLAUDE.md` §4, spawn protocol). O prefixo de um
spawn nomeado é **estritamente maior** que o do agente medido.

Os sítios dizem tudo o que precisa ser dito sobre o *n* e sobre a inferência
— «aggregate over 40 trivial agents divided by n», «MEASURED = that aggregate
over n; “fixed, before any work” is INFERENCE» (`PROTOCOL.md:234-241`,
`.claude/team.md:649-655`, `.claude/commands/spawn.md:144-147`,
`.claude/skills/core/parallelization-by-default/SKILL.md:80-88`) — e
**nenhum** diz de que classe de agente o número veio. Um número sem
população é um número sem insumo, mesmo com o *n* declarado.

Direção do viés, que é o que importa para a decisão: **subestima**. Check 2
com um piso baixo demais **sub-bloqueia** — despacha trabalho que não paga o
próprio overhead. Errar para o lado permissivo é o lado seguro para
governança e o lado ERRADO para a quota, que é a moeda que o PLAN-186
escolheu. Uma cláusula resolve: «medido em agentes `general-purpose` sem
skill inline; um spawn nomeado carrega prefixo maior, logo isto é um PISO».

### R-W5-3 — P2 — a dívida do evento nasce sem dono e sem instrumento

A nota da skill é o melhor parágrafo do pacote: declara que o evento **não é
emissível hoje**, dá a contagem (331) e o nome do followup
(`.claude/skills/core/parallelization-by-default/SKILL.md:281-290`).
Verifiquei os dois fatos por AST; ambos verdadeiros.

Mas `FU-PARALLELIZATION-ACTION-REGISTER` aparece em **exatamente um lugar em
toda a árvore aplicada** — esse blockquote. Não existe
`PLAN-186-FOLLOWUP-<slug>.md` (há 4 followups em `.claude/plans/`, nenhum
deste). E o instrumento que fecharia a classe é cego a ela por desenho: o
detector #6 do `reality-ledger.py` (`audit_action_phantom`) percorre AST
atrás de `emit_generic(action="…")` **em call-sites**
(`.claude/scripts/reality-ledger.py:686-740`) — ele vê ação EMITIDA e
ausente do registro, nunca ação DECLARADA que ninguém emite. Um «MUST emit»
que nada emite é invisível a ele para sempre.

Sem arquivo de followup, a próxima sessão só reencontra a dívida se abrir
essa skill nessa linha. É a classe que este repo já batizou: dívida nomeada
que nenhum gate pergunta.

### R-W5-4 — P3 — dentro de dois arquivos, a afirmação vem ANTES da correção

Duas vezes o mesmo formato: quem entra pelo meio lê a versão pré-correção.

1. `.claude/skills/core/parallelization-by-default/SKILL.md:31`
   (`audit_action: parallelization_recommended`, frontmatter
   *machine-readable*) e `:214` («CEO MUST emit … at dispatch time») — a
   correção está em `:281`, 67 linhas depois.
2. Mesmo arquivo, `:56` traz `~95k` **sem** procedência; a procedência
   completa está em `:80-88`, 24 linhas ADIANTE.

Nada disso é falso; é ordem de leitura. Uma cláusula de 6 palavras em `:214`
(«— see §Audit emit hint: not registrable today») e um ponteiro em `:56`
fecham os dois.

### R-W5-5 — P3 — a doutrina passa a ser paga em TODA disparada do hook, e ninguém orçou isso

`_STEP0_DOCTRINE` mede **827 caracteres ≈ 206 tokens** (medido no arquivo
aplicado) e entra nos DOIS caminhos: o `systemMessage` advisory
(`.claude/hooks/check_anti_ceo_overhead.py:687-702`) e o `reason` de bloqueio
do fallback P4/P5 (`:738-745`). O orçamento de volume que a própria skill
publica é **<=50/hr**
(`.claude/skills/core/parallelization-by-default/SKILL.md:292-295`). No teto:
~10 k tokens/hora de doutrina repetida no assento, num repo cujo `F` de
gate-boot é 97.292.

Não é caro; é **não-medido**, numa wave cuja tese é que custo fixo não
declarado é o defeito. Basta uma linha no ADR-198 §Consequences ao lado de «o
que fica mais lento».

### R-W5-6 — P3 — o hook diz «measured mean» onde os seis sítios dizem «aggregate ÷ n, e o resto é inferência»

`.claude/hooks/check_anti_ceo_overhead.py:585-587`: «~95k context tokens per
agent, the measured mean over 40 trivial agents». A média É o agregado sobre
n, então não é falso — mas é a única superfície da wave que **larga** a
distinção inferência/medição que os outros seis sítios carregam com cuidado,
e é a superfície que o CEO lê no meio de uma decisão de dispatch. Três
palavras («per agent — an inference») alinham.

## Onde o texto pode falhar depois de landado

1. **Por multiplicação, não por violação** (R-W5-1): ninguém desobedece o
   Check 2; o CEO simplesmente declara cada spawn «julgamento independente» e
   despacha seis. O texto atual autoriza isso.
2. **Por piso baixo** (R-W5-2): a razão «múltiplo pequeno do overhead» é
   calculada contra um overhead menor que o real, e o Check 2 aprova
   despachos que não se pagam.
3. **Por esquecimento** (R-W5-3): a próxima wave que tocar a skill lê «MUST
   emit» em `:214`, não desce até `:281`, e «fecha» a classe registrando o
   nome sem a allowlist de campos — o falso-verde que o ADR-198 §Residual já
   descreve para o Check 1, na outra ponta.

## O que falta para o AC-7

O AC-7 (`.claude/plans/PLAN-186-orchestrator-operating-model.md:209`) pede
quatro coisas: 6 sítios, reconciliação com a skill e o hook, ADR, e debate
`design-coherent`.

- **6 sítios:** presentes e coerentes entre si nas quatro asserções que
  testei (dependência, custo fixo, carve-out, ordem). OK
- **Reconciliação skill+hook:** feita, e o Fail-Fast está subordinado no
  texto que eu li
  (`.claude/skills/core/parallelization-by-default/SKILL.md:49-63`) — a
  pergunta 3 da proposta está respondida SIM para a seção Fail-Fast e SIM
  para a lista de critérios (`:70`, `:80`, `:100`). OK
- **ADR:** ADR-198 declara os dois residuais e recusa o falso-verde. OK
- **`design-coherent`:** da minha lente, **sim** — nenhuma das minhas
  descobertas contradiz o modelo; todas são cláusulas ausentes no texto.

**Falta, para a ASSINATURA (não para a coerência):** R-W5-1 e R-W5-2, que são
duas cláusulas; e o arquivo de followup do R-W5-3, que é um arquivo. O pacote
também ainda não tem materiais de cerimônia (item 3 do
`CEO-DECISIONS-r12-S345.md` no pack), mas isso é execução do CEO, não texto
de doutrina — não o conto como bloqueio meu.

## Must-fix (blocking)

1. **Cardinalidade do carve-out** (R-W5-1) — a isenção cobre o revisor
   EXIGIDO; um segundo revisor do mesmo produto volta ao Check 2. Nos quatro
   sítios que enunciam o carve-out, com a mesma âncora byte-idêntica que o
   derivador já usa nos pares de espelho.
2. **População do número** (R-W5-2) — uma cláusula, nos sítios que citam os
   ~95 k, dizendo que a medição veio de agentes `general-purpose` sem skill
   inline e que por isso o valor é um **PISO** para spawn nomeado.

## Nice-to-have (advisory)

1. Criar `PLAN-186-FOLLOWUP-parallelization-action-register.md` e apontar a
   nota da skill para ele (R-W5-3). Um arquivo.
2. Ponteiro em `SKILL.md:214` e `:56` para a correção que vem depois
   (R-W5-4).
3. Uma linha em ADR-198 §Consequences com os 206 tokens/disparada e o teto de
   50/hr (R-W5-5).
4. Alinhar a frase do hook com a dos seis sítios (R-W5-6).
5. A proposta desta rodada nomeia `no_spawn_judgment_carve_out`; a skill
   aplicada usa `spawn_judgment_carve_out` (a r10 registrou a inversão como
   P1 e curou). Se o `proposal.md` for copiado para
   `.claude/plans/PLAN-186/debate/round-4/`, ele entra no repo nomeando um
   valor de vocabulário que não existe — corrigir na cópia ou anotar a errata.

## Unseen by the original plan

1. **O Check 2 tem um caminho de fuga que não exige má-fé — a
   multiplicação.** O debate inteiro discutiu se o carve-out era largo demais
   por CLASSE; ninguém perguntou por QUANTIDADE. É a pergunta de FinOps, e é a
   única forma pela qual o Check 2 pode virar decorativo sem que uma linha do
   texto seja violada.
2. **O número mede o agente mais barato que este repo despacha.** A wave
   protegeu o leitor de ler «medido» como «fixo» e de ler «~95 k» como
   limiar, mas não de ler um piso como estimativa central. As três ressalvas
   presentes empurram todas na mesma direção (não trate como exato); a que
   falta empurra na direção oposta e é a única com sinal conhecido.
3. **A honestidade da nota do evento tem custo zero de gate.** Declarar
   «isto não pode ser emitido hoje» é a coisa certa e nenhum instrumento do
   repo verifica que continua verdade — nem que deixou de ser. O detector #6
   olha para o outro lado da mesma parede.

## What I would NOT change

1. **O critério continuar sendo uma RAZÃO e não um número.** Com n=1 por
   célula e o análogo `F` com spread de 51,7 %, um limiar numérico seria
   Goodhart imediato. A pergunta 2 da proposta está respondida: não-numérico
   é o certo — e com a cláusula do R-W5-2 fica também honesto.
2. **O hook carregar as perguntas que ele não sabe responder.** Não é teatro
   (pergunta 4): o texto diz explicitamente que o hook conta eventos e que
   contagem não autoriza dispatch, e a rota de recuperação
   (`CEO_OVERHEAD_ACK=1`) está no mesmo parágrafo — sem ela a mensagem
   mandaria ficar num assento que o próprio hook bloqueia. Semântica de
   decisão intacta, teste por substring e não por texto exato
   (`.claude/hooks/tests/test_anti_ceo_overhead.py`,
   `Step0DoctrineMessageTest`) — acoplamento frágil evitado.
3. **A leitura de Kim et al.** (pergunta 9): as classes de tarefa são
   nomeadas como do paper, os **+80,8 %** aparecem ao lado dos **−70,0 %**, e a
   ordem serial é rotulada «THIS repo's inference» (`PROTOCOL.md:218-224`).
   Sobrevive a revisor hostil, e é mais do que a maioria das citações deste
   repo entrega.
4. **A nota de leitura sobre os EXEMPLOS «Correct»**
   (`.claude/skills/core/parallelization-by-default/SKILL.md:219-236`):
   admitir que exemplos anteriores à medição prescrevem dispatches que o
   critério 2 recusaria, e adiar a reescrita para wave própria, é a forma
   certa de não fingir coerência retroativa.
5. **O R7 sem forma exportável** (pergunta 10): a linha declara que
   `/effort` não exporta o teto do assento e que ele vale como doutrina
   (`.claude/commands/effort.md:110-114`). Regra aplicada pelo próprio
   regulado vale a linha quando está escrito que é isso que ela é — o oposto
   seria fingir enforcement.
6. **Não mexer em comportamento de gate nesta wave.** Doutrina primeiro,
   janela advisory depois, enforcement por último é a sequência que esta casa
   já provou.
