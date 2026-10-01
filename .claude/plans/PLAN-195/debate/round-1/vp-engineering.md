---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: "(nenhuma — perfil sintetizado da linha do skill-map em .claude/team.md:83)"
generated_at: 2026-10-01T02:45:23Z
---

> Regra de divulgação respeitada: nenhuma string de comando; formas descritas em prosa;
> linhas da matriz privada citadas só pelo id. Toda afirmação sobre código cita
> `arquivo:linha` conferido nesta rodada (HEAD `96f2f635`). O que não foi sondado está
> marcado **hipótese**. Baseline medido hoje: `test_byte_identity_fuzzer.py` +
> `test_byte_identity_harness.py` + `test_check_bash_safety.py` = 207 passed, 1 skipped.

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano quer fazer o `check_bash_safety.py` recusar o verbo destrutivo e a escrita canônica quando chegam por indireção ou expansão (classe GuardFall), sem lockout, com W0 doc já e W1/W2 canônicas em sequência.
- Forte: o diagnóstico da assimetria está certo e conferido no disco, a disciplina de divulgação e de controle negativo (exit 1, não 5) é a correta, e as alternativas rejeitadas (fail-closed cego, allowlist de leitura) estão bem rejeitadas.
- Fraco: a tese nomeia o ativo ERRADO do E4 para a classe A (o piso de literais dá ALLOW por construção em posição de verbo), o `_scan_blob` não é reutilizável como descrito, o escopo da W1 não cobre A-8/A-9 que a prova exige, o tamanho está uma ordem de grandeza abaixo do precedente no próprio arquivo, e a bateria omite as duas suítes de paridade que vão ficar vermelhas.

## Risks

- **R-VP1 — HIGH — a tese reusa o instrumento errado para a classe A.**
  Descrição: o piso `_E4_GLOB_MIN_LITERALS = 4` (`check_bash_safety.py:2569`, aplicado em `:2935`) mede literais de um GLOB DE CAMINHO; os verbos do trio têm 2 e 3 literais, então qualquer esqueleto de verbo cai abaixo do piso e vira ALLOW por construção — é exatamente o mecanismo que deixa A-1/A-2/A-3 passarem. E o `_scan_blob` (`:2304`) é uma closure definida DENTRO do laço `while` do E3 (`:2245`), que devolve um CAMINHO canônico (ou o prefixo do corpo, `:2309`/`:2315`), não tokens nem subcomandos — não é chamável de fora sem refatorar o E3.
  Mitigação: a ADR-201 nomeia o reuso real e só por LEITURA: tabelas de runner do E4 (`_E4_PREFIX_RUNNERS` `:2652`, `_E4_PREFIX_RUNNER_FLAGS` `:2699`, `_e4_classify_prefix_flag` `:3154`), o padrão de atribuição na mesma linha (`assigned_toggle`, `:3680-3685`, `:3740-3743`), o padrão de substituição em posição de comando (`_e4_substitution_body_names_toggle`, `:2888`) e a decodificação de aspas estáticas (`:3377`). Para verbo indecidível, a regra é a CONJUNÇÃO «palavra de comando com expansão ∧ forma de argumento destrutiva» (o trio testado com o verbo curinga), nunca o piso. Código do E3 e do E4 byte-idêntico na W1.

- **R-VP2 — HIGH — escopo × prova incoerentes em A-8 e A-9.**
  Descrição: A-8 e A-9 não são indireção — são verbos/formas DIRETAS que o vocabulário do trio não nomeia (`:364`, `:426`, `:447`). «Recursar o trio» não os cobre, mas `TestIndirectDestructiveBlocks` promete uma linha por forma A-1..A-9 com exit 0 depois da cura. Como escrito, a W1 não fecha a própria prova — ou fecha só se o executor inventar dois matchers novos sem debate do falso-positivo.
  Mitigação: declarar a extensão de vocabulário como item próprio. A-9 (escrita em dispositivo de bloco) entra com FP ~0. A-8 é uso legítimo frequente (limpeza de cache/scratch): ou entra com regra de forma (remoção por busca SEM predicado filtrante ≡ remoção recursiva) decidida no debate, ou sai da W1 e da prova.

