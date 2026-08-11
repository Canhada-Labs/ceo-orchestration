# PRÉ-REGISTRO E0b + E6 — DRAFT para assinatura do Owner (PLAN-172)

> **Status: DRAFT (S302e, 2026-08-11).** Vira pré-registro IMUTÁVEL
> com a assinatura GPG do Owner (`gpg --clearsign`, mesmo rito do
> W5-preregistration do PLAN-169). NENHUM dado é coletado antes da
> assinatura; qualquer mudança pós-assinatura = novo pré-registro.
> Herda o bloco metodológico comum do W5/PLAN-169 (p50/p95, ≥3 runs
> onde aplicável, grading cego, negativo publica igual, medição
> imprime seus inputs).

## E0b — Decomposição do tempo-morto (gate de financiamento do E5)

**Pergunta:** das 429,6h de tempo-morto do E0 (59% do wall-clock),
que fração é {ci-wait, hold-24h, quota, lag-de-retomada, outro}?

**Método:** etiquetagem retrospectiva do audit log HMAC dos MESMOS
14 planos do E0 (M=155→168, amostra PINADA — nenhuma escolha nova)
+ janela prospectiva de 2 semanas a partir da assinatura. Script
deriva de `PLAN-169/e0-serial-fraction.py` (imprime inputs: dirs,
shas, contagens). GAP_MACHINE_S=120 e GAP_HUMAN_MAX_S=3600 herdados
do E0 — NÃO recalibráveis pós-assinatura.

**Regras de precedência de etiqueta (sobreposições):** hold-24h >
quota > ci-wait > lag-de-retomada > outro. Um intervalo recebe UMA
etiqueta (a de maior precedência ativa no início do intervalo).
lag-de-retomada = tempo entre evento-terminal (CI verde, hold
vencido, quota renovada) e primeiro evento de trabalho subsequente.

**Decisão (tabela IMUTÁVEL — cópia da §1 do PLAN-172):**
| Resultado | Decisão |
|---|---|
| quota > 40% do morto | E5 NÃO financiado como desenhado; orçamento → wake-on-event; redesenho só via NOVO pré-registro |
| quota 20-40% | E5 piloto (metade do N, mesmos kills) |
| quota < 20% | E5 completo |
| lag-de-retomada > 30% do morto | wake-on-event ANTES de qualquer braço E5 |
| janela prospectiva com <10 unidades etiquetáveis | estende 2 semanas UMA vez; depois decide só com o retrospectivo |

**Censura:** intervalos não-etiquetáveis são REPORTADOS como taxa de
censura; censura >25% do morto ⇒ resultado marcado DEGRADED e
qualquer decisão de financiamento exige ratificação explícita do
Owner (lição: p95 de amostra censurada é inestimável).

## E6 — Cascata de filtros pré-review (unidade experimental = ROUND)

**H1:** com cascata (mutation-adequacy diff-scoped + verificadores
estáticos + dossiê ranqueado) entregue ao revisor ANTES do round,
rounds-até-GO caem ≥30% e minutos-humano ≥20%, sem aumento de
escapes (defeito achado ≤2 sessões após land que o rail deveria ter
pego).

**Fase 0 (pré-braços, obrigatória):** telemetria de TODOS os
desfechos do adequacy_gate (`measured_ok / weak / bail:<causa>`) por
2 semanas — taxa de censura publicada. Braço C (gating) SÓ nasce se
censura <50%. Limiar de kill-rate do C = p50 da telemetria da fase
0, CONGELADO neste pré-registro no ato da assinatura (valor
preenchido: ____ — Owner preenche ao assinar, após a fase 0).

**Braços:** A = rounds atuais (controle); B = cascata ADVISORY
(dossiê anexado, revisor livre); C = cascata GATING (kill-rate <
limiar ⇒ round devolvido antes do revisor externo). ≥30 rounds por
braço, atribuição por unidade de trabalho, ordem intercalada.

**Kill table (imutável):**
| Sinal | Ação |
|---|---|
| escapes ↑ vs A | mata o braço |
| falso-bloqueio em C >15% | mata C, mantém B |
| cascata p95 >2min | mata (virou gate caro) |
| rejeição precoce f≥30% MAS minutos-humano caem <5% | NEGATIVO; não promover |
| achados-humanos fora-do-dossiê caem JUNTO com minutos | review superficial ⇒ ABORTA imediato |

**O que este pré-registro NÃO cobre:** E5 (pré-registro próprio
pós-E0b), E3/E3b (E3 = W5/PLAN-169 imutável; E3b = registro futuro),
M1/M2 do inventor (plano próprio).

---
Assinatura do Owner (clearsign abaixo congela o documento):
