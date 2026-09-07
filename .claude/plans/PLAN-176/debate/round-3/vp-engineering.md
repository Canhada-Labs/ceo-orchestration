---
round: 3
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-07T00:55:00Z
---

## Verdict

ADJUST — **4 itens bloqueantes.**

## Summary (≤ 3 bullets)

- **A cura do round 2 funcionou, e eu a re-verifiquei em disco, não no texto.** Os **20** vereditos de oráculo que o plano publica (§2 :69-81 e as linhas `Paths:` das oito ondas) reproduzem um a um com `check_canonical_edit.py --is-canonical`, inclusive as três descobertas que re-cortaram as ondas (`_lib/tests/test_model_registry.py 1`, `nightly-hygiene.js 1`, `model-currency-expected-reds.txt 0`). Os quatro trechos citados de `_lib/audit_emit.py` (`:1349`, `:1359-1362`, `:1601-1608`, `:8480-8498`) estão corretos **byte a byte**. As contagens de caixas (42 = 8+8+4+7+4+5+4+2) e de `Check: none` (4 = 3 no progress log + 1 fronteira de escopo) batem. O manifesto tem **9** membros, o `pytest.ini` coleta os três diretórios nas linhas 39/41, `nightly-hygiene.js` tem `schedule:` = 0, `F = 97.292` está em `CLAUDE.md:97`, a aritmética de orçamento (510-760k + 6-8×97.292 ⇒ 1,09-1,54M ⇒ 9,84-13,85 USD ao teto e 8,97-12,55 na mistura) fecha nos dois ramos. **15 dos 16 ajustes do round 2 estão cumpridos.**
- **Onde é forte:** o corte W1b/W1c por ORDENAÇÃO (e não por tamanho) é o desenho certo — ele tira da W1b a espera pelo `w4b-ci-matrix`, e a autoridade citada confere (`PLAN-186/debate/owner-decisions-S347.md:21` e `:55`). A degradação das promessas de auditoria aos campos que os allowlists fechados carregam é honesta e mecânica. O ponto cego declarado do oráculo de runtime é a forma correta de fechar a classe «instrumento que prevê código por TEXTO não converge».
- **Onde é fraco:** os quatro bloqueantes são todos da MESMA família — **uma cura do round 2 aplicada a um sítio e não ao sítio irmão**. A regra do ADR ficou não-idempotente; a degradação de auditoria pulou a terceira ação; a régua «Paths = conjunto das ACs» foi aplicada a W1b/W1c e não a W2a; e a §4 ganhou dois critérios de morte que a AC que os deve ler ainda não conta.

## Risks

**R-VP1 — CRITICAL — BLOQUEANTE — A regra do §3.4 é não-idempotente: reproduzida em HEAD ela elege 179, não 180, e o número publicado é falso.**
`PLAN-176:290-292` publica «**Saída medida em HEAD**: 22 livres …; **13 com zero menção** `[68, 166, …, 179, 180]`; escolhido **180**». Rodei o snippet do próprio plano (`:270-285`) no HEAD de hoje, com o plano já landado:

    livres 22 [68, 130, 134, 166..180, 184, 187, 188, 189]
    zero   12 [68, 166, 167, 168, 169, 170, 171, 172, 176, 177, 178, 179]
    max    179

O delta é exatamente **180**, e a causa é o próprio texto: `grep -rl 'ADR-180' --exclude-dir=.git .` agora casa o arquivo do plano. Duas consequências, e as duas são defeito: (i) a linha `:290-292` é **falsa em HEAD** — o número «13» e o `max` já não reproduzem; (ii) a regra, como publicada, **nunca pode re-eleger a sua própria escolha** — qualquer pessoa que a rode para conferir aterrissa em 179 e conclui que o plano errou. É a forma exata do defeito que o round 2 mandou curar (adjustment 8: «regra determinística **reprodutível**»), um número adiante. Note que a AC de reserva (`:643-646`) usa uma régua DIFERENTE (`grep -rl` em `.claude/plans --exclude-dir=debate` menos `PLAN-176`) que fica verde — então nenhum portão enxerga a contradição.
*Mitigação:* uma linha no §3.4 — a regra roda com o arquivo deste plano EXCLUÍDO (`--exclude=PLAN-176-*.md`), e a saída publicada carrega a âncora de commit em que foi medida. Ou congelar a medição declarando-a pré-land. Custo: uma frase; sem ela, o §3.4 refuta a si mesmo.

