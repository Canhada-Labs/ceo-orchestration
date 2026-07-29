---
plan: PLAN-164
round: 1
rounds_synthesized: [round-1]
agents_considered: [vp-engineering, security-engineer, devops-engineer]
decisions_revised_in_plan:
  - "§Approach — ADR fixado como AMEND-1 do ADR-110 (interlock de contagem 181/183 com o pack congelado)"
  - "§Waves W0 — protocolo de medição EXECUTADO in-debate: N=9, p95=75,1s > 70s → escalada OQ1=120/OQ2=150"
  - "§Waves W1 — +5 ACs: teste de invariante, migração de upgrade de adopter, guard de aposentadoria do pin-pack, statusMessage+_comments, sequência do gêmeo baseline-antes-do-sync"
  - "§Waves W2 — mecânica da re-âncora corrigida (âncora pós-commit, commitada no closeout) + validação fail-closed do resolve_anchor + disciplina de freeze"
  - "§Open questions — OQ1-OQ4 re-drafted com condições dos críticos incorporadas"
synthesized_at: 2026-07-29T18:20:00Z
synthesized_by: CEO
---

# PLAN-164 — consenso round 1

Insumo: críticas anonimizadas (Critic-A/B/C; mapa em `anonymization-map.md`).
Verditos: **3× ADJUST** — nenhum critic rejeitou a premissa (uplift + cerimônia
única + re-âncora); todos os must-fixes são incorporáveis por edição do plano.

## Consensus findings (2+ agents flagged)

1. **C1 — `resolve_anchor()` deve validar a âncora como ponteiro, fail-closed**
   (Critic-A, Critic-B; Critic-C documentou a direção-segura do fallback).
   Severidade: ALTA (superfície de laundering de fail-opens; dual-source
   divergente pós-re-âncora). Mitigação acordada: `ts` derivado de
   `git log -1 --format=%cI <sha>` (nunca lido do arquivo); `sha` deve
   resolver a commit existente com tag sentinel (`[SENT-PLAN163-PIN]` OU
   `[SENT-PLAN164-RAIL]`, preferindo o mais novo — o fallback git-log ganha
   a mesma dupla); qualquer falha → die. Fix no mesmo commit da cerimônia
   (script vive em `PLAN-163/`, não-canônico). → W2.
2. **C2 — invariante entre camadas como TESTE mecânico** (A, B, C — os três).
   Severidade: ALTA (é a classe que reintroduz hook-kill por flip
   unilateral). Mitigação: teste que parseia `settings.json`,
   `settings.base.json` e o default literal do hook e asserta
   (a) registration kernel == registration template;
   (b) `registration ≥ interno + 30`. Roda na suíte E no overlay do
   preflight do pack. → W1.
3. **C3 — delta-review do pack prova a NEGATIVA com evidência mecânica**
   (A, B; C travou a ordem). Severidade: ALTA (janela de contrabando no
   recompute). Mitigação: commitar o gêmeo `inputs-pack.sha256` do estado
   R6 ATUAL antes do sync (baseline — o gêmeo NÃO existe hoje, verificado);
   aplicar delta → recomputar → delta-review sobre bytes FINAIS → regenerar
   gêmeo → 2º commit; diff dos gêmeos limitado às entradas pretendidas
   (linha extra = abort); sha antigo→novo por arquivo registrado no
   artefato de review. → W1, com a sequência de Critic-C (R6) como ordem
   NORMATIVA.
4. **C4 — literais velhos em packs staged / máquina de upgrade** (B provou o
   pin-pack por manifest; C provou o merge aditivo do upgrade.sh; A pediu o
   sweep repo-inteiro+staged). Severidade: ALTA (reversão silenciosa do fix
   com preflight verde; adopter em hook-kill invisível). Mitigação em 3
   partes: (i) guard de aposentadoria no APPLY do `land-plan163-pin.sh`
   (die se `[SENT-PLAN164-RAIL]` existe no log; `--gate-v2` continua
   válido) — menor que re-sync do pin-pack; (ii) migração idempotente no
   settings-merge do `upgrade.sh`: bump da registration 60→150 IFF valor
   atual == 60 (custom preservado) + check no `doctor.sh` + caso na família
   `test_upgrade_settings_migration.py`; (iii) sweep de literais no repo
   inteiro E `staged/` inteiro (fixtures de migração incluídas). → W1.
5. **C5 — números fixados por MEDIÇÃO, não por chute** (A: overhead; C:
   protocolo N≥5/2-tamanhos/carga; B: margem de 1 máquina). EXECUTADO
   in-debate: N=9 — small idle 25,8/33,3/34,9/36,3/38,8/68,8 s; big idle
   (15,4 KB) 58,4/51,3 s; small SOB CARGA (suíte em paralelo) **75,1 s**.
   p95≈75 s **> 70 s** → pela regra de escalada do próprio protocolo
   (Critic-C MF5): **interno 120 / registration 150** (não 100/120).
   150−120 = 30 s de margem absoluta (restaura a margem pré-uplift que
   Critic-B pediu; precedente de registration >120 já existe no kernel:
   `codex_review_user_code.py` timeout 130). Overhead não-invoke observado
   nos probes: ~0,3 s (expected→invoke) + startup — folga de 30 s cobre com
   sobra a variância de carga registrada na lição do perf-gate. → OQ1/OQ2.

