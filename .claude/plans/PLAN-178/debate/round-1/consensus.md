---
plan: PLAN-178
round: 1
round_verdict: PROCEED
rounds_synthesized: 1
agents_considered: [Critic-A, Critic-B, Critic-C]
verdicts: [ADJUST, ADJUST, ADJUST]
consensus_adjustments: 9
decisions_revised_in_plan: [W1.1, W1.2, W1.3, W2.1, W-C(novo), Guard-rails, AC-2, AC-2b, AC-2c, AC-3, AC-6, AC-7, Debate]
synthesized_at: 2026-08-13
synthesized_by: CEO (texto anonimizado; mapa em anonymization-map.md)
created_at: 2026-08-13
---

# PLAN-178 — Consenso do round 1

> 3× ADJUST convergentes; nenhuma contradição irreconciliável. Verdito
> **PROCEED (design-coherent) com as emendas abaixo aplicadas ao
> plano**. Lembrete de escopo: design-coherent NÃO autoriza shipping —
> só a cascata V0-V3.

## Consensus findings (≥2 críticos)

1. **Reagrupar o lote de curas por CANONICIDADE, não severidade**
   (A must-fix 3; B must-fix 1). Verificado contra
   `check_canonical_edit.py`: C1 (hooks), C2 (workflows/*.js!), C5 +
   W1.3 (settings.json) são canônicos ⇒ UM pack GPG (Lote B); C3+C4
   (ceo-boot.py) não são ⇒ PR normal (Lote A). C2 NÃO é "cura barata".
2. **C1 é pré-requisito DURO de armar `CEO_SPAWN_OVERLAP_GUARD`**
   (B R-SEC1: antes de C1, o guard pune só o compliant e a omissão
   degrada o detector para a sessão inteira; A unseen 3: "C1 e
   C5-overlap são UM item"). Vira aresta de dependência nos ACs.
3. **Enforcement write-time de FILE ASSIGNMENT: NÃO construir**
   (B R-SEC2: não existe primitivo de identidade de agente que cruze a
   fronteira de spawn — trusted_env é "NEVER ship across spawn
   boundaries" por invariante; A 8b: seria oráculo do mesmo lado da
   fronteira, classe já registrada). C1 fecha a CLAIM, não o INJ-4;
   INJ-4 fecha no W1.3 (se o probe provar) ou vira residual declarado.
4. **Piloto W1.1 ≠ re-pass de release** (C achado 1: o re-pass nem usa
   Task tool — é bash+codex subprocess — e é o maior blast radius do
   repo; A must-fix 9). **Piloto escolhido: a RE-AUDITORIA MAST via
   Workflow** — read-only, recorrente, e transforma a tabela W0 de
   foto em instrumento (fecha também o R-VP8 de A).
5. **AC-2 reenquadrado: o gap do rail Workflow é VIVO, não
   pré-condição** (B unseen 1: as 4 skills Workflow shipadas já rodam
   agentes sem protocolo; A must-fix 2 + evidência preliminar
   PLAN-169:470-476; CONFIRMADO pelo probe live-fire
   `wf_d7af49d9`: blocked=false). Ramo negativo escrito: migração de
   fan-out que ESCREVE fica proibida até gate existir; piloto
   read-only prossegue COM validador pré-despacho no script.
6. **C5 = measure-first, por item** (B must-fix 5-6 com tabela por
   detector; A nice 2 com ordem; C achado 4). Nenhum flip sem contagem
   would-block do audit-log em janela nomeada (≥30d ou ≥20 sessões) +
   triagem TP/FP por disparo. `CEO_SUBAGENT_FABRICATION_BLOCK` não
   bloqueia (nome mente) — não conta como controle.
7. **C3 exige controle positivo próprio + waiver marker** (B must-fix
   10: lint de vacuidade sem fixture vacuoso é a própria doença;
   C achado 3: `# CEO-INFORMATIONAL-ONLY` espelhando `# CEO-DEBT:`).
   Protótipo v1 do CEO já mostrou: regra "discrimina ≥2 status" acha 8
   candidatos mas NÃO pega o caso canônico — a cura são as duas pernas
   (lint R1 + positive control por check R2).
8. **Reversibilidade por item adotado do W1** (A must-fix 4:
   fingerprint do probe + fallback + entrada no substrate-watch;
   B must-fix 4: probe de 5 casos do W1.3 incl. fuga-por-Bash e
   managed-policy quebrada; C: probes têm de IMPRIMIR evidência).
   O W1.2 (duas fontes + limiar) vira o TEMPLATE dos demais.
9. **Fronteira PLAN-178 ↔ PLAN-169 W4/W4-C declarada item a item**
   (A R-VP1 CRITICAL — o guard-rail omitia justamente o 169):
   probes de Workflow → 169 W0.0/W4.2.0 é DONO, o 178 consome;
   W1.3/settings nas 4 superfícies → decidir absorção no W4-C na
   abertura do Lote B; W1.2/W1.4 → 178. Tensão de direção nomeada:
   adopter default fail-closed (`disableWorkflows`) COEXISTE com
   dogfood supervisionado — decisão registrada por escrito.

## Single-agent insights KEPT

- (A R-VP5) Freeze mecânico do GA-CUT: resolvido por SEQUÊNCIA — os
  arquivos do 178 landam ANTES do corte da rc.4, logo entram DENTRO da
  tag; o `OWNER-GA-CUT-rc4.sh` retargetado (W2/PLAN-177) computa o
  delta a partir da rc.4. Invariante registrado no plano: NADA landa
  entre a tag rc.4 e o GA. A frase "freeze relaxado" substituída pela
  análise mecânica.
- (A R-VP6) W2.1 retargetado: não existe template vivo
  `run-*-review.sh`; a regra de critic-fresco landa em
  `DEBATE-SCHEMA.md` + `commands/debate.md` (PR normal); a linha de
  PROTOCOL.md, SE ratificada, entra no Lote B.
- (A nice 3) ADR-191 para o C1 (mudança de contrato de aceite de
  spawn), dentro do Lote B.
- (B must-fix 3) CLAUDE.md:88: cumprir a parte cumprível (FILE
  ASSIGNMENT) E reescrever a frase com precisão (AGENT PROFILE é
  detector, não requisito) — edição no closeout (cache discipline).
- (B must-fix 8) ADR-089-AMEND-1 com gatilho OBSERVÁVEL (derivável de
  `emit_pattern_stored/queried`: ≥2 papéis no mesmo tópico na janela)
  + fence barato no retorno do `query()`.
- (B must-fix 9) Rota de recuperação do C1 fail-closed nomeada e
  testada no mesmo commit (padrão ADR-186 / `CEO_SOTA_DISABLE=1`).
- (B unseen 3) `CEO_SPAWN_DEPTH_GUARD` (7º detector, rail 2) entra na
  tabela C5 — é pré-condição do estudo W1.4 (nested).
- (C achado 2) W1.2 estende o precedente do agent-budget Step 3b (O3);
  breakdown POR SPAWN; janela por N≥50 eventos; switch por divergência
  máxima POR CATEGORIA (opts.model é INERTE no Workflow — economics
  diferem por caminho).
- (C achado 4) env-inventory "no mesmo commit" não tem dente
  (validate.yml só ::warning) — W1 adota linguagem "deveria" OU escala
  o check para bloqueante escopado no diff (decisão na abertura do
  Lote B).
- (B nice 4) Pós-C1, rejeitar FILE ASSIGNMENT só-de-wildcard (a evasão
  migra de "omitir" para "declarar `*`").
- (B nice 1) Emitir `spawn_file_assignment_recorded` com path_count=0
  quando ausente — mede a omissão durante a transição.

## Single-agent insights REJECTED / DEFERRED

- (A nice 1 → ABSORVIDO no piloto W1.1): tabela-como-instrumento é o
  próprio piloto; não é item separado.
- (B R-SEC7 "18ª instância"): o rótulo fica, mas a contagem de
  instâncias da classe não entra no plano (métrica de memória, não AC).
- (C: escalar env-inventory p/ bloqueante JÁ): deferido para decisão
  na abertura do Lote B (não trivial: classe de FP própria).

## Plan adjustments (aplicados no arquivo do plano)

A1 Guard-rails ganham a fronteira 178↔169 item a item (+tensão
   direção adopter/dogfood).
A2 W1.1 reescrito: piloto = re-auditoria MAST; ramo negativo do AC-2;
   validador pré-despacho no script; migração de fan-out que escreve
   PROIBIDA até gate.
A3 W1.3 ganha o probe de 5 casos (B must-fix 4) + fingerprint/
   fallback/substrate-watch (A must-fix 4).
A4 Lote de curas reagrupado: Lote A (C3+C4, PR normal) e Lote B
   (C1+C2+C5-flips+W1.3+ADR-191 [+linha PROTOCOL.md se ratificada],
   UM pack GPG). C2 com semântica DEGRADED no cap + residual R-SEC4
   documentado.
A5 C5 vira tabela por detector com veredito B must-fix 6 + gate
   measure-first (B must-fix 5); +`CEO_SPAWN_DEPTH_GUARD`.
A6 W2.1 retargetado para DEBATE-SCHEMA.md + commands/debate.md.
A7 AC-2 ganha o desfecho real do probe (`wf_d7af49d9`) e o ramo
   vermelho; AC novo: aresta C1→overlap-guard.
A8 Freeze: análise mecânica substitui "Owner relaxou" (sequência
   land-antes-da-tag + retarget do GA-CUT; NADA entre tag e GA).
A9 C1: rota de recuperação nomeada + censo de callers (A must-fix 7)
   + janela advisory-com-audit antes do enforce.

## Verdict

**PROCEED** — design-coherent com A1-A9 aplicadas. Round 2 não é
necessário: os três críticos convergem e as divergências (piloto,
sequência C1/C5) foram resolvidas por evidência, não por voto.
