---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer (auth/crypto VETO holder)
generated_at: 2026-10-01T02:44:30Z
---

> Regra de divulgação respeitada: nenhuma linha de comando que funcione como desvio aparece
> aqui. Formas são descritas em prosa; linhas da matriz privada só pelo id (A-n / B-n).
> Toda afirmação sobre o código cita `arquivo:linha` conferido nesta rodada sobre a árvore de
> trabalho (HEAD `96f2f635`). Onde a afirmação depende de comportamento que só uma sonda
> provaria, ela vem marcada **hipótese (leitura de código, não sondada — regra da tarefa)**.
> Arquivo do hook = `.claude/hooks/check_bash_safety.py` (abreviado `cbs`).

## Verdict

**ADJUST** — com **VETO condicional** (ADR-052) sobre a execução da W1 *como está
especificada*. O VETO cai quando os itens 1–9 de «Must-fix» estiverem no texto do plano e no
rascunho da ADR-201, ANTES de qualquer edição do hook. Para retirar o VETO basta texto; não é
preciso código.

## Summary (≤ 3 bullets)

- **O que o plano quer:** fechar no hook a classe A (verbo destrutivo por execução indireta) e
  a B (escrita canônica com alvo computado), reusando o `_scan_blob` do E3 e o esqueleto de
  expansão do E4; corrigir o doc (W0); medir o sandbox à parte (W3).
- **Onde está forte:** o diagnóstico da assimetria confere no disco (`cbs:3891-3896` e
  `cbs:601` só olham `tokens[0]`; `_scan_blob` `cbs:2304-2330` só procura caminho canônico).
  Também estão certos a rejeição do fail-closed cego e da allowlist de leitura, a disciplina de
  divulgação, o «exit 5 não vale» e a nomeação dos dois sítios.
- **Onde está fraco:** (i) reusar o **piso de literais** do E4 reabre, por aritmética, as
  formas de nome de comando por glob ou expansão que o plano diz fechar. (ii) A raiz não é a
  «indireção». É que o trio decide sobre `tokens[0]` de pedaços de um split cego. Há formas
  **diretas** da mesma família abertas que o escopo não nomeia, e assinar «classe fechada»
  gravaria uma afirmação falsa em superfície assinada. (iii) A-8/A-9 não são recursão do trio
  (são verbos novos), então a prova da §4 da proposta não fecha com o escopo da §3.

## Risks

- **R-SEC1 — CRITICAL — a raiz está mal identificada; há formas DIRETAS da mesma família
  fora do escopo.**
  O trio decide só sobre `tokens[0]` (`cbs:378`, `cbs:436`, `cbs:456`) de pedaços produzidos
  por um split que só conhece `&&`, `||`, `;` e `|` (`cbs:275`, `cbs:339-344`).
  - A normalização remove apenas quatro prefixos (`cbs:107`) e três valores de flag
    (`cbs:108`), sem casefold (`cbs:188-189`).
  - O `git` é casado por posição fixa: `tokens[1] == "reset"` e `tokens[2] == "--hard"`
    (`cbs:436-437`); `tokens[1] == "push"` (`cbs:456`).
  - **Hipótese (leitura de código, não sondada):** passam pelo trio, sem nenhuma indireção, o
    verbo depois de quebra de linha sem aspas, depois de `&` simples ou `|&`, dentro de
    subshell ou grupo de chaves, depois de palavra reservada do shell, depois de lançador fora
    dos quatro prefixos, depois de flag de valor do `sudo`/`env` fora de `cbs:108`, com nome
    em maiúsculas (APFS resolve o PATH sem distinguir caixa), e `git` com opção global antes
    do subcomando ou com a opção destrutiva depois de um operando.
  - O próprio arquivo já documentou e curou essas formas, **só para o guarda de toggle (E4)**:
    quebra de linha `cbs:3279-3286`; caixa `cbs:2868-2873` e `cbs:3761-3763`; cadeia de
    lançadores `cbs:2622-2657` e `cbs:2699-2829`; ANSI-C `cbs:3362-3369`; chaves
    `cbs:2571-2585`.
  - `test_check_bash_safety.py` não tem nenhum teste dessas formas para o trio (grep por
    quebra de linha, `&` simples, grupos, `nohup`/`timeout`/`exec`/`command`, caixa: zero
    resultados).
  - **Mitigação:** itens 1–2 de «Must-fix».