**R-VP2 — CRITICAL — BLOQUEANTE — A AC `refused_destination_emits_event` exige um campo que a mesma página prova não existir.**
`:534-537` — «Um destino fora da allowlist emite `egress_destination_detected` com o host recusado **e a decisão**», e `:496` repete: «o que a cadeia carrega é host + `egress_class` … **+ a decisão**». Medido em `_lib/audit_emit.py:8480-8488` — e o plano cita esse mesmo bloco corretamente em `:487-490`:

    _EGRESS_DESTINATION_DETECTED_ALLOWLIST = frozenset({
        "action", "session_id", "project", "egress_class", "destination",
        "ts", "event_schema", "tokens_in", "tokens_out", "tokens_total",
        "hmac", "hmac_error"})

Verificado por leitura do frozenset: `'decision' in allowlist` ⇒ **False**. Não há campo `decision` nesta ação — ao contrário de `model_routing_enforced` (`:1601-1608`), onde ele existe e onde o plano o usa com razão. O ajuste 6 do round 2 degradou as promessas de DUAS ações (§3.1 e §3.3) e **pulou a terceira**. Resultado: duas seções da mesma onda se contradizem (`:487-490` lista o allowlist sem `decision`; `:496` e `:534` afirmam que ele viaja), e a caixa `refused_destination_emits_event` só fecha com a rota cara da **OQ-2** — que o §5b declara explicitamente como NÃO executada.
*Mitigação:* a promessa que sobrevive ao scrub é «host recusado + `egress_class`»; o FATO da recusa distingue-se do despacho pela ausência do par no relatório, não por campo na cadeia. Reescrever `:496` e `:534` para isso, ou mover a AC para dentro da OQ-2 e dizer que ela não abre sem a decisão do Owner.

**R-VP3 — CRITICAL — BLOQUEANTE — O conjunto-vermelho publicado contradiz `active_lanes_is_anthropic_only`, e uma das suas quatro pernas se apoia num símbolo que não existe em código vivo.**
`:380-383` publica «**quatro identificadores estão vermelhos hoje**: `claude-haiku-4-5-20251001`, `claude-mythos-5` e `claude-opus-4-8-fast` fora do conjunto de trabalho do ADR-149, e **`gpt-5.6-sol` fora de `_VALID_MODELS`**». Duas medições:
- `grep -rn 'VALID_MODELS' --exclude-dir=.git .` casa **apenas** `.claude/plans/PLAN-142/staging/codex_cli_shape.py` (artefato de *staging* sob um diretório de plano) e a prosa deste plano. `.claude/hooks/_lib/adapters/codex.py` e `_constants.py`: **zero ocorrências**. Não existe autoridade VIVA chamada `_VALID_MODELS` em HEAD — a quarta perna do conjunto-vermelho não tem fonte executável.
- A mesma onda declara em `:400-408` que «Fornecedor sem linha de preço é INERTE por construção» e que «na abertura existe exatamente **UMA raia ativa: Anthropic**» (confirmei: `cost-table.yaml` tem 12 identificadores, todos `claude-*`). Um vermelho de raia OpenAI **não pode ser produzido** por um detector cuja raia OpenAI é inerte.

E a AC `:392-399` fecha a armadilha: «`--expected-reds` compara o conjunto EXATO e falha em QUALQUER diferença — **inclusive encolhimento**». Um arquivo semeado com 4 linhas contra um detector que só consegue produzir 3 nasce **VERMELHO no dia do land** — a classe «caixa permanentemente vermelha» que o round 2 curou em C1/C5 e que reaparece aqui pelo lado do CONTEÚDO em vez do lado do caminho.
*Mitigação:* o arquivo de vermelhos-esperados nasce com as **3** linhas da raia ativa; a linha `gpt-5.6-sol` entra num bloco comentado «raia inerte — reabrir quando houver linha de preço», como `ownership-expected-reds.txt` faz com a causa por linha. E a §W0a nomeia a autoridade real da linha OpenAI (hoje: nenhuma em código vivo) em vez de `_VALID_MODELS`.

