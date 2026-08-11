---
id: PLAN-176
title: Currency-by-construction — rotina de refresh do models-registry com rede (a ÚNICA parte que precisa de plano novo)
status: draft
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169]
budget_tokens: 150-300k (firmado S302e; W1 rotina 100-150k, W2-W3 100-150k)
budget_sessions: 2-3 (W1 1; W2+W3 1-2; fase-2 auto-merge FORA — gated em ADR)
context_risk: medium
external_wait: "milestone: pós-GA v1.3.0 + registry/resolver landados (PLAN-169 W4.3 item iv). L3: rotina com REDE que escreve commits ⇒ debate próprio"
tags: [model-currency, egress, automation, seed]
---

# PLAN-176 — Refresh automático do models-registry (fase com rede)

> **SEMENTE (S302d, 2026-08-11).** Do pente-fino hardcode-currency (4
> scanners + arquiteto + mapa de cobertura, árvore intocada em
> freeze). Contexto: a cura da classe "modelo desatualizado" NÃO
> precisa de plano grande — registry + resolver + lint + oracles são
> a forma concreta do PLAN-169 W4.3 (item iv, manifesto+oracle já
> reservado lá); os hardcodes vivos achados entram no lote mecânico
> do W2.10; a doutrina vira ADR-149 Amendment 2; a shape codex
> 0.144.6 + `_VALID_MODELS` entram no checklist da próxima cerimônia
> de pin-bump. **Este plano cobre SÓ o que nada existente cobre: a
> rotina COM REDE que detecta lançamentos e propõe o refresh.**

## 1. Arquitetura herdada (decidida no ADR-149 Amendment 2, não aqui)

- **Camada T (trust):** VETO holders, reviewer pós-land, experimentos
  pré-registrados, pins de CLI, `settings.json model` — id concreto
  Owner-signed; o sistema AVISA "pin atrás do frontier, agende
  cerimônia", nunca troca sozinho.
- **Camada P (preference):** lanes advisory, defaults de live-adapter,
  probes, pricing, roteamento não-VETO — aliases (`claude-frontier`,
  `codex-latest` = omitir `--model`, doutrina D5 como dado) resolvidos
  por `.claude/governance/models-registry.json` (sentinel-gated) via
  `_lib/model_registry.py` (stdlib, no-network). Precedência: override
  do caller > env do usuário > registry. TTL vencido = advisory.
- **Fechamento da classe:** lint CI `check-model-literals.py` com
  grandfather-ledger e ratchet (literal novo fora de autoridade =
  vermelho); oracle `replacements ⊆ valid_override_ids`.
- **Teste-mestre:** injetar `claude-opus-6` fake no registry ⇒ todas
  as superfícies P refletem com zero edit de código.

## 2. Escopo DESTE plano (o que exige debate próprio por ter rede)

- **W1 — rotina cloud semanal** (irmã da substrate-watch já ativa,
  trig_014Y…): fetcha feeds/changelogs dos vendors (Anthropic, OpenAI
  /codex, xAI/grok, Google) e o npm/brew dos CLIs; compara com o
  registry e com os pins.
- **W2 — proposta AUDITADA, nunca troca silenciosa:** ao detectar
  lançamento, a rotina abre PR (ou commit em branch) tocando SÓ
  campos da camada P + atualiza `last_seen` upstream dos CLIs. Owner
  = merge de 1 clique. Fase 2 (opcional, gated em 4 semanas sem
  falso-positivo): auto-merge com janela de veto.
- **W3 — advisory tripla no `/ceo-boot` e nightly:** para cada CLI
  (codex/grok/claude): instalado vs pin vs upstream conhecido —
  "codex instalado 0.144.6, pin 0.144.6, upstream 0.151 ⇒ agende
  pin-bump". Informa, NUNCA bloqueia sessão.
- **Egress:** a rotina só LÊ fontes públicas dos vendors; nada do
  repo sai além de números de versão em query nenhuma (fetch é
  GET público). Ainda assim: revisão ADR-114 no debate.

## 3. Kill criteria / guard-rails

- Rotina com >2 falsos-positivos/mês (PR de "lançamento" inexistente)
  ⇒ desativa auto-abertura, vira relatório no nightly.
- PR da rotina tocando qualquer campo da camada T ⇒ vermelho
  fail-closed no CI (o lint distingue T de P por schema).
- Fase 2 (auto-merge) só com ratificação explícita do Owner em ADR.

## 3b. Pronto-para-execução (S302e)

**ACs por wave:** W1 = rotina registrada (RemoteTrigger, irmã da
substrate-watch trig_014Y…) com 1 run manual verde que compara feeds
vs registry vs pins e emite relatório; AC: relatório lista os 3 CLIs
com {instalado, pin, upstream}. W2 = 1 PR real gerado pela rotina
(pode ser sobre lançamento simulado no fixture) tocando SÓ campos P;
AC: o lint `check-model-literals` (do W4.3-iv/169) fica VERMELHO se o
PR tocar campo T — positive control do próprio guard-rail. W3 =
advisory tripla visível no `/ceo-boot` com os 3 CLIs; AC: nunca
bloqueia (é advisory por construção — testar com upstream fake à
frente do pin).

**Dependência dura:** registry+resolver+lint landados (PLAN-169
W4.3-iv). Sem eles, este plano não abre — não há o que refrescar.

**Draft do ADR-149 Amendment 2** (Trust vs Preference — a doutrina
que este plano implementa a fase-com-rede): em
`PLAN-176/adr-149-amendment2-draft.md`; formaliza via cerimônia de
ADR no início da execução (nunca criado direto em `.claude/adr/`).

**Runbook sessão 1:** `/debate start PLAN-176` (L3: egress + rotina
que escreve commits) → cerimônia do ADR-149-A2 → W1.

**Debate:** este plano NÃO passou pelo pair-rail de S302c (nasceu
depois) — o round Codex r4 do conjunto cobre; o `/debate` L3 formal
é obrigatório na abertura por envolver egress.

## 4. Anexo — inventário S302d (para o lote W2.10/W4.3; NÃO re-descobrir)

Bugs vivos: shape codex congelada em 0.139 vs binário 0.144.6
(`codex_cli_shape.py`, `codex_invoke.py`, `run-promotion-gate.py`);
`_VALID_MODELS` rejeita o replacement recomendado pelo próprio
`model-deprecations.json`; `adapters/live/claude.py` sem gen-5 no
`_ADAPTIVE_ONLY_MODELS` (HTTP 400); substrate-watch SEM probe de grok
(débito PLAN-163:295); `task-route.py` roteia VETO holders p/
opus-4-8/sonnet-4-6 literais; `success-receipt.py` pricing sem gen-5.
Rot: `_WAVE1_PROVIDER_DEFAULTS` com `gpt-4o`; `canonical_models.json`
sem gen-5 e expirando 01/09; duas tabelas role→model paralelas
(audit_log.py vs model_routing.py) — unificação sem dono;
`anthropic-version` em 6 arquivos; ledger substrate-watch stale.
Fora da classe modelo (itens independentes, mais barato→mais urgente:
npm-publish.yml Node 20 EOL desde 30/04; SIGN_KEY GPG hardcoded em
release.sh; `runs-on: Ceo` sem fallback em 6 sites; python-version
misto 3.11/3.12; actionlint triplicado c/ 1 cópia sem hash).
