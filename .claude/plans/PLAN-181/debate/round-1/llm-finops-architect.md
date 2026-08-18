# LLM FinOps Architect — PLAN-181 round 1

## Verdict
ADJUST — a tese está certa e o wrapper é a rota correta, mas o §Cost do plano não cumpre o gate do próprio ADR-125 que ele cita, e o mecanismo apontado (`cost_envelope.py`) não tem granularidade "por tick" nem está ligado sem uma decisão explícita de tier/env.

## Summary

`.claude/hooks/_lib/cost_envelope.py` (lido integralmente) confirma: caps são por classe (`vibecoder`/`CTO`/`team`) × janela `daily`/`weekly`/`monthly`/`per_plan`/`max_parallel`, em CENTAVOS, controlados por `check_and_record()` (atômico, lock-serializado). **Não existe conceito de "tick"** no módulo — a única janela que se aproximaria é `per_plan` (filtro por `plan_id` dentro do state file do dia), então "budget por tick" (W2.2) é implementável, mas só se o wrapper chamar `check_and_record(cents, plan_id=<id do loop>)` a CADA tick e deixar o cap `per_plan` acumular — isso não está dito no plano, e é o desenho certo.

Mais crítico: `is_disabled()` (cost_envelope.py:96-104) retorna `True` (= passthrough, zero enforcement) sempre que `CEO_SWARM` está ausente ou `"0"`. O `cost_envelope.py` foi desenhado para o **PLAN-102/ADR-133 "autonomous-loop" do PRÓPRIO framework** (swarm coordinator), não para o `/loop` nativo do Claude Code CLI que o PLAN-181 quer envelopar — são dois mecanismos de loop DIFERENTES compartilhando o nome. Usar `cost_envelope.py` para o `/loop-governed` é reaproveitamento legítimo (o molde de caps por classe/janela serve), mas ativa a cadeia de 6 camadas de kill-switch do ADR-133 (`CEO_SWARM=1` + sentinel GPG + `CEO_SWARM_<CLASSE>_ENABLED=1` exact-match) — nenhuma linha do PLAN-181 menciona isso. Sem essa decisão explícita, W2.2 é exatamente o "wrapper que virou teatro" que o próprio plano cita como risco (lição t10): o hook chama `check_and_record()`, mas como `is_disabled()==True` por padrão, o cap nunca é avaliado — passthrough silencioso.

## Risks

