---
id: PLAN-172
title: Velocidade honesta — E0b (decomposição do tempo-morto) como gate, E5 (pipelining WIP=2), E6 (filter-cascade no review) + políticas observacionais
status: reviewed
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169, PLAN-171]
budget_tokens: "firmado S302e — W-IM 150-300k; E0b 50-100k; replay M3 80-150k; W-DH (2 emendas + cerimônia) 150-250k; E6 30k telemetria + 100-200k experimento; E5 2-4M SÓ se E0b liberar. Total sem E5: ~0,6-1,1M"
budget_sessions: "W-IM 2-3; E0b 1-2; M3 1; W-DH 2; E6 passivo + 1-2; E5 6-9 pós-gate"
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
**Tabela de decisão COMPLETA (Codex r1 — pré-registrada, nada fica
para juízo post-hoc):**
| Resultado E0b | Decisão |
|---|---|
| quota > 40% do morto | E5 NÃO financiado como desenhado; orçamento migra p/ wake-on-event; qualquer redesenho exige NOVO pré-registro (r2: sem escolha post-hoc) |
| quota 20-40% | E5 piloto (metade do N, mesmos kills) |
| quota < 20% | E5 completo (3 braços, N pleno) |
| lag-de-retomada > 30% do morto | wake-on-event ANTES de qualquer braço do E5 |
| janela sem ≥10 unidades etiquetáveis | estende 2 semanas UMA vez; depois roda só retrospectivo |

Os holds de 24h (ADR-103) são previsíveis: só "calendar packing"
deles já é estimável retrospectivamente. Budget E5 (firmado no
pré-registro, não TBD): ~18 unidades L2 ≈ 6-9 sessões, estimativa
2-4M tokens; aborta na metade se σ(A) cobrir Δ (regra do bloco
metodológico W5).

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
- **Braços:** A controle; B cascata ADVISORY; C cascata GATING.
  **Limiar do C (Codex r1 — especificado, não vago): derivado do p50
  histórico da telemetria Via Canhada (passo 1) e CONGELADO no
  pré-registro do E6; o braço C só nasce se a telemetria der censura
  <50%** (senão o gating seria sobre sinal majoritariamente mudo).
  ≥30 rounds por braço (os rails já produzem 30+/sessão — custo
  marginal ~zero).
- **Kill (r5): a kill-table do pré-registro
  (`PLAN-172/preregistration-e0b-e6-draft.md`) é a ÚNICA autoridade —
  5 kills quantificados lá (escapes ≥A+2/30 rounds; falso-bloqueio C
  >15%; cascata p95 >2min; f≥30% com minutos-humano <5% = NEGATIVO;
  fora-do-dossiê caindo >30% na mesma janela = aborta). Este corpo
  não duplica números para não divergir.** O kill do NEGATIVO
  resolve com dado a divergência entre lanes (academia otimista ×
  Codex cético × Grok "verifier theater").

### E3 — INTOCADO (pré-registro W5 assinado é IMUTÁVEL; execução = PLAN-170)
**Nenhum ajuste entra no E3** (Codex r1, P1: emendar pré-registro
assinado é ilegal). Os refinamentos sugeridos pela pesquisa —
single-pass (multi-turn infla FP; fonte no archive S298),
heterogeneidade real de vendor/papel, métrica horas-de-adjudicação
por achado confirmado — ficam registrados como **E3b: follow-on com
pré-registro PRÓPRIO e assinatura própria**, financiado apenas se os
resultados do E3 motivarem.

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

- **W-DH — delta-hold (a maior alavanca única).** Mecânica: o hold só
  reinicia para a superfície que MUDOU; crédito do tempo decorrido
  quando `inputs_hash` é idêntico (a rc.3 declarou hash idêntico ao da
  rc.2 e reiniciou 24h do zero) — ou hold concorrente com o re-pass.
  Infraestrutura (inputs_hash, delta_manifest) já computada e assinada.
  **Formalização (Codex r1):** só é legal via (a) emenda ADR-103
  ACEITA por cerimônia própria E (b) emenda do W6.2 do PLAN-169 (que
  pina hold→re-pass) pelo processo de amendment. Invariantes: hold
  NUNCA reduzido para superfície mudada; fronteira irreversível
  intacta; delta derivado exclusivamente do delta_manifest ASSINADO.
  **Fallback:** sem emenda aceita antes da v1.4.0-rc.1, o trem roda
  sob ADR-103 vigente, sem exceção ad-hoc. **Hipótese H-DH (nunca
  claim): redução de 24-48h por trem multi-rc — a validar no
  primeiro trem sob a emenda.**
