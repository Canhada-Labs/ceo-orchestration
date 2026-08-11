# ADR-149 — Amendment 2 (DRAFT): Trust vs Preference — currency por construção

> **Status: DRAFT (S302e, 2026-08-11).** Este texto vive no diretório
> do PLAN-176 e SÓ vira emenda real via cerimônia de ADR
> (canonical-edit + pair-rail + sentinel), no início da execução.
> Nunca copiar direto para `.claude/adr/` fora da cerimônia.

## Contexto

O ADR-149 nomeou a cura de CLASSE para model-currency após a S298
(7 bugs funcionais de model-id de geração antiga). O pente-fino S302d
achou a classe ainda viva (shape codex 0.139 vs binário 0.144.6;
`_VALID_MODELS` rejeitando o replacement recomendado pelo próprio
deprecations-ledger; gen-5 ausente de adapters/pricing/roteamento) e
o gap estrutural: toda a cobertura é REATIVA. Esta emenda estabelece
a doutrina POR CONSTRUÇÃO.

## Decisão

1. **Duas camadas de identidade de modelo, separadas por SCHEMA:**
   - **Camada T (Trust):** superfícies onde o modelo participa da
     GARANTIA — reviewer bloqueante do rail, VETO holders,
     experimentos pré-registrados, pins de CLI (ADR-111/182),
     `settings.json:model`. Identidade = id CONCRETO Owner-signed.
     O sistema AVISA quando o pin fica atrás do frontier ("agende
     cerimônia de bump"); NUNCA troca sozinho. Racional: reviewer que
     muda de modelo muda o verdito — é mudança auditável por
     definição.
   - **Camada P (Preference):** lanes advisory, defaults de
     live-adapter, probes, pricing, roteamento não-VETO. Identidade =
     ALIAS estável (`claude-frontier`, `codex-latest` ≡ omitir
     `--model` — doutrina D5/PLAN-142 codificada como dado,
     `grok-latest`, `gemini-latest`) resolvido em runtime.
2. **Fonte única com SPLIT cerimonial (r4):** DOIS arquivos —
   `.claude/governance/models-registry.json` = camada T + SCHEMA da
   camada P (sentinel-gated; muda SÓ por cerimônia canonical-edit) e
   `.claude/data/models-preference.json` = valores da camada P
   (aliases → resolved-id; muda por PR auditado com evidência, SEM
   sentinel — por design, para o refresh fluir SEM contornar
   cerimônia: a superfície cerimonial é o schema/T, não os valores
   P). Resolver `_lib/model_registry.py` (stdlib, NO-network, cache
   por-processo) valida os valores P contra o schema T em toda
   leitura — valor P fora do schema = fail-closed p/ o default do
   schema. Precedência: override do caller > env do usuário >
   preference > default do schema. TTL vencido = advisory, nunca
   bloqueio.
3. **Fechamento da classe:** lint CI `check-model-literals.py` —
   model-id literal NOVO fora do registry/autoridades declaradas =
   vermelho (fail-closed em input novo); legado entra em
   grandfather-ledger com ratchet (só diminui). Oracle permanente:
   `replacements ⊆ valid_override_ids` (mata a contradição
   deprecations-vs-validador por construção).
4. **Refresh:** rotina com rede (PLAN-176) propõe atualização da
   camada P via PR auditado; camada T só muda por cerimônia. Advisory
   tripla {instalado, pin, upstream} por CLI no `/ceo-boot`/nightly.
5. **Teste-mestre da classe (AC permanente):** injetar id fake de
   próxima geração no registry ⇒ todas as superfícies P refletem com
   ZERO edição de código; nenhuma superfície T muda.

## Consequências

- (+) "Ficar para trás" deixa de ser vigilância e vira impossibilidade
  estrutural na camada P; na camada T vira alerta acionável.
- (+) 3+ tabelas paralelas (pricing, role→model, valid-models)
  colapsam em 1 fonte.
- (−) Um arquivo canônico novo (registry) entra na superfície de
  cerimônia; custo aceito — é O ponto de controle.
- (−) Resolver adiciona 1 indireção em caminhos quentes; mitigação:
  cache por-processo, perf-gate existente cobre.

## Rota (r5 — alinhada ao W0 do PLAN-176)

Implementação: **PLAN-176 W0** (registry split T/P + resolver + lint
+ oracles); PLAN-169 W2.10 (lote de literais vivos) e W4.3(iv)
(manifesto/oracle de fleet-currency, escopo assinado inalterado).
Fase com rede: PLAN-176 W1-W3. Shape codex 0.144.6 +
`_VALID_MODELS`: checklist da próxima cerimônia de pin-bump.
