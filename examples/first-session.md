# Exemplo: Primeira Sessão com CEO Orchestration

> Tutorial narrativo de uma sessão real de trabalho. Mostra o fluxo
> completo: ativar o protocolo → pedir uma feature → CEO planeja →
> debate → execução → merge. Tempo estimado: 30 min.

## Cenário

Você é Owner de um projeto Node.js de e-commerce chamado `shop-api`.
Seu time (imaginário): 2 devs juniores e você. Acabou de instalar o
ceo-orchestration e quer validar que funciona de verdade antes de
apresentar pros devs.

**Tarefa de teste:** adicionar rate limiting no endpoint público
`POST /api/v1/orders` para evitar abuso.

---

## Setup

```bash
cd ~/projects/shop-api
bash ~/ceo-orchestration/scripts/install.sh
```

Output esperado:
```
✓ Copied .claude/skills/core/... (19 skills)
✓ Copied .claude/skills/frontend/... (8 skills)
✓ Installed .claude/hooks/ (53 hooks, Python)
✓ Installed .claude/team.md template
✓ Installed .claude/frontend-team.md template
✓ Installed CLAUDE.md + PROTOCOL.md at repo root
Done. Next: edit CLAUDE.md to replace {{PROJECT_NAME}} + {{OWNER_NAME}}.
```

Edita `CLAUDE.md`:
```
{{PROJECT_NAME}} → shop-api
{{OWNER_NAME}} → the Owner
```

## Abrindo Claude Code

```bash
claude
```

## Sua primeira mensagem

```
Ativa o protocolo CEO.
```

### Resposta esperada do CEO

```
## Protocolo CEO — ATIVADO ✅

Gate 1 Reading: CLAUDE.md ✅ PROTOCOL.md ✅ MEMORY.md ✅
Gate 2 Ativação: skill ceo-orchestration ✅ team.md ✅
Gate 3 Plan: aguardando diretiva

Estou como CEO de shop-api reportando a você, the Owner.

Roster carregado: 12 archetypes backend + 8 frontend. 2 VETOs ativos:
Staff Code Reviewer (merge) e Staff Security Engineer (auth/input).

Qual a diretiva?
```

## Segunda mensagem: pedir a feature

```
Preciso adicionar rate limit de 100 req/min no POST /api/v1/orders.
Faz um plano.
```

### Resposta esperada do CEO

```
Entendi. Rate limit em endpoint público é L2-L3 (toca auth middleware
+ potencialmente schema de storage pro counter). Vou planejar
brevemente antes de debater.

## Proposta de plano

**Blast radius:** L2 — modifica auth middleware + 1 rota + adiciona
lib rate-limit. Sem migration.

**Fases:**
- Phase 0 (Product): qual comportamento quando excede? 429 + Retry-After?
  Ou silent throttle? → Preciso sua decisão aqui.
- Phase 1 (Implementation): Staff Backend Engineer com skill
  `public-api-design` implementa usando `express-rate-limit` ou
  `@fastify/rate-limit` (depende do stack).
- Phase 2 (Quality): Staff Code Reviewer checa tests + naming.
  Staff Security Engineer checa se o rate limit escapa por header
  spoofing (X-Forwarded-For).
- Phase 3 (Deploy): smoke-test com k6 ou autocannon; 100 req burst
  → ver 429 na 101ª.

**Escala 10x:** 100 req/min × 10 = 1000 req/min. Memory-store dá
conta. Se cresce pra 100 mil req/min, precisa Redis — mas esse é
problema de outro sprint.

**Debate?** L2 não obriga, mas Security tem veto — quer que eu
rode `/debate start` mesmo assim, ou vou direto pra Phase 0 perguntar
do 429?
```

## Sua resposta

```
Pode pular debate, L2 pequeno. 429 com Retry-After, padrão. Parte pra
implementação.
```

## CEO executa

```
OK. Pulando Phase 0 (decisão Owner explícita: 429 + Retry-After).

Spawnando Staff Backend Engineer...
```

Internamente acontece:
1. CEO monta prompt com:
   - `## AGENT PROFILE` (persona do Staff Backend)
   - `## SKILL CONTENT` (SKILL.md de `public-api-design`)
   - `## FILE ASSIGNMENT` (src/routes/orders.ts, src/middleware/rate-limit.ts)
   - `## TASK` (implementar rate limit 100/min com 429 + Retry-After)
2. Invoca Agent tool com `subagent_type=general-purpose`
3. Hook `check_agent_spawn.py` valida (existe `## SKILL CONTENT`? ✓ existe `## AGENT PROFILE`? ✓)
4. Hook `audit_log.py` registra no PostToolUse

Se o hook bloqueasse (spawn sem skill), você veria:
```
[check_agent_spawn] BLOCKED: spawn missing ## SKILL CONTENT section
```

## Subagent retorna

```
## Done

Edited files:
- src/middleware/rate-limit.ts (new, 45 LOC)
- src/routes/orders.ts (+3 LOC apply middleware)
- src/middleware/__tests__/rate-limit.test.ts (new, 5 tests)

Rate limit: 100 req/min per IP; window rolling (not fixed bucket);
429 + Retry-After header; store = MemoryStore (single-instance only).

Ran tests: 5/5 passing.
Ran type check: tsc --noEmit clean.

Note: MemoryStore won't work across instances. If this app scales
horizontally, switch to Redis-backed store (documented in TODO at
rate-limit.ts:12).
```

