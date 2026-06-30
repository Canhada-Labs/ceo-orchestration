# Roadmap de Fechamento — ceo-orchestration

> **SUPERSEDED 2026-06-20.** Os marcos de "fechamento" deste roadmap não
> refletem mais o estado do framework. **Marco 1** (Internal SOTA GA via
> Sprints 12-16) foi **aposentado** pela mudança de doutrina do ADR-096
> (`vibecoder-only by design`): o framework entrou em **modo de
> manutenção reativa** e não persegue mais a esteira de sprints descrita
> abaixo. O veredito de prontidão corrente vive em
> `docs/READINESS-STATUS.md` (`MAINTENANCE-MODE-VIBECODER`), não nos
> critérios de fechamento deste arquivo.
>
> Este "fechamento" também **não está fechado**: a dívida de higiene
> remanescente é carregada por **PLAN-143**, não pelos Sprints 12-17
> daqui. Trate o corpo abaixo como contexto histórico (a taxonomia de
> gaps A-E continua útil); os marcos, tags e critérios de saída estão
> **obsoletos**.
>
> Documento escrito em 2026-04-14 após Sprint 11 (PLAN-011) shippar.
> **Estratégia: internal-first.** Repo fica privado até SOTA técnico
> + validação em adopter-1 + adopter-2. Public launch é Sprint 17
> condicional, não milestone automático.

## Definição de "closure"

Este roadmap tem **dois marcos distintos**:

### Marco 1 — Internal SOTA GA (v1.5.0 privado)
Framework considerado **tecnicamente fechado e internamente validado**
quando:

1. Critérios técnicos verificáveis ✅ (multi-LLM live, MCP server,
   policy-as-code, threat model, flips validados)
2. Release chain **v1.0.0 → v1.5.0 tagged** internamente
3. Instalado e validado em **adopter-1** (produção)
4. Instalado e validado em **adopter-2** (produção)
5. Pelo menos 30 dias de uso real em cada adopter interno

**Este é o target real do roadmap.** Repo continua privado.

### Marco 2 — Public launch (Sprint 17, condicional)
Só acontece se Marco 1 fechar sem incidentes e se **Owner aprovar
explicitamente**. Não é milestone automático; é decisão separada.

### "Estado da arte 10/10" significa
- Cobrir 100% das capacidades de orquestração que Claude Code 2026-Q2
  expõe, **com** governance formal que o Claude Code sozinho não tem
- Interop com ecossistema (MCP server próprio, NPM install path,
  multi-IDE via adapter real não-stub)
- Segurança + compliance mapeados a controles externos (SOC2, threat
  model STRIDE, output safety em enforce mode)
- Documentação bilíngue EN+PT (EN pra adopters técnicos mesmo em uso
  interno; português pra Owner)
- Community surface pronto MAS não ativado (CONTRIBUTING, CoC, issue
  templates ficam no repo, discussions só ativam no launch)

---

## Diagnóstico atual (post Sprint 11)

### O que temos (inegavelmente SOTA em rigor)
- 52 skills · 5 squads · 12 hooks Python · 13 commands · 38 ADRs · 16 SPEC/v1 schemas
- 1.529 testes · coverage gate ≥86%
- CEO protocol · Plan→Debate→Execute · N-round debate com Red Team contingent
- Multi-LLM canonical envelope (Claude default · Gemini/OpenAI/local fixtures)
- Retrieval tf-idf · LLM-as-judge com κ calibration · skill self-improvement com 10 mitigações
- Budget advisory · scratchpad · OTEL export · output safety · chaos · session graph · squad marketplace
- Global kill-switch `CEO_SOTA_DISABLE=1`
- MIT license

### Os 4 tipos de gap que impedem closure

**Gap A — Validação interna (o framework nunca foi usado fora daqui):**
- Dogfood está limitado a evolução do próprio ceo-orchestration.
- Nenhum projeto externo do Owner (adopter-1, adopter-2) usa
  ainda.
- Metodologia de migração de projeto existente (seção 6 do
  `docs/GUIA-COMPLETO.md`) escrita mas **não testada em projeto real**.
- Zero evidência que o framework não quebra em stack diferente
  (TypeScript, Node, diferentes layouts de `.claude/`).

