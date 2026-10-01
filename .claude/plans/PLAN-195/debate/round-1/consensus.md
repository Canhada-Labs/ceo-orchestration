---
plan: PLAN-195
round: 1
rounds_synthesized: [round-1]
critics: [Critic-A, Critic-B, Critic-C]
agents_considered: [Critic-A, Critic-B, Critic-C]
verdicts: [ADJUST, ADJUST, ADJUST]
vetoes: "Critic-B (escopo estreito: cobertura/FPR/operabilidade) e Critic-C (W1 como especificada) — ambos CONDICIONAIS a texto no plano e na ADR-201, sem código"
claim_verification: "workflow wf_430c1885-742 (6 verificadores read-only, sem sonda): 36 afirmações — 28 TRUE, 8 PARTIAL, 0 FALSE; 1 achado novo (C16)"
external_lane: "Codex review --uncommitted em 3 rodadas: (1) proposta + 3 críticas — APPROVE; (2) + consolidação e plano — REJECT, 1 P2 (fail-closed de corpo de shell só com assinatura); (3) — REJECT, 2 P2 (checklist da W1-ADR desalinhado; controle negativo N de N incompatível com pacotes em sequência). Os 3 P2 procedem e foram corrigidos; regra de parada pré-registrada antes da 3.ª rodada: P2/P3 de texto corrigidos sem nova rodada."
round_verdict: RUN-ANOTHER-ROUND
design_coherent: false
consensus_adjustments: 14
decisions_revised_in_plan:
  - "Context — «formas DIRETAS seguem bloqueadas» restrito à grafia canônica; formas diretas irmãs nomeadas pela forma"
  - "Goal / Thesis — raiz = decisão posicional sobre fatiamento ingênuo; cura = UMA passada aditiva sobre posições de palavra de comando; «eleva o custo; residual declarado pela forma»"
  - "Alternativas — piso de literais na posição do verbo e ASK puro rejeitados"
  - "W0 — corrigir a frase das formas diretas; registrar que o PreToolUse é a única detecção para A/B"
  - "W1 → W1-ADR (PROPOSED) → W1a → W1b na mesma vaga; escopos, prova N de N, observabilidade, bateria, regra de parada do rail"
  - "W2 — herda a mensagem A3, a lacuna argv, o find limitado ao segmento e o contrato de cwd"
  - "OQ-1 corrigida (premissa do §4.4 era falsa); OQ-2/OQ-3/OQ-4 com direção do debate; OQ-8 e OQ-9 novas"
  - "Oráculo — 5 suítes e o gêmeo YAML na tabela"
  - "budget_tokens/budget_sessions refeitos"
synthesized_at: 2026-10-01T03:10:00Z
synthesized_by: CEO
synthesized_from: "texto anonimizado das críticas (anonymization-map.md guarda o mapa). Limitação declarada: o sintetizador é a mesma sessão que despachou os críticos e leu os arquivos com o nome; a anonimização foi aplicada à escrita da síntese, e cada decisão abaixo se apoia em afirmação conferida no disco, não em quem a fez."
---

# Consenso — PLAN-195, rodada 1

> **Escopo do veredito:** `design-coherent` (PLAN-134 W1) certifica só coerência interna do
> desenho entre as perspectivas forçadas; NÃO autoriza ship. Ship = cascata V0 → V1 → V2
> (rail Codex, único gate de verdade LLM) → V3 (GPG do Owner). Esta rodada NÃO chegou a
> `design-coherent`: há dois VETOs condicionais a confirmar e um conflito a fechar.
>
> **Divulgação:** repo público. Formas só em prosa; matriz privada só por id. O achado novo
> (C16) está descrito aqui pela forma; o detalhe concreto ficou na evidência privada do Owner.

## Verificação das afirmações (antes de consolidar)

Seis verificadores só-de-leitura conferiram 36 afirmações das críticas no código do HEAD
`96f2f635`, sem sondar o hook (`wf_430c1885-742`). Resultado: 28 TRUE, 8 PARTIAL, 0 FALSE. As
ressalvas que mudam texto:

