---
id: PLAN-178
title: Method currency — auditoria MAST-14 + injeção inter-agente, adoção de substrato 2026, e regras derivadas da pesquisa S305
status: draft
created: 2026-08-13
owner: CEO
depends_on: []
budget_tokens: 150-300k (W0 60-100k; W1 50-120k; W2 20-40k; W3 20-40k)
budget_sessions: 2-3
context_risk: low
external_wait: "nenhum — Owner autorizou execução pré-rc.4 (S305). Nenhuma wave toca superfície canônica sem cerimônia própria."
tags: [research, governance-audit, substrate, security, seed]
---

# PLAN-178 — Method currency: fechar os gaps que a pesquisa S305 achou

> **SEMENTE (S305, 2026-08-13).** Duas rodadas de pesquisa
> academia-vs-framework (gauntlet-loop S304 + varredura completa S305).
> Autoridade das referências: `PLAN-178/research-S305.md` (fonte
> ÚNICA; planos apontam, nunca duplicam números — lição 3× "cura no
> corpo ≠ referências"). Conclusão central: o framework já implementa
> a versão forte da maioria das famílias (cross-vendor > fresh-context;
> MEA ≈ Plan→Execute→Verify); os gaps reais são QUATRO e cabem aqui.
> Dono único: itens que fundamentam planos existentes (E6/cascata →
> 172; context-reframe → 175; T/P → 176) moram NAQUELES planos — este
> plano NÃO os re-executa.

## Context

- A classe de falha dominante da literatura (MAST: spec-ambiguity +
  coordenação = 79%) é exatamente a que nossos gates atacam — mas
  nunca mapeamos formalmente check-a-check contra os 14 modos.
- A literatura de segurança inter-agente documenta o confused deputy
  entre agentes (injeção via par "confiável" com taxa de sucesso muito
  superior à direta). Nossos scanners (injection_patterns, shards
  ADR-141 como DADO) cobrem parte; a classe "trust propagation entre
  spawns" não tem auditoria dedicada.
- O substrato Claude Code 2026 (versão que o Owner instalou) traz
  features que o framework usa parcialmente (Workflow em 4 skills) ou
  ignora (cost-attribution nativa, scoped permissions, nested
  subagents, dreaming). Substrate-watch vigia DRIFT, não ADOÇÃO.
- Da análise gauntlet (S304): 2 regras extraíveis com respaldo
  empírico ainda vivem só em memória, não em protocolo.

## Waves

### W0 — Auditoria MAST-14 + injeção inter-agente (L2, read-only, 1 sessão)

Mapear os 14 modos de falha MAST + as classes de injeção inter-agente
(confused deputy, trust-authorization mismatch, contágio via shared
memory) contra nossos controles, com evidência arquivo:linha para cada
célula (coberto / parcial / gap). Formato: shards ADR-141; agentes não
escrevem arquivo (confinamento ADR-136-AMEND-1); relatório é retorno.

- Saída: `PLAN-178/mast-coverage-table.md` (escrito pelo CEO a partir
  dos shards) — tabela 14+N linhas × {controle, evidência, status}.
- Cada GAP acionável vira item L2/L3 com dono proposto (aqui ou em
  plano existente — sem double-booking).
- **Positive control da auditoria:** injetar 1 modo sabidamente
  coberto (ex.: spawn sem FILE ASSIGNMENT ⇒ check_agent_spawn bloqueia
  — live-fire, não fixture) e 1 sabidamente NÃO coberto (esperado:
  gap) — auditoria que dá "tudo verde" sem controle é instrumento com
  pergunta envelhecida.
- Kill: se a tabela der 100% coberto SEM nenhum gap, parar e
  desconfiar do instrumento (lição feedback-instrument-green).

### W1 — Adoção de substrato 2026 (L2 por item; qualquer wiring novo em settings = L3)

Triage das features novas, cada uma com PROBE live-fire primeiro
(disciplina W4.1.0/W4.2.0 do PLAN-169 — evidência antes de doc):

1. **Workflow para fan-outs recorrentes [L2]:** migrar 1 fan-out
   piloto hoje espontâneo (candidato: o re-pass de release, hoje
   script + agentes ad-hoc) para Workflow determinístico
   (pipeline/resume/budget). **Gate de governança ANTES da migração:**
   positive control provando que `check_agent_spawn.py` dispara também
   no caminho Workflow-agent; se NÃO disparar, isso é um GAP W0 e a
   migração fica bloqueada até a cura (fail-closed).
2. **Cost-attribution nativa [L2]:** `agent-budget` passa a consumir a
   telemetria por-agente do harness quando disponível, com fallback no
   audit-log (nunca substituição silenciosa — as duas fontes impressas
   lado a lado por 1 janela de validação).
3. **Scoped permissions em spawns [L3 — toca settings]:** defesa em
   profundidade sob os hooks existentes; probe primeiro (o que o
   scope nativo REALMENTE bloqueia vs o que o hook bloqueia); só
   depois desenho. Cerimônia própria se tocar `.claude/settings.json`.
4. **Nested subagents + agent teams: ESTUDO apenas [L2 read-only].**
   Teams full-mesh fica FORA (MAST: coordenação é onde quebra; lição
   S284 clobber). Saída = memo go/no-go com condições.

### W2 — Regras derivadas da pesquisa (L2, docs de protocolo; advisory até ratificação)

1. **Critic fresco por retry** nos re-passes internos Claude-side:
   emenda ao texto do `/debate` e do template `run-*-review.sh` — o
   agente que criticou o draft N não re-julga o N+1 (Codex já é fresco
   por processo; a regra fecha o lado Claude).
2. **Barra-por-exemplar para superfícies de prosa** (README,
   announcement kit): o revisor compara contra 1 exemplar real
   nomeado, às cegas, em vez de rubrica abstrata.
3. **Registro de fronteira:** doutrina verificador-primeiro
   (candidatos paralelos > rodadas seriais) fica REGISTRADA como
   motivação do gate barato §2/PLAN-172 — execução mora lá; teto de
   rodadas já é mecanismo no tiering §4/PLAN-172. Este plano não
   duplica.

### W3 — Estudo dreaming/curadoria de memória (L2 read-only, 1 sessão)

Avaliar a curadoria de memória agendada do substrato ("dreaming")
contra o gated-learning loop do PLAN-154 (default-OFF por design):
sobreposição, fronteira de confiança (memória é superfície de injeção
— render como DADO, nunca instrução), e se ativação parcial do
PLAN-154 (CEO_LEARNING_BOOT_LESSONS=1) é melhor que adotar o nativo.
Saída = memo com recomendação; qualquer ativação é decisão do Owner.

## Acceptance criteria

- [ ] AC-1 [P0] Tabela MAST+injeção completa com evidência
      arquivo:linha por célula E os 2 positive controls executados
      (1 coberto live-fire, 1 gap esperado). Tudo-verde-sem-gap ⇒
      FALHA do AC (instrumento suspeito).
- [ ] AC-2 [P0] Migração Workflow do piloto SÓ com o positive control
      de `check_agent_spawn` no caminho Workflow provado ANTES; se
      gap, migração bloqueada + gap registrado no W0.
- [ ] AC-3 [P1] agent-budget imprime as DUAS fontes (nativa + audit-log)
      na janela de validação; divergência >10% investigada antes de
      qualquer switch de fonte.
- [ ] AC-4 [P1] Regras W2 landadas nos docs de protocolo com diff
      mínimo e marcadas ADVISORY até ratificação do Owner.
- [ ] AC-5 [P2] Memos W1.4 e W3 entregues com recomendação explícita
      go/no-go + condições.

## Guard-rails

- Read-only por padrão; NENHUMA superfície canônica muda sem cerimônia
  própria (W1.3 é o único candidato e é L3 explícito).
- Referências/números de literatura só em `research-S305.md` — corpo
  de plano e docs públicos não herdam números (doutrina §3/PLAN-172).
- Sem double-booking: cascata→172/176, context-reframe→175,
  best-of-N-gate→172 §2, fleet-currency→176. Este plano só cruza
  referências.
- Toda env nova em `env-inventory.json` no mesmo commit (R-SEC12).

## Debate

L3 pelo conjunto (W1.3 toca settings; W1.1 muda caminho de spawn de
release): `/debate start PLAN-178` obrigatório antes do W1. W0 pode
executar direto (read-only + shards).
