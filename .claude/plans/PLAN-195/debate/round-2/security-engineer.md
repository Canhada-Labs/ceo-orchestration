---
round: 2
archetype: Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer (auth/crypto VETO holder)
generated_at: 2026-10-01T03:19:30Z
---

> **Regra de divulgação respeitada.** Nenhuma linha de comando que funcione como desvio
> aparece aqui; as formas vêm em prosa e a matriz privada só pelo id. `cbs` =
> `.claude/hooks/check_bash_safety.py`, conferido no HEAD `d572e374`. `PLAN` = o plano revisto
> `PLAN-195-bash-guard-indirect-execution.md` no mesmo HEAD.
>
> **Hipóteses marcadas.** O que depende de execução vem como **hipótese (leitura, não
> sondada)**. Não rodei sonda contra o hook nem tokenizei nenhuma string.
>
> **Fonte da semântica do `shlex`.** Lida no próprio código da biblioteca padrão do Python
> 3.9.6 desta máquina, `.../lib/python3.9/shlex.py`, com as linhas citadas abaixo.

## Verdict

**ADJUST.** O plano revisto absorve, inteiros, 6 dos meus 9 must-fix. A arquitetura da K3 é
melhor que a minha proposta da rodada 1. Fica um FATO NOVO que atinge o mecanismo central, e
ele está nos must-fix abaixo. O VETO continua, mas a condição encolheu para quatro edições de
texto (ver «VETO»).

## Summary (≤ 3 bullets)

- **O que o plano entrega na parte A:**
  - raiz posicional reconhecida;
  - passada aditiva única;
  - verbo computado sem piso de literais;
  - invariante de não-permissividade;
  - fail-closed de corpo de shell com ou sem assinatura;
  - BLOCK, nunca ASK;
  - prova N de N por pacote, com a classe do motivo;
  - bateria de 9 suítes;
  - «eleva o custo» com residual declarado pela forma.
- **Onde está forte:** a passada é MONOTÔNICA. Ela só acrescenta BLOCK depois do laço legado,
  com o laço e o recheck intocados, então não existe divergência entre sítios capaz de
  afrouxar um veredito. Isso é mais seguro que o helper chamado pelos dois sítios que eu pedi.
- **Onde está fraco (fato novo):** «o MESMO léxico do E3» herda duas propriedades do `shlex`
  que o bash não tem.
  - **Comentário no meio de palavra** consome o resto da linha. Combinado com a normalização
    de quebra de linha do E4, que não conhece comentário, um apóstrofo dentro de um comentário
    achata as linhas seguintes. A passada nova ficaria cega a script de várias linhas com
    comentário, uma forma natural e não adversarial.
  - **O tipo de aspas se perde.** Uma substituição de comando entre aspas duplas, que executa,
    fica igual a uma entre aspas simples, que é dado.

## Risks

- **R2-SEC1 — HIGH — o léxico do E3 não é fiel ao bash em comentário e quebra de linha.**
  - **O que o código faz:**
    - O E3 cria o `shlex.shlex` sem mexer em `commenters` (`cbs:2190`). O padrão é `#`
      (`shlex.py:36`).
    - No estado de palavra, um `#` ENCERRA o token e descarta o resto da linha
      (`shlex.py:230-237`). No bash, `#` só abre comentário no INÍCIO de uma palavra.
    - `shlex.split`, o tokenizador dos pedaços do trio, desliga comentário (`shlex.py:314`).
      Essa é a divergência C16, que o plano já registra.
    - O normalizador de quebra de linha do E4 (`cbs:3276-3344`) trata aspas mas não comentário.
      Um apóstrofo dentro de um comentário abre uma «aspa» (`cbs:3334-3335`). Enquanto essa
      aspa fica aberta, as quebras de linha seguintes não viram separador (`cbs:3338`).
  - **Hipótese (leitura, não sondada):** sobre esse léxico, com ou sem o normalizador do E4,
    duas coisas saem da posição de palavra de comando:
    - o texto que vem depois de um `#` no meio de uma palavra, na mesma linha;
    - as linhas que vêm depois de um comentário com apóstrofo.

    O laço legado não cobre os separadores que motivam a passada nova. A divergência de
    comentário reaparece DENTRO da cura.
  - **Mitigação:** must-fix 1.