- **R-VP3 — HIGH — tamanho e orçamento subestimados contra o precedente do próprio arquivo.**
  Descrição: o guarda do posture-toggle (E4) — um alvo, um caminho — ocupa `:2452-3815` (~1.360 linhas) e passou por pelo menos 8 rodadas do rail (`:2468-2478`, «codex S292 r8»). A classe A é 3+ verbos × 9 formas × 4 tipos de contêiner. Os ~80-150 linhas de hook da W1 e os 300-600k tokens não são críveis; o pacote estoura o teto de 400 linhas mesmo com a W1-ADR separada.
  Mitigação: pré-registrar a divisão W1-ADR → W1a → W1b na MESMA vaga, em sequência (mesma lógica já aceita para a W1-ADR), com o escopo de cada uma (ver Must-fix 7) e orçamento refeito (ver «Esforço»).

- **R-VP4 — HIGH — paridade com o gêmeo declarativo vai quebrar e a bateria não vê.**
  Descrição: `.claude/policies/bash-safety.policy.yaml` (oráculo 1) + `_lib/policy_preprocessors.py:98-226` são um ESPELHO do trio («Mirror», «byte-equivalent»), e `test_byte_identity_fuzzer.py:78-100` exige deriva ZERO entre hook e YAML em ≥ 500 entradas. O gerador tem um controle ALLOW de heredoc com o verbo destrutivo no corpo (`fixtures/byte_identity/bash_safety_fuzzer.py:99`): uma normalização de quebra de linha que não entenda heredoc (a do E4 não entende — `:3276-3306`) transforma esse corpo em comando ⇒ BLOCK no hook, ALLOW no YAML ⇒ vermelho. A bateria da W1 não inclui nenhuma das duas suítes de paridade (lição «LAND verde ≠ CI verde»). Hipótese: o gerador com semente 42 amostra essa linha (não medido).
  Mitigação: bateria da W1 inclui `test_byte_identity_fuzzer.py` e `test_byte_identity_harness.py`; segmentação ciente de heredoc; a ADR-201 decide a relação com o gêmeo (hook ⊇ YAML, asserção de mão única no teste não-canônico, ou aposentadoria por FU) — sem tocar os 3 arquivos canônicos do gêmeo na W1.

- **R-VP5 — MEDIUM — acoplamento operacional com a classe do disco cheio (S358).**
  Descrição: a lição S358 (memória `feedback-workflow-agents-must-clean-their-clones`) exige que cada agente APAGUE o próprio diretório por limpeza confinada; parte das rotas reais passa por corpo de shell aninhado. Fechar a classe A sem rota sancionada devolve o ENOSPC de ~200 GB.
  Mitigação: a ADR-201 nomeia a rota sancionada (helper confinado por realpath invocado por caminho; corpos de interpretador NÃO-shell, como a remoção de árvore em Python, fora do escopo do trio e declarados como residual) e um teste a fixa como ALLOW.

- **R-VP6 — MEDIUM — «ASK» não existe como canal e trava execução sem humano.**
  Descrição: o único `ask` que o hook emite é o da reescrita H5 (`_to_contract_decision`, `:3947-3963`); ASK sem reescrita é contrato novo. E pedido de permissão em subagente/noite é silêncio (memória `feedback-subagents-hang-on-permission-when-auto-mode-drops`).
  Mitigação: BLOCK com mensagem acionável e `destructive=True` (herda as rotas de liberação do fact-gate/citação, `:4166-4179`, como o rawscan já faz em `:3884-3887`); teste fixa que força-push indireto NUNCA vira reescrita (a guarda de `_rewrite_git_push_force` `:708-716` já recusa, mas tem de ser pinada).