- **R-SEC2 — HIGH — o piso de literais, reusado na palavra de comando, é um desvio por
  construção.**
  - `_E4_GLOB_MIN_LITERALS = 4` (`cbs:2569`). O teste do piso (`cbs:2935`) recusa padrões com
    menos de 4 caracteres literais. Os verbos do trio têm 2 (`rm`) e 3 (`git`) caracteres, então
    **toda** grafia em glob desses nomes cai abaixo do piso e vira ALLOW.
  - O esqueleto troca nome computado por `*`, e a nota `cbs:3462-3465` diz que isso é ALLOW
    **de propósito**. O piso foi dimensionado para um nome-base de 13 caracteres e protege
    contra lockout na posição de OPERANDO; na posição de COMANDO ele é exatamente o buraco das
    linhas A-1/A-2/A-3 e do glob no nome.
  - **Mitigação:** item 3.

- **R-SEC3 — HIGH — a lista de recursão é incompleta, e o localizador de corpo do E3 que a
  proposta reusa tem lacunas próprias.**
  - O E3 só reconhece o corpo de shell quando o token é exatamente `-c` e pega o token
    seguinte (`cbs:2413-2414`); o mesmo vale para `python`/`node`/`perl` (`cbs:2336-2337`). Um
    aglomerado de opções curtas que contém `c` (forma comum de shell de login) e um corpo que
    não vem logo depois do `-c` ficam fora.
  - O `eval` concatena **todos** os argumentos, mas o E3 olha só o primeiro (`cbs:2440`).
  - No `xargs`, o comando é o argv que sobra depois das flags do próprio `xargs`, mas o E3
    olha só o token seguinte (`cbs:2440`).
  - O `env` com divisão de string transforma uma string em argv. O trio consome a flag como
    booleana (`cbs:170-175`) e lê a string inteira como nome de comando. A tabela do E4 conhece
    essa flag (`cbs:2702`).
  - Faltam por inteiro na proposta:
    - substituição de comando como ARGUMENTO, inclusive dentro de aspas duplas e em here-doc
      de delimitador não citado (executa qualquer que seja o consumidor);
    - substituição de processo;
    - subshell e grupo;
    - here-doc ou here-string cujo consumidor é um shell;
    - corpo de função e valor de alias definidos no mesmo comando;
    - `find` com `-execdir`, `-ok` e `-okdir`.
  - **Mitigação:** item 4.

- **R-SEC4 — HIGH — a prova vermelho→verde, como escrita, não prova a classe e admite
  falso-verde.**
  - «Suíte sai com exit 1» prova só que **uma** linha está vermelha.
  - Uma linha pode ficar «verde» pelo motivo errado. O `_scan_blob` do E3 faz fail-closed cego
    em corpo que o shlex não tokeniza (`cbs:2313-2315`) e em corpo acima de 16 KiB
    (`cbs:2307-2309`): devolve BLOCK com mensagem de caminho canônico.
  - Nove exemplos não são a classe. O E4 precisou de 8 rodadas do rail na S292, cada uma com
    P1 numa grafia nova (registro em `cbs:2497-2534` e `cbs:2626-2635`).
  - **Mitigação:** item 7.

- **R-SEC5 — MEDIUM — A-8 e A-9 não são recursão do trio.**
  - Remoção por predicado de busca e sobrescrita de dispositivo são VERBOS fora do trio
    (`cbs:364`, `cbs:426`, `cbs:447`). Recursar o trio deixa essas duas linhas vermelhas para
    sempre.
  - Ou a ADR amplia o conjunto de verbos (decisão de política, com custo próprio de
    falso-positivo), ou as linhas saem da classe de teste.
  - **Mitigação:** item 6.