- **E5 ganha substrato definido:** background-rail (rounds Codex
  detached via run_in_background/Monitor — padrão S285 virando skill;
  **hipótese H-BG, a validar:** 38 rounds seriais ~8h → ~3-4h com 2
  lanes, com wall-clock efetivo tendendo a baixo porque o CEO segue
  autorando) + cross-session SendMessage
  (v2.1.224) para WIP=2 entre sessões com worktree próprio; spike
  curto de sandbox antes de fechar design.
- **E6 nasce risk-tiered com M3 como estágio-1.** M3 = "Distância de
  Irreversibilidade" (conceito novo, inventor S302): risco como
  gradiente DERIVADO do grafo de alcance até sinks irreversíveis
  (tag/publish/GPG/HMAC/settings), nunca classificado à mão; arestas
  desconhecidas colapsam para d=1 (conservador); d≤1 ⇒ cerimônia
  síncrona integral sempre. Validação barata: replay read-only dos 14
  planos do E0 — **kill pré-registrado com corte numérico (Codex r1):
  se >40% dos P0/P1 históricos caírem no tercil de MAIOR d, o
  gradiente não separa risco ⇒ o grafo é proxy errado e M3 morre.**
  Complemento: classificar
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
- **Separar DESCOBERTA de VERIFICAÇÃO-DE-CURA:** descoberta = k
  revisores cegos sobre pack congelado (desenho do E3 COMO
  PRÉ-REGISTRADO; o refinamento single-pass pertence ao E3b); verificação
  = serial mas SÓ sobre o delta da cura, veredito amarrado a base
  SHA + diff hash; passe final de integração permanece (os melhores
  achados são cross-artefato).
- **Webhook/cron de hold-vencido + CI-verde** (notificação, nunca
  execução) — comprime o lag Owner-volta-ao-teclado dentro dos 59%.
- **Progressive disclosure do boot** (ceo-orchestration/SKILL.md
  ~15,6k tok ≈ 40% do Gate-1/2).

**HIPÓTESES pré-registráveis (Codex r1: nunca claims; nenhuma
superfície pública de doc herda estes números até evidência; o
no-speed-claim do AGENTS.md segue incondicional):** H-REV: reviewer
externo ~12-17h/trem → ~4-6h; H-RND: rounds −50-70%; H-DH: hold
−24-48h. Advertência da academia: fracionar ganha LATÊNCIA, não
yield — a hipótese certa é "mesmos achados, antes, com ~1/3 do
wall-clock", nunca "mais achados".

