Inventário completo. Tenho evidência suficiente — segue o relatório.

---

# Auditoria da classe "model-id/geração hardcoded" — superfícies vivas

**Autoridade usada (skill `claude-api`, cache 2026-06-24):** frota corrente = `claude-opus-5` ($5/$25), `claude-fable-5` ($10/$50), `claude-sonnet-5` ($3/$15 sticker; intro $2/$10 até 2026-08-31), `claude-haiku-4-5` ($1/$5); N-1 ativos: `claude-opus-4-8`, `claude-sonnet-4-6`. Fast mode: só Opus 5/4.8 ($10/$50). Não existe variante `[1m]` na geração 5 (1M é default). `claude-opus-4-1` **retirou em 2026-08-05 — há 3 dias**.

**Escopo varrido:** ~363 hits fora de `tests/` em `.claude/{scripts,hooks,commands}`, `team.md`, `CLAUDE.md` (zero hits), `templates/`, `scripts/`, `.github/workflows/` + ~40 arquivos em `docs/`. A maioria é display/histórico/fixture. **7 superfícies funcionais têm problema real.**

## Correção ao pré-scan (importante)

Os agent files **hoje NÃO estão em 4-8**: os 5 VETO holders estão em `claude-fable-5` e os advisories em `claude-sonnet-4-6` (verificado em `.claude/agents/*.md`). A inversão "VETO abaixo da sessão" **não está ativa — está a um comando de distância** (F1 abaixo).

## Tabela de achados

