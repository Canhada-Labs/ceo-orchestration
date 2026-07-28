---
plan: PLAN-163
round: 1
created_at: 2026-07-27
critiques: [Critic-A, Critic-B, Critic-C]
verdicts: [ADJUST, ADJUST, ADJUST]
round_verdict: PROCEED
consensus_adjustments: 14
---

# PLAN-163 round-1 consensus

Três ADJUST, zero REJECT, VETO não exercido. A forma (1 plano, 6 threads,
red-first no W1, pack canônico no padrão PLAN-160/161) é unanimemente
endossada. Duas premissas factuais do draft caíram na verificação (contagem
de event types; caracterização do G3/G5), um Check nasceria verde (vacuoso) e
o item do pin codex mirava o arquivo errado — por cima de um defeito de
atestação PRÉ-EXISTENTE (launcher-vs-payload) que o round descobriu e provou.
Verdict: **PROCEED após ajustes** — design-coherent; shipping autorizado
apenas pela verification cascade (V2 pair-rail + V3 Owner GPG), nunca pelo
debate.

## Consensus findings (2+ críticos)

- **CF-1 [A+B+C] Contagens erradas/hardcoded dentro do próprio plano.**
  São **13** event types (não 14) e 46 registrations hoje (47 `"type":
  "command"` − 1 statusLine); T3 leva a 48. Oracle do T2 deve derivar o
  conjunto de hooks do settings.json em runtime; Check do T3 com números
  explícitos; counts do CLAUDE.md mudam no closeout obrigatoriamente.
- **CF-2 [A+C] Check do G3 nasce VERDE (vacuoso).** As ocorrências
  `opus-4-7` citadas são carriers históricos allowlisted no parity ou
  referência a filename. O defeito REAL é de PRESENÇA: `_PRICING_PER_MTOK`
  (audit-telemetry.py:40-46) não tem opus-4-8 NEM fable-5; detectors
  (`_LARGE_MODELS`) não têm fable-5. Fix presence-based e ADITIVO (replay
  ADR-142 proíbe remover linhas históricas); display-map é cosmético;
  docstrings do profiler são decisão separada; team.md tem DUAS linhas
  drifted (:578 e :589); path do parity é `scripts/local/`.
- **CF-3 [A+B(+C endossa pin=1)] Depth pin exige probes, e a premissa do G5
  é falsa.** Existe Rail 2 depth-fence (`check_agent_spawn.py:1822-1833`) —
  advisory, alimentado por sinais COOPERATIVOS; nesting nativo não os
  carrega. Probes exigidos: (i) nome/semântica do env var verificados contra
  o binário (classe S218); (ii) probe de NEGAÇÃO (pin seta → spawn aninhado
  negado); (iii) hook-coverage em depth-2 (PreToolUse dispara para Task de
  subagente?); (iv) regressão dos 3 instrumentos Workflow (council-audit,
  audit-fanout, nightly-hygiene) sob o pin.
- **CF-4 [A+B+C] T5 (pin codex) mal-escopado + mecanismo de atestação
  furado.** Semver `>=0.128.0,<0.145.0` JÁ cobre 0.144.6; o arquivo que muda
  é `codex-cli-binary-sha256.txt`. E o sha atual atesta o LAUNCHER Node
  (`bin/codex.js`) — provado: sha idêntico pré/pós upgrade 0.144.1→0.144.6 →
  o gate deixou passar um bump sem cerimônia e deixaria passar payload
  adulterado. Fix: emenda ADR-111 para atestar o payload RESOLVIDO (sha
  por-arch do binário nativo ou manifest-hash npm) + re-record fixtures +
  checklist ADR-161 + eleição catch_rate. Ordem declarada: cerimônia ADR-111
  do pin PRIMEIRO; pack W3 revisado sob o pin novo (são DUAS cerimônias —
  honestidade na thesis).
- **CF-5 [B+C] T2 oracle subespecificado nos pontos que já queimaram.**
  (i) CI não tem o binário `claude` → schema 2.1.220 extraído vira ARTEFATO
  versionado (stamp+sha256+recipe), oracle valida contra o snapshot; job
  próprio no validate.yml com timeout + pre-push. (ii) Blocks intencionais
  são stdout-JSON exit-0 (verificado ao vivo no 2.1.220); a superfície nova
  do 2.1.214 é exit-2 ACIDENTAL — 3 hooks wired importam argparse
  (check_harness_config, emit_architect_outcome, policy_dispatch) e argparse
  faz `sys.exit(2)` em erro de argv → oracle asserta EXIT CODES + caso
  sintético argv-inesperado; fix SystemExit→`{}` (fail-open on
  infrastructure). Caso de block só onde caminho de block existe.
- **CF-6 [A+C] Sonnet-5 em `availableModels` flipa o default de sessão.**
  O `_enforce_available_models_comment` documenta a resolução de default; o
  tier default do CC é sonnet-5 desde 2.1.197. Adicionar à allowlist antes
  do re-baseline mata a OQ2. Fix: T1.1 verifica a semântica no 2.1.220
  (via diff de schema do T2, incluindo o fail-open documentado da chave);
  entrada sonnet-5 migra para pós-baseline OU pina o default de sessão
  explicitamente no mesmo commit.
- **CF-7 [C, endossado por A via disciplina de cerimônia] Superfícies
  shipped exigem oracles de upgrade.** availableModels, defaultMode e
  registrations viajam a adopters: oracles no smoke-install.yml (padrão
  PLAN-161 U1-U3), pós-install E pós-upgrade.
- **CF-8 [A, estruturalmente assumido por B] V2 está RED agora.** pair_rail
  fail-opened 11/11 na janela de 168h; restauração (PLAN-161 Passo 4 /
  expiração ≈2026-08-03) vira GATE NOMEADO antes do review do pack W3.
