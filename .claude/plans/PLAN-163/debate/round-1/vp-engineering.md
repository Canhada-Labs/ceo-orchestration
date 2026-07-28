---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: VP Engineering (archetype)
generated_at: 2026-07-27T00:00:00Z
---

## Verdict

ADJUST — o plano tem a forma certa (1 plano, evidência verificada, W1 red-first), mas contém uma interação de settings que contradiz a própria OQ2, um pin de depth que pode quebrar os instrumentos Workflow existentes, e uma cerimônia que na prática são duas.

## Summary (≤ 3 bullets)

- O plano reconcilia a janela de substrato 2.1.199→2.1.220 + adota a família Claude 5 em 6 threads com uma cerimônia canônica única, com ênfase em velocidade/paralelização.
- Forte: base de evidência verbatim + inventário file:line (spot-check: 8 de 9 claims verificados conferem); disciplina red-first no W1 ("o número decide, não a vontade"); posturas conservadoras nos drafts das OQs.
- Fraco: interações entre superfícies não mapeadas — `enforceAvailableModels` × sonnet-5 default, depth-pin × instrumentos Workflow, pin codex × pair-rail do próprio pack, e o rail V2 (pair-rail) está RED agora, exatamente quando este plano precisa dele para edits de kernel.

## Risks

- **R-VP1 — HIGH — Adicionar sonnet-5 ao `availableModels` flipa o default de sessão ANTES do re-baseline do tokenizer.** O `_enforce_available_models_comment` (settings.json, junto à chave `enforceAvailableModels: true`) documenta: quando o tier default do harness NÃO está na allowlist, o Default resolve para a primeira entrada permitida. Sonnet 5 é o default do CC desde 2.1.197; hoje ele está FORA da lista, então o default efetivo é pinado. No momento em que T1.1 adiciona `claude-sonnet-5`, o tier default passa a estar na allowlist → o default de sessão vira sonnet-5 com tokenizer +30%, invalidando budgets — exatamente o que a OQ2 diz querer adiar. Mitigação: T1.1 verifica a semântica de resolução primeiro; se confirmada, a entrada sonnet-5 no `availableModels` migra para o passo pós-baseline da OQ2 (ou pina o default de sessão explicitamente no mesmo commit).
- **R-VP2 — HIGH — Pin `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` pode quebrar os instrumentos Workflow.** audit-fanout (8 finders + refuters por dimensão), nightly-hygiene (8 + synthesis) e council-audit orquestram agentes; se qualquer camada dessas roda como agente que spawna agentes, é spawn depth-2 e o pin bloqueia o instrumento. O plano propõe o pin sem probe de regressão sobre os instrumentos existentes. Mitigação: probe W1 dos 3 instrumentos sob o pin + verificação do NOME do env var contra o binário 2.1.220 (classe env-inventory, o footgun S218).
- **R-VP3 — HIGH — O gate V2 está degradado agora.** Telemetria corrente: `pair_rail` fail-opened em TODAS as 11 invocações classificadas na janela de 168h (`failopen_rail_liveness_7d` RED; pendência Passo 4 do PLAN-161). O success criterion deste plano exige pair-rail APPROVE sobre pack canônico/kernel (settings, agent_frontmatter, hooks novos). `depends_on: [PLAN-161]` existe, mas não nomeia QUAL parte de 161 é pré-condição dura. Mitigação: W3 só abre com o rail comprovadamente verde (1 review risky sadio na janela).
- **R-VP4 — MEDIUM — O cap N≤6 tem TRÊS justificativas documentadas; T4 re-mede UMA.** A skill (parallelization-by-default SKILL.md:93-99, verificado) fundamenta o cap em (a) contenção flock do audit-log, (b) git index lock com >6 sub-agentes staging simultâneo, (c) precisão do tally do token-budget-guard com >6 in-flight. T4.1 re-mede só o flock. Subir para N=8 pelo flock deixa (b) e (c) sem base empírica. Mitigação: re-validar as três, ou escopar o cap novo a fan-outs read-only/sem-staging (mantendo 6 para waves que commitam patches).
- **R-VP5 — MEDIUM — Ordem pin-codex × pair-rail do próprio pack é circular e não declarada.** T5.2 pina codex 0.144.1→0.144.6 via cerimônia ADR-111 dentro do MESMO plano cujo pack W3 é revisado pelo codex. Revisar o pack com pin velho e landar o pin junto = o verdict ancora num reviewer que o próprio pack substitui. Mitigação: declarar a ordem (pin primeiro, própria cerimônia ADR-111; pack depois, revisado no pin novo) — ver Must-fix 5.
- **R-VP6 — MEDIUM — Contagens hardcoded no plano ficam stale DENTRO do próprio plano.** T2 promete oracle "44/44" e T3 adiciona 2 hooks (44→46 wired, 46→48 registrations). O repo já tomou 2× main-red por drift de contagem (tolerance=0). Mitigação: oracle deriva o conjunto de hooks do settings.json em runtime; hook_live_smoke reconta, não assume.
- **R-VP7 — LOW — G3 mischaracteriza 3 das 5 evidências como "defaults vivos", e o fix errado quebraria replay.** Verificado: `generate-dispatch.py:316` é mapa de label de display (fall-through gracioso para ids novos); `context-budget.py:42,112` são docstrings referenciando o script `profile-opus-4-7.py` (renomear o profiler é outra decisão); `detectors/overpowered.py:28` é set de CLASSIFICAÇÃO (`_LARGE_MODELS`) — o fix é ADITIVO (incluir opus-5/fable-5), nunca remover opus-4-7, senão replay de logs históricos deixa de classificar. Só `audit-telemetry.py:40-44` (pricing sem a frota atual) é fix substantivo. Path correto do parity: `scripts/local/smoke-install-parity.sh` (não `.claude/scripts/`). Mitigação: corrigir as disposições por item no T1.6.
- **R-VP8 — LOW — Edit da skill (cap 6→8) não declara o rail de governança.** A pilha de guards por tipo de arquivo exige SP-NNN + soak para SKILL.md; T4.1 trata como edit comum. Mitigação: nomear o rail (SP-NNN) ou justificar edit canônico direto sob o scope do sentinel da cerimônia.