- **C2c (piso de literais na posição do verbo):** a conclusão fica, mas «TODA grafia em glob»
  é falso — o piso conta os caracteres dentro de classe de colchetes. As grafias comuns ficam
  abaixo do piso e viram ALLOW; uma classe de colchetes com letras extras passa do piso. O que
  sustenta a decisão é outro fato, TRUE: a própria nota do arquivo (`cbs:3461-3466`) dá como
  exemplo do piso a posição de OPERANDO de interpretador, não a palavra de comando.
- **C9 (forense):** `canonical_edit_completed` emite com ou sem o prefixo `!`; só o
  `bash_canonical_bypass_invoked` exige `!`. O resto fica: o forense casa só 4 formas literais de
  escrita e não cobre destrutivo indireto nem alvo computado.
- **C7d (log):** a janela móvel de 7 dias dá 17 `bash_parse_failed_fail_closed` + 10
  `fact_gate_shadow_deny` (não 20/17); o total retido 685/685 com `session_id` vazio confere; não
  existe NENHUM evento de bloqueio de escrita canônica (coerente com C7a/C7b).
- **C8b (gêmeo YAML):** a entrada de here-doc do fuzzer é entrada de PARIDADE, não controle
  ALLOW garantido; o risco de deriva hook × YAML continua.
- **C20 (§4.4 do guards doc):** o «≤ 3 em 7 dias» é o orçamento de USO do kill-switch de
  bypass, não de falso-positivo de regra. A premissa da OQ-1 do plano estava errada.
- **C4b:** o laço externo do E3 aplica o nome de comando a todo token, então verbo depois das
  flags do `xargs` é visto pelos ramos do E3; para o TRIO a lacuna fica.
- **C13:** «8 rodadas do rail no E4» é inferido do maior número de rodada citado (r8).
- **C1c:** os valores de flag removidos na normalização são 5 grafias (3 opções), não 3.

**Achado novo da verificação (C16 — forma direta irmã, fail-open):** o tokenizador do E3 liga
comentários; o dos pedaços do trio (`shlex.split`, `cbs:322`) os desliga. Um pedaço pode falhar
no parse depois que o E3 passou, e o `continue` de `_recheck_whole_command` (`cbs:597-600`)
libera esse pedaço. Inferido por leitura e por medição do tokenizador com string inofensiva; não
sondado contra o hook. É mais uma forma da classe «o trio não vê o verbo» (Critic-C contou
4 ocorrências históricas) — reforça a cura estrutural.

## Consensus findings (2+ críticos)

1. **C1 — A raiz é a decisão posicional sobre um fatiamento ingênuo, não só a indireção.**
   Critic-A, Critic-C (Critic-B aceita a assimetria como descrita). Severidade: CRITICAL.
   Conferido: o trio decide sobre `tokens[0]` (`cbs:378`, `:433-437`, `:456`) de pedaços cortados
   só em `&&`, `||`, `;` e `|` (`cbs:275`, `:526-584`); sem casefold; `git` por posição fixa.
   Mitigação: a W1 entrega UMA passada nova sobre as posições de palavra de comando, no léxico do
   E3; o plano deixa de afirmar que «as formas diretas seguem bloqueadas» sem qualificação
   (`PLAN-195:90-91`). → Context, Thesis, W0, W1a.

2. **C2 — O piso de literais do E4 não é o instrumento para a posição do verbo.** Critic-A,
   Critic-C (Critic-B defendeu o piso em geral — ver conflito K2). Severidade: HIGH. Mitigação:
   regra do verbo computado = propagar atribuições literais do mesmo comando; se o verbo
   continua computado E o segmento traz marcadores destrutivos literais do trio, BLOCK; senão
   ALLOW com residual declarado. O piso continua sendo a ferramenta da W2 (alvo de caminho).
   Invariante na ADR-201: nenhuma forma que a passada reconhece recebe veredito mais permissivo
   que a sua forma direta. → Thesis, W1b, W2.