- **CF-9 [A+B] DirectoryAdded: provar blockability antes de prometer
  hardblock; e hardblock-FLOOR para roots sensíveis.** Roots sensíveis
  (raiz de `$HOME`, `~/.claude/`, `.claude/` de repo alheio, ancestrais do
  project dir) bloqueiam independente do env opt-in; se o evento for
  notification-only, o enforcement migra para os guards PreToolUse de
  escrita; payload de Notification segue no-value-echo; dogfood deste repo
  liga `CEO_DIRADD_HARDBLOCK=1`.
- **CF-10 [A+C] Protocolo de medição do T4 pré-registrado e cobrindo as 3
  justificativas do cap.** ≥200 amostras/nível (classe PLAN-159), máquina/
  carga declaradas, percentil+threshold exatos, workload shape PLAN-083;
  cap novo só com as TRÊS bases (flock, git index lock, budget-guard tally)
  re-validadas OU escopado a fan-outs read-only (mantendo 6 p/ staging);
  edit da skill declara o rail de governança (SP-NNN ou scope do sentinel).
- **CF-11 [B+C] `STALE_RE += claude-opus-4-1` exige deltas de allowlist
  enumerados ANTES** (model-deprecations.json, check-model-deprecations.py,
  .claude/data/canonical_models.json) — senão o parity cai; promover de
  "avaliar" para executar (retirement 2026-08-05 dentro do horizonte).

## Single-critic insights KEPT

- **[B] ADR-181 com critério de sunset** para opus-4-8 no VETO floor
  (evento pós-migração, ADR-095) + nota de que a bijeção de floor NÃO cobre
  o caminho de runtime-fallback (`fallbackModel`).
- **[B] Probe advisory de sha por-invocação** no rail vivo (janela entre
  upgrades locais e cerimônias hoje fica sem sinal) — vira nice-to-have do
  T5.
- **[B] Nota SlashCommand** no ADR do T3 (muda o modelo de ameaça do
  /add-dir de "só humano" para "agente pode invocar").
- **[C] Grok probe = `_PROBE_ARGV`** (o ledger TEM a entry; falta o probe de
  código) — precisão no T5.1.
- **[C] Registrar resultado do probe MCP mesmo se dormente** (T2.4).
- **[C] Perf-gate `opus-4-7-profiler-smoke` fora de escopo EXPLÍCITO** —
  required checks de branch protection acoplam ao NOME do job; rename é
  follow-up coordenado, nunca grep-fix.
- **[A] Sweep de counts nos docs não-vigiados** (ARCHITECTURE/GUIA/FAQ/
  npm-README) no T6.
- **[A] Pré-autorizar 4ª sessão** no budget.
- **[A+C] Nota de honestidade do tokenizer**: re-baseline completo de
  budgets shipped (166 skills, DEBATE-SCHEMA §9, templates) é follow-up
  plan, não item deste.

## Single-critic insights REJECTED / DEFERRED

- **[B] Ligar `sandbox.network.strictAllowlist`/`disableAutoMode` neste
  repo (dogfood)** — DEFERRED para OQ5 como opção (c); decisão do Owner
  (muda o perfil operacional da sessão CEO, não só template).
- **[C] Fallback soak (manter opus-4-8 como fallbackModel)** — ACEITO
  parcialmente: vira sub-opção da OQ1 em vez de decisão fechada.

## Plan adjustments (índice — edits aplicados no arquivo do plano)

1. G4/G7: 14→13 event types; G5 reescrito citando Rail 2 depth-fence.
2. T1.1: verificação da semântica default-resolution + contingência sonnet-5
   (pós-baseline OU pin explícito de default no mesmo commit) [CF-6].
3. T1.5/T1.6: fix presence-based + aditivo; fable-5 nos detectors; duas
   linhas team.md; disposições por evidência corrigidas [CF-2].
4. T1.7: deltas de allowlist enumerados antes do STALE_RE; promovido a
   executar [CF-11].
5. T2: artefato de schema versionado + job CI próprio + exit-codes +
   argv-case + SystemExit→{} + lista derivada + MCP probe registrado [CF-5].
6. T3: probe de blockability primeiro; hardblock-floor de roots sensíveis;
   fallback p/ write-guards; no-value-echo; dogfood hardblock; Check 48
   explícito [CF-9, CF-1].
7. T4.1: protocolo pré-registrado (≥200/nível etc.) + 3 justificativas +
   rail de governança do SKILL.md edit [CF-10].
8. T4.3: 4 probes de depth (env-var verbatim, negação, hook-coverage
   depth-2, regressão dos 3 instrumentos) [CF-3].
9. T5.2: reescopo para sha-payload + emenda ADR-111 (launcher-vs-payload) +
   ordem das DUAS cerimônias declarada [CF-4].
10. Novo gate nomeado pré-W3: pair_rail liveness saudável [CF-8].
11. T3/T5: oracles smoke-install pós-install/pós-upgrade [CF-7].
12. T6: CLAUDE.md counts obrigatório no closeout; docs não-vigiados;
    nota tokenizer; perf-gate rename OUT-OF-SCOPE explícito.
13. ADR-181: sunset opus-4-8 + nota runtime-fallback; ADR do T3 com nota
    SlashCommand.
14. OQ1 ganha sub-opção fallback-soak; OQ5 ganha opção (c) dogfood-enable;
    budget pré-autoriza 4ª sessão.

## Round verdict

**PROCEED** — design-coherent após os 14 ajustes. Sem contradições entre
críticos; nenhum VETO. Não autoriza shipping: V2 (pair-rail, sob gate CF-8)
e V3 (Owner GPG) permanecem os únicos gates de verdade.
