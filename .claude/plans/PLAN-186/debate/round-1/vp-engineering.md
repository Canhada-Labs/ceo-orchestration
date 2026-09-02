---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-02T16:10:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano quer transformar herança silenciosa em política explícita de roteamento (papel × modelo × effort), medir o assento por A/B, cortar CI pela metade e ensinar o Step 0 a olhar dependência sequencial. A medição é honesta e o instinto de «medir, não argumentar» está certo.
- **Onde é forte:** a disciplina de falsificação (AC-3 exige o campo `model` da resposta servida, não `grep`), a recusa do derivador da W1 em usar o «17» do relatório quando o código diz 10, e a lista explícita do que NÃO fazer (V-block, Agent Teams, `used_pct`).
- **Onde é fraco:** o diagnóstico «não há política, há herança» é **falso** para o caminho de spawn dominante. Já existem **quatro** superfícies que decidem papel→modelo, e o plano adiciona uma quinta ligando-a a apenas uma delas. É a forma exata dos defeitos D1–D4 da S322–S327: a ORIGEM tinha dono, a ROTA não.

## Risks

**R-VP1 — CRITICAL — Quinta superfície de roteamento sem resolvedor único.**
Verificado em disco, quatro superfícies já decidem papel→modelo hoje: (a) os pins de `.claude/agents/*.md`, aplicados só no rail nativo — ADR-082 §Consequences/Negative diz literalmente que a atribuição de modelo do VETO floor «becomes advisory rather than enforced for non-cr archetypes»; (b) o bloco `MODEL_HINT` de `inject-agent-context.sh:273-312`, uma tabela `case` por skill que emite `opus`/`sonnet` com justificativa; (c) `.claude/dispatcher/routing-matrix.yaml`, com `coder_model` por arquétipo e guarda de tamper T-4; (d) `VETO_HARDCODE` em `tier_policy_cli/_constants.py:44-47`, de onde `set-quality-profile.sh` deriva. Mais `CLAUDE_CODE_SUBAGENT_MODEL: "inherit"` em três espelhos de settings. A W1 liga a matriz nova só aos 10 sítios de `agent()`.
*Mitigação:* o primeiro entregável canônico do PLAN-186 é a ROTA — uma tabela `papel → model id` com as superfícies existentes como LEITORAS, no molde de `scripts/delivery-routes.tsv` (3 leitores, uma fonte). Sem isso o plano cria a sexta grafia do mesmo fato.

**R-VP2 — CRITICAL — O raio de explosão da W3 é ~9 sítios, não «os 5 pins» do AC-5.**
`claude-fable-5-1` **não está** em `VETO_FLOOR_ALLOWED`: o Amendment 2 do ADR-149 (linhas 248-251) diz «`VETO_FLOOR_ALLOWED` is **unchanged**: Fable 5.1 is selectable, not VETO-eligible». Flipar os pins sem emendar a allowlist **bloqueia todo spawn VETO** (`veto_floor_demoted`). Pior: `VETO_HARDCODE` (`_constants.py:44-47`) e o literal INDEPENDENTE `VETO_HARDCODE_APPLY` (`apply.py:90-93`) guardam `claude-fable-5` atrás de uma asserção sha256 em tempo de import (`FROZEN_SHA256_HEX_LITERAL`, `apply.py:95-101`) — mudar o dict sem regenerar o hex no MESMO patch faz `learn.py`/`apply.py` falharem no import. Os oráculos do AC-5 (parity e2e, `generate-available-models.py --check`) respondem sobre `availableModels`, não sobre a allowlist e não sobre os dois dicts congelados.
*Mitigação:* enumerar o conjunto de sítios MECANICAMENTE antes da cerimônia (não de memória) e escrever um oráculo por sítio no AC-5; o derivador do W3 regenera o hex congelado como edição derivada, nunca à mão.