- **R-SEC6 — MEDIUM — «herdar o fail-closed de parse» aponta para o precedente errado.**
  - `_recheck_whole_command` PULA o subcomando que continua desbalanceado (`cbs:597-600`): isso
    é fail-open.
  - O `_scan_blob` faz fail-closed CEGO (`cbs:2313-2315`), e é dele que vem o ruído da A3
    (corpo de `python3 -c` recusado como «caminho canônico»).
  - O precedente certo é o E4 em `cbs:3644-3665`: fail-closed só quando o texto bruto, sem
    aspas e escapes e em caixa baixa, contém a assinatura do alvo.
  - Fato adicional: o `shlex` com `punctuation_chars` devolve uma CORRIDA de pontuação como um
    token só (nota em `cbs:3268-3272`). Um terminador grudado em parêntese vira um token que
    não pertence ao conjunto `_E3_TERMINATORS` (`cbs:2047`).
  - **Mitigação:** itens 1 e 5.

- **R-SEC7 — MEDIUM — «BLOCK/ASK» presume um ASK que o hook não tem.**
  - `Decision` tem três formas: allow, block, rewrite-ask (`cbs:299-322`).
    `_to_contract_decision` só emite `ask` com `updatedInput` de rewrite (`cbs:3947-3963`).
  - Um ASK puro é mudança de contrato. Sem humano (subagente, night-run) uma permissão
    pendente é silêncio, não recusa (lição registrada na memória do projeto: subagente
    pendurado em permissão). Em modo auto, o comportamento do `ask` de hook não foi medido.
  - **Mitigação:** item 9.

- **R-SEC8 — MEDIUM — marcar as recusas novas com `destructive=True` as torna liberáveis.**
  - A tag liga o fact gate e o piloto de citação (`cbs:4166-4179`).
  - O verificador procura a agulha como substring no fim do JSONL da sessão (`cbs:1132-1135`),
    sem filtrar papel.
  - **Hipótese:** o texto do próprio assistente e o resultado das ferramentas estão nesse
    JSONL. Sob o modelo de ameaça deste plano (modelo dirigido por injeção), a liberação seria
    auto-satisfazível.
  - O piloto está desligado por padrão (`cbs:991-1001`); o risco é latente.
  - **Mitigação:** nice-to-have 3 (a ADR decide e registra).

- **R-SEC9 — MEDIUM — a bateria da W1 não inclui todos os testes do hook.**
  - O Check da W1 (plano, linha 258) lista 4 arquivos.
  - O hook tem mais três suítes que a refatoração do `_scan_blob` e do normalizador pode
    quebrar: `test_bash_posture_toggle_invocation.py` (que afirma dos dois lados a divisão de
    trabalho E3/E4, `cbs:2479-2481`), `test_check_bash_safety_cp_chaining.py` e
    `test_check_bash_safety_h5_rewrite.py`.
  - **Mitigação:** item 7(d).

- **R-SEC10 — MEDIUM — o tamanho está subestimado.**
  - A cura correta (caminhador, normalizador compartilhado, recursão, regra de palavra de
    comando computada, fail-closed com assinatura, mensagem A3, ADR, testes combinatórios)
    passa de 400 linhas.
  - **Mitigação:** pré-registrar a divisão (ver «Esforço»).

- **R-SEC11 — LOW — orçamento de latência.**
  - A recursão roda em TODO comando Bash.
  - O orçamento é p95 < 50 ms (AC8, citado em `cbs:3629-3632`). Um aninhamento patológico sem
    teto quebra o orçamento ou, pior, levanta `RecursionError` — e crash dentro de matcher é
    fail-OPEN no `except` final (`cbs:4227-4233`).
  - **Mitigação:** item 5 (teto iterativo, como `_e4_brace_words` `cbs:3062-3065`).

## Must-fix (blocking)