**Gap B — Flips pendentes (PLAN-012 stub):**
- 10 flip criteria em advisory → enforcing/blocking. Janelas de
  medição não fecharam. Framework ainda opera majoritariamente em
  State 0.
- Live wiring de adapters (Gemini/OpenAI/local) — temos fixtures,
  falta a chamada real de rede.
- Team.md Red Team row bloqueada por sentinel (PHASE5-BLOCKED.md).
- `docs/provider-pricing.md` 8/9 linhas TBD.
- `benchmarks/human-sample-calibration.md` κ TBD.
- Shadow-CI wiring de skill patches stub-only.

**Gap C — Features que faltam pra 10/10 em orquestração:**
- **MCP server próprio** — hoje somos consumidor de MCP. Pra ser
  SOTA precisa expor ceo-orchestration como MCP server (Cursor,
  outros clients usam).
- **Policy-as-code framework** — hooks são Python hardcoded.
  Terceiros estendem via fork. Falta engine declarativa (OPA-style).
- **Deterministic replay** — session graph shippou, replay real
  (re-run spawns em ordem exata com mesmo contexto) não existe.
- **A/B testing de skills** — skill patches têm shadow mode, mas
  comparação A/B de performance em benchmark não é automática.
- **Predictive budgeting** — budget advisory mede consumo, não
  prediz plan estimate pre-execução.
- **Long-horizon planning** — plans são single-sprint. Falta epic
  tracking multi-sprint com dependency graph.
- **Cross-plan memory** — scratchpad é plan-scoped. Falta knowledge
  layer que transcende planos (ex: convenções do time).
- **Red-team continuous evaluation** — chaos testa infra. Falta
  adversarial testing contínuo contra prompt injection real.

**Gap D — Compliance / enterprise readiness:**
- Threat model STRIDE não documentado.
- SOC2 audit trail mapping não existe (audit-log.jsonl tem dados
  pra isso, falta o mapping formal).
- GDPR/LGPD self-assessment report não escrito.
- Formal verification dos state machines (plan lifecycle, debate
  convergence) — hoje testado, não provado.
- Bus factor + SLA/SLO documents.

**Gap E — Distribuição (adiada até pós-validação interna):**
- Sem NPM install path.
- Docs só em PT-BR (EN mirror quebrado em `docs/translations/`).
- Sem landing page.
- Sem screencast/demo.
- Sem benchmark comparativo público.

---

## Plano: Sprints 12-16 (~3 meses pra Internal SOTA GA)

### Sprint 12 — Flip Validations + Technical Closure (PLAN-012) ✅ DONE

**Duração executada:** ~2h wall clock (single session, 9 agent spawns + CEO inline)
**Status:** `reviewed` → **EXECUTED** 2026-04-14. Tag `v1.4.0-rc.1` pendente Owner.
**Output:** +213 non-gated tests (1529→1742) + 3 ADRs + 1 SPEC + 2 workflows + 3 scripts + 2 libraries. Zero regressões.
**Detalhes:** ver CLAUDE.md Session 18 CHANGELOG + `.claude/plans/PLAN-012-sprint-12-stub.md` (reviewed body).

**Itens ativáveis agora (não dependem de window):**
- [D1] `docs/provider-pricing.md` — popular 8/9 linhas com Anthropic/Google/OpenAI 2026-Q2 snapshot
- [D2] `benchmarks/human-sample-calibration.md` — coletar N=50 paired human grades vs LLM judge
- [D3] Live wiring Gemini/OpenAI/local adapters (atualmente fixtures only)
- [D4] Shadow-CI workflow wiring pra skill patches
- [D5] Team.md Red Team row via Owner-signed sentinel
- [D6] Scoped-conditional-veto tier + squad-overlap recursion guard + state-machines benchmark

**Itens com window aberta:**
- Output safety flag → redact (30d window)
- Budget State 0 → 1 (30d window)
- OTEL State 0 → 1 (2 semanas)
- Chaos State 0 → 1 (4 semanas)
- Perf-profile State 0 → 1 (3 semanas)
- Docs-freshness State 1 → 2 (2 semanas)
- Confidence gate default enforce (FPR <5% em 50+ spawns)
- Skill retrieval real embeddings default (quando wiring OpenAI)