| # | arquivo:linha | string | classe | sev | cura de 1 linha |
|---|---|---|---|---|---|
| F1 | `.claude/scripts/set-quality-profile.sh:49-55` | perfis pinam canonical-5 em `claude-opus-4-8`/`sonnet-4-6`/`haiku-4-5-20251001` | **FUNCIONAL** | **P1** | Derivar o mapa de perfis da autoridade ADR-149 (ceiling corrente = fable-5), não de literais 4.x |
| F2 | `.claude/scripts/tier_policy_cli/learn.py:541-544` | `_tier_rank` sem `opus-5`/`sonnet-5` → rank −1 | **FUNCIONAL** | **P1** | Adicionar gen-5 ao `order` (ou derivar de `_types`); hoje `_direction(opus-5→sonnet-4-6)` = "promote" (é demote de 2 gerações — contorna o gate de demote) |
| F3 | `.claude/scripts/value-dashboard.py:264-272` | pricing sem `opus-5`/`fable-5`/`sonnet-5`; `compute_cost_usd` → `None` | **FUNCIONAL** | **P1** | Espelhar as linhas gen-5 de `ceo-cost.py:76-87` — custo da frota CORRENTE está invisível no dashboard |
| F4 | `.claude/hooks/check_codex_stop_review.py:117` | `_DEFAULT_REVIEWER_MODEL = "claude-opus-4-8"` | **FUNCIONAL** | P2 | Default → `claude-opus-5` (reviewer cross-model pós-land, VETO-adjacente, roda 2 gerações abaixo do ceiling) |
| F5 | `.claude/hooks/_lib/tier_policy/_types.py:103-109` + `loader.py:24-25,428` | enum `MODEL_ID` fechado sem `opus-5`/`fable-5`; loader REJEITA `default_model: claude-opus-5` | **FUNCIONAL** | P2 | Adicionar membros gen-5 (nomes estáveis, R-CR R2-2); inconsistente com `learn.py` que já rankeia fable-5 |
| F6 | `templates/.claude/tier-policy.json:7-27` | baseline de adopter pina 4-8/4-6/haiku-dated | **FUNCIONAL** | P2 | Regenerar baseline na geração corrente (fresh install herda política de geração antiga) |
| F7 | `.claude/scripts/tournament/runner.py:39-47,88` | `DEFAULT_MODELS` + `JUDGE_MODEL="claude-opus-4-8"` + pricing sem gen-5 | **FUNCIONAL** | P2 | Torneios avaliam/julgam a frota antiga; adicionar arms/judge gen-5 |
| F8 | `.claude/hooks/audit_log.py:901` | `"devops": "claude-haiku-4-5-20251001"` (dated) em `EXPECTED_MODEL_BY_ROLE` | FUNCIONAL (advisory) | P3 | Trocar pelo bare `claude-haiku-4-5`; o dated id não está em `availableModels` do settings (risco de interação com `enforceAvailableModels`) |
| F9 | `.claude/scripts/model-deprecations.json` (replacements) | `repl: claude-opus-4-8`/`sonnet-4-6` para modelos retirados | FUNCIONAL (guia) | P3 | Refresh do ledger (`fetched: 2026-06-12`): guia de migração corrente é opus-5/sonnet-5; o `(-> X)` do checker aponta para trás |
| F10 | `.claude/scripts/optimizer/model_normalize.py:62-73` | alias map só cobre 4.x | FUNCIONAL (latente) | P3 | Adicionar aliases gen-5; normalização de `"opus-5"` bare é indefinida |
| D1 | `.claude/hooks/audit_log.py:40-41,835-844` | docstrings "current fleet = 4-8/4-6/haiku" | DISPLAY | P3 | Atualizar prosa (a tabela `EXPECTED_MODEL_BY_ROLE:889-924` JÁ migrou p/ gen-5) |
| D2 | `.claude/hooks/check_agent_spawn.py:2151` | msg de bloqueio "requires… claude-opus-4-8" | DISPLAY | P3 | Enforcement real é membership em `VETO_FLOOR_ALLOWED` (4-8, fable-5, opus-5); mensagem mente sobre a regra |
| D3 | `.claude/scripts/inject-agent-context.sh:753` | "INHERITS parent CEO model (Opus 4.8 by default)" | DISPLAY | P3 | Confirmado display-only: `MODEL_HINT` usa tiers genéricos `opus`/`sonnet` (linhas 247-285) ✓ |
| D4 | `.claude/team.md:578,592` | "Default CEO: Sonnet 4.6 / VETO ALWAYS Opus 4.8" | DISPLAY (mitigado) | P3 | Notas `[UPDATED PLAN-163]` existem, mas o texto legado é o principal e a correção é rodapé — inverter. Gate-2 cache-stable: editar só em closeout |
| D5 | `.claude/skills/core/llm-routing-and-finops/SKILL.md:104-123,254-258` | floor table + price card inteiros em 4-8/4-6/haiku; sem gen-5 | DISPLAY-doutrinário | **P2** | O manual do próprio archetype FinOps ensina ids/preços de geração antiga (Sonnet 5 intro nem aparece); Gate-2 cache-stable → closeout |
| D6 | `.github/workflows/validate.yml:1168` | job `opus-4-7-profiler-smoke` | DISPLAY | P3 | Nome de job herdado; renomear na próxima mexida no workflow |
| D7 | `docs/*` (~40: QUALITY-PROFILES, CEO-MODEL-ROUTING, provider-pricing, cost-of-operation, CHEAT-SHEET, DAY-1-CHECKLIST, opus-4-7-operations…) | prosa 4.x extensa | DISPLAY | P3 | Sweep único de docs no mesmo item de classe; `QUALITY-PROFILES.md` documenta F1 e herda a cura |
| OK1 | `.claude/scripts/audit-telemetry.py:47-62,116` e `ceo-cost.py:76-87,201` | linhas 4-7/[1m]/4-6/haiku retidas + gen-5 completa (`opus-5`, `opus-5-fast`, `fable-5`, `sonnet-5` c/ dated intro→sticker) | HISTÓRICO-INTENCIONAL | — | **Curados** (PLAN-163 T1.5a + 168 W2 P2a/P2b); NUNCA remover linhas de replay (ADR-142) |
| OK2 | `.claude/scripts/validate-governance.sh:710-726` | working set c/ fable-5/opus-5/sonnet-5 ✓ + legados | INTENCIONAL | — | Espelho independente DELIBERADO do ADR-149 com oracle de paridade (`test_adr149_validator_parity.py`) — conforme doutrina; não é recitação sem vigia |
| OK3 | `scripts/local/historical/*`, `docs/benchmarks/*.jsonl`, `*/tests/*`, fixtures | ids antigos | HISTÓRICO/FIXTURE | — | Cobertos pelas `inert_path_rules` do ledger; não tocar |

## Foco F1 — a resposta à pergunta do Owner

