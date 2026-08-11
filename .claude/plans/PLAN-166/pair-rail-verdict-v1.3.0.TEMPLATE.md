# Pair-Rail Verdict - v1.3.0 (GA)

```yaml
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
  - .claude/plans/PLAN-166/repass-ga/PROVENANCE-ga.md
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
gpg_signature: base64:@@SIG_B64@@
```

## Signature verification recipe

base64 -d do valor apos "base64:" -> .asc destacado; verificar contra
.claude/plans/PLAN-166/verdict-fields-v1.3.0.md (commitado junto).
Signer CFCFACF00335DC74.

<!-- VERDICT: GO-WITH-CONDITIONS -->
## Review record - re-pass do hold ADR-103 (advisory input)

- Reviewer: codex-cli 0.144.6 (codex exec --sandbox read-only), prompt
  + diff atraves do redactor ADR-114 como UM pipeline; pin ADR-182
  byte-exato; worktree detached da TAG v1.3.0-rc.3.
- Escopo: release mechanics, diff v1.2.0..v1.3.0-rc.3 (o trem inteiro:
  driver, tag guard, workflows de release/publish, superficies de
  versao, docs de release). Runner:
  repass-ga/run-ga-repass.sh (2 partes; escopo expandido com os
  helpers executados _release_bump_sites.py, await_release_gate.py e
  validate-pair-rail-verdict.py — achado P1-2 do pair-rail S300);
  verditos em repass-ga/verdict-ga-{1,2}.txt.
- Historia de review do trem (nao re-litigada, instruida no prompt):
  4 rodadas pre-rc.1 (18 achados, 17 curados, 1 refutado com citacao)
  + 4 rodadas multi-part rc.1->rc.2 (todas as curas landadas) + 1o
  re-pass do hold NO-GO sobre a rc.2 (8 achados reais, TODOS curados na
  rc.3; rail das curas GO em repass-rc3-cures/) + este re-pass do hold
  sobre a rc.3.
- Condicoes: as 4 excecoes nomeadas V1/V2/V4/V5 (por extenso no
  verdict-fields assinado da rc.2) seguem abertas por rota (b);
  curas STAGED no pack W3, que landa imediatamente pos-GA.
- Main CONGELADO do corte da rc.3 ate este GA: o unico delta e o proprio
  verdito + evidencia do hold (fechado pelo delta_allowlist acima e
  verificado pelo guard local + server-side).