## Must-fix (blocking)

1. **T1.1 (R-VP1):** verificar a semântica default-resolution de `enforceAvailableModels` no 2.1.220 ANTES de adicionar `claude-sonnet-5` a `availableModels`; se o tier default entra em vigor ao entrar na allowlist, mover a entrada sonnet-5 para o passo pós-baseline da OQ2 ou pinar o default de sessão explicitamente no mesmo commit. Sem isso, a OQ2 draft ("migrar default só após re-baseline") é natimorta.
2. **T4.3 (R-VP2):** antes do pin depth=1, probe W1 provando que council-audit, audit-fanout e nightly-hygiene não spawnam em depth≥2 sob 2.1.220 + confirmação do nome exato do env var contra o binário.
3. **Pré-condição W3 (R-VP3):** nomear a restauração do `failopen_rail_liveness_7d` (PLAN-161 Passo 4) como gate duro antes de qualquer review de pack — o V2 é o único truth-gate LLM e está fail-opening em 11/11 invocações na janela atual.
4. **T4.1 (R-VP4):** a decisão de cap deve cobrir as 3 justificativas documentadas na skill (flock, git index lock, budget-guard tally) — medir as três, ou escopar o cap 8 a fan-outs read-only e manter 6 para staging.
5. **T5.2 (R-VP5):** declarar a ordem pin-codex vs pack-review e reconciliar com o success criterion de "uma cerimônia": ou são DUAS cerimônias (ADR-111 do pin primeiro; pack GPG depois, revisado no pin novo), ou o plano aceita explicitamente review no pin velho e registra isso no verdict.
6. **T2/T3 (R-VP6):** oracle `hook-stdout-schema-check` deriva o conjunto de hooks do settings.json (zero contagens hardcoded); check do T3 reconta registrations (48, não "46/46"); T6.2 já cobre CLAUDE.md, mas o plano deve declarar que os counts de CLAUDE.md (55 on disk/44 wired/46 registrations) MUDAM com T3 — a edição no closeout é obrigatória, não condicional.
7. **T3.1 (novo):** verificar via a extração de schema do T2.2 se o evento `DirectoryAdded` suporta decisão de bloqueio antes de prometer `CEO_DIRADD_HARDBLOCK=1`; se for notify-only (pós-fato), re-escopar o opt-in para alert/telemetria — prometer hardblock num evento não-bloqueável é contrato morto.
8. **T1.6 (R-VP7 + achado novo):** corrigir as disposições por evidência (aditivo nos detectors; display-map é cosmético; docstrings do profiler são decisão separada; path `scripts/local/`) e ampliar o sweep do team.md — há DUAS linhas drifted, não uma: `team.md:578` ("Default CEO model: Sonnet 4.6 / Upgrade to Opus 4.8") além da `:589` citada.
9. **T4.1 (R-VP8):** declarar o rail de governança do edit em `parallelization-by-default/SKILL.md` (SP-NNN + soak, ou inclusão explícita no scope do sentinel com justificativa).