- **R-VP7 — MEDIUM — o Goal promete fechamento que o próprio arquivo diz impossível.**
  Descrição: o Goal diz que o hook «recusa … inclusive quando» o verbo chega por expansão/indireção. O E4 já registrou, assinado, que análise estática de bash é incompleta por construção e que dizer o contrário é afirmação falsa em superfície assinada (`:2468-2478`). O rail vai apontar isso no texto da ADR.
  Mitigação: reescrever Goal, Success criteria e ADR-201 como «eleva o custo; residual declarado pela FORMA», no molde de `:2468-2478`.

- **R-VP8 — MEDIUM — rail sem regra de parada.**
  Descrição: «rail codex nas duas lanes até rodada limpa» (W1/W2) não tem teto; matcher de bash é instrumento que prevê código por texto (memória: não converge) e o precedente foram 8 rodadas.
  Mitigação: ver Must-fix 7.

- **R-VP9 — MEDIUM — W1 e W7a do PLAN-183 em voo ao mesmo tempo.**
  Descrição: pela ordem das vagas (`PLAN-194:27-31`), a W7a pega a vaga 1 quando a W1 do PLAN-194 landar, enquanto a parte A ocupa a vaga 2. Sem arquivo em comum, mas `test_check_harness_config.py` está nas duas baterias e a W7a move a fixture que ele re-executa (`check_harness_config.py:151`).
  Mitigação: quem landar por segundo roda a bateria do outro sobre a árvore composta (lição do ensaio em cadeia), registrado no pacote.

- **R-VP10 — LOW — a correção da mensagem A3 contamina o pacote aditivo.**
  Descrição: separar «parse falho» de «caminho achado» exige mudar o contrato de retorno do `_scan_blob` (`:2309`, `:2315`) e seus 4 consumidores (`:2338`, `:2415`, `:2432`, `:2441`) — edição no E3 dentro de um pacote que, de resto, pode ser puramente aditivo.
  Mitigação: mover para a W2 (que já é a onda do E3), junto com o argv (OQ-4).

- **R-VP11 — LOW — B-4 tem uma metade entre chamadas que o hook não enxerga.**
  Descrição: o `cwd` do Bash persiste entre chamadas na sessão principal, mas o `NormalizedEvent` não carrega `cwd` (`_lib/contract.py:60-76`; zero ocorrência em `_lib/adapters/claude.py`) e `decide_command(command)` (`:3818`) não recebe cwd. Hipótese: o payload do `PreToolUse` traz `cwd` (não conferido contra a doc do substrato).
  Mitigação: a W2 declara que fecha só o `cd` intra-comando, ou lê o `cwd` do stdin cru como o citation-gate já lê o `transcript_path` (`:4167`), mudando a assinatura de `decide_command` com teste.

- **R-VP12 — LOW — ADR antes do código.**
  Descrição: a W1-ADR landa antes do código; se entrar `ACCEPTED`, o texto assinado afirma comportamento inexistente e desmente a W0.
  Mitigação: landar `PROPOSED`; o flip vai no pacote de código que entrega o comportamento.

## Must-fix (blocking)

