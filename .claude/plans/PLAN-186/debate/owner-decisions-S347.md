---
plan: PLAN-186
recorded_at: 2026-09-06
recorded_by: CEO (AskUserQuestion, doutrina PLAN-135 K10 — texto da opção selecionada, verbatim; terminal ceo-orchestration-58, 20:1x-20:4x)
---
# Decisões do Owner — S347 (2026-09-06), as 19 decisões respondidas via AskUserQuestion

> Fonte primária: `MORNING-S347.md` §4 (itens 4.13–4.19) + `MORNING-S345.md` §4/§5
> (itens 4.1–4.12, 5.a) — arquivo fora do repo,
> `~/.claude/projects/<project-slug>/s344-packs/OWNER-DECISIONS-S347.md`.
> Cada linha abaixo é o rótulo da opção ESCOLHIDA pelo Owner, verbatim entre «».
> Este arquivo é a cópia canônica no repo; o efeito de cada decisão é copiado
> verbatim para o plano/OQ que a própria linha nomeia.

## Bloco 1 — destravam assinaturas (respondido 20:1x)

| Item | opção selecionada (verbatim) | efeito no plano |
|---|---|---|
| 4.13 — W1 saída 2′ (pins dos 5 agentes VETO no `upgrade.sh`) | «Nunca migrar automaticamente (Recomendado)» | o `upgrade.sh` preserva o pin dos 5 arquétipos VETO e avisa; pins não-VETO migram sob a allowlist. → PLAN-186 W1 / pack `w1-widen` (nota r19 ratificada) |
| 4.12 — W6 divisão | «Dividir em duas assinaturas (Recomendado)» | W6a (recusa + exibição + esforço) assina primeiro; W6b (custo) depois, com tabela de tarifas gerada. → PLAN-186 W6 / pack `w6-adapter` |
| 4.8 — W4b | «Aceitar as duas (Recomendado)» | ACK do desvio dos required checks (`CEO_W4B_REQUIRED_CHECK_ACK=I-ACCEPT` no LAND) + manifesto ADR-192 crescendo de 9 para 12 membros. → PLAN-186 W4b / pack `w4b-ci-matrix` |
| 4.19 — ADR do gate de teto de esforço | «ADR curto na W5b (Recomendado)» | → PLAN-186 W5 / pack `w5-doctrine` (W5b) |

## Bloco 2 — planos (respondido 20:2x)

| Item | opção selecionada (verbatim) | efeito no plano |
|---|---|---|
| 4.5 — PLAN-183 W1 (ponteiro portátil), 4 leituras | «Aceitar as 4 leituras (Recomendado)» | OQ-3 opção 1 (registro tem precedência só enquanto resolve; demovido é mantido e avisado); AC-1 = população de prefixo comum com o limite escrito; 4d = A (e2e só no nightly, medir custo antes de PR); OQ-3c = receita guardada agora, wave `live_content` depois da assinatura. Colateral aceito: tabela de posse 65→68 células; a frase «62 green / 3 red» do `CLAUDE.md` §4 muda no closeout. → PLAN-183 §OQ / pack `p183-w1-pointer` |
| 4.14 — PLAN-176 | «Autorizar a revisão do plano (Recomendado)» | pack docs: renumerar ADR, fetcher em módulo canônico próprio, W0a/W0b, ACs com `Check:`; rodada 2 do debate depois. → PLAN-176 / `debate/round-1/consensus.md` (ESCALATE resolvido) |
| 4.15 — PLAN-175 | «Autorizar a revisão do plano (Recomendado)» | pack docs com os 9 consensos; flip para `executing` só depois. → PLAN-175 / `debate/round-1` |
| 4.2 — Contaminação v4 (remoção da isenção por regra) | «Ratificar a remoção (Recomendado)» | o AC-0 do `PLAN-186-FOLLOWUP-sentinel-gpg-verification` deixa de ser provisório. → esse follow-up + PLAN-186 |

## Bloco 3 — planos (respondido 20:2x)

| Item | opção selecionada (verbatim) | efeito no plano |
|---|---|---|
| 4.3 — PLAN-169 W4.1 retomada por cota (6 decisões) | «Aceitar as 6 recomendações (Recomendado)» | 1=(c) marcador por SESSÃO + lock de disparo por projeto, wave própria; 2=(b) duas entradas exatas (`--consume`, `--mark-armed`) no dogfood + template base; 3=(c) dedupe em memória por processo; 4=(b) prefixo auto-resolvente `cd "$(git rev-parse --show-toplevel)" && python3 …` com a entrada de allow casando a forma composta; 5=(b) reservar marcador antes do `CronCreate` (EXPERIMENTAL); 6=(A) id do job condicionado à sonda, follow-up. O rótulo EXPERIMENTAL fica e declara «inerte para adotantes até o piso de StopFailure mudar». → `p169-w41-quota-resume/OWNER-DECISION-r8-scope-and-allowlist.md` + PLAN-169 W4.1 |
| 4.6 — PLAN-184 N/M | «N = US$ 3/dia e M = 40 % (Recomendado)» | teto medido US$ 2,195/dia < N ⇒ o plano FECHA como residual registrado (pré-registro US0 cumprido; W1 não abre). → PLAN-184 US0 + flip para status terminal pelo próximo terminal (docs) |
| 4.7 — W-ROTA (modelos por perfil) | «Quero rever os modelos escolhidos» | PENDENTE na resposta inicial — revisto pelo Owner no Bloco 3b abaixo (mesma sessão, 20:3x) |
| 4.4 — PLAN-186 AC-1 | «Manter (a), fechado (Recomendado)» | a 4.ª linha (assento `claude-fable-5-1`, 207×660) vira follow-up nomeado. → PLAN-186 AC-1 nota |