## CEO valida

```
Verificando output:
  ✓ Files listed exist (grep rate-limit.ts in src/middleware: found)
  ✓ Tests pass (ran npm test, 5/5)
  ✓ Type check clean (ran tsc --noEmit)
  ✓ Agent respected file assignment
  ✓ Uses skill terms ("window rolling", "Retry-After", "per IP")

Qualidade: OK.

Próximo: Staff Code Reviewer e Staff Security Engineer para Phase 2.
Posso rodar em paralelo (files não conflitam: Reviewer só lê, Security
só lê).

Autoriza?
```

## Você autoriza

```
Autoriza.
```

## Two agents em paralelo

```
Spawnando:
- Staff Code Reviewer (skill: code-review-checklist)
- Staff Security Engineer (skill: security-and-auth)

Waiting for both...
```

2 minutos depois:

```
Staff Code Reviewer: APPROVED.
  - Naming consistent with existing middleware patterns
  - Tests cover happy path + 2 edge cases (exact-at-limit, reset)
  - No :any types, no @ts-ignore added
  - Missing: JSDoc on the middleware factory. Minor, advisory-only.

Staff Security Engineer: APPROVED WITH WARNING.
  - Rate limit uses IP from req.ip (good — respects Express trust-proxy)
  - ⚠ WARNING: if app is behind proxy/CDN and trust-proxy não está
    configurado em app.ts, req.ip retorna IP do proxy (não do client).
    Todos os requests viriam do mesmo IP e o rate limit ficaria inútil.
  - RECOMMEND: verificar app.set('trust proxy', true) existe em app.ts.
    Se não, adicionar antes de merge.

Não bloqueia merge mas flag pra você decidir.
```

## Você decide

```
Checa se trust proxy tá configurado. Se não, adiciona.
```

## CEO resolve

```
Checando src/app.ts:2: 'app.set("trust proxy", 1)' já existe.
Warning resolved. Pode merge.

Status final:
- 3 files modified (middleware + route + test)
- 5 novos tests
- Tipo check clean
- 2 agentes aprovaram
- 1 warning investigado e resolvido

Posso commit + push OU você prefere revisar o diff antes?
```

## Você revisa

```
Mostra diff primeiro.
```

CEO mostra o diff unificado. Você aprova.

```
OK, commit e push.
```

## CEO commita

```
Seguindo política: commit só quando Owner pede explicitamente ✓

git add src/middleware/rate-limit.ts src/routes/orders.ts src/middleware/__tests__/rate-limit.test.ts
git commit -m "feat(orders): rate limit 100 req/min on POST /api/v1/orders"
git push origin main

Pushed. CI rodando: https://github.com/.../actions/runs/...
```

## Consultando o audit

```bash
python3 .claude/scripts/audit-query.py summary
```

Output:
```
action_counts: {agent_spawn: 3, veto_triggered: 0, plan_transition: 0}
top_skills: [public-api-design, code-review-checklist, security-and-auth]
hook_duration_ms: median 34, p95 38
```

Você vê: 3 spawns, zero bloqueios, nenhum veto acionado. Tudo limpo.

## /status

```
/status
```

Output:
```
## /status — 2026-04-13 19:25 UTC (janela 24h)

Plan: — (sem plan em execução — rate limit foi task L2 sem plan formal)
Health: PASS
CI: ✅ success — feat(orders): rate limit...

### Últimas 3 spawns
- 19:12  Staff Backend Engineer    skill=public-api-design
- 19:18  Staff Code Reviewer       skill=code-review-checklist
- 19:18  Staff Security Engineer   skill=security-and-auth

### Tokens: 42,180 in + 18,920 out = 61,100
  - public-api-design: 28k
  - security-and-auth: 18k
  - code-review-checklist: 15k

### Warnings: ✓ 0 vetos  ✓ 0 injection flags  ✓ 0 breadcrumbs
```

## O que você aprendeu

1. **CEO não age sem plano.** Ele pediu clarificação (429?) antes de
   executar.
2. **Especialistas têm papel real.** Cada um usa vocabulário e
   checklist da skill dele.
3. **Hooks protegem silenciosamente.** Se o CEO tivesse spawnado sem
   skill, o hook teria bloqueado.
4. **Audit trail é automático.** Você vê tudo que aconteceu em 1
   comando.
5. **Warnings não bloqueiam.** O Staff Security não impediu merge,
   só te informou. Você decidiu investigar.
6. **Commit só quando pedido.** Nunca CEO commita sozinho.

## Próximos passos depois desse tutorial

- Leia `docs/FOR-EMPLOYEES.md` — para entender quando usar `/debate`
  vs spawn direto
- Leia `PROTOCOL.md` — seção "Plan → Debate → Execute"
- Instale em 1 projeto real pequeno e repita esse exercício
- Quando sentir confiança, apresente pros devs juniores

## Se quer testar os gates mecânicos

Tente:

```
Apaga o arquivo .claude/team.md
```

CEO vai recusar (hook `check_canonical_edit` bloqueia).

```
rm -rf ~/Downloads/temp
```

Hook `check_bash_safety` bloqueia com razão.

```
Spawn um agente chamado "VP Engineering" sem carregar skill
```

Hook `check_agent_spawn` bloqueia com razão "missing SKILL CONTENT".

Esses 3 experimentos provam que os gates funcionam — não é só papel.
