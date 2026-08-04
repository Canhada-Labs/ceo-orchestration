---
adr_id: ADR-186
title: Política de deadline de hook — fail-closed (verificação incompleta) vs fail-open (falha de infraestrutura)
status: ACCEPTED
proposed_at: 2026-08-04
accepted_at: 2026-08-04
proposed_by: CEO (S292 — conflito levantado pelo consensus C2 do PLAN-162 e confirmado de forma independente pelo pair-rail em DOIS rounds)
decided_by: Owner (ratificação em sessão, S292)
risk_tier: A
debate_required: true
supersedes_clause_in: [CLAUDE.md §4, AGENTS.md §1]
related_plans: [PLAN-162]
related_adrs: [ADR-119, ADR-164, ADR-164-AMEND-1]
---

# ADR-186 — Política de deadline de hook: o timeout interno de um matcher de segurança é falha de INFRAESTRUTURA ou sinal de VERIFICAÇÃO INCOMPLETA?

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

## §4 Decisão — RATIFICADA PELO OWNER

**Escolha:** **(i) fail-CLOSED** — o wall-deadline do matcher canônico é
uma exceção deliberada e nomeada à regra de fail-open em infraestrutura.

**Data:** 2026-08-04.

**Decidida por:** o Owner (S292), sobre a proposta do CEO.

**Justificativa (o que pesou mais).** Pesou, nesta ordem: (a) o **consensus
C2** do debate do PLAN-162 já havia decidido fail-CLOSED com três críticos, e
essa decisão é coerente com a postura F-01-07 que o próprio
`check_canonical_edit.py` pratica hoje em três outros pontos — reverter agora
seria trocar uma decisão debatida por uma leitura literal de uma frase que
nunca teve o deadline de um matcher em mente; (b) a janela é **medida, não
hipotética** — o ADR-164-AMEND-1 registra 4,16 s consumidos de um orçamento
de 5 s com 20 alvos, ou seja, quem planta sentinels alcança o teto por
**saturação**, e fail-open ali não é "o gate teve azar com a infra", é uma
porta que o atacante abre quando quiser; (c) o custo honesto do fail-closed
— travar o Owner com um `gpg-agent` pendurado — deixou de ser hipótese
porque a **rota de recuperação com proveniência** (`CEO_SENTINEL_UNLOCK` mais
`CEO_SESSION_ANCHOR_SHA` **ou** `CEO_SENTINEL_UNLOCK_SHA256`, com o próprio
bloqueio ensinando os dois `export` quando há janela armada) é implementada,
testada e documentada **no MESMO patch** (`plan162-w2-NOTES.md`, §"Codex r2
fold", P1-2/P1-3), e um gate fail-closed com saída documentada não é um
tijolo; e (d) a coerência do contrato é preservada da única forma que este
repo aceita — por **emenda explícita** a `CLAUDE.md` §4 e `AGENTS.md` §1 no
mesmo commit, nomeando a exceção e o seu porquê, em vez de deixar o código
praticar uma regra que os documentos publicados negam, que é exatamente o
P0 descrito no §3.

### Se (i) — o que entra no MESMO commit
1. `plan162-w2-fixes.patch` como está (já implementa).
2. **Emenda a `CLAUDE.md` §4 e `AGENTS.md` §1**: registrar que o deadline
   do matcher canônico é a exceção deliberada, com o porquê (§2.i) — ambos
   são canonical, entram na Fase B.
3. Rota de recuperação **testada**, não só documentada: o unlock com a
   proveniência nova (ver `plan162-w2-NOTES.md` §"Codex r2 fold").
4. Reabilitar o teste skipado, pinando BLOCK.

### Se (ii) — o que entra no MESMO commit *(NÃO ADOTADA — registrada para o histórico da decisão; não executar esta lista)*
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