### Bloco 3b — W-ROTA, modelos por perfil (4.7 revisto pelo Owner, 20:3x)

| Item | opção selecionada (verbatim) | efeito na wave W-ROTA |
|---|---|---|
| Linha 1 — `devops \| workflow_change:release\|ci` | «Opus 5 (Recomendado)» | `claude-opus-5` substitui o literal `claude-opus-4-8` de `task-route.py:539` |
| Linha 2 — `{qa-architect, performance-engineer, devops} \| profile:max-quality` | «Opus 5 (Recomendado)» | `claude-opus-5` substitui `claude-opus-4-8` em `set-quality-profile.sh:161` |
| Linha 3 — `profile:max-speed` | «devops Haiku 4.5; qa e perf Sonnet 5 (Recomendado)» | `devops` → `claude-haiku-4-5` (grafia do ADR-149); `qa-architect` e `performance-engineer` → `claude-sonnet-5`; item 3 = NÃO servir abaixo do piso (as 2 violações medidas em `routing-matrix.yaml:109/134` fecham pelo valor, não pelo piso) |
| Pergunta do Owner registrada | «e se a Anthropic soltar outros modelos novos precisa fazer isso aqui tudo de novo?» | resposta do CEO: não — a W-ROTA constrói a tabela em DOIS NÍVEIS (papel → nível {quality, balanced, speed}; nível → id), de modo que uma geração nova = 3 linhas + 1 assinatura; detecção automática = PLAN-176 (revisão autorizada em 4.14); adoção nunca automática (`CLAUDE.md` §5). Requisito NOVO para o builder da W-ROTA: tabela em dois níveis, ids só no nível → id |

## Bloco 4 — operação (respondido 20:3x)

| Item | opção selecionada (verbatim) | efeito no plano |
|---|---|---|
| 4.17 — WIP canônico | «No máximo 3 de dia; máximo só em noite autônoma (Recomendado)» | prioridade W1, W6a, W4b. → PLAN-186 modelo v2 |
| 4.16 — gate de latência de hooks | «Recalibrar com teto relativo, follow-up livre (Recomendado)» | promover a fase 1 advisory (chave relativa `hook_p50 ≤ K_e × ref_p50`, S328) a gate; emenda ADR-163; pack livre. → `PLAN-159`/ADR-163 follow-up |
| 4.18 — regra material-only | «Registrar no PLAN-186 (Recomendado)» | docs livre; exceção explícita: nunca para canônicos. → PLAN-186 §modelo v2 |
| 4.10 — flips PLAN-176/175 | DERIVADO de 4.14/4.15 | flip para `executing` só DEPOIS da revisão de cada plano (não perguntado de novo) |

## Bloco 5 — operação (respondido 20:4x)

| Item | opção selecionada (verbatim) | efeito no plano |
|---|---|---|
| 4.1 — cota do codex | «Reservar para sessões de assinatura (Recomendado)» | lander sem codex registra `PENDING-CODEX` e para; nada assinado com registro pendente |
| 4.11 — flakes de CI | «Follow-up livre, sem urgência (Recomendado)» | isolar do relógio do runner `test_ceo_boot_enhanced.py::TestIdempotency::test_back_to_back_identical_results` e `test_write_endpoints.py::TestRealHandlerIntegration::test_audit_event_push_handler_rejects_action_not_in_allowlist` |
| 5.a — nome de projeto privado em 6 planos | «Aceitar como está» (NÃO a recomendação) | nenhum commit de limpeza; registrar a aceitação no PLAN-183 (achado do refutador `p183`) |
| Registro destas decisões | «Deixar para o outro terminal (Recomendado)» | o próximo terminal commita este arquivo como `.claude/plans/PLAN-186/debate/owner-decisions-S347.md` (docs livre) e copia cada resposta VERBATIM para o plano/OQ citado em cada linha |

## O que o próximo terminal faz com isto (ordem, do ledger original)

1. Commit docs: este ledger + PLAN-186 (regra material-only §modelo v2; WIP ≤ 3 de dia; W6 dividida; W4b ACK+manifesto 9→12; AC-1 (a) nota; W-ROTA: tabela em DOIS níveis + 3 linhas decididas) + PLAN-184 (N=3/M=40% ⇒ US0 cumprido, plano fecha como residual) + PLAN-183 (OQ-3 opção 1, AC-1 prefixo comum, 4d=A, OQ-3c wave `live_content`; 5.a aceito) + PLAN-169 W4.1 (6 decisões) + PLAN-176/175 (revisão autorizada; flip depois) + follow-up sentinel-gpg AC-0 ratificado.
2. Lands livres na fila: `p171-w0-lote5` (material-only) → lote6 (re-ancorar) → `p188-plan-r3` (após cura r8) → `p189-plan-draft` (após cura r14) → `p189-pilot-specs`.
3. Canônicos, WIP ≤ 3, ordem W1 (`w1-widen`, saída 2′ ratificada) → W6a (`w6-adapter` estágio a) → W4b (`w4b-ci-matrix`, cura S347-r8); depois `ac13`, `p183` W1, W5a (+ADR na W5b).
4. Packs docs novos: revisão PLAN-176, revisão PLAN-175, follow-up gate de latência relativo, follow-up flakes.