1. **P0 — §Cost do plano não cumpre ADR-125:234-236 (o próprio ADR citado).** ADR-125 exige, para TODO opt-in Tier C: "(a) per-invocation token estimate, (b) daily burn cap, (c) cost-cap enforcement mechanism" na seção §Cost do plano. `.claude/plans/PLAN-181-loop-governed-adoption.md` não tem seção `## Cost` — tem `budget_tokens: 120-220k` no frontmatter (uma faixa, sem quebra por wave) e a seção `## Riscos` menciona custo recorrente de passagem, mas não declara (a) nem (b) nem nomeia (c). Pela própria checklist da skill (`SKILL.md:678-681`, Acceptance Criteria #1), "budget_tokens sem tier_mix_estimate = MAJOR finding"; aqui falta também `budget_usd_estimate` e `tier_mix_estimate`. Isso é BLOQUEADOR pelo padrão que o próprio plano invoca (ADR-125 é `related_adrs[1]`).
2. **P0 — cost_envelope.py fica DESLIGADO por padrão; o plano não decide ligá-lo.** `cost_envelope.py:96-104` (`is_disabled()`): `CEO_SWARM` ausente ou `"0"` ⇒ passthrough. W2.2 diz "acionar `_lib/cost_envelope.py` por tick; hard cap single-strike" sem citar `CEO_SWARM=1` nem qual `class_tier` (`vibecoder`/`CTO`/`team`) o loop usa. Sem isso, a AC de W2.2 é inverificável — não há como provar RECUSA (lição t10: "toda detecção nova exige RECUSA + controle positivo").
3. **P1 — caps de `vibecoder` são incompatíveis com o cenário W0 se ligados sem escolha de tier.** `cost_envelope.py:70-78`: `vibecoder` = `daily=500¢($5)`, `per_plan=300¢($3)`. Quantificando o pior caso do delay×TTL (ver Unseen): W0 com 24 ticks a 1h de intervalo, cache SEMPRE frio (TTL padrão ~5min << 60min), F≈50k tokens/tick, Sonnet mecânico ($4.2/M efetivo por `SKILL.md:270`) ⇒ **≈$0.21/tick × 24 = ≈$5,04 para o piloto inteiro** — acima do cap `per_plan` de $3 e no limite do cap `daily` de $5 da classe `vibecoder`. Se o wrapper for ligado sob essa classe, o PRÓPRIO piloto W0 dispara o hard cap que ele deveria estar testando. Se a intenção é `CTO`/`team` (caps 5-10x maiores), isso precisa estar escrito — hoje não está.
4. **P1 — parent-inheritance trap não resolvida para o dispatch do tick.** O plano deixa como pergunta aberta ("que tier roda um tick de vigia (Haiku? — precisa de tournament evidence)") sem decidir. Pela doutrina (`SKILL.md:127-132`, Regra 1: "Haiku só com evidência de torneio n≥30/cell") Haiku está PROIBIDO sem essa evidência — não existe torneio para arquétipo "tick de vigia" no catálogo. Floor correto por default é Sonnet (anti-padrão A3, `SKILL.md:589-609`: dispatch sem `model:` herda o tier do pai — se o `/loop` for disparado via `Agent`/Task a partir de uma sessão CEO em Opus, cada tick herda Opus silenciosamente). W2 precisa nomear `model: sonnet` explicitamente no primeiro tick e a MESMA disciplina se aplica ao script `nightly-proposals.py`→`morning_ledger.py` caso ele dispare qualquer sub-agente.
5. **P2-advisory — W2.3 (detector de não-progresso) não tem análise de custo do teto de 2 ciclos.** 2 ciclos sem progresso, se cada um re-paga F frio (cenário nightly ou hold de 1h), custam ≈2×$0.21≈$0.42 em Sonnet antes de escalar — aceitável, mas SE o tick herdar Opus pelo trap do item 4, o mesmo teto custa ≈2×50k×$11/M(Opus reasoning-heavy)≈$1,10 — quase 3x. O teto de 2 ciclos é razoável SOMENTE se o floor de modelo do item 4 estiver fechado primeiro; hoje os dois riscos se compõem.

## Must-fix

- Adicionar seção `## Cost` ao `PLAN-181-loop-governed-adoption.md` com os 3 campos exigidos por ADR-125:234-236: (a) estimativa de tokens por invocação/tick (declarar separadamente W0-tick vs W2-nightly-tick, já que os perfis de cache diferem), (b) cap diário de burn, (c) mecanismo de enforcement nomeado — se for `cost_envelope.py`, dizer explicitamente `CEO_SWARM=1` + qual `class_tier` + qual `plan_id` chave o `per_plan`.
- Adicionar `budget_usd_estimate` e `tier_mix_estimate`/`tier_mix_rationale` ao frontmatter do plano (gap mecânico do Acceptance Criteria #1 da skill).
- W2.2: nomear que window do `cost_envelope.py` mapeia "budget por tick" (resposta: `per_plan`, chamado a cada tick via `check_and_record(cents, plan_id=...)`) e decidir/declarar `CEO_SWARM` + `class_tier` — sem isso a AC não é testável (repete a classe t10: checagem que nunca dispara).
- W2 (qualquer dispatch de tick que use `Agent`/Task): nomear `model: sonnet` explicitamente com a rationale "Haiku não validado por torneio para arquétipo tick-de-vigia" (fecha a OQ do próprio plano e a Regra 1 da skill).
- OQ-5 (dono do custo recorrente): nomear o dono explicitamente no plano (recomendação: LLM FinOps Architect revisa o relatório de tokens/tick no fechamento de cada trem RC→GA para W0; para W2/nightly, o relatório entra no `morning_ledger.py` já citado como consumidor — mas isso precisa virar uma linha do plano, não ficar implícito).

## Nice-to-have

- Quantificar no próprio corpo do plano (não só nesta crítica) o número "$5/piloto W0, ~$0,21/dia recorrente no nightly" — títulos de risco sem número viram "vibe budget" (anti-padrão A5 da skill).
- W1 (inventário `session_crons`): já que é `$0` e mecânico, considerar citar explicitamente no AC que é Sonnet-floor mecânico (não deixar implícito) — barato mas a disciplina de nomear o tier em TODO dispatch é o que a skill cobra (Acceptance Criteria #2).

## Unseen

- **Delay×TTL quantificado (pergunta do dispatcher):** TTL de cache padrão da API é ~5min (extended-cache 1h é beta, custo de escrita maior, não mencionado no plano). Com `/loop 1h` (W0, ~24 ticks ao longo do hold de 24h) e cadência de 1 tick/hora, 60min > TTL em QUALQUER configuração padrão ⇒ **cache SEMPRE frio, todo tick é cache-miss integral** — não é um "caso de borda", é o caso ÚNICO no cenário W0 tal como desenhado. Custo: F≈45-55k × $4,2/M (Sonnet mecânico) ≈ $0,19-0,23/tick × 24 ticks ≈ **$4,56-$5,52 só no piloto W0**, batendo no teto `vibecoder.per_plan` ($3) e quase no `vibecoder.daily` ($5) do próprio mecanismo citado como enforcement — ver Risco 3.
- **Cenário nightly diário:** cadência de 1x/dia garante cache frio SEMPRE (dias >> minutos de TTL) ⇒ ≈$0,19-0,23/dia recorrente, perpétuo, sem relatório nomeado (OQ-5) — pequeno em valor absoluto mas exatamente o padrão que a skill classifica como "MINOR que composto vira MAJOR" (abertura da skill, linha 62-64) quando multiplicado por outros loops futuros que adotem o mesmo molde.
- Nenhum dos dois números acima está no plano hoje — a honestidade "F≈45-55k re-pagos se o cache expirar entre ticks" está lá, mas sem o passo seguinte (multiplicar por contagem de ticks × $/M) que transforma a honestidade em decisão orçamentária.

## What I would NOT change

- A tese central (adotar com wrapper, nunca cru) e a arquitetura dos 7 gaps de W2 — o molde de reuso (night-mode, cost_envelope, swarm_paused_owner_absent) é o padrão certo; nenhum gap novo de FinOps falta na lista dos 7.
- W0 como piloto read-only assistido com Owner presente — a linha dura (nunca corta tag/GA-CUT) é a decisão de segurança correta e não tem dimensão de custo que a contradiga.
- A ordem W1→W2→W3 — não há argumento de custo para inverter a sequência.

DONE_WITH_CONCERNS