1. **Corrigir a tese:** a raiz é «decisão posicional sobre um split cego». A W1 entrega **um
   caminhador único** que produz todo comando simples que o bash executaria e que está
   estaticamente visível; o trio roda sobre cada um.
   - Reusar a tokenização e a caminhada do E3/E4 (`shlex` com `punctuation_chars`,
     `_e4_normalise_command` `cbs:3276`, terminadores), não só o esqueleto.
   - Completar com: corrida de pontuação que CONTÉM terminador; palavras reservadas do shell
     (lista fechada e documentada no manual); abertura de contexto de comando em parêntese, na
     substituição de comando, na crase e nas duas substituições de processo.
   - Os dois sítios do trio consomem o MESMO caminhador (resposta da OQ-2). Duas segmentações
     é a divergência que `cbs:3249-3251` registra como a forma de defeito do E4.
2. **Um normalizador de palavra de comando compartilhado com o E4:**
   - cadeia de lançadores pela tabela `_E4_PREFIX_RUNNER_FLAGS` (`cbs:2699-2829`), com flag
     desconhecida tratada como ambígua (`cbs:2689-2698`);
   - `env` com divisão de string tratado como CORPO;
   - caixa baixa com `str.lower` (`cbs:2544-2549` explica por que não `casefold`) e nome-base;
   - decodificação das aspas estáticas (`_e4_expansion_replacement` `cbs:3377-3409`);
   - expansão de chaves por PERTENÇA: `_e4_brace_words` não preserva ordem (`cbs:3067-3069`),
     então qualquer palavra expandida que seja verbo do trio torna o token candidato;
   - glob no nome casado diretamente contra os nomes do trio.

   Esta é a 4.ª ocorrência da classe «verbo fora do `tokens[0]`» no trio (PLAN-019 P0-02
   `cbs:73-89`, PLAN-153.E5 `cbs:97-109`, PLAN-152 rawscan `cbs:469-504`, agora) ⇒ cura
   estrutural obrigatória (CLAUDE.md §4).
3. **Proibir o piso de literais na posição de palavra de comando.** Regra de palavra de comando
   computada, em ordem:
   - (a) propagar as atribuições literais feitas no MESMO comando (precedente `assigned_toggle`,
     `cbs:3680-3685`, `cbs:3740-3743`);
   - (b) se continuar computada e o segmento carregar marcadores destrutivos LITERAIS do trio
     (letras `r` e `f` em opção curta ou as longas; `reset` com `--hard`; `push` com força),
     BLOCK;
   - (c) senão, ALLOW, e a forma vira residual declarado.

   Invariante na ADR-201: **nenhuma forma que o caminhador reconhece recebe veredito mais
   permissivo que a sua forma direta.**
4. **Escopo de recursão enumerado pela FORMA no plano e na ADR:**
   - corpo de `-c` localizado como o primeiro operando depois de um aglomerado de opções que
     contém `c` (shells e interpretadores);
   - TODOS os argumentos do `eval`, concatenados;
   - o argv depois das flags do `xargs` e de `find` com `-exec`/`-execdir`/`-ok`/`-okdir`;
   - substituição de comando em qualquer posição, inclusive dentro de aspas duplas e em
     here-doc de delimitador não citado;
   - substituição de processo;
   - subshell e grupo;
   - corpo de função e valor de alias definidos no mesmo comando;
   - here-doc e here-string cujo consumidor é shell.

   Texto de programa de origem NÃO literal entregue a interpretador vira BLOCK: cano, leitura
   explícita da entrada padrão, `/dev/stdin`, substituição de processo como script, avaliação
   do resultado de uma substituição. Corpo de here-doc com destino a arquivo é DADO, e precisa
   de controle ALLOW. O normalizador de quebra de linha do E4 respeita aspas, mas não conhece
   here-doc (`cbs:3276-3344`), e escrever arquivo por here-doc é padrão comum do agente.
5. **Fail-closed de parse pelo precedente do E4 (`cbs:3644-3665`), não pelo do `_scan_blob`:**
   - corpo de programa SHELL que o shlex não tokeniza vira BLOCK quando a forma achatada (sem
     aspas e escapes, em caixa baixa) contém uma assinatura do trio;
   - teto de profundidade e de tamanho, iterativo, vira BLOCK;
   - nunca aplicar fail-closed cego a corpo não-shell (python/node), para não multiplicar o
     ruído da A3.