**R-VP3 — HIGH — O mecanismo que sustenta a camada P tem «no forward guarantee» declarado e nenhum vigia.**
A emenda do ADR-144 (linhas 140-141) diz que o roteamento de `opts.model` é «a timeless property and carries no forward guarantee — the Workflow rail routed `opts.model` on the version measured, and a later harness may stop doing so». A medição foi em 2.1.237; a sonda da W0 registra 2.1.258 instalado (60 versões de drift). O AC-3 prova UMA vez, no land. Se um harness futuro voltar a `inherit`, a economia evapora, o roteamento reverte para o assento e **nada fica vermelho** — a classe «instrumento verde cuja pergunta envelheceu» que este repo já pagou duas vezes.
*Mitigação:* o instrumento de custo da W0 já lê `message.usage` por modelo nos transcripts; fazê-lo asseverar o INVARIANTE de roteamento por execução (modelo servido por label == modelo declarado no sítio) converte a prova pontual do AC-3 num detector permanente, com critério de morte pré-registrado.

**R-VP4 — HIGH — A coluna `effort` contradiz a própria regra que a governa, em 2 das 7 linhas.**
A regra publicada é «escale por **incerteza de especificação**, não por blast radius», e o texto do estudo dá o exemplo: «tarefa com derivador determinístico e critério de aceite em bytes ⇒ `high`». Mesmo assim a matriz dá `xhigh` ao refutador (cuja tarefa é re-derivar e comparar — totalmente especificada) e `max` ao builder canônico/KERNEL com derivador anchor-exact (o exemplo canônico de tarefa especificada). Ambas as linhas estão escaladas por blast radius, exatamente o que a regra proíbe.
*Mitigação:* aplicar a regra (refutador e builder anchor-exact caem para `high`) ou trocar a regra por uma que descreva a matriz. E publicar o classificador: sem um teste de «esta tarefa está especificada?», a regra não é falsificável e vira retórica.

**R-VP5 — HIGH — A regra do Step 0 vive em 6 sítios vivos; o AC-7 nomeia 2.**
Verificado por grep: `PROTOCOL.md:195-197`, `PROTOCOL.pt-BR.md:194-196`, `.claude/team.md:640-642`, `team.en.md:250-252`, `.claude/commands/spawn.md:135-137`, `.claude/skills/core/ceo-orchestration/SKILL.md:512-514` (mais uma menção em `docs/ROADMAP.md:145`). Dois são espelhos de tradução cobertos por `translations-drift.yml` e `check-canonical-doc-freshness.py`; **o comando `spawn` e a skill `ceo-orchestration` não são cobertos por nada** e ficariam contradizendo o `PROTOCOL.md` em silêncio.
*Mitigação:* AC-7 lista o conjunto completo, derivado por censo antes da edição; e a skill `ceo-orchestration` é Gate-2 cache-stable, logo a edição pertence a um closeout, não ao meio de uma wave.

**R-VP6 — HIGH — O −US$ 1.369/mês está precificado sobre um perfil que a W1 não alcança.**
O número vem de re-precificar 80 % dos tokens de subagente dos 30 dias. A W1 edita `agent()` dentro de 4 workflows + 3 sítios do molde de night-run. O caminho de spawn dominante deste repo é a chamada `Agent` DIRETA do CEO — só nesta sessão foram nove (seis pesquisadores, dois builders da W0/W1, eu). Nenhum desses passa por um `agent()` de workflow; todos herdam o assento, e a W1 não os toca.
*Mitigação:* separar os ACs — AC-3 cobre os sítios de workflow; um AC novo cobre o caminho de spawn direto (o `MODEL_HINT` deixa de ser copy/paste e vira campo registrado). E re-precificar o ganho da W1 contra a fração de tokens de subagente que de fato passa pelos 13 sítios, medida no instrumento da W0 — hoje esse número não existe.

**R-VP7 — MEDIUM — A OQ-5 é apresentada como pergunta de debate, mas é MEDÍVEL.**
`grep` sobre `.claude/hooks/` e `.claude/settings.json` por `SendMessage|ListAgents` retorna **zero**. E o carimbo universal de ciclo de vida por tool-call anda no matcher ENUMERADO de `settings.json:302` (`Agent|Bash|Edit|…|Task|mcp__.*`), enquanto o observador de PostToolUse é universal (`matcher: ""`). Ou seja: a superfície de mensagens está, na melhor hipótese, meio observada, e se um `PreToolUse` sequer é entregue para `SendMessage` é uma SONDA, não uma opinião.
*Mitigação:* mover a OQ-5 da W5 para a W0 como sonda (o mecanismo já usado no probe `wf_d7af49d9`), e — se a resposta for «religar» — **alargar o matcher, não enumerar mais um nome**. A lição r22 do PLAN-179 é literal: canal instruction-adjacent fecha por REMOÇÃO, não por enumeração; um matcher enumerado nasce cego para o próximo tool que o substrato adicionar.

