---
plan: PLAN-186
round: 4
focus: W5 — texto da doutrina Step-0 (ADR-191-AMEND-1); rodada FOCADA da mesma série (rounds 1-3 = debate do plano, design-coherent)
scope: W5 (US1, US2, US3) — o TEXTO da doutrina, não o desenho da wave
created_at: 2026-09-05T03:00:00Z
source_plan: .claude/plans/PLAN-186-orchestrator-operating-model.md
pack: s344-packs/w5-doctrine (derivador + patch + 2 ADRs + 1 AMEND)
---

# PLAN-186 W5 — proposta para uma rodada FOCADA no texto da doutrina

> **O que esta rodada NÃO é.** O debate de PLANO já rodou: 3 rodadas, round 3
> = 3× ACCEPT, `design-coherent`. O MODELO da W5 não está em disputa —
> C-K3 (6 sítios), C-K4 (a regra existe com default oposto), C-K5 (`CONSUMES:`
> não exprime dependência) e C9 (custo fixo) já foram acordados e já mudaram o
> plano. Esta rodada revisa **o texto que aterrissa** e a **reconciliação
> skill+hook**, que são a superfície nova. O AC-7 exige `design-coherent`; é
> este o registro que o satisfaz.

## Tese

O Step 0 do Spawn Protocol decide por UMA variável — sobreposição de arquivos —
e uma tarefa perfeitamente sequencial com zero arquivos em comum passa por ele
sem atrito. A literatura quantifica o custo dessa lacuna (**−70,0 %** em
planejamento sequencial, Kim et al., arXiv:2512.08296) e a sonda da W0
quantifica um segundo custo que nenhuma regra modelava (**~95 k tokens de
contexto por spawn**, medido). Pior que a lacuna: a regra CERTA já existe na
skill `parallelization-by-default`, três linhas depois da regra que a
contradiz, e o hook `check_anti_ceo_overhead.py` empurra para o dispatch por
CONTAGEM, sem predicado de dependência. **Doutrina que não vence o predicado
que empurra para o dispatch é texto sem mecanismo.**

## O que muda

### US1 — Step 0 passa a ter TRÊS checagens, em ordem

1. **Dependência sequencial.** B consome a saída de A (arquivo, valor de
   retorno, veredito) ⇒ SERIAL, quaisquer que sejam os conjuntos de arquivos.
2. **Custo fixo por spawn.** ~95 k tokens de contexto por agente antes de
   qualquer trabalho; agente cujo trabalho útil esperado não excede um múltiplo
   pequeno do próprio overhead vira chamada de ferramenta no assento. **Vale
   para todo spawn DISCRICIONÁRIO, inclusive um único** (um agente sozinho
   paga o custo inteiro). Um spawn que a ROUTING TABLE torna obrigatório (code
   review de TODA mudança, dono de domínio VETO, participante de debate L3)
   está **FORA DO ESCOPO** do Check 2: não é avaliado, logo não passa nem
   reprova, e o Check 2 nunca encerra a decomposição por causa dele.
3. **Atribuição de arquivos** (o texto atual, inalterado) — só depois de 1 e 2.

