---
plan: PLAN-186
round: 4
archetype: VP Engineering
skill: architecture-decisions
scope: W5 — o TEXTO da doutrina Step 0 e a reconciliação skill+hook
tree_reviewed: sombra do pacote APLICADO, HEAD `2292979` + patch sha256 `fee3a477…` (conferido contra `W5DOCTRINE.patch.sha256`; 28 paths, 133 561 bytes)
verdict: ADJUST
blocking: 2
generated_at: 2026-09-05T03:40:00Z
---

## Verdict

ADJUST — **2 itens BLOQUEANTES**, ambos de uma linha, nenhum de modelo.

## Summary (≤ 3 bullets)

- **O modelo aguentou a auditoria de texto.** Os dois pares de espelho são
  byte-idênticos onde importa (`diff` do bloco Step 0 `.claude/team.md` ↔
  `team.en.md`: **vazio** sobre 63 linhas; `PROTOCOL.md` ↔ `PROTOCOL.pt-BR.md`:
  **vazio** sobre 105 linhas, com a divergência restante confinada ao ponteiro
  de cabeçalho, que já divergia em HEAD). Nenhuma âncora morta sobreviveu à
  renomeação do heading. Contagens derivadas batem com o disco (201 ADRs em 8
  superfícies = `ls .claude/adr/ADR-*.md | wc -l` = **201**), os dois geradores
  respondem `in sync`, e `CLAUDE.md` fecha em **39 853** bytes (margem 147).
- **Onde é forte:** o carve-out é definido pelo PRODUTO em **todos** os sítios
  de doutrina, com a frase que fecha a má-leitura («matching a ROUTING TABLE
  row is NOT, by itself, that carve-out»); e a skill DECLARA que o evento de
  auditoria que ela manda emitir **não pode ser emitido hoje** — isso responde
  a pergunta 4 da proposta pelo lado honesto: não é teatro, é dívida nomeada.
- **Onde é fraco:** um parágrafo entregue está **agramatical** e o DESIGN diz
  que foi curado; e o documento que vira o REGISTRO DO DEBATE cita um nome que
  a própria árvore aplicada rejeitou como invertido.

## Risks