- **R2-SEC2 — HIGH — o tipo de aspas se perde e a substituição entre aspas duplas fica sem dono.**
  - No modo POSIX (`cbs:2190`), o `shlex` remove as aspas. Uma substituição entre aspas duplas
    e uma entre aspas simples viram o MESMO token. A «abertura de contexto em … substituição de
    comando, crase» da W1a (`PLAN:359-361`) enxerga só a substituição sem aspas.
  - A direção da OQ-2 (`PLAN:558-560`) diz que a substituição dentro de aspas duplas e em
    here-doc de delimitador não citado é PROGRAMA. Nenhum dos dois escopos, W1a (`PLAN:357-372`)
    ou W1b (`PLAN:374-379`), atribui essa forma a alguém.
  - A W1a também diz «here-doc para arquivo é DADO» sem a ressalva: a substituição num corpo
    de delimitador não citado EXECUTA, seja qual for o consumidor.
  - **Mitigação:** must-fix 1.

- **R2-SEC3 — MEDIUM — expansão de chaves ausente do plano.**
  - `grep` por chave/brace no plano: zero ocorrências.
  - A doutrina do próprio arquivo manda EXPANDIR, não trocar por curinga (`cbs:2587-2593`). O
    expansor do E4 responde PERTENÇA, não ordem (`cbs:3067-3069`).
  - Um único token com chaves pode gerar o verbo E as flags.
  - O normalizador da W1a (`PLAN:361-363`) lista lançadores, divisão de string, caixa baixa,
    nome-base e aspas estáticas — não lista chaves.
  - **Mitigação:** must-fix 2.

- **R2-SEC4 — MEDIUM — a lista de residuais é circular e não está escrita no plano.**
  - A W1-ADR remete à «lista do Goal e da W0» (`PLAN:353`).
  - A W0 remete à «a mesma da ADR-201» (`PLAN:322`).
  - O Goal (`PLAN:138-144`) não tem lista nenhuma. A lista só existe na consolidação (C11).
  - A W0 landa primeiro e livre, então sairia sem lista ou com uma lista inventada na hora.
  - **Mitigação:** must-fix 3.

- **R2-SEC5 — MEDIUM — «alimentador opaco» sem definição pela forma.**
  - Sem definição, um interpretador com programa VISÍVEL que recebe DADOS pela entrada padrão
    pode ser classificado como opaco. Isso infla o falso-positivo e empurra a sub-forma para o
    rebaixamento da OQ-9, que reabre a classe inteira.
  - **Mitigação:** must-fix 4.

- **R2-SEC6 — LOW — o retorno antecipado da reescrita de força-push roda antes da passada da
  cauda (`cbs:3909-3916`).**
  - É inerte por construção. O comando novo é remontado token a token com `shlex.quote`
    (`cbs:736`), então todo texto de programa aninhado vira argumento literal.
  - O piloto vem desligado por padrão (`cbs:660-679`).
  - A prova (g) do plano (`PLAN:404`) cobre só o inverso: força-push DENTRO de contêiner.
  - **Mitigação:** nice-to-have 1.

- **R2-SEC7 — LOW — um kill-switch novo é uma superfície nova de desarme.**
  - O snapshot `trusted_env` impede armar o kill-switch por prefixo no comando
    (`_lib/trusted_env.py`, captura na importação).
  - Os dois arquivos de settings do projeto são canônicos (oráculo `1` para os dois, rodado
    nesta rodada).
  - Nada registra o desarme.
  - **Mitigação:** condição (d) da OQ-9.

- **R2-SEC8 — LOW — a medição de p95 não exercita o teto de aninhamento.**
  - A afirmação do plano está certa: o teste é `assert` duro
    (`test_check_bash_safety_canonical_matrix.py:330-332`), apesar do nome «advisory».
  - Só que a amostra é fixa (`:313`: as 5 primeiras linhas de BLOCK mais as de ALLOW) e não
    inclui a linha no teto de profundidade.
  - **Mitigação:** nice-to-have 2.

## Must-fix (blocking)