**Critério de fechamento Sprint 12:**
- [ ] D1-D6 executados
- [ ] Pelo menos 5 de 10 flips concluídos
- [ ] Tests continuam verdes
- [ ] Amendments dos ADRs registrando transições

**Output esperado:** v1.4.0-rc.1 (tag **interna**, não publicada externamente)

---

### Sprint 13 — Technical Closure (NOVO PLAN-013)

**Duração:** 3 semanas
**Premissa:** Sprint 12 flipou ao menos 5 criteria + D3 live adapters
**Nota:** Sprint 13 NÃO inclui "tornar repo público" (descopado até
Sprint 17 condicional).

**Fase 1 — Tradução EN completa (1 semana)**
Motivação: mesmo em uso interno, Owner pode ter devs ou adopters
secundários que preferem EN. CI drift check evita bitrot.
- [ ] `README.en.md` (paridade com README.md PT-BR)
- [ ] `docs/QUICKSTART.pt-BR.md`
- [ ] `docs/GUIA-COMPLETO.pt-BR.md`
- [ ] `docs/FOR-EMPLOYEES.pt-BR.md`
- [ ] `docs/TROUBLESHOOTING.pt-BR.md`
- [ ] `docs/GLOSSARY.pt-BR.md`
- [ ] CI job `translations-drift.yml` expandido pra EN↔PT hash diff

**Fase 2 — NPM install path (3 dias)**
Motivação: facilitar install em adopter-1 e adopter-2 na Sprint 15.
- [ ] `scripts/install-npm.sh` empacotando git-clone num `package.json`
  fino `@ceo-orch/init` (NOT published yet — only shipped as internal
  tarball)
- [ ] Testar `npx @ceo-orch/init` em projeto vazio local
- [ ] SPEC/v1/npm-shim.md validar que está current
- [ ] NPM publish workflow **permanece disabled** — só ativa no
  Sprint 17 se Owner aprovar público

**Fase 3 — Community surface (PRONTO, não ativado) (3 dias)**
Motivação: arquivos existem no repo pra quando virar público, mas
discussions/issues ficam fechados até lá.
- [ ] `CONTRIBUTING.md`
- [ ] `.github/ISSUE_TEMPLATE/` (bug, feature, skill proposal)
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] `CODE_OF_CONDUCT.md` validado/expandido (já existe stub)
- [ ] GitHub Discussions **permanecem disabled**
- [ ] Landing page draft em `docs/site/` (HTML pronto, não deployed)

**Fase 4 — MCP server (1 semana, CRITICAL)**
Motivação: adopter-1 e adopter-2 podem usar Cursor ou outros
clients; MCP expõe o framework via protocolo aberto.
- [ ] `packages/mcp-server/` com Python MCP server (stdlib only)
  expondo:
  - `list_skills` → inventory atual
  - `get_skill <name>` → conteúdo de SKILL.md
  - `list_agents` → roster de team.md
  - `spawn_agent <name> <task>` → spawn governed (via inject-agent-context.sh)
  - `get_audit_log <filter>` → query do audit-log.jsonl
  - `list_pitfalls <domain>` → pitfalls do squad
- [ ] SPEC/v1/mcp-server.schema.md
- [ ] ADR-040 MCP server contract
- [ ] Instalação documentada (Cursor `mcp_settings.json` example)
- [ ] Tests: +30 pra MCP handlers

**Fase 5 — Internal release v1.4.0 (1 dia)**
- [ ] Tag interno `v1.4.0-rc.1` → 7-day hold → `v1.4.0`
- [ ] Branch protection enabled (permanece útil em repo privado)
- [ ] CHANGELOG entry
- [ ] Repo **permanece privado**

**Critério de fechamento Sprint 13:**
- [ ] Docs EN + PT em paridade (CI drift check verde)
- [ ] MCP server funcional local (tested com Cursor local)
- [ ] NPM tarball buildable (sem publish)
- [ ] Community files existem mas discussions/issues permanecem closed
- [ ] `v1.4.0` tagged internamente

**Output esperado:** v1.4.0 (internal)

---

### Sprint 14 — Security + Compliance Hardening (NOVO PLAN-014)

**Duração:** 2 semanas
**Premissa:** Sprint 13 fechou com v1.4.0 interno