6. **Reconciliar A-8 e A-9 com o escopo.** Ou a ADR-201 define o conjunto de verbos
   «destrutivos» e o amplia explicitamente (com controles ALLOW para a busca legítima e para o
   `dd` em arquivo comum), ou as duas linhas saem de `TestIndirectDestructiveBlocks` para um
   item próprio. Nenhuma linha da matriz pode ficar fora do alcance da cura.
7. **Prova:**
   - (a) no HEAD sem a cura, **cada** linha de `TestIndirectDestructiveBlocks` falha (contagem
     N de N, não só «exit 1»);
   - (b) cada linha afirma a CLASSE do motivo (prefixo estável ou código do ramo novo), não só
     `allow=False`; isso mata o falso-verde do R-SEC4;
   - (c) bateria combinatória gerada a partir de verbo × invólucro × grafia × separador ×
     lançador da tabela do E4, com a matriz privada como semente, não como universo; mais um
     teste de aninhamento até o teto e acima dele;
   - (d) o Check da W1 inclui TODAS as suítes do hook (`test_bash_posture_toggle_invocation.py`,
     `test_check_bash_safety_cp_chaining.py`, `test_check_bash_safety_h5_rewrite.py`), além
     das quatro já listadas.
8. **Residuais declarados pela forma** na ADR-201 e na §6.6 da W0. Sem esta lista,
   «classe A fechada» é afirmação falsa:
   - APIs destrutivas da própria linguagem (sem verbo de shell);
   - script em arquivo, inclusive escrito antes pela ferramenta Write;
   - funções e aliases do perfil do shell ou de chamadas anteriores;
   - configuração de ferramenta que executa valor como programa (aliases de shell do `git`,
     chaves executáveis de configuração);
   - variáveis de arquivo de inicialização do shell (dono: env guard,
     `_lib/env_guard.py:70-71`, advisory por padrão, `cbs:3852-3860`);
   - argumentos que chegam ao `xargs` pela entrada padrão;
   - palavra de comando E argumentos totalmente computados.
9. **ASK fora da W1:** a W1 emite BLOCK com mensagem acionável («escreva o comando na forma
   direta; ela é julgada pelo próprio mérito», como `cbs:3503-3508`). Um ASK puro só com ADR
   de contrato e medição em modo auto e sem humano.

**Condição de retirada do VETO:** 1–9 refletidos no plano (Thesis, W1, Success criteria) e no
rascunho da ADR-201, revisados nesta mesma cascata de debate. Itens 1–5 e 7 podem ser
divididos entre W1a e W1b (ver «Esforço»), desde que a divisão esteja pré-registrada e que a
W0 descreva o estado real entre as duas.

## Nice-to-have (advisory)

1. **Replay diferencial para o FPR** (detalhe na OQ-1).
2. **Teste de mutação por sub-regra.** Desligar cada regra nova faz pelo menos uma linha
   ficar vermelha; prova que cada regra carrega peso.
3. **A ADR-201 decide a tag `destructive` da recusa nova.** Recomendo manter equivalência com
   a forma direta (tag igual), mas registrar o risco do R-SEC8 e condicionar o armamento do
   piloto de citação a uma verificação restrita a entradas de papel `user`.
4. **Gramática do `git` no próprio trio** (forma direta, entra na W1a): opções globais antes
   do subcomando; opção destrutiva depois de operando; refspec com prefixo de força;
   `--mirror`; exclusão remota. **Hipótese:** abreviação de opção longa por prefixo único,
   aceita pelo parser de opções do git e pelo `getopt_long` do GNU `rm` — conferir na
   documentação antes de virar regra.
5. **Remoção recursiva sem `-f`.** Para arquivos graváveis é tão destrutiva quanto com `-f`.
   É decisão de política do conjunto de verbos; a ADR pode ao menos registrá-la.