**W-IM — imediatos COM DONO (primeira wave deste plano; Codex r1:
mudanças de release-rail/gate/manifesto exigem Plan→Debate→Execute —
nada de "sem plano"):** cada item entra como sub-item L2 (gate
normal) ou L3 (debate) desta wave: shift-left do escopo de release no
rail da rc (re-pass vira delta-check) [L3]; derivação de contagens
(elevar itens #3/#4/#6 do ledger 169 p/ "derivar a classe") [L2];
stop-rule no template run-*-review.sh [L2]; varredura substrate-drift
(matchers exact-match v2.1.195, exit-2+JSON v2.1.214) [L2 read-only];
rota batch P2 + Merkle-manifest por lote [L3]; sweep de atualidade
das skills [L2 — executa aqui, regra de poda pertence ao PLAN-175].

**M1 (loteria de aceitação com cascata de contaminação) NÃO entra
aqui:** muda o CONTRATO de garantia (exaustivo → estatístico-com-
bound) — plano próprio pós-172 com ADR + ratificação do Owner. M2
(revisor residente com dívida de cobertura + mutantes-sentinela)
entra como candidato do E5/E6 v2 APÓS o replay hunk-vs-composição.

## 5. Pronto-para-execução (S302e)

**Pré-registro:** o draft do pré-registro E0b+E6 (hipóteses, braços,
kill tables, regras de precedência de etiquetas, inputs impressos)
está em `PLAN-172/preregistration-e0b-e6-draft.md` — assinatura do
Owner o congela ANTES do primeiro dado coletado. E5 ganha pré-registro
próprio só se E0b liberar (célula da tabela §1).

**Ordem interna executável:** (1) W-IM em lotes L2 primeiro (cada
item com gate normal; os L3 esperam `/debate`); (2) E0b: assinar
pré-registro → rodar etiquetagem retrospectiva (o script deriva de
`e0-serial-fraction.py`, que já imprime inputs) → tabela §1 decide
E5; (3) replay M3 (read-only, 1 sessão) — mata ou financia o
estágio-1 do E6; (4) W-DH: rascunho das DUAS emendas (ADR-103 +
PLAN-169 W6.2) → debate → cerimônia; (5) E6 conforme telemetria.

**ACs de fechamento por item:** W-IM = cada sub-item com evidência de
gate verde no commit que o landa; E0b = relatório com inputs + célula
da tabela marcada; M3 = verdito kill/financia com o corte de 40%
aplicado; W-DH = emendas aceitas OU fallback documentado ativado; E6
= relatório com TODOS os kills da kill-table do pré-registro
avaliados (a tabela do anexo é a autoridade, não uma contagem aqui);
E5 = só nasce com pré-registro assinado + PLAN-171 W5 verde.

**Debate:** pair-rail Codex r1→r3 APPROVE (S302c) cobre o conjunto;
`/debate start PLAN-172` no início da execução cobre o Gate 3; as
emendas do W-DH têm debate PRÓPRIO (mudam ADR + plano assinado).

### Registro de execução — W-IM#4 varredura substrate-drift (S316, 2026-08-20)

Sub-item `[L2 read-only]` executado com o instrumento permanente da
classe (`check-substrate-watch.py`, PLAN-135 O12 / nightly-hygiene
dim. vii). Resultado, com exit VERDADEIRO capturado sem pipe (lição
`pytest|tail`):

- `--json`: `status=current` contra o ledger, `fail_open=false`,
  `source_stale=false`.
- `--probe-installed --check`: **exit 1 — DRIFT em 4 componentes**:
  claude_code 2.1.198→2.1.237, codex_cli 0.144.1→0.147.0,
  codex_harness 0.139.0→0.147.0, cc_native_usage 2.1.232→2.1.237.
  Os dois codex carregam o runbook ADR-182 (pin-first + fixture
  re-record); claude_code/cc_native carregam "re-run
  verify-the-knob-routes".
- **Os dois alvos nomeados do item:** matchers exact-match **v2.1.195
  ≤ last_seen 2.1.198** ⇒ já reconciliado no ledger quando o item foi
  escrito; exit-2+JSON **v2.1.214 > last_seen 2.1.198** ⇒ pendente de
  reconciliação no LEDGER, mas com evidência comportamental na
  2.1.237: o probe da W4/169 (S315) re-capturou o enum de hooks e o
  achou IDÊNTICO ao da 2.1.220 (31 eventos, mesma ordem).
- Corroboração independente no mesmo dia: nightly-hygiene
  `wf_a740c4c1-458` dim. vii reportou o mesmo drift (yellow).

**Estado do item: varredura EXECUTADA e publicada; gate `--check`
vermelho por construção até o refresh do ledger** — que é PENDING-OWNER
por design (a receita `--refresh` exige WebFetch das fontes e cada
drift tem runbook próprio; bump cego de `last_seen` sem executar os
runbooks recriaria a classe "instrumento verde com pergunta
envelhecida"). O item FECHA quando o Owner rodar a receita + dispuser
os 4 runbooks (ou registrar waiver por componente).

## 6. Anexo S305 — fundamentação externa (advisory; NÃO altera pré-registros)

Pesquisa academia-vs-framework S305; fonte única das referências e
números: `PLAN-178/research-S305.md` (números de literatura NÃO entram
neste corpo — doutrina §3). O que ela muda AQUI: nada de escopo; só
fundamentação e prioridade relativa.

- **E6 (cascata de filtros):** a família cascade/routing é a mais bem
  documentada da varredura (linha 5 da tabela S305) — reforça E6 como
  o experimento de melhor razão evidência-externa/custo do trem. Kill
  table intacta; o pré-registro segue a única autoridade.
- **Circuit-breaker do tiering (§4):** a literatura de multi-agent
  debate (linha 11) converge com a lição-mãe S296 — saturação em
  poucas rodadas + afunilamento por amostragem dependente. O mecanismo
  já landado aqui fica com validação externa registrada.
- **Gate barato do §2 (best-of-N):** ganha motivação da linha 4
  (escalar verificadores > escalar builders). Execução do gate
  permanece DESTE plano; PLAN-178 apenas cruza a referência.
- **E3: INTOCADO** — nada deste anexo emenda pré-registro assinado.
