# Pair-Rail Verdict - v1.3.0

```yaml
verdict: GO-WITH-CONDITIONS
generated_at: 2026-08-17T18:44:49Z
ttl_hours: 24
parent_sha: 4273d6c3edbcf79add7156f41afd375b2f49941a
release_tag: v1.3.0
inputs_hash: 11146c1ef1d34f03943754c8c810c387420a4c6ffa46b1123094d1b5a453b6ab
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
delta_allowlist:
  - .claude/governance/pair-rail-verdict-v1.3.0.md
  - .claude/plans/PLAN-177/verdict-fields-v1.3.0.md
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
  - .claude/plans/PLAN-177/repass-rc4/run-rc4-repass.sh
delta_manifest: .claude/plans/PLAN-177/repass-rc4/MANIFEST-rc4.sha256
delta_manifest_sha256: fb1657bb29b6f038752a3d9f233f34852879499a03a360c5a91dde4bc7a443ce
tool_versions:
  codex_cli: 0.144.6
  codex_target_triple: aarch64-apple-darwin
  codex_payload_sha256: 80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff
  claude_code: claude-fable-5
  python: 3.9.6
transcript_hash: 065fcfbde8821fbfe83050a191dc77464152794ffde2f109496d0ce6920af483
rail_decisions: [part1=NO-GO, part2=GO-WITH-CONDITIONS]
findings: [ga-repass-t2-t12-NOGO-curados-por-rodada, t13-part1-nogo-part2-gowithconditions, lote-B-PLAN-178-44-rounds-2GOs-sentinel-SENT-PLAN178-LOTEB, ga-reseal-rc4-hold-ADR-103-sem-novo-repass-S310]
conditions:
  - RESIDUAL R1 (parte 1 t13, Owner-ratified 2026-08-16): fence-shadow variante 5 (yaml block hidden inside raw HTML comment) — extractor is a line-whitelist, not a CommonMark parser; a block deliberately hidden by the SIGNER of an Owner-GPG-signed envelope is outside the threat model (signer == Owner). Definitive cure = fixed-format envelope (canonical title, blank line, opener) in BOTH twins; named v1.4.0 item.
  - RESIDUAL R2 (parte 1 t13 P2): pair-rail-verdict-template.md still describes gpg_signature as an armored multiline value while the strict grammar requires the single-line base64 form. The template is an ARBITRATION-KERNEL path (no sentinel route; requires Owner CEO_KERNEL_OVERRIDE in-session), so it follows the next Owner-authorized kernel touch. The generator (PLAN-177/gen-envelope-rc4.py) emits the canonical form and validates the fields against the twins' grammar before writing, so no operator following the generator can produce a rejected envelope.
  - CONDITION C1 (parte 2 t13 P2): root .gitignore dry-run parity — with a deeper state/.gitignore re-including mcp_client_secrets/, upgrade --dry-run reports would-ENSURE and exits 0 while the real helper fails closed; fail-closed in execution. Follow-up: shared read-only root-ignore preview + control on the S11 fixture. Destino: v1.4.0 train.
  - CONDITION C2 (t6 conditions, carried): 5 P2 test/doc/wiring items — stamp same-line and Contract-row 5-cell CURED (t7); gitignore prose CURED (t7); --ceremony help CURED (t7); CI wiring of controls CURED (t7, sentinel round-2). All closed.
  - CONDITION C3 (validate.yml:869 stale comment): arbitration-kernel path, no sentinel route by design; comment says the replay suite is local-only while it now runs nightly. Follows the next Owner-authorized kernel touch. Zero executable change pending.
gpg_signature: base64:LS0tLS1CRUdJTiBQR1AgU0lHTkFUVVJFLS0tLS0KCmlKRUVBQllLQURrV0lRU3VteU52MnZCR0tIUUdER3ZQejZ6d0F6WGNkQVVDYW9OWW5Cc1VnQUFBQUFBRUFBNXQKWVc1MU1pd3lMalVyTVM0eE1pd3dMRE1BQ2drUXo4K3M4QU0xM0hRNkF3RUFsZk5ya1RFQ1k2d0lScGl1b25XNApCdDd6RGo5Ym93TVpQeTNYcStDUlFlQUJBSmllVlViY2g0clVQTjJ5NG01OEZZK3lxQUpOYllHdEk0ZHdpRjQ0CjVKRUsKPVJWZS8KLS0tLS1FTkQgUEdQIFNJR05BVFVSRS0tLS0tCg==
```

## Signature verification recipe

base64 -d do valor apos "base64:" -> .asc destacado; verificar contra
.claude/plans/PLAN-177/verdict-fields-v1.3.0.md (commitado junto).
Signer CFCFACF00335DC74. As CONDICOES fazem parte do material assinado
(sub-mapa `conditions:` dos fields).

<!-- VERDICT: GO-WITH-CONDITIONS -->
## Review record - GA re-sela o veredito da rc.4 (hold ADR-103)

- Rota S310 Owner-ratificada: o hold de 24h da v1.3.0-rc.4 completou SEM
  novo re-pass; este envelope re-sela para a tag estavel o MESMO
  veredito t13 (evidencia em repass-rc4/, identica, ja commitada na
  arvore do parent). parent_sha = commit da v1.3.0-rc.4; a cadeia
  evidencia->candidato (ff27e54) ->envelope-rc.4->parent e verificada
  pelo gerador (binding transitivo).
- Contexto do re-pass: t2..t12 NO-GO com curas a cada rodada
  (quarentenas repass-rc4-20260816-tN-NOGO/, cronica em
  repass-rc4-advisory-preparent/NOTA.md) -> t13 (rodada FINAL
  declarada) fechado por decisao Owner-ratificada; decisoes por
  rail em `rail_decisions:` (material assinado).
- Reviewer: codex-cli (codex exec --sandbox read-only), prompt +
  diff atraves do redactor ADR-114 como UM pipeline; pin ADR-182
  VERIFICADO (check_pair_rail --verify-codex-pin) antes de gerar.

## Derivacoes (parte do material assinado)

- transcript_hash = sha256(transcript-rc4-1.log || transcript-rc4-2.log).
- inputs_hash RECOMPUTADO nesta arvore com compute_inputs_hash do
  proprio validador.
- parent_sha VINCULADO ao commit da v1.3.0-rc.4 cujo envelope selado
  aponta o candidato do runner/PROVENANCE (gerador recusa qualquer
  outro SHA).
- delta_manifest_sha256 pina MANIFEST-rc4.sha256 (12 entradas, runner
  incluso). Payloads raw NAO commitados; pins em PROVENANCE-rc4.md.

## Excecoes herdadas (registro)

V1/V2/V4/V5 do trem (verdict-fields-v1.3.0-rc.2.md §Condicoes) seguem
abertas pela rota (b) ratificada: curas STAGED no pack W3 (PLAN-169),
landa por cerimonia GPG apos o GA com re-staging por ITEM semantico.