**R-VP8 — MEDIUM — Famílias de auditoria por projeto tornam a troca entre terminais estruturalmente incorrelacionável.**
A W1 do PLAN-182 separou a cadeia HMAC por projeto — decisão correta e que não se deve desfazer. A consequência é que uma troca entre dois repos escreve em DUAS cadeias sem nenhum correlator comum, e `verify_chain()` por projeto nunca reconstrói o par. O AC-8 pede «evento de auditoria emitido» sem dizer que o evento de um lado é ilegível do outro.
*Mitigação:* se a US3 vai auditar a troca, o envelope da mensagem carrega um id de troca cunhado pelo emissor e ecoado pelo receptor (dois eventos, uma chave). Se isso for caro demais, o ADR declara EXPLICITAMENTE que a correlação entre projetos está fora de escopo — como o ADR-190 fez com os REDs por desenho.

**R-VP9 — MEDIUM — A gramática atual não consegue expressar dependência sequencial, e o proxy de arquivo não cobre a classe que motiva a mudança.**
O ADR-191 declara apenas um conjunto de ESCRITA (`CAN edit:` concreto ou `NONE-READ-ONLY`); não existe conjunto de LEITURA declarado. Dependência sequencial é uma aresta escrita→leitura, então `escrita ∩ escrita` não a exprime. Pior: a classe de −70 % deste repo em geral **não é mediada por arquivo** — a aresta finder→refutador do `audit-fanout` e o caso do S338 (um draft de design alimentando um debate) são dependências de VALOR DE RETORNO, com zero sobreposição de path. Um check baseado em arquivo que declare fechada a classe de Kim et al. é falso-verde.
*Mitigação:* uma linha opcional `CONSUMES:` na gramática torna a aresta derivável mecanicamente dos dois conjuntos declarados, reusando `spawn_file_assignment_recorded` — custa um campo, não uma cerimônia. E o ADR nomeia o residual: dependências de valor de retorno seguem fora do alcance mecânico, cobertas só por doutrina.

**R-VP10 — MEDIUM — A doutrina nova perde para um hook que empurra na direção oposta, e para uma skill que já diz o contrário.**
`check_anti_ceo_overhead.py` dispara em P1 (≥3 leituras sequenciais de skill), P2 (≥3 edições não relacionadas) e P3 (≥2 arquivos de config — `:182-183`, `:515`, `:526`, `:537`) e **recomenda dispatch**; nenhum dos três predicados pergunta sobre estrutura de dependência. Ele disparou contra mim durante esta tarefa, por ler em ordem três arquivos que eu precisava ler em ordem. E `parallelization-by-default/SKILL.md` já contém a regra que a W5-US1 quer introduzir — critério 2, linhas 56-59: «Item B depending on Item A's output means serial» — mas com o default OPOSTO nas linhas 44-47: «If a task contains >=3 independent items… CEO MUST dispatch sub-agents in parallel».
*Mitigação:* a W5-US1 não está adicionando uma regra ausente; está reconciliando duas skills com critérios diferentes e sem precedência, mais um hook que materializa o viés. O escopo tem de incluir os três, e a mensagem do hook precisa de uma ressalva de dependência — senão a doutrina nova é contrariada pelo mecanismo a cada poucos minutos.

**R-VP11 — MEDIUM — O `MODEL_HINT` já está defasado, e a matriz aprofundaria a contradição.**
`inject-agent-context.sh:280-282` emite `MODEL_HINT="opus"` com a razão «VETO floor (ADR-052) — Opus mandatory». É um alias de família, que resolve para `claude-opus-5` — não para o teto `claude-fable-5` dos pins. Um CEO que siga a dica para um arquétipo VETO satisfaz a allowlist e contradiz o pin, em silêncio. Levar os pins para 5.1 sem tocar aqui amplia a distância.
*Mitigação:* a dica deriva da mesma tabela de rota do R-VP1 e emite **ids pinados**, nunca aliases de família.

