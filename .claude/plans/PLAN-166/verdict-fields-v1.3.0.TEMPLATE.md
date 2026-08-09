<!-- TEMPLATE - OWNER-GA-CUT.sh preenche @@PARENT_SHA@@, @@GENERATED_AT@@,
     @@DELTA_MANIFEST_SHA@@ e @@TRANSCRIPT_SHA@@; arquivo final em
     .claude/plans/PLAN-166/verdict-fields-v1.3.0.md (caminho canonico do
     guard). Owner assina o final; .asc embutido em base64 no verdito. -->
verdict: GO-WITH-CONDITIONS
generated_at: @@GENERATED_AT@@
ttl_hours: 24
parent_sha: @@PARENT_SHA@@
release_tag: v1.3.0
inputs_hash: 1c1d8f4404521de942451b7f7c25cba721eedaeb51d6a4f01d3dde20335ed10f
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
delta_allowlist:
  - .claude/governance/pair-rail-verdict-v1.3.0.md
  - .claude/plans/PLAN-166/verdict-fields-v1.3.0.md
  - .claude/plans/PLAN-166/repass-ga/MANIFEST-ga.sha256
  - .claude/plans/PLAN-166/repass-ga/payload-ga-1.redacted.txt
  - .claude/plans/PLAN-166/repass-ga/payload-ga-2.redacted.txt
  - .claude/plans/PLAN-166/repass-ga/diff-ga-1.patch
  - .claude/plans/PLAN-166/repass-ga/diff-ga-2.patch
  - .claude/plans/PLAN-166/repass-ga/paths-ga-1.manifest.txt
  - .claude/plans/PLAN-166/repass-ga/paths-ga-2.manifest.txt
  - .claude/plans/PLAN-166/repass-ga/verdict-ga-1.txt
  - .claude/plans/PLAN-166/repass-ga/verdict-ga-2.txt
  - .claude/plans/PLAN-166/repass-ga/transcript-ga-1.log
  - .claude/plans/PLAN-166/repass-ga/transcript-ga-2.log
delta_manifest: .claude/plans/PLAN-166/repass-ga/MANIFEST-ga.sha256
delta_manifest_sha256: @@DELTA_MANIFEST_SHA@@
tool_versions:
  codex_cli: 0.144.6
  codex_target_triple: aarch64-apple-darwin
  codex_payload_sha256: 80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff
  claude_code: claude-fable-5
  python: 3.9.6
transcript_hash: @@TRANSCRIPT_SHA@@
findings: [hold-repass-ga-2-partes-verditos-em-verdict-ga-N-txt, V1-upgrade-observer-sem-baseline-guard-EXCEPTION-W3, V2-pin-version-note-falsa-EXCEPTION-W3, V4-symlink-rejeitado-vira-hash-record-EXCEPTION-W3, V5-fms-link-paths-unset-allow-all-EXCEPTION-W3]

## Derivacoes (parte do material assinado)

- transcript_hash = sha256 da concatenacao transcript-ga-1.log +
  transcript-ga-2.log (hold ADR-103 em 2 partes, worktree da tag rc.2).
- inputs_hash identico ao da rc.2 por construcao: main CONGELOU do
  corte ao GA (o parent_sha e o unico delta legitimo = artefatos deste
  verdito), e o validator recomputa server-side.
- delta_manifest_sha256 pina MANIFEST-ga.sha256 (basenames).
- payload-ga.raw.txt nao commitado (precedente r1/r2); pin em
  repass-ga/PROVENANCE-ga.md.

## Condicoes (o "WITH-CONDITIONS") - carregadas da rc.2, INALTERADAS

As 4 excecoes nomeadas de produto V1/V2/V4/V5 do verdito assinado da
rc.2 (verdict-fields-v1.3.0-rc.2.md, secao "Condicoes") seguem abertas
NO GA por decisao de rota (b): main congelado do corte ao GA, curas
STAGED no pack W3 (PLAN-169), que landa por cerimonia GPG imediatamente
apos este GA. O re-pass do hold foi instruido a reportar se qualquer
uma fosse PIOR que o avaliado ou alcancavel no caminho mainline - o
verditos do rail estao em repass-ga/verdict-ga-{1,2}.txt, sob o manifesto
pinado acima.

## Ratificacao approx/collect-errors

Ratificada no material assinado da rc.2 (F.14 / W0.3); segue valida
para o trem - nada mudou entre os dois verditos (main congelado).

## Excecao herdada (registro)

r6-P2 smoke-install.yml:206 (2o fator nao-causal) - excecao ja
ratificada do trem; cura canonica no pack W3 (W3.2).