3. **C3 — `_scan_blob` não é peça reutilizável; o reuso real do E3/E4 é por leitura.** Critic-A,
   Critic-C. Conferido (C3a, C17): `_scan_blob` é closure dentro do laço do E3 e devolve caminho;
   as tabelas de runner, de flags, o padrão de atribuição, de substituição e a decodificação de
   aspas estáticas do E4 existem nas linhas citadas. Mitigação: E3 e E4 byte-idênticos na W1;
   reuso só por chamada/leitura. → Thesis, W1a.

4. **C4 — A-8 e A-9 não são recursão do trio; escopo e prova não fecham.** Critic-A, Critic-C.
   Severidade: MEDIUM/HIGH. Mitigação: extensão de vocabulário explícita na W1b — A-9 (escrita em
   dispositivo de bloco) entra com controle ALLOW para arquivo comum; A-8 vai para a OQ-8 (regra
   de forma ou sai da W1 e da prova). Nenhuma linha da matriz fica fora do alcance da cura. → W1b,
   OQ-8.

5. **C5 — Tamanho e orçamento subestimados; dividir a W1.** Critic-A, Critic-C. Referência de
   classe: o E4 ocupa `cbs:2450-3815` e chegou a r8. Mitigação: W1-ADR (`PROPOSED`) → W1a → W1b
   na MESMA vaga, cada uma ≤ 400 linhas e ≤ 8 paths; parte A ≈ 0,8–1,5 M tokens, 3–4 sessões. →
   W1, frontmatter.

6. **C6 — ASK puro não existe no hook; sem humano, ASK é travamento.** Critic-A, Critic-C.
   Conferido (C6): `Decision` só tem allow/block/rewrite-ask; `ask` só sai com `updatedInput`.
   Mitigação: a W1 emite BLOCK com mensagem acionável («escreva a forma direta; ela é julgada pelo
   próprio mérito»). O ponto de Critic-B sobre falso-positivo é tratado no conflito K1. →
   Alternativas, W1.

7. **C7 — A prova precisa ser mais forte.** Critic-A, Critic-C (Critic-B pede o mesmo pelo lado
   do controle legítimo). Mitigação: (a) no HEAD de antes de cada pacote, CADA linha NOVA
   daquele pacote em `TestIndirectDestructiveBlocks` falha (N de N das linhas novas), e as
   linhas de pacotes anteriores seguem verdes (correção pós-síntese, revisão Codex P2: a W1b
   roda sobre um HEAD que já contém a W1a); (b) cada linha afirma a classe do motivo (reason code), não só `allow=False` —
   mata o falso-verde do fail-closed cego do `_scan_blob` (C3b); (c) bateria combinatória (verbo
   × invólucro × grafia × separador × lançador da tabela do E4), com a matriz privada como
   semente, não como universo; (d) teste de aninhamento até o teto e acima dele. → W1a/W1b.

8. **C8 — Corpus de controle legítimo + replay offline para o falso-positivo.** Critic-A,
   Critic-B, Critic-C. Mitigação: (a) `TestIndirectLegitAllow` versiona um corpus sintético
   representativo (interpretador dirigido por variável, `xargs`/`find` não destrutivos, shell `-c`
   com verbo legítimo, texto destrutivo citado, here-doc para arquivo); (b) replay offline dos
   comandos Bash dos transcripts locais contra `decide_command` HEAD × cura, com `HOME` e
   `CLAUDE_PROJECT_DIR` isolados, sem executar nada; só CONTAGENS vão ao repo, o conjunto-delta
   fica privado e é classificado à mão. Meta: regras de equivalência com a forma direta = zero
   bloqueio novo legítimo; regras heurísticas com limite pré-registrado. → OQ-1, W1a/W1b.

9. **C9 — Bateria incompleta.** Critic-A (2 suítes de paridade), Critic-C (3 suítes do hook).
   Conferido (C12): as 5 existem e nenhuma está no plano. Mitigação: o Check de W1a/W1b/W2 roda
   `test_bash_posture_toggle_invocation.py`, `test_check_bash_safety_cp_chaining.py`,
   `test_check_bash_safety_h5_rewrite.py`, `test_byte_identity_fuzzer.py` e
   `test_byte_identity_harness.py`, além das 4 já listadas. → W1a, W1b, W2.