**R-VP1 — P1 — BLOQUEANTE — `CHANGELOG.md` entrega um parêntese órfão e uma
frase sem sujeito, e o DESIGN §9 declara a classe curada.**
Verificado no bloco aplicado (`CHANGELOG.md:11-18`): o texto lê
«… refuses both a stale numeral and a rephrased label. Label / v1.3.0: 166
skills, 27 slash commands, 201 ADRs, 71 `_lib` modules) **are reproducible**
…». Balanço mecânico de parênteses do blockquote: **2 abre, 3 fecha**. O
`(` de «(as of v1.3.0:» foi removido pela cura da r9; o `)` ficou porque o
regex do gate `changelog/header` de `verify-counts.sh` exige o rótulo
CONTÍGUO **com** o `)` — de modo que o gate fica **verde sobre a prosa
quebrada**, e por isso nenhum dos 10 gates da bateria acusa. «Label v1.3.0:
… are reproducible» também perdeu o sujeito («Counts cited below»). O
`DESIGN-w5-doctrine-S344.md` §9 item 9 marca o achado com `~~tachado~~` e
«**CURADO na r9 (lane B, P1)**». A afirmação do DESIGN é falsa contra os
bytes finais.
*Já nomeado pelo CEO como R1 nas decisões r12 — este relato confirma que
sobrevive na derivação FINAL `fee3a477`, não numa anterior.*
*Mitigação:* curar pelo derivador restaurando sujeito **e** o `(`, mantendo o
rótulo intacto; e a célula de guarda que o CEO pediu (balanço de parênteses +
presença do sujeito) é o que impede a classe de voltar — porque o gate que
existe hoje é, por construção, cego a ela.

**R-VP2 — P1 — BLOQUEANTE — a proposta do round 4 cita um nome de evento que
a árvore aplicada REJEITOU como invertido; o registro do debate aterrissaria
contradizendo o que ele ratifica.**
`<SP>/debate-w5/round-4/proposal.md` (§US1 — reconciliação) diz: «dois valores
novos no vocabulário do evento de auditoria (`no_spawn_fixed_cost`,
**`no_spawn_judgment_carve_out`**)». A árvore aplicada
(`.claude/skills/core/parallelization-by-default/SKILL.md:271-277`) nomeia
`spawn_judgment_carve_out` — **sem** o `no_` — e registra por quê, no próprio
arquivo: «O segundo nome era `no_spawn_…` no primeiro rascunho e isso estava
INVERTIDO — a branch que ele nomeia é a que SEMPRE despacha (rail r10, P1)».
A proposta é, na sua área, mais velha que a cura que a wave pagou. Como o AC-7
se satisfaz com ESTE registro arquivado em `.claude/plans/PLAN-186/debate/
round-4/`, o repo passaria a carregar, na mesma pasta de plano, a decisão e a
sua versão refutada.
*Não consta das pendências R1..R7 do CEO.*
*Mitigação:* corrigir a linha na cópia que o CEO arquiva (é um `no_` a
remover) antes de copiar a rodada para `.claude/plans/`. Custo: uma palavra.

**R-VP3 — P2 — O hook é o ÚNICO dos 7 sítios que enquadra o carve-out por
«mandatory» em vez de por PRODUTO — exatamente a má-leitura que o rail r8 (P1)
curou em todos os outros.**
Censo da frase-chave na árvore aplicada: `PROTOCOL.md:210,251`,
`.claude/team.md:484,632,660`, `team.en.md:194,242,270`,
`.claude/commands/spawn.md:151`,
`.claude/skills/core/ceo-orchestration/SKILL.md:494`,
`templates/CLAUDE.md:26` e `parallelization-by-default/SKILL.md:45,94,142,177`
— **todos** dizem «INDEPENDENT JUDGMENT», e os canônicos acrescentam «matching
a ROUTING TABLE row is NOT, by itself, that carve-out». O
`_STEP0_DOCTRINE` de `.claude/hooks/check_anti_ceo_overhead.py:590` diz apenas:
«Check 2 covers DISCRETIONARY spawns only: **a mandatory reviewer** is out of
scope, never folded in». Não contém «INDEPENDENT JUDGMENT», não contém a
cláusula da ROUTING TABLE. Um leitor que casou uma linha da tabela (que é
`MANDATORY` no seu próprio título) pode ler «obrigatório ⇒ fora de escopo» —
a leitura que tornaria o Check 2 decorativo, e que os outros seis sítios
gastaram uma rodada de rail para fechar. Agrava que este é o sítio de MAIOR
leitura em voo: é a mensagem que o hook imprime no meio da sessão, e o único
que o adopter vê sem abrir um `.md`.
*Mitigação:* trocar «a mandatory reviewer» por «a spawn whose PRODUCT is
independent judgment (review, VETO, debate) — matching a routing-table row is
not, by itself, that carve-out». Cabe na constante; não muda semântica de
decisão (o texto é advisory, `decide()` não o lê), logo o controle POSITIVO
existente dos 37 testes continua valendo.

**R-VP4 — P2 — `PROTOCOL.md` §`/effort` scope clause enumera um conjunto de
tokens que NÃO inclui `xhigh`, e a W5 acabou de fazer de `xhigh` o fallback
que carrega a regra.**
`PROTOCOL.md:441` (não tocado pelo patch — `git diff PROTOCOL.md | grep -c
effort` = **0**) diz: «`/effort` slash-command tokens (`low|default|high|max`,
plus the `ultrathink` keyword) are CEO-only». `xhigh` é token legal desde antes
da wave (`git show HEAD:.claude/commands/effort.md:20,27,47,74`), então a
defasagem é **PRÉ-EXISTENTE** e está corretamente FORA de escopo. O que muda é
a consequência: a W5 torna `xhigh` o teto de R1 **e** o default declarado para
linha ambígua, de modo que a enumeração desatualizada do `PROTOCOL.md` passa a
omitir justamente o valor que a nova regra mais usa.
*Mitigação:* não curar aqui (seria alargar a wave e a superfície assinada).
Nomear em `DESIGN §9` como residual herdado, com o path e a linha, para que a
próxima sessão não o descubra como se fosse defeito da W5.

**R-VP5 — P3 — Linha em branco espúria em `templates/CLAUDE.md`**, entre o
bullet «Owner Routing» e «3-Strike» (visível no `git diff` do arquivo). Já
nomeada pelo CEO (decisões r12, item 4); sobrevive na derivação final.
Cosmética, mas é a raiz que o adopter RECEBE.

## Must-fix (blocking)

1. **R-VP1** — restaurar a gramática do preâmbulo do `CHANGELOG.md` pelo
   derivador, mantendo o rótulo que o gate lê, **e** re-derivar a afirmação do
   `DESIGN §9` a partir dos bytes aplicados (citar o parágrafo final). Uma
   afirmação de cura que os bytes desmentem é o defeito mais caro deste
   pacote, porque é a única que o revisor seguinte tende a acreditar sem ler.
2. **R-VP2** — remover o `no_` de `no_spawn_judgment_carve_out` na cópia da
   proposta que o CEO arquiva em `.claude/plans/PLAN-186/debate/round-4/`.

## Nice-to-have (advisory)

- **R-VP3** — reescrever `_STEP0_DOCTRINE` pelo PRODUTO. Não é bloqueante
  porque o texto é advisory e nenhum caminho de decisão o lê; é a correção de
  maior retorno por byte do pacote inteiro.
- **R-VP4** — declarar a defasagem do `PROTOCOL.md:441` como residual herdado.
- **R-VP5** — remover a linha em branco.

## Unseen by the original plan

- **A assimetria de numeração entre os espelhos de `team` é PRÉ-EXISTENTE e
  está corretamente intocada.** `.claude/team.md:717` numera «4. FILE
  ASSIGNMENT», `team.en.md:326` numera «3.» — porque `team.md` tem um item
  «SPEC CONTEXT (ADR-058)» que o espelho não tem. Confirmado em HEAD
  (`git show HEAD:.claude/team.md` → `660:4.`; `git show HEAD:team.en.md` →
  `269:3.`). Não é divergência criada pela W5; um revisor apressado a
  reportaria como tal.
- **O par `team.md` ↔ `team.en.md` não tem gate mecânico** (DESIGN §2.4: par
  intencionalmente excluído de `translations-pairs.yaml`), e a única coisa que
  os mantém juntos é a âncora idêntica no derivador. Isso funcionou **nesta**
  wave (medido: bloco idêntico). É frágil para a próxima: qualquer edição
  futura feita a mão, e não pelo derivador, diverge em silêncio. Vale um
  follow-up nomeado — não desta wave.
- **A renomeação do heading do Step 0 não quebrou nada.** `grep -rn '#step-0'`
  na árvore aplicada: **zero**; as duas únicas ocorrências do título antigo
  estão em `.claude/plans/PLAN-166/repass-r2/transcript-*.log`, que são
  transcrições históricas inertes.

## What I would NOT change

- **A escolha de não numerar o Check 2** («um múltiplo pequeno do próprio
  overhead»). O texto entrega a medição, a sua base (`agregado sobre 40 agentes
  triviais ÷ n`) e a inferência que faz dela, e diz explicitamente «an order
  of magnitude, **not a threshold** — the criterion below is a RATIO, not a
  number» (`PROTOCOL.md:241-244`). Um número fixo, com a dispersão que o
  PLAN-179 já mediu no análogo `F`, seria falsa precisão e convidaria a
  gaming. A resposta à pergunta 2 da proposta é: mantenha o razão.
- **A citação de Kim et al.** O texto separa o que o paper estabelece
  (desalinhamento arquitetura-tarefa) do que é inferência deste repo (ordenar
  a cadeia em série), nomeadamente, nos dois idiomas
  (`PROTOCOL.md:222-227`). Sobrevive a um revisor hostil, e respeita o
  `AGENTS.md`: fala em degradação MEDIDA pelo paper, nunca em ganho previsto
  aqui.
- **A honestidade do evento de auditoria.** A skill declara que
  `parallelization_recommended` **não está** em `_KNOWN_ACTIONS` (331 entradas)
  e que `audit_emit` descarta ação desconhecida em silêncio — verificado:
  `grep -rn 'no_spawn_fixed_cost'` na árvore inteira devolve **um** hit, o do
  próprio texto da skill. Declarar a dívida no ponto de uso é a forma certa; um
  «MUST emit» sem essa nota é que seria a mentira.
- **Manter `PROTOCOL.pt-BR.md` byte-idêntico ao EN nos blocos novos.** O
  arquivo já é de conteúdo inglês com ponteiro em português no cabeçalho
  (verificado em HEAD), e o par tem gate estrutural bloqueante
  (`translations-drift.yml`). Traduzir só estes blocos criaria a divergência
  que o gate existe para impedir.
