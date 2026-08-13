# PLAN-178 W3 — Memo: "dreaming" nativo vs gated-learning (PLAN-154)

> Estudo read-only (S305). Decisão de ativação = Owner. Fontes do
> substrato em `research-S305.md` linha 15; código nosso citado com
> arquivo:linha.

## O que cada lado é

- **Dreaming (substrato 2026):** processo agendado que revisa sessões
  e memory stores, extrai padrões e CURA memórias automaticamente.
  Escreve na memória persistente sem gate humano por item.
- **PLAN-154 (nosso, status done, default-OFF):** loop de lições com
  trilha completa de confiança: `write_lesson` com scan de injeção no
  ingest (lessons.py:430,479), aprovação registrada na CADEIA HMAC
  com `sha256(trigger + advisory_text)` (lessons.py:47-48,156),
  verify-before-render, ranking com decay (lessons.py:615,644),
  outcome com undo (lessons.py:704,782), poda governada (ADR-017/020),
  renderização no boot fail-CLOSED por lição
  (ceo-boot.py `_validate_boot_lesson`:4272-4339) e ativação
  estruturalmente OFF sem `CEO_LEARNING_BOOT_LESSONS=1` (ausente do
  bloco env de settings.json — verificado).

## Análise

A memória persistente é SUPERFÍCIE DE INJEÇÃO com alcance
cross-session: o que entra nela é renderizado como contexto de
sessões futuras. Um curador autônomo que escreve na memória sem
aprovação por item é, na taxonomia do nosso próprio W0, um INJ-3
amplificado (escrita não-gateada lida depois como contexto) — e sem
proveniência HMAC, um evento de curadoria não é distinguível de uma
adulteração. O PLAN-154 resolveu exatamente isso: aprovação humana
(/lesson-review), hash na cadeia, render fail-closed. O dreaming
nativo, na forma atual documentada, não expõe nem trilha de auditoria
por mutação nem gate de aprovação — é estritamente mais fraco no eixo
que este repo considera inegociável.

## Recomendação (go/no-go + condições)

- **NO-GO para dreaming nativo neste repo, nesta forma.** Re-avaliar
  apenas se o substrato expuser: (a) log por mutação de memória com
  proveniência; (b) modo propose-only (curadoria vira PROPOSTA que o
  Owner aprova); (c) kill-switch. Vigilância: dimensão vii do
  nightly (substrate-watch) já cobre changelog — nenhum trabalho novo.
- **GO condicional para o NOSSO rail:** a alternativa correta ao
  dreaming já existe pronta e auditada — ativar
  `CEO_LEARNING_BOOT_LESSONS=1` (opt-in do Owner, reversível,
  master-kill `CEO_SOTA_DISABLE=1`). Se o Owner quiser curadoria
  automática de PADRÕES, o caminho é `/lesson-evolve` (cluster →
  SP-NNN com soak de 7d), não um escritor autônomo.
- Nenhuma mudança de código neste memo; W3 fecha com esta
  recomendação registrada (AC-5).