1. **Pré-léxico fiel ao bash, uma frase na Thesis item 2 e no escopo da W1a** (R2-SEC1,
   R2-SEC2). Antes do léxico do E3 (configuração de `punctuation_chars` mantida, e
   `commenters` vazio), UMA varredura ciente de aspas faz quatro coisas:
   - (a) trata `#` como comentário só no início de palavra e fora de aspas; aspas dentro de
     comentário são inertes; o comentário termina na quebra de linha;
   - (b) trata a quebra de linha como separador fora de aspas e fora de corpo de here-doc;
   - (c) delimita os corpos de here-doc, distinguindo delimitador citado de não citado;
   - (d) guarda o TIPO de aspas, para que corpos de substituição fora de aspas simples sejam
     recursados — inclusive dentro de aspas duplas e em here-doc de delimitador não citado,
     seja qual for o consumidor.

   Atribuir explicitamente a um pacote a substituição entre aspas duplas e a de here-doc não
   citado. A bateria combinatória ganha dois eixos: «comentário» (início de palavra, meio de
   palavra, com aspas dentro) e «tipo de aspas».
2. **Chaves no normalizador da W1a** (R2-SEC3), por pertença:
   - se qualquer palavra expandida de um token na posição de comando for verbo do trio, os
     marcadores são avaliados sobre a união das palavras expandidas com o resto do segmento;
   - acima de `_E4_BRACE_MAX_WORDS` (`cbs:2603`), BLOCK (fail-closed, precedente
     `cbs:2597-2600`).
3. **Escrever a lista de residuais UMA vez no plano** (Goal ou W0), com a W0 e a ADR-201
   remetendo a ela (R2-SEC4). Conteúdo:
   - os sete itens da C11;
   - os que este debate acrescenta: as sub-formas rebaixadas pela OQ-9, se houver, e a
     remoção por busca COM predicado (OQ-8).
4. **Definição pela forma de «alimentador opaco» na OQ-9 resolvida** (R2-SEC5): um
   interpretador chamado SEM operando de programa, que lê o programa da entrada padrão, de um
   descritor ou de uma substituição de processo; ou a avaliação da saída de uma substituição.
   Um interpretador com programa visível que recebe DADOS pela entrada padrão NÃO é opaco.

## Nice-to-have (advisory)

1. A ADR-201 registra por que o retorno da reescrita de força-push antes da passada é inerte
   (re-citação token a token). Um teste fixa o caso de força-push de um subcomando só
   carregando texto de programa aninhado: o resultado é BLOCK, ou uma reescrita cujo comando
   novo tem esse texto citado (R2-SEC6).
2. Medir o p95 também sobre a bateria combinatória, incluindo a linha no teto de aninhamento
   (R2-SEC8).
3. Abrir o FU `PLAN-195-FOLLOWUP-e4-comment-normaliser`. O normalizador de quebra de linha do
   E4 (`cbs:3276-3344`), com o mesmo léxico, deixa o guarda de toggle exposto ao mesmo ponto
   cego de comentário. O E4 fica byte-idêntico na W1, então isso vira residual declarado do
   E4 mais um FU.
4. Se o pré-léxico do must-fix 1 empurrar a W1a para mais de 400 linhas, pré-registrar a
   divisão: o pré-léxico e os separadores primeiro; lançadores, `git` e recursão em corpo
   depois, na mesma vaga.

## Unseen by the original plan

1. **A semântica de comentário do `shlex` no meio de palavra** (`shlex.py:230-237`). Não é só
   a divergência ENTRE tokenizadores que a C16 registra: é um ponto cego da própria passada
   nova.
2. **O normalizador do E4 não conhece comentário.** Um apóstrofo em comentário — muito comum
   em texto em inglês — desliga a conversão de quebra de linha.
3. **O léxico POSIX apaga o tipo de aspas** — e é o tipo que separa programa de dado na
   substituição de comando.
4. **Remoção por busca é o contorno NATURAL quando o trio recusa uma remoção recursiva.** Não
   é adversarial: um modelo prestativo chega a ela. Isso pesa a favor da opção (a) da OQ-8.

## What I would NOT change

- A passada aditiva única e monotônica na cauda (K3), com o laço legado, o recheck, o E3 e o
  E4 byte-idênticos.
