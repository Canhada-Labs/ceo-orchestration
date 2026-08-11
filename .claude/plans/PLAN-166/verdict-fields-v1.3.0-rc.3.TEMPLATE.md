<!-- TEMPLATE - OWNER-RC3-CUT.sh preenche @@PARENT_SHA@@, @@GENERATED_AT@@,
     @@DELTA_MANIFEST_SHA@@ e @@TRANSCRIPT_SHA@@; arquivo final em
     .claude/plans/PLAN-166/verdict-fields-v1.3.0-rc.3.md (caminho canonico do
     guard). Owner assina o final; .asc embutido em base64 no verdito. -->
verdict: GO-WITH-CONDITIONS
generated_at: @@GENERATED_AT@@
ttl_hours: 24
parent_sha: @@PARENT_SHA@@
release_tag: v1.3.0-rc.3
inputs_hash: 1c1d8f4404521de942451b7f7c25cba721eedaeb51d6a4f01d3dde20335ed10f
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
delta_allowlist:
  - .claude/governance/pair-rail-verdict-v1.3.0-rc.3.md
  - .claude/plans/PLAN-166/verdict-fields-v1.3.0-rc.3.md
  - .claude/plans/PLAN-166/repass-rc3-cures/MANIFEST-cures.sha256
  - .claude/plans/PLAN-166/repass-rc3-cures/CEREMONY-MANIFEST.sha256
  - .claude/plans/PLAN-166/repass-rc3-cures/PROVENANCE-cures.md
  - .claude/plans/PLAN-166/repass-rc3-cures/diff-cures-round1.patch
  - .claude/plans/PLAN-166/repass-rc3-cures/diff-cures-round2.patch
  - .claude/plans/PLAN-166/repass-rc3-cures/diff-cures-round3.patch
  - .claude/plans/PLAN-166/repass-rc3-cures/diff-cures-round4.patch
  - .claude/plans/PLAN-166/repass-rc3-cures/diff-cures-round5.patch
  - .claude/plans/PLAN-166/repass-rc3-cures/diff-cures-round6.patch
  - .claude/plans/PLAN-166/repass-rc3-cures/diff-cures-round7.patch
  - .claude/plans/PLAN-166/repass-rc3-cures/payload-cures-round1.redacted.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/payload-cures-round2.redacted.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/payload-cures-round3.redacted.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/payload-cures-round4.redacted.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/payload-cures-round5.redacted.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/payload-cures-round6.redacted.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/payload-cures-round7.redacted.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/transcript-cures-round1.log
  - .claude/plans/PLAN-166/repass-rc3-cures/transcript-cures-round2.log
  - .claude/plans/PLAN-166/repass-rc3-cures/transcript-cures-round3.log
  - .claude/plans/PLAN-166/repass-rc3-cures/transcript-cures-round4.log
  - .claude/plans/PLAN-166/repass-rc3-cures/transcript-cures-round5.log
  - .claude/plans/PLAN-166/repass-rc3-cures/transcript-cures-round6.log
  - .claude/plans/PLAN-166/repass-rc3-cures/transcript-cures-round7.log
  - .claude/plans/PLAN-166/repass-rc3-cures/verdict-cures-round1.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/verdict-cures-round2.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/verdict-cures-round3.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/verdict-cures-round4.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/verdict-cures-round5.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/verdict-cures-round6.txt
  - .claude/plans/PLAN-166/repass-rc3-cures/verdict-cures-round7.txt
delta_manifest: .claude/plans/PLAN-166/repass-rc3-cures/MANIFEST-cures.sha256
delta_manifest_sha256: @@DELTA_MANIFEST_SHA@@
tool_versions:
  codex_cli: 0.144.6
  codex_target_triple: aarch64-apple-darwin
  codex_payload_sha256: 80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff
  claude_code: claude-fable-5
  python: 3.9.6
transcript_hash: @@TRANSCRIPT_SHA@@
findings: [ga-repass-NOGO-8-achados-curados-rc3-sentinel-RC3-approved, rail-curas-round7-GO, V1-upgrade-observer-sem-baseline-guard-EXCEPTION-W3, V2-pin-version-note-falsa-EXCEPTION-W3, V4-symlink-rejeitado-vira-hash-record-EXCEPTION-W3, V5-fms-link-paths-unset-allow-all-EXCEPTION-W3]

## Derivacoes (parte do material assinado)

- transcript_hash = sha256 da concatenacao, em ordem de round
  (round1 -> round2 -> round3 -> round4 -> round5 -> round6 -> round7), dos transcript-cures-roundN.log em
  .claude/plans/PLAN-166/repass-rc3-cures/.
- inputs_hash identico ao da rc.2: nenhuma superficie do trust-chain
  (pair-rail-inputs-hash-manifest.txt) mudou nas curas — as curas tocam
  CHANGELOG, verify-counts, checklist, npm-publish/release.yml e testes,
  nenhum deles no manifesto do inputs_hash. O validator recomputa
  server-side no step 15.
- delta_manifest_sha256 pina MANIFEST-cures.sha256 (basenames).
- Payloads raw (pre-redacao) nao commitados (precedente r1/r2/ga); pins
  sha256 em repass-rc3-cures/PROVENANCE-cures.md.

## Condicoes (o "WITH-CONDITIONS") - as 4 excecoes do trem, INALTERADAS

V1/V2/V4/V5 do verdito assinado da rc.2 (verdict-fields-v1.3.0-rc.2.md,
secao "Condicoes") seguem abertas nesta rc.3 pela MESMA rota (b)
ratificada: curas STAGED no pack W3 (PLAN-169), que landa por cerimonia
GPG imediatamente apos o GA. Nenhuma excecao NOVA entra neste corte: os
8 achados do re-pass NO-GO da rc.2 foram CURADOS (nao
excepcionados) — curas aplicadas pelo sentinel RC3-approved.md e
revisadas pelo rail de curas ate GO.

## Ratificacao approx/collect-errors

Ratificada no material assinado da rc.2 (F.14 / W0.3); segue valida.

## Excecao herdada (registro)

r6-P2 smoke-install.yml:206 (2o fator nao-causal) - excecao ja
ratificada do trem; cura canonica no pack W3 (W3.2).