**Fase 1 — Threat Model STRIDE (4 dias)**
- [ ] `docs/threat-model.md` — STRIDE analysis cobrindo:
  - Spoofing: plan-id spoof, agent spawn spoof, squad signature
  - Tampering: canonical edit, audit log append-only, state store
  - Repudiation: audit trail completeness
  - Info disclosure: output safety, redact_secrets, OTEL
  - DoS: chaos testing, hook fail-open, budget kill-switch
  - Elevation: sentinel bypass, skill patch privilege
- [ ] Cross-reference com ADRs existentes
- [ ] Gaps identificados viram action items

**Fase 2 — SOC2 audit trail mapping (3 dias)**
- [ ] `docs/soc2-audit-mapping.md` — mapear audit events a controles
  CC6.1 / CC6.6 / CC7.1 / CC7.2 / CC8.1
- [ ] SPEC/v1/soc2-control-map.schema.md
- [ ] ADR-041 SOC2 audit contract

**Fase 3 — Policy-as-code framework (1 semana)**
- [ ] `_lib/policy.py` — engine declarativa stdlib-only
- [ ] `.claude/policies/` — políticas em YAML
- [ ] Migrar 2-3 hooks pra usar policy engine
- [ ] SPEC/v1/policy-dsl.schema.md
- [ ] ADR-042 policy-as-code

**Fase 4 — Formal verification pilot (3 dias)**
- [ ] Escolher 1 state machine (plan lifecycle ou debate convergence)
- [ ] Modelar em TLA+ ou Alloy
- [ ] `docs/formal-verification/plan-lifecycle.tla`
- [ ] Documentar propriedades provadas (liveness, safety)
- [ ] ADR-043 formal verification pilot

**Fase 5 — Red-team continuous evaluation (3 dias)**
- [ ] `.claude/scripts/red-team-eval.py`
- [ ] `red-team.yml` weekly workflow
- [ ] +20 tests

**Critério de fechamento Sprint 14:**
- [ ] Threat model + SOC2 mapping + policy-as-code + formal verification
  pilot + red-team eval shipados
- [ ] 3-4 novos ADRs
- [ ] Tests +50
- [ ] Zero veto do Staff Security

**Output esperado:** v1.4.1 internal

---

### Sprint 15 — Internal Validation em adopter-1 (NOVO PLAN-015)

**Duração:** 3 semanas (incluindo 2 semanas de observação)
**Premissa:** Sprint 14 hardening fechou
**Este sprint é o mais importante do roadmap — é o que valida
product-market fit antes de qualquer consideração de público.**

**Fase 1 — Install em adopter-1 (2 dias)**
- [ ] Seguir `docs/GUIA-COMPLETO.md` §6 (projeto existente) em
  adopter-1 com Owner presente
- [ ] Documentar cada fricção em tempo real em
  `docs/case-studies/adopter-1-install.md`
- [ ] Resolver blockers mid-install (não pular passos)
- [ ] Se algum passo do guia estiver errado: fix it IN the guide
  antes de continuar

**Fase 2 — 2 semanas de uso real em adopter-1 (14 dias)**
- [ ] Owner usa framework pra TODO trabalho ledger-related
- [ ] Audit log coletado continuamente
- [ ] Toda fricção vira issue interna em `.claude/plans/PLAN-015/frictions.md`
- [ ] Reuniões de 30min bissemanais (2×/semana) pra triage friction
  e decidir: fix in framework vs workaround
- [ ] Métricas coletadas:
  - Quantas sessions usadas
  - Quantos spawns totais
  - % spawns bloqueados por hook (deve ser baixo se framework está good)
  - % tasks completadas vs abandonadas
  - Tokens gastos vs estimated
  - Quantas "skills custom" adopter-1 precisou criar
  - Quais ADRs foram ativados na prática

**Fase 3 — Análise + framework fixes (3 dias)**
- [ ] Consolidar friction log → categoria (bug / UX / missing feature /
  doc gap)
- [ ] P0 bugs fixed imediatamente
- [ ] P1 UX improvements → Sprint 16 ou deferred a PLAN-017
- [ ] Case study final escrito em
  `docs/case-studies/adopter-1-case-study.md` (mesmo interno)