- O fail-closed de corpo de shell reconhecido **com ou sem assinatura**, a correção da revisão
  Codex. A minha redação da rodada 1 era mais fraca e a correção está certa: paridade com
  `cbs:2307-2315`, que já bloqueia o `-c` exato.
- O controle N de N por PACOTE, com as linhas dos pacotes anteriores verdes.
- A mensagem A3 movida para a W2. A W1 não toca o E3, e o custo de mensagem fica declarado.
- O Goal «eleva o custo»; BLOCK, nunca ASK; `destructive=True` com o FU do filtro por papel no
  piloto de citação.
- A regra de parada do rail (no máximo 4 rodadas por pacote; troca de arquitetura quando a
  mesma subclasse volta em duas rodadas seguidas).
- OQ-3 e OQ-4 resolvidas como estão.

## Respostas da rodada 2

**1. Os must-fix 1–9 da rodada 1 no plano revisto:**

| # | Must-fix r1 | Estado | O que falta |
|---|---|---|---|
| 1 | Raiz posicional + caminhador único consumido pelos dois sítios | **em parte** | O mecanismo (K3) está atendido. Falta o pré-léxico fiel ao bash: comentário, quebra de linha, here-doc, tipo de aspas (must-fix 1). |
| 2 | Normalizador compartilhado com o E4 | **em parte** | Lançadores pela tabela, flag ambígua, divisão de string, `str.lower`, nome-base e aspas estáticas: OK (`PLAN:361-363`). O glob no verbo entra na regra do verbo computado (Thesis 4). Faltam as **chaves** (must-fix 2). |
| 3 | Piso proibido no verbo + regra do verbo computado + invariante | **atendido** | — (Thesis 4–5, alternativa rejeitada em `PLAN:208-210`) |
| 4 | Escopo de recursão pela forma | **em parte** | `-c` em aglomerado, todos os argumentos do `eval`, argv do `xargs`, a família `-exec` do verbo de busca, here-doc para shell, parênteses/substituição/crase/substituição de processo, função e alias: OK. A substituição entre **aspas duplas** e em **here-doc não citado** não tem pacote (must-fix 1). |
| 5 | Fail-closed de parse pelo precedente certo, teto iterativo, nada cego em corpo não-shell | **atendido** | Atendido de forma mais forte que o meu pedido (Thesis 6). |
| 6 | A-8/A-9 reconciliados com o escopo | **atendido** | A-9 na W1b com controle ALLOW; A-8 depende da OQ-8 (resposta 4 abaixo). |
| 7 | Prova N de N, classe do motivo, combinatória, bateria completa | **atendido** | Faltam só os dois eixos novos da combinatória (dentro do must-fix 1). |
| 8 | Residuais declarados pela forma | **em parte** | A lista não está escrita e as referências são circulares (must-fix 3). |
| 9 | BLOCK, sem ASK | **atendido** | — (Thesis 7, alternativa em `PLAN:214-217`) |

**O VETO cai?** Ainda não. Falta o texto dos must-fix 1–4 desta rodada (ver «VETO»).

**2. K3 — a passada aditiva única atende «os dois sítios consomem o mesmo caminhador»?**
**SIM.** E atende melhor que o helper que eu pedi, por três razões conferidas:

- **Cobre o escopo dos dois sítios.**
  - Ela roda sobre o comando INTEIRO depois do laço legado (`cbs:3872-3919`).
  - O ramo do recheck só existe quando o naive split quebra dentro de aspas. Nesse caso o léxico
    do topo já parseou o comando inteiro, porque senão o E3 teria bloqueado em `cbs:2193-2208`.
  - O `continue` fail-open de `cbs:597-600` e o de `cbs:3888` caem na cauda.
- **É monotônica.** Só acrescenta BLOCK, então as duas segmentações que continuam existindo
  (a legada e a nova) nunca afrouxam um veredito. O defeito que `cbs:3249-3251` registra era
  UMA posição aplicando uma regra que a outra não aplicava, e aqui isso não pode deixar
  passar o que já era bloqueado.
- **Tem um só ponto de evento.**

Duas ressalvas, sem nova divergência:
- **Retorno antecipado da reescrita de força-push** (`cbs:3916`): inerte pela re-citação
  (R2-SEC6, nice-to-have 1).
