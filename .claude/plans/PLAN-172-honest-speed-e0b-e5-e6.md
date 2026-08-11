---
id: PLAN-172
title: Velocidade honesta — E0b (decomposição do tempo-morto) como gate, E5 (pipelining WIP=2), E6 (filter-cascade no review) + políticas observacionais
status: draft
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169, PLAN-171]
budget_tokens: "E0b+E6+políticas: baixo (retrospectivo/observacional); E5: ALTO (~18 unidades L2) — só se E0b liberar"
budget_sessions: E0b 1-2; E6 acompanha rails existentes; E5 TBD pós-gate
context_risk: high
external_wait: "gatilho: pós-GA v1.3.0 + W3/W4; E5 adicionalmente pós-PLAN-171 W5 (log único de worktree)"
tags: [experiments, speed, pipelining, review, seed, pre-registration]
---

# PLAN-172 — Velocidade honesta: atacar as frações medidas, não a autoria

> **SEMENTE (S302, 2026-08-11).** Registrada após segunda rodada de
> pesquisa (workflow speed-research-r2: lanes academia, indústria,
> primeiros-princípios, Codex CLI e Grok CLI — 5/5 ok, com atribuição
> de vendor). Pré-registro formal + debate L3 obrigatórios antes de
> qualquer braço rodar. **Nada aqui é claim de velocidade** — o
> contrato "no speed claim" (AGENTS.md) permanece incondicional até
> que um experimento pré-registrado produza evidência, e negativo
> publica igual.

## 0. O fato que reorienta tudo (E0, PLAN-169 W5, executado S300)

Sobre 14 planos reais (M=155→168), 723h de wall-clock:
**máquina 155,4h (21%) · humano 137,9h (19%) · tempo-morto 429,6h
(59%)**. S conservador = 1,000; mesmo no limite otimista S ≥ 0,785 ⇒
teto de Amdahl ≈ 1,27× para paralelizar AUTORIA. E1/E2 desfinanciados
pela regra pré-registrada (S ≥ 0,40). O morto por unidade (~30,7h)
EXCEDE o trabalho ativo da próxima unidade (~21h): sempre há mais
espera do que trabalho para escondê-la — o limite do pipelining é (i)
a fração do morto que é QUOTA (capacidade, não latência) e (ii) a
atenção do único humano.

**Convergência de 3 formalismos independentes** (Amdahl/E0, USL com
σ derivado do E0, varredura acadêmica S298): mais autores em paralelo
não compra nada. Teto composto honesto dos mecanismos deste plano:
**1,3–1,7×** (hipótese, não claim). A frase do verdito: *"não é um
problema de arquitetura de agentes — é um problema de calendário."*

## 1. Sequência interna MANDATÓRIA

**E0b é GATE de financiamento do E5, não irmão dele.**
E0b (≈zero custo) → decisão go/rebaixa do E5. E6 e as políticas
observacionais rodam em paralelo desde já (baratas).

### E0b — decomposição do tempo-morto (gate; consenso 5/5 lanes)
Etiquetar o audit log (janela ≥2 semanas + retrospectivo) por classe
de espera: `{ci-wait, hold-24h, quota, lag-de-retomada, outro}`, com
regra de precedência para sobreposições PRÉ-REGISTRADA e medição que
imprime seus inputs (lição S285). Saídas: (a) fração de cada classe;
(b) baseline do lag-de-retomada (evento terminou → trabalho retomou).
**Decisão embutida: quota > 40% do morto ⇒ teto do E5 cai < 1,4× ⇒
rebaixar/redesenhar o E5 ANTES de gastar 18 unidades.** Os holds de
24h (ADR-103) são previsíveis: só "calendar packing" deles já é
estimável retrospectivamente.

### Políticas observacionais (implantar sem braços; medição no log)
1. **Wake-on-event + fila-preparada** — acordar no evento (Monitor/
   cron) com a próxima unidade JÁ staged, em vez de ser encontrado
   pelo evento. Kill: lag mediano de retomada não cai ≥30%.
   Possivelmente o maior ganho por unidade de esforço do trem inteiro.
2. **Fusão de round-trips ao CI** — pré-push espelho dos gates exatos
   do CI (lição já em memória) para ir ao CI 1× em vez de k×. Kill:
   k baseline ≤ 1,5 (já fundido).
3. **Flake auto-rerun com breadcrumb** — minerar `gh run list` 90d;
   ativar só se taxa de flake ≥8%; NUNCA em gates de segurança.
   Conecta com PLAN-169(c) (tratamento N-maior do PLAN-159).