10. **C10 — Fail-closed de parse pelo precedente certo.** Critic-A, Critic-C. Conferido (C5,
    C16): o recheck é fail-open por pedaço; o `_scan_blob` é fail-closed cego. Mitigação: a
    passada nova anda no MESMO léxico do E3 (que já bloqueia a montante se falhar); para corpos
    de SHELL recursados (shell `-c` em qualquer grafia reconhecida, `eval` concatenado,
    here-doc/here-string para shell, corpo de função), falha de parse = BLOCK com ou sem
    assinatura do trio; a assinatura (precedente E4, `cbs:3644-3665`) só escolhe o
    `reason_code` e a mensagem. Nunca fail-closed cego em corpo não-shell. Teto de profundidade e
    tamanho iterativo ⇒ BLOCK acima do teto (crash em matcher é fail-open, `cbs:4227-4233`). →
    W1a. **Correção pós-síntese (revisão Codex `--uncommitted` da consolidação, P2):** a
    primeira redação dava BLOCK só COM assinatura; um corpo de shell numa grafia nova
    (aglomerado de opções) que não tokeniza e não tem assinatura cairia em ALLOW, enquanto o
    mesmo corpo pelo `-c` exato é bloqueado pelo E3 (`cbs:2307-2315`, `:2411-2415`) — violação
    do invariante de não-permissividade e do fail-closed de entrada. Corrigido no plano
    (Thesis item 6).

11. **C11 — Residuais declarados pela forma; Goal sem promessa impossível.** Critic-A, Critic-C.
    Mitigação: Goal, Success criteria e ADR-201 dizem «eleva o custo; residual declarado pela
    forma» (molde do E4); lista de residuais na ADR-201 e na §6.6 da W0 (APIs destrutivas da
    linguagem, script em arquivo, funções/aliases de chamadas anteriores, configuração que
    executa valor, variáveis de inicialização do shell, argumentos do `xargs` pela entrada
    padrão, verbo e argumentos totalmente computados). → Goal, Success criteria, W0, W1-ADR.

12. **C12 — OQ-3: `.mcp.json` e `CLAUDE.md` fora do PLAN-195.** Critic-A, Critic-B, Critic-C
    (3/3). Conferido (C11): oráculo 0 para os dois; o `CLAUDE.md` foi excluído de propósito,
    com motivo escrito. Mitigação: a W2 consome `_CANONICAL_GUARDS` como está; ampliar é decisão
    do guarda de edição canônica, em plano próprio (FU). → OQ-3.

13. **C13 — OQ-4: a lacuna argv é da W2.** Critic-A, Critic-B, Critic-C (3/3). Conferido (C4c):
    o ramo `-c` de interpretador faz `break` depois do corpo. → OQ-4, W2.

14. **C14 — Observabilidade e uma só origem de evento.** Critic-B (must-fix), Critic-A e
    Critic-C pelo desenho de um sítio só. Conferido (C7a/C7b): bloqueio de escrita canônica não
    emite nada; destrutivo direto só via shadow do fact-gate. Mitigação: `reason_code` distinto
    por classe nova (parte A e parte B), emitido UMA vez por comando a partir do único ponto de
    chamada, com `blocked_tool="Bash"` e técnica mapeada (paridade com o forense); a recusa nova
    leva `destructive=True` (paridade com a forma direta) MAIS o evento próprio. → W1a/W1b, W2.

## Single-agent insights kept

1. **Critic-A — arquitetura aditiva:** UMA chamada na cauda de `decide_command`, depois do laço
   legado e antes do `return` de ALLOW, com laço legado e `_recheck_whole_command`
   byte-idênticos. Mantido como direção da OQ-2: cobre o escopo dos DOIS sítios legados (anda no
   comando inteiro), tem um só ponto de evento (atende Critic-B) e uma só segmentação nova
   (atende o ponto de Critic-C sobre divergência — C16 mostra o custo de duas segmentações).
   Confirmação de Critic-C na rodada 2.
