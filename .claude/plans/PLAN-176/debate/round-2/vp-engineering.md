---
round: 2
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-07T00:20:00Z
---

## Verdict

ADJUST — **5 itens bloqueantes**

## Summary (≤ 3 bullets)

- A revisão é honesta e a maioria dos 16 must-fix do round 1 está CURADA e re-verificada por mim em disco: o oráculo dos 10 paths do §2 reproduz linha por linha (`check_canonical_edit.py --is-canonical`), o fetcher saiu de `check-substrate-watch.py` (grep de rede = **0**, postura ADR-136-AMEND-1 intacta) e foi para `_lib/model_feed_fetch.py` (oráculo **1**), a allowlist ganhou dois pares concretos, T virou TETO, o conjunto de env é um elemento com gramática, os critérios de morte estão em ciclos com arquivo/comando/dono, e as ACs viraram **31 checkboxes** com `Check:` (contadas: 5+6+4+8+5+3 — o breakdown do progress log fecha).
- **Onde é forte:** a tese central (split T/P preserva a cerimônia POR CONSTRUÇÃO, zero extensão de guard-list) sobrevive à re-medição; a decisão de pôr a allowlist de destinos DENTRO da superfície cerimonial é a cura certa para C2; os três diretórios de teste citados nos `Check:` estão em `pytest.ini:38-45` (`testpaths`), então as ACs são coletáveis — a armadilha `scripts/tests/` foi evitada.
- **Onde é fraco:** o plano reutiliza três ações da taxonomia fechada de auditoria **sem ler o allowlist de campos de cada uma** — duas ACs e uma decisão de arquitetura afirmam gravar dados que `audit_emit.py` DESCARTA por desenho. E repete a forma exata do C1 (número de ADR já reivindicado por outro material) um número adiante.

## Risks

**R-VP1 — P1 — A AC de egresso da W0b não pode ser satisfeita: a taxonomia fechada APAGA o caminho, e os dois destinos diferem SÓ no caminho.**
A AC `[P0][US2]` da W0b (plano `:244-247`, «Cada despacho emite `egress_destination_detected` com host **e caminho**») colide com o consumidor: `.claude/hooks/_lib/audit_emit.py:6836` chama `_coerce_egress_destination(event["destination"])`, e essa função (`:8506-8522`, docstring «Reduce a destination to a bare host string (no scheme/path/query/cred)») corta em `/`, `?` e `#`. A allowlist da W0b (plano `:217-218`) é **dois pares host+caminho com o MESMO host** (`platform.claude.com`, `/docs/…/models/overview` e `/docs/…/model-deprecations`): depois da coerção os dois despachos gravam o **mesmo** evento. O rastro de auditoria não consegue distinguir qual destino foi buscado — a garantia de egresso da onda fica sem lastro no log.
*Mitigação:* ou a AC declara «host + classe de egresso» (o campo `egress_class`, `:6833`) e o caminho vive num campo já permitido pelo `_EGRESS_DESTINATION_DETECTED_ALLOWLIST` (a ser lido antes de escrever a AC), ou a onda declara uma emenda de campo à taxonomia — o que é edição de `_lib/audit_emit.py`, path canônico, e portanto MUDA o tamanho do pacote da W0b.

**R-VP2 — P1 — Duas decisões do §3 afirmam gravar um «motivo» que o allowlist do evento descarta.**
(i) §3.3 (`:121-124`): «a troca emite `model_choice_recommended` **com o motivo**». O allowlist desse action é `_OPTIMIZER_ENVELOPE + (subtask_index, model_recommended, confidence_basis_points, cost_governed, fell_back_to_static)` (`audit_emit.py:1359-1362`, envelope = `("action","session_id")`, `:1349`) — **não existe campo de motivo**; o scrub (`:5290-5291`) dropa e só deixa um breadcrumb. (ii) §3.1 item 3 (`:99-101`): a recusa pelo teto emite `model_routing_enforced`, cujo allowlist (`:1601-1607`) tem `archetype, mode, recommended_model, killswitch_armed, decision` — **nenhum campo carrega o identificador RECUSADO nem a origem que o pediu**. O plano vende «não se inventa ação nova» como economia; o preço não declarado é que o evento reutilizado não consegue responder a pergunta da §3.
*Mitigação:* para cada uma das 4 ações citadas (`model_routing_enforced`, `env_var_hijack_blocked`, `model_choice_recommended`, `egress_destination_detected`) o plano publica o allowlist medido e o mapeamento campo→dado; onde faltar campo, a decisão é explícita (usar campo existente, ou emenda canônica ao `audit_emit.py` com o custo de cerimônia somado à onda). Precedente da casa: a lição «`emit_generic` recebe kwargs top-level — o scrub dropa».