### E5 — pipelining WIP=2 (o experimento caro; só se E0b liberar)
- **H1:** WIP=2 (autorar U(n+1) durante o morto de U(n), base SÓ em
  artefatos landados) reduz p50 do wall/unidade ≥25% sem aumento de
  defeitos escapados.
- **Braços:** A = serial estrito (controle token-matched); B = WIP=2
  não-especulativo; C = B + especulação scoped a CI-waits com
  p_gate>0,8 — **PROIBIDO especular através de verdito humano de
  release** (NO-GO local ≥50% observado; consenso 5/5), logando taxa
  de rollback r e custo C_rollback.
- **N:** 6 unidades L2 por braço, ≥3 planos distintos, intercaladas;
  bloco metodológico comum do W5/169 (p50/p95, ≥3 runs, grading cego,
  negativo publica).
- **Kill:** defeitos B/C > 2× A ⇒ mata braço; redução p50 <10% após 6
  unidades ⇒ mata (sem estender N "até dar certo"); em C, r medido >
  r* = G/(G+C_rollback) ⇒ mata C, mantém B; **minutos-humano/unidade
  sobem >20% ⇒ mata (thrash do single-maintainer — risco #1, invisível
  no wall-clock; contribuição da lane Grok)**; qualquer violação de
  governança (HMAC, colisão de sentinel-scope entre unidades em voo)
  ⇒ PARA e reporta como RESULTADO.
- **Pré-requisito:** PLAN-171 W5 (log único por repo com worktree_id).

### E6 — cascata de filtros pré-review (barato; unidade = o ROUND)
Reutiliza o **Via Canhada** (`adequacy_gate.py`, PLAN-128: mutation
diff-scoped em sandbox, advisory, $0) + verificadores estáticos +
dossiê ranqueado entregue ao revisor.
- **H1:** rounds-até-GO caem ≥30% e minutos-humano ≥20%, sem subir
  escapes.
- **Braços:** A controle; B cascata ADVISORY; C cascata GATING
  (limiar de kill-rate CONGELADO antes do experimento). ≥30 rounds
  por braço (os rails já produzem 30+/sessão — custo marginal ~zero).
- **Kill:** escapes sobem ⇒ mata; falso-bloqueio em C >15% ⇒ mata C,
  mantém B; cascata >2min p95 ⇒ virou gate caro, mata; f≥30% de
  rejeição precoce mas minutos-humano caem <5% ⇒ **NEGATIVO, não
  promover** (resolve com dado a divergência entre lanes: academia
  otimista × Codex cético × Grok "verifier theater"); achados-humanos
  fora-do-dossiê caindo JUNTO com os minutos ⇒ review ficou
  superficial ⇒ aborta imediato.

### E3 (da bateria do PLAN-170) — só absorver 2 ajustes
Manter como pré-registrado; absorver: revisores single-pass
(multi-turn infla FP — fonte no archive S298) e heterogeneidade REAL
de vendor/papel; métrica nova: horas-de-adjudicação por achado
confirmado (kill se subir >50% vs rail serial).

## 2. O que este plano NÃO re-litiga

- **E1/E2 (autoria paralela):** mortos pela regra pré-registrada do
  E0. Qualquer proposta futura de "multi-model authors" herda esse
  verdito salvo dado NOVO de fração serial (um E0b pode fornecê-lo —
  ou não).
- **Remover/substituir review humano:** fora de escopo permanente.
- **Best-of-N sem oráculo executável:** gate barato antes de qualquer
  piloto — classificar retrospectivamente os achados dos NO-GOs
  históricos; se <30% seriam pegos por gates locais em N variantes,
  morre sem experimento.
- **Encurtar o hold ADR-103 por política:** decisão do Owner sobre
  governança, não mecanismo de velocidade; o hold é atacável apenas
  ENCHENDO-O (E5) ou por emenda explícita de ADR.

## 3. Publicação

Resultados (positivos OU negativos) entram como relatório no repo no
mesmo regime do E0; claims externas de números da literatura ficam no
archive (doutrina research-README do PLAN-169). O "no speed claim" do
AGENTS.md só muda por decisão do Owner sobre evidência pré-registrada.

## 4. Revisão v2 — auditoria total S302: este plano vira O TREM GRANDE

A auditoria (14 agentes; 6 dimensões internas com evidência
arquivo:linha + 6 lanes externas) recalibrou o alvo: o custo da
governança é o AGENDAMENTO (síncrono, exaustivo, no fim), não a
garantia. Entram:

- **W-DH — delta-hold (emenda ADR-103, a maior alavanca única):** o
  hold só reinicia para a superfície que MUDOU; crédito do tempo
  decorrido quando `inputs_hash` é idêntico (a rc.3 declarou hash
  idêntico ao da rc.2 e reiniciou 24h do zero) — ou hold concorrente
  com o re-pass. Toda a infraestrutura (inputs_hash, delta_manifest)
  já é computada e assinada. Corta 24-48h por trem multi-rc.
