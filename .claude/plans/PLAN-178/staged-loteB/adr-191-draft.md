# ADR-191 (DRAFT — formaliza via cerimônia do Lote B/PLAN-178)

## Title
Spawn acceptance contract v2 — `## FILE ASSIGNMENT` obrigatório e
parseável em todo spawn nomeado; gramática reduzida para agentes de
workflow; fence obrigatório no ingest de retornos in-harness

## Status
DRAFT (proposto S305; aceita na cerimônia do Lote B)

## Context
- W0/PLAN-178 (tabela MAST + injeção): CLAUDE.md:88 prometia bloqueio
  de spawn sem FILE ASSIGNMENT; live-fire mostrou allow silencioso —
  o bloco era parseado só para o Rail 3 advisory, e a OMISSÃO removia
  o spawn da detecção de colisão da sessão inteira (R-SEC1).
- Censo de callers: o gerador canônico não emitia o bloco; os 4
  workflows shipados despacham `agent()` fora do gate de spawn (probe
  `wf_d7af49d9`: `blocked=false`).
- Retorno de subagente in-harness era interpolado CRU no prompt do
  consumidor (assimetria vs lanes externas — confused deputy).

## Decision
1. Spawn NOMEADO exige `## FILE ASSIGNMENT` parseável: ≥1 path
   concreto em `CAN edit:` OU a forma read-only explícita
   `CAN edit: NONE-READ-ONLY`. Bloco ausente ou só-de-wildcard =
   rejeição nomeada (após janela advisory medida; rota de recuperação
   testada no mesmo commit).
2. O gerador (`inject-agent-context.sh`) emite o bloco SEMPRE.
3. Agentes de rail Workflow usam gramática REDUZIDA validada
   PRÉ-despacho no próprio script (PROMPT DEFENSE ≥6 bullets + FILE
   ASSIGNMENT explícito + regras read-only); AGENT PROFILE/SKILL
   dispensados (purpose-built por design). [⚖️ confirmar na cerimônia]
4. Todo retorno de subagente consumido em prompt de outro agente é
   FENCED como dado + capped; truncamento envenena CLEAN da dimensão
   dona (nunca entra como achado limpo).
5. Capability autodeclarada não conta como controle (precedente
   check_worktree_writer; 3ª re-descoberta — agora doutrina escrita).
6. Limitação DECLARADA: enforcement write-time de FILE ASSIGNMENT não
   será construído — não existe primitivo de identidade de agente que
   atravesse a fronteira de spawn (trusted_env: "NEVER ship across
   spawn boundaries"); a autoridade residual do INJ-4 fecha por scoped
   permissions nativas (W1.3, se o probe de 5 casos provar) ou fica
   registrada como residual.

## Consequences
- (+) A claim de CLAUDE.md §4 volta a ser verdadeira (e é reescrita
  com precisão no closeout: AGENT PROFILE é detector, não requisito).
- (+) O detector de colisão (Rail 3) passa a ver TODOS os spawns;
  `CEO_SPAWN_OVERLAP_GUARD` ganha pré-condição satisfeita (AC-2b).
- (−) Callers ad-hoc quebram se omitirem o bloco após o flip — pago
  com a janela advisory + gerador curado + rota de recuperação.
- (−) Fence não reduz a autoridade que um ponteiro hostil DIRIGE
  (R-SEC4) — residual aceito e documentado.