`set-quality-profile.sh` reescreve `model:` frontmatter dos 5 canônicos via awk e grava `ceo_quality_profile` em settings. **Consumidor:** o frontmatter que ele grava é o que o Claude Code substitui no spawn e o que `check_agent_spawn.py` valida. O perigo: `VETO_FLOOR_ALLOWED` (`agent_frontmatter.py:136-139`) aceita `claude-opus-4-8` por tolerância N-1 intencional — logo **qualquer invocação do script (até `max-quality`) reverte os VETO holders de `fable-5` → `opus-4-8` SEM nenhum hook bloquear**. É downgrade silencioso de 2 gerações do ceiling preferido, legal perante o floor mecânico, invisível até a retrospectiva. `max-speed` ainda joga qa/perf/devops em Haiku — proibido pela própria doutrina sem tournament (§Q5). Bônus: o header do script diz "balanced → 2 Opus + 2 Sonnet + 1 Haiku" mas o código dá 2 Opus + 3 Sonnet (linha 52) — nem o display interno bate.

## Por que `check-model-deprecations.py` não pegou

O instrumento responde **"este id vai quebrar na API?"** — não **"este id é a frota corrente?"**. É ledger-driven (`model-deprecations.json`) e o ledger só contém ids **deprecados/retirados**; `opus-4-8`, `sonnet-4-6` e `haiku-4-5` são ATIVOS e por construção nunca entram. As três variantes da classe escapam: (a) pin de geração antiga-mas-ativa em routing = invisível; (b) texto de display desatualizado = não é model-id deprecado; (c) tabela de pricing com FUROS (id corrente ausente) = ausência não é match de regex. Ironia: os `replacement` do próprio ledger apontam para 4-8/4-6 (F9).

**Extensão que fecha a CLASSE** (closed-sets-must-be-derived): o repo JÁ tem a autoridade — o working set ADR-149 — e JÁ tem o padrão de vigia — espelho independente + oracle de paridade (`test_adr149_validator_parity.py`, único consumidor hoje é validate-governance.sh). A cura é generalizar: (1) um manifesto de superfícies funcionais portadoras de conjuntos de model-id (profiles map F1, `_tier_rank` F2, pricing keys F3/F7, enum `MODEL_ID` F5, tier-policy template F6, defaults F4) com um oracle por superfície no estilo ADR-149-parity; (2) uma dimensão nova (ou extensão da v) no nightly-hygiene: "fleet-currency" — para cada superfície do manifesto, asserta cobertura da frota corrente e ausência de decisão baseada em id fora do working set. Isso pega tanto o pin antigo quanto o furo de pricing, que o checker de deprecação estruturalmente não pode pegar.

## Veredito

- **Bug funcional REAL: 7** (3×P1: F1 downgrade-por-perfil, F2 direção invertida no learning loop, F3 custo da frota corrente invisível; 4×P2: F4-F7) + 3×P3 latentes/advisory (F8-F10).
- **Cosmético enganoso:** ~7 nomeados (D1-D6) + ~40 docs (D7), incluindo o SKILL.md do próprio archetype (D5, o mais grave dos displays).
- **Intencional (não re-flagar):** linhas de replay de pricing (ADR-142), working set N-1 do validate-governance (espelho vigiado), ledger, históricos, fixtures.
- A inversão "VETO abaixo da sessão" **não está ativa hoje** (agent files em fable-5), mas F1 a reativa com um comando e nenhuma defesa dispara.

## Encaixe no PLAN-169 — item ÚNICO de classe

Um item **"Fleet-currency: derivar todo conjunto funcional de model-ids da autoridade ADR-149"**, partido em dois pedaços nos slots existentes:

- **W2 (superfícies livres)** — os fixes mecânicos de DADOS, todos fora de caminho canônico-sensível ou já cobertos por teste: F2, F3, F4, F8, F9, F10, D1-D3, D6 + sweep D7. São edits de literal com espelho-teste; nenhum muda política.
- **W4.3 (tier policy)** — a parte que é DECISÃO: alvo dos perfis na geração 5 (F1 — `max-quality` vira fable-5 ou opus-5? exige rev do QUALITY-PROFILES + possivelmente ADR-amend), extensão do enum `MODEL_ID` + loader (F5, toca contrato do tier-policy artifact), baseline do template (F6) e a dimensão fleet-currency no nightly. D4/D5 (team.md + SKILL.md) entram aqui por serem Gate-1/2 cache-stable — edição só em closeout, junto do pack.

Anti-padrão a evitar (lição-mãe S296): NÃO patchear F1…F10 um a um como achados independentes — é produto cartesiano superfície×geração e vai regredir no próximo bump. O deliverable do item é a autoridade única + oracles; os 10 fixes caem como consequência.