## Single-agent insights kept

1. **Critic-A — ADR é AMEND-1 do ADR-110, não ADR novo.** Restrição DURA
   verificada: `land-plan163-pack.sh:242/:477` fail-closed em contagem
   181→183 e o número 183 já está consumido por bytes double-APPROVEd do
   pack congelado. Amend não muda contagem nem consome número; o pack não
   contém cópia staged de ADR-106/110 (não é revertido). Cross-ref ADR-106;
   precedente ADR-136-AMEND-1.
2. **Critic-C — janela de assimetria na sessão da cerimônia** (interno novo
   vale por-invocação; registration só pós-restart): NENHUM edit canônico
   na sessão da cerimônia pós-apply (closeout via `!`/bash) + freeze de
   edits canônicos em TODAS as sessões até o W3 PASS registrado. Sem isso,
   um deficit pós-âncora re-envenena o gate (mesma aritmética que matou a
   âncora `a4371c7`).
3. **Critic-C — mecânica da re-âncora corrigida**: um commit não contém o
   próprio sha; padrão do pin (`7860d62`): cerimônia commita
   `[SENT-PLAN164-RAIL]` → âncora escrita com sha+ts DESSE commit →
   commitada no closeout imediato.
4. **Critic-B — residual do env-knob nomeado no ADR-amend**
   (`CEO_PAIR_RAIL_TIMEOUT_S` sub-piso = fail-open universal; aceito porque
   env-control ⊃ ameaça e case F é auditável).
5. **Critic-C — `statusMessage` na registration** (kernel + template +
   cópias do pack): mata a sessão-congelada-sem-feedback na mesma cerimônia,
   zero superfície nova. Promovido a AC do W1.
6. **Critic-A — gatilho de recalibração no ADR-amend**: após ≥10 cases
   healthy, p95 de (`case.ts − expected.ts`) do audit-log revisita os
   números; query documentada no amend.
7. **Critic-A — alternativas rejeitadas nomeadas no ADR-amend** (review
   assíncrono pós-facto; downgrade de reasoning-effort por invocação) com
   as razões — honestidade do registro.
8. **Critic-B/C — semântica do PASS re-ancorado registrada**: o GATE-V2
   re-ancorado prova "liveness sob pin + timeout novo" (estritamente mais
   forte; o pin não é tocado). O registro do PASS no PLAN-163 diz isso
   explicitamente.

## Single-agent insights rejected / deferred

1. **Critic-B — `git verify-commit` da âncora**: DEFERRED (em clone de
   adopter a pubkey não está no keyring; a validação sentinel-tag do C1 já
   fecha o vetor primário). Candidato a hardening futuro se o gate for
   exportado para adopters.
2. **Critic-B — piso mínimo no env-knob** (`<10 → default`): DEFERRED para
   o amend como nota (mudar semântica de knob documentado é contrato novo;
   o residual nomeado + auditabilidade do case F bastam agora).
3. **Critic-B — clamp-to-bound no overflow**: aceito como nice-to-have no
   W1 SE couber no mesmo diff do hook sem crescer escopo; senão registrado
   no amend como known-wart (reset-to-default documentado).

## Plan adjustments

Índice (edits reais no arquivo do plano):
- §Approach: ADR fixado AMEND-1 do ADR-110 + racional do interlock.
- §Waves W0: item de medição marcado EXECUTADO com o dataset N=9 e a
  escalada 120/150 aplicada.
- §Waves W1: +ACs — teste de invariante (C2); migração upgrade.sh +
  doctor.sh + teste (C4-ii); guard de aposentadoria do pin-pack (C4-i);
  sweep repo+staged (C4-iii); statusMessage + `_comment` template (kept-5);
  sequência gêmeo-baseline→delta→review→gêmeo-novo (C3).
- §Waves W2: validação do resolve_anchor (C1); mecânica da âncora
  pós-commit (kept-3); freeze + closeout-via-bash (kept-2).
- §Waves W3: registro do PASS com a semântica "pin + timeout novo" (kept-8).
- §Open questions: OQ1=120, OQ2=150 (dados C5); OQ3/OQ4 re-drafted com as
  condições; tudo pendente de ratificação do Owner.

## Round verdict

**PROCEED** — design-coherent com os ajustes acima aplicados ao plano.
Convergência integral entre os críticos (nenhum par de posições mutuamente
exclusivas; as diferenças eram de profundidade, resolvidas pela medição).
Lembrete de contrato: este verdito NÃO autoriza ship — a autorização vem do
verification cascade (V1 determinístico → V2 pair-rail → V3 Owner GPG), e
as OQ1-OQ4 permanecem tie-break do Owner.