**R-VP3 — P1 — As duas ACs da W3 apontam para arquivos que NÃO existem em HEAD — e uma delas substituiu a âncora irrecuperável do round 1 por outra.**
`[P0][US6][.claude/skills/core/ceo-boot/SKILL.md]` (`:367`) e `[P1][US6][.claude/skills/core/nightly-hygiene/SKILL.md]` (`:375`) — medido: `find .claude -name SKILL.md` não retorna nenhum dos dois; `git ls-files | grep -Ei 'ceo-boot|nightly-hygiene'` dá `.claude/commands/ceo-boot.md`, `.claude/scripts/ceo-boot.py` e `.claude/workflows/nightly-hygiene.js`. O must-fix 15 do round 1 pedia trocar a âncora truncada `trig_014Y…` por «AC baseada em configuração»; a substituta (`grep -q 'check-model-currency' .claude/skills/core/nightly-hygiene/SKILL.md`) ancora num arquivo inexistente — o `grep` sai rc 2 e a AC fica PERMANENTEMENTE vermelha, o que é pior que vacuamente verde: bloqueia a onda por defeito do texto.
*Mitigação:* re-derivar os dois paths por censo (`git ls-files`) antes de re-abrir a W3; a dimensão noturna vive num `.js` de workflow e o boot num `.py` — o que muda também o oráculo e possivelmente a cerimônia da onda.

**R-VP4 — P1 — `ADR-198` já está reivindicado por outro material landado: o plano repete a forma do C1 um número adiante.**
`.claude/plans/PLAN-186/debate/round-4/proposal.md:133` reserva `ADR-198-spawn-step0-dependency-and-fixed-cost.md`, e o consenso do mesmo round (`round-4/consensus.md:137,178`) trata esse ADR-198 como o artefato do US1 do PLAN-186. A medição do §3.4 do plano («não existe arquivo `ADR-198-*`») é verdadeira e **insuficiente**: o teste do «próximo livre» é o mesmo para os dois planos, então os dois o passam e colidem no land. Corolário aritmético: o diretório tem 198 arquivos `ADR-*` mas só **175 números distintos** (18 prefixos duplicados: 019, 040, 042, 049, 054, 055, 062, 087, 089, 104, 110, 116, 118, 129, 135, 136, 155, 164) — «tem 198 arquivos» não é evidência de que 198 seja o próximo livre, e há 20 números livres ≤197 (68, 130, 134, 166–180, 184, 187).
*Mitigação:* alocação de número de ADR não pode ser medida local por plano; ou o Owner arbitra (item de OQ), ou o número é reservado por arquivo `PROPOSED` no MESMO pacote que o cita.

**R-VP5 — P1 — A W1b declara cinco caminhos; as ACs dela exigem nove, e um path declarado não tem AC nenhuma.**
O texto (`:291-297`) diz «Cinco caminhos canônicos, um pacote, uma assinatura — dentro do teto de oito caminhos». Mas: (a) **nenhuma** das 8 ACs da W1b traz a tag `[.claude/governance/models-registry.json]` — o registro T é declarado no pacote e não tem `Check:` (o único AC que o nomeia está na W2, `:344`); (b) as ACs adicionam três arquivos de teste não declarados (`.claude/hooks/_lib/tests/test_model_registry.py`, `.claude/scripts/tests/test_gate_scripts_manifest.py`, `.claude/scripts/tests/test_check_model_literals.py` — este último editado na W1b para ganhar `-k wired_into_ci`) e um quarto arquivo, `.claude/data/model-currency-expected-reds.txt` (`:336`), que não aparece na lista de paths de **nenhuma** onda. Contagem real do pacote: 5 + 3 + 1 = **9 paths**, acima do teto de 8 do modelo de operação v2. Duas seções do mesmo plano dizem números diferentes.
*Mitigação:* re-cortar a W1b (o candidato natural é tirar o `validate.yml` + manifesto para uma W1c) e declarar o arquivo de conjunto-vermelho na onda que o cria (a W0a, que é dona do `check-model-currency.py`).

**R-VP6 — P2 — A primeira AC da W0a é vacuamente verde: um stub que sai 0 a satisfaz.**
`Check: python3 .claude/scripts/check-model-currency.py --check; test $? -le 1` (`:166`). O predicado aceita 0 **e** 1, então nenhum resultado de comparação o vermelhe — só um crash (rc ≥ 2) o faz. Um detector que não implementa comparação alguma passa. É a classe «instrumento verde cuja PERGUNTA envelheceu», já paga por este repo. As duas ACs de controle (negativa de rede, positiva de injeção) cobrem parte, mas a AC do comportamento principal não tem oráculo próprio.
*Mitigação:* separar código de saída de EXECUÇÃO (0 ok / ≥2 defeito) de código de ACHADO, e a AC assevera o ACHADO por teste, não por `$?` tolerante.

**R-VP7 — P2 — Os critérios de morte declaram um comando de leitura que nenhuma AC obriga a existir.**
§4 (`:385-386`): «Comando de leitura único: `check-model-currency.py --state --json`». Nenhuma das 31 ACs menciona `--state` nem `--json` — as ACs da W0a exercitam `--check` e a da W1b `--expected-reds`. K-2 («qualquer ocorrência ⇒ vermelho fail-closed no CI») também não tem AC de fiação no CI: a única AC de CI da W1b (`:317-319`) fia o **lint de literais**, não o guarda da camada T. Critério de morte sem instrumento fiado é declaração, não catraca.
*Mitigação:* uma AC por flag citada no §4, e uma AC explícita de que o vermelho do K-2 aparece no `validate.yml`.