1. **Corrigir a tese de reuso (R-VP1).** No plano, na proposta e na ADR-201: retirar «reusa o `_scan_blob`» e «esqueleto do E4 com piso de literais» como mecanismo da classe A; nomear os ativos reais lidos por referência; regra de verbo indecidível = conjunção expansão-no-verbo ∧ forma destrutiva; E3/E4 byte-idênticos na W1. O piso continua sendo a ferramenta certa — da W2 (alvo de caminho).
2. **Reconciliar escopo e prova de A-8/A-9 (R-VP2)**: extensão de vocabulário explícita (A-9 dentro; A-8 com regra de forma decidida aqui ou fora da W1 e da prova).
3. **Arquitetura do OQ-2: UMA chamada aditiva na cauda de `decide_command`** — depois do laço legado e antes do `return Decision(allow=True)` (`:3921`) —, com o laço legado (`:3872-3919`) e `_recheck_whole_command` (`:587-612`) byte-idênticos. A nova passada caminha posições de palavra de comando sobre o tokenizador do E3 (`punctuation_chars`, `:2190`) e não sobre `tokens[0]` de um fatiamento ingênuo — isso também fecha o ponto cego de segmentação descrito em «Unseen» 1 —, com normalização de quebra de linha CIENTE de heredoc e recursão limitada em profundidade.
4. **Bateria com as suítes de paridade (R-VP4)**: `test_byte_identity_fuzzer.py` e `test_byte_identity_harness.py` no Check da W1 (e da W2); a ADR-201 declara a relação com o gêmeo YAML; nenhum dos 3 arquivos canônicos do gêmeo entra na W1.
5. **Decisão = BLOCK com `destructive=True`, nunca ASK (R-VP6)**, e teste: força-push dentro de contêiner nunca gera reescrita/`ask`.
6. **Reescrever a promessa (R-VP7)**: Goal, Success criteria e ADR-201 dizem «eleva o custo; residual pela forma»; a fronteira real (modo de permissão, sandbox, git) nomeada.
7. **Divisão + regra de parada do rail pré-registradas (R-VP3, R-VP8)**: W1-ADR (`PROPOSED`) → **W1a** (passada aditiva: segmentação, cadeia de runners, `find -exec`, corpos de shell `-c`/`eval`, heredoc para shell; A-4, A-5 e o corpo de `find -exec`) → **W1b** (verbo por expansão A-1/A-2/A-3, alimentadores opacos para shell A-6/A-7, A-9, e A-8 se aceito). Cada pacote ≤ 400 linhas / ≤ 8 paths. Rail: no máximo 4 rodadas por pacote; NO-GO só por P0 ou afirmação falsa; achado que é nova grafia de residual já declarado pela forma vai para o anexo da rodada final, não bloqueia; P1 na mesma subclasse em duas rodadas seguidas ⇒ parar e trocar a arquitetura (estreitar a afirmação), não remendar.
8. **Rota de limpeza sancionada fixada como ALLOW (R-VP5)** por teste, nomeada na ADR-201.
9. **Costura do E3 (R-VP10 + OQ-4)**: a W1 não toca o E3; a correção da mensagem A3 sai da W1 e vai para a W2, no mesmo pacote (ou antes) da regra de argv.

## Nice-to-have (advisory)

1. Mensagem de recusa nomeia o contêiner onde o verbo foi achado (corpo de shell, avaliação, cadeia de runner, expansão), no molde do `_E4_EXPANSION_NOTE` (`:3481-3486`) — senão a recusa cita um token que o operador não vê.
2. Kill-switch da passada nova no molde do `CEO_BASH_RAWSCAN` (`:502-523`): lido do snapshot `trusted_env` na importação, ligado por padrão.
3. Registrar p95 de `decide_command` antes/depois com o `test_perf_p95_under_50ms_advisory` (`test_check_bash_safety_canonical_matrix.py:300`) — a W1 do PLAN-194 muda o runner do CI ao mesmo tempo, e o gate de latência já sofre deriva de runner.
4. FU declarado: unificar o caminhante do E4 e o novo caminhante destrutivo num caminhante parametrizado por predicado (2.ª ocorrência ⇒ cura estrutural), com o registro do rail do E4 como baseline.
5. FU declarado: censo do vocabulário destrutivo (ver «Unseen» 2) e aposentadoria ou regeneração do gêmeo YAML.

## Unseen by the original plan