- **E5 ganha substrato definido:** background-rail (rounds Codex
  detached via run_in_background/Monitor — padrão S285 virando skill;
  38 rounds seriais ~8h → ~3-4h com 2 lanes e wall-clock efetivo
  ~zero porque o CEO segue autorando) + cross-session SendMessage
  (v2.1.224) para WIP=2 entre sessões com worktree próprio; spike
  curto de sandbox antes de fechar design.
- **E6 nasce risk-tiered com M3 como estágio-1.** M3 = "Distância de
  Irreversibilidade" (conceito novo, inventor S302): risco como
  gradiente DERIVADO do grafo de alcance até sinks irreversíveis
  (tag/publish/GPG/HMAC/settings), nunca classificado à mão; arestas
  desconhecidas colapsam para d=1 (conservador); d≤1 ⇒ cerimônia
  síncrona integral sempre. Validação barata: replay read-only dos 14
  planos do E0 — kill pré-registrado: se P0/P1 históricos concentram
  em d ALTO, o grafo é proxy errado e morre. Complemento: classificar
  retrospectivamente os ~38 verdicts da rc.3 em "mecânico vs
  semântico" (adjudica quanto o cascade pode capturar).
- **Via Canhada (sequência §1-E6) recalibrada pela leitura do código:**
  corte realista HOJE ~0-5% (não cobre shell/CI, onde os rounds
  foram); passo 1 vira telemetria de TODOS os desfechos
  (measured_ok/weak/bail:*) por 1-2 semanas — medir a taxa de censura
  ANTES de financiar diff-scoping real (o gate diz "diff-scoped" mas
  muta o arquivo INTEIRO — adequacy_gate.py:2 vs :253), amostragem
  estratificada com filtro AST e veredito tri-estado. Sandbox v2 só
  se bail >80%. Multi-linguagem descartado (padrão E1/E2).
- **Tiering do rail + stop-rules (do relatório §5.2):** canônico =
  open-ended com parada em 2 GOs consecutivos sobre artefato
  congelado (1 GO não basta: GO no r5, 2 P1 reais no r6); scripts
  operacionais = cap 5 rounds + checklist + escalada (espelha o
  round-3 do DEBATE); docs = gate determinístico sem rail;
  circuit-breaker universal ~8-10 rounds sem GO ⇒ mudar o ALVO
  (lição-mãe S296 virando mecanismo).
- **Separar DESCOBERTA de VERIFICAÇÃO-DE-CURA:** descoberta =
  single-pass k revisores cegos sobre pack congelado (E3); verificação
  = serial mas SÓ sobre o delta da cura, veredito amarrado a base
  SHA + diff hash; passe final de integração permanece (os melhores
  achados são cross-artefato).
- **Webhook/cron de hold-vencido + CI-verde** (notificação, nunca
  execução) — comprime o lag Owner-volta-ao-teclado dentro dos 59%.
- **Progressive disclosure do boot** (ceo-orchestration/SKILL.md
  ~15,6k tok ≈ 40% do Gate-1/2).

**Números honestos esperados (compostos, a PROVAR aqui):** reviewer
externo ~12-17h/trem → ~4-6h; rounds −50-70%; hold −24-48h.
Advertência da academia: fracionar ganha LATÊNCIA, não yield — a
promessa é "mesmos achados, semanas antes, com ~1/3 do wall-clock",
nunca "mais achados".

**Imediatos SEM plano (pós-GA, antes deste plano abrir):** shift-left
do escopo de release no rail da rc (CHANGELOG/workflows/npm no rail
da rc, re-pass vira delta-check); derivação de contagens (elevar
itens #3/#4/#6 do ledger 169 de "consertar exatos" p/ "derivar a
classe" — mata 4/8 achados do último NO-GO); stop-rule no template
run-*-review.sh; varredura substrate-drift (matchers exact-match
v2.1.195, exit-2+JSON v2.1.214); rota batch P2 + Merkle-manifest por
lote; sweep de atualidade das skills (cita gemini-1.5-pro/gpt-4-turbo
em skill core).

**M1 (loteria de aceitação com cascata de contaminação) NÃO entra
aqui:** muda o CONTRATO de garantia (exaustivo → estatístico-com-
bound) — plano próprio pós-172 com ADR + ratificação do Owner. M2
(revisor residente com dívida de cobertura + mutantes-sentinela)
entra como candidato do E5/E6 v2 APÓS o replay hunk-vs-composição.
