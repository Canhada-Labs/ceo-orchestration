---
id: PLAN-176
title: Currency-by-construction — rotina de refresh do models-registry com rede (a ÚNICA parte que precisa de plano novo)
status: reviewed
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169]
budget_tokens: 300-550k (re-firmado S302e r4 — W0 registry/resolver/lint 150-250k AGORA MORA AQUI; W1 rotina 100-150k; W2-W3 100-150k)
budget_sessions: 4-5 (W0 2; W1 1; W2+W3 1-2; fase-2 auto-merge FORA — gated em ADR)
context_risk: medium
external_wait: "milestone: pós-GA v1.3.0 + lote W2.10/169 (literais curados). Registry/resolver/lint = W0 DESTE plano (r5). L3: rotina com REDE que escreve commits ⇒ debate próprio"
tags: [model-currency, egress, automation, seed]
---

# PLAN-176 — Refresh automático do models-registry (fase com rede)

> **SEMENTE (S302d, 2026-08-11).** Do pente-fino hardcode-currency (4
> scanners + arquiteto + mapa de cobertura, árvore intocada em
> freeze). Contexto: os hardcodes vivos achados entram no lote
> mecânico do W2.10/169; o manifesto/oracle de fleet-currency segue
> no W4.3(iv)/169; a doutrina vira ADR-149 Amendment 2; a shape codex
> 0.144.6 + `_VALID_MODELS` entram no checklist da próxima cerimônia
> de pin-bump. **Correção r4 (Codex): o texto assinado do W4.3(iv)
> NÃO promete registry/resolver/lint — então eles MORAM AQUI (W0),
> sem dependência pendurada. Este plano = W0 (sem rede) + a rotina
> COM REDE que detecta lançamentos e propõe o refresh (W1-W3).**

## 1. Arquitetura herdada (decidida no ADR-149 Amendment 2, não aqui)

- **Camada T (trust):** VETO holders, reviewer pós-land, experimentos
  pré-registrados, pins de CLI, `settings.json model` — id concreto
  Owner-signed; o sistema AVISA "pin atrás do frontier, agende
  cerimônia", nunca troca sozinho.
- **Camada P (preference):** lanes advisory, defaults de live-adapter,
  probes, pricing, roteamento não-VETO — aliases (`claude-frontier`,
  `codex-latest` = omitir `--model`, doutrina D5 como dado) resolvidos
  pelo SPLIT do W0 (r4): schema+T em
  `.claude/governance/models-registry.json` (sentinel-gated); VALORES
  P em `.claude/data/models-preference.json` (PR auditado, sem
  sentinel — validados contra o schema em toda leitura, fora-do-schema
  = fail-closed p/ default) via `_lib/model_registry.py` (stdlib,
  no-network). Precedência: caller > env > preference > default do
  schema. TTL vencido = advisory.
- **Fechamento da classe:** lint CI `check-model-literals.py` com
  grandfather-ledger e ratchet (literal novo fora de autoridade =
  vermelho); oracle `replacements ⊆ valid_override_ids`.
- **Teste-mestre:** injetar `claude-opus-6` fake no registry ⇒ todas
  as superfícies P refletem com zero edit de código.

## 2. Escopo DESTE plano

- **W0 — registry + resolver + lint (sem rede; r4: mora aqui, não no
  169):** split de arquivos que preserva a cerimônia POR CONSTRUÇÃO —
  `.claude/governance/models-registry.json` = camada T + SCHEMA
  (sentinel-gated; muda SÓ por cerimônia canonical-edit) e
  `.claude/data/models-preference.json` = camada P (aliases →
  resolved-id; muda por PR auditado com review advisory, SEM
  sentinel). Resolver `_lib/model_registry.py` (stdlib, no-network,
  cache por-processo) + lint `check-model-literals.py`
  (grandfather+ratchet) + oracle `replacements ⊆ valid_override_ids`.
- **W1 — rotina cloud semanal (a única parte com rede):** cobre SÓ
  feeds de MODELOS dos vendors (Anthropic/OpenAI/xAI/Google) — o que
  o substrate-watch NÃO faz. **Sem double-booking (r4): drift de CLI
  segue 100% do substrate-watch; este plano APENAS estende
  `check-substrate-watch.py` com o probe upstream faltante (e o probe
  grok do débito PLAN-163) e CONSOME seus ledgers — nenhum fetcher
  paralelo de CLI.** Controles de ingress (r4): allowlist FIXA de
  hosts/paths HTTPS; redirects não seguidos fora do mesmo host;
  limite de tamanho/timeout por resposta; digest sha256 da resposta
  gravado como proveniência; feed malformado/ambíguo = FAIL-CLOSED
  (relatório, nunca PR). **Garantia de egress (r5 — restaurada e
  endurecida): requisições são GET-only, SEM body, SEM query params
  além do path fixo da allowlist, SEM headers customizados — NADA do
  repo (nem números de versão locais) sai em requisição alguma; a
  comparação local↔upstream acontece inteiramente em disco. Revisão
  ADR-114 no debate de abertura.**
