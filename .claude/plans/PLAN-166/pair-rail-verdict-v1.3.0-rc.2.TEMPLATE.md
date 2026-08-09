# Pair-Rail Verdict - v1.3.0-rc.2

```yaml
verdict: GO-WITH-CONDITIONS
generated_at: @@GENERATED_AT@@
ttl_hours: 24
parent_sha: @@PARENT_SHA@@
release_tag: v1.3.0-rc.2
inputs_hash: 1c1d8f4404521de942451b7f7c25cba721eedaeb51d6a4f01d3dde20335ed10f
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
delta_allowlist:
  - .claude/governance/pair-rail-verdict-v1.3.0-rc.2.md
  - .claude/plans/PLAN-166/verdict-fields-v1.3.0-rc.2.md
  - .claude/plans/PLAN-166/repass-r2/MANIFEST-r2.sha256
  - .claude/plans/PLAN-166/repass-r2/payload-a.redacted.txt
  - .claude/plans/PLAN-166/repass-r2/payload-b.redacted.txt
  - .claude/plans/PLAN-166/repass-r2/payload-c.redacted.txt
  - .claude/plans/PLAN-166/repass-r2/payload-d.redacted.txt
  - .claude/plans/PLAN-166/repass-r2/payload-e.redacted.txt
  - .claude/plans/PLAN-166/repass-r2/diff-a.patch
  - .claude/plans/PLAN-166/repass-r2/diff-b.patch
  - .claude/plans/PLAN-166/repass-r2/diff-c.patch
  - .claude/plans/PLAN-166/repass-r2/diff-d.patch
  - .claude/plans/PLAN-166/repass-r2/diff-e.patch
delta_manifest: .claude/plans/PLAN-166/repass-r2/MANIFEST-r2.sha256
delta_manifest_sha256: 1c7b3758d4b746b31118037900ebffba71a6cf4416c206db9fba54e87b2d4d3c
tool_versions:
  codex_cli: 0.144.6
  codex_target_triple: aarch64-apple-darwin
  codex_payload_sha256: 80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff
  claude_code: claude-fable-5
  python: 3.9.6
transcript_hash: 4b75aee401631f98f12d78ac3910678692f02b1cdbbf27a631a7c48c846f5ff2
findings: [r4-P1-injector-env-leak-FIXED-c0295e1, r4-P2-injector-rc-lax-FIXED-c0295e1, V1-upgrade-observer-sem-baseline-guard-EXCEPTION-W3, V2-pin-version-note-falsa-EXCEPTION-W3, V4-symlink-rejeitado-vira-hash-record-EXCEPTION-W3, V5-fms-link-paths-unset-allow-all-EXCEPTION-W3]
gpg_signature: base64:@@SIG_B64@@
```

## Signature verification recipe

base64 -d do valor apos "base64:" -> .asc destacado; verificar contra
.claude/plans/PLAN-166/verdict-fields-v1.3.0-rc.2.md (commitado junto,
caminho canonico do guard). Signer CFCFACF00335DC74. O arquivo
verdict-fields carrega, alem dos campos acima, as 4 excecoes nomeadas
POR EXTENSO e a ratificacao approx/collect-errors - tudo sob a
assinatura.

<!-- VERDICT: GO-WITH-CONDITIONS -->
## Review record - re-pass rc.1 -> candidato rc.2 (advisory input)

- Reviewer: codex-cli 0.144.6 (codex exec --sandbox read-only),
  prompt+diff atraves do redactor ADR-114 como UM pipeline; pin de
  payload ADR-182 verificado byte-exato antes de cada invocacao
  (80a3933d..., aarch64-apple-darwin).
- Datas: 2026-08-08/09 (S299-S300). Rodadas: 4, multi-part (5 partes
  a-e por rodada; delta vivo rc.1->candidato ~790KB > cap 256KB do
  redactor => runner multi-part com truncamento fail-closed).
- Escopo: diff unificado v1.3.0-rc.1..candidato particionado em
  (a) framework scripts install/upgrade/generator + root hygiene,
  (b) harness e2e scripts/tests, (c) governance scripts, (d) suites
  de teste de scripts, (e) hooks tests + docs + workflows + root docs.
- Trajetoria: r1 sobre o pack W2 (4 achados reais MEUS, curados em
  39fdd27) -> r2 sobre 39fdd27 (NEEDS 4/5 + parte c FATAL de redacao:
  redactor reescrevia model-deprecations.json; 9 reais curados em
  fe6f484; excluida por proveniencia no r3) -> r3 sobre fe6f484
  (parte d = APPROVE; curas baratas reais em 3138deb: sonda login
  exec-free M4, doc npm supply-chain de pacote inexistente, prosa de
  frota, no-speed-claim) -> r4 sobre 3138deb+d1b6f14 (NEEDS 5/5;
  2 reais NOVOS na parte d - env do teste vazando p/ HOME real via
  subprocess e rc aceitando crash - curados em c0295e1).
- Candidato final: c0295e1 (CI verde; nightly Linux verde 2x com
  62 GREEN / 3 RED exatos {0016,0024,0027}).
- Criterio de parada: triagem COMPLETA de todos os achados das 4
  rodadas (cada um curado, refutado com citacao, ou promovido a
  excecao nomeada) - nao "rodada limpa", que e claim e nao prova.
- Residuais que NAO gateiam este corte, todos nomeados:
  (i) 4 excecoes de produto V1/V2/V4/V5 (superficie canonica;
  cerimonia; curas STAGED no pack W3 pos-GA) - detalhe por extenso no
  verdict-fields assinado; (ii) endurecimento do INSTRUMENTO
  harness/parity (wave propria; inclui skew 120s do await-gate,
  residual documentado no codigo desde o 166); (iii) release.yml P2
  marker-equality whitespace (canonico -> pack W3); (iv) OWN-0016
  conhecido e gateado (ADR-190 s2.6).
- Ratificacao approx/collect-errors: no verdict-fields assinado
  (compromisso do paragrafo final do PLAN-166, cumprido aqui).
- Evidencia: .claude/plans/PLAN-166/repass-r2/ (payloads redacted,
  diffs, verditos, transcripts, PROVENANCE-r2.md com pins dos raws;
  MANIFEST-r2.sha256 pinado neste verdito por delta_manifest_sha256).
