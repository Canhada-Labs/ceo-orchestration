# ADR-186 (DRAFT — decisão do OWNER) — Política de deadline de hook: o timeout interno de um matcher de segurança é falha de INFRAESTRUTURA ou sinal de VERIFICAÇÃO INCOMPLETA?

<!-- Ceremony copy target (se aceito): .claude/adr/ADR-186-hook-deadline-policy.md -->
<!-- ⚠ Este arquivo NÃO tem status decidido. O Owner escolhe (i) ou (ii)      -->
<!--    no §4, preenche o status, e SÓ ENTÃO ele entra na cerimônia.          -->

---
adr_id: ADR-186
title: Política de deadline de hook — fail-closed (verificação incompleta) vs fail-open (falha de infraestrutura)
status: PROPOSED
proposed_at: 2026-08-04
proposed_by: CEO (S292 — conflito levantado pelo consensus C2 do PLAN-162 e confirmado de forma independente pelo pair-rail em DOIS rounds)
risk_tier: A
debate_required: true
supersedes_clause_in: [CLAUDE.md §4, AGENTS.md §1]
related_plans: [PLAN-162]
related_adrs: [ADR-164, ADR-164-AMEND-1]
---

## §1 O conflito, sem eufemismo

O `plan162-w2-fixes.patch` introduz um **wall-deadline fail-CLOSED** em
`check_canonical_edit.py`: se a verificação (GPG + parse de sentinels) não
termina dentro de `_HOOK_WALL_BUDGET_S` (4 s, sob a registração de 5 s), o
hook **bloqueia** o edit com `canonical_edit_hook_fault`.

Isso é o que o debate do PLAN-162 decidiu (consensus **C2**, com F-01-07).

E contradiz o contrato **publicado** do repo:

> `CLAUDE.md` §4 / `AGENTS.md` §1 — *"hooks never block the user session on
> INFRASTRUCTURE bugs — on a missing file, import failure, or **timeout**, a
> hook logs a breadcrumb and emits `{}` (a schema-compliant allow). But an
> INPUT-parse failure inside a security matcher is fail-CLOSED by design."*

O pair-rail apontou a contradição **duas vezes, de forma independente**
(S292 rounds 3 e 5), sem conhecer o histórico. A S291 já a havia registrado
como não resolvida — e o teste correspondente está **SKIPADO de propósito**
(não `xfail`: um xfail ficaria verde sob as DUAS implementações e esconderia
a indecisão).

**A pergunta real, e é doutrinária, não técnica:** um timeout do próprio
matcher é "a infra quebrou" (⇒ allow, como qualquer import faltando) ou "a
verificação não terminou" (⇒ block, como um input que não parseia)?

## §2 As duas leituras — ambas defensáveis

### (i) Fail-CLOSED — timeout é verificação incompleta

- Um gate que **não conseguiu decidir** não tem base para liberar um edit
  canônico. Diferente de um import faltando (o hook não roda, e o CI +
  CODEOWNERS continuam a jusante), aqui o hook RODOU e não concluiu — o
  edit está exatamente no caminho que ele existe para julgar.
- Sob o `_PLAN160_MAX_CANDIDATES=512`, o custo é **atacável**: a medição do
  ADR-164-AMEND-1 mostra 4,16 s de um budget de 5 s com 20 alvos. Fail-open
  aqui é uma porta que o atacante consegue abrir por saturação.
- Custo honesto: um `gpg-agent` travado vira **bloqueio do Owner**. Exige
  rota de recuperação documentada (o unlock, cujo contrato mudou no mesmo
  patch) — sem ela, um gate fail-closed sem saída é travamento.

### (ii) Fail-OPEN + breadcrumb — timeout é infraestrutura

- É o que o contrato escrito diz, e a coerência entre hooks tem valor:
  hoje **todos** os outros fail-open em timeout. Uma exceção não
  documentada em ADR é justamente a "governance drift" que o repo combate.
- O breadcrumb + o evento de auditoria preservam a forense; a decisão passa
  ao CI e ao CODEOWNERS.
- Custo honesto: reabre a janela que o C2 quis fechar, e a janela é
  **explorável por saturação** (§2.i), não apenas azar.

## §3 O que NÃO é opção

- **Deixar como está.** O patch implementa (i) enquanto os documentos
  publicados afirmam (ii). Qualquer que seja a escolha, uma das duas
  superfícies precisa mudar no MESMO commit — publicar contrato divergente
  do código é a classe de defeito que este repo trata como P0.
- **Resolver por teste.** O teste segue skipado justamente porque a
  indecisão é de doutrina; ele volta a rodar (sem skip) quando esta ADR for
  aceita, pinando o comportamento escolhido.

## §4 Decisão — **A PREENCHER PELO OWNER**

```
Escolha:      [ ] (i) fail-CLOSED     [ ] (ii) fail-OPEN + breadcrumb
Data:
Justificativa (1 parágrafo — o que pesou mais):
```

### Se (i) — o que entra no MESMO commit
1. `plan162-w2-fixes.patch` como está (já implementa).
2. **Emenda a `CLAUDE.md` §4 e `AGENTS.md` §1**: registrar que o deadline
   do matcher canônico é a exceção deliberada, com o porquê (§2.i) — ambos
   são canonical, entram na Fase B.
3. Rota de recuperação **testada**, não só documentada: o unlock com a
   proveniência nova (ver `plan162-w2-NOTES.md` §"Codex r2 fold").
4. Reabilitar o teste skipado, pinando BLOCK.

### Se (ii) — o que entra no MESMO commit
1. Converter o branch do deadline para breadcrumb + `{}` allow, mantendo o
   evento de auditoria (`canonical_edit_hook_fault` vira observabilidade).
2. Registrar em ADR-164-AMEND-1 §4 que o residual de saturação **permanece
   aberto** — a partição de cache reduz a probabilidade, não a classe.
3. Reabilitar o teste skipado, pinando ALLOW + presença do breadcrumb.

## §5 Custo de adiar

A Fase B da cerimônia 2 fica **bloqueada** (por construção, as fases são
separáveis — o resto da leva anda sem ela). O P0 de case-fold do
`PLAN162_FIX_CASEFOLD` viaja junto do mesmo patch, então adiar mantém
aberto o bypass por filesystem case-insensitive verificado em S291.
**Essa é a única pressão real de tempo** — e ela é argumento para decidir
rápido, não para decidir de qualquer jeito.