O carve-out do item 2 não é ornamento: sem ele, o Step 0 novo **revoga em
silêncio** `.claude/team.md` §ROUTING TABLE («The CEO NEVER does the
specialist's work») e o «No merge without review by the merge-VETO staff
member» da skill `ceo-orchestration` — bastava a mudança ser pequena. Foi o
achado P1 da 3ª rodada de pair-rail. A frase que fixa o limite: **o custo fixo
pode encolher QUANTO trabalho é despachado; não pode remover um revisor
exigido.**

Nos 6 sítios do censo. Os dois pares de espelho viajam com a **mesma âncora
byte-idêntica** no derivador: editar um lado só é mecanicamente impossível.

### US1 — reconciliação (o item que dá mecanismo ao texto)

- `parallelization-by-default/SKILL.md`: dependência e custo fixo viram os
  critérios **1 e 2**; `>=3 itens ⇒ MUST` fica SUBORDINADA, na seção Fail-Fast
  E na lista de critérios. **A ordem no arquivo era o defeito** — e
  subordinar não bastou: a 9.ª rodada de rail mostrou que, com a contagem
  ainda escrita como REGRA, dois itens independentes que passassem no Check 2
  iam para o assento pela skill enquanto o `PROTOCOL.md` (que fala em «dois ou
  mais agentes», sem piso de três) permitia os dois spawns. A contagem passa a
  ser declarada **HEURÍSTICA**, proxy barato do Check 2, que **nunca** o
  sobrepõe. Na mesma rodada entraram o **passo 2-bis** do algoritmo de 5
  passos (que nunca avaliava o custo fixo e terminava despachando todos os N),
  dois valores novos no vocabulário do evento de auditoria
  (`no_spawn_fixed_cost`, `spawn_judgment_carve_out`) e uma nota de leitura
  sobre os EXEMPLOS «Correct», que são anteriores à medição do custo fixo.
- `.claude/commands/spawn.md`: ganha um **Step 4-bis — STOP**, fluxo de
  controle e não conselho. Sem ele a «exact sequence» ia do Step 4 ao Step 5 e
  chamava o Agent tool sem condição: quem seguisse o comando ao pé da letra
  ainda fazia o spawn que o Check 2 acabara de recusar.
- `templates/CLAUDE.md` (a raiz que o adopter RECEBE): mandava «IF a finding
  has an Owner → SPAWN that agent» sem condição, em 3 sítios. Numa árvore
  instalada, isso e o Step 0 seriam duas instruções obrigatórias
  incompatíveis. A cura usa a distinção que a própria doutrina faz: o
  JULGAMENTO do dono é sempre roteado; a EXECUÇÃO passa pelo Step 0.
- `check_anti_ceo_overhead.py`: a recomendação passa a CARREGAR as duas
  perguntas + «Count alone does not authorize dispatch», e — cura da r9 —
  também a rota de recuperação, porque a mensagem manda ficar no assento
  enquanto o próprio hook bloqueia o Edit que o assento precisa fazer.
  **Semântica de decisão byte-idêntica** (block/advisory/allow), com controle
  POSITIVO nos testes.

### US2 — teto de effort e citações

Teto por classe §2b em `.claude/commands/effort.md` (R1 `xhigh`; R2/R3/R4
`high`; R5 VETO `max`; R6 síntese/REDUCE `max`; **R7, a orquestração do próprio
assento, `high`**), com ponteiro para o classificador que o plano já shipou
(`docs/task-classifier-2b.md`, AC-14 — rotulado «Framework repo only», porque
ele NÃO viaja no `install.sh`). É TETO, não piso. **E é EXECUTÁVEL para as
seis linhas DESPACHADAS** — R7, a orquestração do próprio assento, não é
despachada, então não tem forma exportável e carrega o teto como doutrina:
a
`## Procedure` do comando ganhou um passo que resolve a linha §2b e **corta** o
pedido acima do teto (exportando o teto, dizendo qual linha resolveu), com
linha ambígua caindo em R1 (`xhigh` — ACIMA de todo `high`, ABAIXO dos dois
`max`: nunca corta R2/R3/R4, mas CORTA um R5 ou R6 genuíno) para que
ambiguidade não corte
trabalho real. Sem esse passo, «may never run above it» era uma regra que
ninguém executava (achado P2 da 3ª rodada). As 3 citações (arXiv:2503.13657, arXiv:2310.01798,
arXiv:2502.00271) entram no `PROTOCOL.md` §Verification cascade como
fundamento de V0–V3 e **da razão de existir do V3**, um parágrafo por idioma.

### US3 — ADR-199, dois ramos, decisão do Owner

Ramo A (emissão voluntária correlacionada, `session_id` sempre LOCAL de quem
emite + `sender_session_id` próprio, `body_digest` **CHAVEADO por correlação**
— um sha256 cru de corpo enumerável é oráculo de confirmação, a classe que o
ADR-079 já pagou com salt — e o veredito local do receptor, com
`refused-by-policy` obrigatório: sem registrar a recusa, laundering e
cooperação são indistinguíveis) vs. ramo B (incorrelação como limite ACEITO,
molde ADR-190). O emissor NÃO é implementado.

O custo do ramo A foi **corrigido para cima** na 3ª rodada e a correção importa
para a decisão: não são «duas linhas em `_KNOWN_ACTIONS`». O invariante do
próprio `audit_emit.py` manda toda ação nova sem branch dedicada para o
`else` **default-deny, descartando todos os campos do chamador** — o ramo A
exige branch de scrub por ação, allowlist de campos por ação e coerção de
valor. O ramo B continua custando um parágrafo.

## Os três ADRs

| arquivo | papel |
|---|---|
| `ADR-198-spawn-step0-dependency-and-fixed-cost.md` | a decisão do US1, com as opções REJEITADAS (manter contagem; `CONSUMES:` por arquivo) e o residual NOMEADO |
| `ADR-199-cross-terminal-coordination.md` | o US3, dois ramos, decisão do Owner |
| `ADR-191-AMEND-1-step0-decomposition-gate.md` | o par que a disciplina SEMVER exige para a edição MINOR do `PROTOCOL.md`, com o Sync Impact Report |

## Perguntas para os críticos (é aqui que a rodada ganha o seu custo)

1. **O texto do Check 1 é falsificável?** «B consome a saída de A» cobre
   arquivo, valor de retorno e veredito. Existe uma quarta forma de consumo
   que o texto deixa passar — estado compartilhado (índice git, sombra, pack
   em espera) que A muta e B lê?
2. **O Check 2 é operável sem virar Goodhart?** «Um múltiplo pequeno do
   próprio overhead» é deliberadamente não-numérico (os ~95 k vêm de UMA
   sonda; o `F` análogo do PLAN-179 tem spread de 51,7 %). Um número fixo seria
   melhor apesar da dispersão, ou pior por convidar a gaming?
3. **A subordinação do «>=3 itens» está feita nos DOIS lugares?** A seção
   Fail-Fast e a lista de critérios são lidas por caminhos diferentes; se só um
   for reordenado, a contradição sobrevive na leitura de quem abre o arquivo
   pelo meio.
4. **O hook está honesto?** Ele vê eventos de ferramenta, nunca um grafo de
   dependência nem o tamanho do trabalho. Carregar as perguntas no texto é a
   coisa certa, ou é teatro que faz o leitor achar que o hook checa o que ele
   não checa?
5. **O residual está declarado com força suficiente?** O ADR-198 diz que
   dependências de valor de RETORNO estão fora do alcance mecânico e que um
   check por arquivo que declarasse a classe fechada seria falso-verde. Falta
   alguma coisa para que a próxima sessão não «feche» a classe por engano?
6. **O ADR-199 enquadra a decisão do Owner sem empurrá-la?** Os dois ramos
   têm custo escrito — A: duas ações novas em `_KNOWN_ACTIONS` (331 hoje),
   MAIS branch de scrub, allowlist por ação e coerção de valor, tudo em
   KERNEL canônico com cerimônia GPG, mais um instrumento de reconciliação que
   não existe; B: um parágrafo. A distância entre eles cresceu quando o custo
   de A foi medido de verdade (rail r2/r4). Isso é enquadramento honesto ou
   já é o polegar na balança contra A?
7. **O carve-out de governança está desenhado na fronteira certa?** Hoje ele
   nomeia três classes (revisão de merge, dono de domínio VETO, participante de
   debate L3). Existe uma quarta classe de spawn obrigatório neste repo que o
   teste econômico ainda poderia comer — e nomear classes é a forma certa, ou
   isso pede um predicado («o spawn é exigido por uma tabela?») em vez de uma
   lista que envelhece?
8. **O corte do `/effort` erra para o lado certo?** Linha ambígua ⇒ R1
   (`xhigh`). `xhigh` fica ACIMA de todo `high` e ABAIXO dos dois `max`: o
   fallback nunca corta R2/R3/R4, mas CORTA um R5 (VETO) ou R6 (REDUCE)
   genuíno. A defesa é que essas duas linhas se ANUNCIAM. Um revisor hostil
   diria que o teto é contornável por alegação de ambiguidade E que o
   fallback corta justamente onde errar é irrecuperável — qual dos dois danos
   é o maior, e existe um terceiro default (recusar e perguntar) melhor que os
   dois?
10. **O R7 sem forma exportável é honesto ou é letra morta?** `/effort` não
   despacha o assento, então o teto de R7 é doutrina lida pelo CEO, não env
   var. Uma regra que só o próprio regulado aplica a si mesmo vale a linha na
   tabela, ou convida a tratá-la como decorativa?
9. **A citação de Kim et al. está bem usada?** O paper mede *desempenho de
   arquitetura por tipo de tarefa*, não *este repo*. O texto diz «−70,0 % em
   planejamento sequencial» como fato do paper, nunca como previsão sobre
   este repo — a leitura sobrevive a um revisor hostil?

## Restrições que a rodada NÃO pode relaxar

- `AGENTS.md`: nenhuma claim de speedup. O texto fala em degradação MEDIDA
  pelo paper, nunca em ganho previsto aqui.
- Nenhuma mudança de comportamento de gate. Se a rodada quiser enforcement,
  isso é OUTRA wave, com medição própria.
- A skill `ceo-orchestration` é Gate-2 cache-stable: a edição pertence a um
  commit de CLOSEOUT (DESIGN §5).
- Citação sem identificador resolvível é rejeição automática.