- **Fidelidade do léxico:** é o must-fix 1. Sem ele, o «mesmo léxico do E3» devolve a classe
  C16 para dentro da própria passada nova.

**3. OQ-9 (K1, alimentadores opacos) — a proposta do CEO é aceitável?** **SIM, com cinco
condições que entram no texto da OQ-9 resolvida e da ADR-201:**
- **(a)** A definição pela forma do must-fix 4. Ela sozinha elimina a maior parte do
  falso-positivo, porque o caso comum de dados pela entrada padrão para um programa visível
  não é opaco.
- **(b)** Pré-registro de verdade, ANTES de o replay rodar: limite numérico, corpus e métrica
  fixados na ADR-201. O rebaixamento vale por sub-forma, nunca para a classe inteira, e é
  decisão de cerimônia (emenda da ADR), não configuração em tempo de execução.
- **(c)** Sub-forma rebaixada vira residual declarado pela forma na ADR-201 e na §6.6. O evento
  continua saindo (advisory) e o critério de sucesso não a conta como coberta.
- **(d)** Kill-switch próprio, lido do snapshot `trusted_env`, ligado por padrão. Quando
  desarmado, emite um evento uma vez por sessão (precedente `_emit_learning_rail_disabled`,
  `cbs:1715-1733`).
- **(e)** Piso de segurança: a sub-forma cujo produtor VISÍVEL é um baixador de rede nunca é
  rebaixada. Um erro ali é execução remota de código; a regra `deny` nativa cobre uma grafia
  só; e o uso legítimo (instalador) tem a rota humana `!`.

**4. OQ-8 (A-8) — (a) ou (b)?** **(a), na forma ESTREITA**, com a remoção filtrada declarada
como residual.
- **Regra.** BLOCK quando a expressão da busca não tem NENHUM teste — só opções e ações, com a
  ação de remoção. Qualquer teste presente dá ALLOW. A classificação usa o conjunto fechado das
  OPÇÕES do verbo de busca, tirado do manual. Uma palavra com hífen que não estiver nesse
  conjunto conta como teste e dá ALLOW. A seletividade do teste não é julgada: isso seria a
  lista fechada de memória que erra para ALLOW (`cbs:2626-2635`).
- **Por quê:**
  - A forma sem teste É remoção recursiva do caminho inicial. A paridade com a forma direta é
    exigida pelo invariante da Thesis item 5.
  - É o contorno natural quando o trio recusa (Unseen 4).
  - O falso-positivo fica perto de zero, porque a limpeza legítima filtra.
  - Conferi na evidência privada, sem citar a string, que a amostra da linha A-8 não tem teste.
    Então o N de N da W1b fecha.
- **Residual declarado pela forma:** remoção por busca COM qualquer predicado, inclusive um
  predicado que casa tudo. Pela regra de parada do rail, uma grafia nova desse residual vai
  para o anexo e não bloqueia.
- **Por que não (b):** a opção (b) deixaria aberto justamente o contorno de esforço zero.

**5. Afirmação FALSA ou P0 novo.**
- **P0 novo:** nenhum. Nada executa ainda; as lacunas acima são de texto de desenho.
- **Afirmação falsa — ponteiro interno, não afirmação sobre o sistema:** «lista do Goal e da
  W0» (`PLAN:353`). O Goal não contém lista (`PLAN:138-144`). Correção de texto, coberta pelo
  must-fix 3, sem NO-GO.
- **Afirmações conferidas como VERDADEIRAS nesta rodada:**
  - as referências da Thesis 3 (`cbs:2652`, `:2699`, `:3154`, `:3680-3685`, `:3740-3743`,
    `:2888`, `:3377`);
  - Thesis 6 (`cbs:2193-2208`, `:2307-2315`, `:3644-3665`, `:4227-4233`);
  - as alternativas (`cbs:3249-3251`, `:299-322`, `:3947-3963`);
  - Prova (d): o teste de p95 é `assert` duro (`:330-332`).
- **Afirmação incompleta, que não é falsa:** «o MESMO léxico do E3» (Thesis 2), pelo motivo do
  R2-SEC1.

## VETO

