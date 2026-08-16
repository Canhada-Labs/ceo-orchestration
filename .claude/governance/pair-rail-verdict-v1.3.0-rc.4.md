# Pair-Rail Verdict - v1.3.0-rc.4

```yaml
verdict: GO-WITH-CONDITIONS
generated_at: 2026-08-16T09:25:11Z
ttl_hours: 24
parent_sha: 5af2cd752cdc6ba361154b2c21b0b1e425523353
release_tag: v1.3.0-rc.4
inputs_hash: 4dcf78de5a7e8c18f055b8f621b96a1c5a39f17a7432b2580ef09359046abdb8
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
delta_allowlist:
  - .claude/governance/pair-rail-verdict-v1.3.0-rc.4.md
  - .claude/plans/PLAN-177/verdict-fields-v1.3.0-rc.4.md
  - .claude/plans/PLAN-177/repass-rc4/MANIFEST-rc4.sha256
  - .claude/plans/PLAN-177/repass-rc4/PROVENANCE-rc4.md
  - .claude/plans/PLAN-177/repass-rc4/diff-rc4-1.patch
  - .claude/plans/PLAN-177/repass-rc4/diff-rc4-2.patch
  - .claude/plans/PLAN-177/repass-rc4/paths-rc4-1.manifest.txt
  - .claude/plans/PLAN-177/repass-rc4/paths-rc4-2.manifest.txt
  - .claude/plans/PLAN-177/repass-rc4/payload-rc4-1.redacted.txt
  - .claude/plans/PLAN-177/repass-rc4/payload-rc4-2.redacted.txt
  - .claude/plans/PLAN-177/repass-rc4/transcript-rc4-1.log
  - .claude/plans/PLAN-177/repass-rc4/transcript-rc4-2.log
  - .claude/plans/PLAN-177/repass-rc4/verdict-rc4-1.txt
  - .claude/plans/PLAN-177/repass-rc4/verdict-rc4-2.txt
delta_manifest: .claude/plans/PLAN-177/repass-rc4/MANIFEST-rc4.sha256
delta_manifest_sha256: ef0c7656978574fbe3301506d2e86b3a475da3ad54edec863dac6c4222e9af2b
tool_versions:
  codex_cli: 0.144.6
  codex_target_triple: aarch64-apple-darwin
  codex_payload_sha256: 80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff
  claude_code: claude-fable-5
  python: 3.9.6
transcript_hash: 7d5571a5b4643eab7786af6c0ab98184c4643ef5462504e1f80cac285db9d694
findings: [ga-repass-t2-NOGO-8-achados-curados, t3-NOGO-6-achados-curados, t5-NOGO-5-achados-curados, t6-GO-WITH-CONDITIONS-nas-2-partes, lote-B-PLAN-178-44-rounds-2GOs-sentinel-SENT-PLAN178-LOTEB]
gpg_signature: base64:LS0tLS1CRUdJTiBQR1AgU0lHTkFUVVJFLS0tLS0KCmlKRUVBQllLQURrV0lRU3VteU52MnZCR0tIUUdER3ZQejZ6d0F6WGNkQVVDYW9HREFSc1VnQUFBQUFBRUFBNXQKWVc1MU1pd3lMalVyTVM0eE1pd3dMRE1BQ2drUXo4K3M4QU0xM0hReVlnRUFrR3pZSlNDdi84OXIrOE9RanJXeApiWkw3Zi80WGJ5MERrM3h1NzRJUkhuVUJBTlFaMi9sdjIwMkRXaktwS0NkN0ZJUXdKeDc3bEdFeTE0UVVsSnhRCkpQQUwKPU1tVmMKLS0tLS1FTkQgUEdQIFNJR05BVFVSRS0tLS0tCg==
```

## Signature verification recipe

base64 -d do valor apos "base64:" -> .asc destacado; verificar contra
.claude/plans/PLAN-177/verdict-fields-v1.3.0-rc.4.md (commitado junto).
Signer CFCFACF00335DC74.