6. **Limitar ao segmento a varredura de `find` do E3** (`cbs:2431`, A3-5). **Dado observado
   nesta revisão:** um comando composto só de leitura meu (busca com `find` num segmento e um
   caminho canônico como argumento de OUTRO comando) foi recusado com a mensagem de
   «-exec sed/-i edit denied», que não se aplicava. É um falso-positivo real do E3 vigente.
7. **Teste de latência com o teto de aninhamento**, no padrão do AC8.
8. **A W2 herda o MESMO caminhador e o mesmo localizador de corpo.** As lacunas de
   `cbs:2336-2337` e `cbs:2413-2414` (aglomerado de opções; corpo que não vem logo depois do
   `-c`) também abrem a classe B.

## Unseen by the original plan

1. **Formas diretas irmãs** (R-SEC1): a afirmação «as formas DIRETAS seguem BLOQUEADAS»
   (plano, linha 90; proposta, linha 45) vale só para a grafia canônica, com o verbo no início
   de um pedaço delimitado por `&&`/`||`/`;`/`|`. A W0 também precisa corrigir essa frase.
2. **O E4 é a lista já paga.** As 8 rodadas da S292 acharam exatamente as grafias que o trio
   ainda não trata. Reusar o esqueleto sem a caminhada e o normalizador repete aquelas
   rodadas no trio.
3. **A aritmética do piso para verbos curtos** (R-SEC2): o piso só é seguro para nomes-base
   longos.
4. **A expansão de chaves do E4 responde pertença, não ordem** (`cbs:3067-3069`). Ela não
   reconstrói argv, e a cura precisa ser desenhada sobre pertença.
5. **Substituição de comando dentro de aspas duplas EXECUTA.** O controle ALLOW atual (texto
   destrutivo citado num `echo`, `test_check_bash_safety.py:574-577`) é correto só porque ali
   não há substituição. A cura precisa distinguir as duas formas com controles dos dois lados.
6. **Here-doc é ao mesmo tempo dado e programa,** conforme o consumidor e as aspas do
   delimitador. Reusar sem cuidado o normalizador de quebra de linha do E4 bloquearia a
   escrita de arquivo por here-doc.
7. **ASK sem humano = travamento** (R-SEC7).
8. **Três suítes do hook ficaram fora da bateria** (R-SEC9).
9. **Liberação por citação sem restrição de papel** (R-SEC8), latente por padrão.
10. **A ordem em `decide_command` importa.** O E3 roda antes do trio (`cbs:3840-3842`) e
    responde com a mensagem canônica para corpos não tokenizáveis. Depois da cura, um corpo
    destrutivo e malformado ganha a mensagem errada, a menos que a mensagem da A3 separe esse
    ramo (o item 2 da W1 já toca nisso — amarrar os dois).

## What I would NOT change

- A rejeição do fail-closed cego em toda expansão e da allowlist de leitura (doutrina em
  `cbs:2492-2495`): as duas estão certas e devem ficar na ADR com o motivo.
- O sandbox como decisão ORTOGONAL, medido antes de ligar. Ele não substitui o matcher dentro
  da árvore.
- A regra de divulgação: classe pela forma no repo público; teste com strings concretas só no
  commit da cura.
- O «exit 5 não vale como controle».
- Os espelhos `dist/` e `npm/` provados por `cmp`, fora do commit e do Scope.
- A W2 estritamente depois da W1 (mesmo arquivo), e a A3 como correção SÓ de mensagem.
- `test_check_harness_config.py` na bateria (`check_harness_config.py:151` re-executa a
  fixture destrutiva contra este hook).
- A regra de parada pré-registrada (no máximo 3 rodadas; NO-GO só por P0 ou por afirmação
  falsa).

## Respostas às OQs