**MANTIDO**, com a condição reduzida ao mínimo: os must-fix 1–4 desta rodada entram como
TEXTO no plano.
1. Uma frase do pré-léxico fiel ao bash na Thesis item 2 e no escopo da W1a, com o dono
   explícito da substituição entre aspas duplas e da de here-doc não citado, e os dois eixos
   novos na prova (c).
2. Chaves por pertença no normalizador da W1a.
3. A lista de residuais escrita uma vez, com a W0 e a ADR-201 remetendo a ela.
4. A OQ-9 resolvida com a definição pela forma de alimentador opaco e as condições (a)–(e) da
   resposta 3.

Não exijo rodada 3. Se essas quatro edições entrarem como descrito, retiro o VETO por leitura
do diff do plano, e o debate pode fechar `design-coherent` dentro da regra de parada. Nenhum
outro ponto da rodada 1 fica aberto.

**Esforço desta mudança** (ADR-081):
- pré-léxico e eixos novos na W1a: +50–100k tokens (~60–120 linhas);
- chaves: +10–30k;
- texto do plano: ~10–20k.

Não acrescenta sessão, mas aumenta o risco de a W1a passar de 400 linhas (nice-to-have 4).

## Confirmação do VETO (pós-edição)

Li o diff ainda não commitado do plano (`git diff -- .claude/plans/PLAN-195-bash-guard-indirect-execution.md`,
base `d572e374`; 186 linhas acrescentadas e 62 removidas). As citações de código abaixo foram
conferidas de novo no disco.

**As 4 condições:**

1. **Pré-léxico fiel ao bash — ATENDIDA.**
   - A Thesis item 2 traz (a)–(d): comentário só no início de palavra e fora de aspas, com
     aspas inertes dentro dele; quebra de linha como separador fora de aspas e de here-doc;
     here-doc citado × não citado; tipo de aspas guardado. O léxico roda com `commenters`
     vazio.
   - O escopo da W1a dá dono explícito à substituição entre aspas duplas e à de here-doc
     não citado.
   - A prova (c) ganhou os eixos «comentário» e «tipo de aspas».
2. **Chaves por pertença — ATENDIDA.** Estão no normalizador da W1a, com a união das
   palavras expandidas e BLOCK acima de `_E4_BRACE_MAX_WORDS` (`cbs:2603`; precedente
   `cbs:2597-2600`).
3. **Lista de residuais escrita uma vez — ATENDIDA.**
   - O Goal traz 12 itens e se declara «FONTE ÚNICA».
   - A W0 (c) e o conteúdo mínimo da W1-ADR remetem a ela.
   - A referência circular («lista do Goal e da W0») saiu.
4. **OQ-9 com a definição pela forma e as condições (a)–(e) — ATENDIDA**, e mais forte que o
   meu pedido. A pré-registração ganhou limite em número absoluto, denominador e uma
   definição operacional de falso-positivo. O kill-switch ganhou dois níveis.

**Correção que sobra — não bloqueia o debate, mas é conteúdo obrigatório da W1-ADR.** Ela vem
do precedente que EU citei na condição (d).
- `learning_rail_disabled` é uma ação registrada (`_lib/audit_emit.py:956`, dentro de
  `_KNOWN_ACTIONS`, `:156-1171`).
- Mas o emissor COAGE os campos para enumerações fechadas do trilho de aprendizado:
  - `rail` só aceita observe/distill/boot_render/fact_gate (`:8316`); qualquer outro valor vira
    «observe» (`:7588-7589`);
  - `switch` cai em «other» fora da lista (`:8317-8321`, `:7590-7591`).
- Desarmar o kill-switch da passada nova, do jeito que o plano descreve, gravaria
  `rail=observe`. É uma atribuição FALSA no registro forense: diria que o trilho de observação
  foi desligado.
- O `_lib/audit_emit.py` é canônico (oráculo `1`, rodado agora) e o plano diz que não o toca.
- Portanto a W1-ADR tem de escolher, e declarar, uma de duas saídas:
  - estender as duas enumerações, com `_lib/audit_emit.py` entrando como path do pacote
    W1a-1 ou W1a-2, sob a mesma cerimônia;
  - ou outra ação já registrada cujo esquema caiba.
