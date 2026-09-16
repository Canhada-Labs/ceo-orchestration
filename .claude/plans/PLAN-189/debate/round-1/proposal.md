---
plan: PLAN-189
round: 1
created_at: 2026-09-16T00:10:00Z
scope_of_this_round: "W0 — regra de classe no PROTOCOL.md (uma assinatura, sozinha). W1+W2 vêm na assinatura seguinte; W3 depois."
owner_decisions: ".claude/plans/PLAN-186/debate/owner-decisions-S353.md (decisões 6, 7 e 8)"
---

# PLAN-189 — proposta para o round 1 (W0: cure a CLASSE, não o exemplo)

Plano completo: `.claude/plans/PLAN-189-cure-quality-and-rail-instrumentation.md`.
Este round critica **o texto real que será assinado**, não uma paráfrase.

## Tese (do plano)

Cerimônias de 6, 11, 12 e 27 rodadas custaram dezenas de horas do Owner. Três
hipóteses morreram contra dados: «o rail produz ruído» (classe temática ≠ falso
positivo), «teto de 3 rodadas» (validade dos achados NÃO decai: r1-r3 93 %,
r4-r7 93 %, r8+ 91 %; 178 REAL contra 13 REFUTADO) e «parar quando não há P0/P1
novo» («nenhum novo» deixa bloqueio antigo aberto). A causa medida são DUAS,
coexistindo: **cura por enumeração** (`_sanitize_memory_basename` byte-idêntica
entre os candidatos da r6 e da r15; a r22 declara ser a QUINTA rodada da mesma
classe e só então REMOVE a superfície) e **regressão por cura** (a cura do P2 da
r9 introduziu `-m`; o P1 da r26 denuncia a união dos diffs dos pais; o teste da
r9 seguia VERDE — um exemplo coberto não cobre a classe).

Nada aqui reduz detecção: sem teto, sem filtro, sem severidade que dispense
revisão.

## Decisões do Owner já tomadas (S353, 15/09, verbatim)

- OQ-1: «W0 primeiro, sozinha». W3 fica para assinatura posterior.
- OQ-2: «Propriedade OU superfície, julgado pelo autor». Mesma propriedade violada
  OU mesma superfície de entrada; quem cura julga e escreve a classe no registro.
- OQ-3: «Fazer agora junto» — W2 (telemetria) entra no programa agora; viaja com a
  W1 na assinatura seguinte à da W0 (leitura do CEO).
- Molde da cerimônia: o `OWNER-PIN-SIGN.sh` de 15/09 (um passo, sem push, GPG só
  no sentinel, gates completos, `touched ⊆ scope`).

## O que a W0 entrega (escopo canônico desta assinatura)

| path | op | oráculo |
|---|---|---|
| `PROTOCOL.md` | insere a seção abaixo entre «## Receiving review» e «## 3-Strike policy» | 1 |
| `.claude/adr/ADR-140-AMEND-1-cure-the-class.md` | novo — emenda ao ADR-140 (doutrina de receber revisão) | 1 |
| `.claude/adr/README.md` | 1 linha nova no índice | 1 |

SEMVER do protocolo: **MINOR** (doutrina aditiva) ⇒ ADR-AMEND emparelhado + Sync
Impact Report no corpo do commit (`docs/PROTOCOL-SEMVER.md`). Dependent-set do
relatório: `CLAUDE.md` §Critical Rules (já carrega a linha «Cure a CLASSE» da
S352 — vira referência, não duplicata), `PLAN-SCHEMA.md`/`DEBATE-SCHEMA.md`
(sem mudança prevista — os críticos dizem se há), skill `receiving-review`
(SP-NNN, FORA desta assinatura — follow-up nomeado).

## TEXTO PROPOSTO para o PROTOCOL.md (o objeto da crítica)

```markdown
## Cure discipline — cure the class, not the example

> Added 2026-09-16 (PLAN-189 W0, ADR-140-AMEND-1). Applies to every cure of a
> review finding — pair-rail, debate, Owner, CI — from the first round of a
> ceremony onward. It reduces no detection: no round ceiling, no filter, no
> severity that waives review.

Every finding a reviewer raises belongs to a **class**: the property it
violates, or the input surface it enters through. The author of the cure
names the class in the round record — one `Class:` line per finding — and the
judgment is the author's, written down, never implicit. "Same class" is met by
either test: same property violated, or same input surface.

1. **First occurrence** — cure the finding and name its class in the record.
2. **Second occurrence of the same class in the same ceremony** — the next
   cure MUST NOT be another example. Either it removes the surface (an
   architecture change: the input no longer exists, or the property holds by
   construction), or the record states in writing why removal is not
   possible and carries a **named risk acceptance** for that class.
3. A round record showing a second occurrence of a class with neither a
   structural cure nor a declared acceptance is a **visible violation** of
   this section: it is a blocking finding against the record itself, and no
   further round opens on that class until the record carries one of the two.

Enumerating instances is not a cure; it is how a class stays open. Precedents:
PLAN-179 r22 — five rounds on one basename sanitizer (spaces, hyphens,
concatenation, limits), closed only when the surface was removed; PLAN-189
diagnosis — `_sanitize_memory_basename` byte-identical between the r6 and r15
candidates, so the "late" P1 had been there since r6.

Companion rules land in their own signatures: controls proportional to the
risk of the change (PLAN-189 W1), rail telemetry (W2), and the safeguard
against editing the record (W3).
```

## O que pedimos aos críticos

1. O texto reduz detecção em algum caso? Onde uma cura legítima ficaria
   proibida ou um achado real deixaria de ser registrado?
2. A definição de «mesma classe» (propriedade OU superfície, julgado pelo autor)
   é operável sem discussão? Onde ela abre porta para «tudo é outra classe»?
3. O item 3 promete um mecanismo que não existe? («no further round opens» — hoje
   é regra de processo; W2/W3 tornam mecânico). A redação está honesta?
4. Interação com as regras já ratificadas do modelo v2.1 (R1: zero codex em land
   livre; R2: teto por classe; R3: >20 registros = custo afundado). Conflito?
5. Sync Impact: que artefato a jusante PRECISA mudar nesta assinatura para o
   protocolo não ficar auto-contraditório (CLAUDE.md, DEBATE-SCHEMA, skill
   `receiving-review`, `docs/HONEST-LIMITATIONS.md`)?
6. Estimativas em tokens+sessões (ADR-081); prazo humano SÓ para external_wait;
   converta qualquer «semanas» recebido de fonte externa antes de consolidar.

Formato obrigatório: DEBATE-SCHEMA.md §4 (7 seções). Escreva EXATAMENTE um
arquivo: o do seu FILE ASSIGNMENT. Não toque em nenhum outro.