**R-VP12 — LOW — O `model` passado no call site não é validado por ninguém.**
Confirmado na leitura do DESIGN-W1 §5 e coerente com o ADR-191: `assertDispatchable` inspeciona apenas a STRING do prompt (bullets de PROMPT DEFENSE, linha `CAN edit`, marcador de regras). `model` vive no segundo argumento de `agent(prompt, opts)`, fora do alcance dele. Um typo de model id nos 10 literais novos passaria despercebido até cair em fallback silencioso.
*Mitigação:* o lint de model id que o DESIGN nomeia como follow-up viaja no MESMO patch da W1. É a única coisa que faz os 10 literais falharem alto; sem ele a W1 substitui herança silenciosa por literal silencioso.

## Must-fix (blocking)

1. **Entregar a ROTA antes dos literais (R-VP1).** Uma tabela `papel → model id` como fonte única, com as quatro superfícies existentes (`agents/*.md`, `MODEL_HINT`, `routing-matrix.yaml`, `VETO_HARDCODE`) declaradas como leitoras. A W1 vira o primeiro consumidor, não a política.
2. **Re-escopar o AC-5 com o conjunto de sítios derivado mecanicamente (R-VP2)**, incluindo `VETO_FLOOR_ALLOWED` + espelhos independentes do ADR-149, `VETO_HARDCODE`, `VETO_HARDCODE_APPLY` e a regeneração do sha256 congelado no mesmo patch. Um oráculo por sítio; `generate-available-models.py --check` não responde por nenhum deles.
3. **Converter o AC-3 de prova pontual em detector permanente (R-VP3)**, asseverando o invariante «modelo servido == modelo declarado» no instrumento da W0, com critério de morte escrito.
4. **Reconciliar a coluna `effort` com a regra que a governa (R-VP4)** e publicar o classificador de «tarefa especificada». Enquanto o classificador não existir, a regra não decide nada.
5. **AC-7 lista os 6 sítios do Step 0 (R-VP5)**, marcando quais têm gate de paridade e quais não têm; a edição da skill `ceo-orchestration` respeita a disciplina de cache (closeout, não meio de wave).
6. **Separar o AC da W1 entre caminho de workflow e caminho de spawn direto (R-VP6)** e re-precificar o −US$ 1.369 contra a fração medida de tokens que passa pelos 13 sítios. Hoje o número é atribuído a uma wave que não o pode entregar.
7. **Mover a OQ-5 para uma sonda da W0 (R-VP7).** Decidir por debate uma pergunta que uma sonda responde é a inversão que o repo já nomeou. Se religar, alargar o matcher em vez de enumerar mais um nome.
8. **Declarar a fronteira de cobertura do check de dependência (R-VP9)**: adicionar `CONSUMES:` à gramática do ADR-191 para as dependências mediadas por arquivo, e nomear como residual as dependências de valor de retorno — que são a maioria da classe de −70 % aqui.
9. **Incluir no escopo da W5-US1 a skill `parallelization-by-default` e o hook `check_anti_ceo_overhead.py` (R-VP10).** Uma doutrina de Step 0 que não vence o predicado que empurra para o dispatch é texto sem mecanismo.

## Nice-to-have (advisory)

1. Fazer o lint de model id (R-VP12) viajar no patch da W1 em vez de virar `PLAN-186-FOLLOWUP`.
2. Corrigir a razão e o valor do `MODEL_HINT` (R-VP11) na mesma wave que tocar os pins.
3. Cunhar um id de troca no envelope entre terminais (R-VP8), ou declarar a incorrelação como limite aceito.
4. Repetir a sonda de concorrência 3× por N antes de citar p95 — o próprio arquivo da W0 marca `n=1` e o AC-2 exige 3/3; hoje o plano cita como fato uma célula única.
5. Registrar num ADR a escolha deliberada de roteamento por REGRA e não por classificador aprendido (RouteLLM). O estudo diz que já é escolha consciente; nada no repo a documenta.
6. Medir o custo fixo de contexto por spawn (~95 k tokens, W0) contra o ganho de paralelizar: é o número que transforma «mais agentes» em «menos janela» e deveria entrar no Step 0 como terceiro critério, ao lado de colisão e dependência.