**R-VP4 — HIGH — BLOQUEANTE — A AC que torna os critérios de morte LEGÍVEIS conta sete; a §4 tem nove.**
`:364-370` — «A bandeira de leitura `--state --json` … serve os **SETE** critérios de morte … o teste enumera os **sete** critérios», com o nome `state_json_serves_all_seven_death_criteria`; `:839` repete o vínculo. Medido na tabela do §4: `grep -c '^| K-'` ⇒ **9** linhas, `:844-852` (K-1 … K-9). Os dois critérios que faltam são exatamente **K-8 (zero raias ativas)** e **K-9 (rotina parada)** — os dois que ESTA cura criou (`:855-869`), e K-9 é, pelo texto do próprio plano, «a única perna que enxerga a rotina morta». Um teste escrito ao nome da AC enumera sete e passa verde com a perna de vida FORA da leitura: o instrumento de vida do plano fica sem consumidor, que é a classe «instrumento verde cuja PERGUNTA envelheceu» já paga por este repo.
*Mitigação:* renomear a AC para `state_json_serves_all_nine_death_criteria` e trocar «SETE»/«sete» por «NOVE»/«nove» em `:364-368`. Melhor ainda: a AC assere que a saída cobre **todas** as linhas `^| K-` do §4, derivando a contagem do arquivo em vez de digitá-la — é a regra «figura GERADA por instrumento, nunca digitada» do modelo de operação v2.

**R-VP5 — MEDIUM — não bloqueante — A W2a viola a «Regra de leitura» que a própria cura escreveu.**
`:295-307` fixa que toda onda declara «uma linha `Paths:` com o conjunto EXATO dos caminhos que ela toca», e o re-corte W1b/W1c foi justificado por «a lista de caminhos da onda e o conjunto de caminhos das suas ACs têm de ser o MESMO conjunto» (ajuste 2 do round 2). Medido na W2a: `Paths (2)` em `:721-723` = `model-currency-propose.py` + `test_model_currency_proposal.py`; as etiquetas das 5 caixas, extraídas mecanicamente, são `[P0][US5][.claude/data/models-preference.json]`, `[P0][US5][.claude/governance/models-registry.json]`, `[P0][US5]`, `[P1][US5]`, `[P1][US5]` — **duas** apontam para caminhos FORA da linha `Paths:` e **três não têm segmento de caminho nenhum**. O plano explica os dois primeiros como «alvo de controle, não caminho editado» (`:715-720`), o que é razoável, mas então a régua tem duas leituras e a W1b foi re-cortada por causa da leitura estrita. (Não é violação de `PLAN-SCHEMA.md` §13.2 — verifiquei: o esquema exige cobertura de `Check:`, não a tripla de etiqueta.)
*Mitigação:* uma linha na «Regra de leitura» distinguindo *caminho EDITADO* de *alvo de CONTROLE*, e a W1a/W1b/W1c relidas sob a mesma distinção — ou etiquetas de caminho nas três caixas nuas.

**R-VP6 — MEDIUM — não bloqueante — A W1c espera um pacote de OUTRO plano e essa espera não tem dono, relógio nem critério de morte.**
`:678-681` — «A W1c só abre depois do land do `w4b-ci-matrix`». A autoridade confere (`PLAN-186/debate/owner-decisions-S347.md:21`, manifesto 9→12; `:55`, prioridade W1 → W6a → W4b) e o manifesto vivo tem **9** membros hoje. Mas o `w4b-ci-matrix` é o **terceiro** numa fila de WIP canônico ≤ 3, e o plano não diz o que acontece se ele não aterrissar. O custo é concreto e nomeado pelo próprio texto: **K-2 inteiro** («proposta tocando a camada T ⇒ vermelho fail-closed no CI») é fiado pela W1c (`:845`), e a caixa `k2_trust_layer_touch_is_red_in_ci` (`:704-708`) diz que «sem isto, K-2 é declaração e não catraca». Ou seja: uma espera indefinida em pacote de terceiro deixa um critério de morte como declaração, sem que nada fique vermelho.
*Mitigação:* dar à espera a mesma perna de relógio que a §4 deu aos ciclos — um prazo declarado após o qual a W1c ou abre com re-derivação de baseline sobre o manifesto de 12, ou K-2 é registrado como dívida ABERTA no §5b. Sem isso, é a única dependência do plano sem dono.