2. **Critic-A — paridade com o gêmeo YAML** (C8a/C19: YAML e `policy_preprocessors.py` são
   canônicos). A ADR-201 declara a relação (hook ⊇ YAML, asserção de mão única no teste não
   canônico, ou aposentadoria por FU); a W1 não toca os arquivos canônicos do gêmeo.
3. **Critic-A — rota de limpeza sancionada** (lição S358: agentes precisam apagar o próprio
   clone). A ADR-201 nomeia a rota (helper confinado invocado por caminho) e um teste a fixa
   como ALLOW.
4. **Critic-A — ADR-201 landa `PROPOSED`;** o flip vai no pacote de código que entrega o
   comportamento.
5. **Critic-A — mensagem A3 sai da W1 para a W2** (junto com a argv): a W1 não toca o E3. Custo
   aceito e declarado: entre W1 e W2, corpo destrutivo malformado segue BLOQUEADO pelo E3, mas
   com a mensagem de caminho canônico (ponto de Critic-C sobre ordem em `decide_command`).
6. **Critic-A — regra de parada do rail:** no máximo 4 rodadas por pacote; NO-GO só por P0 ou
   afirmação falsa; nova grafia de residual já declarado pela forma vai para o anexo da rodada
   final; P1 da mesma subclasse em duas rodadas seguidas ⇒ parar e estreitar a afirmação.
7. **Critic-A — W7a do PLAN-183 em voo junto:** quem landar por segundo roda a bateria do outro
   sobre a árvore composta.
8. **Critic-A — contrato de cwd** (C14: `NormalizedEvent` não tem `cwd`): a W2 declara que fecha
   só o `cd` intra-comando, ou passa a ler o `cwd` do stdin com teste.
9. **Critic-B — PreToolUse é a ÚNICA detecção para as classes A e B** (C9): a W0 registra isso no
   doc de ameaças.
10. **Critic-B — kill-switch próprio da passada nova**, separado do `CEO_BASH_RAWSCAN`, para que
    um falso-positivo não leve o operador a desarmar o rawscan inteiro (também nice-to-have de
    Critic-A).
11. **Critic-C — normalizador de palavra de comando compartilhado com o E4** (lançadores pela
    tabela do E4 com flag desconhecida = ambígua; `env` com divisão de string como CORPO; caixa
    baixa com `str.lower`; aspas estáticas; chaves por pertença; glob no nome contra os nomes do
    trio) e **gramática do git** (opção global antes do subcomando, opção destrutiva depois de
    operando). Itens a conferir na W1a; os que não estiverem em `cbs` conferido viram hipótese
    na ADR.
12. **Critic-C — escopo de recursão pela forma:** corpo de `-c` depois de aglomerado de opções
    com `c`; todos os argumentos do `eval`; argv depois das flags do `xargs`; `find` com
    `-exec`/`-execdir`/`-ok`/`-okdir`; substituição de comando em qualquer posição (inclusive
    entre aspas duplas e em here-doc de delimitador não citado); substituição de processo;
    subshell e grupo; corpo de função/alias definidos no mesmo comando; here-doc/here-string
    consumidos por shell. Texto de programa de origem não literal entregue a interpretador ⇒
    BLOCK (sujeito ao K1). Here-doc com destino a arquivo é DADO, com controle ALLOW.
13. **Critic-C — risco latente do piloto de citação** (C10: busca por substring sem filtro de
    papel; piloto desligado por padrão): a ADR-201 registra; armar o piloto exige filtro por
    papel `user` (FU).
14. **Critic-C — `find` do E3 varre além do segmento** (C4e; falso-positivo observado A3-5):
    entra na W2 (onda do E3).

## Single-agent insights rejected / deferred

1. **Critic-B — ASK nos corpos opacos** → não aceito como está (C6: não há canal de ASK puro; sem
   humano é travamento). A preocupação de fundo (FPR e pressão para desarmar o trilho) é
   aceita e vai para o K1, com proposta de saída na rodada 2.