<!-- VERDICT: GO-WITH-CONDITIONS -->
## Review record - re-pass do CANDIDATO rc.4 (advisory input)

- Contexto: o re-pass do hold sobre a rc.3 (12/08) terminou NO-GO com 4
  P1; as curas (PLAN-177 t1-t2) + o Lote B do PLAN-178 (spawn acceptance
  contract v2, sentinel SENT-PLAN178-LOTEB, rail proprio de 44 rounds com
  2 GOs consecutivos) landaram em main. O re-pass do CANDIDATO rodou 4
  tentativas nesta sessao: t2 NO-GO (8 achados) -> curas t3 -> t3 NO-GO
  (6 achados) -> curas t4 -> t5 NO-GO (5 achados) -> curas t6 -> **t6
  GO-WITH-CONDITIONS nas DUAS partes** (runner
  PLAN-177/repass-rc4/run-rc4-repass.sh, pin 5af2cd7; evidencia NO-GO
  arquivada em repass-rc4-20260816-t{2,3,5}-NOGO/).
- Reviewer: codex-cli 0.144.6 (codex exec --sandbox read-only), prompt +
  diff atraves do redactor ADR-114 como UM pipeline; pin ADR-182.
- Achados curados no caminho (23 no re-pass + ~60 no rail do Lote B):
  decision gate fail-closed nas DUAS rails (continuacao indentada,
  comentario colado, whitespace Unicode, separador obrigatorio),
  gitignore delivery symlink-safe com previews honestos, schemas de
  plans/ hash-gated, ceremony pre-state fail-safe com persistencia so
  explicita, exemptions por-ausencia do ceo-boot aposentadas, npm
  honesty (INTEGRITY/SBOM/install-npm).

## Derivacoes (parte do material assinado)

- transcript_hash = sha256 da concatenacao transcript-rc4-1.log +
  transcript-rc4-2.log em .claude/plans/PLAN-177/repass-rc4/.
- inputs_hash RECOMPUTADO nesta arvore (difere da rc.3: o trust-chain
  mudou — validate-pair-rail-verdict.py e _release_tag_guard.py estao no
  manifesto e foram CURADOS pelo proprio re-pass). O validator recomputa
  server-side no step 15; o valor acima foi validado localmente com o
  argv literal do step-15 ANTES do push.
- delta_manifest_sha256 pina MANIFEST-rc4.sha256 (basenames).
- Payloads raw (pre-redacao) nao commitados (precedente r1/r2/ga); pins
  sha256 em repass-rc4/PROVENANCE-rc4.md.

## Condicoes (o "WITH-CONDITIONS") — 5 P2 de teste/doc/wiring

1. (p1) scanner de versao: stamp same-line mascarava literal stale —
   remover so o match do stamp + positive control.
2. (p1) Contract rows de 5 celulas silenciosamente descartadas —
   rejeitar malformadas + relapse control.
3. (p2) prosa do .claude/.gitignore gerado: declarar "never replaced;
   missing mandatory posture entries may be appended".
4. (p2) upgrade.sh --help documenta --ceremony <maintainer|user> com
   precedencia recorded-state.
5. (p2) wirar test-gitignore-symlink-and-dryrun-unit.sh + casos
   pre-state ceremony no smoke-install.yml/validate.yml (canonico —
   amendment GPG proprio).
Registradas como follow-up (task #13 da sessao; destino: antes do GA se
o Owner quiser, senao trem v1.4.0). Nenhuma e release-blocking: os dois
vereditos dizem "the four release-blocking cures are complete".

## Excecoes herdadas (registro)

V1/V2/V4/V5 do trem (verdict-fields-v1.3.0-rc.2.md §Condicoes) seguem
abertas pela MESMA rota (b) ratificada: curas STAGED no pack W3
(PLAN-169), que landa por cerimonia GPG imediatamente apos o GA — com o
re-staging por ITEM semantico (11/29 STALE, lição S304). r6-P2
smoke-install.yml (2o fator nao-causal) segue excepcionado.