1. **Ponto cego de SEGMENTAÇÃO na forma direta (hipótese de alta confiança pela leitura do código; não sondado, por regra da tarefa).** O trio só olha `tokens[0]` de cada pedaço (`:378`, `:433-437`, `:456`), e os dois fatiadores só cortam nos quatro operadores de `:275` e `:566-580`. Separadores e agrupadores que o fatiador não modela — o mesmo conjunto que o E4 teve de normalizar na S292 r3 (`:3279-3292`), mais palavras reservadas de agrupamento — deixam o verbo fora da posição 0 sem nenhuma indireção. Não está na matriz A-1..A-9. A Must-fix 3 fecha isso de graça se o caminhante usar posições de palavra de comando.
2. **O vocabulário é um conjunto fechado escrito de memória.** O próprio arquivo registra que lista assim erra nos dois sentidos (`:2626-2634`). Há formas DIRETAS de destruição e de força no git e fora dele que o trio não nomeia (hipótese pela leitura de `:456-464`: força sem a flag). Fora do escopo da W1 por disciplina de tamanho, mas tem de virar FU nomeado; senão a W0 declara a classe errada.
3. **O gêmeo declarativo e o teste de deriva zero** (R-VP4): ausentes do plano.
4. **Taxonomia de contêineres**, que a ADR-201 precisa fixar: (a) RUNNERS, cujo operando é um argv — a tabela do E4, onde o `xargs` já está (`:2654`); o E3 trata `xargs` e `eval` como «próximo token» (`:2439-2446`), raso para o trio; (b) TOMADORES DE CORPO, cujo operando é texto de shell — shell `-c`, avaliação (junta TODOS os argumentos), heredoc para shell; (c) ALIMENTADORES OPACOS — cano, substituição de processo ou `source` de texto não estático ⇒ BLOCK; (d) VERBO INDECIDÍVEL — expansão na palavra de comando ⇒ conjunção com forma destrutiva.
5. **Fail-closed herdado**: para os corpos que o E3 já adjudica (shell `-c`, `eval`/`xargs`, `find`), corpo malformado ou > 16 KiB já é BLOCK a montante (`:2307-2315`, chamado em `:3840` antes do trio). A W1 não deve reimplementar isso — mas os tipos NOVOS (heredoc para shell, alimentador estático) não têm adjudicação a montante e precisam do próprio fail-closed.
6. **Corpus de PERMITIDOS existe** (ver OQ-1): os transcripts locais da sessão guardam todo comando Bash, não só os bloqueados.
7. **Contrato de cwd** (R-VP11) para a W2.

## What I would NOT change

1. W0 já, sem esperar o debate, e sem listar desvios.
2. Regra de divulgação: teste com strings concretas só no commit da cura.
3. Controle negativo em árvore descartável com exit 1, não 5; `TestIndirectLegitAllow` verde dos dois lados.
4. A rejeição do fail-closed cego (`:3462-3465`) e da allowlist de leitura (`:2492-2495`).
5. W2 sempre depois da W1 (mesmo arquivo) e o piso de literais na W2.
6. Espelhos `dist/`/`npm/` fora do pacote, provados por `cmp`.
7. ADR-201 escolhido por busca de menções, não pelo maior arquivo.
8. W3 «medir antes de ligar» como decisão ortogonal.
9. `test_check_harness_config.py` na bateria.

## Respostas às OQs

