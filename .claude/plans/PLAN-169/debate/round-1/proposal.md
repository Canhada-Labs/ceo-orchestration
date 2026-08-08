---
plan: PLAN-169
round: 1
created_at: 2026-08-08
---

# Proposta (round 1) — PLAN-169: Fechamento total + evolução cross-session

> Destilação. Plano completo: `.claude/plans/PLAN-169-closure-and-cross-session-evolution.md`.
> Evidência: `PLAN-169/ledger-S298.md` (65 itens, path:line) + pesquisa
> S298 (originais no archive privado; integridade + fontes públicas em
> `PLAN-169/research-MANIFEST.md` — citações `research-*.md:N` nos
> registros de debate resolvem contra os originais hasheados).

## Tese

1. **Dois trens, em sequência — não um trem gordo.** v1.3.0 GA via
   PLAN-166 W2 como escrito (rc.2 pronta, debate fechado, delta-gate
   estrito); v1.4.0 logo atrás com as novidades. Injetar features na
   1.3.0 reabriria o debate do 166 e violaria o delta-allowlist que o
   próprio 166 construiu.
2. **Fechar o instrumento antes do trem.** O nightly vermelho tem causa
   única de 1 linha (`test-ownership-table.sh:162`, `stat` BSD-first
   contamina stdout no GNU; 22 falsos-RED por super-detecção + 2 por
   sub-detecção = delta exato 24). Port antes da rc.2.
3. **Novidade vira claim só depois de teste pré-registrado.** A
   literatura 2026 FORTALECE o "no speed claim" para código; a bateria
   E7 (E0→E4→E3→E1→E2) testa onde a literatura diz que há chance
   (verificação paralela com revisores cegos), com braço token-matched
   obrigatório e gate-zero de Amdahl (H≥0,40 ⇒ E1/E2 nem são
   financiados).
4. **Quota 5h é continuidade, não velocidade.** Acionador em duas
   camadas nativas (hook `StopFailure(rate_limit)` + snapshot
   `resets_at` que o sidecar do statusline JÁ persiste) → cron one-shot
   de retomada. Pedido explícito do Owner.

## Estrutura de waves

- **W0** Higiene + escrituração (9 itens; L1-L2): untracked commitado/
  removido, step1 obsoleto marcado, Translations drift triado, §-final
  do 166 (subsunção AC-3/AC-4), memórias corrigidas (2 claims da
  memória estavam ERRADAS vs disco), 2 claims herdadas verificadas,
  2 decisões do Owner (convenção ACs 167/168; break-glass ADR).
- **W1** Port do harness e2e para Linux (fix 1 linha + rider
  fail-closed de mtime + rider FALSE-GREEN OWN-0073 + sweep da classe
  `A 2>/dev/null || B`). Aceite falsificável: 62 GREEN / 3 RED exatos.
  PROIBIDO tocar tabela/expected-reds.
- **W2** 8 fixes verificados em superfícies livres: grep causal do
  parity (1 linha), perf probe N=200+índices derivados (fix de
  CLASSE), injector exact-match fail-closed, overhead-ack canal
  sentinela+TTL, pair-rail-gate rota de auth login, marcador
  `.claude/.framework-version` como 12º site de bump (P1 com prazo:
  quebra no bump 1.4.0), matcher GUIA-COMPLETO, inventário da família
  "script livre que decide gate".
- **W3** Pack canônico único + cerimônia GPG: sanitização
  `PROTOCOL_SOURCE` (repro confirmado: newline no install-state mata
  upgrade a meio caminho sob `set -e`; fix = rejeitar control chars ⇒
  fallback D3 + gerador sem sed + atribuição guardada ⇒
  WARNING+PRESERVE), linha morta ancestral-symlink, emenda ADR-163,
  ADR break-glass (se W0.9 aceitar), ADR cross-session (W4.2).
- **W3-K** Cerimônia de kernel separada: emits do caminho GRANT
  silenciosos (`ceremony_sha` recebe PATH) + teste positivo do emit.
- **W4** Evolução do substrato:
  - **W4.1 quota-resume** (acima).
  - **W4.2 cross-session:** probes empíricos PRIMEIRO
    (`UserPromptSubmit` dispara p/ peer inbound? `SubagentStart`
    dispara p/ `agent()` de Workflow? cross-machine send real?);
    postura default `crossSessionInbound: "refuse"` (única alavanca
    fail-closed soberana ao repo — project refuse VENCE managed);
    PreToolUse em SendMessage/ListAgents (lado de envio é o
    interceptável) + evento HMAC; ADR de doutrina (peer = fronteira de
    confiança; buraco de proveniência do inbound registrado
    honestamente).
  - **W4.3 parametrização:** tiers por classe de tarefa + enforcement
    declarativo `Agent(param:value)` em permission rules.
  - **W4.4 hardening drift:** auditoria dos 48 matchers (2.1.195
    exact-match SILENCIOSO — candidato nº1 a hook morto) com controle
    positivo POR REGISTRO; pinagem de versão; `ConfigChange` hook;
    `--append-subagent-system-prompt`; `PostToolBatch`; `TaskCompleted`
    gate; DEFER channels (sender pode APROVAR tool use — laundering).
- **W5** Bateria E7 pré-registrada (E0 gate-zero de H → E4 handoff
  half-life → E3 verificação paralela cega → E1/E2 se E0 liberar);
  3 braços sempre (incl. token-matched); negativo publica igual.
- **W6** Trens: v1.3.0 GA (166 W2 pinado) → v1.4.0 (W1-W4 + relatório
  W5; bump minor = controle ao vivo do fix do marcador).

## Execução autônoma

Owner pré-autorizou execução autônoma por instrução literal (registrada
no plano). Pontos Owner-only (GPG, tags, aprovação npm, OQ-1/2/3) param
em checklist de retorno — nunca contornados.

## Open questions ao debate

- OQ-1: ordem de publicação (recomendação: 1.3.0 → 1.4.0 imediata).
- OQ-2: postura default do quota-resume (night-mode-only vs sempre-on).
- OQ-3: break-glass ADR — aceitar ou recusar.
- OQ-4: família "script livre que decide gate" — guard canônico ou
  checksum.

## O que pedimos dos críticos

Ataquem: sequenciamento (algo do W2 deveria estar no W3 por ser
canônico?), completude (o ledger tem item sem endereço?), segurança da
postura cross-session (refuse default quebra algo? o probe W4.2.0
falta cenário?), honestidade do W5 (algum braço/controle faltando?),
e o risco de escopo do pack W3 crescer.