- **OQ-1 (orçamento de FP):** decidir por três medidas, não por opinião.
  - **(a) O corpus de comandos PERMITIDOS provavelmente existe.** Os transcripts locais do
    harness registram todo `tool_use` de Bash, permitido ou não. **Hipótese:** é preciso
    confirmar quanto sobra depois do sweep de `cleanupPeriodDays`.
  - **Replay diferencial:** passar o corpus pelo `decide_command` puro, HEAD × cura, com `HOME`
    e `CLAUDE_PROJECT_DIR` isolados (método da evidência privada), sem `main()` e sem executar
    nada. Saem só contagens; o conjunto de diferenças fica privado. Cada recusa NOVA é revisada
    à mão.
  - **Orçamento:** as regras de equivalência com a forma direta (itens 1–4) não podem gerar
    nenhuma recusa nova legítima no corpus, porque espelham a política vigente. As regras
    heurísticas (item 3b, fail-closed por assinatura do item 5) ficam dentro do ≤ 3 por 7 dias
    da §4.4, em dogfood.
  - **(b)** Controles sintéticos em `TestIndirectLegitAllow`, cobrindo os dois lados de cada
    forma.
  - **(c) BLOCK, não ASK, na W1** (item 9 e R-SEC7).
- **OQ-2 (here-doc, aspas, dois sítios):**
  - **Um caminhador único** chamado pelos dois sítios (item 1). Recursão só num sítio deixa o
    ramo de parse sem cura, e helper sem caminhador comum recria a divergência registrada em
    `cbs:3249-3251`.
  - **Fail-closed de parse** pelo precedente do E4 com assinatura (item 5), não pelo pulo de
    `cbs:597-600` nem pelo cego de `cbs:2313-2315`.
  - **Here-doc:** o corpo é DADO, salvo quando o consumidor é shell ou avaliação; substituição
    de comando em here-doc de delimitador não citado e dentro de aspas duplas é sempre
    PROGRAMA.
  - **O controle do `echo` com texto destrutivo citado continua ALLOW.**
- **OQ-3 (`.mcp.json` e `CLAUDE.md` na parte B):** **não é pergunta da W2.**
  - O oráculo responde `0` para os dois (rodado nesta revisão). Bloquear só no Bash, sem entrar
    em `_CANONICAL_GUARDS`, cria assimetria sem ganho: Bash bloqueado, Write livre.
  - A W2 deve consumir `_CANONICAL_GUARDS` como está. A ampliação é decisão do guarda de
    edição canônica, em cerimônia própria.
  - Minha recomendação para essa decisão: `.mcp.json` SIM (define processos lançados no início
    da sessão — persistência de execução). `CLAUDE.md` medir antes o custo de cerimônia, porque
    ele é editado em todo closeout.
- **OQ-4 (lacuna argv):** **W2**, concordo com o padrão do CEO.
  - É alvo de escrita computado pelo programa; não é verbo destrutivo.
  - Regra pela forma: caminho canônico entre os operandos posicionais depois de um corpo `-c`
    ou `-e` de interpretador vira BLOCK, sem tentar provar se o corpo lê ou escreve (seria
    allowlist de leitura disfarçada, contra `cbs:2492-2495`).
  - Uma linha na matriz e o controle ALLOW correspondente (operando não canônico).

## Esforço

Estimativa em tokens e sessões (ADR-081). O prazo humano aparece só como `external_wait`.

| Pacote | Conteúdo | Tokens | Sessões |
|---|---|---|---|
| W1-ADR | ADR-201 com invariante, escopo pela forma, residuais, decisão ASK/tag | ~80–150k | ~0,5 |
| W1a | caminhador único, normalizador compartilhado com o E4, gramática do `git`, os dois sítios; formas diretas irmãs | ~250–450k (rail de 3–6 rodadas) | ~1 |
| W1b | recursão pela forma, regra de palavra computada, fail-closed por assinatura, origem não literal → BLOCK, mensagem A3, bateria combinatória | ~350–650k (rail de 4–8 rodadas; o E4 levou 8) | ~1–2 |
| Replay de FP (OQ-1) | | ~40–80k | — (cabe numa das sessões acima) |

- **Total da parte A:** ~0,7–1,3M tokens, 3–4 sessões — cerca de 2× os ~300–600k do plano.
- **`external_wait`:** uma assinatura GPG do Owner por pacote canônico (2 a 3 assinaturas). A
  W1a e a W1b ficam na MESMA 2.ª vaga, uma depois da outra (mesmo arquivo).