**Critério de fechamento Sprint 15:**
- [ ] adopter-1 rodando framework em produção por ≥14 dias
- [ ] Friction log triageiado, P0/P1 resolvidos ou planejados
- [ ] Case study interno escrito
- [ ] Métricas quantitativas coletadas
- [ ] Decisão Owner: "framework está pronto pra adopter-2?" (Y/N
  decision point — se N, repete Sprint 15 depois dos fixes)

**Output esperado:** v1.4.2 internal + case study adopter-1

---

### Sprint 16 — Internal Validation em adopter-2 (NOVO PLAN-016)

**Duração:** 3 semanas
**Premissa:** Sprint 15 passou com Y decision
**Motivação:** validar que metodologia funciona em SEGUNDO projeto de
contexto diferente — não é one-off do adopter-1.

**Fase 1 — Install em adopter-2 (2 dias)**
- [ ] Mesmo processo Sprint 15 Fase 1
- [ ] Aplicar lessons aprendidas do install adopter-1
- [ ] Guia `docs/GUIA-COMPLETO.md` §6 deve funcionar sem fix desta
  vez (se precisar fix, é sinal de regressão)

**Fase 2 — 2 semanas de uso real em adopter-2 (14 dias)**
- [ ] Mesmo processo Sprint 15 Fase 2
- [ ] Comparar métricas com adopter-1: consistência sugere que
  framework generaliza

**Fase 3 — Análise cross-project (3 dias)**
- [ ] Consolidar friction logs adopter-1 + adopter-2
- [ ] Identificar padrões: friction que apareceu nos dois = gap real
  do framework; friction só em um = project-specific
- [ ] Fix patterns-comum
- [ ] Case study `docs/case-studies/adopter-2-case-study.md`
- [ ] Meta-case-study `docs/case-studies/internal-validation-summary.md`

**Fase 4 — Internal v1.5.0 GA tag (1 dia)**
- [ ] Tag interno `v1.5.0-rc.1` → 7-day hold → `v1.5.0`
- [ ] CHANGELOG entry completa
- [ ] CLAUDE.md Session 16 entry
- [ ] Repo **permanece privado**

**Critério de fechamento Sprint 16 (= Internal SOTA Closure):**
- [ ] adopter-2 rodando framework em produção por ≥14 dias
- [ ] Métricas consistentes com adopter-1
- [ ] Zero P0 open após cross-project analysis
- [ ] `v1.5.0` tagged internamente
- [ ] Owner decision point: "aprovar Sprint 17 public launch?" (Y/N)

**Output esperado:** v1.5.0 Internal GA

---

### Sprint 17 — Public Launch (CONDICIONAL, só se Owner aprovar)

**Duração:** 1-2 semanas
**Premissa CRITICAL:** Sprint 16 fechou + Owner explicitly approved
"let's go public"
**Esta Sprint não é automática. Sem Owner approval, repo permanece
privado indefinidamente.**

**Fase 1 — Go/no-go checklist**
Antes de público, validar:
- [ ] adopter-1 + adopter-2 produção estável 30+ dias
- [ ] Zero security incident em 30 dias
- [ ] Zero vazamento de credential/PII em audit logs
- [ ] Contamination check zero hits (handles pessoais, paths privados)
- [ ] Todos os 2 case studies aprovados pra publicação
- [ ] Benchmark comparativo vs concorrência reproduzível

**Fase 2 — Pre-launch polish (3 dias)**
- [ ] `benchmarks/public/vs-competitor.md` + `vs-claude-code-vanilla.md`
- [ ] Screencasts (3×):
  - "from install to first spawn" (10min)
  - "debate protocol em ação" (5min)
  - "audit log query + dashboard" (5min)
- [ ] Landing page `docs/site/` deployed em GitHub Pages
- [ ] HN submission template
- [ ] Blog post técnico draft

**Fase 3 — Repo vai público (1 dia)**
- [ ] Owner approval explícito final
- [ ] Contamination scan final
- [ ] `gh repo edit --visibility public`
- [ ] NPM publish `@ceo-orch/init`
- [ ] GitHub Discussions enable
- [ ] Issue templates live
- [ ] Blog post published
- [ ] HN submission

**Fase 4 — Launch week monitoring (1 semana)**
- [ ] Triage issues 2×/dia
- [ ] Hot-fix P0 em <4h
- [ ] Social media monitor

**Critério de fechamento Sprint 17 (= Public GA):**
- [ ] Repo público
- [ ] Primeira semana sem P0
- [ ] 50+ stars orgânicos em 30 dias OU decisão explicita que numbers
  não são métrica
