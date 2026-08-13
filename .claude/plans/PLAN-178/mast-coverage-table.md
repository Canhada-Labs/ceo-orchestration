# PLAN-178 W0 — Tabela de cobertura MAST-14 + injeção inter-agente (S305)

> Sintetizada pelo CEO a partir dos shards de 4 auditores read-only
> (2× QA sonnet, CR opus, Sec opus — rail mitigado ADR-080, prompts
> gerados por `inject-agent-context.sh`). Evidência arquivo:linha em
> cada célula conforme reportada pelos auditores; shards brutos no
> scratchpad da S305 (efêmero — esta tabela é o artefato durável).
> Taxonomia: MAST (arXiv 2503.13657, ref. em `research-S305.md`).

## AC-1 — controles positivos do instrumento

- ✅ **Coberto live-fire:** 4 spawns custom bloqueados com razões
  nomeadas (`reference_missing`, `spawn_prompt_defense_missing`);
  overhead-guard P4 disparou contra o PRÓPRIO auditor cat.1 durante a
  varredura; probe canônico registrado no boot (ceo-boot.py:472,487).
- ✅ **Gap-conhecido reportado como gap:** EXTRA-3.4 (rotação de
  crítico) veio `gap` com evidência — o instrumento discrimina.
- ✅ **Não deu tudo-verde:** 6 coberto / 10 parcial / 4 gap.

## Tabela (20 células)

| Modo | Status | Controle principal | Evidência-âncora |
|---|---|---|---|
| FM-1.1 desobedecer tarefa | parcial | gate de FORMA no spawn; aderência semântica = Step-4 manual | check_agent_spawn.py:2382-2406; PROTOCOL.md:349-359 |
| FM-1.2 desobedecer papel | coberto | recursão Architect bloqueada + veto_floor demote | check_agent_spawn.py:2244-2257,2754 |
| FM-1.3 repetição de passos | coberto | anti-CEO-overhead P1-P5 fail-closed até ack | check_anti_ceo_overhead.py:27-49,613 |
| FM-1.4 perda de contexto | coberto | PreCompact/PostCompact snapshot + reinject pointers (ADR-153) | check_precompact_continuity.py:2-71 |
| FM-1.5 condições de término | coberto | review_loop MAX=3; 3-Strike; máquina de estados do plano | review_loop.py:39; PLAN-SCHEMA.md |
| FM-2.1 reset entre agentes | parcial | bracket compactação advisory; eixo agente→agente sem mecanismo | check_precompact_continuity.py:30-32; team.md:764-766 |
| FM-2.2 não pedir esclarecimento | **gap** | só doutrina (NEEDS_CONTEXT, spec-clarify) | team.md:738-751; PROTOCOL.md:421 |
| FM-2.3 descarrilamento | parcial | duro na forma destrutiva; dentro-da-superfície = manual | check_agent_spawn.py:1546-1573; PROTOCOL.md:337-345 |
| FM-2.4 retenção de informação | parcial | Workflow: degradado envenena CLEAN, counts-win; Task comum: doutrina | audit-fanout.js:102-108,223-233 |
| FM-2.5 ignorar input de par | parcial | release fail-closed (E_DECISION=13); sessão fail-open s/ codex | check_pair_rail.py:18-20; _release_tag_guard.py |
| FM-2.6 raciocínio≠ação | parcial | confidence_gate/fabrication/verify_after_edit — todos ADVISORY vivos | settings.json:739-746; GOVERNANCE.md:127 |
| FM-3.1 término prematuro | parcial | grafo de status fechado (reviewed→done ilegal); prosa sem hook | check_plan_edit.py:111-133,279-297 |
| FM-3.2 verificação ausente | parcial | gates de release fail-closed; adequacy_gate OPT-IN silencioso | pair-rail-gate.sh:64-101; adequacy_gate.py:36-38 |
| FM-3.3 verificação incorreta | **gap** | NENHUM detector de check-vacuoso; caso vivo ao lado do padrão certo | ceo-boot.py:1017-1034 vs 1037-1053 |
| EXTRA-3.4 rotação de crítico | **gap** | debate PREFERE mesmos agentes r1→r3; V2 cold = mesmo vendor | debate.md:104-114; PROTOCOL.md:476-531 |
| INJ-1 retorno de subagente | parcial | scanners Agent advisory; in-harness entra CRU no próximo prompt | audit-fanout.js:142; output_scan.py:368-390 |
| INJ-2 disco→contexto | coberto | _sanitize_for_recs + _validate_boot_lesson fail-CLOSED | ceo-boot.py:204-280,4272-4339 |
| INJ-3 memória compartilhada | **gap** (aceito) | só redact_secrets no ingest; query devolve cru; ADR-089 REFUSED | memory_shared.py:267-347,360-455; ADR-089:36-59 |
| INJ-4 trust-authorization | parcial | canônico forte (sentinel+trusted_env); FILE ASSIGNMENT não é capability | check_canonical_edit.py:1508-1582; audit_log.py:531-535 |
| INJ-5 lanes externas | coberto | ADR-114 single-pass + ingress fenced + decisão igualdade exata | codex_egress_redact.py:1-50; validate-pair-rail-verdict.py:85-97 |