## Unseen by the original plan

1. **As quatro superfícies de roteamento que já existem.** O diagnóstico §4.1 («ausência de decisão, tomada 10 vezes por omissão») é falso para o caminho dominante: `inject-agent-context.sh:273-312` contém uma tabela de roteamento por papel, escrita e comentada, que diz «CEO must pass `model:` param explicit». A decisão existe — o que falta é que ela seja única, pinada e MEDIDA.
2. **A asserção de integridade em tempo de import.** `VETO_HARDCODE_APPLY` + `FROZEN_SHA256_HEX_LITERAL` fazem `apply.py` falhar no import se o dict divergir. É um fail-closed correto, e uma armadilha para uma wave que mude pins sem saber que ele existe.
3. **O hook que empurra na direção contrária ao Step 0 novo.** Nenhum dos três predicados de `check_anti_ceo_overhead.py` pergunta sobre dependência; ele recomenda dispatch por CONTAGEM.
4. **`parallelization-by-default` critério 2 já é a regra de Kim et al.** — o plano a apresenta como lacuna quando o defeito real é duplicação com defaults opostos.
5. **Cobertura zero de hook em `SendMessage`/`ListAgents`, e um matcher ENUMERADO no carimbo de ciclo de vida.** O plano diz «nenhum hook audita essa troca» e está certo, mas não vê a causa de forma: enumeração, a mesma classe que a r22 do PLAN-179 fechou por remoção.
6. **A separação de cadeia por projeto impede correlacionar a troca entre repos** — uma consequência da cura correta da S319/S321 que o AC-8 não considera.
7. **`set-quality-profile.sh` continua sendo um caminho de reescrita dos pins**, hoje derivado de `VETO_HARDCODE` (endurecido na W4.3 do PLAN-169). Se a W3 mudar os pins sem mudar a constante, a próxima invocação do script os reverte em silêncio — a mesma armadilha registrada em `PLAN-169/fleet-currency-audit-S298.md`, agora com um alvo novo.
8. **O `MODEL_HINT` de VETO aponta para `opus` enquanto o pin aponta para `fable-5`** — uma contradição viva entre duas superfícies que o plano quer estender.
9. **A W1 não cobre o spawn direto do CEO**, que é como quase todos os agentes deste repo nascem, inclusive os nove desta sessão.

## What I would NOT change

- **A recusa de decidir o assento por argumento.** O A/B de 7 dias com decisão pré-registrada e critério de invalidação (`< 4 janelas por braço`) é o desenho certo para uma moeda sem número oficial. Não substituir por estimativa de multiplicador.
- **Não paralelizar o V-block do LAND.** Dezenas de segundos contra reabrir a corrida na cadeia HMAC viva e re-certificar um `trap/restore` endurecido por cinco rodadas de rail. A conta não fecha, e o plano já diz isso.
- **Agent Teams fora.** A doutrina de topologia FLAT e o fato de que 2.1.247 fez o teammate herdar o modelo do líder confirmam a decisão, não a enfraquecem.
- **A disciplina do AC-3: provar pelo campo `model` da resposta servida, não por `grep`.** É a regra que este repo pagou caro para aprender (uma rota errada-mas-existente manteve 10 testes verdes) e ela está aplicada corretamente aqui.
- **A correção 17 → 10 sítios feita pelo derivador da W1.** Contradizer o próprio relatório-fonte com um comando reproduzível, e usar os sítios verificados em vez do número citado, é exatamente o comportamento que se quer preservar. Não «reconciliar» isso de volta para 17.
- **Manter W0/W1 como ESTUDO, sem tocar a árvore viva.** O `--check` sobre a árvore viva e o `--apply` só em worktree descartável é a disciplina certa; nenhuma pressa de wave justifica relaxá-la.
- **A claim honesta de que não há speedup geral.** Nada neste plano a contradiz, e nada nos cortes de CI deve ser reescrito como se contradissesse.
- **Não mexer no pin de `settings.json` antes da W2.** O ADR-149 já separa «5.1 selecionável» de «5.1 padrão de sessão», e a rota do `settings.local.json` para uma máquina só é a saída correta enquanto o A/B roda.