- [ ] Case studies publicados

**Output esperado:** v1.5.0 Public GA

---

## Critério de sucesso total

### Internal SOTA GA (Marco 1 — target real)
- [ ] Release chain v1.0.0 → v1.5.0 tagged internamente
- [ ] Multi-LLM com live invocations em 3+ providers
- [ ] MCP server funcional (testado com Cursor local)
- [ ] Policy-as-code framework
- [ ] ≥5 de 10 flip criteria flipados
- [ ] Threat model STRIDE
- [ ] SOC2 audit trail mapping
- [ ] Formal verification pilot
- [ ] Red-team continuous eval rodando
- [ ] **adopter-1 produção ≥30 dias**
- [ ] **adopter-2 produção ≥30 dias**
- [ ] Case studies internos escritos
- [ ] Métricas cross-project consistentes

### Public Launch (Marco 2 — condicional, só se Owner aprovar)
- [ ] Benchmark comparativo público reproduzível
- [ ] 3 screencasts
- [ ] Landing page deployed
- [ ] NPM publicado
- [ ] GitHub Discussions live
- [ ] Blog post publicado
- [ ] HN submission

---

## Timeline consolidado

| Sprint | Plan | Duração | Deliverable | Tag | Repo |
|--------|------|---------|-------------|-----|------|
| 12 | PLAN-012 | 4-6 sem | Flip validations + D1-D6 | v1.4.0-rc.1 | privado |
| 13 | PLAN-013 | 3 sem | EN docs + MCP + NPM build + v1.4.0 | v1.4.0 | privado |
| 14 | PLAN-014 | 2 sem | Security + compliance hardening | v1.4.1 | privado |
| 15 | PLAN-015 | 3 sem | adopter-1 install + 14d real use + case study | v1.4.2 | privado |
| 16 | PLAN-016 | 3 sem | adopter-2 install + 14d real use + v1.5.0 | v1.5.0 | privado |
| 17 | PLAN-017 | 1-2 sem | **Condicional**: benchmarks públicos + launch | v1.5.0 public | público (se aprovar) |

**Total até Marco 1 (internal GA):** ~15-17 semanas (~4 meses)
**Total até Marco 2 (public GA):** +1-2 semanas (~4.5 meses, só se aprovar)

Sprints 12-13 podem ter overlap parcial — Sprint 13 tradução EN + MCP
não dependem de flips do Sprint 12. Sprint 15 e 16 **não podem ser
paralelizados** — precisam do framework estabilizado um-por-vez.

---

## Riscos + mitigações (atualizados)

### Risco 1: adopter-1 rejeita framework (usabilidade horrível)
- **Causa:** framework feito pra orquestrar CEO-of-ceo-orchestration
  não generaliza pra ledger financeiro
- **Mitigação:** Sprint 15 é explicitamente pra encontrar isso.
  Friction log + triage + fix. Melhor descobrir em adopter-1 do que em
  HN launch
- **Fallback:** repetir Sprint 15 após fixes. Roadmap atrasa, não
  morre. Public launch só acontece depois.

### Risco 2: adopter-2 expõe problemas adopter-1 não mostrou
- **Causa:** dois projetos com contextos diferentes revelam gaps
  distintos
- **Mitigação:** é exatamente pra isso que existe Sprint 16. Cross-
  project analysis filtra generalizável vs project-specific
- **Fallback:** Sprint 16.5 adicional se friction cross-project grande

### Risco 3: Flip windows não fecham no tempo previsto
- **Causa:** volume de uso baixo no repo privado + 2 adopters
- **Mitigação:** Sprint 15/16 aumentam volume dramaticamente
  (adopter-1 + adopter-2 = 2 novas sources de events). Flips não
  medidos no ceo-orchestration podem ser medidos via adopters
- **Fallback:** alguns flips ficam pro Sprint 17+ sem bloquear GA

### Risco 4: Concorrência copia
- **Causa:** um framework concorrente pode reagir
- **Mitigação:** nossa vantagem é core (rigor + ADRs + schemas), não
  surface. Mesmo em privado, quando formos público teremos case
  studies reais de adopters internos; o concorrente não tem isso