- **W2 — proposta AUDITADA tocando SÓ a camada P:** PR sobre
  `models-preference.json` (não-sentinel POR DESIGN do split W0 — a
  cerimônia não é contornada porque a superfície cerimonial é outra);
  o PR carrega o relatório+digests como evidência; CI vermelho
  fail-closed se tocar o arquivo T/schema. Fase 2 (auto-merge com
  janela de veto): FORA — só com ADR próprio.
- **W3 — advisory tripla no `/ceo-boot` e nightly:** para cada CLI
  (codex/grok/claude): instalado vs pin vs upstream (via
  substrate-watch estendido) — informa, NUNCA bloqueia.

## 3. Kill criteria / guard-rails (ampliados no r4)

- >2 falsos-positivos/mês (PR de lançamento inexistente) ⇒ desativa
  auto-abertura, vira relatório no nightly.
- PR tocando o arquivo T/schema ⇒ vermelho fail-closed no CI.
- Feed stale/parcial (mais velho que 30d ou campos ausentes) ⇒
  report-only, nunca PR.
- Drift de parser (schema do feed mudou) ⇒ fail-closed + breadcrumb.
- **Controle de falso-NEGATIVO mensal:** fixture de lançamento
  conhecido injetado ⇒ a rotina TEM de detectá-lo (positive control
  da detecção; se falhar, lane marcada morta no nightly).
- 3 falhas consecutivas de um vendor ⇒ lane desabilitada + alerta
  (nunca silêncio).
- Fase 2 (auto-merge) só com ratificação explícita do Owner em ADR.

## 3b. Pronto-para-execução (S302e)

**ACs por wave:** W1 = rotina registrada (RemoteTrigger, irmã da
substrate-watch trig_014Y…) com 1 run manual verde que compara feeds
vs registry vs pins e emite relatório; AC: relatório lista os 3 CLIs
com {instalado, pin, upstream}. W2 = 1 PR real gerado pela rotina
(pode ser sobre lançamento simulado no fixture) tocando SÓ campos P;
AC: o lint `check-model-literals` (do W0 DESTE plano) fica VERMELHO
se o PR tocar campo T — positive control do próprio guard-rail. W3 =
advisory tripla visível no `/ceo-boot` com os 3 CLIs; AC: nunca
bloqueia (é advisory por construção — testar com upstream fake à
frente do pin).

**Dependência dura (r4: corrigida — era pendurada):** W1-W3 só abrem
com o W0 DESTE plano landado (registry/resolver/lint); do 169 este
plano depende apenas do lote W2.10 (literais curados) e consome o
deprecations-ledger e os ledgers do substrate-watch.

**Draft do ADR-149 Amendment 2** (Trust vs Preference — a doutrina
que este plano implementa a fase-com-rede): em
`PLAN-176/adr-149-amendment2-draft.md`; formaliza via cerimônia de
ADR no início da execução (nunca criado direto em `.claude/adr/`).

**Runbook sessão 1 (r5: começa pelo W0):** `/debate start PLAN-176`
(L3: egress + rotina que escreve commits) → cerimônia do ADR-149-A2
→ **W0** (split T/P + resolver + lint, sem rede) → só então W1.

**Debate:** este plano NÃO passou pelo pair-rail de S302c (nasceu
depois) — o round Codex r4 do conjunto cobre; o `/debate` L3 formal
é obrigatório na abertura por envolver egress.

## 3c. Anexo S305 — fundamentação externa do split T/P (advisory)

A literatura de cascade/routing (linha 5 de
`PLAN-178/research-S305.md`) fundamenta exatamente a arquitetura
herdada do §1: roteamento cost-aware vive na camada P (preference,
troca barata e auditada) enquanto decisões de confiança ficam
Owner-signed na camada T. Nada muda no escopo; a referência entra no
debate de abertura como evidência de que o split não é idiossincrasia
nossa — é o desenho que a literatura de custo/qualidade recomenda.

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