**R-VP7 — MEDIUM — não bloqueante — Duas das três autoridades do detector offline são citadas por nome nu, e as duas são ambíguas em disco.**
`:333-336` — o detector compara os blocos do ADR-149 «com `cost-table.yaml`, `model-deprecations.json` e `settings.json`». Todas as outras autoridades do plano carregam caminho completo (`.claude/scripts/cost-table.yaml:29`, `.claude/hooks/_lib/audit_emit.py:8480-8488`). Medido: `model-deprecations.json` existe em **`.claude/scripts/`** e há uma segunda cópia viva em `npm/.claude/scripts/`; `settings.json` é ambíguo entre `.claude/settings.json`, `.claude/settings.local.json` (os dois existem) e a superfície de perfil `user`, que por ADR-197 / wave-s330-F é **DERIVADA** da base por subtração declarada e mora em `templates/settings/settings.user.json`. Um detector de currency que lê uma das três superfícies de settings é estruturalmente cego às outras duas — e nenhuma AC diz qual.
*Mitigação:* caminho completo nas três autoridades da `:335`, e uma frase dizendo se o espelho `npm/` e o perfil `user` derivado entram no censo (a resposta certa é provavelmente «sim ao `user` derivado, não ao espelho `npm/`», mas é decisão, não default).

**R-VP8 — LOW — não bloqueante — A AC do flip do ADR depende de uma convenção de `status:` que é minoritária no diretório.**
`:637-641` fecha a caixa com `grep -qx 'status: PROPOSED'`. Medido em `.claude/adr/`: **8** arquivos casam `^status: PROPOSED$` e **85** casam `^status: ACCEPTED$` — a forma existe, então a caixa é satisfazível e **não** nasce vermelha. Mas **86** arquivos usam a grafia `Status` capitalizada e/ou em *bullet*, e a linha S333 de `CLAUDE.md` registra que essa mesma classe de âncora já falhou uma vez neste repo (nove ADRs «sem `Status:`» que tinham o campo em *bullet*). Um ADR-180 escrito na grafia majoritária deixa a caixa vermelha por FORMA, não por substância.
*Mitigação:* a AC diz explicitamente que o ADR-180 nasce com o campo em `status:` minúsculo na linha 4 do *frontmatter*, no molde de `ADR-195`/`ADR-196` (verificados: `:4 status: PROPOSED`).

## Missing before execution (OQ que o Owner ratifica — não decididas aqui)

As três OQ do §5b (`:945-950`) estão bem-postas e nenhuma bloqueia uma onda: **OQ-1** (arbitrar 198 entre este plano e `PLAN-186/debate/round-4` — verifiquei que `proposal.md:133` de fato o reserva, e que 199/200 também estão falados), **OQ-2** (emendar `_lib/audit_emit.py`, oráculo = 1, +1 caminho canônico e +1 assinatura — e note que **R-VP2 aumenta o preço da rota barata**: sem a OQ-2 uma AC precisa ser reescrita, não só degradada), **OQ-3** (8 caminhos numa assinatura contra o re-corte em duas). Acrescento uma quarta que o plano deveria NOMEAR e não decidir: **a espera da W1c pelo `w4b-ci-matrix`** (R-VP6) é a única dependência do plano cujo desfecho está fora da autoridade do CEO e cujo não-desfecho apaga um critério de morte — merece linha própria na tabela do §5b, com a rota barata («K-2 fica declarado como dívida») ao lado da cara («re-priorizar o WIP canônico»).

O `status:` permanece `reviewed`; o flip é a decisão 4.10 do Owner e não é matéria deste round.