- **Fallback:** nicho fintech/healthcare/government regulado é
  defensável por governance

### Risco 5: Claude Code muda API e quebra hooks
- **Mitigação:** Adapter Layer (ADR-008) isola. Adopters internos
  notam primeiro
- **Fallback:** pin versão suportada

### Risco 6: Owner decide nunca abrir público
- **Causa:** pode descobrir via uso interno que o diferencial compete
  contra outros produtos do portfolio Owner e prefere manter private
- **Mitigação:** não é risco de fato — é opção válida. Marco 1 é o
  target real. Marco 2 é bônus condicional.
- **Fallback:** framework permanece private indefinidamente, serve
  Owner + team interno. Zero problema.

---

## O que NÃO fazer (anti-goals)

1. **Não abrir repo público antes de Sprint 17 + Owner approval
   explícito.** (Principal anti-goal do roadmap.)
2. **Não prometer data de public launch.** Continuar "criterion +
   window + fallback".
3. **Não adicionar mais squads.** 5 é defensável.
4. **Não adicionar mais skills.** 48 já é suficiente; refine as
   existentes com feedback de adopter-1/adopter-2.
5. **Não reescrever hooks em TypeScript/Go/Rust.** Stdlib Python é
   vantagem.
6. **Não criar Pro tier comercial.** Mantém MIT + free.
7. **Não adicionar web UI.** CLI + file-based é a promessa.
8. **Não aceitar PRs externos.** Repo é privado, então não aplicável —
   mas mesmo no Sprint 17+ wait 30 dias pra abrir PRs externos.
9. **Não publicar NPM antes de Sprint 17.** Build local é suficiente
   pra install em adopter-1/adopter-2 via tarball ou git.
10. **Não ativar GitHub Discussions antes de Sprint 17.**

---

## Cronograma sugerido (Owner planning)

| Quando | O que | Owner action |
|--------|-------|--------------|
| Semana 1-6 | Sprint 12 | Aprovar PLAN-012 promoção draft→reviewed |
| Semana 5-9 | Sprint 13 (overlap ok) | Aprovar PLAN-013 draft |
| Semana 9-11 | Sprint 14 | Aprovar PLAN-014 |
| Semana 11-14 | Sprint 15 (adopter-1) | **Decision point 1**: framework pronto pra adopter-2? |
| Semana 14-17 | Sprint 16 (adopter-2) | **Decision point 2**: internal GA aprovada? |
| Semana 17+ | Sprint 17 (condicional) | **Decision point 3**: go public? |

**Decisão crítica #1 (semana 14):** adopter-1 validou ou repete?
**Decisão crítica #2 (semana 17):** Tag v1.5.0 internal GA?
**Decisão crítica #3 (semana 17+):** Tornar repo público?

Decision points 1 e 2 são binários Y/N. Decision point 3 é Y/N/defer
(defer = "não ainda, mas não não para sempre").

---

## O que significa "fechado" (explicitamente)

### Após Marco 1 (Internal SOTA GA)
- Framework entra em modo maintenance + adoption support
- adopter-1 e adopter-2 são "customers internos" formalizados
- Sprints emergenciais só via PLAN-NNN — bug crítico, CVE, regressão
- Feature requests dos dois adopters internos viram backlog priorizado
- Owner decide quando expandir pra 3º adopter interno ou ir pra
  Marco 2

### Após Marco 2 (Public GA, se acontecer)
- Framework ganha community surface ativa
- Comunidade pode contribuir via PR
- Feature requests viram issues públicos
- Owner + CEO mantêm veto final em direction

**"Fechado" não significa morto — significa estável, documentado, e
defensável em produção real. Sem Marco 2, ainda é fechado — apenas
para audiência menor.**

---

## Referências
- `docs/ROADMAP.md` — roadmap histórico geral
- `.claude/plans/PLAN-012-sprint-12-stub.md` — Sprint 12 stub
- `docs/v2-break-inventory.md` — features reservadas pra v2.0
- `docs/GUIA-COMPLETO.md` — guia de uso do framework (inclui §6
  projeto existente que Sprint 15/16 vão validar em produção)
- `PROTOCOL.md` — contrato de governance
- Memória: `project_closure_strategy.md` (Owner decision 2026-04-14:
  internal-first, no público até adopter-1 + adopter-2 validados)