## Nice-to-have (advisory)

1. T6: estender o sweep de counts aos docs não-vigiados (ARCHITECTURE/GUIA-COMPLETO/FAQ/npm-README) — classe de drift já observada em GA v1.1.0.
2. T3: hooks novos nascem com fixtures unitárias + `TestEnvContext` além do probe live (padrão da casa; o probe prova wiring, a fixture prova contrato).
3. ADR-181: declarar a consequência da doutrina N-1 do VETO floor — com `{opus-4-8, fable-5, opus-5}` o set vira 3-wide; nomear o critério de saída do opus-4-8 (follow-up pós-migração) para honrar o comentário do kernel (`agent_frontmatter.py:130-136`).
4. T1.7: `STALE_RE += claude-opus-4-1` só após 2026-08-05 e lembrando as exemptions de fixtures/replay do parity.
5. OQ2: dimensionar o re-baseline honestamente — tokenizer +30% afeta também `context_budget_tokens` no frontmatter das 166 skills e a estimativa de custo de debate (DEBATE-SCHEMA §9, ~90K/round); se a migração do advisory default exigir re-baseline dessas superfícies, isso é follow-up plan, não item.
6. Budget: 250-350k/3 sessões é plausível só se o re-record de fixtures (T5) for mecânico; pré-autorizar uma 4ª sessão evita handoff apertado.

## Unseen by the original plan

1. **A interação `enforceAvailableModels` × sonnet-5** (R-VP1) — o plano trata `availableModels` como allowlist pura; o comentário no próprio settings.json documenta que ela também governa a resolução do DEFAULT. É a única linha do plano que pode mudar o modelo de TODAS as sessões como efeito colateral.
2. **Instrumentos Workflow como consumidores de depth≥2** (R-VP2) — o plano avalia depth-3 como capability nova, mas não pergunta se o pin conservador quebra o que JÁ existe.
3. **"Uma única cerimônia canônica" (thesis) vs duas cerimônias reais** — o pin codex tem runbook próprio (ADR-111) e relação circular com o reviewer do pack (R-VP5).
4. **O estado corrente do pair-rail** — o plano assume o V2 disponível; a telemetria da janela diz o contrário (R-VP3). Sequenciamento com PLAN-161 precisa ser nominal, não só `depends_on`.
5. **A base tripla do cap N≤6** — o plano cita a contenção flock como "a base empírica" do cap; a skill documenta três fundamentos independentes (R-VP4).
6. **Pilha de governança por tipo de arquivo** — SKILL.md tem rail próprio (SP-NNN + soak); o plano só modela canonical/kernel vs mecânico (R-VP8).
7. **`team.md:578`** — segundo ponto de drift textual de modelo, fora do escopo citado (só :589).
8. **Blockability do `DirectoryAdded`** — o desenho do hook novo promete um modo hardblock sem verificar se o evento aceita decisão de bloqueio (Must-fix 7).

## What I would NOT change

- **A forma 1-plano/1-pack-canônico para os 6 threads.** Split (model-refresh vs hook-events) dobraria o custo de cerimônia e os dois lados editam settings.json — um sentinel scope único é mais limpo e o precedente PLAN-161 (7 threads/1 cerimônia) provou o padrão. A única correção necessária é a honestidade sobre o pin codex (Must-fix 5), não o split.
- **W1 red-first como gate dos edits canônicos** — oracle que nasce vermelho + "o número decide o cap" é exatamente a disciplina certa; não diluir.
- **OQ3 draft pin=1** — postura conservadora correta para preservar a assunção de spawn auditado em 1 nível; só precisa do probe de regressão (Must-fix 2), não de reversão.
- **OQ4 documentar postura sobre agent teams** — correto não adotar peer-messaging sem modelo de governança; resistir à tentação de "adotar porque existe".
- **Default audit-only do `check_directory_added.py`** com deny opt-in — coerente com fail-open-on-infrastructure; mudança de perímetro mid-session invisível é gap real e a priorização como segurança está certa.
- **A base de evidência** — verificação verbatim das 4 claims perigosas do CHANGELOG + inventário file:line é o padrão que evitou drift em planos anteriores; 8 de 9 spot-checks meus conferem (o 9º é a nuance do R-VP7, não um claim falso).
- **G11 SKIP (plugins)** — verificado e corretamente descartado.