2. **Critic-B — popular `session_id` no evento do hook** → adiado (nice-to-have; FU de
   telemetria). Para este plano, o painel de taxa é por PROJETO, declarado.
3. **Critic-C — remoção recursiva sem `-f`** → adiado: é mudança de política do vocabulário;
   registrado na ADR-201 como pergunta de FU.
4. **Critic-A — unificar o caminhante do E4 e o novo num caminhante parametrizado** → FU
   declarado (2.ª ocorrência da forma); fora da W1 por disciplina de tamanho.
5. **Critic-C — abreviação de opção longa por prefixo único** → hipótese; conferir na
   documentação antes de virar regra (W1a).

## Conflitos a fechar na rodada 2

- **K1 — ASK × BLOCK nos alimentadores opacos** (cano para interpretador, decodificação,
  substituição de processo como script). Critic-B (VETO) pede ASK; Critic-A e Critic-C pedem
  BLOCK. Proposta do CEO para a rodada 2: **BLOCK com mensagem acionável + `reason_code`
  próprio + kill-switch próprio + replay offline antes do land; regra de rebaixamento
  PRÉ-REGISTRADA por sub-forma: se o replay mostrar bloqueio legítimo acima de um limite fixado
  na ADR-201, aquela sub-forma sai como advisory (só evento, ALLOW) — nunca como ASK.** Critic-B
  diz se isso retira o VETO dele.
- **K2 — piso de literais.** Critic-B defendeu o piso como mecanismo de precisão; Critic-A e
  Critic-C mostraram que na posição do verbo ele vira ALLOW por aritmética (C2a/C2b, conferido;
  C2c com ressalva). Proposta: piso só na W2 (alvo de caminho). Critic-B confirma.
- **K3 — arquitetura da OQ-2.** Proposta: passada aditiva única (insight 1). Critic-C confirma
  que isso atende «os dois sítios consomem o mesmo caminhador».

## Plan adjustments

Índice das edições feitas em `PLAN-195-bash-guard-indirect-execution.md` nesta rodada:

1. Frontmatter: `budget_tokens`/`budget_sessions` refeitos (C5).
2. Context: frase das formas diretas qualificada; formas diretas irmãs nomeadas pela forma,
   inclusive a divergência de comentário entre tokenizadores (C1, C16).
3. Goal: «eleva o custo; residual declarado pela forma» (C11).
4. Thesis: raiz, passada aditiva única, reuso por leitura, regra do verbo computado, invariante
   de não-permissividade, fail-closed de parse de corpo de shell reconhecido (C1–C3, C10).
5. Alternativas: piso na posição do verbo e ASK puro rejeitados (C2, C6).
6. Oráculo: 5 suítes de teste, gêmeo YAML e `policy_preprocessors.py` (oráculo 1, não tocados).
7. W0: corrigir a frase das formas diretas e registrar a detecção única (C1, insight 9).
8. W1 dividida em W1-ADR, W1a e W1b, com escopo, prova, observabilidade, bateria e regra de
   parada (C4–C10, C14, insights 1–7, 10–12).
9. W2: mensagem A3, argv, `find` limitado ao segmento, cwd, bateria (C9, C13, insights 5, 8, 14).
10. Open questions: OQ-1 corrigida; OQ-2, OQ-3 e OQ-4 com a direção do debate; OQ-8 (A-8) e
    OQ-9 (K1) novas.
11. Success criteria: critério 2 reescrito (C11).
12. How to continue: aponta para o debate em curso e para a divisão.
13. Session history: entrada S360.
14. Status segue `draft`.

## Round verdict

**RUN-ANOTHER-ROUND.** Motivos: (1) dois VETOs condicionais a texto — os portadores precisam
confirmar que as condições estão no plano; (2) os conflitos K1–K3; (3) a OQ-8 nova. A rodada 2
usa os mesmos três críticos, retomados com o próprio contexto (PLAN-135 D4), lendo o plano
atualizado, este consenso e as três críticas da rodada 1. Regra de parada pré-registrada: no
máximo 3 rodadas; NO-GO só por P0 ou afirmação falsa.