- A prova (k) tem de afirmar o CONTEÚDO do evento (`rail` e `switch` corretos), não só que ele
  aparece uma vez.

**OQ-8 — ACEITO a decisão (b) do CEO. Não afeta o VETO.**
- O fato procede: o trio só recusa quando acha as opções recursiva E de força juntas
  (`cbs:380-417`, o `if has_r and has_f` em `:417`). A remoção recursiva sem força passa.
- Pelo texto do POSIX, sem terminal na entrada padrão a remoção não pergunta antes de apagar.
  O CEO marcou isso como inferido e eu concordo com a leitura.
- Então o equivalente direto da linha A-8 é uma forma PERMITIDA. A minha opção (a) deixaria a
  forma indireta mais estrita que a direta: isso não viola o invariante, mas dá uma política
  incoerente.
- Juntar as duas na OQ-10 é a forma certa da pergunta. O meu argumento do «contorno natural»
  (Unseen 4) continua válido, mas vale para as DUAS formas. Fica registrado como insumo da
  OQ-10, ao lado do replay.

VETO: RETIRADO

## Reconfirmação sobre o sha256 final

sha256 calculado por mim agora (`shasum -a 256 .claude/plans/PLAN-195-bash-guard-indirect-execution.md`):
`9894151f1648b0f7743cea526a89eab37f97f67326ae6b3c25227865ec6e0406`. Confere com o valor
informado. As passagens foram lidas no arquivo atual: «COAGE» na `:406`, «CONTEÚDO» na
`:495`, «Exceção declarada» na `:580`.

1. **W1-ADR — coerção do `learning_rail_disabled`: ACEITA.**
   - O texto nomeia a coerção certa, com as linhas certas (`_lib/audit_emit.py:7585-7591`,
     `:8316-8321`).
   - A ADR escolhe e declara entre duas saídas: estender as enumerações ou usar outra ação
     registrada cujo esquema caiba.
   - O `_lib/audit_emit.py` ficou como path condicional da W1a (`:446`, «≤ 4») e entrou na
     tabela do oráculo (`:276`, oráculo `1`).
2. **Prova (k) — afirmar o CONTEÚDO do evento de desarme: ACEITA.**
   - O teste exige `rail`/`switch` com os valores do kill-switch novo, não os coagidos
     `observe`/`other` (`:493-496`).
   - Isso fecha o falso-verde da simples contagem.
3. **W2 — exceção ao «BLOCK→ALLOW = zero»: ACEITA, com uma precisão de conteúdo para a W2
   (não bloqueia).**
   - A exceção é necessária, porque a W2 corrige de propósito o falso-positivo A3-5. Ela também
     está bem cercada: só o ramo do verbo de busca, cada transição classificada à mão, e
     qualquer outra BLOCK→ALLOW continua sendo defeito.
   - **A precisão:** o critério «não faz edição canônica no próprio segmento» (`:583-584`) usa
     a noção de segmento do E3, e essa noção tem um furo conhecido. No modo POSIX, o `;` que o
     verbo de busca usa como terminador da sua ação de execução vira, depois de escape ou aspas,
     a MESMA string do separador de comando. O E3 corta o segmento por pertença de string a
     `_E3_TERMINATORS` (`cbs:2097`).
   - Logo, uma edição canônica que venha DEPOIS desse terminador, na mesma invocação de busca,
     ficaria fora do «segmento». A busca limitada ao segmento a deixaria passar, e o critério de
     classificação a contaria como falso-positivo corrigido.
   - **Conteúdo obrigatório da W2:**
     - o limite da varredura é o fim da EXPRESSÃO do verbo de busca em termos de bash, não o
       segmento do léxico do E3. A W1 já guarda o tipo de aspas no pré-léxico (Thesis item 2,
       (d)), e é com ele que a W2 separa o terminador escapado/citado do separador real;
     - a classificação manual de cada transição BLOCK→ALLOW julga a invocação INTEIRA;
     - há uma linha BLOCK de controle com a edição canônica depois do terminador escapado.

Nenhum ponto novo exige rodada 3. A precisão do item 3 vai para o rail e para a classificação
da W2.

VETO: RETIRADO (sha256 9894151f)
