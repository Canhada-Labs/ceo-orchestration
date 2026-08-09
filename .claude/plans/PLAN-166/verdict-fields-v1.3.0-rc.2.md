verdict: GO-WITH-CONDITIONS
generated_at: 2026-08-09T21:14:30Z
ttl_hours: 24
parent_sha: fcac12d36474f7a1181e1a2846f760db5ebe590b
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

## Derivacoes (parte do material assinado)

- transcript_hash = sha256 da concatenacao, em ordem a->e, dos
  transcript-{a,b,c,d,e}.log do round vigente (round 4) em
  .claude/plans/PLAN-166/repass-r2/.
- inputs_hash recomputavel via
  .github/scripts/validate-pair-rail-verdict.py sobre
  .claude/governance/pair-rail-inputs-hash-manifest.txt - identico ao
  da rc.1 (nenhuma superficie do trust-chain mudou desde 2026-08-04).
- delta_manifest_sha256 pina o MANIFEST-r2.sha256 reescrito em
  basenames (mesmos 10 hashes de conteudo; formato exigido pelo guard).
- Payloads raw (pre-redacao) nao sao commitados (precedente r1); pins
  sha256 registrados em repass-r2/PROVENANCE-r2.md.

## Condicoes (o "WITH-CONDITIONS") - 4 excecoes nomeadas de PRODUTO

Achados de produto 167/168 da parte a do re-pass, CONFIRMADOS por
leitura estrutural (S299/S300), TODOS fora do caminho mainline de
install/upgrade. Sao superficies canonicas - a cura exige cerimonia
GPG (ADR-190 s3 veta patch em ramo local) e esta STAGED no pack W3
(PLAN-169), que so pode landar apos o GA (freeze do trem). Rota (b)
ratificada pelo Owner (S299-manha): rc.2 corta COM as excecoes
nomeadas; o pack W3 as cura imediatamente pos-GA.

- V1 scripts/upgrade.sh _ov_obs_prior_record (:1826-1844):
  grep cru no manifesto sem consultar _BASELINE_INVALID (a cura
  R1-P0#2 guardou so o _baseline_lookup de :1027-1037) => linha
  duplicada/ambigua autoriza replace forcado. Classe compoem-errado
  S294.
- V2 scripts/upgrade.sh rota --pin pre-marcador (:2129-2138):
  NOTE promete "VERSION reflete o pin", mas :346-348 documenta VERSION
  NUNCA tocado => updater/forense reportam versao errada. Recorreu nas
  3 rodadas do rail.
- V4 scripts/_framework_manifest_set.sh (:352-360): symlink
  rejeitado por _wbm_link_allowed cai no elif [ -f ], que SEGUE o
  link => hash record de conteudo do adotante (fura o espirito da
  INV-2 por rota nova).
- V5 scripts/_framework_manifest_set.sh _wbm_link_allowed
  (:275): FMS_LINK_PATHS unset = allow-all ("too wide" documentado);
  scripts/install.sh (:2277-2279) exporta o modo SEM a lista (a cura
  anterior cobriu so o caller do upgrade).

Nota: V3 da triagem = OWN-0016, defeito de produto JA conhecido e
gateado (ADR-190 s2.6, RED esperado do nightly) - nao e excecao nova.

## Ratificacao approx/collect-errors (PLAN-166 F.14 / W0.3)

Ratifica-se, neste material assinado, a semantica do kind approx do
gate de claims numericas: erros de coleta > 0 = VIOLATION
(rule: approx/collect-errors), fail-closed - uma banda approx cuja
coleta falha nao passa vacuosamente. Teste:
test_collect_errors_fail_when_band_enforced. (O W0.3 prometia esta
ratificacao no material do W1; registrada aqui, primeira superficie
assinada do trem W6.1, conforme o paragrafo final do PLAN-166.)

## Excecao herdada (registro, nao-nova)

r6-P2 do PLAN-166: o 2o fator do controle de parity aceita evidencia
nao-causal (smoke-install.yml:206) - excecao nomeada JA ratificada
para o trem v1.3.0 (rota PLAN-169 OQ-5). A cura causal esta STAGED no
pack W3 (W3.2) e landa POS-GA - a excecao segue ABERTA neste corte e
no GA (registro honesto: nada aqui afirma cura landada). Nao gateia
este corte.