## Achados transversais (ranqueados)

1. **[P1] Doc-claim falso em superfície de governança — CLAUDE.md:88.**
   Afirma bloqueio de spawn sem `## FILE ASSIGNMENT`; live-fire com
   controle positivo mostra ALLOW `{}` silencioso (só skill ausente
   bloqueia). Sem o parse, o spawn não emite
   `spawn_file_assignment_recorded` e SOME da detecção de colisão
   (check_agent_spawn.py:1836-1853) — cujo Rail 3 já é advisory
   (`CEO_SPAWN_OVERLAP_GUARD` não armado). 17ª instância da classe
   instrumento-verde-pergunta-envelhecida. **Cura recomendada: fazer o
   hook cumprir a claim (enforce), não enfraquecer a claim** — decisão
   no debate do PLAN-178; CLAUDE.md só muda em closeout (cache).
2. **[P1] FILE ASSIGNMENT não é capability em write-time (INJ-4).**
   Nenhum hook Edit/Write compara o path alvo com a atribuição do
   spawner; worktree-writer é default-OFF autodeclarado. Autoridade
   residual: subagente escreve qualquer não-canônico. Candidato de
   cura no W1.3 (scoped permissions nativas) — a feature nova do
   substrato pode fechar isso mais barato que hook novo.
3. **[P2] Assimetria de ingest (INJ-1).** Lane externa: capped +
   schema + fenced. Retorno de subagente Claude: interpolado CRU no
   prompt do refuter/síntese (audit-fanout.js:142,190-196) e zero
   fence no nightly-hygiene. Cura barata: fence + cap nos
   consumidores de Workflow (mesmo padrão do council).
4. **[P2] Detectores existem mas estão desarmados na config viva.**
   `CEO_CONFIDENCE_ENFORCE`, `CEO_SUBAGENT_FABRICATION_BLOCK`,
   `CEO_VERIFY_AFTER_EDIT_BLOCK`, `CEO_SPAWN_TOOL_SCOPE`,
   `CEO_SPAWN_OVERLAP_GUARD`, `CEO_UNICODE_HARDBLOCK` — nenhum no
   bloco env de settings.json. Decidir POR ITEM (custo/FP) quais
   viram default-on; não é um flip em massa.
5. **[P2] Sem lint de vacuidade de checks (FM-3.3).** Caso vivo:
   `check_tier_a_spec_version_drift` (ceo-boot.py:1017) sem branch
   red alcançável, ao lado do padrão correto (1037-1053). Cura:
   lint "todo check_* precisa de caminho red alcançável" + positive
   control por check.
6. **[P3] Drift de referência:** ceo-boot.py:240 cita
   `_lesson_render_safe`, símbolo inexistente (real:
   `_validate_boot_lesson`). Classe cura-no-corpo≠referências.
7. **[P3] FM-2.2 (pedir esclarecimento) segue 100% doutrina** — sem
   sinal mecânico; aceitável, registrar como limitação conhecida.

## Disposição

- Gaps 1, 3, 5, 6 → candidatos de cura no próprio PLAN-178 (debate
  decide o lote); gap 2 → resolve-se no W1.3; gap 4 → item por item.
- EXTRA-3.4 → já tem dono: PLAN-178 W2.1 (critic fresco por retry).
- INJ-3 → risco aceito (ADR-089) mas com a justificativa do
  ADR-116-AMEND-1 anotada como insuficiente para ESTA classe —
  reavaliar no debate se o gatilho de reabertura deve incluir o vetor
  escrita-mesmo-plano.
