# S318-approved — sentinel do pack SENT-S318 (DRAFT — assinar como S318-approved.md)

> Assinatura em um passo: `! bash ~/canhada-labs/OWNER-S318-SIGN.sh`
> (gera este arquivo com Anchor-SHA real, registra a eleição do
> locked-corpus, assina, dry-run, land).

Plans: PLAN-169 (emenda ADR-163) + PLAN-174 (re-pin ADR-182 §5 e
registro/reposição `ceremony_lint_unlock_used`) + PLAN-182 (emendas
ADR-001 AC-7 e ADR-079 OQ-4)
Wave: pack consolidado S318 (staged em `5ba9cf6`)
Anchor-SHA: e3b89c2fc1d38b5a7447c2e2b8d97a22060c7d80
Data: 2026-08-20
Locked-corpus catch_rate (ADR-111 §2, eleição do Owner): RUN

## Scope

```
.github/workflows/validate.yml
.claude/scripts/profile-opus-4-7.py
.claude/scripts/tests/test_profile_opus47_latency_gate.py
.claude/plans/PLAN-159/wave2-regression-proof.sh
.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
.claude/governance/codex-cli-pin-manifest.json
.claude/governance/codex-cli-pin.txt
.claude/hooks/_lib/audit_emit.py
SPEC/v1/audit-log.schema.md
.claude/scripts/check-ceremony-script.py
.claude/hooks/tests/test_audit_emit_ceremony_lint_unlock.py
.claude/hooks/tests/test_w5_scrub_enforcement.py
.claude/adr/ADR-001-runtime-state-directory.md
.claude/adr/ADR-079-prompt-sha-salt-hmac-impact.md
```

## O que este pack muda

1. **Emenda ADR-163 (S318) — o gate hook-latency para de precificar o
   runner.** p95 120→180ms HARD (recalibrado com a evidência de
   2026-08-20: run 32408847458 falhou 3 attempts — 110.6/302/162.1ms —
   e carimbou "regressão" com o local em 70.6ms; artifacts N=1000 de
   18–20/ago mostram a distribuição inteira do runner movendo 1.5–2.3×
   entre janelas). p99 vira ADVISORY no gate do CI (flag nova
   `--p99-advisory`: breach vira `p99_within=false` + WARN no stderr e
   step summary, nunca exit≠0 — a avenida "demote p99 to advisory" que
   o próprio ADR deferiu em 2026-07 "revisit with Wave-2 data"). N=200,
   retry wrapper, probe de contenção e os dois controles anti-vacuity:
   INTOCADOS. Ratificação do Owner: AskUserQuestion S318 ("Emenda
   ADR-163 (Recomendado)").
2. **Re-pin codex 0.147.0 (ADR-182 §5).** Manifest de payload:
   sha256 `19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37`
   (aarch64-apple-darwin; mismatch vs o pin 0.144.6 confirmado pelo
   passo 1 `--verify-codex-pin`), `npm_integrity` do artefato de
   plataforma registrado. Range do `codex-cli-pin.txt`: widen-upper-only
   `<0.145.0` → `<0.148.0`, fora de janela de release (GA v1.3.0
   cortado 2026-08-17). Destrava o wire da W2 do PLAN-174. A eleição
   run-vs-defer do locked-corpus fica registrada no cabeçalho deste
   sentinel.
3. **Registro + reposição do `ceremony_lint_unlock_used`.** A ação entra
   nas DUAS fontes canônicas (`_KNOWN_ACTIONS` 325→326 + linha v2.57 do
   `SPEC/v1/audit-log.schema.md`) com branch de scrub deny-by-default
   dedicado (`file_sha256` 16-hex com sentinela `"invalid"`;
   `reason_len` int TYPE-strict clampado 0..9999; o TEXTO do motivo
   nunca alcança o wire) e o emit é REPOSTO em
   `check-ceremony-script.py::_emit_unlock_audit` — encerrando a
   parcagem de `908707e` no mesmo pack assinado, como a regra "um
   emissor não embarca antes do registro dele" exige (precedente
   v2.51/SENT-GK-F). Correção material achada no clone-sim: o shape
   `fields={...}` de `7d467a8` aninhava o payload sob uma chave que o
   scrub corretamente dropa — o emissor reposto usa kwargs top-level.
   Bump do pin de contagem em `test_w5_scrub_enforcement.py` (325→326,
   linha nomeando a ação) + teste novo
   `test_audit_emit_ceremony_lint_unlock.py` (12 casos: registro,
   allowlist, smuggle, coerções, clamps).
4. **Emendas que destravam a W1 do PLAN-182** (direção ratificada pelo
   Owner via AskUserQuestion S318): **ADR-001** — `<project-slug>` vira
   NORMATIVO com a derivação path-based nativa do Claude Code; um
   resolvedor único consumido pela família; invariante de
   família-atômica (log, key, lock, errors, salt movem JUNTOS — a
   matriz W0 mediu `CEO_AUDIT_LOG_PATH` partindo a família); blast
   radius L2→L3. **ADR-079** — "installation" passa a significar
   PROJETO; "No rotation" ganha exatamente UMA exceção REGISTRADA (a
   migração: herdeiro da cadeia herda o `.salt` byte-a-byte, demais
   cunham salt novo com marcador na cadeia); teste de distinção com
   controle negativo exigido na W1. Limite honesto mantido nos dois
   textos: nada disso restaura tamper-evidence entre tenants do mesmo
   UID.

## Prova pré-assinatura (S318, clone local com o pack aplicado)

`check-audit-registry-coverage` exit 0; pytest 54/54 (teste novo +
profiler + w5) + 44/44 (payload-pin + validate-pair-rail contra o
manifest NOVO) + 15/15 (check-ceremony-script); controle positivo do
advisory nos DOIS sentidos no CLI real (sem flag: exit 1 nomeando p99;
com flag: exit 0 + exatamente 1 WARN + `p99_within=false` em todas as
entries); `proof-retry-matrix.sh` 11/11 contra o run-block novo do
validate.yml; **`wave2-regression-proof.sh` PROOF GREEN com o teto 180**
(regressão injetada ~215ms RED-flagada através do wrapper, breach medido
nos dois entries de output_secrets, 2026-08-20T22:03:50Z);
`verify-counts` 0 drift. Pair-rail codex (0.147.0, advisory — o pin
que este pack re-pina): rodada 1 registrada em
`.claude/plans/PLAN-174/staged-s318/RAIL-R1.md`.

## Depois do land

`python3 .claude/hooks/check_pair_rail.py --verify-codex-pin` deve sair
0 (G6 verifica); push manual; W2 do PLAN-174 (wire) fica destravada;
W1 do PLAN-182 fica desbloqueada no frontmatter (`blocked_on_adr`
resolvido — o flip do texto do frontmatter é edição de plano da próxima
sessão de execução do 182).