- **OQ-1 — orçamento de FP.** BLOCK, não ASK (R-VP6). Medir o FPR ANTES do land, sem esperar 7 dias de dogfood: reproduzir offline o corpus histórico de comandos Bash dos transcripts locais (inclusive de subagentes) contra o `decide_command` antigo e o novo. A função é pura; rodar com `HOME`/`CLAUDE_PROJECT_DIR` isolados, porque o E3 emite na cadeia em falha de parse (`:2196-2204`, classe S326). O conjunto-delta (BLOCKs novos) é classificado à mão; a meta é zero BLOCK novo em comando legítimo, salvo categorias aceitas pelo nome na ADR-201. Só as CONTAGENS vão para o repo; a lista fica na evidência privada do Owner. O ≤ 3/7d do §4.4 (`docs/security-bash-canonical-guards.md:162-164`) vira confirmação pós-land, não a medida primária. O mesmo instrumento serve W1a, W1b e W2.
- **OQ-2 — heredoc, aspas, dois sítios.** Nem «dois sítios» nem «helper chamado pelos dois»: uma chamada aditiva na cauda (Must-fix 3), que cobre o ramo rawscan porque roda sobre o comando inteiro depois do laço. No topo, o parse não pode falhar ali: o tokenizador idêntico do E3 já passou, senão o comando teria sido bloqueado em `:2193-2208`. Aspas: o caminhante só examina posições de palavra de comando, então texto destrutivo entre aspas como argumento de `echo` ou `grep` segue ALLOW (controles `test_check_bash_safety.py:58` e `:63`, e `bash_safety_fuzzer.py:94-100`). Heredoc: é dado, salvo quando o consumidor é runner de shell — aí é corpo, com recursão.
- **OQ-3 — `.mcp.json` e `CLAUDE.md` no conjunto protegido.** Não, no PLAN-195. O `_CANONICAL_GUARDS` é UMA lista que alimenta o rail Edit/Write e o E3 (`check_bash_safety.py:2216`), e o `check_canonical_edit.py` é canônico. O `CLAUDE.md` foi excluído deliberadamente, com motivo escrito (`check_canonical_edit.py:200-204`: editado a cada closeout). Nos adopters os dois arquivos são do próprio adopter (`.mcp.json` é semente única), e protegê-los vira lockout mais impacto no ownership de install/upgrade. Mudar o conjunto no mesmo pacote que muda a resolução de alvo também impede o rail de atribuir os FPs. Se o Owner quiser, é um plano próprio (a «convenção de cerimônia de closeout» que o comentário cita) — vira FU.
- **OQ-4 — lacuna argv (B-6).** W2, como o padrão do CEO. É pergunta de ALVO no ramo `-c` de interpretador do E3: o código escaneia só o corpo e faz `break` (`:2333-2345`), sem olhar os posicionais depois dele. A W1 não toca o E3 (Must-fix 9). Ir junto com a correção da mensagem A3 é obrigatório, porque a regra de argv torna MAIS frequente a recusa de leitura por interpretador e a mensagem certa (Read/`cat`/`grep`) tem de chegar no mesmo land ou antes.

## Esforço

Estimativa em tokens + sessões (ADR-081); a referência de classe é o E4 (~1.360 linhas, ≥ 8 rodadas de rail).

| unidade | linhas revisáveis (est.) | tokens (est.) | sessões | espera externa |
|---|---|---|---|---|
| Instrumento de FPR offline (OQ-1), reusado em W1a/W1b/W2 | ~80-120 (fora do repo ou teste não-canônico) | 60-120k | 0,5 | — |
| W1-ADR (`PROPOSED`) | 100-150, 1 path | 80-150k | 0,5 | SIGN do Owner |
| W1a — passada aditiva + segmentação + runners + corpos | 300-400, 3-4 paths | 350-650k (teto de 4 rodadas) | 1-1,5 | SIGN do Owner |
| W1b — verbo por expansão + alimentadores + vocabulário | 250-400, 3-4 paths | 300-600k (teto de 4 rodadas) | 1-1,5 | SIGN do Owner |
| **Parte A total** | — | **~0,8-1,5 M** | **3-4** | 3 assinaturas |

Isso é ~2-3× o orçamento de W1 do plano (300-600k, 1 sessão). A W2 também deve subir: ela herda a mensagem A3 e o argv, e talvez o contrato de cwd (+50-100k). Sem a regra de parada da Must-fix 7, o teto não existe: o precedente da classe é a S354, com 6 rodadas e 12,5 M tokens.
