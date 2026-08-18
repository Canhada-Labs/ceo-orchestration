# PLAN-180 W3 — material pronto para a cerimônia (Owner GPG, 1 sentinel)

> **LANDADO na S313 (2026-08-18, `4b7efee`, sentinel `S313-approved.md`)
> como carona do trem S313.** Correção à nota abaixo: o Edit 2 foi
> aplicado em `.claude/workflows/council-audit.js` (`laneBrief`), NÃO em
> `council.md` — o `.md` só delega ao workflow; o template do prompt das
> lanes externas vive no `.js`. Este arquivo é histórico.

> W3 é DESTACÁVEL (o plano entrega o valor principal com W0-W2, já
> landados). Pode pegar carona em qualquer cerimônia futura — p.ex. a
> mesma sessão do pack W3 do PLAN-169 (sentinels SEPARADOS, mesma
> pinentry-session é aceitável; escopos não se cruzam).

## Edit 1 — `.claude/adr/ADR-081-token-as-time-unit.md` (canônico)

No frontmatter, trocar:
    enforcement_commit: pending
por:
    enforcement_commit: <sha do commit "feat(PLAN-180 W0-W2)" em main>
(fecha o "pending" de abril; o validador advisory existe e está wired.)

## Edit 2 — `.claude/commands/council.md` (canônico, egress-guarded)

Acrescentar ao template de prompt das lanes externas (Codex/Grok), junto
das instruções fixas:

    - Estimativas de esforço em tokens+sessões (ADR-081); prazo humano
      SÓ para external_wait; converta qualquer "semanas de trabalho"
      da sua análise antes de reportar.

## Sentinel

Escopo de 2 paths (os acima). Draft de approved segue o molde de
qualquer cerimônia comum (Anchor-SHA = HEAD na assinatura). Depois do
land: flip do PLAN-180 executing→done com `related_commits` (W0-W2 + W3)
e `completed_at` — regra check_plan_edit.