**R-VP8 — P2 — W0b («nunca de dentro de um agente») e W3 («o boot mostra upstream») podem ser lidas como regras diferentes.**
W0b (`:206-208`): «o fetcher é invocado pelo Owner ou pela rotina agendada, **nunca de dentro de um agente**». W3 (`:367-370`): «o `/ceo-boot` mostra, por raia ativa, o trio {instalado, fixado, **upstream**}». O `/ceo-boot` roda dentro da sessão do CEO. Ou o boot lê um artefato em cache — que o plano **não nomeia** (`model-currency-state.json` é descrito no §4 como estado de CICLO, não como cache de upstream) — ou a W3 viola a regra da W0b. A W3 também não tem linha `Paths:` nem classificação de oráculo, ao contrário de W0a/W0b/W1a/W1b.
*Mitigação:* nomear o artefato de cache e seu produtor, e dar a W2 e W3 a mesma linha `Paths:` + oráculo que as outras quatro ondas têm — a regra de leitura das ondas (`:143-146`) diz «em **cada** onda a perna `a`… a perna `b`…», e W2/W3 não têm pernas, o que já é uma terceira grafia da mesma regra.

**R-VP9 — P3 — `depends_on: [PLAN-169]` aponta para um plano ainda `executing`.**
`.claude/plans/PLAN-169-*.md:4` = `status: executing`. Não é bloqueante (o flip de PLAN-176 para `executing` é decisão 4.10 do Owner), mas o plano deve dizer QUAL entregável da PLAN-169 é a dependência dura e se a W0a pode abrir antes dele — hoje a dependência é um id nu.

**R-VP10 — P3 — O progress log afirma «31 caixas … cada uma com um `Check:` declarado»; uma delas é `Check: none`.**
`:363` — `Check: none (fronteira de escopo…)`. A afirmação é literalmente verdadeira e operacionalmente enganosa: 30 ACs têm oráculo executável, 1 não. Escrever «30 executáveis + 1 fronteira de escopo declarada» custa uma linha e não envelhece.

## O que falta antes de executar (OQ para o Owner ratificar)

- **OQ-1 (bloqueia W1b).** Número do ADR: `ADR-198` está reivindicado por PLAN-186 round-4. Quem fica com 198, e o outro vai para qual número?
- **OQ-2 (bloqueia W0b).** A taxonomia de auditoria fechada não carrega caminho de egresso nem motivo/id recusado. Aceita-se degradar as ACs para os campos existentes, ou a emenda ao `_lib/audit_emit.py` (canônico) entra no escopo — somando uma cerimônia?
- **OQ-3 (bloqueia W1b).** O corte da W1b em 9 paths reais: re-corta em W1b/W1c, ou o Owner autoriza o excedente sobre o teto de 8?
- **OQ-4 (bloqueia W3).** Os alvos reais da W3 são `.claude/scripts/ceo-boot.py` (+ `.claude/commands/ceo-boot.md`) e `.claude/workflows/nightly-hygiene.js`. Confirma-se o alvo antes de a onda abrir?
- **OQ-5.** O cache de upstream que a W3 lê: qual arquivo, quem escreve, e ele é rastreado?
- **OQ-6.** O `PLAN-176-FOLLOWUP-canonical-models-expiry` (§5) é criado agora (o arquivo expirou em 2026-09-01, `.claude/data/canonical_models.json:10`) ou fica como nota?

## Onde o plano falha DEPOIS de executado

1. **O log não distingue os dois destinos de egresso** (R-VP1): no primeiro incidente de feed, ninguém consegue dizer qual endpoint respondeu — a garantia de egresso da W0b perde a evidência que a sustenta.
2. **A degradação da camada P fica invisível** (R-VP2): o `model_choice_recommended` sem motivo entrega um evento que diz que houve troca e não diz por quê; o `/ceo-boot` da W3 mostra um trio sem causa.
3. **A W1b encalha na assinatura** (R-VP5): pacote acima do teto descoberto na véspera da cerimônia — o padrão exato que a noite S329 pagou com o pacote E.
4. **Os critérios de morte não disparam** (R-VP7): o comando que os lê não existe, então K-1/K-3/K-5/K-6 nunca são avaliados e a rotina segue viva com raia cega.

## Nota de disciplina

Nada neste arquivo é opinião sem disco: cada risco cita `arquivo:linha` ou a saída do comando que o mediu (oráculo de canonicidade, `pytest.ini`, `audit_emit.py`, `git ls-files`, censo de ADR). Os must-fix 1-14 e 16 do round 1 estão, no meu julgamento, CURADOS; o 15 está curado pela metade (nome do arquivo do plano corrigido no §5; a âncora nova quebrou — R-VP3). Este round certifica coerência interna do TEXTO e não autoriza nada; `status: reviewed` deve permanecer até o Owner responder OQ-1..OQ-4.
